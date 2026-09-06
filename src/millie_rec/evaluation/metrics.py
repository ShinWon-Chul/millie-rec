"""3지표 순수 함수 — evaluation.md 지표 정의 그대로. 유저 평균은 harness.py."""

import math
from collections.abc import Sequence, Set

import numpy as np

from millie_rec.contracts import K_RANK, K_RECALL


def recall_at_k(ranked: Sequence[int], relevant: Set[int], k: int = K_RECALL) -> float:
    """|L_u[:k] ∩ R_u| / |R_u|. 분모를 min(|R_u|, k) 로 바꾸지 않는다(evaluation.md)."""
    if not relevant:
        return 0.0
    hits = sum(1 for b in ranked[:k] if b in relevant)
    return hits / len(relevant)


def ndcg_at_k(ranked: Sequence[int], relevant: Set[int], k: int = K_RANK) -> float:
    """이진 gain, 할인 1/log2(i+1)(i 1-based), IDCG 는 min(|R_u|, k) 개 기준."""
    if not relevant:
        return 0.0
    dcg = sum(1.0 / math.log2(i + 2) for i, b in enumerate(ranked[:k]) if b in relevant)
    idcg = sum(1.0 / math.log2(i + 2) for i in range(min(len(relevant), k)))
    return dcg / idcg if idcg > 0 else 0.0


def ild_at_k(vectors: np.ndarray, k: int = K_RANK) -> float:
    """상위 k 아이템 모든 쌍 (1 − cosine) 평균. 쌍이 없으면 0. 0 벡터의 cosine 은 0(거리 1)."""
    v = np.asarray(vectors, dtype=float)[:k]
    n = v.shape[0]
    if n < 2:
        return 0.0
    norms = np.linalg.norm(v, axis=1, keepdims=True)
    unit = v / np.where(norms == 0, 1.0, norms)
    cos = unit @ unit.T
    iu = np.triu_indices(n, k=1)
    return float(np.mean(1.0 - cos[iu]))
