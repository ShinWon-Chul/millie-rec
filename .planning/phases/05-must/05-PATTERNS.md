# Phase 5: 서빙 Must 완성 - Pattern Map

**Mapped:** 2026-09-06
**Files analyzed:** 소스 15개(신규 8 + 수정 6 + Advisor `app/server.py` 1) + 테스트 7~8개(신규 7 + 기존 확장)
**Analogs found:** 19 / 23 — 라우터·SQLite·응답 조립·메타 조인·테스트 골격은 Phase 1~4 코드가 그대로 아날로그다(exact 10 · role-match 9). **`asyncio` 루프 · `hashlib` 셀 배정 · 표준 라이브러리 HTTP 클라이언트(bench) · 정규화 제목 dedup 의 서빙 측 아날로그는 0건**(grep `asyncio|hashlib` → src 0건) → "No Analog" 절에 규칙·CONTEXT 기반 제안 스니펫을 두었다.

## 기준선 (실측 2026-09-06, 이 페이즈 시작 직전)

| 항목 | 값 |
|---|---|
| `uv run python --version` | Python 3.11.6 |
| `uv run pytest --no-header` | **327 passed**, 2 warnings, 3.49s (CONTEXT D-18 기준선과 일치) |
| 줄 수(150줄 규칙) | `serving/api.py` **150(한도 도달)** · `compose.py` 60 · `db.py` 60 · `fallback.py` 45 · `__init__.py` 16 · `schemas.py` 277(예외) · `schemas_should.py` 101 · `app/server.py` 26 · `app/pipeline.py` 149 · `app/pipeline_kr.py` 123 · `app/cli.py` 135 · `data/catalog_kr.py` 118 |
| `create_app` 시그니처(verbatim, `serving/api.py` L92-102) | `def create_app(pipelines: dict[str, Pipeline], fallback: Pipeline, *, catalog: Catalog \| None = None, db: Database, neighbors: Neighbors \| None = None, book_stats: BookStatsSource \| None = None, state: object \| None = None, weights: Callable[[UserState], dict[str, float]] \| None = None) -> FastAPI` |
| `serving/__init__.__all__` | `API_VERSION Database EventIn GlobalPopularFallback RecommendOut create_app resolve_db_path` |
| 의존성 | 런타임 numpy·scipy·pandas·pyarrow·scikit-learn·fastapi·uvicorn·matplotlib / dev pytest·ruff·**httpx(dev 전용 → bench.py 는 `urllib.request`)** — 추가 없음 |
| ruff | `line-length = 100`, `select = ["E","F","I","UP","B"]` → **B008**: FastAPI 파라미터 기본값은 `Annotated[..., Query()]` 형태만(`api.py` L130-135 관례) |
| `artifacts/serving/` | `books_kr.json` **9,447권 · 카테고리 29종**(아래 §카탈로그 실측) · `eval_table.json` 4행(값이 **문자열** `"0.063"`, 키 `recall@20`) · `item_edges_kr.json` · `content_vectors_kr.npz` · `popularity_kr.json` — 🧊 읽기만 |
| `results/` | `latest.csv` `latest_states.csv` `eval_*.json` `millie_coverage.csv` `millie_edges_gate.json` — **`latency.json` 없음**(bench 가 만든다) |
| 테스트 fixture | **`tests/fixtures/millie/serving_sample/` 디렉터리는 없다.** 정본은 `tests/conftest.py::millie_serving_sample`(session scope, `tmp_path_factory` 에 20권 `books_kr.json`·`item_edges_kr.json`·`popularity_kr.json` + npz 생성, L92-130; 자격 없는 3권 = 18·19·20, 카테고리 4종 `소설 에세이 경제경영 인문` 순환, `publisher="표본 출판사"`, `millie_label=None`, `review_count=i*3`, `pop_rank=i`). CONTEXT D-17 의 경로 표기는 이 fixture 를 가리킨다 |
| 서버 내 `asyncio`·`hashlib` | src 0건 — Nearline 루프·셀 배정은 이 페이즈가 최초 |
| SQLite 쓰기 | `db.py` 에 `commit` 0건 — `apply_schema` 의 `executescript` 만(암묵 커밋). DML 헬퍼는 신규 |

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `src/millie_rec/serving/state.py` (NEW) | store(메모리 dict aggregate + DB 읽기, `BookStatsSource` 어댑터) | event-driven(Nearline 이 쓰고 요청이 읽음) | `serving/db.py::Database` L24-39(자기 상태 보유 클래스·thread-local) + `data/catalog_kr.py::CatalogKR` L43-63·L117-118(`__init__` 1회 인덱스, `user_level` Protocol 자리) | role-match |
| `src/millie_rec/serving/nearline.py` (NEW) | background loop(`async` + `asyncio.to_thread`) | event-driven / batch(24h 리플레이) | `serving/api.py::lifespan` L110-114(태스크 시작 자리)만 — 루프 본체 **no analog** | partial |
| `src/millie_rec/serving/persona.py` (NEW) | utility(순수 매핑 + 문장 조립) | transform | `ranking/hybrid.py` L7-14(상단 매핑 dict 상수 `SLOT_OF_SOURCE`) + `app/demo_cli.py` L15-23(고정 문장 상수) + `demo/mock/preferences_response.json`(텍스트 형태) | role-match |
| `src/millie_rec/serving/demo_api.py` (NEW) | controller(`APIRouter`, GET 2 + POST 2, Should `POST /api/ratings`) | CRUD(SQLite INSERT) + request-response | `serving/api.py` L118-148(동기 `def`·`response_model`·`Annotated Query`·`_422`) + `serving/schemas.py` L104-129·L191-220(요청 모델) | role-match(POST body·APIRouter 는 repo 최초) |
| `src/millie_rec/serving/privacy_api.py` (NEW) | controller(`APIRouter`, GET 2 + DELETE 1) | CRUD(SELECT·DELETE) | `serving/api.py` L118-126(`/health` 가 `db.row_counts()` 를 그대로 돌려주는 형태) + `db.py::row_counts` L48-54(테이블별 COUNT dict = `PersonalizationDeleted.deleted` 형태) | role-match |
| `src/millie_rec/serving/dashboard_api.py` (NEW) | controller(`APIRouter`, `GET /api/showcase` Must + `GET /api/dashboard` Should) | file-I/O(json 읽기) + SQLite 집계 | `data/catalog_kr.py::CatalogKR.load` L65-71(json 파일 1회 로드, 부재 분기) + `app/export.py::write_eval_table` L19-41(eval_table 페이로드 형태의 생산자) + `serving/schemas_should.py` L56-101 | role-match |
| `src/millie_rec/serving/bench.py` (NEW) | CLI(`python -m`) + HTTP 클라이언트 + results writer | request-response(클라이언트) → file-I/O(`results/latency.json`) | `app/cli.py::main` L113-135(argparse 1개·`if __name__`) + `evaluation/report.py::git_sha` L53-66·`write_results` L104-119(`created_at`·json 쓰기) + `scripts/collect_millie.py::_get` L66-69(`urllib.request`) | role-match |
| `src/millie_rec/serving/onboarding_meta.json` (NEW) | config(정적 텍스트) | — | `demo/config/onboarding.json`(S1·S3 옵션 텍스트 원천) + 백엔드 서빙 01 §2 JSON + `serving/db.py` L10 `SCHEMA_PATH = Path(__file__).parent / "schema.sql"`(패키지 옆 파일 로드) | exact(텍스트) |
| `src/millie_rec/serving/api.py` (MODIFY) | controller | request-response | 자기 자신 L47-89(`_fallback_response`·`_personalized_response`) · L107-116(lifespan) | exact |
| `src/millie_rec/serving/compose.py` (MODIFY — Must 5행·dedup·배지·메타) | transform | transform | 자기 자신 L34-60 + `serving/fallback.py::trending_row` L37-45(Row 조립) + `app/pipeline_kr.py::WithMeta.recommend` L82-98(meta 5필드 `replace`) + `app/demo_cli.py::_norm` L26-27(정규화 키) | exact |
| `src/millie_rec/serving/fallback.py` (MODIFY — level 1 캐시·level 2) | service(`Pipeline` 구현 + cascade) | request-response | 자기 자신 L13-34 | exact |
| `src/millie_rec/serving/db.py` (MODIFY — 쓰기 헬퍼·`close`) | infrastructure(SQLite) | CRUD | 자기 자신 L32-54 | exact |
| `src/millie_rec/serving/schema.sql` (MODIFY — `CREATE INDEX IF NOT EXISTS` 2개) | migration | — | 자기 자신 L1-22(`IF NOT EXISTS` 멱등 DDL) | exact |
| `src/millie_rec/serving/__init__.py` (MODIFY) | public surface | — | 자기 자신 L1-16(알파벳 `__all__`) · `data/__init__.py` L39-72 | exact |
| `src/millie_rec/app/server.py` (MODIFY, **Advisor**) | entrypoint | — | 자기 자신 L15-24 | exact |
| `tests/serving/test_state.py`·`test_nearline.py` (NEW) | test | — | `tests/serving/test_smoke.py::test_database_apply_schema_creates_must_tables` L125-129(`Database(tmp_path/…)` 직접) + `tests/reranking/test_guard.py::_FakeStats` L12-27(Protocol 가짜) | role-match |
| `tests/serving/test_compose.py` (NEW) | test | — | `tests/serving/test_schemas.py::_response` L20-52(Row·ScoredItem 손조립) + `tests/app/test_pipeline.py::_FakeCatalog` L81-103 | role-match |
| `tests/serving/test_fallback_cascade.py` (NEW) | test | — | `tests/serving/test_recommend_level0.py` L55-69·L142-148(`_Boom`·`_app` 조립·예외→200) + `test_smoke.py` L132-136(`monkeypatch`) | exact |
| `tests/serving/test_demo_api.py`·`test_privacy_api.py` (NEW) | test | — | `tests/serving/test_smoke.py` L67-78(`_app`·`client` fixture, `with TestClient`) + `test_api_weights.py::_app` L48-54(keyword 인자 주입) | exact |
| `tests/serving/test_dashboard_api.py` (NEW) | test | — | `tests/app/test_export.py` L20-55(`tmp_path` 에 `eval_table.json` 써 넣고 읽기) | exact |
| `tests/serving/test_bench.py` (NEW, 선택) | test | — | `tests/evaluation/test_report.py`(json 페이로드 키 단정) | role-match |

