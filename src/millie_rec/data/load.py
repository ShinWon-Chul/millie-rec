"""Track A parquet 읽기 + 최소 상호작용 필터(유저>=5 · 아이템>=5 — data.md Track A 규칙)."""

from pathlib import Path

import pandas as pd

from millie_rec.contracts import COL_ITEM, COL_USER, DIR_PROCESSED

INTERACTIONS_FILE = "interactions.parquet"
BOOKS_FILE = "books.parquet"
MIN_USER_INTERACTIONS = 5  # D-01 적격 필터. PDF 각주
MIN_ITEM_INTERACTIONS = 5


def load_interactions(path: Path = DIR_PROCESSED / INTERACTIONS_FILE) -> pd.DataFrame:
    """Track A 상호작용 parquet 을 그대로 읽는다."""
    return pd.read_parquet(path)


def load_books(path: Path = DIR_PROCESSED / BOOKS_FILE) -> pd.DataFrame:
    """Track A 도서 메타 parquet 을 그대로 읽는다."""
    return pd.read_parquet(path)


def filter_min_interactions(
    df: pd.DataFrame,
    *,
    min_user: int = MIN_USER_INTERACTIONS,
    min_item: int = MIN_ITEM_INTERACTIONS,
) -> pd.DataFrame:
    """유저·아이템 최소 상호작용을 동시에 만족할 때까지 반복 필터(벡터화)."""
    while True:
        n = len(df)
        user_counts = df[COL_USER].value_counts()
        item_counts = df[COL_ITEM].value_counts()
        keep = (df[COL_USER].map(user_counts) >= min_user) & (
            df[COL_ITEM].map(item_counts) >= min_item
        )
        df = df[keep]
        if len(df) == n:
            break
    return df.reset_index(drop=True)
