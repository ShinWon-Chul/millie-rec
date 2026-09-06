"""SQLite 쓰기 헬퍼 — 계약(rowcount·Row) · 정확성(close·backup) · 안전성(인덱스·바인딩).

Phase 5 '서빙 Must 완성'(.planning/ROADMAP.md) plan 05-03. `db.py` 쓰기 헬퍼는 05-04·05-05·05-06
의 INSERT 가 Nearline 스레드에서 보이기 위한 전제(커밋 가시성 단정).
"""

import sqlite3
from pathlib import Path

from millie_rec.contracts import DB_FILENAME
from millie_rec.serving.db import Database

TS = "2026-09-07T00:00:00Z"
SQL_INSERT_USER = "INSERT INTO users(user_key, created_at, consent, cell, is_new) VALUES(?,?,?,?,?)"
SQL_INSERT_EVENT = (
    "INSERT OR IGNORE INTO events(event_id, user_key, event_type, ts) VALUES(?,?,?,?)"
)
SQL_INDEXES = (
    "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%' ORDER BY name"
)


def _db(tmp_path: Path) -> Database:
    db = Database(tmp_path / DB_FILENAME)
    db.apply_schema()
    return db


# ── 계약 ────────────────────────────────────────────────────────────────
def test_execute_inserts_commits_and_returns_rowcount(tmp_path: Path):
    db = _db(tmp_path)
    assert db.execute(SQL_INSERT_USER, ("u", TS, 1, "A", 1)) == 1
    # 커밋 증거 — 별도 연결(= Nearline 스레드의 연결)에서 보인다
    other = sqlite3.connect(db.path)
    try:
        assert other.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 1
    finally:
        other.close()


def test_query_returns_sqlite_rows_as_dict_able(tmp_path: Path):
    db = _db(tmp_path)
    db.execute(SQL_INSERT_USER, ("u", TS, 1, "A", 1))
    rows = db.query("SELECT user_key, cell FROM users WHERE user_key = ?", ("u",))
    assert len(rows) == 1
    assert rows[0]["cell"] == "A"
    assert dict(rows[0]) == {"user_key": "u", "cell": "A"}


# ── 정확성 ──────────────────────────────────────────────────────────────
def test_executemany_sums_rowcount_with_insert_or_ignore(tmp_path: Path):
    db = _db(tmp_path)
    inserted = db.executemany(
        SQL_INSERT_EVENT,
        [
            ("e1", "u", "reader_open", TS),
            ("e2", "u", "reader_open", TS),
            ("e1", "u", "reader_open", TS),  # 중복 event_id → IGNORE
        ],
    )
    assert inserted == 2
    assert db.query("SELECT COUNT(*) AS n FROM events")[0]["n"] == 2


def test_execute_delete_returns_affected_rows(tmp_path: Path):
    db = _db(tmp_path)
    db.executemany(
        SQL_INSERT_EVENT, [("e1", "u", "reader_open", TS), ("e2", "u", "completion", TS)]
    )
    assert db.execute("DELETE FROM events WHERE user_key = ?", ("u",)) == 2
    assert db.execute("DELETE FROM events WHERE user_key = ?", ("nobody",)) == 0


def test_close_drops_thread_connection_and_reconnects(tmp_path: Path):
    db = _db(tmp_path)
    con1 = db.connect()
    db.close()
    con2 = db.connect()
    assert con2 is not con1
    assert db.ok() is True
    db.close()
    db.close()  # 두 번 닫아도 예외 없음


def test_backup_creates_snapshot_with_same_counts(tmp_path: Path):
    db = _db(tmp_path)
    db.execute(SQL_INSERT_USER, ("u", TS, 1, "A", 1))
    before = db.row_counts()
    dest = db.backup(tmp_path / "backup" / "b.db")
    assert dest.exists()
    copy = sqlite3.connect(dest)
    try:
        assert copy.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 1
    finally:
        copy.close()
    assert db.row_counts() == before  # 원본 무변경


# ── 안전성 ──────────────────────────────────────────────────────────────
def test_schema_has_two_phase5_indexes_and_is_idempotent(tmp_path: Path):
    db = _db(tmp_path)
    names = [r["name"] for r in db.query(SQL_INDEXES)]
    assert names == ["idx_events_user_ts", "idx_recommendations_user_ts"]
    db.apply_schema()  # 멱등
    assert [r["name"] for r in db.query(SQL_INDEXES)] == names


def test_row_counts_still_dict_int_and_bind_params_block_injection(tmp_path: Path):
    db = _db(tmp_path)
    evil = "x'; DROP TABLE users; --"
    assert db.execute("INSERT INTO users(user_key) VALUES(?)", (evil,)) == 1
    assert "users" in db.table_names()
    assert len(db.query("SELECT user_key FROM users WHERE user_key = ?", (evil,))) == 1
    counts = db.row_counts()
    assert counts["users"] == 1
    assert all(isinstance(v, int) for v in counts.values())
