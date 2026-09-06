"""Goodbooks-10k(Track A) 빌드 — tmp CSV 로만 검증한다. 네트워크 호출 0(CONTEXT D-15).

book_tags.csv 키는 goodreads_book_id — books.csv 로 book_id 매핑이 필수다(함정).
"""

from pathlib import Path

import pandas as pd

from millie_rec.contracts import COL_EVENT, COL_ITEM, COL_RATING, COL_TS, COL_USER
from millie_rec.data.goodbooks import build_goodbooks, download_goodbooks

# 손으로 적은 기대값(구현 상수를 import 하지 않는다)
BOOK_COLUMNS = {
    "book_id",
    "title",
    "authors",
    "image_url",
    "average_rating",
    "ratings_count",
    "original_publication_year",
    "categories",
    "subcategories",
    "tags",
}
RATINGS_CSV = "user_id,book_id,rating\n1,1,5\n1,2,3\n2,1,4\n2,3,2\n1,1,4\n"
BOOKS_CSV = (
    "book_id,goodreads_book_id,authors,original_publication_year,title,"
    "average_rating,ratings_count,image_url\n"
    '1,100,"A. Author",2001,"Book One",4.1,1000,https://x/1.jpg\n'
    '2,200,"B. Author",1999,"Book Two",3.9,500,https://x/2.jpg\n'
    '3,300,"C. Author",,"Book Three",4.5,10,https://x/3.jpg\n'
)
BOOK_TAGS_CSV = (
    "goodreads_book_id,tag_id,count\n100,1,50\n100,2,40\n100,3,30\n100,4,-1\n200,2,10\n200,3,5\n"
)
TAGS_CSV = "tag_id,tag_name\n1,to-read\n2,fantasy\n3,fiction\n4,classics\n"


def _write_raw(raw: Path) -> Path:
    raw.mkdir(parents=True, exist_ok=True)
    (raw / "ratings.csv").write_text(RATINGS_CSV, encoding="utf-8")
    (raw / "books.csv").write_text(BOOKS_CSV, encoding="utf-8")
    (raw / "book_tags.csv").write_text(BOOK_TAGS_CSV, encoding="utf-8")
    (raw / "tags.csv").write_text(TAGS_CSV, encoding="utf-8")
    return raw


# ── 계약 ────────────────────────────────────────────────────────────────────
def test_build_goodbooks_writes_contract_columns_and_null_ts(tmp_path):
    ip, _ = build_goodbooks(
        raw_dir=_write_raw(tmp_path / "goodbooks"), out_dir=tmp_path / "processed"
    )
    inter = pd.read_parquet(ip)
    assert list(inter.columns) == [COL_USER, COL_ITEM, COL_TS, COL_EVENT, COL_RATING]
    assert len(inter) == 4
    assert inter[COL_TS].isna().all()
    assert set(inter[COL_EVENT]) == {"rating"}
    assert inter[COL_RATING].dtype == float


# ── 정확성 ──────────────────────────────────────────────────────────────────
def test_build_goodbooks_maps_goodreads_id_and_drops_noise_tags(tmp_path):
    _, bp = build_goodbooks(
        raw_dir=_write_raw(tmp_path / "goodbooks"), out_dir=tmp_path / "processed"
    )
    books = pd.read_parquet(bp)
    assert BOOK_COLUMNS <= set(books.columns)
    assert len(books) == 3
    tags = books.set_index(COL_ITEM)["tags"]
    assert tags.loc[1] == "fantasy fiction"
    assert tags.loc[2] == "fantasy fiction"
    assert tags.loc[3] == ""


def test_build_goodbooks_dedupes_repeated_user_book_pairs(tmp_path):
    ip, _ = build_goodbooks(
        raw_dir=_write_raw(tmp_path / "goodbooks"), out_dir=tmp_path / "processed"
    )
    inter = pd.read_parquet(ip)
    assert inter.duplicated([COL_USER, COL_ITEM]).sum() == 0
    assert len(inter) == 4
    dup = inter[(inter[COL_USER] == 1) & (inter[COL_ITEM] == 1)]
    assert float(dup[COL_RATING].iloc[0]) == 4.0


# ── 안전성 ──────────────────────────────────────────────────────────────────
def test_download_is_idempotent_when_files_exist(tmp_path, monkeypatch):
    raw = _write_raw(tmp_path / "goodbooks")

    def _boom(*args, **kwargs):
        raise AssertionError("network must not be called")

    monkeypatch.setattr("urllib.request.urlretrieve", _boom)
    paths = download_goodbooks(raw_dir=raw)
    assert len(paths) == 4
    assert all(p.exists() for p in paths)
