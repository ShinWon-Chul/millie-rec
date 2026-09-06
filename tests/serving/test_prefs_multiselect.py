"""취향 설정 다중 선택(시간대·기준·작가) 적재 · 조회 · context 전달 · 기존 DB 마이그레이션.

정본은 설계서 데이터 소스 09 §3-3·§3-4·§4(다중 선택 온보딩과 작가 피처 설계).
단수 reading_time·criterion 은 "처음 고른 값" 파생이라 옛 클라이언트·배지·페르소나가 그대로 돈다.
가짜는 파일마다 복제한다(tests/serving/test_demo_api.py 관례).
"""

import json
import sqlite3
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from millie_rec.contracts import DB_FILENAME
from millie_rec.serving.db import Database
from millie_rec.serving.demo_api import build_router
from millie_rec.serving.resolve import Resolved, resolve_user, user_state_of
from millie_rec.serving.schemas import PreferencesResponse
from millie_rec.serving.state import StateStore

INELIGIBLE = {18, 19, 20}
FIXED_NOW = datetime(2026, 9, 7, 12, 0, 0, tzinfo=UTC)
USER = "u_multi"
SNAP = "snap_multi01"
TIMES = ["저녁, 하루를 마치며", "잠들기 전"]
CRITS = ["bestseller", "review"]
AUTHORS = ["김초엽", "정세랑"]
SNAP_COLS_LEGACY = (  # 새 컬럼 3개가 없던 옛 스키마 — Railway 볼륨의 millie.db 모양
    "CREATE TABLE preference_snapshots (snapshot_id TEXT PRIMARY KEY, user_key TEXT,"
    " created_at TEXT, reading_time TEXT, categories TEXT, criterion TEXT, subcategories TEXT,"
    " seeds TEXT, persona TEXT)"
)
PREFS = {
    "user_key": USER,
    "consent": True,
    "categories": ["IT", "소설"],
    "subcategories": ["SF"],
    "seeds": [1, 2],
    "reading_times": TIMES,
    "criteria": CRITS,
    "authors": AUTHORS,
}


class _Cat:
    """20권 합성 카탈로그. eligible 만 쓴다(library_add 게이트)."""

    def meta(self, book_ids: Sequence[int]) -> list[dict]:
        return [{"book_id": b, "title": f"밀리 표본 도서 {b}"} for b in book_ids]

    def popular(self, categories: Sequence[str] = (), n: int = 50) -> list[int]:
        return [b for b in range(1, 21) if b not in INELIGIBLE][:n]

    def eligible(self, book_ids: Sequence[int]) -> list[int]:
        return [b for b in book_ids if b not in INELIGIBLE]


def _build(tmp_path: Path) -> tuple[Database, TestClient]:
    db = Database(tmp_path / DB_FILENAME)
    db.apply_schema()
    app = FastAPI()
    app.include_router(build_router(db=db, catalog=_Cat(), now=lambda: FIXED_NOW))
    return db, TestClient(app)


def _snap_row(db: Database, sid: str) -> sqlite3.Row:
    return db.query(
        "SELECT reading_time, criterion, reading_times, criteria, authors"
        " FROM preference_snapshots WHERE snapshot_id = ?",
        (sid,),
    )[0]


def _post(client: TestClient, body: dict) -> str:
    r = client.post("/api/preferences", json=body)
    assert r.status_code == 201, r.text
    return PreferencesResponse.model_validate(r.json()).preference_snapshot_id


def _seed_snapshot(db: Database, **cols: str) -> None:
    db.execute(
        "INSERT INTO users(user_key, created_at, consent, cell, is_new) VALUES(?,?,1,?,1)",
        (USER, "2026-09-06T00:00:00Z", "A"),
    )
    row = {
        "categories": json.dumps(["소설"], ensure_ascii=False),
        "criterion": "review",
        "subcategories": json.dumps(["SF"], ensure_ascii=False),
        "seeds": json.dumps([1, 2]),
        "persona": "{}",
        "reading_times": json.dumps(TIMES, ensure_ascii=False),
        "criteria": json.dumps(CRITS, ensure_ascii=False),
        "authors": json.dumps(AUTHORS, ensure_ascii=False),
    } | cols
    keys = ", ".join(row)
    db.execute(
        f"INSERT INTO preference_snapshots(snapshot_id, user_key, created_at, {keys})"
        f" VALUES(?,?,?,{', '.join('?' * len(row))})",
        (SNAP, USER, "2026-09-06T01:00:00Z", *row.values()),
    )


