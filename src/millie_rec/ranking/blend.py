"""★시간 가변 사용자 상태 가중치 α/β/γ.

main §5-2 감쇠(τ) + 아키텍처 01 §3-3 초기값·하한·재정규화 결합(D-02).
"""

import math

from millie_rec.contracts import UserState

ALPHA0, BETA0, GAMMA0 = 0.6, 0.3, 0.1  # 아키텍처 01 §3-3 초기값. freeze(D-14 ①)
TAU = 20  # main §5-2 α_n = α₀·e^{−n/τ}. n=20 → α≈0.22
ALPHA_FLOOR = 0.2  # 아키텍처 01 §3-3 하한 — explicit prior 는 0 이 되지 않는다
WEIGHT_KEYS = ("alpha", "beta", "gamma")  # 응답 user_state_weights 키 = compose.ZERO_WEIGHTS 키
RESET_BOOST, SESSION_BOOST = 0.15, 0.10  # D-02 인자 → Phase 5 cascade 가 실제로 적용(결정 D79)
ROUND = 3  # 응답 표시 소수 3자리(CONTEXT specifics)


def state_weights(
    user: UserState, *, reset_boost: bool = False, session_active: bool = False
) -> dict[str, float]:
    """α_n = max(0.2, 0.6·e^{−n/20}), 나머지를 β:γ = 3:1 → 비어 있는 성분 제거 → 합 1 재정규화.

    n = len(user.history) — Phase 4 는 이벤트가 없다.
    부스트 적용: kwargs ∨ user.context 플래그(Phase 5 cascade 가 기록, 결정 D79).
    """
    reset_boost = reset_boost or user.context.get("reset_boost") == "1"
    session_active = session_active or user.context.get("session_active") == "1"
    n = len(user.history)
    alpha = max(ALPHA_FLOOR, ALPHA0 * math.exp(-n / TAU))
    rest = 1.0 - alpha
    raw = {
        "alpha": alpha,
        "beta": rest * BETA0 / (BETA0 + GAMMA0),
        "gamma": rest * GAMMA0 / (BETA0 + GAMMA0),
    }
    if reset_boost:
        raw["alpha"] += RESET_BOOST  # 취향 재설정 24h 이내 — explicit prior 를 잠시 키운다
    if session_active:
        raw["gamma"] += SESSION_BOOST  # 최근 30분 세션 활동
    present = {
        "alpha": bool(user.explicit_seeds),
        "beta": bool(user.history),
        "gamma": bool(user.session),
    }
    kept = {k: v for k, v in raw.items() if present[k]}
    total = sum(kept.values())
    if total <= 0.0:
        return {k: 0.0 for k in WEIGHT_KEYS}  # 익명 — compose.ZERO_WEIGHTS 와 같은 값
    return {k: round(kept.get(k, 0.0) / total, ROUND) for k in WEIGHT_KEYS}
