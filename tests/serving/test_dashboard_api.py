"""GET /api/showcase — eval_table.json → ShowcaseOut 변환·고정 문장·안전성 (백엔드 서빙 01 §13)."""

import json
import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from millie_rec.serving import dashboard_api
from millie_rec.serving.dashboard_api import (
    DATA_NOTICE,
    PHILOSOPHY,
    ROADMAP,
    build_router,
    load_eval_table,
)
from millie_rec.serving.db import Database
from millie_rec.serving.schemas_should import ShowcaseOut

# artifacts/serving/eval_table.json 실형태(2026-09-06 실측) — 지표 값이 문자열, 키가 recall@20
EVAL_JSON = """{
  "rows": [
    {"variant": "pop", "recall@20": "0.063", "ndcg@10": "0.054", "ild@10": "0.764",
     "n_users": "2000", "split_mode": "holdout", "model_version": "pop_v1"},
    {"variant": "cf", "recall@20": "0.117", "ndcg@10": "0.107", "ild@10": "0.643",
     "n_users": "2000", "split_mode": "holdout", "model_version": "cf_v1"},
    {"variant": "hybrid", "recall@20": "0.118", "ndcg@10": "0.110", "ild@10": "0.606",
     "n_users": "2000", "split_mode": "holdout", "model_version": "hybrid_v1"},
    {"variant": "hybrid_div", "recall@20": "0.116", "ndcg@10": "0.107", "ild@10": "0.684",
     "n_users": "2000", "split_mode": "holdout", "model_version": "hybrid_div_v1"}
  ],
  "meta": {"dataset": "goodbooks-10k", "split_mode": "holdout", "n_users": 2000,
           "k_recall": 20, "k_rank": 10, "seed": 42, "git_sha": "8e5172b",
           "created_at": "2026-09-05T15:14:05+00:00"}
}"""

NOTICE_VERBATIM = "평가 = Goodbooks-10k(CC BY-SA 4.0) · 데모 카탈로그 = 밀리 공개 도서 페이지(수치·메타·표지 URL만, 텍스트 미노출, 요청 시 삭제) · 데모 이웃 = 콘텐츠 유사도 · 개인정보 무수집 · 서버 latency는 참고값"  # noqa: E501


def _paths(root: Path, *, eval_json: str | None = EVAL_JSON, latency: dict | None = None):
    root.mkdir(parents=True, exist_ok=True)
    eval_path = root / "eval_table.json"
    if eval_json is not None:
        eval_path.write_text(eval_json, encoding="utf-8")
    latency_path = root / "latency.json"
    if latency is not None:
        latency_path.write_text(json.dumps(latency), encoding="utf-8")
    return eval_path, latency_path


def _client(root: Path, *, eval_json: str | None = EVAL_JSON, latency: dict | None = None):
    eval_path, latency_path = _paths(root, eval_json=eval_json, latency=latency)
    app = FastAPI()
    app.include_router(
        build_router(
            db=Database(root / "t.db"), eval_table_path=eval_path, latency_path=latency_path
        )
    )
    return TestClient(app)


def _showcase(root: Path, **kw) -> ShowcaseOut:
    r = _client(root, **kw).get("/api/showcase")
    assert r.status_code == 200, r.text
    return ShowcaseOut.model_validate(r.json())


# ── 계약 ────────────────────────────────────────────────────────────────────
def test_showcase_parses_and_converts_string_metrics_to_float(tmp_path: Path):
    out = _showcase(tmp_path / "a")
    table = out.eval_table
    assert table.split_mode == "holdout"
    assert table.source == {"metrics": "results/latest.csv", "p95": "results/latency.json"}
    assert [row.variant for row in table.rows] == ["pop", "cf", "hybrid", "hybrid_div"]
    first = table.rows[0]
    assert isinstance(first.recall_at_20, float)
    assert (first.recall_at_20, first.ndcg_at_10, first.ild_at_10) == (0.063, 0.054, 0.764)
    assert table.rows[3].ild_at_10 == 0.684


