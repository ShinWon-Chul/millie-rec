"""소형 합성 데이터. 실데이터 대신 모든 슬라이스 테스트가 이것을 쓴다."""

import numpy as np
import pandas as pd
import pytest

from millie_rec.contracts import COL_EVENT, COL_ITEM, COL_RATING, COL_TS, COL_USER, SEED

N_USERS, N_ITEMS, N_ROWS = 20, 50, 400


@pytest.fixture(scope="session")
def interactions() -> pd.DataFrame:
    """유저 20 × 아이템 50, ts 오름차순. 인기도 편향을 줘 popularity 가 의미 있게."""
    rng = np.random.default_rng(SEED)
    p = rng.dirichlet(np.ones(N_ITEMS) * 0.3)
    df = pd.DataFrame(
        {
            COL_USER: rng.integers(0, N_USERS, N_ROWS),
            COL_ITEM: rng.choice(N_ITEMS, N_ROWS, p=p),
            COL_TS: pd.to_datetime("2020-01-01")
            + pd.to_timedelta(np.sort(rng.integers(0, 365, N_ROWS)), "D"),
            COL_EVENT: "completion",
            COL_RATING: rng.integers(1, 6, N_ROWS).astype(float),
        }
    )
    return df.drop_duplicates([COL_USER, COL_ITEM]).reset_index(drop=True)


@pytest.fixture(scope="session")
def item_vectors() -> np.ndarray:
    """아이템 50 × 8 차원 콘텐츠 벡터 (ILD·MMR 테스트용)."""
    rng = np.random.default_rng(SEED)
    return rng.random((N_ITEMS, 8))
