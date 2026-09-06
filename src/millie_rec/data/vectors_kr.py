"""Track B 다양성 벡터 어댑터 — content_vectors_kr.npz 기동 1회 로드 (DATA-07, Phase 4 hybrid_div).

contracts.ItemVectors 구현. retrieval/content.py 와 같은 규약(미지 id = 0 벡터).
"""

from collections.abc import Sequence
from pathlib import Path

import numpy as np

from millie_rec.data.catalog_kr import DIR_SERVING

VECTORS_KR_NPZ = "content_vectors_kr.npz"


class VectorsKR:
    """L2 정규화 dense 벡터(npz). 미지 id 는 0 벡터(ILD 에서 거리 1)."""

    def __init__(self, book_ids: np.ndarray, vectors: np.ndarray) -> None:
        self._matrix = np.asarray(vectors, dtype=float)
        self._index = {int(b): i for i, b in enumerate(np.asarray(book_ids).tolist())}

    @classmethod
    def load(cls, path: Path = DIR_SERVING / VECTORS_KR_NPZ) -> "VectorsKR":
        with np.load(path) as z:  # 파일 핸들을 닫는다
            return cls(z["book_ids"], z["vectors"])

    @property
    def dim(self) -> int:
        return int(self._matrix.shape[1])

    @property
    def book_ids(self) -> list[int]:
        return list(
            self._index
        )  # npz 저장 순서. Track B content 채널이 eligible 필터 전 전체 id 열람(D-10)

    def vectors(self, book_ids: Sequence[int]) -> np.ndarray:
        out = np.zeros((len(book_ids), self.dim), dtype=float)
        rows = [(i, self._index[int(b)]) for i, b in enumerate(book_ids) if int(b) in self._index]
        if rows:
            dst, src = zip(*rows, strict=True)
            out[list(dst)] = self._matrix[list(src)]
        return out