# ── 계약 ────────────────────────────────────────────────────────────────
def test_preferences_stores_multiselect_json_columns(tmp_path: Path):
    db, client = _build(tmp_path)
    row = _snap_row(db, _post(client, PREFS))
    assert json.loads(row["reading_times"]) == TIMES
    assert json.loads(row["criteria"]) == CRITS
    assert json.loads(row["authors"]) == AUTHORS


def test_preferences_derives_singular_from_first_choice(tmp_path: Path):
    db, client = _build(tmp_path)
    row = _snap_row(db, _post(client, PREFS))
    assert row["reading_time"] == TIMES[0] and row["criterion"] == CRITS[0]


def test_preferences_legacy_singular_body_fills_plural_columns(tmp_path: Path):
    """옛 클라이언트는 단수만 보낸다 — 복수 컬럼이 그 값 1개짜리 배열이어야 한다."""
    db, client = _build(tmp_path)
    body = {k: v for k, v in PREFS.items() if k not in ("reading_times", "criteria", "authors")}
    row = _snap_row(db, _post(client, {**body, "reading_time": TIMES[1], "criterion": CRITS[1]}))
    assert row["reading_time"] == TIMES[1] and row["criterion"] == CRITS[1]
    assert json.loads(row["reading_times"]) == [TIMES[1]]
    assert json.loads(row["criteria"]) == [CRITS[1]]
    assert json.loads(row["authors"]) == []


def test_resolve_user_returns_multiselect_tuples(tmp_path: Path):
    db = Database(tmp_path / DB_FILENAME)
    db.apply_schema()
    _seed_snapshot(db)
    r = resolve_user(db, USER, None)
    assert r.snapshot_id == SNAP and r.subcategories == ("SF",)
    assert r.reading_times == tuple(TIMES)
    assert r.criteria == tuple(CRITS)
    assert r.authors == tuple(AUTHORS)


def test_user_state_of_puts_multiselect_csv_in_context():
    r = Resolved(
        USER, True, True, "A", SNAP, (1, 2), ("소설",),
        reading_times=tuple(TIMES), criteria=tuple(CRITS), authors=tuple(AUTHORS),
    )  # fmt: skip
    for state in (user_state_of(StateStore(), r, "저녁"), user_state_of(None, r, None)):
        assert state.context["reading_times"] == ",".join(TIMES)
        assert state.context["criteria"] == ",".join(CRITS)
        assert state.context["authors"] == ",".join(AUTHORS)
    plain = user_state_of(None, Resolved(USER), None)
    assert plain.context["criteria"] == "" and plain.context["authors"] == ""


# ── 안전성 ──────────────────────────────────────────────────────────────
def test_apply_schema_adds_columns_to_legacy_db_and_keeps_rows(tmp_path: Path):
    """CREATE TABLE IF NOT EXISTS 는 컬럼을 더하지 않는다 — ALTER 보강이 있어야 한다."""
    path = tmp_path / DB_FILENAME
    con = sqlite3.connect(path)
    con.execute(SNAP_COLS_LEGACY)
    con.execute(
        "INSERT INTO preference_snapshots(snapshot_id, user_key, criterion) VALUES(?,?,?)",
        (SNAP, USER, "review"),
    )
    con.commit()
    con.close()
    db = Database(path)
    db.apply_schema()
    db.apply_schema()  # 두 번 돌려도 예외 없다(멱등)
    cols = {r[1] for r in db.query("PRAGMA table_info(preference_snapshots)")}
    assert {"reading_times", "criteria", "authors"} <= cols
    kept = db.query("SELECT snapshot_id, criterion, criteria FROM preference_snapshots")
    assert len(kept) == 1 and kept[0]["snapshot_id"] == SNAP
    assert kept[0]["criterion"] == "review" and kept[0]["criteria"] is None


def test_resolve_user_tolerates_corrupt_multiselect_json(tmp_path: Path):
    db = Database(tmp_path / DB_FILENAME)
    db.apply_schema()
    _seed_snapshot(db, criteria="{", authors="not json", reading_times="[")
    r = resolve_user(db, USER, None)
    assert r.criteria == () and r.authors == () and r.reading_times == ()
    assert user_state_of(None, r, None).context["criteria"] == ""
