"""Nearline 루프 — 30s 타이머 ∨ 웨이크, rowid 커서, 24h 리플레이.

SERV-09 경계 증거 · 아키텍처 01 §3-5 · 결정 D-08(05-CONTEXT.md).
"""

import asyncio
import logging
import sqlite3
import time
from collections.abc import Callable
from datetime import UTC, datetime

from millie_rec.contracts import NEARLINE_INTERVAL_S, Neighbors
from millie_rec.serving.after_completion import precompute
from millie_rec.serving.db import Database
from millie_rec.serving.state import COMPLETION, REPLAY_WINDOW_S, StateStore

log = logging.getLogger(__name__)

BATCH_ROWS = 1000  # 05-CONTEXT Claude's Discretion "리플레이 배치 크기"
SELECTED_EVENT = "preference_book_selected"  # 같은 candidate_set 의 impression.selected 를 채운다
COLUMNS = "SELECT rowid, user_key, book_id, event_type, ts, candidate_set_id FROM events "
# quality_flag IS NULL — 품질 게이트가 붙인 행(ts_future · ts_backdated · book_ineligible)은
# 분석·대시보드용으로 저장만 하고 온라인 상태를 만들지 않는다(Codex F5). 커서는 아래 hi 로 넘긴다
CLEAN = "WHERE quality_flag IS NULL AND rowid > ? AND rowid <= ? "
SQL_NEW = COLUMNS + CLEAN + "ORDER BY rowid LIMIT ?"
SQL_REPLAY = COLUMNS + CLEAN + "AND ts >= ? ORDER BY rowid LIMIT ?"
SQL_MAX_ROWID = "SELECT COALESCE(MAX(rowid), 0) FROM events"
SQL_MARK_SELECTED = (
    "UPDATE events SET selected = 1 WHERE event_type = 'impression' "
    "AND user_key = ? AND candidate_set_id = ? AND book_id = ?"
)


def _iso(epoch: float) -> str:
    """epoch → ISO-8601 UTC 'Z'. events.ts 와 같은 형식이라 문자열 비교가 성립한다."""
    dt = datetime.fromtimestamp(epoch, UTC)
    return dt.isoformat(timespec="seconds").replace("+00:00", "Z")


class NearlineLoop:
    """events → StateStore 의 유일한 통로. 요청 핸들러는 events INSERT 만 한다(SERV-09)."""

    def __init__(
        self,
        db: Database,
        store: StateStore,
        *,
        neighbors: Neighbors | None = None,
        interval_s: float = NEARLINE_INTERVAL_S,
        now: Callable[[], float] | None = None,
    ) -> None:
        self.db = db
        self.store = store
        self.neighbors = neighbors  # after_completion 사전 계산의 유일한 이웃 경로(D-13)
        self.interval_s = interval_s
        self._now = now or time.time
        self.wake = asyncio.Event()
        self.last_run: str | None = None
        self.last_rowid = 0

    def _apply_rows(self, con: sqlite3.Connection, rows: list[tuple]) -> int:
        """행 단위 try — 한 행의 실패가 루프를 멈추지 않는다(T-05-01-03). 커서는 실패 행도 전진."""
        applied = 0
        for rowid, user_key, book_id, event_type, ts, cand in rows:
            try:
                self.store.apply_event(user_key, event_type, book_id, ts)
                if event_type == COMPLETION and book_id is not None and self.neighbors is not None:
                    precompute(self.store, user_key, book_id, self.neighbors)  # D-13
                if event_type == SELECTED_EVENT and cand and book_id is not None:
                    with con:
                        con.execute(SQL_MARK_SELECTED, (user_key, cand, book_id))
                applied += 1
            except Exception:
                log.exception("nearline apply failed rowid=%s; continuing", rowid)
            self.last_rowid = max(self.last_rowid, rowid)
        return applied

    def run_once(self) -> int:
        """아직 처리하지 않은 events 행(rowid 커서)만 상태에 반영하고 처리 수를 돌려준다."""
        con = self.db.connect()
        hi = con.execute(SQL_MAX_ROWID).fetchone()[0]  # 상한 고정 후 그 아래만 스캔 = 유실 없음
        total = 0
        while self.last_rowid < hi:
            rows = con.execute(SQL_NEW, (self.last_rowid, hi, BATCH_ROWS)).fetchall()
            if not rows:
                break
            total += self._apply_rows(con, rows)
            if len(rows) < BATCH_ROWS:
                break
        self.last_rowid = max(self.last_rowid, hi)  # 건너뛴 플래그 행에서 커서가 멈추지 않게
        return total

    def replay(self) -> int:
        """기동 시 ts ≥ now − 24h 만 반영하고 커서를 MAX(rowid) 로 올린다(D-08)."""
        con = self.db.connect()
        since = _iso(self._now() - REPLAY_WINDOW_S)
        hi = con.execute(SQL_MAX_ROWID).fetchone()[0]
        total = 0
        while self.last_rowid < hi:
            rows = con.execute(SQL_REPLAY, (self.last_rowid, hi, since, BATCH_ROWS)).fetchall()
            if not rows:
                break
            total += self._apply_rows(con, rows)
            if len(rows) < BATCH_ROWS:
                break
        self.last_rowid = max(self.last_rowid, hi)
        return total

    async def _tick(self) -> None:
        """웨이크 ∨ interval_s 타임아웃 1회분. 동기 SQLite 작업은 to_thread 로 뺀다."""
        try:
            await asyncio.wait_for(self.wake.wait(), timeout=self.interval_s)
        except TimeoutError:
            pass
        self.wake.clear()
        try:
            await asyncio.to_thread(self.run_once)
            self.last_run = _iso(self._now())
        except Exception:
            log.exception("nearline run failed; continuing")

    async def run(self) -> None:
        while True:
            await self._tick()

    def waker(self, loop: asyncio.AbstractEventLoop) -> Callable[[], None]:
        """동기 핸들러용 웨이크 — Event.set() 을 직접 부르지 않고 루프 스레드로 넘긴다."""
        return lambda: loop.call_soon_threadsafe(self.wake.set)
