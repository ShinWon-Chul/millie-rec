"""ratings_api.py — 계약(201 RatingOut) · 정확성(rating 이벤트 자동·멱등) · 안전성(422·라벨 미사용).

Phase 5 '서빙 Must 완성'(.planning/ROADMAP.md) Plan 05-11.
05-CONTEXT D-13(Should 범위 — ratings INSERT + rating 이벤트 자동 기록, 모델 라벨 미사용) · SERV-12.
백엔드 서빙 01 §7 = 응답 201 {"ok": true, "rating_id": "rat_1c9d"}.
가짜는 파일마다 복제한다(tests/serving/test_demo_api.py 관례).
"""

import inspect
import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from millie_rec.contracts import DB_FILENAME, FALLBACK_GLOBAL_POP
from millie_rec.serving import ratings_api
from millie_rec.serving.api import create_app
from millie_rec.serving.db import Database
from millie_rec.serving.fallback import GlobalPopularFallback
from millie_rec.serving.ratings_api import build_router
from millie_rec.serving.schemas import RatingOut, RecommendOut

USER = "u-1"
TS_IN, TS_Z = "2026-09-07T12:00:00+00:00", "2026-09-07T12:00:00Z"
RATING = {
    "rating_id": "rat_1c9d00",
    "user_key": USER,
    "book_id": 3,
    "stars": 5,
    "ts": TS_IN,
    "recommendation_id": "rec_8f3a2c",
}


class _Spy:
    """호출 인자를 모으는 가짜 콜백. wake 는 인자 없음, invalidate 는 user_key 1개."""

    def __init__(self) -> None:
        self.calls: list = []

    def __call__(self, *args):
        self.calls.append(args[0] if args else None)


def _build(tmp_path: Path, **kw) -> tuple[Database, TestClient]:
    db = Database(tmp_path / DB_FILENAME)
    db.apply_schema()
    app = FastAPI()
    app.include_router(build_router(db=db, **kw))
    return db, TestClient(app)


def _count(db: Database, table: str) -> int:
    return db.query(f"SELECT COUNT(*) AS n FROM {table}")[0]["n"]  # 테이블 이름은 리터럴만


# ── 계약 ────────────────────────────────────────────────────────────────
def test_rating_201_persists_and_records_rating_event_with_payload_and_z_ts(tmp_path: Path):
    db, client = _build(tmp_path)
    r = client.post("/api/ratings", json=RATING)
    assert r.status_code == 201, r.text
    out = RatingOut.model_validate(r.json())
    assert out.ok is True and out.rating_id == "rat_1c9d00"
    rows = db.query("SELECT * FROM ratings")
    assert len(rows) == 1
    assert rows[0]["rating_id"] == "rat_1c9d00" and rows[0]["user_key"] == USER
    assert rows[0]["book_id"] == 3 and rows[0]["stars"] == 5
    assert rows[0]["ts"] == TS_Z and rows[0]["recommendation_id"] == "rec_8f3a2c"
    evs = db.query("SELECT * FROM events")
    assert len(evs) == 1
    assert evs[0]["event_type"] == "rating" and evs[0]["user_key"] == USER
    assert evs[0]["book_id"] == 3 and evs[0]["surface"] == "reader"
    assert evs[0]["recommendation_id"] == "rec_8f3a2c" and evs[0]["ts"] == TS_Z
    assert json.loads(evs[0]["payload"]) == {"stars": "5"}
    assert len(evs[0]["event_id"]) == 32 and int(evs[0]["event_id"], 16) >= 0


# ── 정확성 ──────────────────────────────────────────────────────────────
def test_rating_idempotent_on_duplicate_rating_id(tmp_path: Path):
    db, client = _build(tmp_path)
    assert client.post("/api/ratings", json=RATING).status_code == 201
    r2 = client.post("/api/ratings", json=dict(RATING, stars=1))
    assert r2.status_code == 201, r2.text
    assert r2.json()["ok"] is True and r2.json()["rating_id"] == "rat_1c9d00"
    assert _count(db, "ratings") == 1 and _count(db, "events") == 1
    assert db.query("SELECT stars FROM ratings")[0]["stars"] == 5  # 첫 값 유지


