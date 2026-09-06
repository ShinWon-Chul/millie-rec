"""열람·삭제·철회 API — 계약(state·data) · 정확성(DELETE 4테이블·멱등) · 안전성(404·422·인젭션).

Phase 5 '서빙 Must 완성'(.planning/ROADMAP.md) plan 05-05, SERV-07.
백엔드 서빙 01 §8·§9·§10 · 05-CONTEXT D-08(메모리 상태·캐시도 함께 제거).
가짜는 파일마다 복제한다(테스트 간 import 금지 관례, tests/serving/test_api_weights.py).
"""

import json
import sqlite3
import uuid
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from millie_rec.contracts import UserState
from millie_rec.serving.db import Database
from millie_rec.serving.privacy_api import build_router
from millie_rec.serving.schemas import PersonalizationDeleted, UserDataOut, UserStateOut

FIXED_NOW = datetime(2026, 9, 6, 12, 0, 0, tzinfo=UTC)
SRC_PATH = Path(__file__).resolve().parents[2] / "src" / "millie_rec" / "serving" / "privacy_api.py"
ZERO_WEIGHTS = {"alpha": 0.0, "beta": 0.0, "gamma": 0.0}
COUNT_TABLES = ("preference_snapshots", "events", "ratings", "recommendations")
# Codex F2(2026-09-06): candidate_sets 가 DELETE 대상에 들어가 응답 키가 5개다
DELETED_5 = ("snapshots", "events", "ratings", "recommendations", "candidate_sets")
SEEDED_DELETED = dict(zip(DELETED_5, (2, 7, 1, 2, 0), strict=True))  # _seed_user 만 넣은 경우
EMPTY_DELETED = dict.fromkeys(DELETED_5, 0)


def _iso(dt: datetime) -> str:
    return dt.isoformat(timespec="seconds")


def _ago(minutes: int) -> str:
    return _iso(FIXED_NOW - timedelta(minutes=minutes))


class _Cat:
    """meta 만 쓰는 가짜 Catalog — 제목·표지 조인 단정용."""

    def meta(self, book_ids: Sequence[int]) -> list[dict]:
        return [
            {
                "book_id": b,
                "title": f"책{b}",
                "authors": f"저자{b}",
                "image_url": f"https://img.millie.co.kr/{b}.jpg",
            }
            for b in book_ids
        ]

    def popular(self, categories: Sequence[str] = (), n: int = 50) -> list[int]:
        return []

    def eligible(self, book_ids: Sequence[int]) -> list[int]:
        return list(book_ids)


class _Spy:
    """state.forget · invalidate 호출 기록 + user_state 주입(state 우선 경로 단정용)."""

    def __init__(self, history: tuple[int, ...] = ()) -> None:
        self.calls: list[tuple[str, str]] = []
        self._history = history

    def user_state(self, user_key: str, *, seeds=(), categories=()) -> UserState:
        return UserState(user_id=None, explicit_seeds=tuple(seeds), history=self._history)

    def forget(self, user_key: str) -> None:
        self.calls.append(("forget", user_key))

    def invalidate(self, user_key: str) -> None:
        self.calls.append(("invalidate", user_key))


def _weights_spy(captured: list[UserState]):
    def weights(user: UserState) -> dict[str, float]:
        captured.append(user)
        return {
            "alpha": 1.0 if user.explicit_seeds else 0.0,
            "beta": 1.0 if user.history else 0.0,
            "gamma": 0.0,
        }

    return weights


