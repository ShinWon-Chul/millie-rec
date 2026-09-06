"""추천 로그(D-12)·rows 축약·breakdown 병합 — 아키 §9-3 목록 외 신설(Advisor 확정 17 B3).

cascade.py 를 150줄 안에 두기 위해 로그 SQL·JSON 축약만 여기로 뺐다.
"""

import json
import logging
import time
from collections.abc import Callable, Sequence
from datetime import UTC, datetime

from millie_rec.contracts import RecommendResponse, Row
from millie_rec.serving.db import Database

log = logging.getLogger(__name__)

SQL_REC_INS = (
    "INSERT INTO recommendations(recommendation_id, user_key, snapshot_id, model_version, "
    "cell, forced, fallback_level, latency_total_ms, latency_breakdown, weights, rows, ts) "
    "VALUES(?,?,?,?,?,?,?,?,?,?,?,?)"
)
SUB_KEYS = ("retrieval", "ranking", "rerank")  # D-09 파이프라인 세분 구간


def _iso(now: Callable[[], float] | None = None) -> str:
    """epoch → ISO-8601 UTC 'Z'. events.ts 와 같은 형식이라 문자열 비교가 성립한다."""
    epoch = (now or time.time)()
    return datetime.fromtimestamp(epoch, UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def abbreviate_rows(rows: Sequence[Row]) -> list[dict]:
    """D-12: 노출 로그 4필드의 단일 소스 — row_id·book_id·position 3키만 남긴다."""
    return [
        {"row_id": row.row_id, "book_id": i.book_id, "position": i.position}
        for row in rows
        for i in row.items
    ]


def merge_breakdown(bd: dict[str, float], sub: object) -> dict[str, float]:
    """C2: pipeline 키는 유지하고 retrieval·ranking·rerank 를 더한다(demo 키 고정 안전)."""
    out = dict(bd)
    if isinstance(sub, dict):
        out.update({k: float(v) for k, v in sub.items() if k in SUB_KEYS})
    return out


def log_recommendation(
    db: Database,
    resp: RecommendResponse,
    *,
    user_key: str | None,
    snapshot_id: str | None,
    cell: str | None,
    forced: bool,
    now: Callable[[], float] | None = None,
) -> None:
    """응답 직전 1행 INSERT(D-12). 로그 실패가 추천을 막지 않는다(T-05-06-07)."""
    try:
        db.execute(
            SQL_REC_INS,
            (
                resp.recommendation_id,
                user_key,
                snapshot_id,
                resp.model_version,
                cell,
                int(forced),
                resp.fallback_level,
                resp.latency_ms,
                json.dumps(resp.latency_breakdown),
                json.dumps(resp.user_state_weights),
                json.dumps(abbreviate_rows(resp.rows), ensure_ascii=False),
                _iso(now),
            ),
        )
    except Exception:
        log.exception("recommendation log failed; response unaffected")