def test_rating_calls_wake_and_invalidate_once_only_when_inserted(tmp_path: Path):
    wake, inv = _Spy(), _Spy()
    db, client = _build(tmp_path, wake=wake, invalidate=inv)
    assert client.post("/api/ratings", json=RATING).status_code == 201
    assert len(wake.calls) == 1 and inv.calls == [USER]
    assert client.post("/api/ratings", json=RATING).status_code == 201  # 중복
    assert len(wake.calls) == 1 and inv.calls == [USER]


def test_rating_after_consent_withdrawal_403_stores_nothing_no_wake(tmp_path: Path):
    """Codex C3 — 철회(consent=0) 뒤 별점이 ratings·events 를 다시 만들면 삭제 응답이 거짓이다."""
    wake, inv = _Spy(), _Spy()
    db, client = _build(tmp_path, wake=wake, invalidate=inv)
    con = db.connect()
    with con:
        con.execute(
            "INSERT INTO users(user_key, created_at, consent, cell, is_new) VALUES(?,?,0,'A',0)",
            (USER, TS_Z),
        )
    r = client.post("/api/ratings", json=RATING)
    assert r.status_code == 403, r.text
    assert _count(db, "ratings") == 0 and _count(db, "events") == 0
    assert wake.calls == [] and inv.calls == []
    # users 행이 없는 익명 키는 events_gate T2 와 같이 막지 않는다
    assert client.post("/api/ratings", json=dict(RATING, user_key="u-anon")).status_code == 201


def test_rating_without_recommendation_id_is_null(tmp_path: Path):
    db, client = _build(tmp_path)
    body = {k: v for k, v in RATING.items() if k != "recommendation_id"}
    assert client.post("/api/ratings", json=body).status_code == 201
    assert _count(db, "ratings") == 1 and _count(db, "events") == 1
    assert db.query("SELECT recommendation_id FROM ratings")[0][0] is None
    assert db.query("SELECT recommendation_id FROM events")[0][0] is None


# ── 안전성 ──────────────────────────────────────────────────────────────
def test_rating_stars_out_of_range_extra_field_user_key_bad_ts_422(tmp_path: Path):
    db, client = _build(tmp_path)
    bads = (
        {"stars": 0},
        {"stars": 6},
        {"stars": "a"},
        {"extra": 1},
        {"user_key": "a';b"},
        {"ts": "bad"},
    )
    for bad in bads:
        r = client.post("/api/ratings", json=dict(RATING, **bad))
        assert r.status_code == 422, (bad, r.status_code, r.text)
    assert _count(db, "ratings") == 0 and _count(db, "events") == 0


def test_rating_source_has_no_model_label_usage_and_no_fstring_sql():
    src = inspect.getsource(ratings_api)
    for banned in ("blend", "state_weights", "score", "execute(f"):
        assert banned not in src, banned
    assert "INSERT OR IGNORE INTO ratings" in src


def test_no_traceback(tmp_path: Path):
    _, client = _build(tmp_path)
    for body in (RATING, dict(RATING, ts="bad"), dict(RATING, user_key="a';b"), {}):
        assert "Traceback" not in client.post("/api/ratings", json=body).text


# ── 통합(api.py include 1줄) ────────────────────────────────────────────
def test_create_app_includes_ratings_route_and_recommend_unchanged(tmp_path: Path):
    app = create_app(
        pipelines={}, fallback=GlobalPopularFallback(None), db=Database(tmp_path / DB_FILENAME)
    )
    with TestClient(app) as c:  # with 블록이어야 lifespan(스키마 적용)이 돈다
        r = c.post("/api/ratings", json=RATING)
        rec = c.get("/api/recommend", params={"seeds": "1,2,3", "k": 5})
    assert r.status_code == 201, r.text
    assert r.json() == {"ok": True, "rating_id": "rat_1c9d00"}
    assert rec.status_code == 200
    assert RecommendOut.model_validate(rec.json()).fallback_level == FALLBACK_GLOBAL_POP
