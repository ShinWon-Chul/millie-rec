"""reranking/mmr.py — 계약(len·position·집합) · 정확성(2차원 4벡터 손계산·ILD 상승)
· 안전성(빈·k 초과·미지 id·풀 절단·벡터 1회 호출).
"""

import numpy as np
import pytest

from millie_rec.contracts import ScoredItem, UserState
from millie_rec.evaluation.metrics import ild_at_k
from millie_rec.reranking.mmr import MMRReranker


class _Vecs:
    """contracts.ItemVectors 가짜 — 2차원. 미지 id 는 0 벡터. 호출 수를 센다."""

    TABLE = {1: (1.0, 0.0), 2: (1.0, 0.0), 3: (0.0, 1.0), 4: (0.6, 0.8)}

    def __init__(self) -> None:
        self.calls = 0

    def vectors(self, book_ids):
        self.calls += 1
        rows = [self.TABLE.get(int(b), (0.0, 0.0)) for b in book_ids]
        return np.array(rows, dtype=float).reshape(-1, 2)


def _items(ids=(1, 2, 3, 4), scores=(1.0, 0.9, 0.8, 0.7)) -> list[ScoredItem]:
    return [
        ScoredItem(book_id=b, score=s, source="itemknn", position=i, source_channels=("itemknn",))
        for i, (b, s) in enumerate(zip(ids, scores, strict=True))
    ]


U = UserState(None, explicit_seeds=(50,))


# ── 계약 ──
def test_rerank_returns_k_items_with_positions_and_subset() -> None:
    out = MMRReranker(_Vecs()).rerank(U, _items(), 3)
    assert len(out) == 3
    assert [i.position for i in out] == [0, 1, 2]
    assert {i.book_id for i in out} <= {1, 2, 3, 4}
    assert all(isinstance(i, ScoredItem) for i in out)
    assert all(i.source == "itemknn" and i.source_channels == ("itemknn",) for i in out)
    original = {i.book_id: i.score for i in _items()}
    assert all(i.score == original[i.book_id] for i in out)


# ── 정확성 ──
def test_hand_calculated_greedy_order_is_a_c_b() -> None:
    """λ=0.7: a(0.7) → c(0.2333 > b 0.1667 > d −0.18) → b(0.1667 > d −0.24) → d."""
    assert [i.book_id for i in MMRReranker(_Vecs()).rerank(U, _items(), 3)] == [1, 3, 2]
    assert [i.book_id for i in MMRReranker(_Vecs()).rerank(U, _items(), 4)] == [1, 3, 2, 4]


def test_k2_increases_ild_over_original_order() -> None:
    out = MMRReranker(_Vecs()).rerank(U, _items(), 2)
    assert [i.book_id for i in out] == [1, 3]
    v = _Vecs()
    assert ild_at_k(v.vectors([1, 2]), 2) == pytest.approx(0.0)
    assert ild_at_k(v.vectors([i.book_id for i in out]), 2) == pytest.approx(1.0)


def test_lambda_1_keeps_relevance_order() -> None:
    out = MMRReranker(_Vecs(), lam=1.0).rerank(U, _items(), 4)
    assert [i.book_id for i in out] == [1, 2, 3, 4]


# ── 안전성 ──
def test_empty_and_short_inputs() -> None:
    r = MMRReranker(_Vecs())
    assert r.rerank(U, [], 5) == []
    assert len(r.rerank(U, _items(), 10)) == 4
    one = r.rerank(U, _items((7,), (1.0,)), 3)
    assert len(one) == 1
    assert one[0].position == 0


def test_unknown_ids_zero_vectors_do_not_raise() -> None:
    items = _items((1, 99, 3), (1.0, 0.9, 0.8))
    out = MMRReranker(_Vecs()).rerank(U, items, 3)
    assert len(out) == 3
    assert {i.book_id for i in out} == {1, 99, 3}


def test_pool_truncates_candidates() -> None:
    out = MMRReranker(_Vecs(), pool=2).rerank(U, _items(), 3)
    assert len(out) == 2
    assert {i.book_id for i in out} == {1, 2}


def test_vectors_called_once_per_rerank() -> None:
    v = _Vecs()
    MMRReranker(v).rerank(U, _items(), 3)
    assert v.calls == 1
