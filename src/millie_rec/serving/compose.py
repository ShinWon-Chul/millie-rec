"""응답 조립 — Must 5행 순서·dedup·배지 부착·응답 DTO(05-CONTEXT D-01~D-04).

렌더 순서 정본 = ROW_ORDER. 행 하나를 만드는 일은 serving/rows.py, 배지 규칙은 serving/badges.py.
rows=None 이면 Phase 2 1행 형태(seeds cold-start 호환, Advisor 확정 7). __init__ 에 노출하지 않는다.
"""

import uuid
from collections import Counter
from collections.abc import Sequence
from dataclasses import replace
from time import perf_counter

from millie_rec.contracts import (
    FALLBACK_CACHE,
    FALLBACK_PERSONALIZED,
    FALLBACK_SEGMENT_POP,
    ROW_ANCHOR_PREFIX,
    VARIANTS,
    Catalog,
    Neighbors,
    Pipeline,
    Recommendation,
    RecommendResponse,
    Row,
    ScoredItem,
)
from millie_rec.serving.after_completion import prepend_after
from millie_rec.serving.badges import attach_badges
from millie_rec.serving.editions import drop_same_work, normalize_title
from millie_rec.serving.fallback import trending_row
from millie_rec.serving.rows import ROW_SIZE, fresh_row, mix, personal_rows, with_meta

# 백엔드 01 §5 "익명은 3, 가중치 전부 0". blend 는 Phase 4·상태는 Phase 5
ZERO_WEIGHTS = {"alpha": 0.0, "beta": 0.0, "gamma": 0.0}
# 렌더 순서의 정본(contracts.ROW_IDS 는 집합). 행 크기·제목 상수는 rows.py
ROW_ORDER = ("after_completion", "continue_reading", ROW_ANCHOR_PREFIX, "persona_shelf",
             "trending", "fresh_picks")  # fmt: skip


def default_variant(pipelines: dict[str, Pipeline]) -> str | None:
    """Phase 2 D-11: 등록된 것 중 VARIANTS 순서상 마지막. 셀 배정(A/B)은 Phase 5 몫."""
    registered = [v for v in VARIANTS if v in pipelines]
    return registered[-1] if registered else None


def new_rec_id() -> str:
    return "rec_" + uuid.uuid4().hex[:6]  # 백엔드 01 §0 ID 형식 rec_<6hex> (Phase 1 D-03)


def catalog_categories(catalog: Catalog) -> list[str]:
    """eligible 도서의 카테고리, 권수 내림차순(동률은 등장 순). 기동 시 1회만 부른다."""
    counts = Counter(
        c for m in catalog.meta(catalog.popular(n=10**6)) for c in (m.get("categories") or [])
    )
    return [c for c, _ in counts.most_common()]


def dedup_rows(rows: Sequence[Row]) -> tuple[tuple[Row, ...], int]:
    """D-04: 렌더 순서 앞 행 우선, book_id 와 정규화 제목 둘 다. channel_mix 는 재계산."""
    seen_ids: set[int] = set()
    seen_titles: set[str] = set()
    removed, out = 0, []
    for row in rows:
        kept: list[ScoredItem] = []
        for i in row.items:
            key = normalize_title(i.title)
            if i.book_id in seen_ids or (key and key in seen_titles):
                removed += 1
                continue
            seen_ids.add(i.book_id)
            if key:
                seen_titles.add(key)
            kept.append(replace(i, position=len(kept)))
        out.append(replace(row, items=tuple(kept), channel_mix=mix(kept)))
    return tuple(out), removed


def compose_rows(
    *,
    items: Sequence[ScoredItem],
    catalog: Catalog,
    neighbors: Neighbors | None,
    level: int,
    seeds: Sequence[int] = (),
    categories: Sequence[str] = (),
    criterion: str | None = None,
    criteria: Sequence[str] = (),
    picked_authors: Sequence[str] = (),
    persona_name: str | None = None,
    continue_ids: Sequence[int] = (),
    read_ids: Sequence[int] = (),
    all_categories: Sequence[str] = (),
    after_completion: tuple[int, Sequence[tuple[int, float]]] | None = None,
    k: int = ROW_SIZE,
) -> tuple[tuple[Row, ...], int]:
    """Must 5행 + dedup + 배지 → (rows, dedup_removed). 행 크기는 k 가 아니라 ROW_SIZE 고정."""
    if level >= FALLBACK_SEGMENT_POP:  # SERV-08 비개인화 2행 — items 는 호출자가 넘긴 인기
        trend = trending_row(with_meta(tuple(items)[:ROW_SIZE], catalog))
        exclude = {int(s) for s in seeds} | {i.book_id for i in trend.items}
        rows: tuple[Row, ...] = (trend, fresh_row(catalog, (), (), all_categories, exclude))
    else:
        rows = personal_rows(items, catalog, neighbors, seeds, categories, persona_name,
                             continue_ids, all_categories)  # fmt: skip
        rows = prepend_after(rows, after_completion, catalog, seeds)  # D-13 최상단
    read = {int(s) for s in seeds} | {int(b) for b in read_ids}
    if after_completion:
        read.add(int(after_completion[0]))
    rows = drop_same_work(rows, catalog, sorted(read))  # 이미 읽은 작품의 판본(보고 09-06)
    rows, removed = dedup_rows(rows)
    return attach_badges(rows, catalog, criterion, seeds, criteria=criteria,
                         picked_authors=picked_authors), removed  # fmt: skip


def build_response(
    items: Sequence[ScoredItem],
    *,
    model_version: str,
    level: int,
    k: int,
    t0: float,
    context: str | None,
    rows: Sequence[Row] | None = None,
    dedup_removed: int = 0,
    latency_breakdown: dict[str, float] | None = None,
    user_state_weights: dict[str, float] | None = None,
) -> RecommendResponse:
    """rows=None 이면 Phase 2 형태(trending 1행). rows 를 받으면 행 순서 평탄화 상위 k."""
    ms = (perf_counter() - t0) * 1000
    if rows is None:
        rows_t: tuple[Row, ...] = (trending_row(items),)
        flat = tuple(Recommendation(i.book_id, i.score) for i in items[:k])
        keep = level == FALLBACK_PERSONALIZED
    else:
        rows_t = tuple(rows)
        flat = tuple(
            Recommendation(i.book_id, i.score, i.title, i.reason) for r in rows_t for i in r.items
        )[:k]
        keep = level <= FALLBACK_CACHE
    return RecommendResponse(
        items=flat if keep else (),
        model_version=model_version,
        fallback_level=level,
        latency_ms=ms,
        recommendation_id=new_rec_id(),
        rows=rows_t,
        latency_breakdown={**(latency_breakdown or {}), "total": ms},
        user_state_weights=dict(user_state_weights or ZERO_WEIGHTS),
        dedup_removed=dedup_removed,
        context=context,
    )
