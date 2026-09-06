"""취향 설정·이벤트 API(백엔드 01 §4·§6) — APIRouter 팩토리. 상태 갱신 없음(SERV-09)."""

import hashlib
import re
import uuid
from collections.abc import Callable
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException

from millie_rec.contracts import Catalog
from millie_rec.serving import events_gate, schemas  # 같은 슬라이스(≤150줄 유지)
from millie_rec.serving.db import Database
from millie_rec.serving.onboarding_api import META_PATH, _iso, _j, load_meta, new_id
from millie_rec.serving.persona import assign_persona

USER_KEY_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")  # privacy_api.py 와 중복 정의(C5)
USER_KEY_MSG = "user_key must match ^[A-Za-z0-9_-]{1,64}$"
SURFACE_ONBOARDING, EVENT_LIBRARY_ADD = "onboarding", "library_add"  # contracts.EVENT_TYPES 안
SQL_USER = "SELECT cell, consent FROM users WHERE user_key = ?"
SQL_USER_INS = "INSERT INTO users(user_key, created_at, consent, cell, is_new) VALUES(?,?,?,?,1)"
SQL_USER_CONSENT = "UPDATE users SET consent = ? WHERE user_key = ?"
SQL_SNAP_INS = (
    "INSERT INTO preference_snapshots(snapshot_id, user_key, created_at, reading_time, categories,"
    " criterion, subcategories, seeds, persona) VALUES(?,?,?,?,?,?,?,?,?)"
)
SQL_SNAP_COUNT = "SELECT COUNT(*) FROM preference_snapshots WHERE user_key = ?"
SQL_LIB_ADD = (  # D-08 seeds 자동 기록. payload 는 빈 JSON, quality_flag 는 NULL
    "INSERT OR IGNORE INTO events(event_id, user_key, book_id, event_type, ts, surface,"
    " preference_snapshot_id, candidate_set_id, payload) VALUES(?,?,?,?,?,?,?,?,'{}')"
)
SQL_EVENT_INS = (  # 확정 16: OR IGNORE + rowcount → duplicates. 이름 바인딩 = EventIn 필드명
    "INSERT OR IGNORE INTO events(event_id, user_key, book_id, event_type, ts, surface, row_id,"
    " position, selected, recommendation_id, model_version, preference_snapshot_id,"
    " candidate_set_id, payload, quality_flag) VALUES(:event_id, :user_key, :book_id, :event_type,"
    " :ts, :surface, :row_id, :position, :selected, :recommendation_id, :model_version,"
    " :preference_snapshot_id, :candidate_set_id, :payload, :quality_flag)"
)


def _422(param: str, msg: str) -> HTTPException:
    return HTTPException(422, detail=[{"loc": ["body", param], "msg": msg, "type": "value_error"}])


def assign_cell(user_key: str) -> str:
    """A/B 셀 — CPython hash() 금지(아키 §3-10). 최초 생성 시 users.cell 에 저장."""
    return "A" if int(hashlib.sha256(user_key.encode()).hexdigest()[:8], 16) % 2 == 0 else "B"


def build_router(
    *,
    db: Database,
    catalog: Catalog | None = None,
    wake: Callable[[], None] | None = None,
    invalidate: Callable[[str], object] | None = None,
    meta_path: Path = META_PATH,
    now: Callable[[], datetime] | None = None,
) -> APIRouter:
    """의존을 클로저로 받는다 — create_app 배선은 Plan 05-06(Advisor 확정 2)."""
    labels = {c["id"]: c["label"] for c in load_meta(meta_path)["criteria"]}
    clock = now or (lambda: datetime.now(UTC))
    router = APIRouter(prefix="/api")

    @router.post("/preferences", response_model=schemas.PreferencesResponse, status_code=201)
    def preferences(body: schemas.PreferencesRequest) -> schemas.PreferencesResponse:
        if not USER_KEY_RE.match(body.user_key):
            raise _422("user_key", USER_KEY_MSG)
        now_s, con = _iso(clock()), db.connect()
        row = con.execute(SQL_USER, (body.user_key,)).fetchone()
        cell = row[0] if row else assign_cell(body.user_key)
        persona = assign_persona(body.categories, labels.get(body.criterion))
        sid = new_id("snap_")
        seeds = list(body.seeds) if body.consent else []  # consent=false 면 seeds 미저장
        snap = (sid, body.user_key, now_s, body.reading_time, _j(body.categories), body.criterion)
        tail = (EVENT_LIBRARY_ADD, now_s, SURFACE_ONBOARDING, sid, body.candidate_set_id)
        rest = (_j(body.subcategories), _j(seeds), _j(asdict(persona)))
        with con:  # 확정 16: with con 으로 커밋
            if row is None:
                con.execute(SQL_USER_INS, (body.user_key, now_s, int(body.consent), cell))
            else:
                con.execute(SQL_USER_CONSENT, (int(body.consent), body.user_key))
            con.execute(SQL_SNAP_INS, (*snap, *rest))
            for b in seeds:  # D-08: seeds 마다 library_add(surface=onboarding) 자동 기록
                con.execute(SQL_LIB_ADD, (uuid.uuid4().hex, body.user_key, b, *tail))
        if seeds and wake:
            wake()
        if invalidate:
            invalidate(body.user_key)
        return schemas.PreferencesResponse(
            user_key=body.user_key,
            preference_snapshot_id=sid,
            created_at=now_s,
            cell=cell,
            snapshots_count=con.execute(SQL_SNAP_COUNT, (body.user_key,)).fetchone()[0],
            persona=schemas.PersonaOut(**asdict(persona)),
        )

    @router.post("/events", response_model=schemas.EventsAccepted, status_code=202)
    def events(body: schemas.EventIn | schemas.EventsBatchIn) -> schemas.EventsAccepted:
        evs = body.events if isinstance(body, schemas.EventsBatchIn) else [body]
        for e in evs:
            if not USER_KEY_RE.match(e.user_key):
                raise _422("user_key", USER_KEY_MSG)
        try:  # INSERT 전에 전부 파싱 — 하나라도 실패하면 배치 전체 422(revision C3)
            parsed = [events_gate.parse_ts(e.ts) for e in evs]
        except ValueError as exc:
            raise _422("ts", "ts must be ISO-8601") from exc
        now_dt, accepted, dup, flagged = clock(), 0, 0, []
        con = db.connect()
        off = events_gate.consent_off_keys(con, [e.user_key for e in evs])  # T2
        with con:
            for e, t in zip(evs, parsed, strict=True):
                if e.user_key in off:  # 동의 철회 유저: 저장·웨이크 없이 flagged 로만 보고(T2)
                    flagged.append(
                        schemas.FlaggedEvent(
                            event_id=e.event_id, quality_flag=events_gate.FLAG_CONSENT_OFF
                        )
                    )
                    continue
                flag = events_gate.quality_flag(con, e, now_dt, catalog, parsed_ts=t)
                sel = None if e.selected is None else int(e.selected)
                row = e.model_dump() | {"ts": _iso(t), "selected": sel, "quality_flag": flag}
                row["payload"] = _j(e.payload)
                if con.execute(SQL_EVENT_INS, row).rowcount == 0:
                    dup += 1
                    continue
                accepted += 1
                if flag:  # 플래그가 붙어도 저장한다(백엔드 01 §6)
                    flagged.append(schemas.FlaggedEvent(event_id=e.event_id, quality_flag=flag))
        if accepted and wake:  # 확정 13: wake 는 05-06 이 call_soon_threadsafe 클로저로 준다
            wake()
        return schemas.EventsAccepted(accepted=accepted, duplicates=dup, flagged=flagged)

    return router
