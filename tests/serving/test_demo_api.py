"""demo_api.py — 계약(preferences 201) · 정확성(events 품질 게이트) · 안전성(형식·상한·주입).

Phase 5 '서빙 Must 완성'(.planning/ROADMAP.md) Plan 05-04.
05-CONTEXT D-08(스냅샷 append·cell·library_add) · D-16(페르소나) · 품질 게이트 순서 · SERV-09 경계.
가짜는 파일마다 복제한다(tests/serving/test_api_weights.py 관례).
"""

import hashlib
import json
import uuid
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from millie_rec.contracts import DB_FILENAME
from millie_rec.serving import demo_api
from millie_rec.serving.db import Database
from millie_rec.serving.demo_api import assign_cell, build_router
from millie_rec.serving.schemas import EventsAccepted, PreferencesResponse

CATS = ("소설", "에세이", "경제경영", "인문")
INELIGIBLE = {18, 19, 20}
FIXED_NOW = datetime(2026, 9, 7, 12, 0, 0, tzinfo=UTC)
USER_B = "u-1"  # sha256 손계산으로 B 셀이 나오는 키
USER_A = "u-2"  # 같은 식으로 A 셀
MOCK_SENTENCE = "회원님은 IT와 소설을 즐기고, 베스트셀러로 책을 고르는 독서가입니다."
PREFS = {
    "user_key": USER_B,
    "consent": True,
    "reading_time": "저녁, 하루를 마치며",
    "categories": ["IT", "소설"],
    "criterion": "bestseller",
    "subcategories": ["SF"],
    "seeds": [1, 2, 3, 4, 5],
    "candidate_set_id": "cand_abc123",
}


def _iso(dt: datetime) -> str:
    return dt.isoformat(timespec="seconds").replace("+00:00", "Z")


def _no_trace(r) -> bool:
    return "Traceback" not in r.text


def _expected_cell(user_key: str) -> str:
    return "A" if int(hashlib.sha256(user_key.encode()).hexdigest()[:8], 16) % 2 == 0 else "B"


def _event(event_id: str, **kw) -> dict:
    body = {
        "event_id": event_id,
        "user_key": USER_B,
        "book_id": 1,
        "event_type": "reader_open",
        "ts": _iso(FIXED_NOW),
    }
    body.update(kw)
    return body


class _Spy:
    """호출 인자를 모으는 가짜 콜백. wake 는 인자 없음, invalidate 는 user_key 1개."""

    def __init__(self) -> None:
        self.calls: list = []

    def __call__(self, *args):
        self.calls.append(args[0] if args else None)


class _Cat:
    """20권 합성 카탈로그. eligible 만 쓴다(book_ineligible 게이트)."""

    def meta(self, book_ids: Sequence[int]) -> list[dict]:
        return [{"book_id": b, "title": f"밀리 표본 도서 {b}"} for b in book_ids]

    def popular(self, categories: Sequence[str] = (), n: int = 50) -> list[int]:
        return [b for b in range(1, 21) if b not in INELIGIBLE][:n]

    def eligible(self, book_ids: Sequence[int]) -> list[int]:
        return [b for b in book_ids if b not in INELIGIBLE]


def _build(tmp_path: Path, **kw) -> tuple[Database, TestClient]:
    db = Database(tmp_path / DB_FILENAME)
    db.apply_schema()
    kw.setdefault("catalog", _Cat())
    kw.setdefault("now", lambda: FIXED_NOW)
    app = FastAPI()
    app.include_router(build_router(db=db, **kw))
    return db, TestClient(app)


@pytest.fixture
def spies() -> tuple[_Spy, _Spy]:
    return _Spy(), _Spy()