def _seed_user(db: Database, key: str, tag: str = "") -> None:
    """users 1 · 스냅샷 2 · events 7 · ratings 1 · recommendations 2. ts 를 못박아 순서 고정."""
    con = db.connect()
    events = [
        (f"ev1{tag}", key, 1, "library_add", _ago(50)),
        (f"ev2{tag}", key, 2, "library_add", _ago(45)),
        (f"ev3{tag}", key, 3, "library_add", _ago(40)),
        (f"ev4{tag}", key, 2, "reader_open", _ago(30)),
        (f"ev5{tag}", key, 3, "completion", _ago(20)),
        (f"ev6{tag}", key, 8, "reader_open", _ago(10)),
        (f"ev7{tag}", key, 9, "detail_click", _ago(5)),
    ]
    with con:
        con.execute(
            "INSERT INTO users (user_key, created_at, consent, cell, is_new)"
            " VALUES (?, ?, 1, ?, 1)",
            (key, _ago(180), "B"),
        )
        con.executemany(
            "INSERT INTO preference_snapshots (snapshot_id, user_key, created_at, reading_time,"
            " categories, criterion, subcategories, seeds, persona) VALUES (?,?,?,?,?,?,?,?,?)",
            [
                (
                    f"snap_aaaaaa{tag}",
                    key,
                    _ago(120),
                    "저녁",
                    json.dumps(["IT", "소설"], ensure_ascii=False),
                    "bestseller",
                    "[]",
                    json.dumps([1, 2, 3, 4, 5]),
                    "{}",
                ),
                (
                    f"snap_bbbbbb{tag}",
                    key,
                    _ago(60),
                    "아침",
                    json.dumps(["인문"], ensure_ascii=False),
                    "review",
                    "[]",
                    json.dumps([6, 7]),
                    "{}",
                ),
            ],
        )
        con.executemany(
            "INSERT INTO events (event_id, user_key, book_id, event_type, ts, payload,"
            " quality_flag) VALUES (?,?,?,?,?,?,?)",
            [(*e, json.dumps({"surface": "home"}), None) for e in events],
        )
        con.execute(
            "INSERT INTO ratings (rating_id, user_key, book_id, stars, ts) VALUES (?,?,?,?,?)",
            (f"rat_aaa{tag}", key, 3, 5, _ago(15)),
        )
        con.executemany(
            "INSERT INTO recommendations (recommendation_id, user_key, snapshot_id, model_version,"
            " cell, forced, fallback_level, latency_total_ms, latency_breakdown, weights, rows, ts)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            [
                (
                    f"rec_aaa{tag}",
                    key,
                    f"snap_bbbbbb{tag}",
                    "hybrid_div_v1",
                    "B",
                    0,
                    0,
                    12.5,
                    json.dumps({"total": 12.5}),
                    json.dumps(ZERO_WEIGHTS),
                    json.dumps([{"row_id": "trending", "book_id": 1, "position": 0}]),
                    _ago(9),
                ),
                (
                    f"rec_bbb{tag}",
                    key,
                    f"snap_bbbbbb{tag}",
                    "global_pop_v1",
                    "B",
                    0,
                    3,
                    5.0,
                    json.dumps({"total": 5.0}),
                    json.dumps(ZERO_WEIGHTS),
                    json.dumps([]),
                    _ago(4),
                ),
            ],
        )


def _app_client(db: Database, **kw) -> TestClient:
    app = FastAPI()
    app.include_router(build_router(db=db, now=lambda: FIXED_NOW, **kw))
    return TestClient(app)


def _client(tmp_path: Path, name: str = "t.db", **kw) -> tuple[Database, TestClient]:
    db = Database(tmp_path / name)
    db.apply_schema()
    return db, _app_client(db, **kw)


def _counts(db: Database, key: str) -> dict[str, int]:
    con = sqlite3.connect(db.path)
    try:
        return {
            t: con.execute(f"SELECT COUNT(*) FROM {t} WHERE user_key = ?", (key,)).fetchone()[0]
            for t in COUNT_TABLES
        }
    finally:
        con.close()


def _consent(db: Database, key: str) -> int | None:
    con = sqlite3.connect(db.path)
    try:
        row = con.execute("SELECT consent FROM users WHERE user_key = ?", (key,)).fetchone()
    finally:
        con.close()
    return None if row is None else row[0]


# ── 계약 ────────────────────────────────────────────────────────────────
def test_state_parses_and_library_three_buckets_with_meta(tmp_path: Path) -> None:
    db, client = _client(tmp_path, catalog=_Cat(), weights=_weights_spy([]))
    _seed_user(db, "u-1")
    r = client.get("/api/users/u-1/state")
    assert r.status_code == 200
    out = UserStateOut.model_validate(r.json())
    assert out.consent is True
    assert out.cell == "B"
    assert out.is_new is True
    assert set(out.library) == {"added", "reading", "completed"}
    assert {b.book_id for b in out.library["added"]} == {1, 2, 3}
    assert [b.book_id for b in out.library["completed"]] == [3]
    assert [b.book_id for b in out.library["reading"]] == [8, 2]
    added = out.library["added"][0]
    assert added.title == f"책{added.book_id}"
    assert added.image_url == f"https://img.millie.co.kr/{added.book_id}.jpg"
    assert out.nearline_lag_s is None


