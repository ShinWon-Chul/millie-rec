"""공용 계약: 상수 · DTO · Protocol 만. 로직·I/O 없음.

Day 1 종료 시 freeze. 변경은 Advisor 가 PROGRESS.md 결정 로그에 기록한 뒤에만.
필드 추가는 기본값 있는 optional 로만. 삭제·이름 변경 금지.
슬라이스는 이 모듈만 import 한다. 실제 객체 연결은 app/ 이 한다.
"""

from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    import numpy as np
    import pandas as pd

# ── 상수 ────────────────────────────────────────────────────────────────────
SEED = 42

ROOT = Path(__file__).resolve().parents[2]
DIR_RAW = ROOT / "data" / "raw"
DIR_PROCESSED = ROOT / "data" / "processed"
DIR_ARTIFACTS = ROOT / "artifacts"
DIR_RESULTS = ROOT / "results"
DIR_FIGURES = ROOT / "report" / "figures"
FILE_ID_MAP = (
    ROOT / "data" / "id_map.csv"
)  # 밀리 hex id ↔ 정수 book_id (append-only, 커밋). data/processed 는 gitignore

# interactions.parquet 컬럼
COL_USER = "user_id"
COL_ITEM = "book_id"
COL_TS = "ts"
COL_EVENT = "event"
COL_RATING = "rating"

# 이벤트 유형 (최종본 §8). 데이터셋 필드 → 이벤트 매핑은 data/labels.py 가 담당
EVENT_TYPES = (
    "impression",
    "detail_click",
    "library_add",
    "reader_open",
    "qualified_read",
    "completion",
    # v2 추가 (화면 v2 §5 · main §8 취향 설정 전용 이벤트 · 구체화 B 별점)
    "rating",
    "preference_started",
    "preference_step",
    "preference_book_selected",
    "preference_book_deselected",
    "preference_completed",
    "preference_restarted",
)

# 평가 K (PDF 비교표와 동일)
K_RECALL = 20
K_RANK = 10
N_ONBOARD_SEEDS = 5

# variant 이름의 유일한 정본: 평가표 행 · /recommend?model= · 인스펙터 라디오 · demo mock 파일명
VARIANTS = ("pop", "cf", "hybrid", "hybrid_div")
MODEL_VERSION_SUFFIX = "_v1"  # model_version = f"{variant}{MODEL_VERSION_SUFFIX}"
MODEL_VERSION_FALLBACK = "fallback_v1"  # level 3 응답. VARIANTS 이름을 빌리지 않는다(숫자 불혼합)

# Page Composition 행 (백엔드 문서 §3). purpose: resume | discover | fallback | explore
ROW_IDS = (
    "after_completion",
    "continue_reading",
    "persona_shelf",
    "similar_readers",
    "trending",
    "fresh_picks",
    "light_start",  # v2: 라이트 리더 활성화 (main §4, 구체화 E)
)
# ROW_IDS 는 허용 집합이다. 렌더 순서의 정본은 serving/compose.py 의 리스트.
ROW_PURPOSES = ("resume", "discover", "fallback", "explore")
ROW_ANCHOR_PREFIX = "anchor_"  # 앵커 row_id = f"anchor_{seed_book_id}" (구체화 C)

# 배지 타입 (화면 01 §4-4 + 적재 계획 §3 publisher). Badge.type 허용 집합
BADGE_TYPES = ("bestseller", "review", "author", "publisher", "buzz", "light")
# 난이도·통계 출처 (적재 계획 §4).
# millie_index = 밀리 완독지수 실측 · category_prior = 결측 대체(difficulty=None)
STATS_SOURCES = ("millie_index", "category_prior", "behavior", "prior")

# fallback cascade 단계 (아키텍처 문서 §3-11). 총 예산은 과제 설계용 SLO
BUDGET_MS = 200
FALLBACK_PERSONALIZED, FALLBACK_CACHE, FALLBACK_SEGMENT_POP, FALLBACK_GLOBAL_POP = 0, 1, 2, 3

# 데모 상수 (아키텍처 문서 §3-5 · §3-6 · 화면 v2 D4)
QUALIFIED_READ_MINUTES = 15  # 데모 상수. production 은 로그 분포로 보정 (main §4)
MIN_EVENTS_FOR_BOOK_STATS = 50  # 미달 시 artifacts 의 difficulty prior 유지 (main §5-6)
CACHE_TTL_S = 600  # fallback level 1 응답 캐시
NEARLINE_INTERVAL_S = 30

# 런타임 저장 경로. 환경변수 해석은 serving/db.py 가 한다 (contracts 는 I/O 없음)
DIR_DATA_LOCAL = ROOT / "data" / "local"
ENV_DATA_DIR = "DATA_DIR"  # 환경변수 '이름' 상수
DB_FILENAME = "millie.db"