---

## Pattern Assignments

### 0. 모든 신규 serving `.py` 공통 — 모듈 머리·상수·로거·import

**Analog:** `src/millie_rec/serving/api.py` L1-30 · `serving/fallback.py` L1-10

```python
"""FastAPI create_app · lifespan · GET /health · GET /api/recommend (백엔드 서빙 01 §0·§1·§5)."""

import logging
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from dataclasses import replace
from time import perf_counter
from typing import Annotated

from fastapi import FastAPI, HTTPException, Query

from millie_rec.contracts import (
    FALLBACK_GLOBAL_POP,
    FALLBACK_PERSONALIZED,
    MODEL_VERSION_FALLBACK,
    MODEL_VERSION_SUFFIX,
    VARIANTS,
    BookStatsSource,
    Catalog,
    Neighbors,
    Pipeline,
    RecommendResponse,
    UserState,
)
from millie_rec.serving.compose import build_response, default_variant
from millie_rec.serving.db import Database
from millie_rec.serving.schemas import API_VERSION, HealthOut, RecommendOut

log = logging.getLogger(__name__)
K_DEFAULT, K_MAX = 40, 100  # 백엔드 01 §5 "k 기본 40" · §0 "k ≤ 100"
```

```python
# fallback.py L7-10 — 문자열 상수는 상단 대문자 + "contracts 의 어느 집합 안인지" 주석
TRENDING_ROW_ID = "trending"  # contracts.ROW_IDS 안
TRENDING_TITLE = "지금 많이 읽는 책"  # 백엔드 01 §5 응답 예시. Phase 5 compose.py 가 재사용
TRENDING_PURPOSE = "fallback"  # contracts.ROW_PURPOSES 안
SOURCE_POPULARITY = "popularity"  # contracts.Candidate.source 허용값
```

**규칙 요약:** docstring 1줄(문서 § 병기) → stdlib → fastapi → `millie_rec.contracts` → `millie_rec.serving.*` 순 import. **`millie_rec.data`·`ranking`·`reranking`·`app` import 금지**(`tests/test_architecture.py` L37-42 가 실패시킨다). `state_weights` 는 이미 `weights` 인자로 주입돼 있다 — `state.py` 가 부스트 인자를 넘기려면 `weights(user, reset_boost=…, session_active=…)` 호출은 **주입된 callable 을 그대로** 호출한다(`ranking.blend.state_weights` L18-20 시그니처: `(user, *, reset_boost=False, session_active=False)`).

---

### 1. `serving/state.py` (store, event-driven)

**Analog A — 자기 상태 보유 클래스 + 스레드 안전 자원:** `serving/db.py::Database` L24-39

```python
class Database:
    """threading.local 연결 보유. 핸들러는 스레드풀에서 돌므로 스레드마다 연결 1개."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._local = threading.local()
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def connect(self) -> sqlite3.Connection:
        con = getattr(self._local, "con", None)
        if con is None:
            con = sqlite3.connect(self.path)
            for pragma in PRAGMAS:
                con.execute(pragma)
            self._local.con = con
        return con
```
→ `state.py` 의 store 는 `self._users: dict[str, <per-user record>]` 하나 + `threading.Lock` 하나(Nearline 스레드가 쓰고 핸들러 스레드가 읽음). 상수는 상단: `SESSION_WINDOW_S = 1800`(D-06) · `REPLAY_WINDOW_S = 86400`(D-08) · `HISTORY_MAX = 200`(재량) · `RESET_BOOST_WINDOW_S = 86400`(D-08) · `HISTORY_EVENT_TYPES = ("reader_open", "qualified_read", "completion")`(D-05, 값은 `contracts.EVENT_TYPES` 안) · `SESSION_EVENT_TYPES = ("reader_open", "detail_click")`.

**Analog B — Protocol 어댑터가 `__init__` 에서 인덱스 1회, `user_level` 자리:** `data/catalog_kr.py` L43-63 · L117-118

```python
class CatalogKR:
    """contracts.Catalog + Neighbors + BookStatsSource. 인덱스·인기 순서는 __init__ 에서 1회."""

    def __init__(self, books: Sequence[dict], edges: dict[str, list[list]] | None = None) -> None:
        self._by_id: dict[int, dict] = { ... }
        ...
    def user_level(self, user: UserState) -> float | None:
        return None  # Phase 4 가드 몫 — 완독 이력 평균은 state.py 이후
```
→ D-07 서빙 측 `BookStatsSource` 어댑터: `stats()` 는 안쪽(`CatalogKR`)에 위임, `user_level(user)` 만 state 로 계산. **serving 은 `CatalogKR` 를 import 할 수 없으므로** 생성자는 `inner: BookStatsSource`(stats 위임) + `catalog: Catalog`(카테고리 prior 용 `meta`) 를 Protocol 로 받고 `app/server.py`(Advisor) 가 실제 객체를 넣는다. 파이프라인이 `book_stats` 로 이 어댑터를 쓰게 하려면 `app/pipeline_kr.py` L115 `kw = {..., "book_stats": catalog, ...}` 의 주입 대상을 바꿔야 한다 — Advisor 몫, 브리프에 "보고만" 지시.

**`UserState` 조립(계약 무변경):** `contracts.py` L122-135 — `UserState(user_id=None, explicit_seeds=snapshot.seeds, history=tuple(distinct 최근순), session=tuple(30분 창), context={...})`. `context: dict[str, str]` 이므로 D-07 재량안 (c) 를 채택하면 `context["n_completed"] = str(n)` 처럼 **문자열**로 넣어야 타입이 맞다(guard·hybrid 의 1줄 분기는 `int(user.context.get("n_completed", len(user.history)))` — Model 레인, Advisor 승인 필요).

