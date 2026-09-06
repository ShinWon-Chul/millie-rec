"""서빙 스켈레톤 스모크 — 계약(스키마 파싱) · 정확성(level 3·Must 4테이블) · 안전성(예외→200·422).

Phase 1 '로컬 서빙 스켈레톤'(.planning/ROADMAP.md). serving 레인 단독 조립(CONTEXT D-13).
app/ 은 마지막 1건(조립 테스트)에서만 import 한다.
"""

import importlib
import sys
from collections.abc import Sequence
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from millie_rec.contracts import (
    DB_FILENAME,
    DIR_DATA_LOCAL,
    ENV_DATA_DIR,
    FALLBACK_GLOBAL_POP,
    FALLBACK_PERSONALIZED,
    MODEL_VERSION_FALLBACK,
    MODEL_VERSION_SUFFIX,
    ScoredItem,
    UserState,
)
from millie_rec.serving.api import create_app
from millie_rec.serving.db import Database, resolve_db_path
from millie_rec.serving.fallback import GlobalPopularFallback
from millie_rec.serving.schemas import HealthOut, RecommendOut

MUST_TABLES = ("users", "preference_snapshots", "events", "recommendations")
ZERO_WEIGHTS = {"alpha": 0.0, "beta": 0.0, "gamma": 0.0}


class _Boom:
    """recommend 가 항상 예외 — '추천 API 장애 ≠ 메인 장애' 증거용 가짜 Pipeline."""

    name = "boom"

    def recommend(self, user: UserState, k: int) -> list[ScoredItem]:
        raise RuntimeError("boom")


class _FakePop:
    """seen 을 뺀 1..39 상위 k — build_pipelines 대체용(D-10 배선 검증)."""

    name = "pop"

    def recommend(self, user: UserState, k: int) -> list[ScoredItem]:
        ids = [b for b in range(1, 40) if b not in user.seen][:k]
        return [ScoredItem(book_id=b, score=float(40 - b), source="popularity") for b in ids]


class _FakeCatalog:
    """popular() 만 쓰는 가짜 Catalog. meta·eligible 은 Phase 1 fallback 이 호출하지 않는다."""

    def meta(self, book_ids: Sequence[int]) -> list[dict]:
        return []

    def popular(self, categories: Sequence[str] = (), n: int = 50) -> list[int]:
        return [1, 2, 3, 4, 5][:n]

    def eligible(self, book_ids: Sequence[int]) -> list[int]:
        return list(book_ids)


def _app(tmp_path: Path, fallback=None):
    return create_app(
        pipelines={},
        fallback=fallback or GlobalPopularFallback(None),
        db=Database(tmp_path / DB_FILENAME),
    )


@pytest.fixture
def client(tmp_path: Path):
    with TestClient(_app(tmp_path)) as c:  # with 블록이어야 lifespan(스키마 적용)이 돈다
        yield c


# ── 계약 ────────────────────────────────────────────────────────────────
def test_health_returns_200_and_parses_health_out(client):
    r = client.get("/health")
    assert r.status_code == 200
    out = HealthOut.model_validate(r.json())
    assert out.status == "ok" and out.db_ok is True
    assert out.model_version is None and out.artifacts_loaded_at is None


def test_recommend_without_pipeline_parses_recommend_out_level3(client):
    r = client.get("/api/recommend", params={"seeds": "1,2,3", "k": 5})
    assert r.status_code == 200
    out = RecommendOut.model_validate(r.json())
    assert out.fallback_level == FALLBACK_GLOBAL_POP
    assert out.model_version == MODEL_VERSION_FALLBACK
    assert out.forced is False and out.items == []


# ── 정확성 ──────────────────────────────────────────────────────────────
def test_recommend_level3_has_single_trending_row_and_rec_id(client):
    r = client.get("/api/recommend", params={"seeds": "1,2,3"})
    assert r.status_code == 200
    d = r.json()
    assert len(d["rows"]) == 1
    row = d["rows"][0]
    assert row["row_id"] == "trending" and row["title"] == "지금 많이 읽는 책"
    assert row["purpose"] == "fallback" and row["items"] == []
    assert d["recommendation_id"].startswith("rec_") and len(d["recommendation_id"]) == 10
    assert d["user_state_weights"] == ZERO_WEIGHTS and "total" in d["latency_breakdown"]


def test_recommend_with_model_query_sets_forced_true(client):
    r = client.get("/api/recommend", params={"model": "pop", "seeds": "1"})
    assert r.status_code == 200
    assert r.json()["forced"] is True and r.json()["fallback_level"] == FALLBACK_GLOBAL_POP


def test_health_db_row_count_has_must_tables_at_zero(client):
    r = client.get("/health")
    assert r.status_code == 200
    counts = r.json()["db_row_count"]
    assert all(counts.get(t) == 0 for t in MUST_TABLES), counts


