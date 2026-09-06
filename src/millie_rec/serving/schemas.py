"""HTTP 계약(pydantic) — 백엔드 서빙/01 §0~§10 의 요청·응답 JSON 코드 정본. Must 엔드포인트.

열거값은 contracts 상수로만 검증한다(문자열 중복 금지). DTO ↔ JSON 변환도 이 파일만 담당.
Should 엔드포인트(dashboard·showcase)는 schemas_should.py.
Day 1 필드 집합 freeze, Day 3 응답 형태 freeze.
"""

from collections.abc import Sequence
from dataclasses import asdict
from typing import Annotated, Any

from pydantic import AfterValidator, BaseModel, ConfigDict, Field

from millie_rec.contracts import (
    BADGE_TYPES,
    EVENT_TYPES,
    ROW_ANCHOR_PREFIX,
    ROW_IDS,
    ROW_PURPOSES,
    VARIANTS,
    RecommendResponse,
)

API_VERSION = "v2"


def _member(allowed: Sequence[str], name: str):  # noqa: ANN202
    def check(v: str) -> str:
        if v not in allowed:
            raise ValueError(f"{name} must be one of {list(allowed)}, got {v!r}")
        return v

    return check


def _row_id(v: str) -> str:
    if v in ROW_IDS or v.startswith(ROW_ANCHOR_PREFIX):
        return v
    raise ValueError(f"row_id must be in ROW_IDS or start with {ROW_ANCHOR_PREFIX!r}, got {v!r}")


Variant = Annotated[str, AfterValidator(_member(VARIANTS, "model"))]
EventType = Annotated[str, AfterValidator(_member(EVENT_TYPES, "event_type"))]
BadgeType = Annotated[str, AfterValidator(_member(BADGE_TYPES, "badge.type"))]
Purpose = Annotated[str, AfterValidator(_member(ROW_PURPOSES, "purpose"))]
RowId = Annotated[str, AfterValidator(_row_id)]
Cell = Annotated[str, AfterValidator(_member(("A", "B"), "cell"))]
FallbackLevel = Annotated[int, Field(ge=0, le=3)]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


# ── §1 /health ──────────────────────────────────────────────────────────────
class HealthOut(_Strict):
    status: str
    api_version: str = API_VERSION
    model_version: str | None = None  # 스켈레톤(Day 2) 은 None
    artifacts_loaded_at: str | None = None
    db_ok: bool
    db_row_count: dict[str, int] = {}
    nearline_last_run: str | None = None
    uptime_s: float


# ── §2 /api/meta/onboarding ─────────────────────────────────────────────────
class Criterion(_Strict):
    id: BadgeType  # S3 선택 기준 id = 배지 타입 (author publisher bestseller buzz review)
    label: str


class CategoryMeta(_Strict):
    name: str
    supported: bool
    subcategories: list[str] = []


class OnboardingMeta(_Strict):
    survey_variant: str
    reading_times: list[str]
    criteria: list[Criterion]
    categories: list[CategoryMeta]


# ── §3 /api/candidates/onboarding ───────────────────────────────────────────
class CandidateItem(_Strict):
    book_id: int
    title: str
    authors: str | None = None
    image_url: str | None = None
    position: int
    book_format: str | None = None


class CandidateSet(_Strict):
    candidate_set_id: str
    survey_variant: str
    created_at: str
    items: list[CandidateItem]


# ── §4 /api/preferences ─────────────────────────────────────────────────────
class PreferencesRequest(_Strict):
    user_key: str
    consent: bool = True
    reading_time: str | None = None
    categories: list[str] = Field(default_factory=list, max_length=3)
    criterion: BadgeType | None = None
    subcategories: list[str] = Field(default_factory=list, max_length=9)
    seeds: list[int] = Field(default_factory=list, max_length=30)
    candidate_set_id: str | None = None
    restart: bool = False


class PersonaOut(_Strict):
    name: str
    work: str
    quote: str
    description: str


class PreferencesResponse(_Strict):
    user_key: str
    preference_snapshot_id: str
    created_at: str
    cell: Cell
    snapshots_count: int
    persona: PersonaOut | None = None


# ── §5 /api/recommend ───────────────────────────────────────────────────────
class BadgeOut(_Strict):
    type: BadgeType
    text: str