def test_state_library_books_carry_authors_and_none_without_catalog(tmp_path: Path) -> None:
    """LibraryBook.authors — 카탈로그 저자를 그대로 싣고, 카탈로그가 없으면 None (06-UAT Gap 1)."""
    db, client = _client(tmp_path, catalog=_Cat())
    _seed_user(db, "u-1")
    payload = client.get("/api/users/u-1/state").json()
    added = payload["library"]["added"]
    assert added, "added 버킷이 비어 있으면 저자 단정이 무의미하다"
    assert [b.get("authors") for b in added] == [f"저자{b['book_id']}" for b in added]
    out = UserStateOut.model_validate(payload)  # _Strict — 여분 키가 있으면 여기서 걸린다
    lib = out.library["added"]
    assert [b.authors for b in lib] == [f"저자{b.book_id}" for b in lib]

    db2, client2 = _client(tmp_path, name="no_catalog.db")  # 카탈로그 미주입 → 조인 없음
    _seed_user(db2, "u-1")
    bare = UserStateOut.model_validate(client2.get("/api/users/u-1/state").json())
    assert all(b.authors is None for b in bare.library["added"])


def test_state_snapshots_desc_with_active_latest_and_weights_from_latest_seeds_history(
    tmp_path: Path,
) -> None:
    captured: list[UserState] = []
    db, client = _client(tmp_path, catalog=_Cat(), weights=_weights_spy(captured))
    _seed_user(db, "u-1")
    out = UserStateOut.model_validate(client.get("/api/users/u-1/state").json())
    assert len(out.snapshots) == 2
    assert out.snapshots[0].snapshot_id == "snap_bbbbbb"
    assert out.snapshots[0].active is True
    assert out.snapshots[0].categories == ["인문"]
    assert out.snapshots[1].active is False
    assert out.snapshots[1].criterion == "bestseller"
    assert out.user_state_weights == {"alpha": 1.0, "beta": 1.0, "gamma": 0.0}
    assert len(captured) == 1
    assert captured[0].explicit_seeds == (6, 7)
    assert captured[0].history == (8, 3, 2)  # reader_open·completion distinct 최근순 (D-05)

    # state 주입 시 SQL 이 아니라 state.user_state 결과가 weights 로 간다(revision C6)
    captured_state: list[UserState] = []
    client2 = _app_client(db, state=_Spy(history=(99,)), weights=_weights_spy(captured_state))
    UserStateOut.model_validate(client2.get("/api/users/u-1/state").json())
    assert len(captured_state) == 1
    assert captured_state[0].history == (99,)


def test_state_without_weights_or_catalog_degrades_gracefully(tmp_path: Path) -> None:
    db, client = _client(tmp_path)
    _seed_user(db, "u-1")
    r = client.get("/api/users/u-1/state")
    assert r.status_code == 200
    out = UserStateOut.model_validate(r.json())
    assert out.user_state_weights == ZERO_WEIGHTS
    assert len(out.library["added"]) == 3
    assert all(b.title is None and b.image_url is None for b in out.library["added"])


def test_data_export_returns_all_tables_with_json_columns_decoded_and_note(tmp_path: Path) -> None:
    db, client = _client(tmp_path, catalog=_Cat())
    _seed_user(db, "u-1")
    r = client.get("/api/users/u-1/data")
    assert r.status_code == 200
    out = UserDataOut.model_validate(r.json())
    assert len(out.snapshots) == 2
    assert out.snapshots[0]["categories"] == ["인문"]  # JSON 컬럼은 문자열이 아니라 풀린 값
    assert out.user.get("user_key") == "u-1"
    assert out.user.get("cell") == "B"
    assert len(out.events) == 7
    assert {
        "event_id",
        "user_key",
        "book_id",
        "event_type",
        "ts",
        "quality_flag",
        "payload",
    } <= set(out.events[0])
    assert isinstance(out.events[0]["payload"], dict)
    assert len(out.ratings) == 1
    assert len(out.recommendations) == 2
    assert all(
        {"recommendation_id", "ts", "model_version", "fallback_level"} <= set(rec)
        for rec in out.recommendations
    )
    assert out.exported_at == _iso(FIXED_NOW)
    assert out.note == "가명 user_key 외 개인정보 없음"


