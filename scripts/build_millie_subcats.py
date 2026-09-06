"""3depth 수집 JSONL → subcategories_kr.parquet·커버리지·메타 → books_kr.* `subcategories` 패치.

패치는 `subcategories` 키만 바꾼다. 다른 키·행 순서·직렬화 방식(`json.dumps(ensure_ascii=False)`)은
export_millie_serving.py 와 같아 나머지는 바이트 동일하다(자체 검증 후에만 기록).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

COLS = ["book_id", "millie_id", "category", "subcategory", "depth3_seq", "rank"]
COV_COLS = [
    "category", "n_subcats", "n_listed_ids", "n_in_catalog", "n_catalog_books",
    "share_books_with_subcat",
]  # fmt: skip


def load_rows(jsonl: Path) -> list[dict]:
    rows = [json.loads(line) for line in jsonl.read_text(encoding="utf-8").splitlines() if line]
    latest: dict[str, dict] = {}
    for r in rows:  # 재수집이 있으면 마지막 ok 가 이긴다
        if r.get("status") == "ok":
            latest[r["depth3_seq"]] = r
    return list(latest.values())


def build_tuples(rows: list[dict], id_map: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    mid2bid = dict(zip(id_map["millie_id"], id_map["book_id"].astype(int), strict=True))
    recs, dropped = [], 0
    for r in rows:
        for rank, mid in enumerate(r["millie_ids"], start=1):
            bid = mid2bid.get(mid)
            if bid is None:
                dropped += 1
                continue
            recs.append((bid, mid, r["category"], r["subcategory"], r["depth3_seq"], rank))
    df = pd.DataFrame(recs, columns=COLS).drop_duplicates(["book_id", "subcategory"])
    return df.sort_values(["book_id", "rank"]).reset_index(drop=True), dropped


def meta_map(rows: list[dict], categories: list[str]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {c: [] for c in categories}
    for r in rows:
        lst = out.setdefault(r["category"], [])
        if r["subcategory"] not in lst:
            lst.append(r["subcategory"])
    return out


def coverage(rows: list[dict], tuples: pd.DataFrame, books: pd.DataFrame) -> pd.DataFrame:
    cat_of = books["categories"].map(lambda v: v[0] if len(v) else None)
    with_sub = set(tuples["book_id"])
    out = []
    for cat in sorted(set(cat_of.dropna())):
        rs = [r for r in rows if r["category"] == cat]
        ids = books.loc[cat_of == cat, "book_id"]
        n_with = int(ids.isin(with_sub).sum())
        out.append((cat, len(rs), sum(r["n"] for r in rs), int((tuples["category"] == cat).sum()),
                    len(ids), round(n_with / max(len(ids), 1), 4)))  # fmt: skip
    n_all_with = int(books["book_id"].isin(with_sub).sum())
    out.append(("ALL", len(rows), sum(r["n"] for r in rows), len(tuples), len(books),
                round(n_all_with / max(len(books), 1), 4)))  # fmt: skip
    return pd.DataFrame(out, columns=COV_COLS)


def subs_per_book(tuples: pd.DataFrame) -> dict[int, list[str]]:
    return {int(b): sorted(set(g["subcategory"])) for b, g in tuples.groupby("book_id", sort=True)}


def patch_parquet(path: Path, subs: dict[int, list[str]]) -> int:
    books = pd.read_parquet(path)
    books["subcategories"] = [list(subs.get(int(b), [])) for b in books["book_id"]]
    books.to_parquet(path, index=False)
    return int(sum(1 for b in books["book_id"] if subs.get(int(b))))


def patch_json(path: Path, subs: dict[int, list[str]]) -> int:
    original = json.loads(path.read_text(encoding="utf-8"))
    patched = [
        {**rec, "subcategories": list(subs.get(int(rec["book_id"]), []))} for rec in original
    ]
    for o, p in zip(original, patched, strict=True):  # 자체 검증: 다른 키는 전부 동일
        assert {k: v for k, v in o.items() if k != "subcategories"} == {
            k: v for k, v in p.items() if k != "subcategories"
        }
    path.write_text(json.dumps(patched, ensure_ascii=False), encoding="utf-8")
    return sum(1 for p in patched if p["subcategories"])


def run(jsonl: Path, id_map: Path, books: Path, out_dir: Path, results: Path, serving: Path,
        dry_run: bool) -> dict:  # fmt: skip
    rows = load_rows(jsonl)
    bk = pd.read_parquet(books)
    tuples, dropped = build_tuples(rows, pd.read_csv(id_map, dtype={"millie_id": str}))
    out_dir.mkdir(parents=True, exist_ok=True)
    results.mkdir(parents=True, exist_ok=True)
    tuples.to_parquet(out_dir / "subcategories_kr.parquet", index=False)
    cats = sorted(set(bk["categories"].map(lambda v: v[0] if len(v) else None).dropna()))
    (results / "subcat_meta.json").write_text(
        json.dumps(meta_map(rows, cats), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    cov = coverage(rows, tuples, bk)
    cov.to_csv(results / "subcat_coverage.csv", index=False)
    subs = subs_per_book(tuples)
    n_pq = n_js = None
    if not dry_run:
        n_pq = patch_parquet(books, subs)
        n_js = patch_json(serving / "books_kr.json", subs)
    return {
        "n_subcats": len(rows), "n_tuples": len(tuples), "n_dropped_unknown": dropped,
        "n_books_with_subcat": len(subs), "share": round(len(subs) / max(len(bk), 1), 4),
        "patched_parquet": n_pq, "patched_json": n_js,
    }  # fmt: skip


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jsonl", type=Path, default=Path("data/raw/millie_subcats.jsonl"))
    ap.add_argument("--id-map", type=Path, default=Path("data/id_map.csv"))
    ap.add_argument("--books", type=Path, default=Path("data/processed/books_kr.parquet"))
    ap.add_argument("--out-dir", type=Path, default=Path("data/processed"))
    ap.add_argument("--results", type=Path, default=Path("results"))
    ap.add_argument("--serving", type=Path, default=Path("artifacts/serving"))
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    print(run(a.jsonl, a.id_map, a.books, a.out_dir, a.results, a.serving, a.dry_run))


if __name__ == "__main__":
    main()
