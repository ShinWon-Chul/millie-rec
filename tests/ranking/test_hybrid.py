"""ranking/hybrid.py blend_channels·HybridRanker — 계약 · 정확성(min-max 손계산·gap 3항) ·
안전성(None 3경로·seen).
"""

import pytest

from millie_rec.contracts import BookStats, Candidate, ScoredItem, UserState
from millie_rec.ranking.hybrid import HybridRanker, blend_channels


def _channels() -> dict[str, list[Candidate]]:
    """min-max 후: cf 1→1.0 2→0.0 · content 2→1.0 3→0.0 · pop 3→1.0(단독). 가중 0.5/0.3/0.2."""
    return {
        "cf": [Candidate(1, "itemknn", 4.0), Candidate(2, "itemknn", 2.0)],
        "content": [Candidate(2, "content", 1.0), Candidate(3, "content", 0.5)],
        "pop": [Candidate(3, "popularity", 10.0)],
    }


class _FakeStats:
    """contracts.BookStatsSource 가짜 — level 과 difficulty 표만."""

    def __init__(self, level: float | None, difficulty: dict[int, float | None]) -> None:
        self.level, self.difficulty = level, difficulty

    def stats(self, book_ids):
        return [
            BookStats(book_id=int(b), difficulty=self.difficulty.get(int(b)), source="millie_index")
            for b in book_ids
        ]

    def user_level(self, user):
        return self.level


U = UserState(None, explicit_seeds=(50,))  # 후보와 겹치지 않는 seed
BASE_SCORES = [0.5, 0.3, 0.2]


# ── 계약 ──
def test_blend_returns_scored_items_sorted_with_positions() -> None:
    items = blend_channels(U, _channels())
    assert [i.book_id for i in items] == [1, 2, 3]
    assert [i.score for i in items] == pytest.approx(BASE_SCORES)
    assert [i.position for i in items] == [0, 1, 2]
    assert all(isinstance(i, ScoredItem) for i in items)


def test_source_channels_and_source_follow_membership_and_max_contribution() -> None:
    """source_channels = 그 책이 들어 있던 채널(정규화 0 이어도 포함). source = 최대 기여 채널."""
    items = blend_channels(U, _channels())
    assert [i.book_id for i in items] == [1, 2, 3]
    assert items[0].source_channels == ("itemknn",)
    assert items[1].source_channels == ("itemknn", "content")
    assert items[2].source_channels == ("content", "popularity")
    assert [i.source for i in items] == ["itemknn", "content", "popularity"]


# ── 정확성 ──
def test_cf_only_weights_drop_other_channels() -> None:
    """cf variant — 가중 없는 슬롯은 후보에서도 빠진다(채널 dict 형태와 무관하게 같은 결과)."""
    a = blend_channels(U, _channels(), weights={"cf": 1.0})
    b = blend_channels(U, {"cf": _channels()["cf"]}, weights={"cf": 1.0})
    assert [i.book_id for i in a] == [1, 2]
    assert [i.book_id for i in b] == [1, 2]
    assert [i.score for i in a] == pytest.approx([1.0, 0.0])
    assert [i.score for i in b] == pytest.approx([1.0, 0.0])


def test_minmax_edges_single_and_constant_channel() -> None:
    single = blend_channels(U, {"pop": [Candidate(9, "popularity", 3.0)]}, weights={"pop": 1.0})
    assert [i.book_id for i in single] == [9]
    assert single[0].score == pytest.approx(1.0)
    flat = blend_channels(
        U,
        {"cf": [Candidate(1, "itemknn", 2.0), Candidate(2, "itemknn", 2.0)]},
        weights={"cf": 1.0},
    )
    assert [i.book_id for i in flat] == [1, 2]  # 동률 → book_id 오름차순
    assert [i.score for i in flat] == pytest.approx([1.0, 1.0])


def test_gap_features_penalize_harder_books_with_negative_weights() -> None:
    """book1 = 0.5 + (−0.1·0.4) + (−0.2·0.4) = 0.38 · book2 gap 0 · book3 결측 → 가중 0."""
    stats = _FakeStats(0.5, {1: 0.9, 2: 0.5, 3: None})
    items = blend_channels(U, _channels(), book_stats=stats)
    assert [i.book_id for i in items] == [1, 2, 3]
    assert [i.score for i in items] == pytest.approx([0.38, 0.3, 0.2])
    assert items[0].difficulty == 0.9
    assert items[2].difficulty is None


def test_n_completed_times_gap_uses_history_length_proxy() -> None:
    """n_completed = len(user.history) 대리값 → 0.38 + (−0.01·2·0.4) = 0.372."""
    u = UserState(None, explicit_seeds=(50,), history=(7, 8))
    items = blend_channels(u, _channels(), book_stats=_FakeStats(0.5, {1: 0.9, 2: 0.5, 3: None}))
    assert [i.book_id for i in items] == [1, 2, 3]
    assert items[0].score == pytest.approx(0.372)


# ── 안전성 ──
def test_missing_stats_level_or_difficulty_means_zero_weight() -> None:
    """① book_stats None ② user_level() None(신규) ③ difficulty 전부 None(결측) → 점수 불변."""
    cases = [
        blend_channels(U, _channels(), book_stats=None),
        blend_channels(U, _channels(), book_stats=_FakeStats(None, {1: 0.9, 2: 0.5, 3: 0.1})),
        blend_channels(U, _channels(), book_stats=_FakeStats(0.5, {1: None, 2: None, 3: None})),
    ]
    for items in cases:
        assert [i.book_id for i in items] == [1, 2, 3]
        assert [i.score for i in items] == pytest.approx(BASE_SCORES)


def test_seen_candidates_are_never_returned() -> None:
    """retriever 가 걸러도 blend 가 한 번 더 막는다(harness 가 seen 반환을 ValueError 로 잡는다)."""
    items = blend_channels(UserState(None, explicit_seeds=(2,)), _channels())
    assert [i.book_id for i in items] == [1, 3]


def test_empty_channels_give_empty_list() -> None:
    assert blend_channels(U, {}) == []
    assert blend_channels(U, {"cf": [], "content": [], "pop": []}) == []


def test_hybrid_ranker_groups_flat_candidates_by_source_slot() -> None:
    """flat 후보를 source → 슬롯으로 묶는다. 매핑에 없는 source("explicit")는 무시."""
    ch = _channels()
    flat = [*ch["cf"], *ch["content"], *ch["pop"], Candidate(4, "explicit", 1.0)]
    ranked = HybridRanker().rank(U, flat)
    assert [i.book_id for i in ranked] == [1, 2, 3]
    assert [i.score for i in ranked] == pytest.approx(BASE_SCORES)
    assert [i.book_id for i in HybridRanker(weights={"cf": 1.0}).rank(U, flat)] == [1, 2]


def test_context_n_completed_overrides_history_proxy_in_gap_term() -> None:
    """D-07: context["n_completed"]=5 → 0.38 + (−0.01·5·0.4) = 0.36(대리값 2 가 아니다)."""
    u = UserState(None, explicit_seeds=(50,), history=(7, 8), context={"n_completed": "5"})
    items = blend_channels(u, _channels(), book_stats=_FakeStats(0.5, {1: 0.9, 2: 0.5, 3: None}))
    assert [i.book_id for i in items] == [1, 2, 3]
    assert items[0].score == pytest.approx(0.38 + (-0.01 * 5 * 0.4))