class ItemOut(_Strict):
    """contracts.ScoredItem 직렬화. 필드 집합 1:1."""

    book_id: int
    score: float
    source: str | None = None
    reason: str | None = None
    title: str | None = None
    authors: str | None = None
    image_url: str | None = None
    position: int | None = None
    source_channels: list[str] = []
    badge: BadgeOut | None = None
    book_format: str | None = None
    difficulty: float | None = None
    subcategories: list[str] = []  # ScoredItem.subcategories — Day 3 freeze 후 optional 추가


class RowOut(_Strict):
    row_id: RowId
    title: str
    purpose: Purpose
    items: list[ItemOut] = []
    subtitle: str | None = None
    channel_mix: dict[str, int] = {}


class RecommendOut(_Strict):
    recommendation_id: str | None = None
    model_version: str
    preference_snapshot_id: str | None = None
    user_key: str | None = None
    cell: Cell | None = None
    forced: bool = False
    fallback_level: FallbackLevel
    context: str | None = None
    latency_ms: float  # 총합 float. 단계별은 latency_breakdown (PDF 숫자 아님)
    latency_breakdown: dict[str, float] = {}
    user_state_weights: dict[str, float] = {}
    dedup_removed: int = 0
    nearline_lag_s: float | None = None
    items: list[ItemOut] = []
    rows: list[RowOut] = []

    @classmethod
    def from_contract(cls, r: RecommendResponse, *, forced: bool = False) -> "RecommendOut":
        d: dict[str, Any] = asdict(r)
        d["items"] = [asdict(i) for i in r.items]
        d["rows"] = [asdict(row) for row in r.rows]
        d["forced"] = forced
        return cls.model_validate(d)


# ── §6 /api/events ──────────────────────────────────────────────────────────
class EventIn(_Strict):
    event_id: str
    user_key: str
    book_id: int | None = None
    event_type: EventType
    ts: str
    surface: str | None = None
    row_id: RowId | None = None
    position: int | None = None
    selected: bool | None = None
    recommendation_id: str | None = None
    model_version: str | None = None
    preference_snapshot_id: str | None = None
    candidate_set_id: str | None = None
    payload: dict[str, str] = {}


class EventsBatchIn(_Strict):
    events: list[EventIn] = Field(min_length=1, max_length=50)


class FlaggedEvent(_Strict):
    event_id: str
    quality_flag: str


class EventsAccepted(_Strict):
    accepted: int
    duplicates: int = 0
    flagged: list[FlaggedEvent] = []


# ── §7 /api/ratings ─────────────────────────────────────────────────────────
class RatingIn(_Strict):
    rating_id: str
    user_key: str
    book_id: int
    stars: Annotated[int, Field(ge=1, le=5)]
    ts: str
    recommendation_id: str | None = None


class RatingOut(_Strict):
    ok: bool = True
    rating_id: str


# ── §8~§10 /api/users/{user_key}/* ──────────────────────────────────────────
class LibraryBook(_Strict):
    book_id: int
    title: str | None = None
    authors: str | None = None
    image_url: str | None = None


class SnapshotSummary(_Strict):
    snapshot_id: str
    created_at: str
    categories: list[str] = []
    criterion: str | None = None
    active: bool = False


class UserStateOut(_Strict):
    user_key: str
    consent: bool
    cell: Cell
    is_new: bool
    library: dict[str, list[LibraryBook]]  # added | reading | completed
    snapshots: list[SnapshotSummary] = []
    user_state_weights: dict[str, float] = {}
    nearline_lag_s: float | None = None


class UserDataOut(_Strict):
    user: dict[str, Any]
    snapshots: list[dict[str, Any]] = []
    events: list[dict[str, Any]] = []
    ratings: list[dict[str, Any]] = []
    recommendations: list[dict[str, Any]] = []
    candidate_sets: list[
        dict[str, Any]
    ] = []  # Codex T3(2026-09-06) — optional 추가, freeze 예외(PROGRESS)
    exported_at: str
    note: str = "가명 user_key 외 개인정보 없음"


class PersonalizationDeleted(_Strict):
    user_key: str
    consent: bool = False
    deleted: dict[str, int]