def test_showcase_p95_none_without_latency_json_and_filled_with(tmp_path: Path):
    without = _showcase(tmp_path / "no_latency")
    assert [row.p95_ms for row in without.eval_table.rows] == [None, None, None, None]
    with_latency = _showcase(
        tmp_path / "with_latency", latency={"p95": 41.2, "p50": 22.1, "p99": 88.0}
    )
    assert [row.p95_ms for row in with_latency.eval_table.rows] == [41.2, 41.2, 41.2, 41.2]


def test_showcase_constants_philosophy_mapping_memorable_roadmap_notice_verbatim(tmp_path: Path):
    out = _showcase(tmp_path / "c")
    assert out.philosophy == PHILOSOPHY and "QRS" in out.philosophy
    assert [m.model_dump() for m in out.metric_mapping] == [
        {"stage": "Candidate Retrieval", "metric": "Recall@20"},
        {"stage": "Ranking", "metric": "NDCG@10"},
        {"stage": "Re-ranking", "metric": "ILD@10"},
    ]
    assert len(out.memorable_5) == 5
    assert all(m.route.startswith("#/") for m in out.memorable_5)
    assert all(m.claim and m.how_to_verify for m in out.memorable_5)
    assert out.roadmap == list(ROADMAP) and len(out.roadmap) == 7
    assert out.data_notice == NOTICE_VERBATIM == DATA_NOTICE
    assert out.personal_case is None


# ── 정확성 ──────────────────────────────────────────────────────────────────
def test_load_eval_table_direct_matches_route_and_passes_split_mode_through(tmp_path: Path):
    root = tmp_path / "d"
    eval_path, latency_path = _paths(root, latency={"p95": 41.2})
    direct = load_eval_table(eval_path, latency_path)
    assert direct.model_dump() == _showcase(root, latency={"p95": 41.2}).eval_table.model_dump()

    raw = json.loads(EVAL_JSON)
    raw["meta"]["split_mode"] = "temporal"
    temporal_root = tmp_path / "e"
    t_eval, t_latency = _paths(temporal_root, eval_json=json.dumps(raw))
    assert load_eval_table(t_eval, t_latency).split_mode == "temporal"


# ── 안전성 ──────────────────────────────────────────────────────────────────
def test_missing_eval_table_is_200_with_empty_rows_unknown(tmp_path: Path):
    client = _client(tmp_path / "f", eval_json=None)
    r = client.get("/api/showcase")
    assert r.status_code == 200
    out = ShowcaseOut.model_validate(r.json())
    assert out.eval_table.rows == []
    assert out.eval_table.split_mode == "unknown"
    assert out.data_notice == NOTICE_VERBATIM
    assert "Traceback" not in r.text


def test_corrupt_eval_table_is_200_and_logged(tmp_path: Path, caplog):
    with caplog.at_level(logging.ERROR, logger="millie_rec.serving.dashboard_api"):
        r = _client(tmp_path / "g", eval_json="{not json").get("/api/showcase")
    assert r.status_code == 200
    out = ShowcaseOut.model_validate(r.json())
    assert out.eval_table.rows == [] and out.eval_table.split_mode == "unknown"
    errors = [rec for rec in caplog.records if rec.levelno >= logging.ERROR]
    assert len(errors) >= 1
    assert "Traceback" not in r.text


def test_row_without_metric_keys_is_skipped(tmp_path: Path):
    raw = json.loads(EVAL_JSON)
    del raw["rows"][1]["ndcg@10"]
    out = _showcase(tmp_path / "h", eval_json=json.dumps(raw))
    assert [row.variant for row in out.eval_table.rows] == ["pop", "hybrid", "hybrid_div"]


def test_no_query_params_or_request_path_building_source_grep():
    src = Path(dashboard_api.__file__).read_text(encoding="utf-8")
    assert "Query(" not in src
    assert "request." not in src
    assert src.count("EVAL_TABLE_PATH = ") == 1 and src.count("LATENCY_PATH = ") == 1
