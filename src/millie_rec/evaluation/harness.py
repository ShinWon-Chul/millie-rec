"""contracts.Pipeline 하나를 유저 목록에서 평가 → EvalResult.

test 라벨은 UserState 에 절대 넣지 않는다(evaluation.md 누수 방지).
"""

from collections.abc import Sequence
from datetime import UTC, datetime

import numpy as np

from millie_rec.contracts import (
    K_RANK,
    K_RECALL,
    MODEL_VERSION_SUFFIX,
    SEED,
    EvalResult,
    ItemVectors,
    Pipeline,
    UserState,
)
from millie_rec.evaluation.metrics import ild_at_k, ndcg_at_k, recall_at_k

EvalUser = tuple[UserState, frozenset[int]]  # (추천 입력, 정답 R_u). R_u 는 하네스만 본다


def _mean(xs: list[float]) -> float:
    return float(np.mean(xs)) if xs else 0.0


def evaluate(
    pipeline: Pipeline,
    users: Sequence[EvalUser],
    vectors: ItemVectors,
    *,
    k_recall: int = K_RECALL,
    k_rank: int = K_RANK,
) -> EvalResult:
    """유저 루프는 여기만 허용(python.md). 예외는 숨기지 않는다 — 숫자 출처."""
    recalls: list[float] = []
    ndcgs: list[float] = []
    ilds: list[float] = []
    for user, relevant in users:
        leaked = user.seen & relevant
        if leaked:
            raise ValueError(f"leak: user {user.user_id} seen ∩ R_u = {sorted(leaked)[:5]}")
        ranked = [i.book_id for i in pipeline.recommend(user, k_recall)]
        returned_seen = user.seen.intersection(ranked)
        if returned_seen:
            raise ValueError(
                f"{pipeline.name} returned seen items for user {user.user_id}: "
                f"{sorted(returned_seen)[:5]}"
            )
        recalls.append(recall_at_k(ranked, relevant, k_recall))
        ndcgs.append(ndcg_at_k(ranked, relevant, k_rank))
        ilds.append(ild_at_k(vectors.vectors(ranked[:k_rank]), k_rank))
    return EvalResult(
        variant=pipeline.name,
        recall=_mean(recalls),
        ndcg=_mean(ndcgs),
        ild=_mean(ilds),
        n_users=len(users),
        k_recall=k_recall,
        k_rank=k_rank,
        seed=SEED,
        model_version=f"{pipeline.name}{MODEL_VERSION_SUFFIX}",
        created_at=datetime.now(UTC).isoformat(timespec="seconds"),
    )
