"""이웃 → 후보 공용 함수 + NeighborRetriever(contracts.CandidateGenerator).

Track A ItemKNN·Track B CatalogKR.neighbors 가 같은 함수를 쓴다(D-10, 이중 구현 금지).
"""

from collections.abc import Callable
from typing import TYPE_CHECKING

from millie_rec.contracts import Candidate, Neighbors, UserState

if TYPE_CHECKING:
    import pandas as pd

SOURCE_CONTENT = "content"  # data.md: Track B 이웃 채널 표기. serving/app 과 중복 정의(중복 < 결합)
DEFAULT_WEIGHTS = {"alpha": 1.0, "beta": 1.0, "gamma": 1.0}  # weights 미주입 = 성분 가중 전부 1
N_NEIGHBORS = 20  # 성분 아이템당 읽는 이웃 수 기본값(contracts.Neighbors.n 기본과 동일)
WeightFn = Callable[[UserState], dict[str, float]]  # app 이 ranking.state_weights 를 넘긴다(D-01)


def component_weights(user: UserState, weights: "WeightFn | None") -> dict[str, float]:
    """α/β/γ dict. None 이면 DEFAULT_WEIGHTS 복사 — retrieval 은 ranking 을 import 하지 않는다."""
    return dict(weights(user)) if weights is not None else dict(DEFAULT_WEIGHTS)


def weighted_items(user: UserState, w: dict[str, float]) -> list[tuple[int, float]]:
    """(book_id, α|β|γ) — seeds→alpha, history→beta, session→gamma. 비어 있는 성분은 자연히 없다."""
    return (
        [(int(b), w.get("alpha", 0.0)) for b in user.explicit_seeds]
        + [(int(b), w.get("beta", 0.0)) for b in user.history]
        + [(int(b), w.get("gamma", 0.0)) for b in user.session]
    )


def retrieve_from_neighbors(
    nbrs: Neighbors,
    user: UserState,
    k: int,
    *,
    source: str = SOURCE_CONTENT,
    weights: "WeightFn | None" = None,
    n_neighbors: int = N_NEIGHBORS,
) -> list[Candidate]:
    """Σ_{i∈성분 아이템} w_성분 · sim(i, ·), seen 제외, (−score, book_id) 정렬 상위 k."""
    scores: dict[int, float] = {}
    for b, wc in weighted_items(user, component_weights(user, weights)):
        if wc == 0.0:
            continue
        for nb, sim in nbrs.neighbors(b, n_neighbors):
            if nb in user.seen:
                continue
            scores[nb] = scores.get(nb, 0.0) + wc * float(sim)
    ranked = sorted(scores.items(), key=lambda t: (-t[1], t[0]))[:k]  # 동률은 id 오름차순(재현성)
    return [Candidate(book_id=int(b), source=source, score=float(s)) for b, s in ranked]


class NeighborRetriever:
    """Neighbors 어댑터를 감싼 CandidateGenerator.

    Track B cf 채널(CatalogKR 엣지) 용 — source 는 content(data.md).
    """

    name = SOURCE_CONTENT

    def __init__(
        self,
        neighbors: Neighbors,
        *,
        source: str = SOURCE_CONTENT,
        weights: "WeightFn | None" = None,
        n_neighbors: int = N_NEIGHBORS,
    ) -> None:
        self._nbrs, self._source, self._weights, self._n = neighbors, source, weights, n_neighbors

    def fit(self, train: "pd.DataFrame") -> "NeighborRetriever":
        return self  # 이웃은 주입된 어댑터가 이미 가진다(빌드는 scripts/ 또는 ItemKNN.fit)

    def retrieve(self, user: UserState, k: int) -> list[Candidate]:
        return retrieve_from_neighbors(
            self._nbrs, user, k, source=self._source, weights=self._weights, n_neighbors=self._n
        )
