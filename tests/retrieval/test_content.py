"""ItemVectors 구현 — 계약(shape·ndarray) · 정확성(L2 norm·직교) · 안전성(미지 id·빈 태그).

retrieve() 증분(Phase 4 REC-01): 계약(Candidate·source) · 정확성(성분 가중)
· 안전성(미지 seed·seen).
"""

import numpy as np
import pandas as pd
import pytest

from millie_rec.contracts import COL_ITEM, Candidate, UserState
from millie_rec.retrieval.content import ContentVectors, VectorRetriever

DIM = 5  # 어휘 {fantasy, magic, romance, history, war}


def _books() -> pd.DataFrame:
    return pd.DataFrame(
        {
            COL_ITEM: [10, 20, 30],
            "tags": ["fantasy magic", "magic romance", "history war"],
        }
    )


# ── 계약 ──
def test_vectors_shape_and_type() -> None:
    cv = ContentVectors(_books())
    v = cv.vectors([10, 20, 30])
    assert isinstance(v, np.ndarray)
    assert v.shape == (3, DIM)
    assert cv.vectors([]).shape == (0, DIM)


# ── 정확성 ──
def test_vectors_rows_are_l2_normalized_and_orthogonal_when_no_shared_tags() -> None:
    v = ContentVectors(_books()).vectors([10, 20, 30])
    assert all(abs(float(np.linalg.norm(row)) - 1.0) < 1e-9 for row in v)
    assert float(v[0] @ v[2]) == 0.0
    assert float(v[0] @ v[1]) > 0.0


def test_vectors_preserve_input_order() -> None:
    cv = ContentVectors(_books())
    assert cv.vectors([20, 10]).shape == (2, DIM)
    assert np.array_equal(cv.vectors([20, 10]), cv.vectors([10, 20])[::-1])


# ── 안전성 ──
def test_unknown_id_and_empty_tags_give_zero_rows() -> None:
    unknown = ContentVectors(_books()).vectors([99])
    assert unknown.shape == (1, DIM)
    assert not unknown.any()
    sparse_books = pd.DataFrame({COL_ITEM: [1, 2], "tags": ["a b", ""]})
    empty_row = ContentVectors(sparse_books).vectors([2])
    assert empty_row.shape == (1, 2)
    assert not empty_row.any()


# ── retrieve 계약 ──
def test_retrieve_returns_content_candidates_for_seed() -> None:
    """30(history war) 은 10 과 직교 → 점수 0 → 제외. 10 은 seen."""
    out = ContentVectors(_books()).retrieve(UserState(None, explicit_seeds=(10,)), k=2)
    assert [c.book_id for c in out] == [20]
    assert 0.0 < out[0].score <= 1.0 + 1e-9
    assert isinstance(out[0], Candidate)
    assert out[0].source == "content"
    assert ContentVectors.name == "content"


def test_fit_is_noop_returning_self() -> None:
    cv = ContentVectors(_books())
    assert cv.fit(pd.DataFrame()) is cv


# ── retrieve 정확성 ──
def test_retrieve_weights_zero_history_component() -> None:
    """β=0 이면 history(30) 벡터가 q 에 안 들어간다. 20 은 history/war 와 직교라 점수 동일."""
    user = UserState(None, explicit_seeds=(10,), history=(30,))
    zeroed = ContentVectors(
        _books(), weights=lambda u: {"alpha": 1.0, "beta": 0.0, "gamma": 0.0}
    ).retrieve(user, 2)
    assert [c.book_id for c in zeroed] == [20]
    default = ContentVectors(_books()).retrieve(user, 2)
    assert [c.book_id for c in default] == [20]
    assert default[0].score == pytest.approx(zeroed[0].score)


def test_vector_retriever_matches_content_retrieve() -> None:
    cv = ContentVectors(_books())
    vr = VectorRetriever(cv, ids=[10, 20, 30])
    user = UserState(None, explicit_seeds=(10,))
    a, b = cv.retrieve(user, 2), vr.retrieve(user, 2)
    assert [c.book_id for c in a] == [c.book_id for c in b]
    assert [c.score for c in a] == pytest.approx([c.score for c in b])
    assert VectorRetriever.name == "content"


# ── retrieve 안전성 ──
def test_retrieve_unknown_seed_or_empty_user_gives_empty() -> None:
    cv = ContentVectors(_books())
    assert cv.retrieve(UserState(None, explicit_seeds=(99,)), 2) == []
    assert cv.retrieve(UserState(None), 2) == []
    assert VectorRetriever(cv, ids=[]).retrieve(UserState(None, explicit_seeds=(10,)), 2) == []


def test_retrieve_never_returns_seen() -> None:
    cv = ContentVectors(_books())
    out = cv.retrieve(UserState(None, explicit_seeds=(10,), history=(20,)), 3)
    assert {c.book_id for c in out} & {10, 20} == set()