**`n_completed` 대리값의 현재 위치(교체 지점 2곳):** `reranking/guard.py` L52 `if self.book_stats is None or len(user.history) >= self.min_completed or not items:` · `ranking/hybrid.py` L49 `n_completed = len(user.history)  # D-08 대리값 — Phase 5 state.py 가 완독 이벤트 수로 교체`. 재량안 (a)(완독 책을 history 앞에)를 택하면 이 두 줄은 무변경.

**시간 주입(테스트 규칙 `python-tdd.md` "시간은 주입"):** 공개 함수는 `now: float | None = None` 또는 `now: datetime | None = None` 인자를 받고 기본은 `time.time()`/`datetime.now(UTC)`. 기존 타임스탬프 관례(`app/export.py` L35): `datetime.now(UTC).isoformat(timespec="seconds")` — 이벤트 `ts` 파싱은 `datetime.fromisoformat(ts.replace("Z", "+00:00"))`(테스트 `test_schemas.py` L67 은 `"2026-09-07T12:00:00Z"` 형태를 쓴다).

---

### 2. `serving/nearline.py` (background loop, event-driven) — 루프 본체 no analog

**Analog(태스크 시작·종료 자리):** `serving/api.py` L107-116

```python
    started = {"t": perf_counter()}
    default = default_variant(pipelines)  # D-11. compose.py 에 두어 api.py ≤150줄 유지

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        db.apply_schema()  # D-06: 행은 쓰지 않는다. 스키마·PRAGMA 만
        started["t"] = perf_counter()
        yield

    app = FastAPI(title="millie-rec", version=API_VERSION, lifespan=lifespan)
```
→ Phase 5 lifespan = `db.apply_schema()` → `replay(db, state, now)`(동기, 24h) → `task = asyncio.create_task(loop(...))` → `yield` → `task.cancel()`. `TestClient` 는 `with` 블록에서만 lifespan 을 돈다(`test_smoke.py` L77 주석). 루프 본체 제안은 "No Analog" 절 참조. **테스트 가능성:** 루프는 `await asyncio.to_thread(run_once, db, state, since)` 한 줄이 되게 하고, 동기 `run_once()` 를 공개해 테스트가 `sleep` 없이 직접 호출한다(CONTEXT specifics "POST /api/events 직후 상태 미변경, 루프 1회 후 변경" 단정 가능).

**웨이크:** `asyncio.Event` 는 이벤트 루프 스레드 소유다. 동기 핸들러(스레드풀)에서 `set()` 하려면 `loop.call_soon_threadsafe(wake.set)` — `create_app` 이 lifespan 안에서 `loop = asyncio.get_running_loop()` 를 잡아 `app.state` 또는 클로저에 보관하고 `demo_api` 핸들러에 `wake: Callable[[], None]` 로 넘긴다.

---

### 3. `serving/persona.py` (utility, transform)

**Analog A — 상단 매핑 dict:** `ranking/hybrid.py` L7-14

```python
CH_CF, CH_CONTENT, CH_POP = "cf", "content", "pop"  # 채널 슬롯. Candidate.source 와 다른 층
...
SOURCE_ITEMKNN, SOURCE_CONTENT = "itemknn", "content"  # retrieval 과 중복 정의(중복 < 결합)
SOURCE_POPULARITY = "popularity"
SLOT_OF_SOURCE = {SOURCE_ITEMKNN: CH_CF, SOURCE_CONTENT: CH_CONTENT, SOURCE_POPULARITY: CH_POP}
```

**Analog B — 고정 문장 상수 + 실제 값 삽입 f-string:** `app/demo_cli.py` L15-23 · L98 `print(f"### 『{m['title']}』을 좋아하셨다면 — {NEIGHBOR_NOTE}")`

**텍스트 정본(화면 01 §4-5, `demo/mock/preferences_response.json`):**
```json
{"name": "오디세우스", "work": "오디세이아", "quote": "지혜로 승리하리라!",
 "description": "회원님은 IT와 소설을 즐기고, 베스트셀러로 책을 고르는 독서가입니다."}
```
→ `PERSONAS: tuple[Persona, ...]` 4종(`contracts.Persona(name, work, quote, description)` — description 은 템플릿 채운 뒤 `replace`) · `CATEGORY_TO_PERSONA: dict[str, int]`(밀리 분류명 → 인덱스; 실측 분류명은 아래 §카탈로그 실측 표) · 미매핑은 `int(hashlib.sha256(cat.encode()).hexdigest()[:8], 16) % 4`(D-16). 기준 라벨은 `onboarding_meta.json` 의 `criteria[id].label`(예: `bestseller` → "베스트셀러") — 배지 id → 라벨 dict 를 persona.py 가 같은 json 에서 읽거나 demo_api 가 넘긴다(파일 하나 = 관심사 하나: json 로드는 `demo_api.py` 한 곳, persona 는 순수 함수 권장).

---

### 4. `serving/demo_api.py` (controller, CRUD) — `APIRouter` 는 repo 최초

**Analog — 동기 핸들러·`response_model`·B008 회피·422 규약:** `serving/api.py` L33-35 · L128-148

```python
def _422(param: str, msg: str) -> HTTPException:
    return HTTPException(422, detail=[{"loc": ["query", param], "msg": msg, "type": "value_error"}])
```
```python
    @app.get("/api/recommend", response_model=RecommendOut)
    def recommend(
        user_key: Annotated[str | None, Query()] = None,
        snapshot_id: Annotated[str | None, Query()] = None,
        model: Annotated[str | None, Query()] = None,
        k: Annotated[int, Query(ge=1, le=K_MAX)] = K_DEFAULT,
        context: Annotated[str | None, Query()] = None,
        seeds: Annotated[str | None, Query()] = None,
    ) -> RecommendOut:
        t0 = perf_counter()
        if model is not None and model not in VARIANTS:
            raise _422("model", f"model must be one of {list(VARIANTS)}")
```
→ `APIRouter` 판: 라우터를 **팩토리 함수**로 만들어 의존(`db`·`catalog`·`state`·`wake`)을 클로저로 받는다 — `create_app` 이 주입만 하는 관례(L103 docstring "주입만 받는다")를 유지한다.

```python
# 제안 골격 (api.py 관례 이식). 파일 ≤150줄이면 meta·candidates·preferences·events 4개 + ratings 1개 가능
def make_router(*, db: Database, catalog: Catalog | None, wake: Callable[[], None] | None = None) -> APIRouter:
    router = APIRouter(prefix="/api")
    meta = json.loads(META_PATH.read_text(encoding="utf-8"))  # 기동 1회 로드 (db.SCHEMA_PATH 관례)

    @router.get("/meta/onboarding", response_model=OnboardingMeta)
    def meta_onboarding() -> OnboardingMeta: ...

    @router.get("/candidates/onboarding", response_model=CandidateSet)
    def candidates(
        categories: Annotated[str, Query()],  # "IT,소설" — api.py._parse_seeds 와 같은 콤마 파싱
        n: Annotated[int, Query(ge=1, le=N_MAX)] = N_DEFAULT,
        user_key: Annotated[str | None, Query()] = None,
    ) -> CandidateSet: ...

    @router.post("/preferences", response_model=PreferencesResponse)
    def preferences(body: PreferencesRequest) -> PreferencesResponse: ...

    @router.post("/events", response_model=EventsAccepted, status_code=202)
    def events(body: EventIn | EventsBatchIn) -> EventsAccepted: ...  # 단건·배치 모두(§6)
    return router
```
- 요청 모델은 이미 있다: `schemas.py` L104-114 `PreferencesRequest`(`categories ≤3`, `seeds ≤30`, `restart`), L191-209 `EventIn`·`EventsBatchIn(min 1, max 50)`, L217-220 `EventsAccepted(accepted, duplicates, flagged)`, L224-235 `RatingIn`·`RatingOut`. **필드 추가 금지**(freeze).
- ID 발급 관례: `compose.py` L30-31 `return "rec_" + uuid.uuid4().hex[:6]` → `snap_`·`cand_`·`rat_` 동일 형태.
- 셀 배정(규칙 `serving.md` §SQLite): `int(hashlib.sha256(user_key.encode()).hexdigest()[:8], 16) % 2` → `"A"`/`"B"`, 최초 생성 시 `users.cell` 저장, 이후 저장값.
- 후보 라운드로빈(D-15)의 원재료: `Catalog.popular(categories=[cat], n=…)`(`catalog_kr.py` L76-82, `pop_rank` 순·eligible 만) → 카테고리별 리스트를 `zip`/인덱스 순환으로 1권씩, `seen: set[int]` 로 카테고리 간 중복 제거. items 의 meta 는 `catalog.meta(ids)` 로 `title authors image_url book_format` 조인(`CandidateItem` L87-93 필드).
- `supported = eligible 도서 20권 이상`(D-14): 카탈로그 전 카테고리 목록은 `catalog.meta(catalog.popular(n=10**6))`(`demo_cli.py::_all_meta` L41-42 관례 — eligible 전량) 에서 `categories` 를 세어 만든다. `Catalog` Protocol 에는 "전 카테고리 목록" 메서드가 없으므로 이 우회가 유일한 계약 내 경로.

