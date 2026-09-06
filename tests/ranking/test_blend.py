"""ranking/blend.py state_weights — 계약(키) · 정확성(수식 대입 손계산) ·
안전성(익명·부스트 인자 무효).
"""

import pytest

from millie_rec.contracts import UserState
from millie_rec.ranking.blend import state_weights


def _u(n_hist: int, session: bool = False, seeds: bool = True) -> UserState:
    """seeds 5권 · history n권 · session 1권 조합. history id 는 후보와 겹치지 않는 100 대."""
    return UserState(
        None,
        explicit_seeds=(1, 2, 3, 4, 5) if seeds else (),
        history=tuple(range(100, 100 + n_hist)),
        session=(99,) if session else (),
    )


# ── 계약 ──
def test_keys_are_alpha_beta_gamma_in_order() -> None:
    w = state_weights(_u(0))
    assert list(w) == ["alpha", "beta", "gamma"]
    assert all(isinstance(v, float) for v in w.values())


# ── 정확성 ──
def test_new_user_seeds_only_gives_alpha_1_beta_0() -> None:
    """REC-03: history·session 이 없으면 재정규화로 α=1.0, 응답 β=0.0."""
    assert state_weights(_u(0)) == {"alpha": 1.0, "beta": 0.0, "gamma": 0.0}


def test_history_20_without_session_renormalizes_over_alpha_beta() -> None:
    """0.220728/(0.220728+0.584454) ≈ 0.274 — 빈 γ 를 뺀 뒤 합 1."""
    w = state_weights(_u(20))
    assert w["alpha"] == pytest.approx(0.274, abs=2e-3)
    assert w["beta"] == pytest.approx(0.726, abs=2e-3)
    assert w["gamma"] == 0.0
    assert sum(w.values()) == pytest.approx(1.0, abs=2e-3)


def test_history_20_with_session_matches_decay_formula() -> None:
    """α = 0.6·e^{−1} = 0.220728, 나머지 0.779272 를 β:γ = 3:1 로."""
    w = state_weights(_u(20, session=True))
    assert w["alpha"] == pytest.approx(0.221, abs=2e-3)
    assert w["beta"] == pytest.approx(0.584, abs=2e-3)
    assert w["gamma"] == pytest.approx(0.195, abs=2e-3)
    assert sum(w.values()) == pytest.approx(1.0, abs=2e-3)


def test_history_200_hits_alpha_floor_exactly() -> None:
    assert state_weights(_u(200, session=True)) == {"alpha": 0.2, "beta": 0.6, "gamma": 0.2}


def test_history_only_gives_beta_1() -> None:
    assert state_weights(_u(20, seeds=False)) == {"alpha": 0.0, "beta": 1.0, "gamma": 0.0}


# ── 안전성 ──
def test_anonymous_is_all_zero_and_seeds_user_is_not() -> None:
    """익명은 합 0 → 나눗셈 회피(serving/compose.py ZERO_WEIGHTS 와 같은 값)."""
    assert state_weights(UserState(None)) == {"alpha": 0.0, "beta": 0.0, "gamma": 0.0}
    assert state_weights(UserState(None, explicit_seeds=(1,)))["alpha"] == 1.0


def test_boost_flags_applied_phase5() -> None:
    """부스트 적용은 Phase 5 — 같은 사용자라도 플래그가 있으면 가중치가 달라진다(D79)."""
    base = state_weights(_u(20, session=True))
    boosted = state_weights(_u(20, session=True), reset_boost=True, session_active=True)
    assert boosted != base
    assert state_weights(_u(20, session=True)) == base  # 플래그 없는 호출은 Track A 그대로


# ── 부스트 적용(Phase 5, 결정 D79) ──
def test_session_boost_raises_gamma_and_keeps_sum_1() -> None:
    """γ 0.194818 + 0.10 → 합 1.1 재정규화: α 0.201 · β 0.531 · γ 0.268."""
    base = state_weights(_u(20, session=True))
    w = state_weights(_u(20, session=True), session_active=True)
    assert w["gamma"] > base["gamma"]
    assert w["alpha"] == pytest.approx(0.201, abs=2e-3)
    assert w["beta"] == pytest.approx(0.531, abs=2e-3)
    assert w["gamma"] == pytest.approx(0.268, abs=2e-3)
    assert sum(w.values()) == pytest.approx(1.0, abs=2e-3)


def test_reset_boost_raises_alpha_by_hand_computed_amount() -> None:
    """α 0.220728 + 0.15 → 합 1.15 재정규화: α 0.322 · β 0.508 · γ 0.169."""
    base = state_weights(_u(20, session=True))
    w = state_weights(_u(20, session=True), reset_boost=True)
    assert w["alpha"] > base["alpha"]
    assert w["alpha"] == pytest.approx(0.322, abs=2e-3)
    assert w["beta"] == pytest.approx(0.508, abs=2e-3)
    assert w["gamma"] == pytest.approx(0.169, abs=2e-3)
    assert sum(w.values()) == pytest.approx(1.0, abs=2e-3)


def test_context_flags_equal_kwargs_flags() -> None:
    """serving cascade 는 user.context 에 기록한다 — kwargs 와 같은 dict 여야 한다."""
    ctx = UserState(
        None,
        explicit_seeds=(1, 2, 3, 4, 5),
        history=tuple(range(100, 120)),
        session=(99,),
        context={"session_active": "1"},
    )
    assert state_weights(ctx) == state_weights(_u(20, session=True), session_active=True)
    both = UserState(
        None,
        explicit_seeds=(1, 2, 3, 4, 5),
        history=tuple(range(100, 120)),
        session=(99,),
        context={"session_active": "1", "reset_boost": "1"},
    )
    assert state_weights(both) == state_weights(
        _u(20, session=True), reset_boost=True, session_active=True
    )


def test_boost_cannot_revive_absent_component() -> None:
    """present 필터가 부스트보다 뒤 — seeds 없으면 α 는 0, 익명은 전부 0."""
    assert state_weights(_u(20, seeds=False), reset_boost=True) == {
        "alpha": 0.0,
        "beta": 1.0,
        "gamma": 0.0,
    }
    assert state_weights(UserState(None), reset_boost=True, session_active=True) == {
        "alpha": 0.0,
        "beta": 0.0,
        "gamma": 0.0,
    }
