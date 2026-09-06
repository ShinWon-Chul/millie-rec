"""온보딩 마스킹 — seeds 5권은 train 긍정 부분집합, 미선택 책은 negative 가 아니다.

CONTEXT D-01·D-03·D-04 · 수용 기준 '미선택 책 != 부정 신호'(PRD §9 수용 기준 표).
"""

import pandas as pd

from millie_rec.contracts import COL_ITEM, COL_RATING, COL_USER, UserState
from millie_rec.data.onboarding import mask_onboarding, select_test_users

K_HISTORY_SMALL = 3  # 손계산용. 구현 기본값(20)을 import 하지 않는다
U1_POSITIVES = {1, 2, 3, 4, 5, 6, 10, 11, 12}
U2_POSITIVES = set(range(21, 27))


def _train() -> pd.DataFrame:
    ratings = [5, 5, 5, 4, 4, 4, 3, 2, 1, 5, 5, 5]
    u1 = pd.DataFrame({COL_USER: 1, COL_ITEM: range(1, 13), COL_RATING: ratings})
    u2 = pd.DataFrame({COL_USER: 2, COL_ITEM: range(21, 27), COL_RATING: 5.0})
    u3 = pd.DataFrame({COL_USER: 3, COL_ITEM: range(31, 35), COL_RATING: [5, 5, 5, 1]})
    return pd.concat([u1, u2, u3], ignore_index=True).astype({COL_RATING: float})


def _test() -> pd.DataFrame:
    return pd.DataFrame(
        {COL_USER: [1, 2, 3], COL_ITEM: [101, 102, 103], COL_RATING: [5.0, 2.0, 5.0]}
    )


# ── 정확성 ──────────────────────────────────────────────────────────────────
def test_mask_onboarding_exposes_exactly_5_seeds_from_train_positives():
    st = mask_onboarding(_train(), (1, 2), k_history=K_HISTORY_SMALL)
    assert len(st.n0) == 2
    positives = {1: U1_POSITIVES, 2: U2_POSITIVES}
    for state in st.n0:
        assert len(state.explicit_seeds) == 5
        assert state.history == () and state.session == ()
        assert set(state.explicit_seeds) <= positives[state.user_id]


def test_mask_onboarding_nk_state_requires_k_history_and_excludes_seeds():
    st = mask_onboarding(_train(), (1, 2), k_history=K_HISTORY_SMALL)
    assert len(st.n_k) == 1
    nk = st.n_k[0]
    assert nk.user_id == 1
    assert set(nk.history) == set(range(1, 13)) - set(nk.explicit_seeds)
    assert set(nk.history) & set(nk.explicit_seeds) == set()
    assert nk.explicit_seeds == st.n0[0].explicit_seeds


def test_select_test_users_requires_5_train_positives_and_1_test_positive():
    assert select_test_users(_train(), _test()) == ((1,), 2)
    assert select_test_users(_train(), _test(), n=1) == ((1,), 2)


# ── 계약 ────────────────────────────────────────────────────────────────────
def test_user_state_has_no_negative_structure():
    st = mask_onboarding(_train(), (1,), k_history=K_HISTORY_SMALL)
    assert len(st.n0) == 1
    fields = set(UserState.__dataclass_fields__)
    assert fields == {"user_id", "explicit_seeds", "history", "session", "context"}
    assert st.n0[0].context == {}
    assert 101 not in st.n0[0].seen


# ── 안전성 ──────────────────────────────────────────────────────────────────
def test_mask_onboarding_is_deterministic():
    a = mask_onboarding(_train(), (1, 2), k_history=K_HISTORY_SMALL)
    b = mask_onboarding(_train(), (1, 2), k_history=K_HISTORY_SMALL)
    assert len(a.n0) == 2
    assert [s.explicit_seeds for s in a.n0] == [s.explicit_seeds for s in b.n0]


def test_select_test_users_samples_n_deterministically():
    extra_train = pd.DataFrame({COL_USER: 4, COL_ITEM: range(41, 47), COL_RATING: 5.0})
    extra_test = pd.DataFrame({COL_USER: [4], COL_ITEM: [104], COL_RATING: [5.0]})
    train = pd.concat([_train(), extra_train], ignore_index=True)
    test = pd.concat([_test(), extra_test], ignore_index=True)
    first, n_excluded = select_test_users(train, test, n=1)
    again, _ = select_test_users(train, test, n=1)
    assert len(first) == 1
    assert first == again
    assert n_excluded == 2
