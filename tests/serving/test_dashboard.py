"""GET /api/dashboard 최소형 — recommendations·events 집계 (백엔드 서빙 01 §11, 05-CONTEXT D-13)."""

import inspect
import json
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from millie_rec.serving import dashboard_agg
from millie_rec.serving.dashboard_agg import ERROR_NOTE, KPI_KEYS, MDE_NOTE, P95_NOTE
from millie_rec.serving.dashboard_api import build_router
from millie_rec.serving.db import Database
from millie_rec.serving.schemas_should import DashboardOut

SQL_USER = "INSERT INTO users(user_key, created_at, consent, cell, is_new) VALUES(?,?,?,?,?)"
SQL_REC = (
    "INSERT INTO recommendations(recommendation_id, user_key, snapshot_id, model_version, cell,"
    " forced, fallback_level, latency_total_ms, latency_breakdown, weights, rows, ts)"
    " VALUES(?,?,?,?,?,?,?,?,?,?,?,?)"
)
SQL_EVENT = (
    "INSERT INTO events(event_id, user_key, book_id, event_type, ts, position, selected,"
    " recommendation_id, model_version, preference_snapshot_id, candidate_set_id, quality_flag)"
    " VALUES(?,?,?,?,?,?,?,?,?,?,?,?)"
)
SQL_CAND = (
    "INSERT INTO candidate_sets(candidate_set_id, user_key, ts, book_ids, survey_variant)"
    " VALUES(?,?,?,?,?)"
)

# 손계산용 6행 — ms 정렬 [10..60], fallback level ≥1 이 2건, 시각은 21시 4건 · 22시 2건
RECS = (
    (10.0, 0, "hybrid_v1", "A", "2026-09-05T21:00:00Z"),
    (20.0, 0, "hybrid_v1", "A", "2026-09-05T21:01:00Z"),
    (30.0, 0, "hybrid_v1", "B", "2026-09-05T21:02:00Z"),
    (40.0, 1, "hybrid_div_v1", "B", "2026-09-05T21:03:00Z"),
    (50.0, 0, "hybrid_div_v1", "A", "2026-09-05T22:00:00Z"),
    (60.0, 3, "fallback_v1", None, "2026-09-05T22:01:00Z"),
)
EVENTS = (
    ("e01", "u1", "reader_open", "20:00", None, None, None, None),
    ("e02", "u2", "reader_open", "20:01", None, None, None, None),
    ("e03", "u3", "reader_open", "20:02", None, None, None, None),
    ("e04", "u1", "qualified_read", "20:03", None, None, None, None),
    ("e05", "u1", "completion", "20:04", None, None, None, None),
    ("e06", "u1", "impression", "20:05", 0, 1, "cand_1", None),
    ("e07", "u1", "impression", "20:06", 1, None, "cand_1", None),
    ("e08", "u2", "impression", "20:07", 2, None, "cand_1", None),
    ("e09", "u2", "impression", "20:08", 3, 1, "cand_1", None),
    ("e10", "u1", "preference_book_selected", "20:09", None, None, None, None),
    ("e11", "u2", "preference_book_selected", "20:10", None, None, None, "ts_future"),
)
EVENT_KEYS = {
    "ts",
    "event_type",
    "user_key",
    "book_id",
    "recommendation_id",
    "model_version",
    "preference_snapshot_id",
}


def _event(db: Database, eid, user, etype, hhmm, position, selected, cand, flag) -> None:
    db.execute(
        SQL_EVENT,
        (
            eid,
            user,
            1,
            etype,
            f"2026-09-05T{hhmm}:00Z",
            position,
            selected,
            "rec_1",
            "hybrid_v1",
            "snap_1",
            cand,
            flag,
        ),
    )


def _rec(db: Database, i, ms, level, mv, cell, ts, *, breakdown=None) -> None:
    bd = json.dumps({"feature": float(i + 1), "pipeline": ms - 2.0, "compose": 1.0, "total": ms})
    db.execute(
        SQL_REC,
        (
            f"rec_{i}",
            "u1",
            "snap_1",
            mv,
            cell,
            0,
            level,
            ms,
            bd if breakdown is None else breakdown,
            "{}",
            "[]",
            ts,
        ),
    )


