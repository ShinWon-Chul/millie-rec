"""US-004 카탈로그 빌더 단위 테스트 + 적재 계획 §7 커버리지 게이트.

단위 테스트는 합성 픽스처만 쓴다. 게이트는 실제 수집 산출물이 있을 때만 돌고,
미달은 경고가 아니라 test fail 이다 (Day 2 게이트).
"""

import csv
import importlib.util
import json
import shutil
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "tests" / "fixtures" / "millie" / "sample_records.jsonl"
REAL_BOOKS = ROOT / "data" / "processed" / "books_kr.parquet"
REAL_COVERAGE = ROOT / "data" / "processed" / "millie_raw_coverage.json"
COVERAGE_CSV = ROOT / "results" / "millie_coverage.csv"

# 적재 계획 §3 의 컬럼 순서 그대로. 스크립트 상수를 import 하지 않고 손으로 적어 둔다.
EXPECTED_COLUMNS = [
    "book_id",
    "millie_id",
    "title",
    "subtitle",
    "authors",
    "publisher",
    "pub_date",
    "original_publication_year",
    "categories",
    "subcategories",
    "book_format",
    "formats",
    "image_url",
    "average_rating",
    "rating_observed",
    "ratings_count",
    "review_count",
    "shelf_count",
    "pop_rank",
    "tags",
    "description",
    "curator_note",
    "completion_prob",
    "category_avg_prob",
    "expected_min",
    "category_avg_min",
    "millie_label",
    "difficulty_source",
    "seg_dist",
    "top_segment",
    "isbn13",
    "pages_diag",
    "collected_at",
    "source",
]

# 계획 §7 커버리지 게이트. average_rating 은 보고만 하고 임계값을 두지 않는다.
THRESHOLDS = {
    "title": 1.0,
    "image_url": 0.99,
    "categories": 0.95,
    "completion_prob": 0.70,
    "formats": 0.90,
    "seg_dist": 0.70,
}
MIN_CATEGORY_DISTINCT = 8
MIN_BOOKS_PER_CATEGORY = 20
MIN_CATEGORIES_WITH_ENOUGH_BOOKS = 6

FIRST_BOOK = "0f1e2d3c4b5a6001"  # shelf_count 최대 · 긴 description·curator_note
NO_PROB_BOOK = "6f708192a3b40007"  # completion_prob 결측 → category_avg_prob 대체
NO_SHELF_BOOK = "92a3b4c5d6e7000a"  # shelf_count 결측 → pop_rank 마지막
NO_IMAGE_BOOK = "a3b4c5d6e7f8000b"  # image_url 키 자체가 없음
NO_FORMAT_BOOK = "5e6f708192a30006"  # formats 빈 리스트 → book_format 기본값
CHATBOOK = "1a2b3c4d5e6f7002"  # formats 에 챗북
FAILED_BOOK = "deadbeefdeadbeef"  # status != ok


def _load(name: str):
    """scripts/ 는 패키지가 아니므로 경로로 직접 로드한다."""
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def catalog():
    return _load("build_millie_catalog")


@pytest.fixture
def built(tmp_path, catalog) -> tuple[pd.DataFrame, Path]:
    """픽스처 JSONL → tmp 디렉터리. raw_dir 은 빈 tmp 라 사전순 폴백이 쓰인다."""
    out = tmp_path / "processed"
    catalog.build(FIXTURE, out, raw_dir=tmp_path / "raw")
    return pd.read_parquet(out / "books_kr.parquet"), out


def _row(df: pd.DataFrame, millie_id: str) -> pd.Series:
    return df.set_index("millie_id").loc[millie_id]


def test_columns_are_exactly_the_contract_order(built):
    df, _ = built
    assert list(df.columns) == EXPECTED_COLUMNS


def test_dedup_keeps_last_collected_and_drops_failed_pages(built):
    df, _ = built
    assert len(df) == 12
    assert df["millie_id"].is_unique
    assert FAILED_BOOK not in set(df["millie_id"])
    assert _row(df, FIRST_BOOK)["title"] == "불편한 편의점 (재수집)"


def test_book_ids_are_lexicographic_over_catalog_urls(tmp_path, catalog):
    """book_id 는 catalog_urls.txt 사전순 surrogate — 파일 순서가 뒤섞여도 결과가 같다.

    수집 실패(status != ok) 도서도 sitemap 에 있으면 id 를 받는다 — 재수집 때 id 가 밀리지 않게.
    """
    raw = tmp_path / "raw"
    raw.mkdir()
    ids = sorted({json.loads(ln)["millie_id"] for ln in FIXTURE.read_text("utf-8").splitlines()})
    (raw / "catalog_urls.txt").write_text("\n".join(reversed(ids)) + "\n", encoding="utf-8")
    out = tmp_path / "processed"
    catalog.build(FIXTURE, out, raw_dir=raw)
    id_map = pd.read_csv(out / "id_map.csv", dtype={"millie_id": "str"})
    assert list(id_map.sort_values("book_id")["millie_id"]) == ids
    assert list(id_map["book_id"]) == list(range(1, len(ids) + 1))
    assert FAILED_BOOK in ids  # sitemap 에 있으니 id 는 받고, 카탈로그 행은 안 생긴다


