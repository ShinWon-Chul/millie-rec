"""cf 후보 — contracts.CandidateGenerator + Neighbors 구현.

train 이진 user×item cosine, 아이템당 이웃 KNN_TOP, npz 캐시(D-04).
"""

import logging
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

from millie_rec.contracts import COL_ITEM, COL_USER, DIR_ARTIFACTS, Candidate, UserState
from millie_rec.retrieval.neighbors import WeightFn, retrieve_from_neighbors

if TYPE_CHECKING:
    import pandas as pd

log = logging.getLogger(__name__)
SOURCE_ITEMKNN = "itemknn"  # contracts.Candidate.source 허용값. Track A 전용(data.md)
KNN_TOP = 50  # D-04 아이템당 이웃. freeze(D-14 ①)
POOL = 200  # D-04 채널별 후보 풀. app StagedPipeline 이 retrieve(user, POOL) 로 부른다
CHUNK = 500  # (CHUNK × n_items) dense 한 장 = 500×10k×8B = 40MB — dense 10k×10k 금지(아키 §8)
ARTIFACT_NAME = "item_neighbors.npz"
KNN_ARTIFACT = DIR_ARTIFACTS / ARTIFACT_NAME  # artifacts/* 는 gitignore(artifacts/serving 예외)


def _meta(train: "pd.DataFrame") -> tuple[int, int, int]:
    """캐시 무효화 키 — 파일 존재만 보면 필터 상수 변경 후 옛 이웃을 써 재현성이 깨진다."""
    return (len(train), int(train[COL_USER].nunique()), int(train[COL_ITEM].nunique()))


class ItemKNNRetriever:
    """이웃 테이블(book_ids · nbr_ids[n,KNN_TOP] · nbr_sims) 을 쥔다. -1/0.0 은 패딩."""

    name = "cf"  # contracts.VARIANTS[1] 과 같은 값 — 문자열 리터럴(계약 상수 import 불필요)

    def __init__(
        self,
        book_ids: "np.ndarray | None" = None,
        nbr_ids: "np.ndarray | None" = None,
        nbr_sims: "np.ndarray | None" = None,
        *,
        meta: tuple[int, int, int] = (0, 0, 0),
        weights: "WeightFn | None" = None,
    ) -> None:
        self._ids = np.asarray(book_ids if book_ids is not None else [], dtype=np.int64)
        empty = np.zeros((0, KNN_TOP))
        self._nbr_ids = np.asarray(nbr_ids if nbr_ids is not None else empty, dtype=np.int64)
        self._nbr_sims = np.asarray(nbr_sims if nbr_sims is not None else empty, dtype=np.float32)
        self._index = {int(b): i for i, b in enumerate(self._ids.tolist())}
        self._meta = tuple(int(x) for x in meta)
        self._weights = weights

    @property
    def meta(self) -> tuple[int, int, int]:
        return self._meta

    def fit(self, train: "pd.DataFrame") -> "ItemKNNRetriever":
        import scipy.sparse as sp  # 서버가 retrieval 공개 표면을 읽어도 scipy 를 끌어오지 않게

        users, u_idx = np.unique(train[COL_USER].to_numpy(), return_inverse=True)
        items, i_idx = np.unique(train[COL_ITEM].to_numpy(), return_inverse=True)
        ones = np.ones(len(train), dtype=np.float32)
        x = sp.csr_matrix((ones, (u_idx, i_idx)), shape=(len(users), len(items)))
        x.data[:] = 1.0  # 중복 (user,item) 이 합쳐져 2 가 되지 않게 — 이진
        norms = np.sqrt(np.asarray(x.multiply(x).sum(axis=0)).ravel())
        xn = x @ sp.diags(1.0 / np.where(norms == 0, 1.0, norms))  # 열 L2=1
        xnt = xn.T.tocsr()
        n = len(items)
        top = min(KNN_TOP, n - 1)  # 합성 3~4 아이템 가드(argpartition kth < n)
        nbr_ids = np.full((n, KNN_TOP), -1, dtype=np.int64)
        nbr_sims = np.zeros((n, KNN_TOP), dtype=np.float32)
        for s in range(0, n, CHUNK):
            if top <= 0:
                break
            block = np.asarray((xnt[s : s + CHUNK] @ xn).todense())  # (chunk, n) cosine
            rows = np.arange(block.shape[0])
            block[rows, s + rows] = -1.0  # self 제외
            idx = np.argpartition(-block, top - 1, axis=1)[:, :top]
            sims = np.take_along_axis(block, idx, axis=1)
            order = np.argsort(-sims, axis=1, kind="stable")
            idx = np.take_along_axis(idx, order, axis=1)
            sims = np.take_along_axis(sims, order, axis=1)
            keep = sims > 0  # 공동 소비 0 은 이웃이 아니다
            nbr_ids[s : s + CHUNK, :top] = np.where(keep, items[idx], -1)
            nbr_sims[s : s + CHUNK, :top] = np.where(keep, sims, 0.0).astype(np.float32)
        self._ids, self._nbr_ids, self._nbr_sims = items.astype(np.int64), nbr_ids, nbr_sims
        self._index = {int(b): i for i, b in enumerate(items.tolist())}
        self._meta = _meta(train)
        return self

    def neighbors(self, book_id: int, n: int = KNN_TOP) -> list[tuple[int, float]]:
        i = self._index.get(int(book_id))
        if i is None:
            return []
        ids, sims = self._nbr_ids[i], self._nbr_sims[i]
        m = ids >= 0  # 패딩 제외. fit 이 이미 sim 내림차순으로 저장했다
        return [
            (int(b), float(s))
            for b, s in zip(ids[m][:n].tolist(), sims[m][:n].tolist(), strict=True)
        ]

    def retrieve(self, user: UserState, k: int) -> list[Candidate]:
        return retrieve_from_neighbors(
            self, user, k, source=SOURCE_ITEMKNN, weights=self._weights, n_neighbors=KNN_TOP
        )

    def save(self, path: Path = KNN_ARTIFACT) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        np.savez(
            path,
            book_ids=self._ids,
            nbr_ids=self._nbr_ids,
            nbr_sims=self._nbr_sims,
            meta=np.asarray(self._meta, dtype=np.int64),
        )
        return path

    @classmethod
    def load(
        cls, path: Path = KNN_ARTIFACT, *, weights: "WeightFn | None" = None
    ) -> "ItemKNNRetriever":
        with np.load(path) as z:  # allow_pickle 기본 False 유지 — 숫자 배열 4키만
            return cls(
                z["book_ids"],
                z["nbr_ids"],
                z["nbr_sims"],
                meta=tuple(int(x) for x in z["meta"]),
                weights=weights,
            )


def load_or_fit_itemknn(
    train: "pd.DataFrame", path: Path | None = None, *, weights: "WeightFn | None" = None
) -> ItemKNNRetriever:
    """캐시 meta 가 train 과 같으면 로드, 아니면 fit 후 저장. path None 이면 저장 안 함."""
    want = _meta(train)
    if path is not None and path.exists():
        try:
            cached = ItemKNNRetriever.load(path, weights=weights)
            if cached.meta == want:
                return cached
            log.info("itemknn cache meta %s != train %s — refit", cached.meta, want)
        except (OSError, ValueError, KeyError):
            log.exception("itemknn cache unreadable at %s — refit", path)
    fitted = ItemKNNRetriever(weights=weights).fit(train)
    if path is not None:
        fitted.save(path)
    return fitted
