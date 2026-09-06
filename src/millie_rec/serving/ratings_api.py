"""POST /api/ratings(Should, 백엔드 서빙 01 §7) — ratings INSERT + rating 이벤트 자동 기록."""

# 아키 §9-3 파일 목록 외 신설(Advisor 확정 17 B5 — demo_api.py 가 150줄), PROGRESS 1줄은 Advisor.
# 별점은 모델 라벨로 쓰지 않는다(05-CONTEXT D-13 · 결정 '1탭 별점 UI를 "설계만" → "데모 축소판"'
# (../.assets/개발일지/ 2026-09-04 파일 항목 D22)).

import json
import re
import uuid
from collections.abc import Callable
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException

from millie_rec.serving.db import Database
from millie_rec.serving.schemas import RatingIn, RatingOut

SURFACE_READER = "reader"  # events.surface — 뷰어 시뮬레이션 화면(#/reader/:id, 화면 구성 02 §2)
EVENT_RATING = "rating"  # contracts.EVENT_TYPES 안
USER_KEY_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")  # demo_api.py 와 중복 정의(C5)
USER_KEY_MSG = "user_key must match ^[A-Za-z0-9_-]{1,64}$"
SQL_RATING_INS = (
    "INSERT OR IGNORE INTO ratings(rating_id, user_key, book_id, stars, ts, recommendation_id)"
    " VALUES(?,?,?,?,?,?)"
)
SQL_EVENT_INS = (  # demo_api.py 와 중복 정의 — 파일 독립(demo_api 무변경 원칙, B5)
    "INSERT OR IGNORE INTO events(event_id, user_key, book_id, event_type, ts, surface, row_id,"
    " position, selected, recommendation_id, model_version, preference_snapshot_id,"
    " candidate_set_id, payload, quality_flag) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"
)


def _422(param: str, msg: str) -> HTTPException:
    return HTTPException(422, detail=[{"loc": ["body", param], "msg": msg, "type": "value_error"}])


def _parse(ts: str) -> datetime:
    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def _iso(dt: datetime) -> str:
    return dt.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def build_router(
    *,
    db: Database,
    wake: Callable[[], None] | None = None,
    invalidate: Callable[[str], object] | None = None,
    now: Callable[[], datetime] | None = None,
) -> APIRouter:
    """의존을 클로저로 받는다(demo_api.build_router 관례). 배선은 api.py create_app."""
    router = APIRouter(prefix="/api")

    @router.post("/ratings", response_model=RatingOut, status_code=201)
    def ratings(body: RatingIn) -> RatingOut:  # 동기 def — 스레드풀(serving.md 이벤트 루프 규칙)
        if not USER_KEY_RE.match(body.user_key):
            raise _422("user_key", USER_KEY_MSG)
        try:
            ts_z = _iso(_parse(body.ts))
        except ValueError as exc:
            raise _422("ts", "ts must be ISO-8601") from exc
        rating = (body.rating_id, body.user_key, body.book_id, body.stars, ts_z,
                  body.recommendation_id)  # fmt: skip
        event = (uuid.uuid4().hex, body.user_key, body.book_id, EVENT_RATING, ts_z, SURFACE_READER,
                 None, None, None, body.recommendation_id, None, None, None,
                 json.dumps({"stars": str(body.stars)}), None)  # fmt: skip
        con = db.connect()
        with con:  # 확정 16: with con 으로 커밋. 두 INSERT 는 같은 트랜잭션
            inserted = con.execute(SQL_RATING_INS, rating).rowcount
            if inserted:  # 재전송(rating_id 중복)이면 이벤트도 늘리지 않는다
                con.execute(SQL_EVENT_INS, event)
        if inserted and wake:  # 확정 13: wake 는 create_app 이 준 스레드세이프 클로저
            wake()
        if inserted and invalidate:  # 별점 뒤 캐시 무효화 — 완독 시와 같은 취지(D-10)
            invalidate(body.user_key)
        return RatingOut(rating_id=body.rating_id)

    return router
