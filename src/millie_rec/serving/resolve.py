"""user_key 해석 — users + preference_snapshots 한 벌을 Resolved 로 굳힌다(백엔드 01 §5).

아키 §9-3 목록 외 신설(cascade.py 150줄 유지, Advisor 승인 2026-09-06) — PROGRESS 1줄은 05-09.
"""

import json
from dataclasses import dataclass

from fastapi import HTTPException

from millie_rec.serving.db import Database

NOT_FOUND_SNAPSHOT = "snapshot_id not found for user_key"

SQL_USER = "SELECT consent, cell FROM users WHERE user_key = ?"
SNAP_COLS = "SELECT snapshot_id, categories, criterion, seeds, persona FROM preference_snapshots "
# created_at 은 초 단위라 같은 초에 두 벌이 들어올 수 있다 — 동률은 삽입 순서(rowid)로 깬다
SQL_SNAP_ONE = SNAP_COLS + "WHERE user_key = ? ORDER BY created_at DESC, rowid DESC LIMIT 1"
SQL_SNAP_BY_ID = SNAP_COLS + "WHERE user_key = ? AND snapshot_id = ?"
SQL_SNAP_AGG = "SELECT COUNT(*), MAX(created_at) FROM preference_snapshots WHERE user_key = ?"


@dataclass(frozen=True)
class Resolved:
    """users + preference_snapshots 한 벌 — 요청 1건의 개인화 입력."""

    user_key: str
    found: bool = False
    consent: bool = False
    cell: str | None = None
    snapshot_id: str | None = None
    seeds: tuple[int, ...] = ()
    categories: tuple[str, ...] = ()
    criterion: str | None = None
    persona_name: str | None = None
    snapshots_count: int = 0
    latest_created_at: str | None = None


def _j(value: object, default: object) -> object:
    """스냅샷 JSON 컬럼. 손상돼도 응답이 500 이 되지 않는다."""
    try:
        return json.loads(value) if value else default
    except (TypeError, ValueError):
        return default


def resolve_user(db: Database, user_key: str, snapshot_id: str | None) -> Resolved:
    """users·스냅샷 조회. snapshot_id 가 그 user 것이 아니면 404(T-05-06-03). 전부 ? 바인딩."""
    u = db.query(SQL_USER, (user_key,))
    if not u:
        return Resolved(user_key)
    args = (user_key, snapshot_id) if snapshot_id else (user_key,)
    rows = db.query(SQL_SNAP_BY_ID if snapshot_id else SQL_SNAP_ONE, args)
    if snapshot_id and not rows:
        raise HTTPException(404, detail=NOT_FOUND_SNAPSHOT)
    count, latest = db.query(SQL_SNAP_AGG, (user_key,))[0]
    s = dict(rows[0]) if rows else {}
    persona = _j(s.get("persona"), {})
    name = persona.get("name") if isinstance(persona, dict) else None
    seeds = tuple(int(b) for b in _j(s.get("seeds"), []))
    cats = tuple(_j(s.get("categories"), []))
    return Resolved(user_key, True, bool(u[0]["consent"]), u[0]["cell"], s.get("snapshot_id"),
                    seeds, cats, s.get("criterion"), name, count, latest)  # fmt: skip
