"""create_app(weights=) — level 0 user_state_weights 채움(D-09·REC-03) · 익명 0 · 미주입 하위 호환
· weights 예외 → level 3 200.

Phase 4 '추천 파이프라인과 모델 freeze'(.planning/ROADMAP.md). 가짜 Pipeline 주입 —
retrieval·ranking·data 를 import 하지 않는다(테스트 간 import 금지 관례로 가짜는 복제).
"""

from collections.abc import Callable
from pathlib import Path

from fastapi.testclient import TestClient

from millie_rec.contracts import (
    DB_FILENAME,
    FALLBACK_GLOBAL_POP,
    FALLBACK_PERSONALIZED,
    MODEL_VERSION_FALLBACK,
    ScoredItem,
    UserState,
)
from millie_rec.serving.api import create_app
from millie_rec.serving.db import Database
from millie_rec.serving.fallback import GlobalPopularFallback

ZERO_WEIGHTS = {"alpha": 0.0, "beta": 0.0, "gamma": 0.0}
SEEDS_ONLY = {"alpha": 1.0, "beta": 0.0, "gamma": 0.0}


class _FakePop:
    """seen 을 뺀 1..39 상위 k — PopPipeline 의 형태 모사."""

    name = "pop"

    def recommend(self, user: UserState, k: int) -> list[ScoredItem]:
        ids = [b for b in range(1, 40) if b not in user.seen][:k]
        return [
            ScoredItem(
                book_id=b,
                score=float(40 - b),
                source="popularity",
                position=i,
                source_channels=("popularity",),
            )
            for i, b in enumerate(ids)
        ]


def _app(tmp_path: Path, *, weights: Callable | None = None, pipelines: dict | None = None):
    return create_app(
        pipelines=pipelines if pipelines is not None else {"pop": _FakePop()},
        fallback=GlobalPopularFallback(None),
        db=Database(tmp_path / DB_FILENAME),
        weights=weights,
    )


# ── 계약 ────────────────────────────────────────────────────────────────
def test_level0_user_state_weights_come_from_injected_callable(tmp_path: Path):
    with TestClient(_app(tmp_path, weights=lambda u: dict(SEEDS_ONLY))) as c:
        r = c.get("/api/recommend", params={"seeds": "1,2,3", "k": 5}).json()
    assert r["fallback_level"] == FALLBACK_PERSONALIZED
    assert r["user_state_weights"] == SEEDS_ONLY


# ── 정확성 ──────────────────────────────────────────────────────────────
def test_callable_receives_user_state_with_seeds(tmp_path: Path):
    seen: list[tuple[int, ...]] = []

    def weights(u: UserState) -> dict[str, float]:
        seen.append(u.explicit_seeds)
        return {"alpha": 0.5, "beta": 0.5, "gamma": 0.0}

    with TestClient(_app(tmp_path, weights=weights)) as c:
        r = c.get("/api/recommend", params={"seeds": "7,8", "k": 5}).json()
    assert seen == [(7, 8)]
    assert r["user_state_weights"]["beta"] == 0.5


# ── 안전성 ──────────────────────────────────────────────────────────────
def test_anonymous_and_uninjected_stay_zero(tmp_path: Path):
    with TestClient(_app(tmp_path, weights=lambda u: dict(SEEDS_ONLY))) as c:
        anon = c.get("/api/recommend").json()
    assert anon["fallback_level"] == FALLBACK_GLOBAL_POP
    assert anon["user_state_weights"] == ZERO_WEIGHTS  # 백엔드 서빙 01 §5 익명은 전부 0
    with TestClient(_app(tmp_path)) as c:  # weights 미주입 → 기존 동작(하위 호환)
        r = c.get("/api/recommend", params={"seeds": "1,2,3", "k": 5}).json()
    assert r["fallback_level"] == FALLBACK_PERSONALIZED
    assert r["user_state_weights"] == ZERO_WEIGHTS


def test_weights_exception_degrades_to_level3_200(tmp_path: Path):
    with TestClient(_app(tmp_path, weights=lambda u: 1 / 0)) as c:
        r = c.get("/api/recommend", params={"seeds": "1,2,3", "k": 5})
    assert r.status_code == 200
    d = r.json()
    assert d["fallback_level"] == FALLBACK_GLOBAL_POP
    assert d["model_version"] == MODEL_VERSION_FALLBACK
    assert d["user_state_weights"] == ZERO_WEIGHTS