---

### 5. `serving/privacy_api.py` (controller, CRUD read/delete)

**Analog — DB 결과를 그대로 pydantic 에 담는 핸들러:** `serving/api.py` L118-126 + `db.py::row_counts` L48-54

```python
    @app.get("/health", response_model=HealthOut)
    def health() -> HealthOut:  # 동기 def — 스레드풀 (serving.md 이벤트 루프 규칙)
        ok = db.ok()
        return HealthOut(
            status="ok",
            db_ok=ok,
            db_row_count=db.row_counts() if ok else {},
            uptime_s=perf_counter() - started["t"],
        )
```
```python
    def row_counts(self) -> dict[str, int]:
        """D-07: 스키마의 모든 테이블 COUNT(*), 0 건도 키 포함."""
        con = self.connect()
        # 테이블 이름은 sqlite_master 에서 온 값만 — 사용자 입력이 아니라 f-string 이 안전하다
        return {
            t: con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in self.table_names()
        }
```
→ `DELETE …/personalization` 응답 `PersonalizationDeleted.deleted: dict[str, int]`(`schemas.py` L274-277) = 테이블별 `cursor.rowcount` dict(키 `snapshots events ratings recommendations`, 백엔드 §10). **user_key 는 사용자 입력** — f-string 금지, 전부 `?` 바인딩. `UserDataOut`(L264-271)은 `dict[str, Any]` 행 목록 → `con.row_factory = sqlite3.Row` 후 `dict(r)`(JSON 컬럼은 `json.loads` 로 풀어 넣기). 미존재 user_key → `HTTPException(404)`. `UserStateOut.library` 3분류(재량 항목)·`snapshots[].active`(최신 1개 true) · `user_state_weights` 는 주입된 `weights` 로 계산. 삭제 후 `state.forget(user_key)` + 캐시 무효화(D-08·D-10) 호출 — 메모리 쓰기는 이 경로가 유일한 핸들러 측 예외(삭제권), 브리프에 명시.

---

### 6. `serving/dashboard_api.py` (controller, file-I/O + 집계)

**Analog A — json 파일 1회 로드, 부재 분기:** `data/catalog_kr.py::CatalogKR.load` L65-71 · `app/pipeline.py::load_catalog` L119-128

```python
    if not (serving_dir / BOOKS_KR_JSON).exists():
        log.info("no catalog at %s — serving without Track B catalog", serving_dir)
        return None
    try:
        return CatalogKR.load(serving_dir)
    except (OSError, ValueError, KeyError, TypeError):  # json 손상·키 누락·형 불일치
        log.exception("catalog unreadable at %s — serving without catalog", serving_dir)
        return None
```

**Analog B — 입력 파일의 실제 형태(생산자):** `app/export.py::write_eval_table` L25-37 → `artifacts/serving/eval_table.json` 실측:
```json
{"rows": [{"variant": "pop", "recall@20": "0.063", "ndcg@10": "0.054", "ild@10": "0.764",
           "n_users": "2000", "split_mode": "holdout", "model_version": "pop_v1"}, ...],
 "meta": {"dataset": "goodbooks-10k", "split_mode": "holdout", "n_users": 2000, "k_recall": 20,
          "k_rank": 10, "seed": 42, "git_sha": "8e5172b", "created_at": "2026-09-05T15:14:05+00:00"}}
```
**⚠ 키·타입 불일치:** `schemas_should.py` L56-61 `EvalRow(variant, recall_at_20: float, ndcg_at_10: float, ild_at_10: float, p95_ms: float | None)` 이므로 showcase 는 **`recall@20` → `recall_at_20` 키 변환 + `float()` 캐스팅**이 필요하다. `EvalTable.split_mode` ← `meta.split_mode`, `EvalTable.source` ← `{"metrics": "results/latest.csv", "p95": "results/latency.json"}` 고정(백엔드 §13). `p95_ms` 는 `results/latency.json` 이 있을 때만 4행 동일 값으로 병기(D-11 bench 는 셀 배정 혼합이라 variant 별 p95 가 없다 — `latency.json` 의 전체 p95 를 넣거나 None, planner 결정).

**상수 문장의 정본:** `philosophy`·`metric_mapping`(Candidate Retrieval→Recall@20 · Ranking→NDCG@10 · Re-ranking→ILD@10)·`memorable_5`·`roadmap`(7개)·`data_notice` 는 백엔드 서빙 01 §13 JSON 과 `../.claude/rules/serving.md` "2트랙 고지 문장" — 모듈 상단 대문자 상수. 고정 문장 상수 관례는 `app/demo_cli.py` L19-22 `FIXED_SENTENCE = (...)`.

**Should `GET /api/dashboard`(D-13 최소형):** `DashboardOut`(`schemas_should.py` L41-52) — `kpi: dict[str, KpiValue(value, n, note)]` 6개 · `latency: LatencyBlock(p50, p95, p99, by_stage={stage: [p50, p95]})` · `events_recent` ≤50 · `by_variant` · `by_hour` · `quality`. 원천은 `recommendations`(latency_total_ms·latency_breakdown JSON·fallback_level·model_version) + `events`(quality_flag·event_type). 백분위 계산은 정렬 후 인덱스(numpy 금지 아님이나 stdlib `statistics.quantiles` 로 충분).

---

### 7. `serving/bench.py` (CLI + HTTP 클라이언트 + results writer)

**Analog A — argparse 1개·`if __name__`:** `app/cli.py` L113-135

```python
def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(
        prog="millie_rec.app.cli", description="Track A 데이터·평가 진입점(make data · make eval)"
    )
    sub = ap.add_subparsers(dest="cmd", required=True)
    ...
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    args.func(args)


if __name__ == "__main__":
    main()
```
→ bench 는 서브커맨드 없이 `--base http://localhost:8000 --users 50 --warmup 50 --n 500 --k 40 --out results/latency.json --seed 42`. `Makefile` L45-46 `bench: uv run python -m millie_rec.serving.bench` 가 이미 이 모듈을 가리킨다(인자 없이 실행돼야 한다 → 전부 기본값).

**Analog B — git sha·created_at·json 쓰기:** `evaluation/report.py` L53-66 · L104-119

```python
def git_sha() -> str | None:
    """짧은 sha. git 이 없거나 실패하면 None — 절대 예외를 내지 않는다."""
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, check=False, cwd=ROOT, timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout.strip() or None if out.returncode == 0 else None
```
```python
    payload = {**asdict(meta), "n_users": n_users, "k_recall": K_RECALL, "k_rank": K_RANK,
               "created_at": now.isoformat(timespec="seconds"), "rows": [...], "states": [...]}
    path = out_dir / f"eval_{now.strftime('%Y%m%d_%H%M')}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
```
→ **serving 은 `millie_rec.evaluation.git_sha` 를 import 할 수 없다**(star 의존) → 6줄 중복 정의(architecture.md "중복 < 결합"). 출력 파일은 `contracts.DIR_RESULTS / "latency.json"` 고정 이름(PDF 의 유일한 지연 숫자, `serving.md` 숫자 규칙). 페이로드 키(D-11): `p50 p95 p99 n warmup users k fallback_levels{0..3: n} variants{model_version: n} catalog{n_books} created_at git_sha base_url`.