# ── DTO ─────────────────────────────────────────────────────────────────────
@dataclass(frozen=True, slots=True)
class Event:
    """이벤트 스키마 (PDF 표용). 공개 데이터에 없는 필드는 None."""

    user_key: str
    book_id: int
    event_type: str
    ts: str
    surface: str | None = None
    row_id: str | None = None
    position: int | None = None
    recommendation_id: str | None = None
    model_version: str | None = None
    preference_snapshot_id: str | None = None
    # v2 추가
    candidate_set_id: str | None = None  # 취향 설문 exposure bias 로깅 (main §3)
    payload: dict[str, str] = field(default_factory=dict)
    quality_flag: str | None = None  # ts 검증·eligibility 실패 표시 (main §7)


@dataclass(frozen=True, slots=True)
class UserState:
    """추천 입력. train 구간 기록과 explicit seeds 만 — test 라벨은 절대 넣지 않는다."""

    user_id: int | None
    explicit_seeds: tuple[int, ...] = ()  # 온보딩 5권 (strong positive seed)
    history: tuple[int, ...] = ()  # long-term: train 구간 소비
    session: tuple[int, ...] = ()  # 최근 세션 (MVP 에서는 비어 있을 수 있음)
    context: dict[str, str] = field(default_factory=dict)  # 독서 시간대 등

    @property
    def seen(self) -> frozenset[int]:
        """추천에서 제외할 아이템."""
        return frozenset(self.explicit_seeds) | frozenset(self.history) | frozenset(self.session)


@dataclass(frozen=True, slots=True)
class Badge:
    """S3 선택 기준 → 노출 근거 개인화 (main §3, 화면 01 §4-4)."""

    type: str  # BADGE_TYPES: bestseller | review | author | publisher | buzz | light
    text: str


@dataclass(frozen=True, slots=True)
class Persona:
    """S6 설명 레이어. 모델 입력 아님 (main §3, 화면 01 §4-5)."""

    name: str
    work: str
    quote: str
    description: str


@dataclass(frozen=True, slots=True)
class Rating:
    """완독 직후 1탭 별점 = satisfaction label (main §7, 구체화 B). 데모 축소판."""

    rating_id: str
    user_key: str
    book_id: int
    stars: int
    ts: str
    recommendation_id: str | None = None


@dataclass(frozen=True, slots=True)
class BookStats:
    """난이도 4층 피처의 아이템 측 (main §5-6, 적재 계획 §4).

    데모 카탈로그(밀리)는 완독지수 실측 → source="millie_index", difficulty = σ(−resid_z).
    결측(≈20%) → source="category_prior", difficulty=None (가드 모집단 제외·UI 미표시).
    24h 집계는 difficulty·n_events 만 갱신하고 completion_rate(밀리 예측값)는 덮지 않는다.
    """

    book_id: int
    difficulty: float | None = None  # 0~1 합성 D_book. 3분위로 ●○○/●●○/●●●. None = 결측
    completion_rate: float | None = None  # 밀리 P_완독(0~1) 또는 데모 집계
    early_dropoff_rate: float | None = None
    rating_mean: float | None = None
    rating_var: float | None = None
    n_events: int = 0  # MIN_EVENTS_FOR_BOOK_STATS 미달이면 prior 사용
    source: str = "prior"  # STATS_SOURCES
    # 원시 2 + 분야 평균 2 (밀리 완독지수). pages 는 공개 페이지에 없어 계약에 두지 않는다
    completion_prob: float | None = None  # %
    category_avg_prob: float | None = None
    expected_min: float | None = None  # 완독 예상 시간(분) = 길이 대리
    category_avg_min: float | None = None
    # 파생 2. speed_z 폐기(pages 없음) — resid_z 가 길이 조건화를 흡수. len_z 는 랭커 피처로만
    resid_z: float | None = None  # z_분야(P_완독 − E[P_완독 | 분야, expected_min 분위])
    len_z: float | None = None  # z_분야(expected_min)


@dataclass(frozen=True, slots=True)
class PreferenceSnapshot:
    """온보딩/재설정 1회 결과. 재설정은 새 스냅샷을 추가만 한다 (Refresh ≠ Reset)."""

    snapshot_id: str
    user_key: str
    created_at: str
    reading_time: str | None = None
    categories: tuple[str, ...] = ()
    criterion: str | None = None  # 베스트셀러 / 리뷰 / 작가 / 출판사 / 화제작 → 배지 타입
    subcategories: tuple[str, ...] = ()
    seeds: tuple[int, ...] = ()
    consent: bool = True  # 정본은 users.consent. 응답 편의용
    persona: Persona | None = None
    # 2026-09-07 다중 선택. 단수 reading_time·criterion 은 "처음 고른 값"으로 남는다
    # (freeze — 삭제·개명 금지. PROGRESS 2026-09-07 결정 · 개발일지 항목 D91 참조)
    reading_times: tuple[str, ...] = ()
    criteria: tuple[str, ...] = ()  # 배지·페르소나 대표는 criteria[0] = criterion
    authors: tuple[str, ...] = ()  # 취향 설정에서 직접 고른 작가 표시 이름


