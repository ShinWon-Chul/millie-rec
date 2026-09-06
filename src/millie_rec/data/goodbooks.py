"""Goodbooks-10k(Track A) 멱등 다운로드 + raw CSV -> parquet 캐시.

데이터 소스 01 §4-1 · CONTEXT D-15. 네트워크는 이 파일에서만.
"""

import logging
import urllib.request
from pathlib import Path

import pandas as pd

from millie_rec.contracts import (
    COL_EVENT,
    COL_ITEM,
    COL_RATING,
    COL_TS,
    COL_USER,
    DIR_PROCESSED,
    DIR_RAW,
)
from millie_rec.data.load import BOOKS_FILE, INTERACTIONS_FILE

log = logging.getLogger(__name__)
# HTTPS 고정. Goodbooks-10k CC BY-SA 4.0 (README 귀속)
GOODBOOKS_URL_BASE = "https://raw.githubusercontent.com/zygmuntz/goodbooks-10k/master/"
FILES = ("ratings.csv", "books.csv", "book_tags.csv", "tags.csv")  # to_read.csv 미사용
RAW_SUBDIR = "goodbooks"
EVENT_RATING = "rating"  # contracts.EVENT_TYPES 안. 데이터 사실 그대로
TOP_TAGS = 20  # D-15: 책별 count 상위 20 태그
# D-15: 서가 관리 잡음 태그 — 안 빼면 거의 모든 책이 같은 태그를 공유해 ILD 가 일괄 눌린다.
NOISE_TAGS = frozenset(
    """to-read currently-reading favorites favourites owned books-i-own owned-books i-own own
    kindle ebook ebooks e-book audiobook audiobooks audible audio audio-books library
    my-library my-books to-buy
    wish-list wishlist default re-read reread borrowed book-club all-time-favorites books series
    dnf did-not-finish abandoned read-in-2014 read-in-2015 read-in-2016 read-in-2017 2014 2015
    2016 2017""".split()
)
# books.csv 이름 그대로 = 계약 컬럼
BOOK_COLS = (
    "book_id",
    "title",
    "authors",
    "image_url",
    "average_rating",
    "ratings_count",
    "original_publication_year",
)
_GOODREADS_ID = "goodreads_book_id"  # book_tags.csv 의 키 — books.csv 로 book_id 에 매핑한다
_TAG_ID, _TAG_NAME, _COUNT = "tag_id", "tag_name", "count"


def download_goodbooks(raw_dir: Path = DIR_RAW / RAW_SUBDIR) -> list[Path]:
    """이미 있고 크기>0 이면 건너뛴다(멱등). 부분 다운로드는 .part 로 받아 교체."""
    raw_dir.mkdir(parents=True, exist_ok=True)
    for name in FILES:
        dst = raw_dir / name
        if dst.exists() and dst.stat().st_size > 0:
            continue
        tmp = dst.with_suffix(".part")
        urllib.request.urlretrieve(GOODBOOKS_URL_BASE + name, tmp)
        tmp.replace(dst)
        log.info("downloaded %s (%d bytes)", name, dst.stat().st_size)
    return [raw_dir / name for name in FILES]


def _interactions(raw_dir: Path) -> pd.DataFrame:
    """ratings.csv -> 계약 5컬럼. ts 는 전부 결측(Goodbooks 에 타임스탬프가 없다)."""
    raw = pd.read_csv(raw_dir / "ratings.csv")
    df = pd.DataFrame(
        {
            COL_USER: raw[COL_USER].astype("int64"),
            COL_ITEM: raw[COL_ITEM].astype("int64"),
            COL_TS: pd.Series([None] * len(raw), dtype="object"),
            COL_EVENT: EVENT_RATING,
            COL_RATING: raw[COL_RATING].astype(float),
        }
    )
    # 같은 (user, book) 이 여러 번 나온다 — 안 지우면 holdout 이 같은 쌍을 train/test 양쪽에 넣는다
    return df.drop_duplicates([COL_USER, COL_ITEM], keep="last").reset_index(drop=True)


def _tags_per_book(raw_dir: Path, books: pd.DataFrame) -> pd.Series:
    """책별 count 상위 TOP_TAGS 개 태그 이름을 공백으로 join. 잡음 태그는 뺀다."""
    book_tags = pd.read_csv(raw_dir / "book_tags.csv")
    tags = pd.read_csv(raw_dir / "tags.csv")
    joined = book_tags[book_tags[_COUNT] > 0].merge(tags, on=_TAG_ID)
    joined = joined[~joined[_TAG_NAME].isin(NOISE_TAGS)]
    joined = joined.merge(books[[COL_ITEM, _GOODREADS_ID]], on=_GOODREADS_ID)
    joined = joined.sort_values([COL_ITEM, _COUNT], ascending=[True, False])
    top = joined.groupby(COL_ITEM).head(TOP_TAGS)
    return top.groupby(COL_ITEM)[_TAG_NAME].agg(" ".join)


def _books(raw_dir: Path) -> pd.DataFrame:
    """books.csv -> 계약 컬럼 + categories/subcategories(빈 리스트) + tags."""
    raw = pd.read_csv(raw_dir / "books.csv")
    out = raw[list(BOOK_COLS)].copy()
    out[COL_ITEM] = out[COL_ITEM].astype("int64")
    out["categories"] = [[] for _ in range(len(out))]  # Goodbooks 엔 분류가 없다(Track A 미사용)
    out["subcategories"] = [[] for _ in range(len(out))]
    out["tags"] = out[COL_ITEM].map(_tags_per_book(raw_dir, raw)).fillna("")
    return out.reset_index(drop=True)


def build_goodbooks(
    raw_dir: Path = DIR_RAW / RAW_SUBDIR, out_dir: Path = DIR_PROCESSED
) -> tuple[Path, Path]:
    """raw CSV 4개 -> interactions.parquet · books.parquet. 경로 2개를 반환."""
    out_dir.mkdir(parents=True, exist_ok=True)
    interactions_path, books_path = out_dir / INTERACTIONS_FILE, out_dir / BOOKS_FILE
    interactions = _interactions(raw_dir)
    books = _books(raw_dir)
    interactions.to_parquet(interactions_path, index=False)
    books.to_parquet(books_path, index=False)
    log.info("built %d interactions, %d books", len(interactions), len(books))
    return interactions_path, books_path
