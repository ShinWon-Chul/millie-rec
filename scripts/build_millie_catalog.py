"""millie_pages.jsonl → books_kr.parquet · id_map.csv · millie_raw_coverage.json (US-004).

적재 계획 §3(스키마)·§4(결측 규칙). book_id 는 catalog_urls.txt 사전순 surrogate 이며
id_map.csv 를 통해 append-only 로만 늘어난다 — 기존 행은 절대 바뀌지 않는다.
"""

import argparse
import json
import re
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from millie_rec.contracts import DIR_PROCESSED, DIR_RAW, FILE_ID_MAP

SCRIPTS_DIR = str(Path(__file__).resolve().parent)  # scripts/ 는 패키지가 아니다(테스트 importlib)
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)
import millie_difficulty  # noqa: E402

COLUMNS = tuple(
    "book_id millie_id title subtitle authors publisher pub_date original_publication_year "
    "categories subcategories book_format formats image_url average_rating rating_observed "
    "ratings_count review_count shelf_count pop_rank tags description curator_note "
    "completion_prob category_avg_prob expected_min category_avg_min millie_label "
    "resid_z len_z difficulty difficulty_source seg_dist top_segment "
    "isbn13 pages_diag collected_at source".split()
)
INT_COLS = tuple(
    "original_publication_year ratings_count review_count shelf_count pop_rank "
    "completion_prob category_avg_prob expected_min category_avg_min".split()
)

# 오디오북 > 챗북 > 전자책 (계획 §3)
FORMAT_PRIORITY = ("오디오북", "챗북", "전자책")
DESC_MAX, NOTE_MAX = 400, 100
MIN_BOOKS_PER_CATEGORY = 20
MAX_TITLELESS_RATIO = 0.005  # D-06: 파서 미스 비율 상한 — 단언은 tests/data 게이트가 한다
# 03-UAT Test 9 배지 title 오염(실측 7종): 걸러내지 않고 카운터로만 드러낸다 — 복구는 재수집
BADGE_TITLES = frozenset(
    "읽던 지점 그대로 이어듣기|도슨트북|무료|오브제북|웹소설|웹툰|오디오웹소설".split("|")
)
BADGE_TITLE_RE = re.compile(r"^종료 D-\d+$")  # 카운트다운 배지(실측 9건, 09-05)

# 커버리지 게이트(계획 §7) 필드명 → 원본 JSONL 키. categories 만 단일값 category 에서 만든다
COVERAGE_FIELDS = {"categories": "category"} | {
    f: f
    for f in (
        "title subtitle authors publisher image_url pub_date average_rating shelf_count "
        "review_count formats seg_dist top_segment completion_prob category_avg_prob "
        "expected_min category_avg_min millie_label curator_note description best_category"
    ).split()
}


def is_badge_title(title: object) -> bool:  # 게이트·재수집 목록이 공유하는 배지 판정
    return isinstance(title, str) and (title in BADGE_TITLES or bool(BADGE_TITLE_RE.match(title)))


def _present(value: object) -> bool:
    """None·빈 문자열·빈 리스트는 결측. 숫자 0 은 값이다."""
    if value is None:
        return False
    if isinstance(value, str | list | tuple | dict):
        return len(value) > 0
    return True


def _clip(text: object, limit: int) -> str | None:
    return text[:limit] if isinstance(text, str) and text else None


def _as_text(value: object) -> str | None:
    if isinstance(value, list | tuple):
        return ", ".join(str(v) for v in value) or None
    return str(value) if value else None


def _year(pub_date: object) -> int | None:
    try:
        return int(str(pub_date)[:4])
    except (TypeError, ValueError):
        return None


def _tags(category: object, label: object, formats: list[str]) -> str:
    return " ".join(str(t) for t in [category, label, *formats] if t)


def _is_collected(rec: dict) -> bool:
    """수집 성공 판정. collector 는 status 에 HTTP 코드(200) 또는 'ok' 를 넣는다 — 둘 다 받는다."""
    status = rec.get("status")
    if status is None or str(status).lower() == "ok":
        return True
    try:
        return 200 <= int(status) < 300
    except (TypeError, ValueError):
        return False