def test_discovered_urls_are_appended_in_file_order(tmp_path, catalog):
    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "catalog_urls.txt").write_text(f"{FIRST_BOOK}\n", encoding="utf-8")
    (raw / "discovered_urls.txt").write_text(
        f"{CHATBOOK}\tbest\n{NO_PROB_BOOK}\tawards\n", encoding="utf-8"
    )
    out = tmp_path / "processed"
    catalog.build(FIXTURE, out, raw_dir=raw)
    id_map = pd.read_csv(out / "id_map.csv", dtype={"millie_id": "str"}).set_index("millie_id")
    assert int(id_map.loc[FIRST_BOOK, "book_id"]) == 1
    assert int(id_map.loc[CHATBOOK, "book_id"]) == 2
    assert int(id_map.loc[NO_PROB_BOOK, "book_id"]) == 3


def test_catalog_urls_may_hold_full_urls(tmp_path, catalog):
    """실제 collector 는 catalog_urls.txt 에 전체 URL 을 쓴다 — 마지막 경로 조각이 millie_id."""
    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "catalog_urls.txt").write_text(
        f"https://www.millie.co.kr/v4/book/{CHATBOOK}\n"
        f"https://www.millie.co.kr/v4/book/{FIRST_BOOK}\n",
        encoding="utf-8",
    )
    out = tmp_path / "processed"
    catalog.build(FIXTURE, out, raw_dir=raw)
    id_map = pd.read_csv(out / "id_map.csv", dtype={"millie_id": "str"}).set_index("millie_id")
    assert int(id_map.loc[FIRST_BOOK, "book_id"]) == 1  # 사전순이 파일 순서를 이긴다
    assert int(id_map.loc[CHATBOOK, "book_id"]) == 2


def test_collector_http_status_is_accepted(catalog):
    """collector 는 status 에 HTTP 코드(200)를, 초기 설계는 'ok' 를 쓴다 — 둘 다 수집 성공."""
    assert catalog._is_collected({"status": 200})
    assert catalog._is_collected({"status": "ok"})
    assert catalog._is_collected({})
    assert not catalog._is_collected({"status": 500})
    assert not catalog._is_collected({"status": "error"})


def test_id_map_default_target_is_committed_not_gitignored(catalog):
    """data/processed/* 는 gitignore 대상이라 id_map 기본 경로는 data/id_map.csv 여야 한다."""
    from millie_rec.contracts import DIR_PROCESSED, FILE_ID_MAP

    assert catalog.FILE_ID_MAP == FILE_ID_MAP
    assert DIR_PROCESSED not in FILE_ID_MAP.parents


def test_id_map_is_append_only_on_rebuild(tmp_path, catalog):
    """사전순으로 제일 앞에 오는 책이 추가돼도 기존 book_id 는 밀리지 않는다."""
    raw = tmp_path / "raw"
    raw.mkdir()
    jsonl = raw / "millie_pages.jsonl"
    shutil.copy(FIXTURE, jsonl)
    out = tmp_path / "processed"
    first = catalog.build(jsonl, out, raw_dir=raw)
    before = pd.read_csv(out / "id_map.csv", dtype={"millie_id": "str"})

    newcomer = json.loads(FIXTURE.read_text("utf-8").splitlines()[0])
    newcomer["millie_id"] = "00000000deadbe01"  # 사전순 최소
    newcomer["title"] = "보충 수집된 책"
    with jsonl.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(newcomer, ensure_ascii=False) + "\n")
    second = catalog.build(jsonl, out, raw_dir=raw)
    after = pd.read_csv(out / "id_map.csv", dtype={"millie_id": "str"})

    kept = after[after["millie_id"].isin(before["millie_id"])].reset_index(drop=True)
    pd.testing.assert_frame_equal(before.sort_values("book_id").reset_index(drop=True), kept)
    assert len(second) == len(first) + 1
    assert int(_row(second, "00000000deadbe01")["book_id"]) == len(before) + 1
    assert int(_row(second, FIRST_BOOK)["book_id"]) == int(_row(first, FIRST_BOOK)["book_id"])


def test_missing_completion_prob_falls_back_to_category_prior(built):
    df, _ = built
    missing = _row(df, NO_PROB_BOOK)
    assert missing["difficulty_source"] == "category_prior"
    assert missing["completion_prob"] == missing["category_avg_prob"] == 49
    present = _row(df, FIRST_BOOK)
    assert present["difficulty_source"] == "millie_index"
    assert present["completion_prob"] == 78


