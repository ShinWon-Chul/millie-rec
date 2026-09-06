"""/api/recommend level 0 — 계약(RecommendOut·pop_v1) · 정확성(seeds 제외·기본 variant) · 안전성.

Phase 2 'Track A 정량 평가 기반'(.planning/ROADMAP.md). 결정 D-11(기본 variant)·D-12(응답 형태)
·D-13(익명 level 3·예외 → level 3)(.planning/phases/02-track-a/02-CONTEXT.md).
가짜 Pipeline 주입 — retrieval·data 를 import 하지 않는다.
"""

from pathlib import Path

from fastapi.testclient import TestClient

from millie_rec.contracts import (
    DB_FILENAME,
    FALLBACK_GLOBAL_POP,
    FALLBACK_PERSONALIZED,
    MODEL_VERSION_FALLBACK,
    MODEL_VERSION_SUFFIX,
    ScoredItem,
    UserState,
)
from millie_rec.serving.api import create_app
from millie_rec.serving.db import Database
from millie_rec.serving.fallback import GlobalPopularFallback
from millie_rec.serving.schemas import RecommendOut

ZERO_WEIGHTS = {"alpha": 0.0, "beta": 0.0, "gamma": 0.0}


class _FakePop:
    """seen 을 뺀 1..39 상위 k — Plan 05 PopPipeline 의 형태 모사."""

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


class _FakeNamed(_FakePop):
    """name 만 다른 가짜 — 기본 variant(D-11) 검증용."""

    def __init__(self, name: str) -> None:
        self.name = name


class _Boom:
    """recommend 가 항상 예외 — '추천 API 장애 ≠ 메인 장애' 증거용 가짜 Pipeline."""

    name = "pop"

    def recommend(self, user: UserState, k: int) -> list[ScoredItem]:
        raise RuntimeError("boom")


def _app(tmp_path: Path, pipelines: dict | None = None):
    return create_app(
        pipelines=pipelines if pipelines is not None else {"pop": _FakePop()},
        fallback=GlobalPopularFallback(None),
        db=Database(tmp_path / DB_FILENAME),
    )


# ── 계약 ────────────────────────────────────────────────────────────────
def test_level0_with_pop_pipeline_returns_personalized_recommend_out(tmp_path: Path):
    with TestClient(_app(tmp_path)) as c:  # with 블록이어야 lifespan(스키마 적용)이 돈다
        r = c.get("/api/recommend", params={"seeds": "1,2,3", "k": 5})
    assert r.status_code == 200
    out = RecommendOut.model_validate(r.json())
    assert out.fallback_level == FALLBACK_PERSONALIZED
    assert out.model_version == "pop" + MODEL_VERSION_SUFFIX
    assert out.forced is False
    d = r.json()
    assert [i["book_id"] for i in d["items"]] == [4, 5, 6, 7, 8]
    assert len(d["rows"]) == 1
    row = d["rows"][0]
    assert row["row_id"] == "trending" and row["title"] == "지금 많이 읽는 책"
    assert row["purpose"] == "fallback"
    assert [i["book_id"] for i in row["items"]] == [4, 5, 6, 7, 8]
    assert row["channel_mix"] == {"popularity": 5}
    assert d["user_state_weights"] == ZERO_WEIGHTS
    assert d["recommendation_id"].startswith("rec_") and len(d["recommendation_id"]) == 10
    assert "total" in d["latency_breakdown"]


# ── 정확성 ──────────────────────────────────────────────────────────────
def test_level0_items_exclude_seeds_and_are_score_sorted(tmp_path: Path):
    with TestClient(_app(tmp_path)) as c:
        r = c.get("/api/recommend", params={"seeds": "4,5", "k": 3})
    assert r.status_code == 200
    d = r.json()
    ids = [i["book_id"] for i in d["items"]]
    assert ids == [1, 2, 3]
    assert not ({4, 5} & set(ids))
    scores = [i["score"] for i in d["items"]]
    assert scores == sorted(scores, reverse=True)
    assert [i["book_id"] for i in d["rows"][0]["items"]] == ids


def test_default_variant_is_last_registered_in_variants_order(tmp_path: Path):
    pipelines = {"pop": _FakePop(), "cf": _FakeNamed("cf")}
    with TestClient(_app(tmp_path, pipelines)) as c:
        r = c.get("/api/recommend", params={"seeds": "1"})
        forced = c.get("/api/recommend", params={"seeds": "1", "model": "pop"})
    assert r.status_code == 200
    assert r.json()["model_version"] == "cf" + MODEL_VERSION_SUFFIX
    assert r.json()["forced"] is False
    assert forced.status_code == 200
    assert forced.json()["model_version"] == "pop" + MODEL_VERSION_SUFFIX
    assert forced.json()["forced"] is True


def test_registered_only_pop_but_model_cf_uses_default_without_error(tmp_path: Path):
    with TestClient(_app(tmp_path)) as c:
        r = c.get("/api/recommend", params={"seeds": "1", "model": "cf"})
    assert r.status_code == 200
    d = r.json()
    assert d["model_version"] == "pop" + MODEL_VERSION_SUFFIX
    assert d["forced"] is True
    assert d["fallback_level"] == FALLBACK_PERSONALIZED


# ── 안전성 ──────────────────────────────────────────────────────────────
def test_anonymous_request_without_seeds_stays_level3(tmp_path: Path):
    with TestClient(_app(tmp_path)) as c:
        r = c.get("/api/recommend")
    assert r.status_code == 200
    d = r.json()
    assert d["fallback_level"] == FALLBACK_GLOBAL_POP
    assert d["model_version"] == MODEL_VERSION_FALLBACK
    assert d["items"] == []


def test_pipeline_exception_degrades_to_level3_200_without_leaking_error(tmp_path: Path):
    with TestClient(_app(tmp_path, {"pop": _Boom()})) as c:
        r = c.get("/api/recommend", params={"seeds": "1"})
    assert r.status_code == 200
    assert r.json()["fallback_level"] == FALLBACK_GLOBAL_POP
    assert r.json()["rows"][0]["items"] == []
    assert "boom" not in r.text and "Traceback" not in r.text


def test_empty_pipelines_regression_stays_level3(tmp_path: Path):
    with TestClient(_app(tmp_path, {})) as c:
        r = c.get("/api/recommend", params={"seeds": "1,2,3", "k": 5})
    assert r.status_code == 200
    assert r.json()["fallback_level"] == FALLBACK_GLOBAL_POP
    assert r.json()["model_version"] == MODEL_VERSION_FALLBACK
