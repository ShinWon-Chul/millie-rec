"""serving/book_stats.py — 계약(stats 위임) · 정확성(완독 평균·카테고리 prior) · 안전성(None·캐시).

Phase 5 '서빙 Must 완성'(.planning/ROADMAP.md). 결정 D-07(.planning/phases/05-must/05-CONTEXT.md).
"""

from collections.abc import Sequence

import pytest

from millie_rec.contracts import BookStats, UserState
from millie_rec.serving.book_stats import ServingBookStats
from millie_rec.serving.state import StateStore

T0 = 1_800_000_000.0
TS = "2026-09-07T12:00:27Z"


class _Catalog:
    """Catalog + BookStatsSource 가짜 — meta·popular·stats 만(calls 관례)."""

    def __init__(
        self,
        difficulty: dict[int, float | None],
        by_cat: dict[str, list[int]] | None = None,
    ) -> None:
        self.d = difficulty
        self.by_cat = by_cat or {}
        self.calls = 0
        self.popular_calls = 0

    def meta(self, book_ids: Sequence[int]) -> list[dict]:
        return [{"book_id": int(b), "difficulty": self.d.get(int(b))} for b in book_ids]

    def popular(self, categories: Sequence[str] = (), n: int = 50) -> list[int]:
        self.popular_calls += 1
        if not categories:
            return list(self.d)[:n]
        return [b for c in categories for b in self.by_cat.get(c, [])][:n]

    def eligible(self, book_ids: Sequence[int]) -> list[int]:
        return list(book_ids)

    def stats(self, book_ids: Sequence[int]) -> list[BookStats]:
        self.calls += 1
        return [BookStats(book_id=int(b)) for b in book_ids]

    def user_level(self, user: UserState) -> float | None:
        return None


def _store(*completed: int) -> StateStore:
    store = StateStore(now=lambda: T0)
    for book_id in completed:
        store.apply_event("u", "completion", book_id, TS)
    return store


# ── 계약 ────────────────────────────────────────────────────────────────
def test_stats_delegates_once_to_catalog():
    cat = _Catalog({})
    assert [s.book_id for s in ServingBookStats(cat, _store()).stats([1, 2])] == [1, 2]
    assert cat.calls == 1


# ── 정확성 ──────────────────────────────────────────────────────────────
def test_user_level_is_mean_difficulty_of_completed_books_excluding_missing():
    store = _store(1, 2, 3)
    adapter = ServingBookStats(_Catalog({1: 0.2, 2: 0.6, 3: None}), store)
    assert adapter.user_level(store.user_state("u")) == pytest.approx(0.4)


def test_user_level_falls_back_to_category_prior_when_no_completion_and_caches():
    cat = _Catalog({10: 0.3, 11: 0.5}, {"소설": [10, 11]})
    store = _store()
    adapter = ServingBookStats(cat, store)
    user = store.user_state("u", categories=("소설",))
    assert adapter.user_level(user) == pytest.approx(0.4)
    assert adapter.user_level(user) == pytest.approx(0.4)
    assert cat.popular_calls == 1


# ── 안전성 ──────────────────────────────────────────────────────────────
def test_user_level_none_without_completion_and_categories():
    empty = _store()
    assert ServingBookStats(_Catalog({}), empty).user_level(empty.user_state("u")) is None
    missing = _store(1, 2)
    adapter = ServingBookStats(_Catalog({1: None, 2: None}), missing)
    assert adapter.user_level(missing.user_state("u")) is None


def test_user_level_anonymous_user_without_user_key_uses_prior_only():
    cat = _Catalog({10: 0.3, 11: 0.5}, {"소설": [10, 11]})
    adapter = ServingBookStats(cat, _store())
    anon = UserState(None, context={"categories": "소설"})
    assert adapter.user_level(anon) == pytest.approx(0.4)
    assert adapter.user_level(UserState(None)) is None