def read_records(jsonl: Path) -> tuple[list[dict], dict]:
    """수집 성공 레코드만, millie_id 기준 마지막 줄(최신 수집)을 남긴다.

    유효 = status 2xx ∧ title 있음(D-05). title 없는 성공 페이지는 카운터로만 남긴다.
    """
    lines, bad = [], 0
    for ln in jsonl.read_text(encoding="utf-8").splitlines():
        if not ln.strip():
            continue
        try:
            lines.append(json.loads(ln))
        except json.JSONDecodeError:
            bad += 1  # 배치가 append 중인 미완성 마지막 줄 — 크래시 없이 센다
    kept: dict[str, dict] = {}
    skipped = 0
    for rec in lines:
        if not _is_collected(rec):
            skipped += 1
            continue
        kept[rec["millie_id"]] = rec
    valid = [r for r in kept.values() if _present(r.get("title"))]
    blank = [r for r in kept.values() if not _present(r.get("title"))]
    # 껍데기(title·category·shelf_count 전무) vs 파서 미스(shelf_count 있음) — D-05
    shell = [r for r in blank if not _present(r.get("category")) and r.get("shelf_count") is None]
    n_empty, n_titleless = len(shell), len(blank) - len(shell)
    meta = {"n_lines": len(lines) + bad, "n_skipped_status": skipped, "n_skipped_badline": bad}
    meta |= {"n_success": len(kept), "n_skipped_empty": n_empty, "n_skipped_titleless": n_titleless}
    meta["titleless_ratio"] = n_titleless / len(kept) if kept else 0.0
    return valid, meta


def _read_id_list(path: Path) -> list[str]:
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        tok = line.strip().split("\t")[0].strip()
        if not tok or tok.startswith("#"):
            continue
        out.append(tok.rstrip("/").split("/")[-1] if "/" in tok else tok)
    return out


def assign_ids(path: Path, raw_dir: Path, jsonl_ids: list[str]) -> dict[str, int]:
    """id_map.csv 를 읽어 기존 배정을 보존하고 신규만 N+1 부터 붙인다."""
    rows: list[dict] = []
    known: dict[str, int] = {}
    if path.exists():
        prev = pd.read_csv(path, dtype={"millie_id": "str"})
        for r in prev.to_dict("records"):
            known[str(r["millie_id"])] = int(r["book_id"])
            rows.append(
                {
                    "millie_id": str(r["millie_id"]),
                    "book_id": int(r["book_id"]),
                    "first_seen_at": r["first_seen_at"],
                }
            )
    valid = set(jsonl_ids)  # D-17: 신규 id 는 유효 레코드에만(append-only)
    order = (
        sorted(_read_id_list(raw_dir / "catalog_urls.txt"))
        + [m for m in _read_id_list(raw_dir / "discovered_urls.txt") if m in valid]
        + sorted(jsonl_ids)
    )
    now = datetime.now(UTC).isoformat(timespec="seconds")
    nxt = max(known.values(), default=0) + 1
    for mid in dict.fromkeys(order):
        if mid in known:
            continue
        known[mid] = nxt
        rows.append({"millie_id": mid, "book_id": nxt, "first_seen_at": now})
        nxt += 1
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows, columns=["millie_id", "book_id", "first_seen_at"]).sort_values(
        "book_id"
    ).to_csv(path, index=False)
    return known


def normalize_category(raw: object) -> str | None:
    """밀리 카테고리 자리의 표기 정규화(09-05 실측 반영).
    웹소설 페이지는 이 자리에 '# 먼치킨' 같은 해시태그나 '완결'·'수 연재' 같은 연재 상태가 온다
    → 온보딩 20 카테고리의 '웹툰/웹소설'로 묶는다. 나머지(오디오북·챗북·밀리 오리지널 등
    콘텐츠 타입 표기)는 밀리 표기 그대로 — 주제 카테고리 매핑은 서빙 레인 결정(계획 §3)."""
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None
    if s.startswith("#") or s.endswith("연재") or s == "완결":
        return "웹툰/웹소설"
    return s


