"""Track B(밀리 카탈로그) 4 variant 조립(D-10).

cf 채널 = CatalogKR.neighbors 엣지 · content 채널 = VectorsKR(SVD 128) · pop = pop_rank.
표기는 전부 content(data.md). pandas 없음(서빙 경로).
"""

import logging
from dataclasses import replace
from pathlib import Path

from millie_rec.app.pipeline import (
    CF,
    HYBRID,
    HYBRID_DIV,
    POP,
    SOURCE_POPULARITY,
    StagedPipeline,
    WeightFn,
)
from millie_rec.contracts import BookStatsSource, Catalog, Pipeline, ScoredItem, UserState
from millie_rec.data import DIR_SERVING, VECTORS_KR_NPZ, CatalogKR, VectorsKR
from millie_rec.ranking import CH_CF, CH_CONTENT, CH_POP, CHANNEL_WEIGHTS
from millie_rec.reranking import DifficultyGuard, MMRReranker
from millie_rec.retrieval import TOP_N, NeighborRetriever, PopularityRetriever, VectorRetriever

log = logging.getLogger(__name__)


class CatalogPopPipeline:
    """D-13: Track B 인기(pop_rank 순, seen 제외) + meta 조인.

    GlobalPopularFallback 과 같은 점수 관례, name 만 'pop'(model_version pop_v1).
    """

    name = POP

    def __init__(self, catalog: Catalog) -> None:
        self.catalog = catalog

    def recommend(self, user: UserState, k: int) -> list[ScoredItem]:
        ids = [b for b in self.catalog.popular(n=k + len(user.seen)) if b not in user.seen][:k]
        meta = {int(m["book_id"]): m for m in self.catalog.meta(ids)}
        items = []
        for i, b in enumerate(ids):
            m = meta.get(b, {})
            items.append(
                ScoredItem(
                    book_id=b,
                    score=float(len(ids) - i),
                    source=SOURCE_POPULARITY,
                    position=i,
                    source_channels=(SOURCE_POPULARITY,),
                    title=m.get("title"),
                    authors=m.get("authors"),
                    image_url=m.get("image_url"),
                    book_format=m.get("book_format"),
                    difficulty=m.get("difficulty"),
                )
            )
        return items


def load_vectors_kr(serving_dir: Path = DIR_SERVING) -> VectorsKR | None:
    """load_catalog 패턴: 파일 없음 → None(로그), 손상 → 로그 후 None, 정상 → VectorsKR."""
    path = serving_dir / VECTORS_KR_NPZ
    if not path.exists():
        log.info("no vectors at %s — serving without content channel/MMR", path)
        return None
    try:
        return VectorsKR.load(path)
    except (OSError, ValueError, KeyError):
        log.exception("vectors unreadable at %s — serving without content channel/MMR", path)
        return None


class WithMeta:
    """Pipeline 데코레이터 — catalog.meta 5필드(제목·저자·표지·포맷·난이도) 조인. name 은 안쪽."""

    def __init__(self, inner: Pipeline, catalog: Catalog) -> None:
        self.inner, self.catalog, self.name = inner, catalog, inner.name

    @property
    def last_breakdown(self) -> dict[str, float] | None:
        """D-09: 안쪽 StagedPipeline 의 구간 밀리초를 그대로 통과시킨다."""
        return getattr(self.inner, "last_breakdown", None)

    def recommend(self, user: UserState, k: int) -> list[ScoredItem]:
        items = self.inner.recommend(user, k)
        meta = {int(m["book_id"]): m for m in self.catalog.meta([i.book_id for i in items])}
        out = []
        for i in items:
            m = meta.get(i.book_id, {})
            out.append(
                replace(
                    i,
                    title=m.get("title"),
                    authors=m.get("authors"),
                    image_url=m.get("image_url"),
                    book_format=m.get("book_format"),
                    difficulty=i.difficulty if i.difficulty is not None else m.get("difficulty"),
                )
            )
        return out


def build_pipelines_kr(
    catalog: CatalogKR,
    *,
    weights: WeightFn | None = None,
    vectors: VectorsKR | None = None,
    book_stats: BookStatsSource | None = None,
) -> dict[str, Pipeline]:
    """vectors 없으면 load_vectors_kr(), 그래도 None 이면 pop 만(Phase 3) — 기동을 막지 않는다."""
    vectors = vectors if vectors is not None else load_vectors_kr()
    bs = book_stats or catalog  # 05-08: 서버는 ServingBookStats 주입(D-07), 없으면 카탈로그 자신
    pops: dict[str, Pipeline] = {POP: CatalogPopPipeline(catalog)}
    if vectors is None:
        return pops
    ranked = catalog.popular(n=TOP_N)
    pop_r = PopularityRetriever([(b, float(len(ranked) - i)) for i, b in enumerate(ranked)])
    nbr = NeighborRetriever(catalog, weights=weights)  # source="content" 기본(data.md)
    ids = catalog.eligible(vectors.book_ids)  # 03-CONTEXT D-14 eligible 선필터
    vec = VectorRetriever(vectors, ids, weights=weights)
    three = {CH_CF: nbr, CH_CONTENT: vec, CH_POP: pop_r}
    kw = {"weights": dict(CHANNEL_WEIGHTS), "book_stats": bs, "catalog": catalog}
    staged = {
        CF: StagedPipeline(CF, {CH_CF: nbr}, weights={CH_CF: 1.0}, catalog=catalog),
        HYBRID: StagedPipeline(HYBRID, three, **kw),
        HYBRID_DIV: StagedPipeline(
            HYBRID_DIV, three, rerankers=(MMRReranker(vectors), DifficultyGuard(bs)), **kw
        ),
    }
    return {**pops, **{name: WithMeta(p, catalog) for name, p in staged.items()}}
