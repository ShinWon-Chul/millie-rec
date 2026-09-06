"""make_mock — 계약(model_validate 10파일) · 정확성(카드 키·top-20·결정성·eval float).

안전성: 자격 없는 책 제외 · 밀리 저작 텍스트 누출 0건 · 구 형태(v1 흔적) 0건.
"""

import importlib.util
import json
import sys
from pathlib import Path

import pytest

from millie_rec.contracts import BADGE_TYPES, ROW_ANCHOR_PREFIX, ROW_IDS
from millie_rec.serving.schemas import (
    CandidateSet,
    OnboardingMeta,
    PreferencesResponse,
    RecommendOut,
    UserStateOut,
)
from millie_rec.serving.schemas_should import DashboardOut, ShowcaseOut

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "demo" / "scripts" / "make_mock.py"
CONFIG = ROOT / "demo" / "config" / "onboarding.json"  # 읽기만 — 화면 텍스트 정본
INELIGIBLE = {18, 19, 20}  # conftest millie_serving_sample 주석 그대로
N_ELIGIBLE = 17  # 20 − 자격 없는 3권
FIXTURE_SEEDS = (1, 2, 3, 4, 5)
MAX_NEIGHBORS = 20

# 스크립트 상수를 import 하지 않고 손으로 적는다(tests/data/test_millie_export.py 관례).
CARD_KEYS = [
    "book_id",
    "title",
    "authors",
    "image_url",
    "categories",
    "publisher",
    "book_format",
    "pop_rank",
    "millie_label",
    "average_rating",
    "review_count",
    "completion_prob",
    "category_avg_prob",
    "expected_min",
    "difficulty",
    "formats",
]
CRITERIA_IDS = ["author", "publisher", "bestseller", "buzz", "review"]
STAGES = ["Candidate Retrieval", "Ranking", "Re-ranking"]
CONTRACT_FILES = {
    "meta_onboarding.json": OnboardingMeta,
    "candidates_onboarding.json": CandidateSet,
    "preferences_response.json": PreferencesResponse,
    "recommend_pop.json": RecommendOut,
    "recommend_cf.json": RecommendOut,
    "recommend_hybrid.json": RecommendOut,
    "recommend_hybrid_div.json": RecommendOut,
    "state.json": UserStateOut,
    "dashboard.json": DashboardOut,
    "showcase.json": ShowcaseOut,
}
# 카탈로그 축약본 2파일에만 적용한다(persona.description 은 PersonaOut 필수 필드).
FORBIDDEN = (
    '"description"',
    '"curator_note"',
    '"seg_dist"',
    '"millie_id"',
    '"tags"',
    '"shelf_count"',
)
FORBIDDEN_FILES = ("catalog_kr.json", "neighbors_kr.json")
# goodbooks 는 넣지 않는다 — data_notice 의 데이터셋 귀속 고지가 정본이다.
OLD_SHAPE = (
    '"format":',
    '"timestamp"',
    '"type": "rating"',
    '"readingtimes"',
    "static_popular",
    "csv_url",
    "zygmuntz",
    "hf.space",
    '"anchor_case"',
)
EVAL_TABLE = {
    "rows": [
        {
            "variant": v,
            "recall@20": r,
            "ndcg@10": n,
            "ild@10": i,
            "n_users": "2000",
            "split_mode": "holdout",
            "model_version": f"{v}_v1",
        }
        for v, r, n, i in (
            ("pop", "0.063", "0.054", "0.764"),
            ("cf", "0.117", "0.107", "0.643"),
            ("hybrid", "0.118", "0.110", "0.606"),
            ("hybrid_div", "0.116", "0.107", "0.684"),
        )
    ],
    "meta": {"dataset": "goodbooks-10k", "split_mode": "holdout", "n_users": 2000, "seed": 42},
}


