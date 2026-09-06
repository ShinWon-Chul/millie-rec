"""books_kr.parquet → popularity_kr.parquet (DATA-07 Must: segment='all').

DATA-08 Should 연령×성별 행은 Plan 07 이 같은 파일에 증분(적재 계획 02 §6 행 소스 분리).
"""

import argparse
import json
from pathlib import Path

import pandas as pd

from millie_rec.contracts import DIR_PROCESSED

POP_COLUMNS = ("book_id", "segment", "score", "rank")
SEGMENT_ALL = "all"
SEG_DIST_COL = "seg_dist"  # Plan 07 세그먼트 확장 재료(json 문자열)
# top_segment 표기("40대 여성")와 같은 형식을 만드는 최소 상수.
# 카테고리 매핑표가 아니다(.planning/phases/03-millie-catalog/03-CONTEXT.md "변환 테이블 없음").
GENDER_LABEL = {"남": "남성", "여": "여성"}
SEGMENT_SEP = " "


def segment_rows(books: pd.DataFrame) -> pd.DataFrame:
    """연령×성별 세그먼트 인기(DATA-08 Should) — score = shelf_count × seg_dist[연령][성별].

    rank 는 세그먼트 안에서 score 내림차순(동률은 book_id 오름차순). seg_dist 없는 책은 제외.
    """
    shelf = pd.to_numeric(books["shelf_count"], errors="coerce").astype(float).fillna(0.0)
    rows: list[dict] = []
    ids = books["book_id"].astype("int64")
    for book_id, count, raw in zip(ids, shelf, books[SEG_DIST_COL], strict=True):
        if not isinstance(raw, str) or not raw:
            continue
        for age, by_gender in json.loads(raw).items():
            for gender, share in (by_gender or {}).items():
                label = f"{age}{SEGMENT_SEP}{GENDER_LABEL.get(gender, gender)}"
                score = float(count) * float(share or 0.0)
                rows.append({"book_id": int(book_id), "segment": label, "score": score})
    if not rows:
        return pd.DataFrame(columns=list(POP_COLUMNS))
    seg = pd.DataFrame(rows).sort_values(
        ["segment", "score", "book_id"], ascending=[True, False, True]
    )
    seg["rank"] = seg.groupby("segment").cumcount() + 1
    return seg.reset_index(drop=True)[list(POP_COLUMNS)]


def build(books: pd.DataFrame) -> pd.DataFrame:
    """segment='all' 행 — rank = pop_rank(정본 1곳, 재계산 없음), score = shelf_count(결측 0.0)."""
    shelf = pd.to_numeric(books["shelf_count"], errors="coerce").astype(float).fillna(0.0)
    rows = pd.DataFrame(
        {
            "book_id": books["book_id"].astype("int64"),
            "segment": SEGMENT_ALL,
            "score": shelf,
            "rank": books["pop_rank"].astype("int64"),
        }
    )
    all_rows = rows.sort_values(["segment", "rank"]).reset_index(drop=True)
    # Plan 07(DATA-08): all 행 뒤에 연령×성별 세그먼트 행을 증분(all 행 값은 불변)
    both = pd.concat([all_rows, segment_rows(books)], ignore_index=True)
    return both[list(POP_COLUMNS)]


def main() -> None:
    ap = argparse.ArgumentParser(description="밀리 카탈로그 → popularity_kr.parquet")
    ap.add_argument("--books", type=Path, default=DIR_PROCESSED / "books_kr.parquet")
    ap.add_argument("--out", type=Path, default=DIR_PROCESSED / "popularity_kr.parquet")
    args = ap.parse_args()
    df = build(pd.read_parquet(args.books))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(args.out, index=False)
    print(f"popularity rows={len(df)} segments={df['segment'].nunique()} → {args.out}")


if __name__ == "__main__":
    main()
