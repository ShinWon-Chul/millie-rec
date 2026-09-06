"""content_vectors_kr.npz 3종 테스트.

계약(키·dtype·shape) · 정확성(L2·재현성·id 정렬) · 안전성(소표본 dim 가드·크기).
"""

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "tests" / "fixtures" / "millie" / "sample_records.jsonl"

N_BOOKS = 12  # 픽스처 14줄 → status 200 ∧ dedup 후 12권
EXPECTED_DIM = 11  # min(SVD_DIM, n-1, features-1) — 12권이면 n-1 이 구속
MAX_BYTES = 50 * 1024 * 1024


def _load(name: str):
    """scripts/ 는 패키지가 아니므로 경로로 직접 로드한다."""
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def processed(tmp_path_factory) -> Path:
    out = tmp_path_factory.mktemp("processed")
    _load("build_millie_catalog").build(FIXTURE, out, raw_dir=out)
    return out


@pytest.fixture(scope="module")
def books(processed) -> pd.DataFrame:
    return pd.read_parquet(processed / "books_kr.parquet")


@pytest.fixture(scope="module")
def vec_mod():
    return _load("export_millie_vectors")


@pytest.fixture(scope="module")
def npz(processed, vec_mod, tmp_path_factory):
    out = tmp_path_factory.mktemp("vectors") / "content_vectors_kr.npz"
    vec_mod.export_vectors(processed / "books_kr.parquet", out)
    return np.load(out)


def test_npz_has_book_ids_and_vectors_with_dtypes(npz):
    assert set(npz.files) == {"book_ids", "vectors"}
    assert npz["book_ids"].dtype == np.int64
    assert npz["vectors"].dtype == np.float32
    assert npz["book_ids"].shape[0] == N_BOOKS
    assert npz["vectors"].shape[0] == N_BOOKS


def test_dim_is_min_of_128_and_sample_guard(npz, vec_mod):
    assert vec_mod.SVD_DIM == 128
    assert npz["vectors"].shape[1] == EXPECTED_DIM


def test_rows_are_l2_normalized(npz):
    vectors = npz["vectors"]
    assert vectors.shape[0] == N_BOOKS
    norms = np.linalg.norm(vectors, axis=1).tolist()
    assert norms == pytest.approx([1.0] * N_BOOKS, abs=1e-4)


def test_book_ids_sorted_and_match_books(npz, books):
    assert npz["book_ids"].tolist() == sorted(int(b) for b in books["book_id"])


def test_export_is_deterministic_and_under_cap(tmp_path, processed, vec_mod):
    books_path = processed / "books_kr.parquet"
    first, second = tmp_path / "a.npz", tmp_path / "b.npz"
    size = vec_mod.export_vectors(books_path, first)
    vec_mod.export_vectors(books_path, second)
    left, right = np.load(first), np.load(second)
    assert left["vectors"].shape == (N_BOOKS, EXPECTED_DIM)
    assert np.array_equal(left["vectors"], right["vectors"])
    assert np.array_equal(left["book_ids"], right["book_ids"])
    assert size == first.stat().st_size < MAX_BYTES