def _load():
    """demo/scripts 는 패키지가 아니므로 경로로 직접 로드한다."""
    spec = importlib.util.spec_from_file_location("make_mock", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules["make_mock"] = module
    spec.loader.exec_module(module)
    return module


def _build_into(work: Path, sample: Path) -> Path:
    """fixture 20권 → work/demo/mock. 실 산출 경로는 읽지도 쓰지도 않는다."""
    eval_path = work / "eval_table.json"
    eval_path.write_text(json.dumps(EVAL_TABLE), encoding="utf-8")
    out = work / "demo" / "mock"
    _load().build(sample, out, CONFIG, eval_table=eval_path, seeds=FIXTURE_SEEDS)
    return out


@pytest.fixture(scope="module")
def built(tmp_path_factory, millie_serving_sample) -> Path:
    return _build_into(tmp_path_factory.mktemp("make_mock"), millie_serving_sample)


def _read(out: Path, name: str):
    return json.loads((out / name).read_text(encoding="utf-8"))


def test_contract_files_validate_against_schemas(built):
    for name, model in CONTRACT_FILES.items():
        model.model_validate(_read(built, name))


def test_recommend_shape_hybrid_div(built):
    d = _read(built, "recommend_hybrid_div.json")
    assert d["model_version"] == "hybrid_div_v1"
    assert isinstance(d["latency_ms"], float)
    assert d["latency_breakdown"]["total"] == d["latency_ms"]
    items = [i for r in d["rows"] for i in r["items"]]
    for row in d["rows"]:
        assert row["row_id"] in ROW_IDS or row["row_id"].startswith(ROW_ANCHOR_PREFIX)
    for item in items:
        assert item["badge"] is None or item["badge"]["type"] in BADGE_TYPES
    assert "itemknn" not in {ch for i in items for ch in i["source_channels"]}


def test_meta_criteria_ids_in_badge_order(built):
    meta = _read(built, "meta_onboarding.json")
    assert [c["id"] for c in meta["criteria"]] == CRITERIA_IDS
    assert all(c["label"] for c in meta["criteria"])
    assert len(meta["reading_times"]) == 5


def test_preferences_has_cell_and_snapshots_count(built):
    d = _read(built, "preferences_response.json")
    assert d["cell"] in {"A", "B"}
    assert d["snapshots_count"] >= 1


def test_catalog_rows_have_exactly_card_keys_and_only_eligible(built):
    rows = _read(built, "catalog_kr.json")
    assert len(rows) == N_ELIGIBLE
    ids = {r["book_id"] for r in rows}
    assert INELIGIBLE.isdisjoint(ids)
    for row in rows:
        assert list(row) == CARD_KEYS


def test_neighbors_top20_desc_eligible(built):
    ids = {r["book_id"] for r in _read(built, "catalog_kr.json")}
    nbrs = _read(built, "neighbors_kr.json")
    assert set(nbrs) == {str(i) for i in ids}
    for edges in nbrs.values():
        assert len(edges) <= MAX_NEIGHBORS
        weights = [w for _, w in edges]
        assert weights == sorted(weights, reverse=True)
        for edge in edges:
            assert len(edge) == 2
            assert edge[0] in ids


def test_showcase_eval_table_floats_and_personal_case(built):
    sc = _read(built, "showcase.json")
    first = sc["eval_table"]["rows"][0]
    assert isinstance(first["recall_at_20"], float)
    assert first["recall_at_20"] == 0.063
    assert sc["eval_table"]["split_mode"] == "holdout"
    assert [m["stage"] for m in sc["metric_mapping"]] == STAGES
    case = sc["personal_case"]
    assert len(case["seeds"]) == len(FIXTURE_SEEDS)
    assert 1 <= len(case["recommendations"]) <= 10
    for rec in case["recommendations"]:
        assert rec["reason"].startswith("『")
        assert rec["reason"].endswith("』을 좋아하셨다면")


def test_personal_case_and_library_cards_carry_authors(built):
    """저자는 쇼케이스 본인 5권·서재 카드에도 실린다(06-UAT Gap 1 · 동명 도서 구분 D-07b ③)."""
    case = _read(built, "showcase.json")["personal_case"]
    for book in case["seeds"] + case["recommendations"]:
        assert book.get("authors"), book["book_id"]
    for bucket in _read(built, "state.json")["library"].values():
        for book in bucket:
            assert book.get("authors"), book["book_id"]


def test_manifest_records_seed_and_input_digests(built):
    manifest = _read(built, "_manifest.json")
    assert manifest["seed"] == 42
    assert set(manifest["inputs"]) >= {"books_kr.json", "item_edges_kr.json", "onboarding.json"}
    assert manifest["outputs"]["catalog_kr.json"] > 0


def test_build_is_deterministic(tmp_path_factory, millie_serving_sample):
    first = _build_into(tmp_path_factory.mktemp("mm_a"), millie_serving_sample)
    second = _build_into(tmp_path_factory.mktemp("mm_b"), millie_serving_sample)
    names = sorted(p.name for p in first.glob("*.json") if p.name != "_manifest.json")
    assert names == sorted(p.name for p in second.glob("*.json") if p.name != "_manifest.json")
    for name in names:
        assert (first / name).read_bytes() == (second / name).read_bytes(), name


def test_outputs_exclude_forbidden_and_old_shape(built):
    for name in FORBIDDEN_FILES:
        raw = (built / name).read_text(encoding="utf-8")
        for key in FORBIDDEN:
            assert raw.count(key) == 0, (name, key)
    for path in built.glob("*.json"):
        raw = path.read_text(encoding="utf-8").casefold()
        for mark in OLD_SHAPE:
            assert mark not in raw, (path.name, mark)
    assert not (built / "books.json").exists()
    assert not (built.parent / "fallback").exists()
