"""3지표 순수 함수 — evaluation.md 지표 정의 손계산.

Recall 분모 |R_u| · NDCG 이진 IDCG=min(|R_u|,K) · ILD 1−cosine 쌍 평균.
"""

import math

import numpy as np
import pytest

from millie_rec.evaluation.metrics import ild_at_k, ndcg_at_k, recall_at_k

LOG2_3 = math.log2(3)


# ── 정확성 ──
def test_recall_hand_cases() -> None:
    assert recall_at_k([1, 2, 3], {2, 9}, 3) == 0.5
    assert recall_at_k([1, 2, 3], {3}, 2) == 0.0
    assert recall_at_k([1, 2, 3], set(), 3) == 0.0
    assert recall_at_k([], {1}, 3) == 0.0
    assert recall_at_k([1, 2, 3, 4], {1, 2, 3, 4, 5, 6}, 4) == pytest.approx(4 / 6)


def test_recall_denominator_is_relevant_size_not_min_k() -> None:
    """분모는 |R_u|=6 이지 min(|R_u|, K)=4 가 아니다(evaluation.md)."""
    assert recall_at_k([1, 2, 3, 4], {1, 2, 3, 4, 5, 6}, 4) == pytest.approx(4 / 6)


def test_ndcg_hand_cases() -> None:
    assert ndcg_at_k([1, 2, 3], {1}, 3) == 1.0
    assert ndcg_at_k([1, 2, 3], {2}, 3) == pytest.approx(1 / LOG2_3)
    assert ndcg_at_k([1, 2, 3], {2, 9}, 3) == pytest.approx((1 / LOG2_3) / (1 + 1 / LOG2_3))
    assert ndcg_at_k([9], {1}, 3) == 0.0
    assert ndcg_at_k([1, 2, 3], set(), 3) == 0.0
    assert ndcg_at_k([1, 2, 3], {3}, 2) == 0.0


def test_ild_hand_cases() -> None:
    assert ild_at_k(np.array([[1.0, 0.0], [0.0, 1.0]]), 2) == 1.0
    assert ild_at_k(np.array([[1.0, 0.0], [1.0, 0.0]]), 2) == 0.0
    assert ild_at_k(np.array([[1.0, 0.0], [0.0, 1.0], [1.0, 0.0]]), 3) == pytest.approx(2 / 3)
    assert ild_at_k(np.array([[2.0, 0.0], [0.0, 3.0]]), 2) == 1.0
    assert ild_at_k(np.array([[1.0, 0.0], [0.0, 1.0], [1.0, 0.0]]), 2) == 1.0


# ── 안전성(경계) ──
def test_metrics_empty_and_k1_edges() -> None:
    assert recall_at_k([], {1}, 3) == 0.0
    assert ndcg_at_k([1, 2, 3], set(), 3) == 0.0
    assert ild_at_k(np.array([[1.0, 0.0]]), 1) == 0.0
    assert ild_at_k(np.zeros((0, 2)), 5) == 0.0


def test_ild_zero_vector_counts_as_distance_one() -> None:
    assert ild_at_k(np.array([[0.0, 0.0], [1.0, 0.0]]), 2) == 1.0


# ── 계약 ──
def test_ild_on_fixture_is_strictly_between_0_and_1(item_vectors) -> None:
    value = ild_at_k(item_vectors[:10], 10)
    assert 0.0 < value < 1.0
    assert isinstance(value, float)
