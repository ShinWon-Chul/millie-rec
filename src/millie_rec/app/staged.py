"""Pipeline 구현 2종 — PopPipeline(단독 retriever) · StagedPipeline(4단계).

app/pipeline.py 가 150줄 한도에 닿아 분리(Advisor 확정 17 B4). 기존 import 경로는
app/pipeline.py 의 re-export 로 유지한다.
"""

import threading
from collections.abc import Sequence
from dataclasses import replace
from time import perf_counter

from millie_rec.contracts import (
    VARIANTS,
    BookStatsSource,
    CandidateGenerator,
    Catalog,
    Reranker,
    ScoredItem,
    UserState,
)
from millie_rec.ranking import blend_channels
from millie_rec.retrieval import POOL, PopularityRetriever

POP = VARIANTS[0]  # 이름의 정본은 contracts.VARIANTS
MS = 1000.0


class PopPipeline:
    """contracts.Pipeline 구현 — retriever 단독 variant 의 glue(Candidate → ScoredItem)."""

    name = POP

    def __init__(self, retriever: PopularityRetriever) -> None:
        self.retriever = retriever

    def recommend(self, user: UserState, k: int) -> list[ScoredItem]:
        return [
            ScoredItem(
                book_id=c.book_id,
                score=c.score,
                source=c.source,
                position=i,
                source_channels=(c.source,),
            )
            for i, c in enumerate(self.retriever.retrieve(user, k))
        ]


class StagedPipeline:
    """contracts.Pipeline — 슬롯 retriever(풀) → blend_channels → rerankers → 상위 k(D-01·D-08)."""

    def __init__(
        self,
        name: str,
        channels: dict[str, CandidateGenerator],
        *,
        weights: dict[str, float] | None = None,
        rerankers: Sequence[Reranker] = (),
        book_stats: BookStatsSource | None = None,
        catalog: Catalog | None = None,
        pool: int = POOL,
    ) -> None:
        self.name = name  # 인스턴스 속성 — Protocol name: str 은 인스턴스로도 만족
        self.channels, self.weights, self.rerankers = dict(channels), weights, tuple(rerankers)
        self.book_stats, self.catalog, self.pool = book_stats, catalog, pool
        self._tl = threading.local()  # 요청 스레드마다 자기 breakdown(revision C2)

    @property
    def last_breakdown(self) -> dict[str, float]:
        """D-09: 직전 recommend 의 구간 밀리초. 아직 없으면 빈 dict."""
        return getattr(self._tl, "bd", {})

    def recommend(self, user: UserState, k: int) -> list[ScoredItem]:
        t = perf_counter()
        cands = {slot: r.retrieve(user, self.pool) for slot, r in self.channels.items()}
        t1 = perf_counter()
        # catalog 는 Track B 에만 있다 — 세부 분류 가점이 Track A 평가 숫자를 건드리지 않는 경계
        items = blend_channels(user, cands, self.weights, book_stats=self.book_stats,
                               catalog=self.catalog)  # fmt: skip
        if self.catalog is not None:  # main §7 노출 자격 게이트(Track B 엣지 dst 는 자격 미검사)
            ok = set(self.catalog.eligible([i.book_id for i in items]))
            items = [i for i in items if i.book_id in ok]
        t2 = perf_counter()
        last = len(self.rerankers) - 1
        for n_, rr in enumerate(self.rerankers):
            # 마지막 reranker 만 k — 앞 단계(MMR)는 풀(≤50)을 재배열만 해 가드가 위반 책을
            # N 밖으로 내리고 다음 책을 끌어올릴 자리를 남긴다(그리디는 prefix-일관).
            items = rr.rerank(user, items, k if n_ == last else len(items))
        # D-09 타이밍만 — 상수·로직·반환값 무변경. eligible 필터는 ranking 구간에 든다
        ret, rank, rer = (t1 - t) * MS, (t2 - t1) * MS, (perf_counter() - t2) * MS
        self._tl.bd = {"retrieval": ret, "ranking": rank, "rerank": rer}
        return [replace(i, position=n) for n, i in enumerate(items[:k])]