# ── 계약 ────────────────────────────────────────────────────────────────
def test_preferences_201_snapshot_cell_sha256_persona_sentence(tmp_path: Path):
    db, client = _build(tmp_path)
    r = client.post("/api/preferences", json=PREFS)
    assert r.status_code == 201, r.text
    out = PreferencesResponse.model_validate(r.json())
    assert out.preference_snapshot_id.startswith("snap_")
    assert len(out.preference_snapshot_id) == 11
    assert out.cell == _expected_cell(USER_B) == "B" == assign_cell(USER_B)
    assert out.created_at == _iso(FIXED_NOW) and out.snapshots_count == 1
    assert out.persona is not None and out.persona.name == "오디세우스"
    assert out.persona.description == MOCK_SENTENCE
    row = (
        db.connect()
        .execute(
            "SELECT reading_time, categories, criterion, subcategories, seeds FROM"
            " preference_snapshots WHERE snapshot_id = ?",
            (out.preference_snapshot_id,),
        )
        .fetchone()
    )
    assert row[0] == "저녁, 하루를 마치며" and json.loads(row[1]) == ["IT", "소설"]
    assert row[2] == "bestseller" and json.loads(row[3]) == ["SF"]
    assert json.loads(row[4]) == [1, 2, 3, 4, 5]
    assert assign_cell(USER_A) == "A"


def test_preferences_appends_second_snapshot_keeps_cell_and_history(tmp_path: Path):
    db, client = _build(tmp_path)
    first = PreferencesResponse.model_validate(client.post("/api/preferences", json=PREFS).json())
    body = dict(PREFS, restart=True, categories=["인문"], seeds=[6, 7])
    r2 = client.post("/api/preferences", json=body)
    assert r2.status_code == 201
    second = PreferencesResponse.model_validate(r2.json())
    assert second.snapshots_count == 2
    assert second.preference_snapshot_id != first.preference_snapshot_id
    assert second.cell == first.cell  # users 저장값 재사용
    assert second.persona is not None and second.persona.name == "돈키호테"
    con = db.connect()
    assert (
        con.execute(
            "SELECT COUNT(*) FROM preference_snapshots WHERE user_key = ?", (USER_B,)
        ).fetchone()[0]
        == 2
    )
    assert con.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 1


def test_preferences_records_library_add_per_seed_with_z_ts_and_calls_wake_invalidate(
    tmp_path: Path, spies: tuple[_Spy, _Spy]
):
    wake, invalidate = spies
    db, client = _build(tmp_path, wake=wake, invalidate=invalidate)
    out = PreferencesResponse.model_validate(client.post("/api/preferences", json=PREFS).json())
    rows = (
        db.connect()
        .execute(
            "SELECT book_id, event_type, surface, preference_snapshot_id, candidate_set_id, ts,"
            " event_id FROM events WHERE user_key = ? ORDER BY book_id",
            (USER_B,),
        )
        .fetchall()
    )
    assert [r[0] for r in rows] == [1, 2, 3, 4, 5]
    assert all(r[1] == "library_add" and r[2] == "onboarding" for r in rows)
    assert all(r[3] == out.preference_snapshot_id and r[4] == "cand_abc123" for r in rows)
    assert all(r[5] == _iso(FIXED_NOW) for r in rows)
    assert len({r[6] for r in rows}) == 5 and all(len(r[6]) == 32 for r in rows)
    assert len(wake.calls) == 1 and invalidate.calls == [USER_B]


def test_preferences_consent_false_stores_no_seeds_no_events_no_wake(
    tmp_path: Path, spies: tuple[_Spy, _Spy]
):
    wake, invalidate = spies
    db, client = _build(tmp_path, wake=wake, invalidate=invalidate)
    r = client.post(
        "/api/preferences", json={"user_key": USER_A, "consent": False, "seeds": [1, 2]}
    )
    assert r.status_code == 201
    out = PreferencesResponse.model_validate(r.json())
    assert out.persona is not None and out.persona.name == "오디세우스"
    con = db.connect()
    assert (
        json.loads(
            con.execute(
                "SELECT seeds FROM preference_snapshots WHERE user_key = ?", (USER_A,)
            ).fetchone()[0]
        )
        == []
    )
    assert con.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 0
    assert con.execute("SELECT consent FROM users WHERE user_key = ?", (USER_A,)).fetchone()[0] == 0
    assert wake.calls == []