**Analog C — 표준 라이브러리 HTTP 클라이언트(httpx 는 dev 전용):** `scripts/collect_millie.py` L66-69

```python
def _get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310
        return resp.read()
```
→ POST 는 `urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"}, method="POST")`. 지연 측정은 클라이언트 측 `perf_counter()` 감싸기(전체 응답 기준 = D-11 "게이트 p95 < 200 은 전체 응답 기준"). 시드 5권은 `GET /api/candidates/onboarding` 또는 `catalog.popular` 가 아닌 **서버 HTTP 만** 써야 하므로(bench 는 클라이언트) `random.Random(contracts.SEED).sample(candidates, 5)` — 후보는 `GET /api/candidates/onboarding?categories=<supported 상위 3>&n=60` 응답에서 뽑는다.

**테스트 가능성:** 측정·집계 함수(`percentiles(samples) -> dict`, `summarize(records) -> payload`) 를 HTTP 와 분리해 순수 함수로 두면 `tests/serving/test_bench.py` 가 네트워크 없이 손계산 단정 가능(테스트 규칙 "네트워크 절대 호출 안 함").

---

### 8. `serving/onboarding_meta.json` (config)

**Analog — 패키지 옆 데이터 파일 로드:** `serving/db.py` L10 · L41-43
```python
SCHEMA_PATH = Path(__file__).parent / "schema.sql"
...
        self.connect().executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
```
**텍스트 원천(글자 그대로, `/contract-sync` 가 `demo/config/onboarding.json` 과 동일성 검사):**
- `reading_times` 5 = `demo/config/onboarding.json` S1 `options`: `"아침, 하루를 시작할 때" "점심시간이나 짧은 휴식 시간" "저녁, 하루를 마치며" "잠들기 전" "주말이나 휴일, 여유로울 때 몰아서"`
- `criteria` 5(id = `contracts.BADGE_TYPES` 원소, `Criterion.id: BadgeType` 검증) = S3 `options` 순서: `author "좋아하는 작가"` · `publisher "좋아하는 출판사"` · `bestseller "베스트셀러"` · `buzz "화제작 (SNS,셀럽 추천, 수상도서)"` · `review "리뷰, 별점 등 대중의 평가"`
- `subcategories`(화면 01 §4-2, 정적): `IT: 개발/프로그래밍 · 그래픽/멀티미디어 · IT 교양 · e비즈니스 · 오피스 활용 · 컴퓨터 수험서` / `소설: 추리/스릴러 · SF · 판타지 · 영미 소설 · 한국 소설 · 일본 소설 · 유럽 소설` / `철학: 동양 · 정치/경제 · 예술/문화 · 서양` — 나머지 카테고리는 `[]`
- `categories[].name`·`supported` 는 **json 에 넣지 않고** 카탈로그에서 계산(D-14) → json 은 `{"survey_variant": "v1", "reading_times": [...], "criteria": [...], "subcategories": {"IT": [...], "소설": [...], "철학": [...]}}` 형태, 응답 시 `OnboardingMeta`(`schemas.py` L79-83) 로 조립. **hatchling 패키징:** `pyproject.toml` `packages = ["src/millie_rec"]` 는 패키지 폴더 안 비-py 파일(`schema.sql` 이 이미 그렇다)을 포함한다 — Dockerfile `COPY src` 도 동일.

---

### 9. `serving/api.py` (MODIFY — 150줄 한도)

**현재 재사용 가능 블록:** `_422` L33-35 · `_parse_seeds` L37-44 · `_fallback_response` L47-64 · `_personalized_response` L67-89 · `recommend` 본문 L137-148

```python
def _personalized_response(pipe, fallback, user, k, t0, context, weights=None) -> RecommendResponse:
    """level 0. 파이프라인 예외는 level 3 로 강하 — 500 도 예외 문자열 노출도 없다(Phase 2 D-13)."""
    try:
        items = pipe.recommend(user, k)
        shown = (
            weights(user) if weights is not None else None
        )  # D-09: 파이프라인과 같은 함수 → 표시 = 실제
    except Exception:
        log.exception("pipeline %s failed; falling back to level 3", pipe.name)
        return _fallback_response(fallback, user, k, t0, context)
    version = f"{pipe.name}{MODEL_VERSION_SUFFIX}"
    resp = build_response(items, model_version=version, level=FALLBACK_PERSONALIZED, k=k, t0=t0, context=context)
    return replace(resp, user_state_weights=dict(shown)) if shown is not None else resp
```
→ **150줄을 지키는 방법(CONTEXT 재량):** `_fallback_response`·`_personalized_response` 를 `fallback.py`(cascade 책임) 로 옮기고 `api.py` 는 `create_app` + `/health` + `/api/recommend` 껍데기 + `include_router` 3줄만 남긴다. D-09 breakdown 은 `perf_counter()` 3구간 — 현재 `build_response(..., t0=t0)` 가 `total` 만 계산(L44·L57) 하므로 `latency_breakdown: dict[str, float]` 인자를 compose 에 추가(기본 `None` → 하위 호환). `getattr(pipe, "last_breakdown", None)` 로 세분 키 병합(D-09). `/health` 채우기(재량): `model_version=f"{default}{MODEL_VERSION_SUFFIX}" if default else None` — **`test_smoke.py` L87 은 `pipelines={}` 일 때 `model_version is None and artifacts_loaded_at is None` 을 단정**하므로 `artifacts_loaded_at` 도 `catalog is None` 이면 None 을 유지해야 한다.

---

### 10. `serving/compose.py` (MODIFY — Must 5행·dedup·배지·메타)

**Analog A — Row 조립:** `serving/fallback.py::trending_row` L37-45
```python
def trending_row(items: Sequence[ScoredItem]) -> Row:
    """D-02: level 3 응답의 유일한 행. Must 5행 뼈대는 Phase 5 compose.py."""
    return Row(
        row_id=TRENDING_ROW_ID, title=TRENDING_TITLE, purpose=TRENDING_PURPOSE,
        items=tuple(items), channel_mix={SOURCE_POPULARITY: len(items)} if items else {},
    )
```
→ 행 순서 리스트 상수(렌더 순서 정본, `contracts.py` L75 주석 "렌더 순서의 정본은 serving/compose.py 의 리스트"): `ROW_ORDER = ("continue_reading", ROW_ANCHOR_PREFIX, "persona_shelf", "trending", "fresh_picks")`, `ROW_SIZE = 12`(D-03), 앵커 `row_id=f"{ROW_ANCHOR_PREFIX}{seed1}"`(`schemas.py` L36-39 `_row_id` 가 접두 허용), `purpose ∈ contracts.ROW_PURPOSES` (`resume discover fallback explore`).

**Analog B — meta 5필드 조인(`replace`):** `app/pipeline_kr.py::WithMeta.recommend` L82-98
```python
        meta = {int(m["book_id"]): m for m in self.catalog.meta([i.book_id for i in items])}
        out = []
        for i in items:
            m = meta.get(i.book_id, {})
            out.append(
                replace(
                    i,
                    title=m.get("title"), authors=m.get("authors"), image_url=m.get("image_url"),
                    book_format=m.get("book_format"),
                    difficulty=i.difficulty if i.difficulty is not None else m.get("difficulty"),
                )
            )
```
→ compose 가 앵커·fallback·후보 items 에 같은 함수를 적용(`with_meta(items, catalog)`; `catalog None` 이면 원본 반환 — 스켈레톤 기동 보장). 배지 근거 필드도 같은 `meta` dict 에서: `pop_rank`(bestseller "인기 N위") · `average_rating`+`review_count`(review 3단) · `authors`·`publisher`(seeds 의 meta 와 일치 시) · `millie_label`(buzz) — `books_kr.json` 실측 키 목록은 기준선 표 참조(`description` 없음).

