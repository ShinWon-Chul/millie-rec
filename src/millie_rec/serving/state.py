"""user_key 메모리 상태 — Nearline 만 쓰고 요청은 읽는다(05-CONTEXT D-05~D-08)."""

import logging
import threading
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime

from millie_rec.contracts import UserState

log = logging.getLogger(__name__)

SESSION_WINDOW_S = 1800  # D-06(05-CONTEXT.md): 세션 창 30분
REPLAY_WINDOW_S = 86400  # D-08(05-CONTEXT.md): 기동 시 리플레이 24h
RESET_BOOST_WINDOW_S = 86400  # D-08: 재설정 부스트는 created_at 24h 이내
HISTORY_MAX = 200  # 05-CONTEXT Claude's Discretion "history 상한(예: 최근 200권)"
HISTORY_EVENT_TYPES = ("reader_open", "qualified_read", "completion")  # D-05: 읽기 행동만
SESSION_EVENT_TYPES = ("reader_open", "detail_click")  # D-06
COMPLETION = "completion"


@dataclass
class _Record:
    """user_key 하나의 집계. 쓰기는 Nearline 스레드 한 곳뿐이다(SERV-09)."""

    history: list[int] = field(default_factory=list)  # D-05 읽기 3종, 최근순 distinct
    session: list[tuple[int, float]] = field(default_factory=list)  # D-06 (book_id, epoch)
    completed: list[int] = field(default_factory=list)  # D-07 n_completed·user_level 원천
    reading: list[int] = field(default_factory=list)  # D-03 continue_reading
    last_event_ts: float | None = None


def parse_ts(ts: str) -> float:
    """ISO-8601 → epoch 초. 'Z' 허용, tz 없으면 UTC(백엔드 01 §0 "ISO-8601 UTC")."""
    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.timestamp()


def reset_boost(snapshots_count: int, latest_created_at: str | None, *, now: float) -> bool:
    """D-08: 최신 스냅샷이 2번째 이상 ∧ created_at 이 24h 이내 → α 부스트 인자 True."""
    if snapshots_count < 2 or not latest_created_at:
        return False
    return now - parse_ts(latest_created_at) <= RESET_BOOST_WINDOW_S


def _push_front(lst: list[int], book_id: int, cap: int) -> None:
    """최근순 distinct 유지 — 있으면 앞으로 옮기고 상한을 넘으면 꼬리를 버린다."""
    if book_id in lst:
        lst.remove(book_id)
    lst.insert(0, book_id)
    del lst[cap:]


def _session_ids(rec: _Record, now: float) -> tuple[int, ...]:
    """최근 SESSION_WINDOW_S 안의 책, 최근순 distinct. 미래 ts 도 창 밖으로 본다(T-05-01-01)."""
    lo, hi = now - SESSION_WINDOW_S, now + SESSION_WINDOW_S
    out: list[int] = []
    for book_id, t in reversed(rec.session):
        if lo <= t <= hi and book_id not in out:
            out.append(book_id)
    return tuple(out)


class StateStore:
    """user_key → 집계 dict. 쓰기는 Nearline(apply_event), 요청 핸들러는 읽기만 한다(D-08)."""

    def __init__(self, *, now: Callable[[], float] | None = None) -> None:
        self._now = now or time.time
        self._users: dict[str, _Record] = {}
        self.after_completion: dict[str, tuple[int, tuple[tuple[int, float], ...]]] = {}
        self._lock = threading.Lock()

    def apply_event(self, user_key: str, event_type: str, book_id: int | None, ts: str) -> None:
        """Nearline 전용 쓰기. 잘못된 ts·book_id 없는 이벤트는 예외 없이 흘려보낸다."""
        try:
            t = parse_ts(ts)
        except ValueError:
            log.warning("bad ts %r for %s; ignored", ts, user_key)
            return
        with self._lock:
            rec = self._users.setdefault(user_key, _Record())
            rec.last_event_ts = t if rec.last_event_ts is None else max(rec.last_event_ts, t)
            if book_id is None:
                return
            b = int(book_id)
            if event_type in HISTORY_EVENT_TYPES:
                _push_front(rec.history, b, HISTORY_MAX)
            if event_type == COMPLETION:
                _push_front(rec.completed, b, HISTORY_MAX)
                rec.reading = [x for x in rec.reading if x != b]
            elif event_type == "reader_open" and b not in rec.completed:
                _push_front(rec.reading, b, HISTORY_MAX)
            if event_type in SESSION_EVENT_TYPES:
                rec.session.append((b, t))
                del rec.session[:-HISTORY_MAX]

    def _snapshot(self, user_key: str) -> _Record:
        """락 안에서 레코드를 얻는다 — 호출자는 곧바로 tuple 로 굳힌다."""
        with self._lock:
            return self._users.get(user_key) or _Record()

    def user_state(
        self,
        user_key: str,
        *,
        seeds: Sequence[int] = (),
        categories: Sequence[str] = (),
        context: str | None = None,
    ) -> UserState:
        """요청 시점 스냅샷. context 값은 전부 str(계약의 dict[str, str])."""
        rec = self._snapshot(user_key)
        done = str(len(rec.completed))
        ctx = {"user_key": user_key, "n_completed": done, "categories": ",".join(categories)}
        if context:
            ctx["reading_time"] = context
        return UserState(
            user_id=None,
            explicit_seeds=tuple(int(s) for s in seeds),
            history=tuple(rec.history),
            session=_session_ids(rec, self._now()),
            context=ctx,
        )

    def session_active(self, user_key: str) -> bool:
        return bool(_session_ids(self._snapshot(user_key), self._now()))

    def n_completed(self, user_key: str) -> int:
        return len(self._snapshot(user_key).completed)

    def completed_books(self, user_key: str) -> tuple[int, ...]:
        return tuple(self._snapshot(user_key).completed)

    def continue_reading(self, user_key: str) -> tuple[int, ...]:
        return tuple(self._snapshot(user_key).reading)

    def last_event_ts(self, user_key: str) -> float | None:
        return self._snapshot(user_key).last_event_ts

    def forget(self, user_key: str) -> None:
        """DELETE …/personalization 은 메모리 상태도 지운다(D-08). 완독 행도 함께(D-13)."""
        with self._lock:
            self._users.pop(user_key, None)
            self.after_completion.pop(user_key, None)

    def __len__(self) -> int:
        with self._lock:
            return len(self._users)