# ── 정확성 ──────────────────────────────────────────────────────────────
def test_delete_removes_four_tables_keeps_user_consent_false_calls_forget_invalidate(
    tmp_path: Path,
) -> None:
    db = Database(tmp_path / "t.db")
    db.apply_schema()
    spy = _Spy()
    client = _app_client(db, catalog=_Cat(), state=spy, invalidate=spy.invalidate)
    _seed_user(db, "u-1")
    r = client.delete("/api/users/u-1/personalization")
    assert r.status_code == 200
    out = PersonalizationDeleted.model_validate(r.json())
    assert out.deleted == SEEDED_DELETED
    assert out.consent is False
    assert _consent(db, "u-1") == 0  # users 행은 남는다(백엔드 01 §10 재동의 시 재생성)
    assert _counts(db, "u-1") == dict.fromkeys(COUNT_TABLES, 0)
    assert spy.calls == [("forget", "u-1"), ("invalidate", "u-1")]


def test_delete_is_idempotent_and_state_after_delete_is_empty(tmp_path: Path) -> None:
    db, client = _client(tmp_path, catalog=_Cat())
    _seed_user(db, "u-1")
    assert client.delete("/api/users/u-1/personalization").status_code == 200
    r2 = client.delete("/api/users/u-1/personalization")
    assert r2.status_code == 200
    out2 = PersonalizationDeleted.model_validate(r2.json())
    assert out2.deleted == EMPTY_DELETED
    assert out2.consent is False
    state = UserStateOut.model_validate(client.get("/api/users/u-1/state").json())
    assert state.consent is False
    assert state.snapshots == []
    assert state.library == {"added": [], "reading": [], "completed": []}


def test_delete_does_not_touch_other_users(tmp_path: Path) -> None:
    db, client = _client(tmp_path, catalog=_Cat())
    _seed_user(db, "u-1")
    _seed_user(db, "u-2", tag="2")
    before = _counts(db, "u-2")
    assert client.delete("/api/users/u-1/personalization").status_code == 200
    assert _counts(db, "u-1") == dict.fromkeys(COUNT_TABLES, 0)
    assert _counts(db, "u-2") == before
    assert _consent(db, "u-2") == 1


def test_delete_without_state_or_cache_callbacks_still_200(tmp_path: Path) -> None:
    db, client = _client(tmp_path, catalog=_Cat(), state=None, invalidate=None)
    _seed_user(db, "u-1")
    r = client.delete("/api/users/u-1/personalization")
    assert r.status_code == 200
    out = PersonalizationDeleted.model_validate(r.json())
    assert out.deleted == SEEDED_DELETED


# ── 안전성 ──────────────────────────────────────────────────────────────
def test_unknown_user_key_is_404_on_all_three_routes(tmp_path: Path) -> None:
    db, client = _client(tmp_path, catalog=_Cat())
    _seed_user(db, "u-1")
    for method, path in (
        ("get", "/api/users/nobody/state"),
        ("get", "/api/users/nobody/data"),
        ("delete", "/api/users/nobody/personalization"),
    ):
        r = getattr(client, method)(path)
        assert r.status_code == 404, path
        assert r.json() == {"detail": "user_key not found"}


def test_user_key_format_422_and_uuid4_passes_format(tmp_path: Path) -> None:
    _db, client = _client(tmp_path)
    for bad in ("%20", "a';b", "a" * 65):
        r = client.get(f"/api/users/{bad}/state")
        assert r.status_code == 422, bad
        assert "Traceback" not in r.text
    ok = client.get(f"/api/users/{uuid.uuid4()}/state")
    assert ok.status_code == 404  # 형식 통과 후 미존재


def test_sql_is_parameter_bound_source_grep() -> None:
    src = SRC_PATH.read_text(encoding="utf-8")
    assert "execute(f" not in src  # 값 보간 SQL 0건 (T-05-05-01)
    assert src.count("WHERE user_key = ?") >= 8


def test_responses_leak_no_traceback_or_pii(tmp_path: Path) -> None:
    db, client = _client(tmp_path, catalog=_Cat(), weights=_weights_spy([]))
    _seed_user(db, "u-1")
    texts = [
        client.get("/api/users/u-1/state").text,
        client.get("/api/users/u-1/data").text,
        client.delete("/api/users/u-1/personalization").text,
    ]
    assert "u-1" in texts[1]  # 열람권 응답이 실제로 그 user_key 의 행을 담는다
    assert all("Traceback" not in t for t in texts)
    assert "@" not in texts[1]  # 가명 user_key 외 개인정보 없음(이메일 형태 부재)


