"""난이도 파생 — 계약(3컬럼·입력 불변) · 정확성(부호·σ 항등·len_z) · 안전성(결측·소표본)."""

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]


def _load(name: str):
    """scripts/ 는 패키지가 아니므로 경로로 직접 로드한다."""
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def diff_mod():
    return _load("millie_difficulty")


def _frame() -> pd.DataFrame:
    """손계산용 13행. 소설 8권(4분위 셀마다 ±10 잔차) · 에세이 3권 · 결측 2권."""
    book_id = list(range(1, 14))
    categories = [["소설"]] * 8 + [["에세이"]] * 3 + [["에세이"], ["소설"]]
    expected_min = [10, 20, 30, 40, 50, 60, 70, 80, 30, 60, 90, 120, None]
    completion_prob = [80, 60, 70, 50, 60, 40, 50, 30, 55, 50, 45, 50, 61]
    source = ["millie_index"] * 11 + ["category_prior"] * 2
    return pd.DataFrame(
        {
            "book_id": book_id,
            "categories": categories,
            "completion_prob": pd.array(completion_prob, dtype="Int64"),
            "expected_min": pd.array(expected_min, dtype="Int64"),
            "difficulty_source": source,
        }
    )


def test_add_difficulty_appends_three_float_columns_and_keeps_input(diff_mod):
    inp = _frame()
    out = diff_mod.add_difficulty(inp)
    assert set(out.columns) == set(inp.columns) | {"resid_z", "len_z", "difficulty"}
    assert len(out) == 13
    pd.testing.assert_frame_equal(out[inp.columns], inp)
    for col in ("resid_z", "len_z", "difficulty"):
        assert out[col].dtype.kind == "f", col


def test_resid_z_sign_follows_within_cell_residual(diff_mod, monkeypatch):
    monkeypatch.setattr(diff_mod, "MIN_CATEGORY_SAMPLE", 4)
    out = diff_mod.add_difficulty(_frame())
    assert "resid_z" in out.columns
    out = out.set_index("book_id")
    for hi, lo in ((1, 2), (3, 4), (5, 6), (7, 8)):
        assert out.loc[hi, "resid_z"] > 0 > out.loc[lo, "resid_z"]
        assert out.loc[hi, "resid_z"] == pytest.approx(-out.loc[lo, "resid_z"])
    assert out.loc[1, "difficulty"] < 0.5 < out.loc[2, "difficulty"]


def test_difficulty_is_sigmoid_of_negative_resid_z(diff_mod):
    out = diff_mod.add_difficulty(_frame())
    assert "difficulty" in out.columns
    out = out.set_index("book_id")
    for bid in range(1, 12):
        assert out.loc[bid, "difficulty"] == pytest.approx(
            1.0 / (1.0 + np.exp(out.loc[bid, "resid_z"]))
        ), bid
    assert pd.isna(out.loc[12, "difficulty"])
    assert pd.isna(out.loc[13, "difficulty"])


def test_missing_completion_prob_gives_zero_resid_and_none_difficulty(diff_mod):
    out = diff_mod.add_difficulty(_frame())
    assert "resid_z" in out.columns and "len_z" in out.columns
    out = out.set_index("book_id")
    for bid in (12, 13):
        assert out.loc[bid, "resid_z"] == 0.0, bid
        assert pd.isna(out.loc[bid, "difficulty"]), bid
    assert np.isfinite(out.loc[12, "len_z"])
    assert pd.isna(out.loc[13, "len_z"])


def test_small_category_uses_global_bins_and_stays_finite(diff_mod):
    out = diff_mod.add_difficulty(_frame())
    assert "resid_z" in out.columns
    out = out.set_index("book_id")
    measured = out.loc[1:11, "resid_z"]
    assert np.isfinite(measured.to_numpy(dtype=float)).all()
    assert (out.loc[[9, 10, 11], "resid_z"] != 0).any()


def test_len_z_is_within_category_zscore_of_expected_min(diff_mod):
    out = diff_mod.add_difficulty(_frame())
    assert "len_z" in out.columns
    out = out.set_index("book_id")
    assert out.loc[1, "len_z"] == pytest.approx(-35 / 24.494897, abs=1e-3)
    assert out.loc[8, "len_z"] == pytest.approx(35 / 24.494897, abs=1e-3)
