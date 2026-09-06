"""열람·삭제·철회 API — GET state · GET data · DELETE personalization (백엔드 서빙 01 §8~§10)."""

import json
import logging
import re
import sqlite3
from collections.abc import Callable
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException

from millie_rec.contracts import Catalog, UserState
from millie_rec.serving.db import Database
from millie_rec.serving.schemas import PersonalizationDeleted, UserDataOut, UserStateOut

log = logging.getLogger(__name__)

USER_KEY_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")  # 백엔드 01 §0 UUIDv4 — 안전 문자·길이 상한
KEY_ERR = [{"loc": ["path", "user_key"], "msg": USER_KEY_RE.pattern, "type": "value_error"}]
DELETE_TABLES = ("preference_snapshots", "events", "ratings", "recommendations", "candidate_sets")
DELETED_KEYS = ("snapshots", "events", "ratings", "recommendations", "candidate_sets")  # §10
HISTORY_EVENT_TYPES = ("reader_open", "qualified_read", "completion")  # D-05 (state.py 와 중복)
LIBRARY_ADD, COMPLETION, NOT_FOUND = "library_add", "completion", "user_key not found"
ZERO_WEIGHTS = {"alpha": 0.0, "beta": 0.0, "gamma": 0.0}
SNAP_KEYS, BOOK_KEYS = ("snapshot_id", "created_at", "criterion"), ("title", "image_url")
_JSON = "categories subcategories seeds persona payload latency_breakdown weights rows book_ids"
JSON_COLS = _JSON.split()  # book_ids = candidate_sets (Codex T3, 2026-09-06)
SQL_USER = "SELECT user_key, created_at, consent, cell, is_new FROM users WHERE user_key = ?"
SQL_EXPORT = {  # §9 열람권 — 키 = UserDataOut 필드명. candidate_sets 는 Codex T3(2026-09-06)
    "snapshots": "SELECT * FROM preference_snapshots WHERE user_key = ? ORDER BY created_at DESC",
    "events": "SELECT * FROM events WHERE user_key = ? ORDER BY ts, rowid",
    "ratings": "SELECT * FROM ratings WHERE user_key = ? ORDER BY ts",
    "recommendations": "SELECT * FROM recommendations WHERE user_key = ? ORDER BY ts",
    "candidate_sets": "SELECT * FROM candidate_sets WHERE user_key = ? ORDER BY ts",
}
SQL_LIB = "SELECT book_id, event_type, ts FROM events WHERE user_key = ? ORDER BY ts DESC"
SQL_DELETE = {t: f"DELETE FROM {t} WHERE user_key = ?" for t in DELETE_TABLES}  # 이름은 상수 튜플
SQL_CONSENT_OFF = "UPDATE users SET consent = 0 WHERE user_key = ?"


def _loads(value: str) -> object:
    try:
        return json.loads(value)
    except ValueError:  # 손상된 JSON 은 원문 유지 — 열람권 응답이 500 이 되지 않는다
        return value


def _rows(con: sqlite3.Connection, sql: str, user_key: str) -> list[dict]:
    cur = con.cursor()  # row_factory 는 커서 단위 — 공유 연결을 바꾸지 않는다
    cur.row_factory = sqlite3.Row  # 행을 dict 로, JSON 컬럼은 풀어서(§9 열람권)
    return [
        {k: (_loads(v) if k in JSON_COLS and isinstance(v, str) else v) for k, v in dict(r).items()}
        for r in cur.execute(sql, (user_key,)).fetchall()
    ]


def _user_or_404(con: sqlite3.Connection, user_key: str) -> dict:  # 422 → 404 (§0 오류 규약)
    if USER_KEY_RE.match(user_key) is None:
        raise HTTPException(422, detail=KEY_ERR)
    rows = _rows(con, SQL_USER, user_key)
    if not rows:
        raise HTTPException(404, detail=NOT_FOUND)
    return rows[0]


def _ids(rows: list[tuple], types: tuple[str, ...]) -> list[int]:  # distinct book_id 최근순
    return list(dict.fromkeys(b for b, t, _ts in rows if t in types and b is not None))


