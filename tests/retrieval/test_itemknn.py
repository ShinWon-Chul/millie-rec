"""cf 후보 생성기 — 계약(Candidate·source·정렬·Neighbors) · 정확성(손계산 cosine·성분 가중)
· 안전성(fit 1인자·seen 제외·npz 라운드트립·캐시 무효화).
"""

import inspect

import numpy as np
import pandas as pd
import pytest

from millie_rec.contracts import COL_ITEM, COL_RATING, COL_USER, Candidate, UserState
from millie_rec.retrieval.itemknn import ItemKNNRetriever, load_or_fit_itemknn

ROOT2 = 0.70710678  # 1/√2 — cos(1,3) = cos(2,3)


def _train() -> pd.DataFrame:
    """u1={1,2,3} u2={1,2} u3={4}. cos(1,2)=1, cos(1,3)=cos(2,3)=1/√2, 4 는 이웃 없음.

    평점 1~5 를 섞어 '평점 무관'(CONTEXT D-05) 을 함께 증명한다.
    """
    return pd.DataFrame(
        {
            COL_USER: [1, 1, 1, 2, 2, 3],
            COL_ITEM: [1, 2, 3, 1, 2, 4],
            COL_RATING: [5.0, 1.0, 3.0, 2.0, 4.0, 5.0],
        }
    )


# ── 계약 ──
def test_retrieve_returns_itemknn_candidates_sorted_desc() -> None:
    r = ItemKNNRetriever().fit(_train())
    out = r.retrieve(UserState(None, explicit_seeds=(1,)), k=5)
    assert [c.book_id for c in out] == [2, 3]
    assert [c.score for c in out] == pytest.approx([1.0, ROOT2], abs=1e-3)
    assert all(isinstance(c, Candidate) and c.source == "itemknn" for c in out)
    assert ItemKNNRetriever.name == "cf"


def test_neighbors_protocol_sorted_and_self_excluded() -> None:
    r = ItemKNNRetriever().fit(_train())
    nbrs = r.neighbors(1, n=5)
    assert [b for b, _s in nbrs] == [2, 3]
    assert [s for _b, s in nbrs] == pytest.approx([1.0, ROOT2], abs=1e-3)
    assert r.neighbors(4) == []
    assert r.neighbors(99) == []
    assert len(r.neighbors(1, n=1)) == 1


# ── 정확성 ──
def test_history_component_sums_neighbor_similarity() -> None:
    r = ItemKNNRetriever().fit(_train())
    out = r.retrieve(UserState(None, explicit_seeds=(1,), history=(2,)), k=5)
    assert [c.book_id for c in out] == [3]
    assert out[0].score == pytest.approx(2 * ROOT2, abs=1e-3)


def test_weights_callable_zeroes_history_component() -> None:
    r = ItemKNNRetriever(weights=lambda u: {"alpha": 1.0, "beta": 0.0, "gamma": 0.0}).fit(_train())
    out = r.retrieve(UserState(None, explicit_seeds=(1,), history=(2,)), k=5)
    assert [c.book_id for c in out] == [3]
    assert out[0].score == pytest.approx(ROOT2, abs=1e-3)


def test_retrieve_on_fixture_is_sorted_and_excludes_seen(interactions) -> None:
    out = ItemKNNRetriever().fit(interactions).retrieve(UserState(None, explicit_seeds=(0,)), k=20)
    assert 0 < len(out) <= 20
    assert all(a.score >= b.score for a, b in zip(out, out[1:], strict=False))
    assert 0 not in [c.book_id for c in out]


# ── 안전성 ──
def test_fit_takes_only_train_and_seen_items_never_returned() -> None:
    assert list(inspect.signature(ItemKNNRetriever.fit).parameters) == ["self", "train"]
    r = ItemKNNRetriever().fit(_train())
    assert r.retrieve(UserState(None, history=(1, 2, 3, 4)), k=5) == []


def test_save_load_roundtrip_keys_and_meta(tmp_path) -> None:
    r = ItemKNNRetriever().fit(_train())
    p = r.save(tmp_path / "knn.npz")
    with np.load(p) as z:
        assert set(z.files) == {"book_ids", "nbr_ids", "nbr_sims", "meta"}
        assert z["meta"].tolist() == [6, 3, 4]
        assert z["nbr_ids"].shape == (4, 50)
    user = UserState(None, explicit_seeds=(1,))
    assert ItemKNNRetriever.load(p).retrieve(user, 5) == r.retrieve(user, 5)


def test_load_or_fit_uses_cache_only_when_meta_matches(tmp_path, monkeypatch) -> None:
    p = tmp_path / "knn.npz"
    load_or_fit_itemknn(_train(), p)
    assert p.exists()

    def _boom(self, train):
        raise AssertionError("fit must not run")

    monkeypatch.setattr(ItemKNNRetriever, "fit", _boom)
    cached = load_or_fit_itemknn(_train(), p)
    assert [c.book_id for c in cached.retrieve(UserState(None, explicit_seeds=(1,)), 5)] == [2, 3]
    monkeypatch.undo()
    assert load_or_fit_itemknn(_train().iloc[:-1], p).meta == (5, 2, 3)
    before = set(tmp_path.iterdir())
    load_or_fit_itemknn(_train(), None)
    assert set(tmp_path.iterdir()) == before
