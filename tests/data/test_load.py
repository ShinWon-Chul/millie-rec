"""Track A parquet 읽기 + 최소 상호작용 필터(유저>=5 · 아이템>=5, data.md Track A 규칙)."""

import pandas as pd

from millie_rec.contracts import COL_EVENT, COL_ITEM, COL_RATING, COL_TS, COL_USER
from millie_rec.data.load import filter_min_interactions, load_books, load_interactions


# ── 정확성 ──────────────────────────────────────────────────────────────────
def test_filter_min_interactions_hand_case():
    rows = [(u, i) for u in range(1, 6) for i in range(1, 6)] + [(6, 6), (1, 7)]
    df = pd.DataFrame(rows, columns=[COL_USER, COL_ITEM])
    df[COL_RATING] = 5.0
    out = filter_min_interactions(df)
    assert len(out) == 25
    assert set(out[COL_USER]) == {1, 2, 3, 4, 5}
    assert set(out[COL_ITEM]) == {1, 2, 3, 4, 5}


# ── 계약 ────────────────────────────────────────────────────────────────────
def test_load_functions_read_parquet_as_is(tmp_path):
    cols = [COL_USER, COL_ITEM, COL_TS, COL_EVENT, COL_RATING]
    inter = pd.DataFrame(
        {COL_USER: [1], COL_ITEM: [2], COL_TS: [None], COL_EVENT: ["rating"], COL_RATING: [5.0]}
    )
    books = pd.DataFrame({COL_ITEM: [2], "title": ["t"], "authors": ["a"]})
    ip, bp = tmp_path / "i.parquet", tmp_path / "b.parquet"
    inter.to_parquet(ip, index=False)
    books.to_parquet(bp, index=False)
    assert list(load_interactions(ip).columns) == cols
    assert list(load_books(bp).columns) == [COL_ITEM, "title", "authors"]
