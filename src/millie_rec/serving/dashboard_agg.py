"""GET /api/dashboard 집계(백엔드 서빙 01 §11, D-13 최소형) — 아키 §9-3 목록 외 신설(B6)."""

import json
import logging
from collections import Counter, defaultdict
from collections.abc import Callable, Sequence
from contextlib import suppress
from datetime import UTC, datetime

from millie_rec.serving.db import Database
from millie_rec.serving.schemas_should import AbRow, DashboardOut, KpiValue, LatencyBlock

log = logging.getLogger(__name__)

EVENTS_RECENT_N = 50
KPI_KEYS = tuple(
    "qualified_reading_start_rate first_completion_rate_new fallback_rate "
    "p95_latency_ms error_rate active_user_keys".split()
)
MDE_NOTE = "데모 표본으로는 검정하지 않습니다. read-start +1%p 를 검출할 셀당 표본은 실서비스 트래픽으로 산정합니다"  # noqa: E501 — 고정 문장 verbatim(줄을 나누면 글자 대조가 불가능하다)
P95_NOTE, ERROR_NOTE = "서버 실측 참고용", "5xx 없음, cascade 가 항상 200 을 냅니다"

SQL_RECS = "SELECT latency_total_ms, latency_breakdown, fallback_level, model_version, cell, ts FROM recommendations"  # noqa: E501
SQL_USERS = "SELECT user_key, cell, is_new FROM users"
SQL_EV_USERS = "SELECT DISTINCT user_key, event_type FROM events WHERE user_key IS NOT NULL"
SQL_EV_RECENT = "SELECT ts, event_type, user_key, book_id, recommendation_id, model_version, preference_snapshot_id FROM events ORDER BY ts DESC, rowid DESC LIMIT ?"  # noqa: E501
SQL_IMPRESSIONS = (
    "SELECT e.candidate_set_id, e.book_id, e.position, e.selected, "
    "COALESCE(c.survey_variant, 'v1') AS survey_variant FROM events e "
    "LEFT JOIN candidate_sets c ON c.candidate_set_id = e.candidate_set_id "
    "WHERE e.event_type = 'impression' ORDER BY e.ts DESC, e.rowid DESC LIMIT ?"
)
SQL_QUALITY = (
    "SELECT COUNT(quality_flag) AS flagged, MAX(ts) AS last_ts, "
    "COUNT(CASE WHEN event_type = 'impression' THEN 1 END) AS imp, "
    "COUNT(CASE WHEN event_type = 'impression' THEN selected END) AS imp_sel FROM events"
)


