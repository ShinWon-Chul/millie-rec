"""cascade 의 비개인화 단계 — seeds cold-start(확정 7) · level 2 세그먼트 인기 · level 3 전역 인기.

아키 §9-3 목록 외 신설(cascade.py 150줄 유지, Advisor 승인 2026-09-06) — PROGRESS 1줄은 05-09.
두 함수 모두 첫 인자 cs 는 serving.cascade.Cascade — 역참조 import 를 피하려고 타입을 적지 않는다.
"""

import logging
from dataclasses import replace

from fastapi import HTTPException

from millie_rec.contracts import (
    FALLBACK_GLOBAL_POP,
    FALLBACK_PERSONALIZED,
    FALLBACK_SEGMENT_POP,
    MODEL_VERSION_FALLBACK,
    MODEL_VERSION_SUFFIX,
    Pipeline,
    RecommendResponse,
    UserState,
)
from millie_rec.serving.compose import build_response, compose_rows
from millie_rec.serving.fallback import segment_popular
from millie_rec.serving.rows import ROW_SIZE

log = logging.getLogger(__name__)

CELL_VARIANT = {"A": "hybrid", "B": "hybrid_div"}  # 백엔드 01 §5 셀 배정
PIPE_K_MIN = 2 * ROW_SIZE  # persona_shelf 12 + fresh_picks leftover 재료(A6)


def variant_for(
    cell: str | None, model: str | None, pipelines: dict[str, Pipeline], default: str | None
) -> str | None:
    """model= 쿼리 > 셀 배정(D-01) > 기본 variant(Phase 2 D-11)."""
    if model in pipelines:
        return model
    want = CELL_VARIANT.get(cell or "")
    return want if want in pipelines else default


def cold_start(cs, seeds, name, k, t0, context, bd) -> RecommendResponse:
    """seeds 쿼리는 기존 1행 trending 유지(확정 7 · A6 k 그대로), 익명은 level 3."""
    user = UserState(None, explicit_seeds=seeds)
    if seeds and name:
        try:
            items = cs.pipelines[name].recommend(user, k)
            shown = cs.weights(user) if cs.weights is not None else None
        except Exception:
            log.exception("pipeline %s failed; cascading to level 3", name)
        else:
            resp = build_response(items, model_version=f"{name}{MODEL_VERSION_SUFFIX}",
                                  level=FALLBACK_PERSONALIZED, k=k, t0=t0, context=context,
                                  latency_breakdown=bd)  # fmt: skip
            return replace(resp, user_state_weights=dict(shown)) if shown is not None else resp
    return nonpersonal(cs, user, FALLBACK_GLOBAL_POP, (), k, t0, context, bd, None)


def nonpersonal(cs, user, level, categories, k, t0, context, bd, criterion) -> RecommendResponse:
    """level 2(세그먼트 인기)·3(전역 인기), 가중치 0. 단계마다 감싸 실패하면 다음으로 내려간다."""
    if level == FALLBACK_SEGMENT_POP:
        try:
            return _staged(cs, user, level, categories, k, t0, context, bd, criterion)
        except HTTPException:
            raise  # 404·422 는 의도된 응답이다 — 삼키지 않는다
        except Exception:
            log.exception("level 2 failed; cascading to level 3")
        categories = ()  # 세그먼트가 깨졌으니 전역으로 내려간다
    try:
        return _staged(cs, user, FALLBACK_GLOBAL_POP, categories, k, t0, context, bd, criterion)
    except HTTPException:
        raise
    except Exception:
        log.exception("level 3 failed; serving catalog-free minimal response")
    return minimal(k, t0, context, bd)


def _staged(cs, user, level, categories, k, t0, context, bd, criterion) -> RecommendResponse:
    """한 단계의 재료 → 행 조립 → 응답. catalog 가 없으면 기존 1행(스켈레톤 기동)."""
    if level == FALLBACK_SEGMENT_POP:
        items = segment_popular(cs.catalog, user, categories, k)
    else:
        items = cs.fallback.recommend(user, k)
    rows, dd = None, 0
    if cs.catalog is not None:
        rows, dd = compose_rows(items=items, catalog=cs.catalog, neighbors=None, level=level,
                                categories=categories, criterion=criterion,
                                all_categories=cs.all_categories)  # fmt: skip
    return build_response(items, model_version=MODEL_VERSION_FALLBACK, level=level, k=k, t0=t0,
                          context=context, rows=rows, dedup_removed=dd,
                          latency_breakdown=bd)  # fmt: skip


def minimal(k, t0, context, bd) -> RecommendResponse:
    """마지막 안전망 — 카탈로그를 건드리지 않는 빈 trending 1행, level 3, 가중치 0."""
    return build_response((), model_version=MODEL_VERSION_FALLBACK, level=FALLBACK_GLOBAL_POP,
                          k=k, t0=t0, context=context, latency_breakdown=bd)  # fmt: skip
