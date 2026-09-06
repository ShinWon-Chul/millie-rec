"""HTTP 계약(pydantic) — 백엔드 서빙/01 §11 dashboard · §13 showcase (Should). 코드 정본."""

from typing import Any

from pydantic import BaseModel, ConfigDict

from millie_rec.serving.schemas import BadgeOut, Variant


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


# ── §11 /api/dashboard ──────────────────────────────────────────────────────
class KpiValue(_Strict):
    value: float
    n: int | None = None
    note: str | None = None


class AbRow(_Strict):
    cell: str
    segment: str
    n: int
    primary: float | None = None
    reader_open: float | None = None
    completion: float | None = None
    rating_mean: float | None = None
    first_completion: float | None = None
    p95_ms: float | None = None
    fallback_rate: float | None = None


class LatencyBlock(_Strict):
    p50: float
    p95: float
    p99: float
    by_stage: dict[str, list[float]] = {}  # [p50, p95]


class DashboardOut(_Strict):
    generated_at: str
    window: str = "all"
    kpi: dict[str, KpiValue]
    ab_table: list[AbRow] = []
    mde_note: str | None = None
    latency: LatencyBlock
    quality: dict[str, float] = {}
    events_recent: list[dict[str, Any]] = []
    impressions_log: list[dict[str, Any]] = []
    by_variant: dict[str, int] = {}
    by_hour: list[dict[str, int]] = []


# ── §13 /api/showcase ───────────────────────────────────────────────────────
class EvalRow(_Strict):
    variant: Variant
    recall_at_20: float
    ndcg_at_10: float
    ild_at_10: float
    p95_ms: float | None = None  # 로컬 bench 만 (results/latency.json)


class EvalTable(_Strict):
    split_mode: str  # holdout | temporal
    source: dict[str, str]
    rows: list[EvalRow]


class MetricMapping(_Strict):
    stage: str
    metric: str


class ShowcaseBook(_Strict):
    book_id: int
    title: str | None = None
    authors: str | None = None
    image_url: str | None = None
    reason: str | None = None
    badge: BadgeOut | None = None


class PersonalCase(_Strict):
    seeds: list[ShowcaseBook]
    recommendations: list[ShowcaseBook]


class Memorable(_Strict):
    claim: str
    how_to_verify: str
    route: str


class ShowcaseOut(_Strict):
    philosophy: str
    eval_table: EvalTable
    metric_mapping: list[MetricMapping]
    personal_case: PersonalCase | None = None
    memorable_5: list[Memorable] = []
    roadmap: list[str] = []
    data_notice: str
