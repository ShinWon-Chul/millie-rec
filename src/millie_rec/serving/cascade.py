"""cascade 오케스트레이션 0→1→2→3 · 셀 배정 variant · breakdown 병합(아키 01 §3-11, D-09~D-12).

해석은 resolve.py, 비개인화 단계·셀 배정 variant 는 levels.py, 로그는 rec_log.py,
완독 행·옛 캐시 판정은 after_completion.py(분할 Advisor 승인 2026-09-06).
"""

import logging
import time
from collections.abc import Callable
from dataclasses import replace
from time import perf_counter

from fastapi import HTTPException

from millie_rec.contracts import (
    FALLBACK_CACHE,
    FALLBACK_GLOBAL_POP,
    FALLBACK_PERSONALIZED,
    FALLBACK_SEGMENT_POP,
    MODEL_VERSION_SUFFIX,
    RecommendResponse,
    UserState,
)
from millie_rec.serving import rec_log
from millie_rec.serving.after_completion import fresh_cache, stored
from millie_rec.serving.compose import build_response, compose_rows
from millie_rec.serving.fallback import over_budget
from millie_rec.serving.levels import (
    CELL_VARIANT,
    PIPE_K_MIN,
    cold_start,
    nonpersonal,
    variant_for,
)
from millie_rec.serving.privacy_api import USER_KEY_RE
from millie_rec.serving.resolve import (
    NOT_FOUND_SNAPSHOT,
    Resolved,
    resolve_user,
    user_state_of,
)
from millie_rec.serving.state import reset_boost

log = logging.getLogger(__name__)

__all__ = ["CELL_VARIANT", "NOT_FOUND_SNAPSHOT", "PIPE_K_MIN", "Cascade", "Resolved",  # 재-export
           "cold_start", "nonpersonal", "resolve_user", "variant_for"]  # fmt: skip
KEY_ERR = [{"loc": ["query", "user_key"], "msg": USER_KEY_RE.pattern, "type": "value_error"}]