def _seeded(tmp_path: Path, name: str = "d") -> Database:
    """users 3 · recommendations 6 · events 11 · candidate_sets 1 을 직접 INSERT 한다."""
    db = Database(tmp_path / f"{name}.db")
    db.apply_schema()
    for user_key, cell, is_new in (("u1", "A", 1), ("u2", "B", 1), ("u3", "A", 0)):
        db.execute(SQL_USER, (user_key, "2026-09-05T19:00:00Z", 1, cell, is_new))
    for i, row in enumerate(RECS):
        _rec(db, i, *row)
    for row in EVENTS:
        _event(db, *row)
    db.execute(SQL_CAND, ("cand_1", "u1", "2026-09-05T20:00:00Z", "[1,2]", "v2"))
    return db


def _client(db: Database, tmp_path: Path) -> TestClient:
    app = FastAPI()
    app.include_router(
        build_router(
            db=db, eval_table_path=tmp_path / "none.json", latency_path=tmp_path / "none2.json"
        )
    )
    return TestClient(app)


def _get(db: Database, tmp_path: Path) -> DashboardOut:
    r = _client(db, tmp_path).get("/api/dashboard")
    assert r.status_code == 200, r.text
    assert "Traceback" not in r.text
    return DashboardOut.model_validate(r.json())


def _kpi(out: DashboardOut, key: str):
    assert key in out.kpi, f"kpi 에 {key} 가 없다: {sorted(out.kpi)}"
    return out.kpi[key]


# ── 계약 ────────────────────────────────────────────────────────────────────
def test_dashboard_parses_kpi_six_keys_all_with_n_and_note(tmp_path: Path):
    out = _get(_seeded(tmp_path), tmp_path)
    assert set(out.kpi) == set(KPI_KEYS)
    assert all(out.kpi[k].n is not None for k in KPI_KEYS)
    assert _kpi(out, "p95_latency_ms").note == P95_NOTE == "서버 실측 참고용"
    assert out.window == "all"
    assert out.generated_at.startswith("20") and "T" in out.generated_at


# ── 정확성 ──────────────────────────────────────────────────────────────────
def test_latency_percentiles_and_by_stage_hand_computed(tmp_path: Path):
    out = _get(_seeded(tmp_path), tmp_path)
    assert out.latency.p50 == 30.0  # 정렬 [10..60], ceil(0.5*6)-1 = 2
    assert out.latency.p95 == 60.0 and out.latency.p99 == 60.0
    assert set(out.latency.by_stage) >= {"feature", "pipeline", "compose"}
    assert "total" not in out.latency.by_stage
    assert all(len(v) == 2 for v in out.latency.by_stage.values())
    assert out.latency.by_stage["feature"] == [3.0, 6.0]  # [1..6] 의 p50·p95
    assert out.latency.by_stage["compose"] == [1.0, 1.0]


def test_kpi_rates_hand_computed(tmp_path: Path):
    out = _get(_seeded(tmp_path), tmp_path)
    fallback = _kpi(out, "fallback_rate")
    assert fallback.value == pytest.approx(2 / 6) and fallback.n == 6
    assert _kpi(out, "error_rate").model_dump() == {"value": 0.0, "n": 6, "note": ERROR_NOTE}
    assert (_kpi(out, "active_user_keys").value, _kpi(out, "active_user_keys").n) == (3.0, 3)
    qrs = _kpi(out, "qualified_reading_start_rate")
    assert qrs.value == pytest.approx(1 / 3) and qrs.n == 3
    first = _kpi(out, "first_completion_rate_new")
    assert first.value == pytest.approx(1 / 2) and first.n == 2
    p95 = _kpi(out, "p95_latency_ms")
    assert p95.value == 60.0 and p95.n == 6


def test_quality_block_three_keys(tmp_path: Path):
    out = _get(_seeded(tmp_path), tmp_path)
    assert set(out.quality) == {
        "impression_receipt_rate",
        "flagged_events",
        "feature_freshness_s",
    }
    assert out.quality["impression_receipt_rate"] == 0.5  # impression 4 중 selected 2
    assert out.quality["flagged_events"] == 1.0
    assert out.quality["feature_freshness_s"] >= 0.0


