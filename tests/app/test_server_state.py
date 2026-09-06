"""app/server.py 상태 주입(D-07·Advisor 확정 5) — 계약(create_app 인자 state·book_stats) ·
정확성(last_breakdown 3키·book_stats 패스스루) · 안전성(catalog None 기동).

실 artifacts/serving 은 읽지 않는다(20권 fixture). /api/recommend 5행 단정은 05-06 몫.
"""

import importlib
import sys
from pathlib import Path

from fastapi.testclient import TestClient

from millie_rec.app.pipeline import build_pipelines
from millie_rec.app.pipeline_kr import build_pipelines_kr
from millie_rec.contracts import ENV_DATA_DIR, UserState
from millie_rec.data import VECTORS_KR_NPZ, CatalogKR, VectorsKR
from millie_rec.serving import ServingBookStats, StateStore

BREAKDOWN_KEYS = {"retrieval", "ranking", "rerank"}


def _server(tmp_path: Path, monkeypatch, serving_dir: Path):
    """test_server_catalog.py L20-28 복제 — fixture 카탈로그·npz 로 server 모듈 재import."""
    monkeypatch.setenv(ENV_DATA_DIR, str(tmp_path))
    monkeypatch.setattr("millie_rec.app.pipeline.load_catalog", lambda: CatalogKR.load(serving_dir))
    monkeypatch.setattr(
        "millie_rec.app.pipeline_kr.load_vectors_kr",
        lambda *a, **k: VectorsKR.load(serving_dir / VECTORS_KR_NPZ),
    )
    sys.modules.pop("millie_rec.app.server", None)
    return importlib.import_module("millie_rec.app.server")


def _pipes(serving_dir: Path, **kw):
    cat = CatalogKR.load(serving_dir)
    vec = VectorsKR.load(serving_dir / VECTORS_KR_NPZ)
    return cat, build_pipelines_kr(cat, vectors=vec, **kw)


class _Spy:
    """CatalogKR 을 감싼 BookStatsSource — stats 호출 수만 세고 user_level 은 고정."""

    def __init__(self, catalog: CatalogKR) -> None:
        self.catalog, self.calls = catalog, 0

    def stats(self, book_ids):
        self.calls += 1
        return self.catalog.stats(book_ids)

    def user_level(self, user):
        return 0.9


# ── 계약 ────────────────────────────────────────────────────────────────
def test_server_injects_state_store_and_serving_book_stats(
    tmp_path: Path, monkeypatch, millie_serving_sample
):
    """StateStore 1개가 create_app(state=) 와 ServingBookStats 양쪽에 같은 객체로 들어간다."""
    import millie_rec.serving as sv

    real = sv.create_app
    captured: dict = {}
    monkeypatch.setattr(
        "millie_rec.serving.create_app",
        lambda *a, **kw: (captured.update(kw), real(*a, **kw))[1],
    )
    server = _server(tmp_path, monkeypatch, millie_serving_sample)
    store = getattr(server, "store", None)
    assert isinstance(store, StateStore)
    assert captured.get("state") is store
    assert isinstance(captured.get("book_stats"), ServingBookStats)
    assert captured["book_stats"].store is store


def test_build_pipelines_passthrough_book_stats_keyword(tmp_path: Path):
    """build_pipelines 가 book_stats keyword 를 받는다(아티팩트 없음 → {})."""
    assert build_pipelines(tmp_path / "none.json", catalog=None, book_stats=object()) == {}


# ── 정확성 ──────────────────────────────────────────────────────────────
def test_staged_pipeline_records_last_breakdown_three_keys(millie_serving_sample):
    """D-09: retrieval·ranking·rerank 밀리초 3키. 로직 무변경(가드 7 은 그대로 밖)."""
    _, pipes = _pipes(millie_serving_sample)
    outer = pipes["hybrid_div"]
    inner = outer.inner  # WithMeta 안쪽 StagedPipeline
    user = UserState(None, explicit_seeds=(1, 2, 3))
    inner.recommend(user, 10)
    bd = getattr(inner, "last_breakdown", None)
    assert isinstance(bd, dict)
    assert set(bd) == BREAKDOWN_KEYS
    assert all(isinstance(v, float) and v >= 0.0 for v in bd.values())
    ids = [i.book_id for i in outer.recommend(user, 10)]
    assert 7 not in ids[:10]  # test_variants.py:64 와 같은 단정 — 로직 무변경 증거
    assert set(getattr(outer, "last_breakdown", None) or {}) == BREAKDOWN_KEYS  # WithMeta 프록시


def test_build_pipelines_kr_passes_book_stats_to_guard_and_blend(millie_serving_sample):
    """주입된 book_stats 를 blend(_gap_bonus) 와 DifficultyGuard 가 함께 쓴다."""
    cat = CatalogKR.load(millie_serving_sample)
    spy = _Spy(cat)
    _, pipes = _pipes(millie_serving_sample, book_stats=spy)
    user = UserState(None, explicit_seeds=(1,), context={"n_completed": "0"})
    pipes["hybrid_div"].recommend(user, 10)
    assert spy.calls >= 2  # blend 1 + guard 1
    _, plain = _pipes(millie_serving_sample)
    assert plain["hybrid_div"].inner.book_stats is not None  # book_stats 없으면 카탈로그 자신


# ── 안전성 ──────────────────────────────────────────────────────────────
def test_server_starts_without_catalog_and_stats_is_none(tmp_path: Path, monkeypatch):
    """local-run.md: 아티팩트 없이 기동 — stats 는 None, store 는 있고 /health 200."""
    monkeypatch.setenv(ENV_DATA_DIR, str(tmp_path))
    monkeypatch.setattr("millie_rec.app.pipeline.load_catalog", lambda: None)
    monkeypatch.setattr("millie_rec.app.pipeline.build_pipelines", lambda **_: {})
    sys.modules.pop("millie_rec.app.server", None)
    server = importlib.import_module("millie_rec.app.server")
    assert getattr(server, "stats", "missing") is None
    assert isinstance(getattr(server, "store", None), StateStore)
    with TestClient(server.app) as c:
        assert c.get("/health").status_code == 200
