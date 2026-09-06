"""온보딩 시뮬레이션 — train 긍정 중 seed 고정 무작위 5권만 explicit_seeds, 두 상태 n=0 / n>=k.

main 설계서 §5-2 · CONTEXT D-01·D-03·D-04.
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd

from millie_rec.contracts import COL_ITEM, COL_USER, N_ONBOARD_SEEDS, SEED, UserState
from millie_rec.data.labels import is_positive

K_HISTORY = 20  # D-04: seeds 외 train 행 >=20 인 유저만 n>=k 표. PDF 각주
N_TEST_USERS = 2000  # D-01: 전 variant·전 상태 공통 표본
STATE_N0 = "n0"
STATE_NK = f"n{K_HISTORY}"  # latest_states.csv 의 state 값(D-07)


@dataclass(frozen=True, slots=True)
class OnboardingStates:
    """n0 = seeds 만, n_k = seeds + 나머지 train 이력(>=K_HISTORY 유저만). 두 상태의 정답은 같다."""

    n0: tuple[UserState, ...]
    n_k: tuple[UserState, ...]


def select_test_users(
    train: pd.DataFrame,
    test: pd.DataFrame,
    *,
    n: int = N_TEST_USERS,
    n_seeds: int = N_ONBOARD_SEEDS,
    seed: int = SEED,
) -> tuple[tuple[int, ...], int]:
    """적격 유저(train 긍정 >= n_seeds ∧ test 긍정 >= 1)에서 1회 추출. (유저, 제외 수) 반환."""
    all_users = pd.Index(np.sort(train[COL_USER].unique()))  # 정렬 = groupby 순서 비의존
    train_pos = train[is_positive(train)].groupby(COL_USER).size().reindex(all_users, fill_value=0)
    test_pos = test[is_positive(test)].groupby(COL_USER).size().reindex(all_users, fill_value=0)
    eligible = all_users[(train_pos.to_numpy() >= n_seeds) & (test_pos.to_numpy() >= 1)]
    n_excluded = len(all_users) - len(eligible)
    rng = np.random.default_rng(seed)
    size = min(n, len(eligible))
    chosen = rng.choice(eligible.to_numpy(), size=size, replace=False) if size else []
    return tuple(int(u) for u in np.sort(chosen)), int(n_excluded)


def mask_onboarding(
    train: pd.DataFrame,
    users: tuple[int, ...],
    *,
    n: int = N_ONBOARD_SEEDS,
    k_history: int = K_HISTORY,
    seed: int = SEED,
) -> OnboardingStates:
    """두 상태를 만든다. 미선택 책은 어느 필드에도 부정 신호로 남지 않는다(PRD §9 AC7)."""
    train = train[train[COL_USER].isin(users)]  # 선필터 — 전체 로그에 groupby 를 돌리지 않는다
    rng = np.random.default_rng(seed)
    pos = train[is_positive(train)]
    items_by_user = train.groupby(COL_USER)[COL_ITEM].apply(lambda s: tuple(int(i) for i in s))
    pos_by_user = pos.groupby(COL_USER)[COL_ITEM].apply(list)
    n0: list[UserState] = []
    n_k: list[UserState] = []
    for user in users:  # 유저 루프는 여기만 — 평가 표본(N_TEST_USERS)에 한정
        cand = sorted(int(i) for i in pos_by_user[user])
        seeds = tuple(int(i) for i in sorted(rng.choice(cand, size=n, replace=False)))
        n0.append(UserState(user_id=int(user), explicit_seeds=seeds))
        chosen = set(seeds)
        rest = tuple(i for i in items_by_user[user] if i not in chosen)
        if len(rest) >= k_history:
            n_k.append(UserState(user_id=int(user), explicit_seeds=seeds, history=rest))
    return OnboardingStates(tuple(n0), tuple(n_k))
