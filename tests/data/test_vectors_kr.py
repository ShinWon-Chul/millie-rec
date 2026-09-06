"""data/vectors_kr.py — 계약(shape·dim) · 정확성(L2 norm·입력 순서) · 안전성(미지 id 0 벡터)."""

from pathlib import Path

import numpy as np
import pytest

from millie_rec.data import VECTORS_KR_NPZ, VectorsKR

DIM = 8  # conftest millie_serving_sample 의 SAMPLE_VECTOR_DIM


@pytest.fixture(scope="module")
def vec(millie_serving_sample: Path) -> VectorsKR:
    return VectorsKR.load(millie_serving_sample / VECTORS_KR_NPZ)


def test_vectors_shape_and_dim(vec: VectorsKR) -> None:
    assert vec.dim == DIM
    assert vec.vectors([1, 2, 3]).shape == (3, DIM)
    assert vec.vectors([]).shape == (0, DIM)


def test_rows_are_l2_normalized(vec: VectorsKR) -> None:
    v = vec.vectors(list(range(1, 21)))
    assert np.linalg.norm(v, axis=1) == pytest.approx(1.0, abs=1e-5)


def test_order_preserved_and_unknown_is_zero(vec: VectorsKR) -> None:
    v = vec.vectors([3, 999, 1])
    assert v[0].any() and v[2].any()
    assert not v[1].any()
    assert np.allclose(v[0], vec.vectors([3])[0])
    assert np.allclose(v[2], vec.vectors([1])[0])


def test_load_from_npz_written_with_savez(tmp_path: Path) -> None:
    np.savez(
        tmp_path / "v.npz", book_ids=np.array([10, 20, 30]), vectors=np.eye(3, dtype=np.float32)
    )
    loaded = VectorsKR.load(tmp_path / "v.npz")
    assert loaded.vectors([20])[0].tolist() == [0.0, 1.0, 0.0]


def test_book_ids_lists_npz_order(vec: VectorsKR) -> None:
    """Phase 4 D-10: Track B content 채널이 eligible 필터 전 전체 id 를 npz 저장 순서로 본다."""
    assert vec.book_ids == list(range(1, 21))
