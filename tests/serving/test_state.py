"""serving/state.py — 계약(UserState) · 정확성(history·세션·완독) · 안전성(forget·ts).

Phase 5 '서빙 Must 완성'(.planning/ROADMAP.md). 결정 D-05~D-08(05-CONTEXT.md).
시간은 주입(now 인자), 네트워크·DB 없음.
"""

import logging
from datetime import UTC, datetime

from millie_rec.serving.state import (
    HISTORY_MAX,
    SESSION_WINDOW_S,
    StateStore,
    parse_ts,
    reset_boost,
)

T0 = 1_800_000_000.0


def _ts(sec: float) -> str:
    """T0 기준 상대 초 → ISO-8601 UTC 'Z'(events.ts 저장 형식)."""
    dt = datetime.fromtimestamp(T0 + sec, UTC)
    return dt.isoformat(timespec="seconds").replace("+00:00", "Z")


def _store(now: float = T0) -> StateStore:
    return StateStore(now=lambda: now)


# ── 계약 ────────────────────────────────────────────────────────────────
def test_parse_ts_accepts_z_offset_and_naive_as_utc():
    expected = datetime(2026, 9, 7, 12, 0, 27, tzinfo=UTC).timestamp()
    assert parse_ts("2026-09-07T12:00:27Z") == expected
    assert parse_ts("2026-09-07T12:00:27+00:00") == expected
    assert parse_ts("2026-09-07T12:00:27") == expected


def test_user_state_context_has_user_key_n_completed_categories_reading_time():
    store = _store()
    user = store.user_state("u", seeds=(1, 2), categories=("소설", "IT"),
                            subcategories=("한국 소설",), context="evening")  # fmt: skip
    assert user.explicit_seeds == (1, 2)
    assert user.context == {
        "user_key": "u",
        "n_completed": "0",
        "categories": "소설,IT",
        "subcategories": "한국 소설",
        "reading_time": "evening",
    }
    assert user.history == () and user.session == ()
    assert "reading_time" not in store.user_state("u", categories=("소설",)).context


# ── 정확성 ──────────────────────────────────────────────────────────────
def test_history_only_reading_events_distinct_recent_first():
    store = _store()
    store.apply_event("u", "library_add", 1, _ts(-100))  # D-05: 서재 담기는 history 아님
    store.apply_event("u", "reader_open", 2, _ts(-90))
    store.apply_event("u", "qualified_read", 3, _ts(-80))
    store.apply_event("u", "completion", 4, _ts(-70))
    assert store.user_state("u").history == (4, 3, 2)
    store.apply_event("u", "reader_open", 2, _ts(-60))
    history = store.user_state("u").history
    assert history == (2, 4, 3)
    assert 1 not in history


def test_session_is_30min_window_and_session_active():
    def _fill(store: StateStore) -> None:
        store.apply_event("u", "detail_click", 5, _ts(-10))
        store.apply_event("u", "reader_open", 6, _ts(-(SESSION_WINDOW_S + 100)))

    fresh = _store()
    _fill(fresh)
    assert fresh.user_state("u").session == (5,)
    assert fresh.session_active("u") is True

    stale = _store(T0 + 3600)
    _fill(stale)
    assert stale.user_state("u").session == ()
    assert stale.session_active("u") is False


def test_n_completed_counts_distinct_completion_books():
    store = _store()
    store.apply_event("u", "completion", 4, _ts(-300))
    store.apply_event("u", "completion", 4, _ts(-200))
    store.apply_event("u", "completion", 7, _ts(-100))
    assert store.n_completed("u") == 2
    assert store.completed_books("u") == (7, 4)
    assert store.user_state("u").context["n_completed"] == "2"


def test_continue_reading_excludes_completed_recent_first():
    store = _store()
    store.apply_event("u", "reader_open", 8, _ts(-50))
    store.apply_event("u", "reader_open", 9, _ts(-40))
    store.apply_event("u", "completion", 9, _ts(-30))
    assert store.continue_reading("u") == (8,)


def test_reset_boost_requires_second_snapshot_within_24h():
    assert reset_boost(2, _ts(-3600), now=T0) is True
    assert reset_boost(1, _ts(-3600), now=T0) is False
    assert reset_boost(3, _ts(-90000), now=T0) is False
    assert reset_boost(2, None, now=T0) is False


def test_history_capped_at_history_max():
    store = _store()
    for book_id in range(1, 206):
        store.apply_event("u", "reader_open", book_id, _ts(-1000 + book_id))
    history = store.user_state("u").history
    assert len(history) == HISTORY_MAX
    assert history[0] == 205
    assert 1 not in history


# ── 안전성 ──────────────────────────────────────────────────────────────
def test_forget_removes_record_and_unknown_key_is_noop():
    store = _store()
    store.apply_event("u", "reader_open", 1, _ts(-10))
    assert len(store) == 1
    store.forget("u")
    assert len(store) == 0
    assert store.user_state("u").history == ()
    store.forget("nobody")
    assert len(store) == 0


def test_event_without_book_id_only_updates_last_event_ts():
    store = _store()
    store.apply_event("u", "impression", None, _ts(0))
    assert store.last_event_ts("u") == T0
    user = store.user_state("u")
    assert user.history == () and user.session == ()


def test_bad_ts_is_ignored_not_raised(caplog):
    store = _store()
    with caplog.at_level(logging.WARNING):
        store.apply_event("u", "reader_open", 1, "not-a-time")
    assert store.user_state("u").history == ()
    assert sum(1 for r in caplog.records if r.levelno == logging.WARNING) == 1
