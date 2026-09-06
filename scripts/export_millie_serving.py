"""processed parquet → artifacts/serving/{books_kr,item_edges_kr,popularity_kr}.json (DATA-07).

적재 계획 §3·§7. 벡터 npz 는 export_millie_vectors.py,
demo/fallback/popular.json 은 export_millie_fallback.py.
description·curator_note 는 TF-IDF 입력 전용이므로 서빙 산출물에 넣지 않는다
(밀리 저작 텍스트 화면·API 미노출 규칙).
"""

import argparse
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

from millie_rec.contracts import DIR_ARTIFACTS, DIR_PROCESSED

MAX_BYTES = 50 * 1024 * 1024
# = data/catalog_kr.py meta() 노출 필드.
# description·curator_note·seg_dist·millie_id 는 넣지 않는다(data.md).
BOOK_FIELDS = (
    "book_id", "title", "authors", "image_url", "average_rating",
    "ratings_count", "original_publication_year", "categories", "subcategories", "tags",
    "publisher", "subtitle", "pub_date", "book_format", "formats",
    "pop_rank", "millie_label", "review_count", "shelf_count", "completion_prob",
    "category_avg_prob", "expected_min", "category_avg_min", "resid_z", "len_z",
    "difficulty", "difficulty_source", "top_segment",
)  # fmt: skip


def _clean(value: object) -> object:
    """pandas NA·NaN → None, numpy 스칼라·배열 → 파이썬 기본형 (parquet 리스트 컬럼은 ndarray)."""
    if isinstance(value, list | tuple | np.ndarray):
        return [_clean(v) for v in value]
    if value is None or value is pd.NA:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    if hasattr(value, "item"):
        return value.item()
    return value


def books_payload(books: pd.DataFrame) -> list[dict]:
    frame = books[list(BOOK_FIELDS)].sort_values("book_id")
    return [{k: _clean(v) for k, v in row.items()} for row in frame.to_dict("records")]


def edges_payload(edges: pd.DataFrame) -> dict[str, list[list]]:
    ordered = edges.sort_values(["src_book_id", "weight"], ascending=[True, False])
    out: dict[str, list[list]] = {}
    for row in ordered.to_dict("records"):
        out.setdefault(str(int(row["src_book_id"])), []).append(
            [int(row["dst_book_id"]), round(float(row["weight"]), 6), str(row["source"])]
        )
    return out


def popularity_payload(pop: pd.DataFrame) -> list[dict]:
    frame = pop.sort_values(["segment", "rank"])
    return [{k: _clean(v) for k, v in row.items()} for row in frame.to_dict("records")]


def _write(path: Path, payload: object) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    size = path.stat().st_size
    assert size < MAX_BYTES, f"{path.name} {size}B ≥ {MAX_BYTES}B — 서빙 산출물 상한 초과"
    return size


def export(
    books_path: Path, edges_path: Path, popularity_path: Path, out_dir: Path
) -> dict[str, int]:
    sizes = {
        "books_kr.json": _write(
            out_dir / "books_kr.json", books_payload(pd.read_parquet(books_path))
        ),
        "item_edges_kr.json": _write(
            out_dir / "item_edges_kr.json", edges_payload(pd.read_parquet(edges_path))
        ),
        "popularity_kr.json": _write(
            out_dir / "popularity_kr.json", popularity_payload(pd.read_parquet(popularity_path))
        ),
    }
    return sizes


def main() -> None:
    ap = argparse.ArgumentParser(description="serving JSON 내보내기")
    ap.add_argument("--books", type=Path, default=DIR_PROCESSED / "books_kr.parquet")
    ap.add_argument("--edges", type=Path, default=DIR_PROCESSED / "item_edges_kr.parquet")
    ap.add_argument("--popularity", type=Path, default=DIR_PROCESSED / "popularity_kr.parquet")
    ap.add_argument("--out", type=Path, default=DIR_ARTIFACTS / "serving")
    args = ap.parse_args()
    for name, size in export(args.books, args.edges, args.popularity, args.out).items():
        print(f"{name} {size / 1024:.1f}KB → {args.out / name}")


if __name__ == "__main__":
    main()
