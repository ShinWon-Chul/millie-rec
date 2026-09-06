"""밀리 카탈로그 난이도 분포 요약 → results/millie_difficulty.json (PDF 난이도 문단 근거)."""

from __future__ import annotations

import argparse
import json
import math
import statistics
import subprocess
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOOKS_JSON = ROOT / "artifacts" / "serving" / "books_kr.json"
OUT_JSON = ROOT / "results" / "millie_difficulty.json"
TOP_CATEGORIES = 8
EXTREMES = 3
NDIGITS = 4
PERCENTILES = (("p10", 0.10), ("p50", 0.50), ("p90", 0.90))
STAT_FIELDS = ("difficulty", "resid_z", "completion_prob")


def _round(x: float | None) -> float | None:
    return None if x is None else round(float(x), NDIGITS)


def _category(row: dict) -> str | None:
    """서빙 아티팩트는 `category` 단일 키가 없다. categories 리스트의 첫 값이 대표 분야."""
    cats = row.get("categories") or []
    return cats[0] if cats else None


def _values(rows: list[dict], key: str) -> list[float]:
    return [float(r[key]) for r in rows if r.get(key) is not None]


def _percentile(ordered: list[float], q: float) -> float:
    """선형보간. pos = q*(n-1) — 손계산이 되는 정의를 쓴다."""
    pos = q * (len(ordered) - 1)
    lo, hi = math.floor(pos), math.ceil(pos)
    if lo == hi:
        return ordered[lo]
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (pos - lo)


def _stats(values: list[float]) -> dict | None:
    """결측 제외 7통계. 값이 하나도 없으면 None — 0으로 나누지 않는다."""
    if not values:
        return None
    ordered = sorted(values)
    out = {"min": _round(ordered[0])}
    for name, q in PERCENTILES:
        out[name] = _round(_percentile(ordered, q))
    out["max"] = _round(ordered[-1])
    out["mean"] = _round(statistics.fmean(ordered))
    out["std"] = _round(statistics.pstdev(ordered))  # 모집단 표준편차
    return out


def _mean(values: list[float]) -> float | None:
    return _round(statistics.fmean(values)) if values else None


def _brief(row: dict) -> dict:
    return {
        "book_id": row.get("book_id"),
        "title": row.get("title"),
        "category": _category(row),
        "difficulty": _round(row.get("difficulty")),
    }


def _by_category(rows: list[dict]) -> list[dict]:
    """권수 상위 TOP_CATEGORIES 개만 남기고 difficulty_mean 내림차순. 결측 분야는 뒤로."""
    groups: dict[str | None, list[dict]] = defaultdict(list)
    for row in rows:
        groups[_category(row)].append(row)
    counts = Counter({cat: len(rs) for cat, rs in groups.items()})
    out = [
        {
            "category": cat,
            "n": n,
            "difficulty_mean": _mean(_values(groups[cat], "difficulty")),
            "completion_prob_mean": _mean(_values(groups[cat], "completion_prob")),
        }
        for cat, n in counts.most_common(TOP_CATEGORIES)
    ]
    out.sort(key=lambda d: (d["difficulty_mean"] is None, -(d["difficulty_mean"] or 0.0)))
    return out


def summarize(rows: list[dict]) -> dict:
    """난이도 커버리지 · 분포 · 분야별 평균 · 상하위 EXTREMES 권."""
    n_books = len(rows)
    scored = [r for r in rows if r.get("difficulty") is not None]
    hard = sorted(scored, key=lambda r: (-float(r["difficulty"]), r.get("book_id")))
    easy = sorted(scored, key=lambda r: (float(r["difficulty"]), r.get("book_id")))
    return {
        "n_books": n_books,
        "n_difficulty": len(scored),
        "coverage": round(len(scored) / n_books, NDIGITS) if n_books else 0.0,
        "by_source": dict(Counter(r.get("difficulty_source") for r in rows).most_common()),
        **{f: _stats(_values(rows, f)) for f in STAT_FIELDS},
        "by_category": _by_category(rows),
        "hardest_easiest": {
            "hardest": [_brief(r) for r in hard[:EXTREMES]],
            "easiest": [_brief(r) for r in easy[:EXTREMES]],
        },
    }


def _git_sha() -> str | None:
    try:
        done = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return done.stdout.strip() or None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--books", type=Path, default=BOOKS_JSON)
    parser.add_argument("--out", type=Path, default=OUT_JSON)
    args = parser.parse_args()

    rows = json.loads(args.books.read_text(encoding="utf-8"))
    out = summarize(rows)
    out["created_at"] = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    out["source"] = str(args.books.resolve().relative_to(ROOT))
    out["git_sha"] = _git_sha()

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {args.out} (n_books={out['n_books']}, coverage={out['coverage']})")


if __name__ == "__main__":
    main()
