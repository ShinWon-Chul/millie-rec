"""MMR 다양성 재순위화 — contracts.Reranker 구현.

풀 MMR_POOL, λ=LAMBDA_MMR, 거리 = 1 − cosine(ItemVectors)(D-07).
"""

from dataclasses import replace

import numpy as np

from millie_rec.contracts import ItemVectors, ScoredItem, UserState

LAMBDA_MMR = 0.7  # D-07. 게이트 미달 시 0.5 로 1회만(Plan 04-05). freeze(D-14 ①)
MMR_POOL = 50  # D-07 hybrid 순위 상위 50 을 풀로


def _minmax(scores: list[float]) -> np.ndarray:
    """풀 안 0~1. 분산 0 이면 전부 1.0(ranking/hybrid._minmax 와 같은 규약 — 중복 정의)."""
    s = np.asarray(scores, dtype=float)
    span = s.max() - s.min()
    return (s - s.min()) / span if span > 0 else np.ones_like(s)


class MMRReranker:
    """상위 pool 을 재배열만 한다 — 새 책·seen 을 넣지 않는다.

    harness 가 seen 반환을 ValueError 로 잡는다.
    """

    def __init__(
        self, vectors: ItemVectors, *, lam: float = LAMBDA_MMR, pool: int = MMR_POOL
    ) -> None:
        self.vectors, self.lam, self.pool = vectors, lam, pool

    def rerank(self, user: UserState, items: list[ScoredItem], k: int) -> list[ScoredItem]:
        head = list(items[: self.pool])
        if len(head) <= 1 or k <= 0:
            return [replace(i, position=n) for n, i in enumerate(head[:k])]
        v = np.asarray(self.vectors.vectors([i.book_id for i in head]), dtype=float)  # 1회 호출
        norms = np.linalg.norm(v, axis=1, keepdims=True)
        unit = v / np.where(norms == 0, 1.0, norms)  # evaluation/metrics.ild_at_k L34-35 그대로
        sim = unit @ unit.T
        rel = _minmax([i.score for i in head])
        n = len(head)
        max_sim = np.zeros(n)  # 선택 집합과의 최대 유사도(누적 갱신 — O(k·pool))
        chosen = np.zeros(n, dtype=bool)
        order: list[int] = []
        for _ in range(min(k, n)):
            mmr = self.lam * rel - (1.0 - self.lam) * max_sim
            mmr[chosen] = -np.inf
            best = int(np.argmax(mmr))  # 동률은 첫 인덱스 = 원 순위(재현성)
            order.append(best)
            chosen[best] = True
            max_sim = np.maximum(max_sim, sim[:, best])
        return [replace(head[i], position=pos) for pos, i in enumerate(order)]