def test_database_apply_schema_creates_must_tables(tmp_path: Path):
    db = Database(tmp_path / DB_FILENAME)
    db.apply_schema()
    assert set(MUST_TABLES) <= set(db.table_names())
    assert db.ok() is True


def test_resolve_db_path_prefers_env_then_local_default(tmp_path: Path, monkeypatch):
    monkeypatch.setenv(ENV_DATA_DIR, str(tmp_path))
    assert resolve_db_path() == tmp_path / DB_FILENAME
    monkeypatch.delenv(ENV_DATA_DIR)
    assert resolve_db_path() == DIR_DATA_LOCAL / DB_FILENAME


def test_fallback_with_catalog_excludes_seeds_and_marks_popularity():
    items = GlobalPopularFallback(_FakeCatalog()).recommend(
        UserState(user_id=None, explicit_seeds=(1,)), k=10
    )
    assert [i.book_id for i in items] == [2, 3, 4, 5]
    assert all(i.source == "popularity" and i.source_channels == ("popularity",) for i in items)
    assert [i.position for i in items] == [0, 1, 2, 3]


# ── 안전성 ──────────────────────────────────────────────────────────────
def test_recommend_invalid_query_returns_422(client):
    assert client.get("/api/recommend", params={"seeds": "1,x"}).status_code == 422
    assert client.get("/api/recommend", params={"model": "foo"}).status_code == 422
    assert client.get("/api/recommend", params={"k": 101}).status_code == 422
    assert client.get("/api/recommend", params={"k": 0}).status_code == 422


def test_recommend_when_fallback_raises_still_200_level3(tmp_path: Path):
    with TestClient(_app(tmp_path, fallback=_Boom())) as c:
        r = c.get("/api/recommend", params={"seeds": "1"})
    assert r.status_code == 200
    assert r.json()["fallback_level"] == FALLBACK_GLOBAL_POP and r.json()["rows"][0]["items"] == []


# ── 조립(app/server.py) ──────────────────────────────────────────────────
def test_server_module_serves_demo_index_and_keeps_api_routes(tmp_path: Path, monkeypatch):
    """app.server:app — StaticFiles 마운트가 마지막: / 는 demo, /health·/docs·/api 는 유지."""
    # 실제 data/local/millie.db 를 건드리지 않는다(D-13)
    monkeypatch.setenv(ENV_DATA_DIR, str(tmp_path))
    # Phase 2 D-10: 아티팩트 유무(머신 상태)에 의존하지 않도록
    # build_pipelines 를 대체 — level 3 경로
    monkeypatch.setattr(
        "millie_rec.app.pipeline.load_catalog", lambda: None
    )  # Phase 3: 실 artifacts 유무와 무관
    monkeypatch.setattr("millie_rec.app.pipeline.build_pipelines", lambda **_: {})
    # 모듈 캐시 — 이 테스트가 유일한 import 지점이지만 재실행에도 안전하게
    sys.modules.pop("millie_rec.app.server", None)
    server = importlib.import_module("millie_rec.app.server")
    with TestClient(server.app) as c:
        root = c.get("/")
        assert root.status_code == 200 and "<html" in root.text.lower()
        assert c.get("/health").status_code == 200
        assert c.get("/docs").status_code == 200  # PDF P2 캡처 대상 — 마운트 순서로 보장
        rec = c.get("/api/recommend", params={"seeds": "1,2,3", "k": 5})
    assert rec.status_code == 200 and rec.json()["fallback_level"] == FALLBACK_GLOBAL_POP
    assert (tmp_path / DB_FILENAME).exists()


def test_server_module_injects_pop_pipeline_when_build_pipelines_returns_pop(
    tmp_path: Path, monkeypatch
):
    """app.server:app — build_pipelines() 가 pop 을 주면 /api/recommend 는 level 0(D-10 배선)."""
    monkeypatch.setenv(ENV_DATA_DIR, str(tmp_path))
    monkeypatch.setattr(
        "millie_rec.app.pipeline.load_catalog", lambda: None
    )  # Phase 3: 실 artifacts 유무와 무관
    monkeypatch.setattr("millie_rec.app.pipeline.build_pipelines", lambda **_: {"pop": _FakePop()})
    sys.modules.pop("millie_rec.app.server", None)
    server = importlib.import_module("millie_rec.app.server")
    with TestClient(server.app) as c:
        rec = c.get("/api/recommend", params={"seeds": "1,2,3", "k": 5})
        anon = c.get("/api/recommend")
    assert rec.status_code == 200 and rec.json()["fallback_level"] == FALLBACK_PERSONALIZED
    assert rec.json()["model_version"] == "pop" + MODEL_VERSION_SUFFIX
    assert [i["book_id"] for i in rec.json()["items"]] == [4, 5, 6, 7, 8]
    assert anon.status_code == 200 and anon.json()["fallback_level"] == FALLBACK_GLOBAL_POP  # D-13