@dataclass(frozen=True, slots=True)
class Candidate:
    book_id: int
    source: str  # "popularity" | "itemknn" | "content" | "explicit" (데모 카탈로그 이웃 = content)
    score: float


@dataclass(frozen=True, slots=True)
class ScoredItem:
    book_id: int
    score: float
    source: str | None = None
    reason: str | None = None  # 앵커 설명: "『X』을 좋아하셨다면"
    # v2 추가: 카드 표시 필드 (아키텍처 문서 §3-2 응답 · demo/mock 과 1:1)
    title: str | None = None
    authors: str | None = None
    image_url: str | None = None
    position: int | None = None
    source_channels: tuple[str, ...] = ()
    badge: Badge | None = None
    book_format: str | None = None  # 전자책 | 오디오북 | 챗북 (우선 오디오북 > 챗북 > 전자책)
    difficulty: float | None = None  # 난이도 점 표시용 (main §5-6)
    # 세부 분류(밀리 3depth). 화면 표시 + 취향 세부 분류 가산의 근거를 같은 필드로 보인다.
    # Day 3 freeze 후 추가 — 기본값 있는 optional(아키 규칙), PROGRESS 2026-09-06 결정 참조
    subcategories: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Recommendation:
    book_id: int
    score: float
    title: str | None = None
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class Row:
    """Page Composition 결과 한 행. purpose: resume | discover | fallback | explore."""

    row_id: str
    title: str
    purpose: str
    items: tuple[ScoredItem, ...] = ()
    subtitle: str | None = None
    channel_mix: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class RecommendResponse:
    items: tuple[Recommendation, ...]
    model_version: str
    fallback_level: int  # 0 개인화 · 1 캐시 · 2 세그먼트 인기 · 3 전역 인기
    latency_ms: float
    recommendation_id: str | None = None
    preference_snapshot_id: str | None = None
    rows: tuple[Row, ...] = ()
    latency_breakdown: dict[str, float] = field(default_factory=dict)
    user_state_weights: dict[str, float] = field(default_factory=dict)
    # v2 추가. latency_ms 는 float 총합(와이어 확정), 단계별은 latency_breakdown
    user_key: str | None = None
    cell: str | None = None  # "A" | "B" — sha256(user_key) 기반 stable 배정 (main §6-3)
    dedup_removed: int = 0
    context: str | None = None  # 독서 시간대 등


@dataclass(frozen=True, slots=True)
class EvalResult:
    variant: str
    recall: float
    ndcg: float
    ild: float
    n_users: int
    k_recall: int
    k_rank: int
    seed: int
    model_version: str
    created_at: str
    p95_ms: float | None = None


# ── Protocol ────────────────────────────────────────────────────────────────
class CandidateGenerator(Protocol):
    """retrieval 슬라이스. fit 은 train 구간만 받는다."""

    name: str

    def fit(self, train: "pd.DataFrame") -> "CandidateGenerator": ...
    def retrieve(self, user: UserState, k: int) -> list[Candidate]: ...


class Ranker(Protocol):
    """ranking 슬라이스. 후보를 점수순 정렬해 반환."""

    def rank(self, user: UserState, candidates: list[Candidate]) -> list[ScoredItem]: ...


class Reranker(Protocol):
    """reranking 슬라이스. 다양성·가드 적용 후 상위 k."""

    def rerank(self, user: UserState, items: list[ScoredItem], k: int) -> list[ScoredItem]: ...


class ItemVectors(Protocol):
    """아이템 콘텐츠 벡터 (MMR·ILD 용). retrieval 이 제공하고 app 이 주입."""

    def vectors(self, book_ids: Sequence[int]) -> "np.ndarray": ...


class Catalog(Protocol):
    """도서 메타·인기도 (serving compose·fallback 용). data 가 제공하고 app 이 주입."""

    def meta(self, book_ids: Sequence[int]) -> list[dict]: ...
    def popular(self, categories: Sequence[str] = (), n: int = 50) -> list[int]: ...
    def eligible(self, book_ids: Sequence[int]) -> list[int]: ...  # main §7 노출 자격 게이트


class Neighbors(Protocol):
    """아이템 이웃 조회. retrieval 이 제공, serving(compose·nearline) 이 사용, app 이 주입.

    앵커 row(구체화 C)·after_completion 사전 계산(구체화 B)의 유일한 경로 —
    serving 은 retrieval 을 import 할 수 없다.
    """

    def neighbors(self, book_id: int, n: int = 20) -> list[tuple[int, float]]: ...


class BookStatsSource(Protocol):
    """난이도·행동 통계 (main §5-6). serving·retrieval 제공, ranking·reranking·serving 사용."""

    def stats(self, book_ids: Sequence[int]) -> list[BookStats]: ...
    def user_level(self, user: UserState) -> float | None: ...


class Pipeline(Protocol):
    """조립된 추천기. evaluation · serving 은 이것만 안다."""

    name: str

    def recommend(self, user: UserState, k: int) -> list[ScoredItem]: ...
