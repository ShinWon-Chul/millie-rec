"""Track A 라벨 — rating>=4 만 긍정.

근거: 결정 '착수 전 운영 결정 4건'
(../.assets/개발일지/2026-09-04_Day0.5_브레인스토밍과_데모명세.md 항목 D45).
"""

import pandas as pd

from millie_rec.contracts import COL_ITEM, COL_RATING, COL_USER
from millie_rec.data.labels import is_positive, relevant_sets


# ── 정확성 ──────────────────────────────────────────────────────────────────
def test_is_positive_is_rating_ge_4_only():
    df = pd.DataFrame({COL_RATING: [1.0, 3.0, 4.0, 5.0, 3.9]})
    assert is_positive(df).tolist() == [False, False, True, True, False]


# ── 계약 ────────────────────────────────────────────────────────────────────
def test_relevant_sets_keeps_only_positive_test_items_per_user():
    test = pd.DataFrame({COL_USER: [1, 1, 2], COL_ITEM: [1, 2, 3], COL_RATING: [5.0, 3.0, 2.0]})
    rel = relevant_sets(test)
    assert rel == {1: frozenset({1})}
    assert all(isinstance(v, frozenset) for v in rel.values())
