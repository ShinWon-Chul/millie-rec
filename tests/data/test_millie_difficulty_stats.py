"""난이도 분포 요약 — 계약(키 집합) · 정확성(손계산 p50·mean·정렬) · 안전성(결측·0분모)."""

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]

STAT_KEYS = {"min", "p10", "p50", "p90", "max", "mean", "std"}


def _load(name: str):
    """scripts/ 는 패키지가 아니므로 경로로 직접 로드한다."""
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def mod():
    return _load("millie_difficulty_stats")


def _row(book_id, cat, diff, cprob, resid_z):
    return {
        "book_id": book_id,
        "title": f"책{book_id}",
        "categories": [cat],
        "difficulty": diff,
        "difficulty_source": "category_prior" if diff is None else "millie_index",
        "completion_prob": cprob,
        "resid_z": resid_z,
    }


def _rows() -> list[dict]:
    """8권. difficulty 6권(0.1~0.9) + 결측 2권. 카테고리 3종."""
    return [
        _row(1, "소설", 0.10, 90, -1.0),
        _row(2, "소설", 0.30, 70, -0.5),
        _row(3, "소설", 0.50, 50, 0.0),
        _row(4, "인문", 0.70, 30, 0.5),
        _row(5, "인문", 0.90, 10, 1.0),
        _row(6, "인문", None, None, 0.0),
        _row(7, "에세이/시", 0.20, 80, -0.8),
        _row(8, "에세이/시", None, None, 0.0),
    ]


def test_summarize_returns_contract_keys_and_types(mod):
    out = mod.summarize(_rows())
    assert set(out) == {
        "n_books",
        "n_difficulty",
        "coverage",
        "by_source",
        "difficulty",
        "resid_z",
        "completion_prob",
        "by_category",
        "hardest_easiest",
    }
    assert out["n_books"] == 8
    assert out["n_difficulty"] == 6
    assert out["coverage"] == 0.75
    assert out["by_source"] == {"millie_index": 6, "category_prior": 2}
    for key in ("difficulty", "resid_z", "completion_prob"):
        assert set(out[key]) == STAT_KEYS
    assert isinstance(out["by_category"], list)
    assert set(out["hardest_easiest"]) == {"hardest", "easiest"}


def test_summarize_percentiles_match_hand_calculation(mod):
    out = mod.summarize(_rows())
    d = out["difficulty"]
    # 정렬 [0.1,0.2,0.3,0.5,0.7,0.9] · 선형보간 pos=q*(n-1)
    assert (d["min"], d["max"]) == (0.1, 0.9)
    assert d["p10"] == 0.15
    assert d["p50"] == 0.4
    assert d["p90"] == 0.8
    assert d["mean"] == 0.45
    assert d["std"] == pytest.approx(0.2814, abs=1e-4)  # 모집단 표준편차
    c = out["completion_prob"]
    assert (c["mean"], c["p50"]) == (55.0, 60.0)
    assert out["resid_z"]["mean"] == -0.1  # 결측 없음 → 8권 전부


def test_summarize_by_category_sorted_by_difficulty_desc(mod):
    out = mod.summarize(_rows())
    assert [c["category"] for c in out["by_category"]] == ["인문", "소설", "에세이/시"]
    assert out["by_category"][0] == {
        "category": "인문",
        "n": 3,
        "difficulty_mean": 0.8,
        "completion_prob_mean": 20.0,
    }
    assert out["by_category"][1]["difficulty_mean"] == 0.3
    assert out["by_category"][1]["completion_prob_mean"] == 70.0


def test_summarize_by_category_keeps_only_top_n_by_count(mod):
    rows = [_row(100 + i, f"c{i}", 0.5, 50, 0.0) for i in range(mod.TOP_CATEGORIES + 3)]
    out = mod.summarize(rows)
    assert len(out["by_category"]) == mod.TOP_CATEGORIES


def test_summarize_extremes_are_ordered_and_named(mod):
    he = mod.summarize(_rows())["hardest_easiest"]
    assert [b["book_id"] for b in he["hardest"]] == [5, 4, 3]
    assert [b["book_id"] for b in he["easiest"]] == [1, 7, 2]
    assert he["hardest"][0] == {
        "book_id": 5,
        "title": "책5",
        "category": "인문",
        "difficulty": 0.9,
    }


def test_summarize_all_missing_difficulty_yields_zero_coverage_without_zero_division(mod):
    rows = [_row(i, "소설", None, None, 0.0) for i in (1, 2, 3)]
    out = mod.summarize(rows)
    assert out["n_difficulty"] == 0
    assert out["coverage"] == 0.0
    assert out["difficulty"] is None
    assert out["completion_prob"] is None
    assert out["hardest_easiest"] == {"hardest": [], "easiest": []}
    assert out["by_category"] == [
        {"category": "소설", "n": 3, "difficulty_mean": None, "completion_prob_mean": None}
    ]
    assert mod.summarize([])["coverage"] == 0.0
