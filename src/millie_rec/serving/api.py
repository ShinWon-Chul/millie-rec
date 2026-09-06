"""FastAPI create_app · lifespan(스키마·24h 리플레이·Nearline) · /health · /api/recommend 껍데기.

라우터 3개 include(백엔드 서빙 01 §0·§1·§5). 판정·조립 로직은 cascade.py·rec_log.py 에 있다.
"""

import asyncio
import contextlib
import logging
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from time import perf_counter
from typing import Annotated

from fastapi import FastAPI, HTTPException, Query

from millie_rec.contracts import (
    MODEL_VERSION_SUFFIX,
    VARIANTS,
    BookStatsSource,
    Catalog,
    Neighbors,
    Pipeline,
    UserState,
)
from millie_rec.serving.authors_api import build_router as authors_router
from millie_rec.serving.cascade import Cascade
from millie_rec.serving.compose import catalog_categories, default_variant
from millie_rec.serving.db import Database
from millie_rec.serving.demo_api import build_router as demo_router
from millie_rec.serving.fallback import Level1Cache
from millie_rec.serving.nearline import NearlineLoop
from millie_rec.serving.onboarding_api import build_router as onboarding_router
from millie_rec.serving.onboarding_api import load_meta
from millie_rec.serving.privacy_api import build_router as privacy_router
from millie_rec.serving.ratings_api import build_router as ratings_router
from millie_rec.serving.schemas import API_VERSION, HealthOut, RecommendOut

log = logging.getLogger(__name__)
K_DEFAULT, K_MAX = 40, 100  # 백엔드 01 §5 "k 기본 40" · §0 "k ≤ 100"


def _422(param: str, msg: str) -> HTTPException:
    return HTTPException(422, detail=[{"loc": ["query", param], "msg": msg, "type": "value_error"}])


def _parse_seeds(raw: str | None) -> tuple[int, ...]:
    """'1,2,3' → (1, 2, 3). 정수가 아니면 FastAPI 규약대로 422."""
    if not raw:
        return ()
    try:
        return tuple(int(s) for s in raw.split(",") if s.strip())
    except ValueError as e:
        raise _422("seeds", "seeds must be comma-separated integers") from e


def create_app(pipelines: dict[str, Pipeline], fallback: Pipeline, *,
               catalog: Catalog | None = None, db: Database,
               neighbors: Neighbors | None = None, book_stats: BookStatsSource | None = None,
               weights: Callable[[UserState], dict[str, float]] | None = None,
               state: object | None = None, segpop: object | None = None) -> FastAPI:  # fmt: skip
    """주입만 받는다. 비즈니스 규칙은 슬라이스 함수에. db 는 keyword-only 필수(D-09 + 리뷰 W-1).

    weights: ranking.state_weights 주입(Phase 4 D-09) — 없으면 user_state_weights 는 0 셋.
    segpop: data.SegmentPopularity 주입 — 없으면 폴백 2단계가 기존 카테고리 인기로 돈다.
    시그니처가 한 줄에 모인 이유는 이 파일이 150줄 상한이라서다(Cascade.__init__ 과 같은 관례).
    """
    started = {"t": perf_counter()}
    loaded_at = datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
    default = default_variant(pipelines)  # D-11. compose.py 에 두어 api.py ≤150줄 유지
    cache = Level1Cache()
    all_cats = catalog_categories(catalog) if catalog is not None else []  # 기동 1회
    labels = {c["id"]: c["label"] for c in load_meta()["criteria"]}
    nearline = NearlineLoop(db, state, neighbors=neighbors) if state is not None else None
    wake_box: dict[str, Callable[[], None] | None] = {"fn": None}
    inv = cache.invalidate
    cascade = Cascade(pipelines, fallback, catalog=catalog, db=db, neighbors=neighbors,
                      store=state, cache=cache, weights=weights, default=default,
                      all_categories=all_cats, criteria_labels=labels, segpop=segpop)  # fmt: skip

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        db.apply_schema()  # D-06: 행은 쓰지 않는다. 스키마·PRAGMA 만
        started["t"] = perf_counter()
        task = None
        if nearline is not None:
            nearline.replay()  # D-08: 최근 24h events 만
            wake_box["fn"] = nearline.waker(asyncio.get_running_loop())  # 확정 13
            task = asyncio.create_task(nearline.run())
        try:
            yield
        finally:
            if task is not None:
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await task
            db.close()

    app = FastAPI(title="millie-rec", version=API_VERSION, lifespan=lifespan)
    app.state.cascade, app.state.nearline = cascade, nearline
    app.state.store, app.state.cache = state, cache

    def wake_fn() -> None:
        """동기 핸들러는 Event.set() 을 직접 부르지 않는다 — 루프 스레드로 넘긴다(확정 13)."""
        if wake_box["fn"] is not None:
            wake_box["fn"]()

    app.include_router(onboarding_router(db=db, catalog=catalog))
    app.include_router(authors_router(catalog=catalog))  # 취향 설정 작가 선택 화면(D91)
    app.include_router(demo_router(db=db, catalog=catalog, wake=wake_fn, invalidate=inv))
    app.include_router(privacy_router(db=db, catalog=catalog, state=state, weights=weights,
                                      invalidate=inv))  # fmt: skip
    app.include_router(ratings_router(db=db, wake=wake_fn, invalidate=inv))
    try:  # 05-07 이 병렬로 만드는 중 — wave 2 종료 후엔 항상 존재
        from millie_rec.serving.dashboard_api import build_router as dashboard_router

        app.include_router(dashboard_router(db=db))
    except ImportError:
        log.info("dashboard_api not present yet (wave 2 parallel)")

    @app.get("/health", response_model=HealthOut)
    def health() -> HealthOut:  # 동기 def — 스레드풀 (serving.md 이벤트 루프 규칙)
        ok, loaded = db.ok(), catalog is not None
        ver = f"{default}{MODEL_VERSION_SUFFIX}" if default and loaded else None
        return HealthOut(status="ok", db_ok=ok, db_row_count=db.row_counts() if ok else {},
                         model_version=ver,
                         artifacts_loaded_at=loaded_at if loaded else None,
                         nearline_last_run=nearline.last_run if nearline is not None else None,
                         uptime_s=perf_counter() - started["t"])  # fmt: skip

    @app.get("/api/recommend", response_model=RecommendOut)
    def recommend(
        user_key: Annotated[str | None, Query()] = None,
        snapshot_id: Annotated[str | None, Query()] = None,
        model: Annotated[str | None, Query()] = None,
        k: Annotated[int, Query(ge=1, le=K_MAX)] = K_DEFAULT,
        context: Annotated[str | None, Query()] = None,
        seeds: Annotated[str | None, Query()] = None,
    ) -> RecommendOut:
        if model is not None and model not in VARIANTS:
            raise _422("model", f"model must be one of {list(VARIANTS)}")
        resp, forced = cascade.respond(user_key=user_key or None, snapshot_id=snapshot_id,
                                       model=model, k=k, context=context,
                                       seeds=_parse_seeds(seeds))  # fmt: skip
        return RecommendOut.from_contract(resp, forced=forced)

    return app
