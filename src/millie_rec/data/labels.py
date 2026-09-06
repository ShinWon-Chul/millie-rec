"""라벨 계층 한 곳 — Goodbooks positive = rating >= 4. 미선택 책은 negative 가 아니다.

근거: 결정 '착수 전 운영 결정 4건'
(../.assets/개발일지/2026-09-04_Day0.5_브레인스토밍과_데모명세.md 항목 D45).
"""

import pandas as pd

from millie_rec.contracts import COL_ITEM, COL_RATING, COL_USER

POSITIVE_MIN_RATING = 4.0  # CONTEXT D-05. PDF 각주


def is_positive(df: pd.DataFrame) -> pd.Series:
    """만족(라벨) 판정 — 소비(읽음)와 구분한다."""
    return df[COL_RATING] >= POSITIVE_MIN_RATING


def relevant_sets(test: pd.DataFrame) -> dict[int, frozenset[int]]:
    """유저별 정답 집합 R_u = test 구간의 긍정만. 긍정이 없는 유저는 키가 없다."""
    pos = test[is_positive(test)]
    return {
        int(user): frozenset(int(i) for i in items)
        for user, items in pos.groupby(COL_USER)[COL_ITEM]
    }