# ── 정확성 ──────────────────────────────────────────────────────────────
def test_events_single_and_batch_dedup_202_and_ts_normalized_to_z(
    tmp_path: Path, spies: tuple[_Spy, _Spy]
):
    wake, _inv = spies
    db, client = _build(tmp_path, wake=wake)
    single = _event("e1", ts="2026-09-07T12:00:00+00:00")
    r = client.post("/api/events", json=single)
    assert r.status_code == 202, r.text
    assert EventsAccepted.model_validate(r.json()).model_dump() == {
        "accepted": 1,
        "duplicates": 0,
        "flagged": [],
    }
    stored = db.connect().execute("SELECT ts FROM events WHERE event_id = 'e1'").fetchone()[0]
    assert stored == "2026-09-07T12:00:00Z"
    again = EventsAccepted.model_validate(client.post("/api/events", json=single).json())
    assert again.accepted == 0 and again.duplicates == 1
    batch = {"events": [_event("e2"), _event("e3"), _event("e2")]}
    out = EventsAccepted.model_validate(client.post("/api/events", json=batch).json())
    assert out.accepted == 2 and out.duplicates == 1
    assert len(wake.calls) == 2  # 중복만인 두 번째 호출은 wake 없음


def test_events_quality_flags_future_backdated_ineligible_first_hit_stored(tmp_path: Path):
    db, client = _build(tmp_path)

    def post(body):
        return EventsAccepted.model_validate(client.post("/api/events", json=body).json())

    fut = post(_event("f1", user_key="u-f", ts=_iso(FIXED_NOW + timedelta(minutes=6))))
    assert [f.model_dump() for f in fut.flagged] == [
        {"event_id": "f1", "quality_flag": "ts_future"}
    ]
    assert fut.accepted == 1
    row = db.connect().execute("SELECT quality_flag FROM events WHERE event_id='f1'").fetchone()
    assert row[0] == "ts_future"  # 플래그가 붙어도 저장된다

    assert post(_event("b0", user_key="u-b")).flagged == []
    back = post(_event("b1", user_key="u-b", ts=_iso(FIXED_NOW - timedelta(hours=2))))
    assert back.flagged[0].quality_flag == "ts_backdated"

    inelig = post(_event("i1", user_key="u-i", book_id=18))
    assert inelig.flagged[0].quality_flag == "book_ineligible"

    assert post(_event("ok1", user_key="u-ok")).flagged == []
    assert post(_event("ok2", user_key="u-ok2", book_id=None)).flagged == []
    assert (
        post(_event("ok3", user_key="u-ok3", ts=_iso(FIXED_NOW + timedelta(minutes=4)))).flagged
        == []
    )
    assert post(_event("ok4", user_key="u-ok4")).flagged == []
    near = post(_event("ok5", user_key="u-ok4", ts=_iso(FIXED_NOW - timedelta(minutes=59))))
    assert near.flagged == []


def test_events_unparseable_ts_is_422_nothing_stored(tmp_path: Path, spies: tuple[_Spy, _Spy]):
    wake, _inv = spies
    db, client = _build(tmp_path, wake=wake)
    assert client.post("/api/events", json=_event("bad1", ts="not-a-time")).status_code == 422
    batch = {"events": [_event("g1"), _event("g2", ts="nope")]}
    assert client.post("/api/events", json=batch).status_code == 422
    assert db.connect().execute("SELECT COUNT(*) FROM events").fetchone()[0] == 0
    assert wake.calls == []


def test_user_key_format_422_on_preferences_and_events_uuid4_passes(tmp_path: Path):
    _, client = _build(tmp_path)
    assert client.post("/api/preferences", json={"user_key": "a';b"}).status_code == 422
    assert client.post("/api/events", json=_event("k1", user_key="x y")).status_code == 422
    assert client.post("/api/preferences", json={"user_key": "u" * 65}).status_code == 422
    key = str(uuid.uuid4())
    assert len(key) == 36
    assert client.post("/api/preferences", json={"user_key": key}).status_code == 201
    assert client.post("/api/events", json=_event("k2", user_key=key)).status_code == 202


def test_events_handler_has_no_state_writes_source_grep():
    src = Path(demo_api.__file__).read_text(encoding="utf-8")
    assert "apply_event" not in src and "StateStore" not in src  # SERV-09 경계


# ── 안전성 ──────────────────────────────────────────────────────────────
def test_extra_forbid_and_limits_422(tmp_path: Path):
    _, client = _build(tmp_path)
    assert client.post("/api/preferences", json={"user_key": USER_B, "foo": 1}).status_code == 422
    bad_type = _event("x1", event_type="itemknn_click")
    assert client.post("/api/events", json=bad_type).status_code == 422
    over_cats = dict(PREFS, categories=["IT", "소설", "인문", "과학"])
    assert client.post("/api/preferences", json=over_cats).status_code == 422
    over_seeds = dict(PREFS, seeds=list(range(1, 32)))
    assert client.post("/api/preferences", json=over_seeds).status_code == 422
    big = {"events": [_event(f"b{i}") for i in range(51)]}
    assert client.post("/api/events", json=big).status_code == 422
    assert client.post("/api/events", json={"events": []}).status_code == 422