class Cascade:
    """level 0 → 1(캐시) → 2(세그먼트 인기) → 3(전역 인기). 항상 200(T-05-06-01·02)."""

    def __init__(self, pipelines, fallback, *, catalog=None, db, neighbors=None, store=None,
                 cache, weights=None, default=None, all_categories=(), criteria_labels=None,
                 segpop=None, now: Callable[[], float] | None = None) -> None:  # fmt: skip
        self.pipelines, self.fallback, self.catalog, self.db = pipelines, fallback, catalog, db
        self.neighbors, self.store, self.cache, self.weights = neighbors, store, cache, weights
        self.default, self.all_categories, self.segpop = default, tuple(all_categories), segpop
        self.criteria_labels = criteria_labels or {}  # criterion id → 라벨(응답 문구용)
        self._now = now or time.time

    def respond(
        self, *, user_key: str | None, snapshot_id: str | None, model: str | None, k: int,
        context: str | None, seeds: tuple[int, ...],
    ) -> tuple[RecommendResponse, bool]:  # fmt: skip
        """(응답, forced). 예외·예산 초과는 안에서 흡수 — 호출자는 항상 200 을 낸다."""
        t0, bd, forced = perf_counter(), {}, model is not None
        if user_key and USER_KEY_RE.match(user_key) is None:
            raise HTTPException(422, detail=KEY_ERR)
        if not user_key:  # 익명 · seeds cold-start(CLI·bench)
            name = variant_for(None, model, self.pipelines, self.default)
            resp = cold_start(self, seeds, name, k, t0, context, bd)
            return self._logged(resp, None, None, None, forced)
        tf = perf_counter()  # D-09: feature 구간은 resolve_user 부터 잰다
        r = resolve_user(self.db, user_key, snapshot_id)  # seeds 와 함께 오면 user_key 우선
        personal = bool(r.found and r.consent)
        sid = r.snapshot_id if personal else None
        if sid is not None:
            resp = self._personal(r, model, k, t0, context, bd, tf)
        else:  # 미등록 · 스냅샷 없음 · consent=false → 항상 3, 가중치 0(백엔드 01 §5)
            user = UserState(None, context={"user_key": user_key})
            resp = nonpersonal(self, user, FALLBACK_GLOBAL_POP, (), k, t0, context, bd, None)
        resp = replace(resp, user_key=user_key, cell=r.cell, preference_snapshot_id=sid)
        keys = (user_key, sid, r.cell) if personal else (None, None, None)  # 철회·미등록은 익명
        return self._logged(resp, *keys, forced)

    def _logged(self, resp, user_key, snapshot_id, cell, forced):
        """D-12: 모든 응답(level 0~3·seeds·익명)을 응답 직전 1행 기록한다."""
        rec_log.log_recommendation(self.db, resp, user_key=user_key, snapshot_id=snapshot_id,
                                   cell=cell, forced=forced, now=self._now)  # fmt: skip
        return resp, forced

    def _personal(self, r, model, k, t0, context, bd, tf):
        """level 0 — 상태 로드 → 파이프라인 → 예산 판정 → 5행 조립 + 캐시 저장(D-09·D-10)."""
        store, user, kw = self.store, user_state_of(self.store, r, context), {}
        if reset_boost(r.snapshots_count, r.latest_created_at, now=self._now()):
            kw["reset_boost"] = True  # D-08 재설정 부스트
        if store is not None and store.session_active(r.user_key):
            kw["session_active"] = True  # D-06 세션 창
        if kw:  # 리트리버도 같은 부스트를 본다 — context 값은 str(계약), 표시 가중치와 한 신호
            user = replace(user, context={**user.context, **dict.fromkeys(kw, "1")})
        bd["feature"] = (perf_counter() - tf) * 1000
        name = variant_for(r.cell, model, self.pipelines, self.default)
        if name is None:
            return nonpersonal(self, user, FALLBACK_GLOBAL_POP, r.categories, k, t0, context, bd,
                               r.criterion)  # fmt: skip
        pipe, version = self.pipelines[name], f"{name}{MODEL_VERSION_SUFFIX}"
        tp, shown = perf_counter(), None
        try:
            items = pipe.recommend(user, max(k, PIPE_K_MIN))
            shown = self.weights(user, **kw) if self.weights is not None else None
        except Exception:
            log.exception("pipeline %s failed; cascading", name)
            items = None
        bd["pipeline"] = (perf_counter() - tp) * 1000
        if items is None or over_budget(bd["feature"] + bd["pipeline"]):  # C2 자체 계측으로 판정
            return self._degrade(r, user, k, t0, context, bd, name)
        bd = rec_log.merge_breakdown(bd, getattr(pipe, "last_breakdown", None))  # D-09 표시용
        tc, rows, dd = perf_counter(), None, 0
        if self.catalog is not None:
            conts = store.continue_reading(r.user_key) if store is not None else ()
            rows, dd = compose_rows(items=items, catalog=self.catalog, neighbors=self.neighbors,
                                    level=FALLBACK_PERSONALIZED, seeds=r.seeds,
                                    categories=r.categories, criterion=r.criterion,
                                    criteria=r.criteria, picked_authors=r.authors,
                                    persona_name=r.persona_name, continue_ids=conts,
                                    read_ids=user.history, all_categories=self.all_categories,
                                    after_completion=stored(store, r.user_key))  # fmt: skip
            self.cache.put(r.user_key, r.snapshot_id, name, rows, version)  # D-10 매 성공 시
        bd["compose"] = (perf_counter() - tc) * 1000
        return build_response(items, model_version=version, level=FALLBACK_PERSONALIZED, k=k,
                              t0=t0, context=context, rows=rows, dedup_removed=dd,
                              latency_breakdown=bd, user_state_weights=shown)  # fmt: skip

    def _degrade(self, r, user, k, t0, context, bd, name):
        """D-10: 캐시 있으면 level 1(캐시된 model_version), 없으면 2 → 비면 3."""
        hit = fresh_cache(self.cache.get(r.user_key, r.snapshot_id, name), self.store,
                          self.cache, r.user_key)  # 완독 뒤 옛 캐시 폐기(D-10)  # fmt: skip
        if hit is not None:
            rows, version = hit
            return build_response((), model_version=version, level=FALLBACK_CACHE, k=k, t0=t0,
                                  context=context, rows=rows, latency_breakdown=bd)  # fmt: skip
        seg = nonpersonal(self, user, FALLBACK_SEGMENT_POP, r.categories, k, t0, context, bd,
                          r.criterion)  # fmt: skip
        if seg.rows and seg.rows[0].items:
            return seg
        return nonpersonal(self, user, FALLBACK_GLOBAL_POP, (), k, t0, context, bd, r.criterion)
