"""폴백 2단계 = 연령×성별 세그먼트 인기 — 추정(다수결) · 순위(세그먼트 rank) · 폴백의 폴백.

segpop 이 없으면 기존 카테고리 인기와 완전히 같아야 한다(회귀는 test_fallback_levels.py).
"""

from collections.abc import Sequence

from millie_rec.contracts import UserState
from millie_rec.serving import segment
from millie_rec.serving.fallback import (
    SEG_POOL_FACTOR,
    SEG_POOL_FACTOR_CAT,
    SOURCE_POPULARITY,
    segment_popular,
)

SEG_A, SEG_B = "30대 여성", "40대 남성"


class _Cat:
    """가짜 Catalog — meta 는 top_segment + categories, eligible 은 9 를 자격 미달로 뺀다."""

    SEG = {1: SEG_A, 2: SEG_B, 3: SEG_A, 4: None}
    CATS = {1: ["소설"], 2: ["인문"], 3: ["소설"], 5: ["소설"], 7: ["소설"], 9: ["소설"]}

    def __init__(self) -> None:
        self.meta_calls = 0

    def meta(self, book_ids: Sequence[int]) -> list[dict]:
        self.meta_calls += 1
        return [
            {"book_id": b, "top_segment": self.SEG.get(b), "categories": self.CATS.get(b)}
            for b in book_ids
        ]

    def popular(self, categories: Sequence[str] = (), n: int = 50) -> list[int]:
        if not categories:
            return list(range(1, 11))[:n]
        if tuple(categories) == ("소설",):
            return [2, 4, 6, 8, 10][:n]
        return []

    def eligible(self, book_ids: Sequence[int]) -> list[int]:
        return [b for b in book_ids if b != 9]


class _SegPop:
    """가짜 SegmentPopularity — ranked 만. 호출 인자를 기록한다."""

    def __init__(self, table: dict[str, list[int]]) -> None:
        self.table, self.calls = table, []

    def ranked(self, seg: str, n: int) -> list[int]:
        self.calls.append((seg, n))
        return self.table.get(seg, [])[:n]


# ── 계약 ────────────────────────────────────────────────────────────────
def test_estimate_majority_segment_of_seeds():
    metas = [{"top_segment": SEG_A}, {"top_segment": SEG_B}, {"top_segment": SEG_A}]
    assert segment.estimate(metas) == SEG_A
    assert segment.KEY_TOP_SEGMENT == "top_segment"


def test_estimate_ignores_missing_and_all_missing_is_none():
    assert segment.estimate([{"top_segment": SEG_B}, {}, {"top_segment": None}]) == SEG_B
    assert segment.estimate([{}, {"top_segment": None}]) is None
    assert segment.estimate([]) is None


def test_estimate_tie_breaks_alphabetically_min():
    tie = [{"top_segment": SEG_B}, {"top_segment": SEG_A}]
    assert segment.estimate(tie) == min(SEG_A, SEG_B)
    assert segment.estimate(list(reversed(tie))) == min(SEG_A, SEG_B)  # 입력 순서와 무관


# ── 정확성 ──────────────────────────────────────────────────────────────
def test_segment_popular_uses_segment_rank_order_not_pop_rank():
    sp = _SegPop({SEG_A: [7, 3, 5, 1]})
    items = segment_popular(_Cat(), UserState(None), ("소설",), 3, segpop=sp, segment=SEG_A)
    assert [i.book_id for i in items] == [7, 3, 5]  # popular("소설") = [2, 4, 6, 8, 10] 이 아니다
    assert sp.calls == [(SEG_A, 3 * SEG_POOL_FACTOR_CAT)]  # 카테고리까지 거를 만큼 넓게
    assert [i.position for i in items] == [0, 1, 2]
    assert [i.score for i in items] == [3.0, 2.0, 1.0]
    assert all(i.source == SOURCE_POPULARITY for i in items)
    assert all(i.source_channels == (SOURCE_POPULARITY,) for i in items)