def _row(rec: dict, book_id: int) -> dict:
    category = normalize_category(rec.get("category"))
    formats = list(rec.get("formats") or [])
    prob, avg_prob = rec.get("completion_prob"), rec.get("category_avg_prob")
    filled = prob is None  # 계획 §4: 결측이면 분야 평균으로 대체 + 출처 표시
    seg = rec.get("seg_dist")
    return {
        "book_id": book_id,
        "millie_id": rec["millie_id"],
        "title": rec.get("title"),
        "subtitle": rec.get("subtitle"),
        "authors": _as_text(rec.get("authors")),
        "publisher": rec.get("publisher"),
        "pub_date": rec.get("pub_date"),
        "original_publication_year": _year(rec.get("pub_date")),
        "categories": [category] if category else [],
        "subcategories": [],
        "book_format": next((f for f in FORMAT_PRIORITY if f in formats), "전자책"),
        "formats": formats,
        "image_url": rec.get("image_url"),
        "average_rating": rec.get("average_rating"),
        "rating_observed": rec.get("average_rating") is not None,
        "ratings_count": rec.get("review_count") or 0,  # 계약 호환 전용
        "review_count": rec.get("review_count"),
        "shelf_count": rec.get("shelf_count"),
        "pop_rank": None,
        "tags": _tags(category, rec.get("millie_label"), formats),  # 계약 호환 전용
        "description": _clip(rec.get("description"), DESC_MAX),
        "curator_note": _clip(rec.get("curator_note"), NOTE_MAX),
        "completion_prob": avg_prob if filled else prob,
        "category_avg_prob": avg_prob,
        "expected_min": rec.get("expected_min"),
        "category_avg_min": rec.get("category_avg_min"),
        "millie_label": rec.get("millie_label"),
        "difficulty_source": "category_prior" if filled else "millie_index",
        "seg_dist": json.dumps(seg, ensure_ascii=False) if seg else None,
        "top_segment": rec.get("top_segment"),
        "isbn13": None,
        "pages_diag": None,
        "collected_at": rec.get("collected_at"),
        "source": rec.get("source"),
    }


def build_frame(records: list[dict], ids: dict[str, int]) -> pd.DataFrame:
    rows = [_row(r, ids[r["millie_id"]]) for r in records if r["millie_id"] in ids]

    def _pop_key(row: dict) -> tuple[float, int]:
        shelf = row["shelf_count"]
        return (-(shelf if shelf is not None else -1), row["book_id"])

    for rank, row in enumerate(sorted(rows, key=_pop_key), start=1):
        row["pop_rank"] = rank  # shelf_count 내림차순, 결측은 마지막
    df = pd.DataFrame(rows, columns=list(COLUMNS)).sort_values("book_id").reset_index(drop=True)
    for col in INT_COLS:
        df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")
    df["book_id"] = df["book_id"].astype("int64")
    df["average_rating"] = pd.to_numeric(df["average_rating"], errors="coerce").astype("Float64")
    df["rating_observed"] = df["rating_observed"].astype("bool")
    return millie_difficulty.add_difficulty(df)


def coverage(records: list[dict], meta: dict) -> dict:
    n = len(records)
    cats = Counter(r["category"] for r in records if _present(r.get("category")))
    return {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "n_records": n,
        **meta,
        "fields": {
            name: (sum(_present(r.get(key)) for r in records) / n if n else 0.0)
            for name, key in COVERAGE_FIELDS.items()
        },
        "categories": dict(cats.most_common()),
        "category_distinct": len(cats),
        "categories_ge_min": sum(1 for c in cats.values() if c >= MIN_BOOKS_PER_CATEGORY),
        "min_books_per_category": MIN_BOOKS_PER_CATEGORY,
        "max_titleless_ratio": MAX_TITLELESS_RATIO,
        "n_badge_title": sum(1 for r in records if is_badge_title(r.get("title"))),
        "badge_titles": sorted(BADGE_TITLES),
    }


def build(
    jsonl: Path, out_dir: Path, raw_dir: Path | None = None, id_map: Path | None = None
) -> pd.DataFrame:
    records, meta = read_records(jsonl)
    ids = assign_ids(
        id_map or out_dir / "id_map.csv",
        raw_dir or jsonl.parent,
        [r["millie_id"] for r in records],
    )
    df = build_frame(records, ids)
    out_dir.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out_dir / "books_kr.parquet", index=False)
    (out_dir / "millie_raw_coverage.json").write_text(
        json.dumps(coverage(records, meta), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return df


def main() -> None:
    ap = argparse.ArgumentParser(description="밀리 원본 JSONL → books_kr.parquet")
    ap.add_argument("--jsonl", type=Path, default=DIR_RAW / "millie_pages.jsonl")
    ap.add_argument("--out", type=Path, default=DIR_PROCESSED)
    ap.add_argument("--raw-dir", type=Path, default=None, help="기본값: --jsonl 의 상위 디렉터리")
    ap.add_argument("--id-map", type=Path, default=FILE_ID_MAP, help="append-only, 커밋 대상")
    args = ap.parse_args()
    df = build(args.jsonl, args.out, args.raw_dir, args.id_map)
    rep = json.loads((args.out / "millie_raw_coverage.json").read_text("utf-8"))
    skip = f"empty={rep['n_skipped_empty']} titleless={rep['n_skipped_titleless']}"
    print(f"books={len(df)} → {args.out / 'books_kr.parquet'} · id_map → {args.id_map} {skip}")


if __name__ == "__main__":
    main()
