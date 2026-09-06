"""app/server.py 카탈로그 주입(D-13) — 계약(level 0 pop_v1) · 정확성(seen 제외·pop_rank·meta 조인) ·
안전성(익명 level 3 인기 채움). 실 artifacts/serving 은 읽지 않는다(fixture 20권).
"""

import importlib
import sys
from pathlib import Path

from fastapi.testclient import TestClient

from millie_rec.contracts import (
    ENV_DATA_DIR,
    FALLBACK_GLOBAL_POP,
    FALLBACK_PERSONALIZED,
    MODEL_VERSION_FALLBACK,
)
from millie_rec.data import VECTORS_KR_NPZ, CatalogKR, VectorsKR


def _server(tmp_path: Path, monkeypatch, serving_dir: Path):
    monkeypatch.setenv(ENV_DATA_DIR, str(tmp_path))
    monkeypatch.setattr("millie_rec.app.pipeline.load_catalog", lambda: CatalogKR.load(serving_dir))
    monkeypatch.setattr(  # 실 npz 를 읽지 않게 — fixture npz 로
        "millie_rec.app.pipeline_kr.load_vectors_kr",
        lambda *a, **k: VectorsKR.load(serving_dir / VECTORS_KR_NPZ),
    )
    sys.modules.pop("millie_rec.app.server", None)
    return importlib.import_module("millie_rec.app.server")


def test_server_injects_catalog_pop_level0_with_korean_titles(
    tmp_path: Path, monkeypatch, millie_serving_sample
):
    server = _server(tmp_path, monkeypatch, millie_serving_sample)
    with TestClient(server.app) as c:
        rec = c.get("/api/recommend", params={"seeds": "1,2,3", "k": 5, "model": "pop"}).json()
    assert rec["fallback_level"] == FALLBACK_PERSONALIZED
    assert rec["model_version"] == "pop_v1"
    assert rec["rows"][0]["row_id"] == "trending"
    assert [i["book_id"] for i in rec["items"]] == [4, 5, 6, 7, 8]
    assert rec["rows"][0]["items"][0]["title"] == "밀리 표본 도서 4"


def test_server_anonymous_is_level3_but_trending_filled_from_catalog(
    tmp_path: Path, monkeypatch, millie_serving_sample
):
    server = _server(tmp_path, monkeypatch, millie_serving_sample)
    with TestClient(server.app) as c:
        anon = c.get("/api/recommend").json()
    assert anon["fallback_level"] == FALLBACK_GLOBAL_POP
    assert anon["model_version"] == MODEL_VERSION_FALLBACK
    assert anon["items"] == []
    ids = [i["book_id"] for i in anon["rows"][0]["items"]]
    assert ids[:5] == [1, 2, 3, 4, 5]
    assert not {18, 19, 20} & set(ids)
