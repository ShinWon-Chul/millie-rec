"""books_kr.parquet → item_edges_kr.parquet (US-005, 적재 계획 §6).

이웃 정본은 title+description+curator_note 문자 2~4gram TF-IDF cosine top-20(content_sim)이고,
분야 BEST 링크(category_best)를 저가중으로 병합해 설명 결손 도서의 이웃 ≥5 를 보장한다.
best_links 는 books_kr.parquet 스키마(§3)에 없으므로 원본 JSONL 에서 millie_id 로 조인한다.
"""

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from millie_rec.contracts import DIR_PROCESSED, DIR_RAW

TOP_N = 20
MIN_NEIGHBOURS = 5
CATEGORY_BEST_WEIGHT = 0.2
NGRAM_RANGE = (2, 4)
EDGE_COLUMNS = ("src_book_id", "dst_book_id", "weight", "source")


def _text(value: object) -> str:
    return value if isinstance(value, str) and value else ""


def read_best_links(jsonl: Path | None) -> dict[str, list[str]]:
    """millie_id → 같은 분야 BEST 링크. 파일이 없으면 category_best 채널을 비운다."""
    if jsonl is None or not jsonl.exists():
        return {}
    out: dict[str, list[str]] = {}
    for line in jsonl.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        out[str(rec["millie_id"])] = [str(x) for x in (rec.get("best_links") or [])]
    return out


def build_texts(books: pd.DataFrame, with_tags: bool = False) -> list[str]:
    """tags 는 기본 제외 — 어휘 25토큰이면 다양성 재순위화가 카테고리 중복 제거로 퇴화한다."""
    cols = ["title", "description", "curator_note"] + (["tags"] if with_tags else [])
    return [
        " ".join(p for p in (_text(row[c]) for c in cols) if p)
        for row in books[cols].to_dict("records")
    ]


def similarity(texts: list[str]) -> np.ndarray:
    vec = TfidfVectorizer(analyzer="char_wb", ngram_range=NGRAM_RANGE, min_df=1)
    sim = cosine_similarity(vec.fit_transform(texts))
    np.fill_diagonal(sim, -1.0)  # self-edge 금지 (게이트 ①)
    return sim


def _content_pairs(sim: np.ndarray, ids: list[int]) -> dict[tuple[int, int], float]:
    order = np.argsort(-sim, axis=1)
    pairs: dict[tuple[int, int], float] = {}
    for i, src in enumerate(ids):
        for j in order[i, :TOP_N]:
            weight = float(sim[i, j])
            if weight > 0:
                pairs[(src, ids[int(j)])] = weight
    return pairs


def _category_pairs(
    books: pd.DataFrame, best_links: dict[str, list[str]]
) -> dict[tuple[int, int], float]:
    id_of = {str(m): int(b) for m, b in zip(books["millie_id"], books["book_id"], strict=True)}
    pairs: dict[tuple[int, int], float] = {}
    for millie_id, src in id_of.items():
        for linked in best_links.get(millie_id, []):
            dst = id_of.get(linked)  # 카탈로그 밖 링크는 버린다
            if dst is not None and dst != src:
                pairs[(src, dst)] = CATEGORY_BEST_WEIGHT
    return pairs


def _merge(
    content: dict[tuple[int, int], float], category: dict[tuple[int, int], float]
) -> dict[tuple[int, int], tuple[float, str]]:
    """겹치는 쌍은 큰 가중을 남기고 소스도 그쪽으로 (동률이면 content_sim 우선)."""
    merged: dict[tuple[int, int], tuple[float, str]] = {
        key: (weight, "category_best") for key, weight in category.items()
    }
    for key, weight in content.items():
        prev = merged.get(key)
        if prev is None or weight >= prev[0]:
            merged[key] = (weight, "content_sim")
    return merged


def _top_up(
    merged: dict[tuple[int, int], tuple[float, str]], sim: np.ndarray, ids: list[int]
) -> None:
    """이웃 ≥5 보장 (게이트 ②) — 부족분은 top-20 밖 content_sim 에서 채운다."""
    degree: dict[int, int] = dict.fromkeys(ids, 0)
    for src, _dst in merged:
        degree[src] += 1
    order = np.argsort(-sim, axis=1)
    for i, src in enumerate(ids):
        for j in order[i, TOP_N:]:
            if degree[src] >= MIN_NEIGHBOURS:
                break
            key = (src, ids[int(j)])
            if key in merged:
                continue
            merged[key] = (max(float(sim[i, j]), 0.0), "content_sim")
            degree[src] += 1


def build(
    books: pd.DataFrame,
    best_links: dict[str, list[str]] | None = None,
    with_tags: bool = False,
) -> pd.DataFrame:
    books = books.sort_values("book_id").reset_index(drop=True)
    ids = [int(b) for b in books["book_id"]]
    sim = similarity(build_texts(books, with_tags))
    merged = _merge(_content_pairs(sim, ids), _category_pairs(books, best_links or {}))
    _top_up(merged, sim, ids)
    rows = [
        {"src_book_id": src, "dst_book_id": dst, "weight": weight, "source": source}
        for (src, dst), (weight, source) in merged.items()
    ]
    return (
        pd.DataFrame(rows, columns=list(EDGE_COLUMNS))
        .sort_values(["src_book_id", "weight"], ascending=[True, False])
        .reset_index(drop=True)
    )


def main() -> None:
    ap = argparse.ArgumentParser(description="books_kr.parquet → item_edges_kr.parquet")
    ap.add_argument("--books", type=Path, default=DIR_PROCESSED / "books_kr.parquet")
    ap.add_argument("--out", type=Path, default=DIR_PROCESSED / "item_edges_kr.parquet")
    ap.add_argument("--jsonl", type=Path, default=DIR_RAW / "millie_pages.jsonl")
    ap.add_argument("--with-tags", action="store_true", help="게이트 ③ 여유 있을 때만")
    args = ap.parse_args()
    edges = build(pd.read_parquet(args.books), read_best_links(args.jsonl), args.with_tags)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    edges.to_parquet(args.out, index=False)
    counts = edges["source"].value_counts().to_dict()
    print(f"edges={len(edges)} {counts} → {args.out}")


if __name__ == "__main__":
    main()