def test_events_recent_capped_50_latest_first_keys(tmp_path: Path):
    db = _seeded(tmp_path)
    out = _get(db, tmp_path)
    assert len(out.events_recent) == len(EVENTS)
    assert set(out.events_recent[0]) >= EVENT_KEYS
    assert out.events_recent[0]["ts"] == "2026-09-05T20:10:00Z"  # 최신순
    for i in range(60):
        _event(db, f"x{i:02d}", "u1", "reader_open", "23:59", None, None, None, None)
    assert len(_get(db, tmp_path).events_recent) == 50


def test_impressions_log_joined_with_survey_variant(tmp_path: Path):
    db = _seeded(tmp_path)
    _event(db, "e12", "u3", "impression", "20:11", 0, None, "cand_missing", None)
    out = _get(db, tmp_path)
    assert len(out.impressions_log) == 5
    keys = {"candidate_set_id", "book_id", "position", "selected", "survey_variant"}
    assert all(set(row) == keys for row in out.impressions_log)
    joined = {row["candidate_set_id"]: row["survey_variant"] for row in out.impressions_log}
    assert joined == {"cand_1": "v2", "cand_missing": "v1"}  # 없으면 COALESCE 기본 v1


def test_by_variant_and_by_hour(tmp_path: Path):
    db = _seeded(tmp_path)
    out = _get(db, tmp_path)
    assert out.by_variant == {"hybrid_v1": 3, "hybrid_div_v1": 2, "fallback_v1": 1}
    assert out.by_hour == [{"hour": 21, "n": 4}, {"hour": 22, "n": 2}]
    _rec(db, 99, 15.0, 0, "hybrid_v1", "A", "bad")  # revision C9 — 파싱 실패 행은 건너뛴다
    after = _get(db, tmp_path)
    assert sum(row["n"] for row in after.by_hour) == 6


def test_ab_table_cells_by_segment_and_mde_note(tmp_path: Path):
    out = _get(_seeded(tmp_path), tmp_path)
    assert out.mde_note == MDE_NOTE
    rows = {(row.cell, row.segment): row for row in out.ab_table}
    assert set(rows) == {("A", "new"), ("A", "existing"), ("B", "new")}
    assert all(row.n == 1 for row in rows.values())
    assert rows[("A", "new")].completion == 1.0 and rows[("A", "new")].first_completion == 1.0
    assert rows[("A", "existing")].completion == 0.0
    assert rows[("A", "existing")].first_completion is None
    assert rows[("A", "new")].primary == 1.0  # u1 reader_open
    assert rows[("A", "new")].p95_ms == 50.0  # cell A = [10, 20, 50]
    assert rows[("B", "new")].p95_ms == 40.0 and rows[("B", "new")].fallback_rate == 0.5
    assert rows[("A", "new")].fallback_rate == 0.0


# ── 안전성 ──────────────────────────────────────────────────────────────────
def test_empty_db_is_200_zero_values(tmp_path: Path):
    db = Database(tmp_path / "empty.db")
    db.apply_schema()
    out = _get(db, tmp_path)
    assert set(out.kpi) == set(KPI_KEYS)
    assert all(out.kpi[k].value == 0.0 for k in KPI_KEYS)
    assert (out.latency.p50, out.latency.p95, out.latency.p99) == (0.0, 0.0, 0.0)
    assert out.latency.by_stage == {}
    assert out.events_recent == [] and out.impressions_log == [] and out.ab_table == []
    assert out.by_variant == {} and out.by_hour == []


def test_corrupt_breakdown_skipped_and_no_file_or_query_access_grep(tmp_path: Path):
    db = _seeded(tmp_path)
    _rec(db, 98, 70.0, 0, "hybrid_v1", "A", "2026-09-05T22:02:00Z", breakdown="{bad")
    out = _get(db, tmp_path)
    assert "feature" in out.latency.by_stage, "손상 행이 by_stage 를 없애면 안 된다"
    assert out.latency.by_stage["feature"] == [3.0, 6.0]  # 손상 행이 계산에 끼지 않는다
    assert out.latency.p95 == 70.0
    routes = build_router(db=db).routes
    endpoints = [r for r in routes if getattr(r, "path", "") == "/api/dashboard"]
    assert len(endpoints) == 1
    src = inspect.getsource(endpoints[0].endpoint)
    assert all(token not in src for token in ("Query(", "request.", "open(", "Path("))
    agg = Path(dashboard_agg.__file__).read_text(encoding="utf-8")
    assert "open(" not in agg and "Path(" not in agg and "execute(f" not in agg
