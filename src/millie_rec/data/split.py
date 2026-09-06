"""Track A split 함수 하나 — ts 없으면 유저별 random holdout, 있으면 전역 시점 temporal.

data.md Track A · CONTEXT D-02. 거짓으로 temporal 이라 쓰지 않는다.
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd

from millie_rec.contracts import COL_TS, COL_USER, SEED

TEST_FRAC = 0.2  # D-02. PDF 각주
SPLIT_HOLDOUT = "holdout"
SPLIT_TEMPORAL = "temporal"
_KEY = "_key"  # holdout 정렬용 임시 컬럼


@dataclass(frozen=True, slots=True)  # DataFrame 필드 — 식별은 split_mode 문자열
class Split:
    """train / test / 실제로 쓴 분할 방식."""

    train: pd.DataFrame
    test: pd.DataFrame
    split_mode: str


def _temporal(df: pd.DataFrame, test_frac: float) -> tuple[pd.DataFrame, pd.DataFrame]:
    """전역 시점 분할. 경계 동률은 train 으로 보내 누수를 막는다."""
    ts = pd.to_datetime(df[COL_TS])
    cutoff = ts.quantile(1 - test_frac)
    train, test = df[ts <= cutoff], df[ts > cutoff]
    assert train[COL_TS].max() < test[COL_TS].min()  # 누수 단언 (data.md Track A split)
    return train, test


def _holdout(df: pd.DataFrame, test_frac: float, seed: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    """유저별 random holdout. 유저 루프 없이 groupby 로만."""
    rng = np.random.default_rng(seed)
    order = df.assign(**{_KEY: rng.random(len(df))}).sort_values([COL_USER, _KEY], kind="stable")
    size = order.groupby(COL_USER)[COL_USER].transform("size").to_numpy()
    rank = order.groupby(COL_USER).cumcount().to_numpy()
    n_test = np.where(size >= 2, np.maximum(1, np.floor(size * test_frac + 1e-9)), 0).astype(int)
    is_test = rank < n_test
    return order[~is_test].drop(columns=_KEY), order[is_test].drop(columns=_KEY)


def split(df: pd.DataFrame, *, test_frac: float = TEST_FRAC, seed: int = SEED) -> Split:
    """데이터가 분할 방식을 정한다 — 사람이 split_mode 를 고를 수 없다."""
    if not 0 < test_frac < 1:
        raise ValueError(f"test_frac 은 (0, 1) 안이어야 한다: {test_frac}")
    has_ts = COL_TS in df.columns and df[COL_TS].notna().any()
    if has_ts and df[COL_TS].isna().any():
        raise ValueError("ts 가 일부만 결측 — 분할 방식을 정할 수 없다")
    if has_ts:
        train, test = _temporal(df, test_frac)
        mode = SPLIT_TEMPORAL
    else:
        train, test = _holdout(df, test_frac, seed)
        mode = SPLIT_HOLDOUT
    return Split(train.reset_index(drop=True), test.reset_index(drop=True), mode)
