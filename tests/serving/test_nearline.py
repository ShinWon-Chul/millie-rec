"""serving/nearline.py — 계약 · 정확성(커서·리플레이·selected) · 안전성(예외·웨이크).

Phase 5 '서빙 Must 완성'(.planning/ROADMAP.md). SERV-09 경계 증거 · 결정 D-08(05-CONTEXT.md).
events 는 tmp_path SQLite, 시간은 주입, 네트워크 없음.
"""

import asyncio
import logging
from datetime import UTC, datetime
from pathlib import Path

from millie_rec.serving.db import Database
from millie_rec.serving.nearline import NearlineLoop
from millie_rec.serving.state import StateStore

T0 = 1_800_000_000.0
SQL_INSERT = (
    "INSERT INTO events(event_id, user_key, book_id, event_type, ts, candidate_set_id, selected) "
    "VALUES(?, ?, ?, ?, ?, ?, ?)"
)
SQL_IMPRESSIONS = (
    "SELECT book_id, selected FROM events WHERE event_type='impression' ORDER BY book_id"
)


def _ts(sec: float) -> str:
    """T0 기준 상대 초 → ISO-8601 UTC 'Z'(demo_api 가 정규화해 저장하는 형식)."""
    dt = datetime.fromtimestamp(T0 + sec, UTC)
    return dt.isoformat(timespec="seconds").replace("+00:00", "Z")


def _db(tmp_path: Path) -> Database:
    db = Database(tmp_path / "t.db")
    db.apply_schema()
    return db


def _insert(
    db: Database,
    event_id: str,
    user_key: str,
    event_type: str,
    book_id: int | None,
    ts: str,
    candidate_set_id: str | None = None,
    selected: int | None = None,
) -> None:
    con = db.connect()
    with con:
        con.execute(
            SQL_INSERT,
            (event_id, user_key, book_id, event_type, ts, candidate_set_id, selected),
        )


def _pair(tmp_path: Path) -> tuple[Database, StateStore, NearlineLoop]:
    db, store = _db(tmp_path), StateStore(now=lambda: T0)
    return db, store, NearlineLoop(db, store, interval_s=5.0, now=lambda: T0)


# ── 계약 ────────────────────────────────────────────────────────────────
def test_loop_exposes_wake_last_run_last_rowid(tmp_path: Path):
    _, _, nearline = _pair(tmp_path)
    assert isinstance(nearline.wake, asyncio.Event)
    assert nearline.last_run is None
    assert nearline.last_rowid == 0
    assert isinstance(nearline.run_once(), int)


# ── 정확성 ──────────────────────────────────────────────────────────────
def test_handler_side_insert_does_not_change_state_until_run_once(tmp_path: Path):
    db, store, nearline = _pair(tmp_path)
    _insert(db, "e1", "u", "reader_open", 1, _ts(-20))
    _insert(db, "e2", "u", "reader_open", 2, _ts(-10))
    assert store.user_state("u").history == ()  # SERV-09: 핸들러는 적재만 한다
    assert nearline.run_once() == 2
    assert store.user_state("u").history == (2, 1)
    assert nearline.run_once() == 0
    _insert(db, "e3", "u", "qualified_read", 3, _ts(-5))
    assert nearline.run_once() == 1


def test_replay_applies_only_last_24h_and_advances_cursor(tmp_path: Path):
    db, store, nearline = _pair(tmp_path)
    _insert(db, "old", "u", "completion", 41, _ts(-90000))
    _insert(db, "new", "u", "reader_open", 42, _ts(-3600))
    assert nearline.replay() == 1
    assert store.user_state("u").history == (42,)
    assert store.n_completed("u") == 0
    assert nearline.run_once() == 0


def test_preference_book_selected_fills_impression_selected(tmp_path: Path):
    db, _, nearline = _pair(tmp_path)
    _insert(db, "i7", "u", "impression", 7, _ts(-30), candidate_set_id="cand_1")
    _insert(db, "i8", "u", "impression", 8, _ts(-30), candidate_set_id="cand_1")
    _insert(db, "s7", "u", "preference_book_selected", 7, _ts(-20), candidate_set_id="cand_1")
    assert nearline.run_once() == 3
    rows = db.connect().execute(SQL_IMPRESSIONS).fetchall()  # db.py row_factory 무관하게 비교
    assert [tuple(r) for r in rows] == [(7, 1), (8, None)]


# ── 안전성 ──────────────────────────────────────────────────────────────
def test_apply_exception_is_logged_and_remaining_rows_applied(tmp_path: Path, monkeypatch, caplog):
    db, store, nearline = _pair(tmp_path)
    for i in (1, 2, 3):
        _insert(db, f"e{i}", "u", "reader_open", i, _ts(-i))
    original, calls = store.apply_event, []

    def flaky(*args, **kwargs):
        calls.append(args)
        if len(calls) == 1:
            raise RuntimeError("boom")
        return original(*args, **kwargs)

    monkeypatch.setattr(store, "apply_event", flaky)
    with caplog.at_level(logging.ERROR):
        assert nearline.run_once() == 2
    assert sum(1 for r in caplog.records if r.levelno == logging.ERROR) == 1
    assert len(store.user_state("u").history) == 2


def test_tick_runs_once_when_woken_and_sets_last_run(tmp_path: Path):
    db, store, nearline = _pair(tmp_path)
    _insert(db, "e1", "u", "reader_open", 11, _ts(-10))
    nearline.wake.set()
    asyncio.run(nearline._tick())
    assert isinstance(nearline.last_run, str) and nearline.last_run.endswith("Z")
    assert nearline.wake.is_set() is False
    assert store.user_state("u").history == (11,)


def test_waker_is_thread_safe(tmp_path: Path):
    _, _, nearline = _pair(tmp_path)

    async def main() -> bool:
        wake = nearline.waker(asyncio.get_running_loop())
        await asyncio.to_thread(wake)
        await asyncio.sleep(0)
        return nearline.wake.is_set()

    assert asyncio.run(main()) is True


# ── 품질 게이트 경계(F5) ────────────────────────────────────────────────
SQL_INSERT_FLAGGED = (
    "INSERT INTO events(event_id, user_key, book_id, event_type, ts, quality_flag) "
    "VALUES(?, ?, ?, ?, ?, ?)"
)


def _insert_flagged(db: Database, event_id: str, book_id: int, ts: str, flag: str) -> None:
    con = db.connect()
    with con:
        con.execute(SQL_INSERT_FLAGGED, (event_id, "u", book_id, "reader_open", ts, flag))


def test_run_once_skips_quality_flagged_rows_and_advances_cursor(tmp_path: Path):
    db, store, nearline = _pair(tmp_path)
    _insert(db, "clean", "u", "reader_open", 1, _ts(-30))
    _insert_flagged(db, "bad", 2, _ts(-20), "book_ineligible")
    assert nearline.run_once() == 1  # 플래그 행은 온라인 상태를 만들지 않는다
    assert store.user_state("u").history == (1,)
    assert nearline.last_rowid == 2  # 커서는 플래그 행을 넘어간다(정체 없음)
    assert nearline.run_once() == 0


def test_replay_skips_quality_flagged_rows(tmp_path: Path):
    db, store, nearline = _pair(tmp_path)
    _insert_flagged(db, "bad", 41, _ts(-3600), "ts_future")
    _insert(db, "clean", "u", "reader_open", 42, _ts(-1800))
    assert nearline.replay() == 1
    assert store.user_state("u").history == (42,)
    assert nearline.last_rowid == 2
    assert nearline.run_once() == 0
