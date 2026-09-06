"""fallback 재료 — 계약(캐시 키·TTL) · 정확성(예산·level 2) · 안전성(기존 회귀·스레드).

Phase 5 '서빙 Must 완성'(.planning/ROADMAP.md) plan 05-03. 결정 '예산 판정·level 1 캐시'
(.planning/phases/05-must/05-CONTEXT.md 항목 D-10). 오케스트레이션(0→1→2→3)은 05-06 cascade.py.
"""

import inspect
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor

from millie_rec.contracts import Row, ScoredItem, UserState
from millie_rec.serving.fallback import (
    SOURCE_POPULARITY,
    TRENDING_PURPOSE,
    TRENDING_ROW_ID,
    TRENDING_TITLE,
    GlobalPopularFallback,
    Level1Cache,
    over_budget,
    segment_popular,
    trending_row,
)

T0 = 1_800_000_000.0


class _Cat:
    """popular 만 쓰는 가짜 Catalog(테스트 간 import 금지 관례 — 파일마다 복제)."""

    def meta(self, book_ids: Sequence[int]) -> list[dict]:
        return []

    def popular(self, categories: Sequence[str] = (), n: int = 50) -> list[int]:
        if not categories:
            return list(range(1, 11))[:n]
        if tuple(categories) == ("소설",):
            return [2, 4, 6, 8, 10][:n]
        return []

    def eligible(self, book_ids: Sequence[int]) -> list[int]:
        return list(book_ids)


def _row(ids: Sequence[int]) -> Row:
    return Row(
        row_id="trending",
        title="지금 많이 읽는 책",
        purpose="fallback",
        items=tuple(ScoredItem(book_id=b, score=1.0) for b in ids),
    )


# ── 계약 ────────────────────────────────────────────────────────────────
def test_cache_put_get_by_user_snapshot_variant_key():
    c = Level1Cache(now=lambda: T0)
    assert c.get("u", "snap_1", "hybrid") is None
    c.put("u", "snap_1", "hybrid", (_row([1, 2]),), "hybrid_v1")
    assert c.get("u", "snap_1", "hybrid") == ((_row([1, 2]),), "hybrid_v1")
    assert len(c) == 1
    assert c.get("u", "snap_1", "pop") is None  # variant 가 키의 일부
    assert c.get("v", "snap_1", "hybrid") is None  # user_key 가 키의 일부


def test_cache_expires_after_ttl_and_evicts():
    clock = {"t": T0}
    c = Level1Cache(now=lambda: clock["t"])
    c.put("u", "snap_1", "hybrid", (_row([1]),), "hybrid_v1")
    clock["t"] = T0 + 599  # CACHE_TTL_S=600 안
    assert c.get("u", "snap_1", "hybrid") is not None
    clock["t"] = T0 + 601
    assert c.get("u", "snap_1", "hybrid") is None
    assert len(c) == 0  # 만료 조회가 제거한다

    clock2 = {"t": T0}
    short = Level1Cache(ttl_s=5, now=lambda: clock2["t"])
    short.put("u", "snap_1", "hybrid", (_row([1]),), "hybrid_v1")
    clock2["t"] = T0 + 6
    assert short.get("u", "snap_1", "hybrid") is None


# ── 정확성 ──────────────────────────────────────────────────────────────
def test_cache_invalidate_removes_only_that_user_key():
    c = Level1Cache(now=lambda: T0)
    c.put("u", "snap_1", "hybrid", (_row([1]),), "hybrid_v1")
    c.put("u", "snap_2", "hybrid_div", (_row([2]),), "hybrid_div_v1")
    c.put("v", "snap_9", "hybrid", (_row([3]),), "hybrid_v1")
    assert c.invalidate("u") == 2
    assert len(c) == 1
    assert c.get("v", "snap_9", "hybrid") == ((_row([3]),), "hybrid_v1")
    assert c.invalidate("nobody") == 0


def test_over_budget_strict_greater_and_monkeypatchable(monkeypatch):
    assert over_budget(199.9) is False
    assert over_budget(200.0) is False  # 경계는 초과가 아니다("누적 > BUDGET_MS")
    assert over_budget(200.1) is True
    monkeypatch.setattr("millie_rec.serving.fallback.BUDGET_MS", 1)
    assert over_budget(1.5) is True
    assert over_budget(0.5) is False


def test_segment_popular_filters_category_and_seen_sorted():
    items = segment_popular(_Cat(), UserState(None, explicit_seeds=(2,)), ("소설",), 3)
    assert [i.book_id for i in items] == [4, 6, 8]
    assert all(i.source == SOURCE_POPULARITY for i in items)
    assert all(i.source_channels == (SOURCE_POPULARITY,) for i in items)
    assert [i.position for i in items] == [0, 1, 2]
    assert [i.score for i in items] == [3.0, 2.0, 1.0]


def test_segment_popular_empty_categories_is_global_and_none_catalog_empty():
    user = UserState(None, explicit_seeds=(2,))
    assert [i.book_id for i in segment_popular(_Cat(), user, (), 3)] == [1, 3, 4]
    assert segment_popular(_Cat(), user, ("없음",), 3) == []
    assert segment_popular(None, user, ("소설",), 3) == []


# ── 안전성 ──────────────────────────────────────────────────────────────
def test_global_popular_fallback_regression_unchanged():
    items = GlobalPopularFallback(_Cat()).recommend(UserState(None, explicit_seeds=(1,)), k=10)
    assert [i.book_id for i in items] == [2, 3, 4, 5, 6, 7, 8, 9, 10]
    assert all(i.source == SOURCE_POPULARITY for i in items)
    assert list(inspect.signature(GlobalPopularFallback.recommend).parameters) == [
        "self",
        "user",
        "k",
    ]
    assert trending_row([]).channel_mix == {}
    assert (TRENDING_ROW_ID, TRENDING_TITLE, TRENDING_PURPOSE, SOURCE_POPULARITY) == (
        "trending",
        "지금 많이 읽는 책",
        "fallback",
        "popularity",
    )


def test_cache_is_thread_safe_under_parallel_put():
    c = Level1Cache(now=lambda: T0)
    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(lambda i: c.put(f"u{i}", "snap_1", "hybrid", (_row([i]),), "v1"), range(200)))
    assert len(c) == 200


def test_segment_popular_never_returns_seen():
    user = UserState(None, explicit_seeds=(2, 4), history=(6,))
    items = segment_popular(_Cat(), user, ("소설",), 5)
    ids = [i.book_id for i in items]
    assert ids == [8, 10]
    assert set(ids) & user.seen == set()