def test_segment_popular_excludes_seen_from_segment_pool():
    sp = _SegPop({SEG_A: [7, 3, 5, 1]})
    user = UserState(None, explicit_seeds=(7,), history=(5,))
    items = segment_popular(_Cat(), user, (), 3, segpop=sp, segment=SEG_A)
    ids = [i.book_id for i in items]
    assert ids == [3, 1]
    assert set(ids) & user.seen == set()


def test_segment_popular_drops_ineligible_from_segment_pool():
    sp = _SegPop({SEG_A: [9, 7, 3]})
    items = segment_popular(_Cat(), UserState(None), (), 3, segpop=sp, segment=SEG_A)
    assert [i.book_id for i in items] == [7, 3]  # 9 는 eligible 탈락


# ── 안전성 ──────────────────────────────────────────────────────────────
def test_segment_popular_empty_segment_flows_to_category_popular():
    sp = _SegPop({SEG_A: []})
    items = segment_popular(_Cat(), UserState(None), ("소설",), 3, segpop=sp, segment=SEG_A)
    assert [i.book_id for i in items] == [2, 4, 6]  # 빈 응답을 내지 않는다


def test_segment_popular_all_filtered_flows_to_category_popular():
    sp = _SegPop({SEG_A: [9]})  # 유일한 후보가 자격 미달
    items = segment_popular(_Cat(), UserState(None), ("소설",), 3, segpop=sp, segment=SEG_A)
    assert [i.book_id for i in items] == [2, 4, 6]


def test_segment_popular_without_segpop_or_segment_is_unchanged():
    user = UserState(None, explicit_seeds=(2,))
    base = [i.book_id for i in segment_popular(_Cat(), user, ("소설",), 3)]
    assert base == [4, 6, 8]
    sp = _SegPop({SEG_A: [7, 3, 5]})
    assert [i.book_id for i in segment_popular(_Cat(), user, ("소설",), 3, segpop=sp)] == base
    assert [i.book_id for i in segment_popular(_Cat(), user, ("소설",), 3, segment=SEG_A)] == base
    assert sp.calls == []  # segment 가 없으면 세그먼트 목록을 아예 부르지 않는다


def test_segment_popular_excludes_books_outside_requested_categories():
    """세그먼트 인기가 사용자가 고른 카테고리를 덮지 않는다 — 카테고리 > 세그먼트 > 전역."""
    cat, sp = _Cat(), _SegPop({SEG_A: [2, 7, 108, 3]})  # 2·108 은 인문
    items = segment_popular(cat, UserState(None), ("소설",), 3, segpop=sp, segment=SEG_A)
    assert [i.book_id for i in items] == [7, 3]  # 인문 책은 세그먼트 순위가 높아도 빠진다
    assert cat.meta_calls == 1  # meta 는 한 번만 (p95 예산)


def test_segment_popular_empty_categories_skips_category_filter():
    cat, sp = _Cat(), _SegPop({SEG_A: [2, 7, 108]})
    items = segment_popular(cat, UserState(None), (), 3, segpop=sp, segment=SEG_A)
    assert [i.book_id for i in items] == [2, 7, 108]  # 전역 세그먼트 인기 — 인문도 나온다
    assert cat.meta_calls == 0  # 필터가 없으면 meta 를 아예 부르지 않는다
    assert sp.calls == [(SEG_A, 3 * SEG_POOL_FACTOR)]  # 좁은 풀로 충분하다


def test_segment_popular_category_intersection_empty_flows_to_category_popular():
    sp = _SegPop({SEG_A: [2, 108]})  # 세그먼트 상위가 전부 인문
    items = segment_popular(_Cat(), UserState(None), ("소설",), 3, segpop=sp, segment=SEG_A)
    assert [i.book_id for i in items] == [2, 4, 6]  # 빈 응답 금지 — 카테고리 인기로 흐른다
