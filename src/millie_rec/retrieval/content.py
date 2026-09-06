"""contracts.ItemVectors + CandidateGenerator — Goodbooks tags TF-IDF 벡터 +
성분별 평균 벡터 cosine 후보(D-04·D-14).
"""

from collections.abc import Sequence
from typing import TYPE_CHECKING

import numpy as np

from millie_rec.contracts import COL_ITEM, Candidate, ItemVectors, UserState
from millie_rec.retrieval.neighbors import SOURCE_CONTENT, WeightFn, component_weights

if TYPE_CHECKING:
    import pandas as pd

TAGS_COL = "tags"  # books.parquet 계약 컬럼. COL_* 상수 없음 → 여기 1회 정의
TOKEN_PATTERN = r"\S+"  # 하이픈 태그(young-adult)를 한 토큰으로


def _query(vectors: ItemVectors, user: UserState, weights: "WeightFn | None") -> np.ndarray:
    """q = Σ_성분 w · mean(성분 아이템 벡터). 미지 id 는 0 벡터라 자연히 빠진다."""
    w = component_weights(user, weights)
    parts = (
        (user.explicit_seeds, w.get("alpha", 0.0)),
        (user.history, w.get("beta", 0.0)),
        (user.session, w.get("gamma", 0.0)),
    )
    q: np.ndarray | None = None
    for items, wc in parts:
        if not items or wc == 0.0:
            continue
        v = wc * vectors.vectors(list(items)).mean(axis=0)
        q = v if q is None else q + v
    return q if q is not None else np.zeros(vectors.vectors([]).shape[1], dtype=float)


def _topk_cosine(
    scores: np.ndarray, ids: np.ndarray, seen: frozenset[int], k: int, source: str
) -> list[Candidate]:
    """점수 > 0 이고 seen 이 아닌 상위 k. argpartition 크기 k + len(seen)(넉넉히 뽑기)."""
    scores = np.asarray(scores, dtype=float).ravel()
    if k <= 0 or scores.size == 0 or not (scores > 0).any():
        return []
    n = min(scores.size, k + len(seen))
    idx = np.argpartition(-scores, n - 1)[:n]
    idx = idx[np.lexsort((ids[idx], -scores[idx]))]  # (−score, id) 결정적 정렬
    out = [
        Candidate(book_id=int(ids[i]), source=source, score=float(scores[i]))
        for i in idx
        if scores[i] > 0 and int(ids[i]) not in seen
    ]
    return out[:k]


class ContentVectors:
    """L2 정규화 dense 벡터. 미지 id 는 0 벡터(ILD 에서 거리 1)."""

    name = SOURCE_CONTENT

    def __init__(
        self,
        books: "pd.DataFrame",
        text_col: str = TAGS_COL,
        *,
        weights: "WeightFn | None" = None,
    ) -> None:
        # sklearn 은 여기서만 import — 서버가 retrieval 공개 표면을 읽어도 sklearn 을 끌어오지 않게
        from sklearn.feature_extraction.text import TfidfVectorizer

        texts = books[text_col].fillna("").astype(str).tolist()
        vec = TfidfVectorizer(analyzer="word", token_pattern=TOKEN_PATTERN)  # norm="l2" 기본
        self._matrix = vec.fit_transform(texts)  # (n_books, dim), 행 L2=1(빈 문서는 0)
        self._index = {int(b): i for i, b in enumerate(books[COL_ITEM].tolist())}
        self._ids = np.asarray(books[COL_ITEM].to_numpy(), dtype=np.int64)  # _index 의 역
        self._weights = weights

    @property
    def dim(self) -> int:
        return int(self._matrix.shape[1])

    def vectors(self, book_ids: Sequence[int]) -> np.ndarray:
        out = np.zeros((len(book_ids), self.dim), dtype=float)
        rows = [(i, self._index[int(b)]) for i, b in enumerate(book_ids) if int(b) in self._index]
        if rows:
            dst, src = zip(*rows, strict=True)
            out[list(dst)] = self._matrix[list(src)].toarray()
        return out

    def fit(self, train: "pd.DataFrame") -> "ContentVectors":
        return self  # 벡터는 books 로 이미 만들어졌다 — 하네스·Protocol 대칭용 no-op

    def retrieve(self, user: UserState, k: int) -> list[Candidate]:
        q = _query(self, user, self._weights)
        scores = np.asarray(self._matrix @ q).ravel()
        return _topk_cosine(scores, self._ids, user.seen, k, SOURCE_CONTENT)


class VectorRetriever:
    """ItemVectors(Track B VectorsKR) 위의 content 후보.

    생성 시 dense 행렬 1회(9,450×128 ≈ 9.7MB), 요청마다 재계산 없음.
    """

    name = SOURCE_CONTENT

    def __init__(
        self,
        vectors: ItemVectors,
        ids: Sequence[int],
        *,
        source: str = SOURCE_CONTENT,
        weights: "WeightFn | None" = None,
    ) -> None:
        self._vectors = vectors
        self._ids = np.asarray([int(b) for b in ids], dtype=np.int64)
        self._matrix = (
            np.asarray(vectors.vectors(list(self._ids)), dtype=float)
            if len(self._ids)
            else np.zeros((0, 0))
        )
        self._source, self._weights = source, weights

    def fit(self, train: "pd.DataFrame") -> "VectorRetriever":
        return self

    def retrieve(self, user: UserState, k: int) -> list[Candidate]:
        if self._matrix.size == 0:
            return []
        q = _query(self._vectors, user, self._weights)
        scores = self._matrix @ q
        return _topk_cosine(scores, self._ids, user.seen, k, self._source)