# ── Codex 수정(2026-09-06, 브리프 A) — candidate_sets 삭제·열람 · 열람 한 트랜잭션 ──
SQL_INSERT_CAND = (
    "INSERT INTO candidate_sets (candidate_set_id, user_key, ts, book_ids, survey_variant)"
    " VALUES (?,?,?,?,?)"
)
CAND_BOOK_IDS = [11, 12, 13]


def _seed_cand(db: Database, key: str, cs_id: str) -> None:
    """candidate_sets 1행 — schema.sql 실제 컬럼(ts·book_ids JSON·survey_variant)."""
    con = db.connect()
    with con:
        con.execute(SQL_INSERT_CAND, (cs_id, key, _ago(35), json.dumps(CAND_BOOK_IDS), "A"))


def _cand_count(db: Database, key: str) -> int:
    con = sqlite3.connect(db.path)
    try:
        sql = "SELECT COUNT(*) FROM candidate_sets WHERE user_key = ?"
        return con.execute(sql, (key,)).fetchone()[0]
    finally:
        con.close()


class _DbTrace:
    """Database 를 감싸 핸들러가 쓴 연결과 실행 SQL 을 기록한다(T4 트랜잭션 단정용)."""

    def __init__(self, db: Database) -> None:
        self.db, self.cons, self.sql = db, [], []

    def connect(self) -> sqlite3.Connection:
        con = self.db.connect()
        if con not in self.cons:  # PRAGMA 이후에 붙인다 — 기록 첫 줄이 핸들러의 첫 문장
            self.cons.append(con)
            con.set_trace_callback(self.sql.append)
        return con


def test_delete_removes_candidate_sets_and_counts_them_without_touching_others(
    tmp_path: Path,
) -> None:
    db, client = _client(tmp_path, catalog=_Cat())
    _seed_user(db, "u-1")
    _seed_user(db, "u-2", tag="2")
    _seed_cand(db, "u-1", "cs_1")
    _seed_cand(db, "u-2", "cs_2")
    r = client.delete("/api/users/u-1/personalization")
    assert r.status_code == 200
    out = PersonalizationDeleted.model_validate(r.json())
    assert out.deleted.get("candidate_sets") == 1  # 같은 트랜잭션에서 지우고 집계까지
    assert _cand_count(db, "u-1") == 0
    assert _cand_count(db, "u-2") == 1  # 다른 사용자 행은 그대로


def test_data_export_includes_candidate_sets_with_book_ids_decoded(tmp_path: Path) -> None:
    db, client = _client(tmp_path, catalog=_Cat())
    _seed_user(db, "u-1")
    _seed_user(db, "u-2", tag="2")
    _seed_cand(db, "u-1", "cs_1")
    _seed_cand(db, "u-2", "cs_2")
    out = UserDataOut.model_validate(client.get("/api/users/u-1/data").json())
    assert len(out.candidate_sets) == 1
    row = out.candidate_sets[0]
    assert row["candidate_set_id"] == "cs_1"
    assert row["user_key"] == "u-1"
    assert row["book_ids"] == CAND_BOOK_IDS  # JSON 컬럼은 다른 테이블과 똑같이 풀려서 나온다
    assert row["survey_variant"] == "A"


def test_data_export_runs_in_one_read_transaction_and_leaves_none_open(tmp_path: Path) -> None:
    db = Database(tmp_path / "t.db")
    db.apply_schema()
    _seed_user(db, "u-1")
    _seed_cand(db, "u-1", "cs_1")
    trace = _DbTrace(db)
    client = _app_client(trace, catalog=_Cat())
    assert client.get("/api/users/u-1/data").status_code == 200
    stmts = [line.strip().split()[0].upper() for line in trace.sql]
    assert stmts == ["BEGIN"] + ["SELECT"] * 6 + ["COMMIT"]  # 검증 1 + 5테이블이 한 스냅샷
    assert all(con.in_transaction is False for con in trace.cons)


def test_data_export_404_does_not_leave_a_transaction_open(tmp_path: Path) -> None:
    db = Database(tmp_path / "t.db")
    db.apply_schema()
    trace = _DbTrace(db)
    client = _app_client(trace, catalog=_Cat())
    assert client.get("/api/users/nobody/data").status_code == 404
    assert all(con.in_transaction is False for con in trace.cons)
