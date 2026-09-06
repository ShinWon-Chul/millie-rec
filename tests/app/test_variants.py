"""app/server.py 4 variant 배선(D-10·D-11) — 계약(model_version 4종·기본 hybrid_div) ·
정확성(fixture 손계산 pop/cf·가드 7) · 안전성(eligible·β=0). 실 artifacts/serving 은 읽지 않는다.
"""

import importlib
import sys
from pathlib import Path

from fastapi.testclient import TestClient

from millie_rec.contracts import ENV_DATA_DIR, VARIANTS
from millie_rec.data import VECTORS_KR_NPZ, CatalogKR, VectorsKR

SEEDS_ONLY = {"alpha": 1.0, "beta": 0.0, "gamma": 0.0}
ZERO_WEIGHTS = {"alpha": 0.0, "beta": 0.0, "gamma": 0.0}


def _server(tmp_path: Path, monkeypatch, serving_dir: Path):
    monkeypatch.setenv(ENV_DATA_DIR, str(tmp_path))
    monkeypatch.setattr("millie_rec.app.pipeline.load_catalog", lambda: CatalogKR.load(serving_dir))
    monkeypatch.setattr(
        "millie_rec.app.pipeline_kr.load_vectors_kr",
        lambda *a, **k: VectorsKR.load(serving_dir / VECTORS_KR_NPZ),
    )
    sys.modules.pop("millie_rec.app.server", None)
    return importlib.import_module("millie_rec.app.server")


def _rec(c: TestClient, model: str | None, k: int = 10) -> dict:
    params = {"seeds": "1,2,3", "k": k, **({"model": model} if model else {})}
    return c.get("/api/recommend", params=params).json()


# ── 계약 ────────────────────────────────────────────────────────────────
def test_four_variants_return_their_model_version_level0(
    tmp_path, monkeypatch, millie_serving_sample
):
    server = _server(tmp_path, monkeypatch, millie_serving_sample)
    with TestClient(server.app) as c:
        for v in VARIANTS:
            r = _rec(c, v)
            assert r["model_version"] == f"{v}_v1"
            assert r["fallback_level"] == 0
            assert r["forced"] is True


def test_default_variant_is_hybrid_div_when_four_registered(
    tmp_path, monkeypatch, millie_serving_sample
):
    server = _server(tmp_path, monkeypatch, millie_serving_sample)
    with TestClient(server.app) as c:
        r = _rec(c, None)
    assert r["model_version"] == "hybrid_div_v1" and r["forced"] is False  # D-11 자동 이동


# ── 정확성 ──────────────────────────────────────────────────────────────
def test_variants_return_different_books_on_fixture(tmp_path, monkeypatch, millie_serving_sample):
    server = _server(tmp_path, monkeypatch, millie_serving_sample)
    with TestClient(server.app) as c:
        ids = {v: [i["book_id"] for i in _rec(c, v)["items"]] for v in VARIANTS}
    assert ids["pop"] == list(range(4, 14))  # pop_rank 순, seen 1·2·3 제외
    assert ids["cf"] == [4, 5, 6, 7, 8]  # 엣지 손계산 — 이웃이 8 까지만 닿는다
    assert 7 in ids["hybrid"]
    assert 7 not in ids["hybrid_div"]  # 가드: 7 은 resid_z −1.5 millie_index, n_completed=0
    assert ids["hybrid"] != ids["hybrid_div"] and ids["pop"] != ids["hybrid"]
    assert len({tuple(v) for v in ids.values()}) == 4


# ── 안전성 ──────────────────────────────────────────────────────────────
def test_all_variants_only_eligible_books_with_korean_meta(
    tmp_path, monkeypatch, millie_serving_sample
):
    server = _server(tmp_path, monkeypatch, millie_serving_sample)
    with TestClient(server.app) as c:
        for v in VARIANTS:
            r = _rec(c, v)
            assert not {18, 19, 20} & {i["book_id"] for i in r["items"]}
            if v == "hybrid_div":
                assert r["rows"][0]["items"][0]["title"].startswith("밀리 표본 도서")  # WithMeta


def test_user_state_weights_beta_zero_for_seeds_only_user(
    tmp_path, monkeypatch, millie_serving_sample
):
    server = _server(tmp_path, monkeypatch, millie_serving_sample)
    with TestClient(server.app) as c:
        assert _rec(c, "hybrid_div")["user_state_weights"] == SEEDS_ONLY  # D-09·REC-03
        assert c.get("/api/recommend").json()["user_state_weights"] == ZERO_WEIGHTS