**Analog C — 정규화 제목 키(D-04 dedup):** `app/demo_cli.py::_norm` L26-27
```python
def _norm(s: object) -> str:
    return "".join(str(s or "").split()).casefold()  # 대소문자·공백 무시 매칭 키
```
→ compose 에 중복 정의(serving 은 app 을 import 못 한다) + 기호 제거 확장: `re.sub(r"[^\w]", "", str(s or "")).casefold()`. dedup 은 `seen_ids: set[int]`·`seen_titles: set[str]` 두 집합을 행 순서대로 흘리며 `dedup_removed` 누적 → `RecommendResponse.dedup_removed`(`contracts.py` L269, 기본 0).

**Analog D — 이웃 조회는 Protocol 로만:** `data/catalog_kr.py::neighbors` L89-91 반환 `list[tuple[int, float]]`(weight 내림차순) → 앵커 items `ScoredItem(book_id=dst, score=w, source="content", reason=f"『{seed_title}』을 좋아하셨다면", source_channels=("content",), position=i)`(`test_schemas.py` L21-40 이 정확히 이 형태의 손조립 예시).

**앵커 reason 문자열 정본:** `app/demo_cli.py` L98 `f"### 『{m['title']}』을 좋아하셨다면 — ..."` · `contracts.py` L223 주석 `"『X』을 좋아하셨다면"` · `schemas.py`/`test_schemas.py` L25 `"『나무』를 좋아하셨다면"` — 조사는 **"을"** 로 통일(D-03 `"『{seed 제목}』을 좋아하셨다면"`).

---

### 11. `serving/fallback.py` (MODIFY — level 1 캐시·level 2·cascade)

**Analog — 자기 자신:** `GlobalPopularFallback.recommend` L21-34(`catalog.popular(n=k+len(user.seen))` → seen 제외 → `ScoredItem(..., source=SOURCE_POPULARITY, position=i, source_channels=(SOURCE_POPULARITY,))`).
→ level 2 = 같은 함수에 `categories=snapshot.categories` 인자(`Catalog.popular(categories, n)` L76-82). level 1 캐시(D-10) = 모듈 내 `dict[tuple[str, str, str], tuple[float, tuple[Row, ...], str]]`(키 `(user_key, snapshot_id, variant)`, 값 `(expires_at, rows, model_version)`) + `threading.Lock`; TTL 은 `contracts.CACHE_TTL_S`(600), 예산은 `contracts.BUDGET_MS`(200) — **테스트는 `monkeypatch.setattr("millie_rec.serving.fallback.BUDGET_MS", 1)` 식으로 모듈 이름공간의 바인딩을 바꾸므로 `from millie_rec.contracts import BUDGET_MS` 로 모듈 상단에 가져와 쓴다**(`test_smoke.py` L132-136 `monkeypatch.setenv/delenv` 관례의 setattr 판). 예외 → 로그 → 다음 단계(`api.py` L57-61 `try/except Exception: log.exception(...)` 형태 그대로), **항상 200**.

---

### 12. `serving/db.py` (MODIFY — 쓰기 헬퍼·`close`) · `schema.sql` (인덱스)

**현재:** `connect()` L32-39 · `apply_schema()` L41-43(`executescript` = 암묵 커밋) · **DML 커밋 헬퍼 없음**. Python 3.11 `sqlite3` 기본 `isolation_level=""` 은 DML 앞에 암묵 `BEGIN` — 커밋하지 않으면 다른 스레드(Nearline)의 연결에서 보이지 않는다.

```python
# 제안 — 기존 메서드와 같은 결(한 메서드 = 한 SQL 관심사, 1줄 docstring)
    def execute(self, sql: str, params: Sequence[object] = ()) -> int:
        """DML 1문 + 커밋. rowcount 반환(DELETE 집계용). 파라미터는 항상 ? 바인딩."""
        con = self.connect()
        with con:  # 예외 시 롤백, 정상 시 커밋
            return con.execute(sql, params).rowcount

    def executemany(self, sql: str, rows: Sequence[Sequence[object]]) -> int: ...

    def query(self, sql: str, params: Sequence[object] = ()) -> list[sqlite3.Row]:
        """SELECT. row_factory=sqlite3.Row 로 dict(r) 가능."""

    def close(self) -> None:
        """현재 스레드 연결만 닫는다(01-CONTEXT Deferred). lifespan shutdown 에서 호출."""
```
JSON 컬럼(`schema.sql` L10·L16·L21 주석 `-- JSON: ...`)은 `json.dumps(v, ensure_ascii=False)`(`app/export.py` L40 관례) 로 TEXT 저장, `consent`·`forced`·`selected` 는 `int(bool)`. `events.event_id TEXT PRIMARY KEY`(L13) → 중복은 `INSERT OR IGNORE` + `rowcount == 0` 으로 `duplicates` 집계(D-12 "중복은 무시").

**`schema.sql` 증분(DDL 만, 컬럼 변경 없음):** 기존 L5-22 `CREATE TABLE IF NOT EXISTS` 와 같은 멱등 형태로 파일 끝에
```sql
-- Phase 5 인덱스 (CONTEXT 재량). 리플레이·상태 조회·대시보드 집계 경로
CREATE INDEX IF NOT EXISTS idx_events_user_ts ON events(user_key, ts);
CREATE INDEX IF NOT EXISTS idx_recommendations_user_ts ON recommendations(user_key, ts);
```
L1 머리 주석 "인덱스는 Phase 5" 를 이 페이즈에서 갱신.

---

### 13. `serving/__init__.py` (MODIFY)

**Analog:** 자기 자신 L1-16 — 알파벳 정렬 `__all__`(대문자 상수 → 클래스 → 함수 순이 아니라 **문자 코드 순**: `API_VERSION Database EventIn ... create_app resolve_db_path`). 추가 후보: `StateStore`(state.py) · `make_demo_router` 등은 `app/server.py` 가 필요할 때만 노출 — `app` 은 공개 표면만 import 가능(`test_architecture.py` L41-42). compose·fallback 내부 이름은 노출하지 않는다(현재 `compose.py` L3 "__init__ 에 노출하지 않는다" 관례).

---

### 14. `app/server.py` (MODIFY, Advisor — `state=`·어댑터 주입·`StagedPipeline.last_breakdown`)

**Analog:** 자기 자신 L15-24
```python
catalog = load_catalog()
app = create_app(
    pipelines=build_pipelines(catalog=catalog, weights=state_weights),
    fallback=GlobalPopularFallback(catalog),
    catalog=catalog,
    db=Database(resolve_db_path()),
    neighbors=catalog,
    book_stats=catalog,
    weights=state_weights,
)
```
→ `state=StateStore(...)`·`book_stats=<serving 어댑터>(catalog)` 채움. `tests/serving/test_smoke.py` L164-204 두 테스트가 `app.server` 를 재import 하며 `load_catalog`·`build_pipelines` 를 monkeypatch 하므로 새 인자는 **`catalog=None` 에서도 기동**해야 한다. `StagedPipeline.recommend`(`app/pipeline.py` L81-92) 의 `retrieve → blend_channels → rerankers` 세 지점에 `perf_counter` 를 감싸 `self.last_breakdown = {"retrieval": ms, "ranking": ms, "rerank": ms}` 를 기록(D-09, 상수·로직 무변경).

---

### 15. `tests/serving/*` (NEW 7개) — 조립·가짜·fixture 관례

**Analog A — `create_app` 직접 조립 + `tmp_path` DB + `with TestClient`:** `tests/serving/test_smoke.py` L67-78
```python
def _app(tmp_path: Path, fallback=None):
    return create_app(
        pipelines={},
        fallback=fallback or GlobalPopularFallback(None),
        db=Database(tmp_path / DB_FILENAME),
    )


@pytest.fixture
def client(tmp_path: Path):
    with TestClient(_app(tmp_path)) as c:  # with 블록이어야 lifespan(스키마 적용)이 돈다
        yield c
```

