"""export_millie_serving — 계약(3파일·28키·<50MB) · 정확성(NaN→null·popularity 행).

안전성: description·curator_note·seg_dist·millie_id 0건.
"""

import importlib.util
import inspect
import json
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "tests" / "fixtures" / "millie" / "sample_records.jsonl"

MAX_BYTES = 50 * 1024 * 1024
N_FIXTURE_BOOKS = 12
FILE_NAMES = ("books_kr.json", "item_edges_kr.json", "popularity_kr.json")

# 스크립트 상수를 import 하지 않고 손으로 적는다 — CatalogKR.meta() 노출 필드와 같은 집합.
EXPECTED_BOOK_KEYS = [
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
    "publisher",
    "subtitle",
    "pub_date",
    "book_format",
    "formats",
    "pop_rank",
    "millie_label",
    "review_count",
    "shelf_count",
    "completion_prob",
    "category_avg_prob",
    "expected_min",
    "category_avg_min",
    "resid_z",
    "len_z",
    "difficulty",
    "difficulty_source",
    "top_segment",
]
CONTRACT_NINE = (
    "book_id",
    "title",
    "authors",
    "image_url",
    "average_rating",
    "ratings_count",
    "original_publication_year",
    "categories",
    "tags",
)
EXCLUDED_KEYS = (
    '"description"',
    '"curator_note"',
    '"seg_dist"',
    '"millie_id"',
    '"rating_observed"',
)
FIRST_BOOK_DESCRIPTION_HEAD = "편의점 야간 아르바이트를"  # 픽스처 1번 책의 밀리 저작 텍스트
BOOK_FORMATS = {"전자책", "오디오북", "챗북"}
POPULARITY_KEYS = {"book_id", "segment", "score", "rank"}


def _load(name: str):
    """scripts/ 는 패키지가 아니므로 경로로 직접 로드한다."""
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def exported(tmp_path_factory) -> tuple[Path, dict]:
    """합성 픽스처 체인 → tmp 로 export. 실 artifacts/serving 은 건드리지 않는다(Plan 06)."""
    exp = _load("export_millie_serving")
    if len(inspect.signature(exp.export).parameters) != 4:
        pytest.fail(
            "export 는 popularity_path 를 받아야 한다(DATA-07) — 현 시그니처 "
            f"{inspect.signature(exp.export)}"
        )
    work = tmp_path_factory.mktemp("export")
    _load("build_millie_catalog").build(FIXTURE, work, raw_dir=work)
    books = pd.read_parquet(work / "books_kr.parquet")
    edges_mod = _load("build_millie_edges")
    edges_mod.build(books, edges_mod.read_best_links(FIXTURE)).to_parquet(
        work / "item_edges_kr.parquet", index=False
    )
    _load("build_millie_popularity").build(books).to_parquet(
        work / "popularity_kr.parquet", index=False
    )
    out = work / "serving"
    sizes = exp.export(
        work / "books_kr.parquet",
        work / "item_edges_kr.parquet",
        work / "popularity_kr.parquet",
        out,
    )
    return out, sizes


@pytest.fixture(scope="module")
def books_json(exported) -> list[dict]:
    out, _ = exported
    return json.loads((out / "books_kr.json").read_text(encoding="utf-8"))


def test_three_files_exist_under_size_cap(exported):
    out, sizes = exported
    assert set(sizes) == set(FILE_NAMES)
    for name in FILE_NAMES:
        path = out / name
        assert path.exists(), f"{name} 없음"
        assert path.stat().st_size < MAX_BYTES


def test_books_json_rows_have_exactly_meta_fields(books_json):
    assert len(books_json) == N_FIXTURE_BOOKS
    for row in books_json:
        assert set(row) == set(EXPECTED_BOOK_KEYS)
        assert list(row) == EXPECTED_BOOK_KEYS
    assert [r["book_id"] for r in books_json] == sorted(r["book_id"] for r in books_json)


def test_books_json_excludes_author_text_and_raw_ids(exported):
    """DATA-06 — 밀리 저작 텍스트·원본 id 는 서빙 산출물로 나가지 않는다."""
    out, _ = exported
    raw = (out / "books_kr.json").read_text(encoding="utf-8")
    for key in EXCLUDED_KEYS:
        assert raw.count(key) == 0, f"{key} 가 books_kr.json 에 있다"
    assert FIRST_BOOK_DESCRIPTION_HEAD not in raw


def test_nan_difficulty_becomes_null(books_json):
    """DATA-04 결측 difficulty=None 이 json null 로 보존된다."""
    prior = [r for r in books_json if r["difficulty_source"] == "category_prior"]
    assert prior, "픽스처에 category_prior 행이 있어야 한다"
    for row in prior:
        assert row["difficulty"] is None
        assert row["resid_z"] == 0.0
    for row in [r for r in books_json if r["difficulty_source"] == "millie_index"]:
        assert 0.0 < row["difficulty"] < 1.0


def test_edges_json_unchanged_shape(exported):
    out, _ = exported
    edges = json.loads((out / "item_edges_kr.json").read_text(encoding="utf-8"))
    assert edges
    first = edges[next(iter(edges))]
    assert len(first[0]) == 3
    weights = [w for _dst, w, _source in first]
    assert weights == sorted(weights, reverse=True)


def test_popularity_json_rows(exported):
    out, _ = exported
    rows = json.loads((out / "popularity_kr.json").read_text(encoding="utf-8"))
    all_rows = [
        r for r in rows if r["segment"] == "all"
    ]  # 전 행 수는 단정하지 않는다(Plan 07 증분)
    assert len(all_rows) == N_FIXTURE_BOOKS
    for row in all_rows:
        assert set(row) == POPULARITY_KEYS
        assert isinstance(row["score"], float)
    assert sorted(r["rank"] for r in all_rows) == list(range(1, N_FIXTURE_BOOKS + 1))


def test_books_json_keys_match_serving_sample_fixture(books_json, millie_serving_sample):
    """스키마 드리프트 가드 — conftest fixture · 이 파일 · 스크립트 BOOK_FIELDS 3벌 일치."""
    sample = json.loads((millie_serving_sample / "books_kr.json").read_text(encoding="utf-8"))
    assert set(sample[0]) == set(EXPECTED_BOOK_KEYS)
    assert set(books_json[0]) == set(sample[0])


def test_book_format_values_and_contract_nine(books_json):
    for row in books_json:
        assert row["book_format"] in BOOK_FORMATS
    assert set(CONTRACT_NINE) <= set(books_json[0])
