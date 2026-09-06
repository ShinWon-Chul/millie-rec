"""app/pipeline.py — 계약(Pipeline·ScoredItem) · 정확성(Candidate→ScoredItem·seen 제외) ·
안전성(아티팩트 없음·손상 → {} 기동).
"""

import logging

import pandas as pd

from millie_rec.app.pipeline import StagedPipeline, build_pipelines, fit_pipelines, load_catalog
from millie_rec.app.pipeline_kr import CatalogPopPipeline
from millie_rec.contracts import COL_ITEM, VARIANTS, ScoredItem, UserState
from millie_rec.data import CatalogKR
from millie_rec.retrieval import ContentVectors, PopularityRetriever

TAGS = ("fantasy magic", "history war", "romance drama", "science space")


def _books50() -> pd.DataFrame:
    return pd.DataFrame({COL_ITEM: list(range(50)), "tags": [TAGS[i % 4] for i in range(50)]})


# ── 안전성 ──────────────────────────────────────────────────────────────
def test_build_pipelines_empty_when_artifact_missing(tmp_path):
    assert build_pipelines(tmp_path / "none.json") == {}


def test_build_pipelines_empty_and_logged_when_artifact_malformed(tmp_path, caplog):
    broken = tmp_path / "popularity.json"
    with caplog.at_level(logging.ERROR):
        broken.write_text("not json", encoding="utf-8")
        assert build_pipelines(broken) == {}
        assert len([r for r in caplog.records if r.levelno >= logging.ERROR]) >= 1
        caplog.clear()
        broken.write_text('{"name": "pop"}', encoding="utf-8")  # items 키 없음
        assert build_pipelines(broken) == {}
        assert len([r for r in caplog.records if r.levelno >= logging.ERROR]) >= 1


# ── 계약 · 정확성 ────────────────────────────────────────────────────────
def test_build_pipelines_loads_pop_and_recommend_excludes_seen(tmp_path):
    path = tmp_path / "popularity.json"
    PopularityRetriever([(1, 3.0), (2, 2.0), (3, 1.0)]).save(path)
    pipes = build_pipelines(path)
    assert set(pipes) == {"pop"}
    assert pipes["pop"].name == "pop"
    items = pipes["pop"].recommend(UserState(user_id=None, explicit_seeds=(1,)), 2)
    assert [i.book_id for i in items] == [2, 3]
    assert [i.position for i in items] == [0, 1]
    assert [i.score for i in items] == [2.0, 1.0]
    assert all(isinstance(i, ScoredItem) for i in items)
    assert all(i.source == "popularity" for i in items)
    assert all(i.source_channels == ("popularity",) for i in items)


def test_fit_pipelines_keys_are_variants_and_recommend_returns_k(interactions):
    pipes = fit_pipelines(interactions, ContentVectors(_books50()))
    assert set(pipes) == set(VARIANTS)
    # 공동 소비가 많은 seed — cf 후보가 5개 이상 나오게
    top3 = tuple(int(b) for b in interactions[COL_ITEM].value_counts().index[:3])
    u = UserState(None, explicit_seeds=top3)
    for name in VARIANTS:
        assert pipes[name].name == name
        items = pipes[name].recommend(u, 5)
        assert len(items) == 5 and all(isinstance(i, ScoredItem) for i in items)
        assert not {i.book_id for i in items} & u.seen
        assert [i.position for i in items] == [0, 1, 2, 3, 4]
    assert isinstance(pipes["cf"], StagedPipeline) and isinstance(
        pipes["hybrid_div"], StagedPipeline
    )
    assert hasattr(pipes["pop"], "retriever")  # cli.cmd_eval 이 pop.retriever.save 를 부른다


def test_fit_pipelines_knn_artifact_written_only_when_path_given(interactions, tmp_path):
    fit_pipelines(interactions, ContentVectors(_books50()), knn_artifact=tmp_path / "knn.npz")
    assert (tmp_path / "knn.npz").exists()
    fit_pipelines(interactions, ContentVectors(_books50()))
    assert len(list(tmp_path.iterdir())) == 1


# ── Phase 3 D-13: 카탈로그 주입 ─────────────────────────────────────────
class _FakeCatalog:
    """popular·meta·eligible 만 — Track B pop 이 쓰는 표면."""

    def meta(self, book_ids):
        return [
            {
                "book_id": b,
                "title": f"책{b}",
                "authors": "a",
                "image_url": "https://img.millie.co.kr/x.jpg",
                "book_format": "전자책",
                "difficulty": 0.4,
            }
            for b in book_ids
        ]

    def popular(self, categories=(), n=50):
        return list(range(1, 11))[:n]

    def eligible(self, book_ids):
        return list(book_ids)


def test_build_pipelines_with_catalog_uses_track_b_pop_and_skips_artifact(
    tmp_path, caplog, monkeypatch
):
    monkeypatch.setattr("millie_rec.app.pipeline_kr.load_vectors_kr", lambda *a, **k: None)
    broken = tmp_path / "popularity.json"
    broken.write_text("not json", encoding="utf-8")
    with caplog.at_level(logging.ERROR):
        pipes = build_pipelines(broken, catalog=_FakeCatalog())
    assert set(pipes) == {"pop"}
    assert isinstance(pipes["pop"], CatalogPopPipeline)
    assert [r for r in caplog.records if r.levelno >= logging.ERROR] == []  # 아티팩트를 열지 않는다
    items = pipes["pop"].recommend(UserState(None, explicit_seeds=(1,)), 2)
    assert [i.book_id for i in items] == [2, 3]
    assert [i.position for i in items] == [0, 1]
    assert [i.score for i in items] == [2.0, 1.0]
    assert all(i.source == "popularity" and i.source_channels == ("popularity",) for i in items)
    assert (
        items[0].title == "책2" and items[0].book_format == "전자책" and items[0].difficulty == 0.4
    )


def test_load_catalog_none_when_missing_or_corrupt(tmp_path, caplog):
    with caplog.at_level(logging.INFO):
        assert load_catalog(tmp_path) is None
    assert any(r.levelno == logging.INFO for r in caplog.records)
    caplog.clear()
    (tmp_path / "books_kr.json").write_text("not json", encoding="utf-8")
    with caplog.at_level(logging.ERROR):
        assert load_catalog(tmp_path) is None
    assert len([r for r in caplog.records if r.levelno >= logging.ERROR]) == 1


def test_load_catalog_reads_serving_dir(millie_serving_sample):
    cat = load_catalog(millie_serving_sample)
    assert isinstance(cat, CatalogKR)
    assert cat.popular(n=3) == [1, 2, 3]