def percentile(sorted_ms: Sequence[float], p: float) -> float:
    """정렬 표본의 p 백분위 — bench.percentile 과 같은 규칙(CLI 모듈이라 import 대신 중복 정의)."""
    n = len(sorted_ms)
    if not n:
        return 0.0
    return float(sorted_ms[min(n - 1, max(0, -(-int(p * n) // 100) - 1))])


def _parse(ts: object) -> datetime | None:
    """ISO-8601('…Z' 포함) → aware datetime. 파싱 실패 행은 None 으로 건너뛴다(revision C9)."""
    try:
        dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def _rate(num: int, den: int) -> float:
    """분모 0 이면 0.0 — 빈 DB 도 200(T-05-12-04)."""
    return num / den if den else 0.0


def _ms(rows: Sequence) -> list[float]:
    """정렬된 latency_total_ms(NULL 행 제외) — 백분위 입력."""
    return sorted(float(r["latency_total_ms"]) for r in rows if r["latency_total_ms"] is not None)


def _by_stage(recs: Sequence) -> dict[str, list[float]]:
    """latency_breakdown JSON 의 total 제외 키별 [p50, p95]. 손상 JSON 행은 통째로 건너뛴다."""
    stages: dict[str, list[float]] = defaultdict(list)
    for r in recs:
        with suppress(TypeError, ValueError):
            for key, value in json.loads(r["latency_breakdown"] or "{}").items():
                if key != "total" and isinstance(value, int | float):
                    stages[key].append(float(value))
    return {k: [percentile(sorted(v), 50), percentile(sorted(v), 95)] for k, v in stages.items()}


def _kpi(recs: Sequence, users: Sequence, ev: dict, ms: list[float]) -> dict[str, KpiValue]:
    """§11 KPI 6개 — 전부 n 병기(표본 고지). 분모가 0 이면 value 0.0."""
    opened, qualified = ev.get("reader_open", set()), ev.get("qualified_read", set())
    completed, new = ev.get("completion", set()), {u["user_key"] for u in users if u["is_new"]}
    n_rec, n_user = len(recs), len(users)
    fb = sum(1 for r in recs if (r["fallback_level"] or 0) >= 1)
    qrs = KpiValue(value=_rate(len(qualified & opened), len(opened)), n=len(opened))
    first = KpiValue(value=_rate(len(new & completed), len(new)), n=len(new))
    return {
        "qualified_reading_start_rate": qrs,
        "first_completion_rate_new": first,
        "fallback_rate": KpiValue(value=_rate(fb, n_rec), n=n_rec),
        "p95_latency_ms": KpiValue(value=percentile(ms, 95), n=len(ms), note=P95_NOTE),
        "error_rate": KpiValue(value=0.0, n=n_rec, note=ERROR_NOTE),
        "active_user_keys": KpiValue(value=float(n_user), n=n_user),
    }


def _ab(recs: Sequence, users: Sequence, ev: dict) -> list[AbRow]:
    """셀 × 신규/기존 집계만(D-13 — 검정 없음). p95·fallback 은 그 셀의 recommendations."""
    opened, completed = ev.get("reader_open", set()), ev.get("completion", set())
    cells: dict[tuple[str, str], set[str]] = defaultdict(set)
    for u in users:
        cells[(u["cell"] or "-", "new" if u["is_new"] else "existing")].add(u["user_key"])
    out = []
    for (cell, seg), keys in sorted(cells.items()):
        rows = [r for r in recs if (r["cell"] or "-") == cell]
        cms, done = _ms(rows), _rate(len(keys & completed), len(keys))
        fb = sum(1 for r in rows if (r["fallback_level"] or 0) >= 1)
        perf = {"p95_ms": percentile(cms, 95) if cms else None}
        perf["fallback_rate"] = _rate(fb, len(rows)) if rows else None
        head = {"cell": cell, "segment": seg, "n": len(keys), "completion": done}
        head["primary"] = _rate(len(keys & opened), len(keys))
        out.append(AbRow(first_completion=done if seg == "new" else None, **head, **perf))
    return out


def build_dashboard(db: Database, *, now: Callable[[], datetime] | None = None) -> DashboardOut:
    """recommendations·events 집계 → DashboardOut. 예외도 빈 DB 도 200 이다(T-05-12-04)."""
    now_dt = (now or (lambda: datetime.now(UTC)))()
    iso = now_dt.isoformat(timespec="seconds").replace("+00:00", "Z")
    try:
        recs, users = db.query(SQL_RECS), db.query(SQL_USERS)
        ev: dict[str, set[str]] = defaultdict(set)
        for r in db.query(SQL_EV_USERS):
            ev[r["event_type"]].add(r["user_key"])
        ms = _ms(recs)
        hours = Counter(dt.hour for dt in (_parse(r["ts"]) for r in recs) if dt)
        q = db.query(SQL_QUALITY)[0]
        last = _parse(q["last_ts"]) if q["last_ts"] else None
        fresh = max(0.0, (now_dt - last).total_seconds()) if last else 0.0
        quality = {
            "impression_receipt_rate": _rate(q["imp_sel"], q["imp"]),
            "flagged_events": float(q["flagged"]),
            "feature_freshness_s": round(fresh, 3),
        }
        pct = [percentile(ms, p) for p in (50, 95, 99)]
        latency = LatencyBlock(p50=pct[0], p95=pct[1], p99=pct[2], by_stage=_by_stage(recs))
        lists = {
            "events_recent": [dict(r) for r in db.query(SQL_EV_RECENT, (EVENTS_RECENT_N,))],
            "impressions_log": [dict(r) for r in db.query(SQL_IMPRESSIONS, (EVENTS_RECENT_N,))],
            "by_variant": dict(Counter(r["model_version"] for r in recs if r["model_version"])),
            "by_hour": [{"hour": h, "n": n} for h, n in sorted(hours.items())],
        }
        head = {"generated_at": iso, "kpi": _kpi(recs, users, ev, ms), "mde_note": MDE_NOTE}
        head["ab_table"] = _ab(recs, users, ev)
        return DashboardOut(latency=latency, quality=quality, **head, **lists)
    except Exception:
        log.exception("dashboard aggregation failed; empty payload")
        kpi = {k: KpiValue(value=0.0, n=0) for k in KPI_KEYS}
        zero = LatencyBlock(p50=0.0, p95=0.0, p99=0.0)
        return DashboardOut(generated_at=iso, kpi=kpi, latency=zero, mde_note=MDE_NOTE)
