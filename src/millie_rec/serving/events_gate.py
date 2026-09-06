"""POST /api/events 품질·동의 게이트.

아키 §9-3 목록 외 신설(demo_api 150줄 유지 · Advisor 승인 2026-09-06).
"""

import sqlite3
from collections.abc import Iterable
from datetime import UTC, datetime

from millie_rec.contracts import Catalog
from millie_rec.serving.schemas import EventIn

FUTURE_SKEW_S, BACKDATED_S = 300, 3600  # 백엔드 01 §6 미래 +5분 · 1h 이상 과거
FLAG_TS_FUTURE, FLAG_TS_BACKDATED = "ts_future", "ts_backdated"  # 백엔드 01 §6 quality_flag
FLAG_BOOK_INELIGIBLE = "book_ineligible"
# 동의 철회(users.consent=0) 유저의 이벤트 — 저장도 웨이크도 하지 않는다(Codex 적대 T2)
FLAG_CONSENT_OFF = "consent_off"
SQL_LAST_TS = "SELECT MAX(ts) FROM events WHERE user_key = ?"
SQL_CONSENT_OFF = "SELECT 1 FROM users WHERE user_key = ? AND consent = 0"


def parse_ts(ts: str) -> datetime:
    """ISO-8601 'Z' 허용 파싱. tzinfo 가 없으면 UTC 로 본다."""
    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def consent_off_keys(con: sqlite3.Connection, user_keys: Iterable[str]) -> set[str]:
    """users.consent = 0 인 user_key 집합. users 행이 없는 익명 키는 포함하지 않는다(T2)."""
    return {k for k in dict.fromkeys(user_keys) if con.execute(SQL_CONSENT_OFF, (k,)).fetchone()}


def quality_flag(
    con: sqlite3.Connection,
    e: EventIn,
    now_dt: datetime,
    catalog: Catalog | None,
    *,
    parsed_ts: datetime | None = None,
) -> str | None:
    """게이트 순서(백엔드 01 §6): ts_future → ts_backdated → book_ineligible, 첫 적중 1개."""
    t = parsed_ts if parsed_ts is not None else parse_ts(e.ts)
    if (t - now_dt).total_seconds() > FUTURE_SKEW_S:
        return FLAG_TS_FUTURE
    last = con.execute(SQL_LAST_TS, (e.user_key,)).fetchone()[0]
    if last and (parse_ts(last) - t).total_seconds() >= BACKDATED_S:
        return FLAG_TS_BACKDATED
    if e.book_id is not None and catalog is not None and not catalog.eligible([e.book_id]):
        return FLAG_BOOK_INELIGIBLE
    return None
