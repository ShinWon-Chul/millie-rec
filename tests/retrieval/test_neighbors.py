"""이웃 → 후보 공용 함수 — 계약(Candidate·source·정렬) · 정확성(성분 가중 손계산)
· 안전성(k 상한·이웃 없음·seen 제외).
"""

import pytest

from millie_rec.contracts import Candidate, UserState
from millie_rec.retrieval.neighbors import (
    NeighborRetriever,
    component_weights,
    retrieve_from_neighbors,
    weighted_items,
)


class _Nbrs:
    """contracts.Neighbors 가짜 — 상속 없이 메서드만(test_harness.py::_OneHot 관례)."""

    TABLE = {
        1: [(2, 1.0), (3, 0.5)],
        2: [(1, 1.0), (3, 0.5)],
        3: [(1, 0.5), (2, 0.5)],
        4: [],
    }

    def neighbors(self, book_id: int, n: int = 20) -> list[tuple[int, float]]:
        return self.TABLE.get(int(book_id), [])[:n]


# ── 계약 ──
def test_retrieve_from_neighbors_returns_content_candidates_sorted() -> None:
    out = retrieve_from_neighbors(
        _Nbrs(), UserState(None, explicit_seeds=(1,)), k=5, source="content"
    )
    assert [c.book_id for c in out] == [2, 3]
    assert [c.score for c in out] == [1.0, 0.5]
    assert all(isinstance(c, Candidate) and c.source == "content" for c in out)


def test_neighbor_retriever_name_and_source() -> None:
    assert NeighborRetriever.name == "content"
    out = NeighborRetriever(_Nbrs()).retrieve(UserState(None, explicit_seeds=(1,)), 5)
    assert [c.book_id for c in out] == [2, 3]
    knn = NeighborRetriever(_Nbrs(), source="itemknn").retrieve(
        UserState(None, explicit_seeds=(1,)), 5
    )
    assert knn[0].source == "itemknn"


# ── 정확성 ──
def test_history_component_adds_to_score_when_weights_none() -> None:
    """weights None → α=β=γ=1.0. 3 은 1·2 양쪽 이웃이라 0.5 + 0.5 = 1.0."""
    out = retrieve_from_neighbors(_Nbrs(), UserState(None, explicit_seeds=(1,), history=(2,)), k=5)
    assert [c.book_id for c in out] == [3]
    assert out[0].score == pytest.approx(1.0)


def test_weights_callable_scales_components() -> None:
    user = UserState(None, explicit_seeds=(1,), history=(2,))
    out = retrieve_from_neighbors(
        _Nbrs(), user, k=5, weights=lambda u: {"alpha": 1.0, "beta": 0.0, "gamma": 0.0}
    )
    assert [c.book_id for c in out] == [3]
    assert out[0].score == pytest.approx(0.5)
    assert component_weights(UserState(None), None) == {"alpha": 1.0, "beta": 1.0, "gamma": 1.0}
    mixed = UserState(None, explicit_seeds=(1,), history=(2, 3), session=(4,))
    assert weighted_items(mixed, {"alpha": 1.0, "beta": 0.5, "gamma": 0.1}) == [
        (1, 1.0),
        (2, 0.5),
        (3, 0.5),
        (4, 0.1),
    ]


# ── 안전성 ──
def test_k_limits_and_no_neighbors_gives_empty() -> None:
    assert len(retrieve_from_neighbors(_Nbrs(), UserState(None, explicit_seeds=(1,)), k=1)) == 1
    assert retrieve_from_neighbors(_Nbrs(), UserState(None, explicit_seeds=(4,)), k=5) == []
    assert retrieve_from_neighbors(_Nbrs(), UserState(None), k=5) == []


def test_seen_never_returned() -> None:
    user = UserState(None, explicit_seeds=(1,), history=(2, 3))
    assert retrieve_from_neighbors(_Nbrs(), user, k=5) == []