def test_pop_rank_follows_shelf_count_desc_with_missing_last(built):
    df, _ = built
    assert sorted(df["pop_rank"]) == list(range(1, 13))
    assert int(_row(df, FIRST_BOOK)["pop_rank"]) == 1
    assert int(_row(df, NO_SHELF_BOOK)["pop_rank"]) == 12
    ranked = df.dropna(subset=["shelf_count"]).sort_values("pop_rank")
    assert list(ranked["shelf_count"]) == sorted(ranked["shelf_count"], reverse=True)


def test_tags_and_book_format(built):
    df, _ = built
    assert _row(df, FIRST_BOOK)["tags"] == "소설 밀리 픽 전자책 오디오북"
    assert _row(df, FIRST_BOOK)["book_format"] == "오디오북"  # 오디오북 > 챗북 > 전자책
    assert _row(df, CHATBOOK)["book_format"] == "챗북"
    assert _row(df, NO_FORMAT_BOOK)["book_format"] == "전자책"
    assert list(_row(df, NO_FORMAT_BOOK)["formats"]) == []
    assert _row(df, NO_SHELF_BOOK)["tags"] == "라이프스타일 전자책"  # millie_label 결측


def test_description_and_curator_note_are_truncated(built):
    df, _ = built
    row = _row(df, FIRST_BOOK)
    assert len(row["description"]) == 400
    assert len(row["curator_note"]) == 100
    assert df["description"].dropna().str.len().max() <= 400
    assert df["curator_note"].dropna().str.len().max() <= 100


def test_derived_and_placeholder_fields(built):
    df, _ = built
    row = _row(df, FIRST_BOOK)
    assert row["original_publication_year"] == 2021
    assert list(row["categories"]) == ["소설"]
    assert list(row["subcategories"]) == []
    assert row["authors"] == "김호연"
    assert row["rating_observed"] and row["average_rating"] == pytest.approx(4.6)
    assert row["ratings_count"] == row["review_count"] == 283
    assert json.loads(row["seg_dist"])["40대"]["여"] == pytest.approx(0.31)
    assert df["isbn13"].isna().all()
    assert df["pages_diag"].isna().all()

    no_rating = _row(df, "4d5e6f7081920005")
    assert not no_rating["rating_observed"]
    assert pd.isna(no_rating["average_rating"])
    assert pd.isna(_row(df, NO_IMAGE_BOOK)["image_url"])
    assert pd.notna(_row(df, NO_SHELF_BOOK)["seg_dist"])
    assert pd.isna(_row(df, "8192a3b4c5d60009")["seg_dist"])  # seg_dist 결측 책


def test_raw_coverage_json_is_written(built):
    _, out = built
    report = json.loads((out / "millie_raw_coverage.json").read_text("utf-8"))
    assert report["n_records"] == 12
    assert report["n_lines"] == 14
    assert report["n_skipped_status"] == 1
    assert report["fields"]["title"] == 1.0
    assert report["fields"]["completion_prob"] == pytest.approx(11 / 12)  # 채우기 전 원본 비율
    assert report["category_distinct"] == 10


# ── 게이트 (실제 수집 산출물) ────────────────────────────────────────────────
def test_coverage_gate():
    """계획 §7 커버리지 게이트. results/millie_coverage.csv 를 남기고 단언한다."""
    if not REAL_BOOKS.exists() or not REAL_COVERAGE.exists():
        pytest.skip(
            "실제 수집 산출물이 없다 — 게이트는 collect_millie.py 야간 배치 후에만 돈다 "
            f"(필요: {REAL_BOOKS.relative_to(ROOT)}, {REAL_COVERAGE.relative_to(ROOT)})"
        )
    report = json.loads(REAL_COVERAGE.read_text("utf-8"))
    fields = report["fields"]
    categories = report["categories"]
    enough = {c: n for c, n in categories.items() if n >= MIN_BOOKS_PER_CATEGORY}

    COVERAGE_CSV.parent.mkdir(parents=True, exist_ok=True)
    with COVERAGE_CSV.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["field", "non_null_ratio"])
        for name, ratio in sorted(fields.items()):
            writer.writerow([name, f"{ratio:.4f}"])
        writer.writerow(["_n_records", report["n_records"]])
        writer.writerow(["_category_distinct", report["category_distinct"]])
        writer.writerow(["_categories_ge_20", len(enough)])

    print(f"\naverage_rating 보유율 {fields['average_rating']:.3f} (임계값 없음, PDF 각주용)")
    print(f"카테고리 {report['category_distinct']}종 · 20권 이상 {len(enough)}종")
    below = {n: fields[n] for n, floor in THRESHOLDS.items() if fields[n] < floor}
    assert not below, f"커버리지 미달 {below} (기준 {THRESHOLDS})"
    assert report["category_distinct"] >= MIN_CATEGORY_DISTINCT
    assert len(enough) >= MIN_CATEGORIES_WITH_ENOUGH_BOOKS, (
        f"20권 이상 분야가 {len(enough)}종뿐 — BEST 보충 또는 온보딩 카테고리 축소 필요"
    )