**Analog B — 가짜 Pipeline 3종(정상·예외·이름만 다른):** `tests/serving/test_recommend_level0.py` L29-61 — `_FakePop`(1..39 seen 제외, `source="popularity"`, `position`, `source_channels`) · `_FakeNamed(name)` · `_Boom`(항상 `RuntimeError`). D-10 예산 초과용은 `_Slow`(`time.sleep(0.01)` 후 `_FakePop` 결과) + `monkeypatch.setattr("millie_rec.serving.fallback.BUDGET_MS", 1)`. **테스트 간 import 금지 관례**(`test_api_weights.py` L5 "가짜는 복제") → 새 파일마다 가짜를 복제한다.

**Analog C — 가짜 Catalog(meta 있음):** `tests/app/test_pipeline.py::_FakeCatalog` L81-103
```python
class _FakeCatalog:
    """popular·meta·eligible 만 — Track B pop 이 쓰는 표면."""

    def meta(self, book_ids):
        return [{"book_id": b, "title": f"책{b}", "authors": "a",
                 "image_url": "https://img.millie.co.kr/x.jpg", "book_format": "전자책",
                 "difficulty": 0.4} for b in book_ids]

    def popular(self, categories=(), n=50):
        return list(range(1, 11))[:n]

    def eligible(self, book_ids):
        return list(book_ids)
```
→ compose·demo_api 테스트용 확장: `categories`·`publisher`·`pop_rank`·`average_rating`·`review_count`·`millie_label` 키 추가, `popular(categories)` 가 카테고리 필터를 흉내(라운드로빈·level 2 단정용), `neighbors(book_id, n)` 추가(앵커 12권 단정). 손계산 가능한 20권 이하로.

**Analog D — 실 형태 20권 카탈로그가 필요할 때:** `tests/app/test_server_catalog.py` L20-28·`tests/data/test_catalog_kr.py` L15-17 — `CatalogKR.load(millie_serving_sample)`(conftest session fixture, Path 반환). `tests/` 는 무엇이든 import 가능하나 D-17 "Model 레인과 독립" 취지상 serving 단위 테스트는 가짜 Catalog 를, 통합 1~2건만 `millie_serving_sample` 을 쓴다(자격 없는 18·19·20 제외 단정 가능, 카테고리 `소설 에세이 경제경영 인문` 순환 = 라운드로빈 검증에 적합).

**Analog E — Protocol 가짜 + 호출 횟수 카운트:** `tests/reranking/test_guard.py::_FakeStats` L12-27(`stats()` 호출 수 `self.calls`, `user_level` None) → state.py 어댑터 테스트에서 `inner.stats` 위임 1회 단정.

**Analog F — 파일 페이로드 테스트:** `tests/app/test_export.py` L20-55(`tmp_path/results/latest.csv` 를 써 넣고 함수 호출 → `json.loads` → 키 집합 단정) → dashboard_api showcase 테스트는 `tmp_path/eval_table.json` 에 위 실측 형태(문자열 값)를 써 넣고 `ShowcaseOut.model_validate(r.json())` 파싱 + `float` 변환 단정.

**네이밍:** `test_<기능>_<시나리오>_<기대결과>` · 파일 머리 3종 표기 `# ── 계약 ──` `# ── 정확성 ──` `# ── 안전성 ──`(`test_smoke.py` L81·L99·L148).

---

## Shared Patterns

### A. 예외는 로그 후 강하, 500·문자열 노출 없음
**Source:** `serving/api.py` L56-61 · L82-84 · `app/pipeline.py` L126-128
**Apply to:** `api.py`(cascade) · `fallback.py` · `nearline.py`(루프 1회 실패 → 로그 후 계속) · `dashboard_api.py`(파일 부재)
```python
    try:
        items = fallback.recommend(user, k)
    except Exception:
        log.exception("fallback pipeline failed; serving empty trending row")
        items = []
```
테스트 단정 관례: `assert "boom" not in r.text and "Traceback" not in r.text`(`test_recommend_level0.py` L148).

### B. 동기 `def` 핸들러 + `response_model` + `Annotated Query`(B008 회피)
**Source:** `serving/api.py` L118-119 · L128-136
**Apply to:** `demo_api.py` `privacy_api.py` `dashboard_api.py` 전 핸들러(Nearline 만 `async`).

### C. 계약 DTO → pydantic 변환은 `schemas.py` 한 곳
**Source:** `serving/schemas.py::RecommendOut.from_contract` L181-187
```python
    @classmethod
    def from_contract(cls, r: RecommendResponse, *, forced: bool = False) -> "RecommendOut":
        d: dict[str, Any] = asdict(r)
        d["items"] = [asdict(i) for i in r.items]
        d["rows"] = [asdict(row) for row in r.rows]
        d["forced"] = forced
        return cls.model_validate(d)
```
→ 새 응답(`PreferencesResponse`·`UserStateOut`·…)은 **DTO 없이 pydantic 을 직접 생성**해도 되나(계약 DTO 가 없는 응답), `Persona`·`PreferenceSnapshot` 처럼 DTO 가 있는 것은 `asdict` 경유. `schemas.py` 에 **메서드 추가도 freeze 위반**이 아닌지 애매하므로 변환 헬퍼는 각 라우터 파일에 둔다(schemas 무변경이 안전).

### D. ID·타임스탬프 관례
**Source:** `serving/compose.py` L30-31(`"rec_" + uuid.uuid4().hex[:6]`) · `app/export.py` L35(`datetime.now(UTC).isoformat(timespec="seconds")`)
**Apply to:** `snap_`·`cand_`·`rat_`(demo_api) · `created_at`·`ts`·`exported_at`(전 파일). `datetime.UTC` 는 3.11 이상(요구 3.11 충족).

### E. meta 5필드 조인 함수 1개
**Source:** `app/pipeline_kr.py::WithMeta.recommend` L84-97
**Apply to:** compose(앵커·trending·fresh_picks·after_completion) · demo_api(후보 `CandidateItem`) · privacy_api(`LibraryBook.title/image_url`). serving 안에 한 번 정의(`compose.py` 공개 함수), 다른 serving 파일이 import(같은 슬라이스 내부 import 허용).

### F. 파이프라인 예외·예산 초과 → 항상 200 의 테스트 3종
**Source:** `tests/serving/test_smoke.py` L156-160 · `test_recommend_level0.py` L142-148 · `test_api_weights.py` L91-98
**Apply to:** `test_fallback_cascade.py` — `_Boom`(예외→1 또는 3) · `_Slow`+`BUDGET_MS` monkeypatch(예산→1) · 캐시 有/無(1→2→3) · `consent=false`(→3, 가중치 0).

### G. star 의존 회피 = 중복 정의 + 주석
**Source:** `app/pipeline.py` L38 `SOURCE_POPULARITY = "popularity"  # serving/fallback.py 와 같은 값 — 공개 표면에 없어 중복 정의` · `app/demo_cli.py` L30-31 `_parse_seeds ... serving/api.py 와 같은 로직의 중복 정의`
**Apply to:** `bench.py::git_sha`(evaluation 것과 동일) · `compose.py::_norm`(demo_cli 것 확장) · `persona.py`/`dashboard_api.py` 고정 문장.

---

## No Analog Found — 규칙·CONTEXT 기반 제안 스니펫

| File | Role | Data Flow | Reason |
|---|---|---|---|
| `serving/nearline.py` 루프 본체 | background loop | event-driven | src 에 `asyncio` 사용 0건 |
| `demo_api.py` 셀 배정 | utility | transform | src 에 `hashlib` 사용 0건 |
| `bench.py` HTTP 클라이언트·백분위 | client | request-response | src 에 HTTP 클라이언트 0건(scripts 만 `urllib`) |
| `fallback.py` level 1 TTL 캐시 | cache | — | 재시도·캐시 데코레이터 금지(simplicity.md) → dict + Lock 수작업 |

