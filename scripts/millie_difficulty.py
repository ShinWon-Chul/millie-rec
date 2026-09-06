"""completion_prob·expected_min → resid_z·len_z·difficulty (DATA-04, 적재 계획 02 §4 C-2).

resid_z = z_분야(P_완독 − E[P_완독 | 셀, expected_min 분위]), len_z = z_분야(expected_min),
difficulty = σ(−resid_z) = 1/(1+exp(resid_z)).
len_z 는 합성에 넣지 않는다("긴 책 = 어려운 책" 회귀 방지).
"""

import numpy as np
import pandas as pd

N_QUANTILES = 4  # expected_min 분야별 4분위 (03-CONTEXT "난이도 파생 세부")
MIN_CATEGORY_SAMPLE = 20  # 분야 측정 표본 미달 → 전역 분위·전역 셀
MIN_Z_SAMPLE = 5  # 분야 표본 <5 또는 std=0 → 전역 std
CATEGORY_COL = "categories"  # 리스트 컬럼 — 분야 = categories[0]
SOURCE_MEASURED = "millie_index"
NEW_COLUMNS = ("resid_z", "len_z", "difficulty")
NO_CATEGORY = "_none"  # categories 가 빈 리스트인 행
GLOBAL_KEY = "_global"  # 측정 표본이 적은 분야가 쓰는 전역 셀
NO_LEN_BIN = -1  # expected_min 결측 행의 분위 라벨

# 소표본 분야의 기대값은 "전 카탈로그 같은 길이 분위의 평균"이다 — 분야 자체 셀을 쓰면
# 3권 분야의 잔차가 전부 0 이 되어 σ(0)=0.5 로 뭉치기 때문(Claude's Discretion, 03-CONTEXT).
# measured 이면서 expected_min 이 결측인 행은 (분야, -1) 셀로 따로 묶는다.


def _category(value: object) -> str | None:
    """categories 리스트의 첫 원소 = 분야(test_millie_edges._same_category_share 와 같은 규칙)."""
    seq = list(value) if isinstance(value, list | tuple | np.ndarray) else []
    return str(seq[0]) if seq else None


def _bins(x: pd.Series, q: int = N_QUANTILES) -> pd.Series:
    """분위 라벨 0..q-1. rank(method='first') 로 동률을 깬다. 표본 < q 면 전부 0."""
    if x.notna().sum() < q:
        return pd.Series(0, index=x.index, dtype="int64")
    return pd.qcut(x.rank(method="first"), q, labels=False).astype("int64")


def _zscore(x: pd.Series, group: pd.Series, min_n: int = MIN_Z_SAMPLE) -> pd.Series:
    """분야 내 z. 분야 표본 < min_n 또는 std 가 0/NaN 이면 분야 평균 − 전역 std(ddof=1)."""
    g = x.groupby(group)
    mean, std, n = g.transform("mean"), g.transform("std"), g.transform("count")
    std = std.where((n >= min_n) & (std > 0), x.std())
    z = (x - mean) / std
    return z.where(std > 0, 0.0)


def add_difficulty(books: pd.DataFrame) -> pd.DataFrame:
    """resid_z·len_z·difficulty 3컬럼 추가. 입력은 build_frame 결과."""
    df = books.copy()
    cat = df[CATEGORY_COL].map(_category).fillna(NO_CATEGORY)
    prob = pd.to_numeric(df["completion_prob"], errors="coerce").astype(float)
    emin = pd.to_numeric(df["expected_min"], errors="coerce").astype(float)
    measured = (df["difficulty_source"] == SOURCE_MEASURED) & prob.notna()

    # ① expected_min 분위 — 분야 측정 표본 ≥ MIN_CATEGORY_SAMPLE 이면 분야 내, 아니면 전역
    m = measured & emin.notna()
    big = cat[m].map(cat[m].value_counts()) >= MIN_CATEGORY_SAMPLE
    cat_bins = emin[m].groupby(cat[m]).transform(_bins)
    global_bins = _bins(emin[m])
    bins = pd.Series(NO_LEN_BIN, index=df.index, dtype="int64")
    bins[m] = cat_bins.where(big, global_bins)
    cell = pd.Series(NO_CATEGORY, index=df.index, dtype="object")
    cell[measured] = cat[measured]
    cell[m] = cat[m].where(big, GLOBAL_KEY)

    # ② E[P_완독 | 셀, 분위] = 셀 평균 → 잔차
    expected = prob[measured].groupby([cell[measured], bins[measured]]).transform("mean")
    resid = prob[measured] - expected

    # ③ 분야 내 z — resid 는 measured 만, len_z 는 expected_min 이 있는 전 행
    resid_z = pd.Series(0.0, index=df.index)
    resid_z[measured] = _zscore(resid, cat[measured])
    len_z = pd.Series(np.nan, index=df.index)
    has_len = emin.notna()
    len_z[has_len] = _zscore(emin[has_len], cat[has_len])
    difficulty = pd.Series(np.nan, index=df.index)
    difficulty[measured] = 1.0 / (1.0 + np.exp(resid_z[measured]))  # σ(−resid_z)

    df["resid_z"], df["len_z"], df["difficulty"] = resid_z, len_z, difficulty
    return df
