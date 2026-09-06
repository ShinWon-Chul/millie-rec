"""uvicorn 진입점: create_app 주입 + demo/ StaticFiles(마지막). CORS 없음(아키텍처 01 §9-3)."""

import logging
import os

from fastapi.staticfiles import StaticFiles

from millie_rec.app.pipeline import build_pipelines, load_catalog
from millie_rec.contracts import ROOT
from millie_rec.ranking import state_weights
from millie_rec.serving import (
    Database,
    GlobalPopularFallback,
    ServingBookStats,
    StateStore,
    create_app,
    resolve_db_path,
)


def init_sentry() -> bool:
    """SENTRY_DSN 있을 때만 Sentry 초기화 — 없으면 SDK import 도 안 한다(07-CONTEXT D-04)."""
    dsn = os.environ.get("SENTRY_DSN")
    if not dsn:
        return False
    import sentry_sdk  # 지연 import — 로컬·테스트 기동 경로는 SDK 를 건드리지 않는다(네트워크 0)

    # traces 0 = 예외만 · PII off + 요청 본문 미수집(Codex C4) = 가명 user_key 외 미전송
    env = os.environ.get("RAILWAY_ENVIRONMENT_NAME", "local")
    try:  # fail-open(Codex F1) — 관측 기능이 기동을 막지 않는다. DSN 은 로그에 안 남긴다
        sentry_sdk.init(dsn=dsn, traces_sample_rate=0, send_default_pii=False, environment=env,
                        max_request_body_size="never")  # fmt: skip
    except Exception:
        logging.getLogger(__name__).warning("SENTRY_DSN 이 잘못돼 Sentry 를 끕니다")
        return False
    return True


init_sentry()

# Phase 3 D-13: artifacts/serving/books_kr.json 있으면 CatalogKR 하나를
# catalog·neighbors·fallback 에 주입(세 Protocol 을 한 객체가 만족),
# 없거나 손상이면 None → Phase 2 동작(D-10). 시그니처 불변(Phase 1 D-09) — 인자만 채운다.
# Phase 4 D-09: 같은 state_weights 를 파이프라인(성분 가중)과 응답(user_state_weights) 양쪽에
# → 표시 혼합비 = 실제 혼합비.
# Phase 5 D-07·D-08: 상태 1개를 create_app(state=) 와 파이프라인 book_stats 양쪽에
# → 가드·gap 이 서빙 완독 수·user_level 을 본다. 카탈로그 없으면 stats 도 없다(local-run.md)
catalog = load_catalog()
store = StateStore()
stats = ServingBookStats(catalog, store) if catalog is not None else None
app = create_app(
    pipelines=build_pipelines(catalog=catalog, weights=state_weights, book_stats=stats),
    fallback=GlobalPopularFallback(catalog),
    catalog=catalog,
    db=Database(resolve_db_path()),
    neighbors=catalog,
    book_stats=stats,
    weights=state_weights,
    state=store,
)
# 반드시 마지막 — 앞에 두면 /health·/api/* 가 StaticFiles 에 가려진다
app.mount("/", StaticFiles(directory=ROOT / "demo", html=True), name="demo")
