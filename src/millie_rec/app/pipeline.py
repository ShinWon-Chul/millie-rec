"""variant 조립 — dict 하나(아키텍처 01 §3-3).

Track A fit_pipelines(make eval) · 서버 build_pipelines(Track B 조립은 pipeline_kr).
"""

import logging
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

from millie_rec.app.staged import PopPipeline, StagedPipeline  # 기존 import 경로 유지(re-export)
from millie_rec.contracts import VARIANTS, BookStatsSource, Catalog, Pipeline, UserState
from millie_rec.data import BOOKS_KR_JSON, DIR_SERVING, CatalogKR
from millie_rec.ranking import CH_CF, CH_CONTENT, CH_POP, CHANNEL_WEIGHTS
from millie_rec.reranking import DifficultyGuard, MMRReranker
from millie_rec.retrieval import (
    POP_ARTIFACT,
    ContentVectors,
    PopularityRetriever,
    load_or_fit_itemknn,
)

if TYPE_CHECKING:
    import pandas as pd

log = logging.getLogger(__name__)
POP, CF, HYBRID, HYBRID_DIV = VARIANTS  # 이름의 정본은 contracts.VARIANTS
SOURCE_POPULARITY = "popularity"  # serving/fallback.py 와 같은 값 — 공개 표면에 없어 중복 정의
WeightFn = Callable[[UserState], dict[str, float]]


def fit_pipelines(
    train: "pd.DataFrame",
    vectors: ContentVectors,
    *,
    knn_artifact: Path | None = None,
    weights: WeightFn | None = None,
) -> dict[str, Pipeline]:
    """make eval 용. 키 = VARIANTS 4종. vectors 는 content 채널·MMR 양쪽에 쓴다(D-04)."""
    pop = PopularityRetriever().fit(train)
    knn = load_or_fit_itemknn(train, knn_artifact, weights=weights)
    three = {CH_CF: knn, CH_CONTENT: vectors, CH_POP: pop}
    return {
        POP: PopPipeline(pop),
        CF: StagedPipeline(CF, {CH_CF: knn}, weights={CH_CF: 1.0}),
        HYBRID: StagedPipeline(HYBRID, three, weights=dict(CHANNEL_WEIGHTS)),
        HYBRID_DIV: StagedPipeline(
            HYBRID_DIV,
            three,
            weights=dict(CHANNEL_WEIGHTS),
            rerankers=(MMRReranker(vectors), DifficultyGuard(None)),  # D-08. Track A 가드 패스스루
        ),
    }


def load_catalog(serving_dir: Path = DIR_SERVING) -> CatalogKR | None:
    """D-13: books_kr.json 있으면 CatalogKR, 없으면 None(Phase 2 동작), 손상이면 로그 후 None."""
    if not (serving_dir / BOOKS_KR_JSON).exists():
        log.info("no catalog at %s — serving without Track B catalog", serving_dir)
        return None
    try:
        return CatalogKR.load(serving_dir)
    except (OSError, ValueError, KeyError, TypeError):  # json 손상·키 누락·형 불일치
        log.exception("catalog unreadable at %s — serving without catalog", serving_dir)
        return None


def build_pipelines(
    artifact: Path = POP_ARTIFACT,
    *,
    catalog: Catalog | None = None,
    weights: WeightFn | None = None,
    book_stats: BookStatsSource | None = None,
) -> dict[str, Pipeline]:
    """서버 기동. 카탈로그 있으면 Track B 4 variant(pipeline_kr, D-10), 없으면 Goodbooks pop."""
    if catalog is not None:
        from millie_rec.app.pipeline_kr import build_pipelines_kr  # 순환 회피

        return build_pipelines_kr(catalog, weights=weights, book_stats=book_stats)
    if not artifact.exists():
        log.info("no pop artifact at %s — serving level 3 only", artifact)
        return {}
    try:
        return {POP: PopPipeline(PopularityRetriever.load(artifact))}
    except (OSError, ValueError, KeyError, TypeError):  # json 손상·키 누락·형 불일치
        log.exception("pop artifact unreadable at %s — serving level 3 only", artifact)
        return {}