def test_router_without_callbacks_or_catalog_still_works(tmp_path: Path):
    db = Database(tmp_path / DB_FILENAME)
    db.apply_schema()
    app = FastAPI()
    app.include_router(build_router(db=db, now=lambda: FIXED_NOW))
    client = TestClient(app)
    assert client.post("/api/preferences", json=PREFS).status_code == 201
    r = client.post("/api/events", json=_event("n1", book_id=18))
    assert r.status_code == 202
    assert EventsAccepted.model_validate(r.json()).flagged == []  # catalog None → 검사 생략


def test_sql_injection_value_blocked_by_format_and_no_fstring_sql(tmp_path: Path):
    db, client = _build(tmp_path)
    evil = "x'; DROP TABLE users; --"
    assert client.post("/api/preferences", json={"user_key": evil}).status_code == 422
    tables = {r[0] for r in db.connect().execute("SELECT name FROM sqlite_master").fetchall()}
    assert "users" in tables
    src = Path(demo_api.__file__).read_text(encoding="utf-8")
    assert "execute(f" not in src


def test_no_traceback_in_responses(tmp_path: Path):
    _, client = _build(tmp_path)
    responses = [
        client.post("/api/preferences", json=PREFS),
        client.post("/api/preferences", json={"user_key": "a b"}),
        client.post("/api/events", json=_event("t1")),
        client.post("/api/events", json=_event("t2", ts="nope")),
    ]
    assert all(_no_trace(r) for r in responses)


# ── 동의 철회 후 재유입 차단(T2) ─────────────────────────────────────────
SQL_USER_ROW = "INSERT INTO users(user_key, created_at, consent, cell, is_new) VALUES(?,?,?,'A',0)"


def _user(db: Database, user_key: str, consent: int) -> None:
    con = db.connect()
    with con:
        con.execute(SQL_USER_ROW, (user_key, _iso(FIXED_NOW), consent))


def test_events_from_consent_off_user_not_stored_and_no_wake(
    tmp_path: Path, spies: tuple[_Spy, _Spy]
):
    wake, _inv = spies
    db, client = _build(tmp_path, wake=wake)
    _user(db, "u-off", 0)
    r = client.post("/api/events", json=_event("c1", user_key="u-off"))
    assert r.status_code == 202, r.text
    out = EventsAccepted.model_validate(r.json())
    assert out.accepted == 0 and out.duplicates == 0
    assert [f.model_dump() for f in out.flagged] == [
        {"event_id": "c1", "quality_flag": "consent_off"}
    ]
    con = db.connect()
    assert con.execute("SELECT COUNT(*) FROM events WHERE user_key = 'u-off'").fetchone()[0] == 0
    assert wake.calls == []


def test_events_consent_on_and_unknown_user_key_still_accepted(
    tmp_path: Path, spies: tuple[_Spy, _Spy]
):
    wake, _inv = spies
    db, client = _build(tmp_path, wake=wake)
    _user(db, "u-on", 1)
    on = EventsAccepted.model_validate(
        client.post("/api/events", json=_event("y1", user_key="u-on")).json()
    )
    assert on.accepted == 1 and on.flagged == []
    anon = EventsAccepted.model_validate(
        client.post("/api/events", json=_event("y2", user_key="u-anon")).json()
    )
    assert anon.accepted == 1 and anon.flagged == []  # users 행 없음(익명) = 기존 동작
    _user(db, "u-off2", 0)
    batch = {"events": [_event("y3", user_key="u-off2"), _event("y4", user_key="u-on")]}
    mixed = EventsAccepted.model_validate(client.post("/api/events", json=batch).json())
    assert mixed.accepted == 1 and [f.quality_flag for f in mixed.flagged] == ["consent_off"]
    assert len(wake.calls) == 3
    stored = {r[0] for r in db.connect().execute("SELECT event_id FROM events").fetchall()}
    assert stored == {"y1", "y2", "y4"}