```python
# nearline.py 제안 — 30s 타이머 ∨ 웨이크(asyncio.Event), 본체는 동기 run_once 를 to_thread
INTERVAL_S = NEARLINE_INTERVAL_S  # contracts 30
REPLAY_WINDOW_S = 24 * 3600

def run_once(db: Database, state: StateStore, *, since_ts: str | None, now: float) -> str | None:
    """events(ts > since) 를 읽어 state 에 반영. 마지막 ts 반환. 예외는 호출자가 로그."""

async def loop(db, state, wake: asyncio.Event, last: dict[str, str | None]) -> None:
    while True:
        try:
            await asyncio.wait_for(wake.wait(), timeout=INTERVAL_S)
        except TimeoutError:  # 3.11: asyncio.TimeoutError is TimeoutError
            pass
        wake.clear()
        try:
            last["ts"] = await asyncio.to_thread(run_once, db, state, since_ts=last["ts"], now=time.time())
            last["run_at"] = datetime.now(UTC).isoformat(timespec="seconds")  # /health nearline_last_run
        except Exception:
            log.exception("nearline run failed; continuing")
```
```python
# 동기 핸들러 → 이벤트 루프 스레드의 Event 를 깨우기 (lifespan 에서 loop 를 잡아 클로저로)
loop_ref = asyncio.get_running_loop()
def wake() -> None:
    loop_ref.call_soon_threadsafe(event.set)
```
```python
# 셀 배정 (serving.md §SQLite · 아키 §3-10). CPython hash() 금지
def assign_cell(user_key: str) -> str:
    return "A" if int(hashlib.sha256(user_key.encode()).hexdigest()[:8], 16) % 2 == 0 else "B"
```
```python
# bench 백분위 — 정렬 인덱스(외부 의존 없음, 손계산 테스트 가능)
def percentile(sorted_ms: Sequence[float], p: float) -> float:
    idx = min(len(sorted_ms) - 1, max(0, math.ceil(p / 100 * len(sorted_ms)) - 1))
    return float(sorted_ms[idx])
```

---

## 기존 테스트와의 충돌 지점 — planner 가 결정해야 한다

D-04 는 "level 3 rows = `trending` + `fresh_picks`", D-01~03 은 level 0 = Must 5행이다. 그런데 아래 기존 단정은 **"rows 1행 = trending"** 을 전제한다(Phase 1 D-02·Phase 2 D-12 형태 — CONTEXT 가 D-04 로 대체한다고 명시). `python-tdd.md` "기존 테스트의 단정을 고치는 것" 금지 규칙과 충돌하므로 **(i) 조건부 호환**(아래 권장) 또는 **(ii) Advisor 승인 하에 해당 단정만 갱신 + PROGRESS 1줄** 중 하나를 plan 에 명시할 것.

| 파일:줄 | 단정 | 상황 |
|---|---|---|
| `tests/serving/test_smoke.py:104` | `len(d["rows"]) == 1` | level 3, `catalog=None`, seeds 만 |
| `tests/serving/test_smoke.py:160` | `rows[0]["items"] == []` | level 3, fallback 예외 |
| `tests/serving/test_recommend_level0.py:83-88` | `len(rows)==1`, `rows[0].row_id=="trending"`, `title=="지금 많이 읽는 책"`, `purpose=="fallback"`, `channel_mix=={"popularity": 5}` | **level 0**, seeds 만, `catalog=None` |
| `tests/serving/test_recommend_level0.py:105` | `rows[0].items == items` | level 0, seeds 만 |
| `tests/serving/test_recommend_level0.py:147` | `rows[0]["items"] == []` | level 3 |
| `tests/app/test_server_catalog.py:39,41,53` | `rows[0].row_id=="trending"`, `rows[0].items[0].title=="밀리 표본 도서 4"` / 익명 `rows[0].items` 인기 | level 0 seeds+`model=pop` **카탈로그 있음** / 익명 level 3 |
| `tests/app/test_variants.py:79` | `rows[0].items[0].title.startswith("밀리 표본 도서")` | level 0 seeds, 카탈로그 있음 |

**권장(i):** compose 를 두 경로로 나눈다 — **`user_key`+스냅샷 경로 = Must 5행(D-01~04)**, **seeds 쿼리 cold-start 경로(CLI·bench·smoke 전용, CONTEXT 재량 "seeds 는 CLI·bench·cold-start 전용") = 기존 1행 `trending_row(items)` 유지**, 익명·level 3 에 `fresh_picks` 를 붙이는 것은 **`catalog is not None` 일 때만**(스켈레톤 기동·`make smoke` 의 `?seeds=1,2,3&k=5` 는 카탈로그 없이도 200). 이렇게 하면 위 표 중 `test_server_catalog.py:53`(익명 + 카탈로그 → rows 가 2행이 되지만 `rows[0]` 은 여전히 trending) 포함 전부 통과하고, D-04 의 "trending + fresh_picks" 는 카탈로그 있는 실서버·`user_key` 경로에서 성립한다. 예외 없이 D-04 를 seeds 경로에도 적용하려면 (ii).

**`/health` 단정:** `test_smoke.py:87` `model_version is None and artifacts_loaded_at is None`(`pipelines={}`·`catalog=None`) — 재량 항목 "`/health` 채우기"는 이 조건에서 None 을 유지해야 한다.

---

## 카탈로그 실측 — persona 매핑·`supported` 계산 입력 (`artifacts/serving/books_kr.json`, 2026-09-06)

9,447권 · 카테고리 29종(전부 eligible ≥ 20 → **`supported=false` 인 분류는 현재 없다**; 오디오북 1,709 중 1,706 eligible). D-16 "Worker 가 분류명을 보고 채운다" 를 위해 인라인:

| 밀리 분류명 | 권수 | 페르소나 후보(화면 01 §4-5) |
|---|---|---|
| 소설 1719 · 오디오북 1709 · 에세이/시 714 · 인문 632 · 자기계발 587 · 경제경영 511 · 어린이 472 · 라이프스타일 383 · 챗북 377 · 역사 245 · 청소년 202 · 철학 202 · 과학 198 · 웹툰/웹소설 184 · 밀리 오리지널 177 · 사회 171 · 부모 147 · 여행 144 · 외국어 115 · 종교 114 · IT 105 · 매거진 87 · 디즈니 60 · 세계문학전집 51 · 도슨트북 47 · 빨간펜 동화 34 · 만화 30 · 미분류 18 · 오브제북 12 | | 오디세우스 ← `경제경영 자기계발 IT` / 셜록 홈즈 ← `소설 과학 철학` / 돈키호테 ← `인문 역사 사회` / 제인 에어 ← `에세이/시 라이프스타일` (나머지 = sha256 결정적) |

`millie_label` 값 4종(buzz 배지 원천): `마니아 2901 · 밀리 픽 2092 · 홀릭 1461 · 히든 1342 · None 1651`. `book_format`: `전자책 6087 · 오디오북 2993 · 챗북 367`. `demo/mock/meta_onboarding.json` 의 `supported=false`(라이프스타일·외국어·매거진·사회·부모)는 **mock 생성기 값**이며 서버 계산과 다를 수 있다 — `/contract-sync` 는 텍스트(이름·라벨)만 비교해야 한다(Phase 6 항목).

---

## Metadata

**Analog search scope:** `millie-rec/src/millie_rec/{serving,app,data,ranking,reranking,evaluation}` · `tests/{serving,app,data,reranking}` · `tests/conftest.py` · `scripts/collect_millie.py` · `demo/config` · `demo/mock` · `../.assets/설계서/백엔드 서빙/01_백엔드_서버_구성.md` §2·§8~§10·§13 · `../.assets/설계서/화면 구성 및 디자인/01_기술스택_및_화면설계.md` §4-2·§4-5
**Files scanned:** 소스 22 · 테스트 12 · 설정/데이터 8
**Pattern extraction date:** 2026-09-06
**CodeGraph:** 미사용(서버 미연결 세션) — Read/Grep 으로 대체, 줄 번호는 2026-09-06 파일 기준 실측
