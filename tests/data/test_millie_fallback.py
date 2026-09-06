"""demo/fallback/popular.json 3종 테스트.

계약(RecommendOut 파싱·상수 동일) · 정확성(eligible 상위 40·pop_rank 순·점수)
· 안전성(format 키 없음·description 누출 0).
"""

import importlib.util
import json
import sys
from pathlib import Path

import pandas as pd
import pytest

from millie_rec.contracts import FALLBACK_GLOBAL_POP, MODEL_VERSION_FALLBACK
from millie_rec.serving import fallback as fb
from millie_rec.serving.schemas import RecommendOut

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "tests" / "fixtures" / "millie" / "sample_records.jsonl"

ELIGIBLE = 11  # 픽스처 12권 중 image_url 없는 '달러구트 꿈 백화점' 1권만 비자격(D-14)
TOP_TITLE = "불편한 편의점 (재수집)"  # shelf 9,814 → pop_rank 1
ITEM_KEYS = {
    "book_id", "score", "source", "reason", "title", "authors",
    "image_url", "position", "source_channels", "badge", "book_format", "difficulty",
}  # fmt: skip


def _load(name: str):
    """scripts/ 는 패키지가 아니므로 경로로 직접 로드한다."""
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _items(payload: dict) -> list[dict]:
    rows = payload.get("rows") or []
    return rows[0].get("items", []) if rows else []


@pytest.fixture(scope="module")
def books(tmp_path_factory) -> pd.DataFrame:
    out = tmp_path_factory.mktemp("processed")
    _load("build_millie_catalog").build(FIXTURE, out, raw_dir=out)
    return pd.read_parquet(out / "books_kr.parquet")


@pytest.fixture(scope="module")
def fb_mod():
    return _load("export_millie_fallback")


@pytest.fixture(scope="module")
def exported(books, fb_mod, tmp_path_factory) -> tuple[dict, str]:
    work = tmp_path_factory.mktemp("fallback")
    books_path = work / "books_kr.parquet"
    books.to_parquet(books_path)
    out = work / "popular.json"
    fb_mod.export_fallback(books_path, out)
    text = out.read_text(encoding="utf-8")
    return json.loads(text), text


def test_validates_as_recommend_out(exported):
    payload, _ = exported
    assert "fallback_level" in payload, "스텁 payload — level 3 응답 형태가 아직 없다"
    RecommendOut.model_validate(payload)
    assert payload["fallback_level"] == FALLBACK_GLOBAL_POP == 3
    assert payload["model_version"] == MODEL_VERSION_FALLBACK
    assert payload["items"] == []  # level 3 은 평탄화 없음(compose.build_response)
    assert isinstance(payload["latency_ms"], float)
    assert payload["latency_breakdown"] == {"total": 0.0}
    assert payload["user_state_weights"] == {"alpha": 0.0, "beta": 0.0, "gamma": 0.0}


def test_constants_match_serving_fallback(exported, fb_mod):
    payload, _ = exported
    assert fb_mod.TRENDING_ROW_ID == fb.TRENDING_ROW_ID
    assert fb_mod.TRENDING_TITLE == fb.TRENDING_TITLE
    assert fb_mod.TRENDING_PURPOSE == fb.TRENDING_PURPOSE
    assert fb_mod.SOURCE_POPULARITY == fb.SOURCE_POPULARITY
    assert payload.get("rows"), "스텁 payload — trending 행이 없다"
    row = payload["rows"][0]
    assert row["row_id"] == fb.TRENDING_ROW_ID
    assert row["title"] == fb.TRENDING_TITLE
    assert row["purpose"] == fb.TRENDING_PURPOSE


def test_items_are_eligible_top_by_pop_rank(exported, books):
    payload, _ = exported
    items = _items(payload)
    assert len(items) == ELIGIBLE
    assert items[0]["title"] == TOP_TITLE
    expected = [
        int(row["book_id"])
        for row in books.sort_values("pop_rank").to_dict("records")
        if isinstance(row.get("image_url"), str) and row["image_url"] and row.get("title")
    ]
    assert [i["book_id"] for i in items] == expected
    assert payload["rows"][0]["channel_mix"] == {"popularity": ELIGIBLE}


def test_scores_positions_and_channels(exported):
    payload, _ = exported
    items = _items(payload)
    assert len(items) == ELIGIBLE
    assert [i["score"] for i in items] == [float(ELIGIBLE - k) for k in range(ELIGIBLE)]
    assert [i["position"] for i in items] == list(range(ELIGIBLE))
    assert {i["source"] for i in items} == {"popularity"}
    assert all(i["source_channels"] == ["popularity"] for i in items)
    assert all(i["badge"] is None and i["reason"] is None for i in items)


def test_item_keys_are_item_out_fields_only(exported):
    payload, _ = exported
    items = _items(payload)
    assert len(items) == ELIGIBLE
    assert all(set(i) == ITEM_KEYS for i in items)  # 'format' 키 금지(extra="forbid")


def test_no_author_text_leaks(exported, books):
    payload, text = exported
    assert len(_items(payload)) == ELIGIBLE
    assert text.count('"description"') == 0
    assert text.count('"curator_note"') == 0
    head = str(books["description"].iloc[0])[:20]
    assert head and head not in text


def test_n_cap_and_nan_difficulty_null(exported, fb_mod, books):
    capped = fb_mod.payload(books, n=3)
    assert _items(capped), "스텁 payload — items 가 없다"
    assert len(_items(capped)) == 3
    source = dict(zip(books["book_id"], books["difficulty_source"], strict=True))
    for item in _items(exported[0]):
        if source[item["book_id"]] == "category_prior":
            assert item["difficulty"] is None
        else:
            assert 0.0 < item["difficulty"] < 1.0
