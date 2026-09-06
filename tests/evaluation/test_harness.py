"""하네스 — 계약(EvalResult 필드) · 정확성(손계산 평균) · 안전성.

안전성: test 라벨을 UserState 에 넣지 않음, seen 반환 시 실패.
"""

import numpy as np
import pytest

from millie_rec.contracts import EvalResult, ScoredItem, UserState
from millie_rec.evaluation.harness import evaluate


class _FakePipeline:
    """user_id → 고정 추천 목록. 받은 user 를 기록해 정답이 넘어오지 않음을 단정한다."""

    name = "fake"

    def __init__(self, plan: dict[int, list[int]]) -> None:
        self.plan = plan
        self.seen_users: list[UserState] = []

    def recommend(self, user: UserState, k: int) -> list[ScoredItem]:
        self.seen_users.append(user)
        return [
            ScoredItem(book_id=b, score=float(k - i))
            for i, b in enumerate(self.plan.get(user.user_id, [])[:k])
        ]


class _OneHot:
    """id 별 직교 one-hot(dim 100) — 모든 쌍 거리 1 → ILD 1.0."""

    def vectors(self, book_ids):
        out = np.zeros((len(book_ids), 100))
        for i, b in enumerate(book_ids):
            out[i, int(b) % 100] = 1.0
        return out


def _users() -> list[tuple[UserState, frozenset[int]]]:
    return [
        (UserState(1, explicit_seeds=(7,)), frozenset({2, 9})),
        (UserState(2, explicit_seeds=(8,)), frozenset({5})),
    ]


# ── 계약 · 정확성 ──
def test_evaluate_returns_eval_result_with_hand_computed_means() -> None:
    pipe = _FakePipeline({1: [1, 2, 3], 2: [5, 6, 7]})
    res = evaluate(pipe, _users(), _OneHot(), k_recall=3, k_rank=3)
    assert isinstance(res, EvalResult)
    assert res.recall == pytest.approx(0.75)
    assert res.ndcg == pytest.approx(0.6934264, abs=1e-6)
    assert res.ild == pytest.approx(1.0)
    assert res.n_users == 2
    assert res.variant == "fake"
    assert res.model_version == "fake_v1"
    assert res.k_recall == 3
    assert res.k_rank == 3
    assert res.seed == 42
    assert res.created_at != ""
    assert res.p95_ms is None


# ── 안전성(누수) ──
def test_evaluate_passes_only_user_state_never_labels() -> None:
    pipe = _FakePipeline({1: [1, 2, 3], 2: [5, 6, 7]})
    users = _users()
    evaluate(pipe, users, _OneHot(), k_recall=3, k_rank=3)
    assert len(pipe.seen_users) == 2
    for got, (_, relevant) in zip(pipe.seen_users, users, strict=True):
        assert isinstance(got, UserState)
        assert got.seen & relevant == frozenset()
        assert got.history == ()
        assert got.session == ()


def test_evaluate_raises_when_seen_overlaps_relevant() -> None:
    pipe = _FakePipeline({1: [1, 2, 3]})
    users = [(UserState(1, explicit_seeds=(2,)), frozenset({2}))]
    with pytest.raises(ValueError):
        evaluate(pipe, users, _OneHot(), k_recall=3, k_rank=3)


def test_evaluate_raises_when_pipeline_returns_seen_item() -> None:
    pipe = _FakePipeline({1: [7, 1]})
    users = [(UserState(1, explicit_seeds=(7,)), frozenset({1}))]
    with pytest.raises(ValueError):
        evaluate(pipe, users, _OneHot(), k_recall=3, k_rank=3)


def test_evaluate_two_states_report_separate_n_users() -> None:
    pipe = _FakePipeline({1: [1, 2, 3], 2: [5, 6, 7]})
    users_nk = [
        (UserState(1, explicit_seeds=(7,), history=(20, 21)), frozenset({2, 9})),
        (UserState(2, explicit_seeds=(8,), history=(22, 23)), frozenset({5})),
    ]
    assert evaluate(pipe, _users(), _OneHot(), k_recall=3, k_rank=3).n_users == 2
    assert evaluate(pipe, users_nk[:1], _OneHot(), k_recall=3, k_rank=3).n_users == 1


def test_evaluate_handles_empty_users_and_empty_recommendations() -> None:
    empty = evaluate(_FakePipeline({}), [], _OneHot(), k_recall=3, k_rank=3)
    assert empty.n_users == 0
    assert (empty.recall, empty.ndcg, empty.ild) == (0.0, 0.0, 0.0)
    no_recs = evaluate(_FakePipeline({}), _users(), _OneHot(), k_recall=3, k_rank=3)
    assert no_recs.n_users == 2
    assert (no_recs.recall, no_recs.ndcg, no_recs.ild) == (0.0, 0.0, 0.0)
