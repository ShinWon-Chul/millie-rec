"""Track A 분할 — ts 전부 결측이면 유저별 random holdout, 있으면 전역 temporal(CONTEXT D-02).

거짓으로 temporal 이라 기록하지 않는다는 주장을 테스트 이름으로 남긴다.
"""

import numpy as np
import pandas as pd
import pytest

from millie_rec.contracts import COL_ITEM, COL_RATING, COL_TS, COL_USER
from millie_rec.data.split import split

TEST_FRAC = 0.2  # 구현 상수를 import 하지 않고 손으로 적는다


def _no_ts(interactions: pd.DataFrame) -> pd.DataFrame:
    df = interactions.copy()
    df[COL_TS] = None
    return df


def _pairs(df: pd.DataFrame) -> set[tuple[int, int]]:
    return {(int(u), int(i)) for u, i in zip(df[COL_USER], df[COL_ITEM], strict=True)}


# ── 계약 ────────────────────────────────────────────────────────────────────
def test_holdout_when_ts_missing_records_split_mode_holdout(interactions):
    assert split(_no_ts(interactions)).split_mode == "holdout"


def test_holdout_partitions_each_user_without_overlap(interactions):
    df = _no_ts(interactions)
    s = split(df)
    train, test = _pairs(s.train), _pairs(s.test)
    assert train | test == _pairs(df)
    assert train & test == set()
    sizes = df.groupby(COL_USER).size()
    assert {u for u, _ in test} == {int(u) for u, n in sizes.items() if n >= 2}


# ── 정확성 ──────────────────────────────────────────────────────────────────
def test_holdout_test_size_per_user_is_max1_floor_frac(interactions):
    df = _no_ts(interactions)
    s = split(df)
    sizes = df.groupby(COL_USER).size()
    test_sizes = s.test.groupby(COL_USER).size()
    for user, n in sizes.items():
        if n < 2:
            continue
        assert int(test_sizes.get(user, 0)) == max(1, int(np.floor(n * TEST_FRAC + 1e-9)))


def test_holdout_hand_case_10_rows_gives_2_test_rows():
    df = pd.DataFrame({COL_USER: 1, COL_ITEM: range(1, 11), COL_TS: None, COL_RATING: 5.0})
    s = split(df)
    assert (len(s.train), len(s.test)) == (8, 2)


def test_temporal_split_no_future_leak(interactions):
    s = split(interactions)
    assert s.split_mode == "temporal"
    assert s.train[COL_TS].max() < s.test[COL_TS].min()
    assert len(s.train) + len(s.test) == len(interactions)
    assert len(s.train) > 0 and len(s.test) > 0


# ── 안전성 ──────────────────────────────────────────────────────────────────
def test_split_is_reproducible_and_rejects_partial_ts_and_bad_frac(interactions):
    df = _no_ts(interactions)
    a, b = split(df), split(df)
    assert a.train.equals(b.train) and a.test.equals(b.test)
    partial = interactions.copy()
    partial.loc[partial.index[: len(partial) // 2], COL_TS] = None
    with pytest.raises(ValueError):
        split(partial)
    with pytest.raises(ValueError):
        split(df, test_frac=1.5)