def _library(rows: list[tuple], catalog: Catalog | None) -> dict[str, list[dict]]:
    """added=library_add · reading=읽었고 완독 없음 · completed=completion (05-CONTEXT 재량)."""
    done = _ids(rows, (COMPLETION,))
    buckets = {
        "added": _ids(rows, (LIBRARY_ADD,)),
        "reading": [b for b in _ids(rows, HISTORY_EVENT_TYPES) if b not in done],
        "completed": done,
    }
    ids = sorted({b for v in buckets.values() for b in v})
    m = {int(x["book_id"]): x for x in catalog.meta(ids)} if catalog is not None and ids else {}
    cards = {b: {"book_id": b, **{k: m.get(b, {}).get(k) for k in BOOK_KEYS}} for b in ids}
    return {k: [cards[b] for b in v] for k, v in buckets.items()}


def _snap(s: dict) -> dict:
    return {**{k: s.get(k) for k in SNAP_KEYS}, "categories": s.get("categories") or []}


def _weights_of(user_key: str, snaps: list[dict], rows: list[tuple], *, state, weights) -> dict:
    """최신 스냅샷 seeds + 읽기 history(D-05) → UserState → 주입된 weights. 실패는 0 셋(로그만)."""
    top = snaps[0] if snaps else {}
    seeds, cats = tuple(top.get("seeds") or ()), tuple(top.get("categories") or ())
    try:
        if state is None:
            user = UserState(None, seeds, tuple(_ids(rows, HISTORY_EVENT_TYPES)))
        else:  # state 가 있으면 메모리 상태가 정본(revision C6)
            user = state.user_state(user_key, seeds=seeds, categories=cats)
        return dict(weights(user)) if weights is not None else dict(ZERO_WEIGHTS)
    except Exception:  # 예외 문자열을 응답에 싣지 않는다 — 로그 후 0 셋(T-05-05-06)
        log.exception("user_state_weights failed; serving zero weights")
        return dict(ZERO_WEIGHTS)


def build_router(*, db: Database, catalog: Catalog | None = None, state: object | None = None,
                 weights: Callable[[UserState], dict[str, float]] | None = None,
                 invalidate: Callable[[str], object] | None = None,
                 now: Callable[[], datetime] | None = None) -> APIRouter:  # fmt: skip
    """의존은 전부 주입(create_app 배선은 plan 05-06). 핸들러는 동기 def — 스레드풀."""
    router = APIRouter(prefix="/api/users")
    clock = now or (lambda: datetime.now(UTC))

    @router.get("/{user_key}/state", response_model=UserStateOut)
    def user_state(user_key: str) -> UserStateOut:
        con = db.connect()
        u = _user_or_404(con, user_key)
        snaps = _rows(con, SQL_EXPORT["snapshots"], user_key)
        lib = con.cursor().execute(SQL_LIB, (user_key,)).fetchall()
        return UserStateOut(
            user_key=user_key,
            consent=bool(u["consent"]),
            cell=u["cell"],
            is_new=bool(u["is_new"]),
            library=_library(lib, catalog),
            snapshots=[_snap(s) | {"active": i == 0} for i, s in enumerate(snaps)],
            user_state_weights=_weights_of(user_key, snaps, lib, state=state, weights=weights),
        )

    @router.get("/{user_key}/data", response_model=UserDataOut)
    def user_data(user_key: str) -> UserDataOut:
        con = db.connect()
        con.execute("BEGIN")  # T4: 검증·SELECT 전부를 한 읽기 트랜잭션으로 — 일관 스냅샷
        with con:  # 정상 COMMIT · 예외 ROLLBACK — 어느 쪽이든 트랜잭션은 닫힌다
            user = _user_or_404(con, user_key)
            tables = {k: _rows(con, q, user_key) for k, q in SQL_EXPORT.items()}
        return UserDataOut(user=user, **tables, exported_at=clock().isoformat(timespec="seconds"))

    @router.delete("/{user_key}/personalization", response_model=PersonalizationDeleted)
    def delete_personalization(user_key: str) -> PersonalizationDeleted:
        con = db.connect()
        _user_or_404(con, user_key)
        with con:  # 4테이블 삭제 + consent=0 한 트랜잭션. users 행은 남긴다(§10 재동의)
            n = [con.execute(SQL_DELETE[t], (user_key,)).rowcount for t in DELETE_TABLES]
            con.execute(SQL_CONSENT_OFF, (user_key,))
        if state is not None:
            state.forget(user_key)
        if invalidate is not None:
            invalidate(user_key)
        deleted = dict(zip(DELETED_KEYS, n, strict=True))
        return PersonalizationDeleted(user_key=user_key, consent=False, deleted=deleted)

    return router
