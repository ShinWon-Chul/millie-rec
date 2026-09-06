"""pop 후보 생성기 — 계약(Candidate·정렬) · 정확성(손계산 카운트·seen 제외)
· 안전성(train 만 fit·save/load).
"""

import inspect
import json

import pandas as pd

from millie_rec.contracts import COL_ITEM, COL_RATING, COL_USER, Candidate, UserState
from millie_rec.retrieval.popularity import PopularityRetriever


def _train() -> pd.DataFrame:
    """아이템 1 이 3행, 2 가 2행, 3 이 1행. 평점은 1~5 로 섞어 '평점 무관' 을 함께 증명."""
    return pd.DataFrame(
        {
            COL_USER: [1, 2, 3, 1, 2, 1],
            COL_ITEM: [1, 1, 1, 2, 2, 3],
            COL_RATING: [1.0, 2.0, 3.0, 4.0, 5.0, 1.0],
        }
    )


# ── 계약 ──
def test_retrieve_returns_candidates_sorted_by_count_desc() -> None:
    out = PopularityRetriever().fit(_train()).retrieve(UserState(None), k=2)
    assert [c.book_id for c in out] == [1, 2]
    assert [c.score for c in out] == [3.0, 2.0]
    assert all(isinstance(c, Candidate) and c.source == "popularity" for c in out)
    assert PopularityRetriever.name == "pop"


def test_retrieve_on_fixture_returns_k_sorted_popularity_candidates(interactions) -> None:
    out = PopularityRetriever().fit(interactions).retrieve(UserState(None), k=20)
    assert len(out) == 20
    assert all(a.score >= b.score for a, b in zip(out, out[1:], strict=False))
    assert all(c.source == "popularity" for c in out)


# ── 정확성 ──
def test_retrieve_excludes_user_seen() -> None:
    r = PopularityRetriever().fit(_train())
    assert [c.book_id for c in r.retrieve(UserState(None, explicit_seeds=(1,)), k=2)] == [2, 3]
    assert r.retrieve(UserState(None, history=(1, 2, 3)), k=2) == []


def test_retrieve_k_larger_than_catalog_returns_all_remaining() -> None:
    assert len(PopularityRetriever().fit(_train()).retrieve(UserState(None), k=10)) == 3


def test_fit_counts_all_train_rows_regardless_of_rating() -> None:
    """D-05 '평점이 있다 = 읽었다' — 평점 1~5 가 섞여도 카운트는 3/2/1."""
    out = PopularityRetriever().fit(_train()).retrieve(UserState(None), k=3)
    assert [(c.book_id, c.score) for c in out] == [(1, 3.0), (2, 2.0), (3, 1.0)]


# ── 안전성 ──
def test_fit_takes_only_train_and_ignores_unseen_test_frame() -> None:
    """fit 인자는 1개 — retriever 가 test 프레임을 알 방법이 없다."""
    assert list(inspect.signature(PopularityRetriever.fit).parameters) == ["self", "train"]
    unseen_test = pd.DataFrame({COL_USER: [9] * 10, COL_ITEM: [3] * 10, COL_RATING: [5.0] * 10})
    r = PopularityRetriever().fit(_train())
    assert len(unseen_test) == 10
    assert [c.book_id for c in r.retrieve(UserState(None), k=10)] == [1, 2, 3]


def test_save_load_roundtrip_and_top_n(tmp_path) -> None:
    r = PopularityRetriever().fit(_train())
    p = r.save(tmp_path / "pop.json")
    assert p.exists()
    payload = json.loads(p.read_text(encoding="utf-8"))
    assert payload["name"] == "pop"
    assert len(payload["items"]) == 3
    assert PopularityRetriever.load(p).retrieve(UserState(None), k=3) == r.retrieve(
        UserState(None), k=3
    )
    small = json.loads(r.save(tmp_path / "p2.json", top_n=2).read_text(encoding="utf-8"))
    assert len(small["items"]) == 2
