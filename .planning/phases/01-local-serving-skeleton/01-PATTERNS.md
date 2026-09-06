# Phase 1: 로컬 서빙 스켈레톤 - Pattern Map

**Mapped:** 2026-09-05
**Files analyzed:** 8 (신규 6 · 수정 2)
**Analogs found:** 5 / 8 (exact 2 · role-match 3 · no-analog 3)

저장소 현황: `src/millie_rec/serving/`에는 `schemas.py`·`schemas_should.py`·`__init__.py`만, `app/`에는 `__init__.py`만 있다. FastAPI 라우터·SQLite 모듈·`Pipeline` Protocol 구현체는 **하나도 없다**. 따라서 이 페이즈의 analog는 (a) 계약·스키마 파일의 import/직렬화 관례, (b) `tests/serving/test_schemas.py`의 DTO 조립·테스트 관례, (c) `scripts/*.py`의 Python 스타일(1줄 docstring·모듈 상단 대문자 상수·`pathlib`), (d) 설계서 원문(DDL·`create_app` 시그니처)으로 구성된다. 경로는 `millie-rec/` 기준.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `src/millie_rec/serving/schema.sql` (신규) | migration (DDL) | file-I/O (기동 시 1회 적용) | 없음 — DDL 원문은 `../.assets/설계서/시스템 아키텍처, 기술 스택 및 배포(프론트, 백엔드 서빙)/01_시스템_아키텍처_기술스택_배포.md` §3-4 데이터 저장 | no-analog (설계서 복사) |
| `src/millie_rec/serving/db.py` (신규) | repository/adapter (SQLite 연결) | file-I/O (연결·PRAGMA·스키마 적용·COUNT) | `scripts/export_millie_serving.py` `_write()` (mkdir·pathlib) + `src/millie_rec/contracts.py` L94-97 (경로 상수) | role-partial |
| `src/millie_rec/serving/fallback.py` (신규) | service (`contracts.Pipeline` 구현체) | transform (UserState → ScoredItem 리스트) | `src/millie_rec/contracts.py` L340-345 `Pipeline` Protocol + L315-320 `Catalog` Protocol; `tests/serving/test_schemas.py` L21-32 `ScoredItem` 조립 | role-match (Protocol 형태만 존재) |
| `src/millie_rec/serving/api.py` (신규) | controller (FastAPI `create_app`·`/health`·`/api/recommend`) | request-response | `src/millie_rec/serving/schemas.py` L14-22 import 관례 · L56-64 `HealthOut` · L181-187 `RecommendOut.from_contract`; `tests/serving/test_schemas.py` L20-52 `_response()` (`RecommendResponse` 조립) | role-partial (라우터 analog 없음, 직렬화 표면은 exact) |
| `src/millie_rec/app/server.py` (신규, Advisor) | composition root / entrypoint | request-response (StaticFiles) | `src/millie_rec/app/__init__.py` (docstring) · `Makefile` L30-31 · `Dockerfile` L13 (진입점 이름) · `contracts.ROOT` L20 | no-analog (설정 파일에서 도출) |
| `tests/serving/test_smoke.py` (신규) | test | request-response (TestClient) | `tests/serving/test_schemas.py` (전체) · `tests/test_architecture.py` L1-13 (docstring·상수 관례) | exact |
| `src/millie_rec/contracts.py` (수정: 상수 1개, Advisor) | config/contract | — | 자기 자신 L60-62 `MODEL_VERSION_SUFFIX` · L94-97 런타임 저장 경로 블록 | exact |
| `src/millie_rec/serving/__init__.py` (수정: `__all__`) | public surface | — | 자기 자신 L1-5 | exact |

## Pattern Assignments

### `src/millie_rec/serving/schema.sql` (migration, file-I/O)

**Analog:** 없음. DDL 정본은 아키텍처 01 §3-4 데이터 저장(`01_시스템_아키텍처_기술스택_배포.md` L187-201). D-05(01-CONTEXT.md 'SQLite 스켈레톤 범위')에 따라 **Must 4 + Should 3 전부**를 `CREATE TABLE IF NOT EXISTS`로 쓴다. 예상 45줄(아키 01 §9-3 표).

**DDL 원문(설계서 §3-4, 그대로 옮긴다 — 타입 표기가 없는 컬럼은 TEXT, `JSON`은 TEXT, `INT`는 INTEGER, `REAL`은 REAL):**
```sql
-- Must 4
users               (user_key PK, created_at, consent INT, cell TEXT, is_new INT)
preference_snapshots(snapshot_id PK, user_key, created_at, reading_time, categories JSON, criterion,
                     subcategories JSON, seeds JSON, persona JSON)
events              (event_id PK, user_key, book_id, event_type, ts, surface, row_id, position, selected INT,
                     recommendation_id, model_version, preference_snapshot_id, candidate_set_id, payload JSON, quality_flag)
recommendations     (recommendation_id PK, user_key, snapshot_id, model_version, cell, forced INT, fallback_level,
                     latency_total_ms REAL, latency_breakdown JSON, weights JSON, rows JSON, ts)
-- Should 3
ratings             (rating_id PK, user_key, book_id, stars, ts, recommendation_id)
candidate_sets      (candidate_set_id PK, user_key, ts, book_ids JSON, survey_variant)
book_stats          (book_id PK, impressions, reader_opens, qualified_reads, completions, rating_mean, rating_var,
                     difficulty REAL, n_events, source, updated_at)
```

**작성 형태(제안):**
```sql
-- serving/schema.sql — SQLite DDL (아키텍처 01 §3-4). CREATE TABLE IF NOT EXISTS 만. 인덱스는 Phase 5.
CREATE TABLE IF NOT EXISTS users (
    user_key   TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    consent    INTEGER NOT NULL DEFAULT 1,
    cell       TEXT,
    is_new     INTEGER NOT NULL DEFAULT 1
);
-- … 나머지 6 테이블 동일 형식. 컬럼 이름은 §3-4 표기 그대로(contracts.Event · Rating · BookStats 필드명과 일치).
```

**패키징 확인(discretion 항목 해소):** hatchling `packages = ["src/millie_rec"]`은 패키지 디렉터리 안의 **non-`.py` 파일을 wheel에 포함**한다 — 스크래치패드에서 `schema.sql` 더미를 넣고 `uv build --wheel`로 실측: wheel 목록에 `millie_rec/serving/schema.sql` 포함됨(2026-09-05). 또한 로컬(`.venv/.../_editable_impl_millie_rec.pth`)·Docker(`uv sync` 기본 = 프로젝트 editable 설치, `COPY src ./src`) 모두 editable이라 `Path(__file__).parent / "schema.sql"`이 `/app/src/millie_rec/serving/schema.sql`로 해석된다. **완료 기준에 `uv build` 단계를 넣을 필요 없음** — `test_smoke.py`가 `Database(tmp_path/…)`로 스키마 적용을 단정하면 충분.

---

### `src/millie_rec/serving/db.py` (repository/adapter, file-I/O)

**Analog:** `scripts/export_millie_serving.py` L71-76(`_write`: `pathlib` + `mkdir(parents=True, exist_ok=True)`), `src/millie_rec/contracts.py` L94-97(경로 상수 3개). 예상 70줄(아키 01 §9-3).

**Imports pattern** (`schemas.py` L8-22 관례 → stdlib / 서드파티 / `millie_rec.contracts` 순, ruff `I` 정렬):
```python
"""SQLite 연결 — thread-local · WAL PRAGMA · schema.sql 적용 · 경로 해석 (아키텍처 01 §3-4)."""

import os
import sqlite3
import threading
from pathlib import Path

from millie_rec.contracts import DB_FILENAME, DIR_DATA_LOCAL, ENV_DATA_DIR

SCHEMA_PATH = Path(__file__).parent / "schema.sql"
PRAGMAS = ("PRAGMA journal_mode=WAL", "PRAGMA busy_timeout=5000", "PRAGMA synchronous=NORMAL")
```

**경로 해석 패턴** (D-08; `contracts.py` L94 주석 "환경변수 해석은 serving/db.py 가 한다"; CLAUDE §4 "환경변수는 `os.environ.get`"만):
```python
def resolve_db_path() -> Path:
    """$DATA_DIR/millie.db 가 있으면 그것, 없으면 contracts.DIR_DATA_LOCAL / millie.db."""
    env = os.environ.get(ENV_DATA_DIR)
    return (Path(env) if env else DIR_DATA_LOCAL) / DB_FILENAME
```

**디렉터리 생성 패턴** (analog `scripts/export_millie_serving.py` L71-73 그대로):
```python
# export_millie_serving.py L71-73
def _write(path: Path, payload: object) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
```
→ `db.py`: `self.path.parent.mkdir(parents=True, exist_ok=True)` 후 `sqlite3.connect(self.path)`.

**Core pattern — thread-local 연결 + 최초 1회 PRAGMA + 스키마 적용** (`.claude/rules/serving.md` L28-30; 클래스 허용 근거 = 주입 대상 `db` 인자, simplicity "클래스는 Protocol 만족 시만"의 실질적 예외이나 `create_app(db=…)` 시그니처가 정본(D-09)):
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

    def apply_schema(self) -> None:
        """schema.sql 을 executescript 로 적용(IF NOT EXISTS → 멱등)."""
        self.connect().executescript(SCHEMA_PATH.read_text(encoding="utf-8"))

    def table_names(self) -> list[str]:
        rows = self.connect().execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ).fetchall()
        return [r[0] for r in rows]

    def row_counts(self) -> dict[str, int]:
        """D-07: 스키마의 모든 테이블 COUNT(*), 0 건도 키 포함."""
        con = self.connect()
        return {t: con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in self.table_names()}

    def ok(self) -> bool:
        try:
            return self.connect().execute("SELECT 1").fetchone()[0] == 1
        except sqlite3.Error:
            return False
```
- `PRAGMA journal_mode=WAL`은 DB 파일에 영구 저장되지만 `busy_timeout`·`synchronous`는 연결 단위이므로 **연결마다** 3개 전부 실행하는 것이 안전(thread-local이라 비용 미미).
- 테이블 이름 f-string은 `sqlite_master`에서 온 값만 쓰므로 인젉션 표면 없음(사용자 입력 아님) — 주석 1줄로 "왜"를 남긴다.
- `backup()`(아키 §9-3 책임 목록)은 Phase 5 몫. Phase 1은 위 5 메서드로 충분(≤70줄).

**Error handling:** 예외 계층 만들지 않음(simplicity). `ok()`만 `sqlite3.Error`를 삼켜 `db_ok=False`로 노출.

---

### `src/millie_rec/serving/fallback.py` (service, transform)

**Analog:** `src/millie_rec/contracts.py` L340-345 `Pipeline` Protocol(구현 대상), L315-320 `Catalog` Protocol(입력), L217-231 `ScoredItem`; `tests/serving/test_schemas.py` L21-32(`ScoredItem` 키워드 인자 조립 예). 예상 60줄(아키 §9-3), Phase 1은 level 3만(D-10).

**만족시킬 Protocol** (`contracts.py` L340-345):
```python
class Pipeline(Protocol):
    """조립된 추천기. evaluation · serving 은 이것만 안다."""

    name: str

    def recommend(self, user: UserState, k: int) -> list[ScoredItem]: ...
```

**입력 Protocol** (`contracts.py` L315-320):
```python
class Catalog(Protocol):
    def meta(self, book_ids: Sequence[int]) -> list[dict]: ...
    def popular(self, categories: Sequence[str] = (), n: int = 50) -> list[int]: ...
    def eligible(self, book_ids: Sequence[int]) -> list[int]: ...
```

**Core pattern** (D-10 · D-02; 상수는 모듈 상단 대문자 — analog `scripts/millie_parse.py` L10-15 `CATEGORY_WHITELIST`·`FORMAT_TOKENS` 스타일):
```python
"""fallback cascade — Phase 1 은 level 3(전역 인기)만. level 1·2 는 Phase 5 에 같은 파일 증분."""

from collections.abc import Sequence

from millie_rec.contracts import FALLBACK_GLOBAL_POP, Catalog, Row, ScoredItem, UserState

TRENDING_ROW_ID = "trending"          # contracts.ROW_IDS 안
TRENDING_TITLE = "지금 많이 읽는 책"  # 백엔드 01 §5 응답 예시 · Phase 5 compose.py 가 재사용
TRENDING_PURPOSE = "fallback"          # contracts.ROW_PURPOSES 안
SOURCE_POPULARITY = "popularity"       # contracts.Candidate.source 주석의 허용값


class GlobalPopularFallback:
    """contracts.Pipeline 구현. catalog 없으면 빈 목록(level 3, 스켈레톤)."""

    name = "fallback"

    def __init__(self, catalog: Catalog | None) -> None:
        self.catalog = catalog

    def recommend(self, user: UserState, k: int) -> list[ScoredItem]:
        if self.catalog is None:
            return []
        ids = [b for b in self.catalog.popular(n=k) if b not in user.seen][:k]
        return [
            ScoredItem(book_id=b, score=float(k - i), source=SOURCE_POPULARITY, position=i,
                       source_channels=(SOURCE_POPULARITY,))
            for i, b in enumerate(ids)
        ]


def trending_row(items: Sequence[ScoredItem]) -> Row:
    """D-02: level 3 응답의 유일한 행. Must 5행 뼈대는 Phase 5 compose.py."""
    return Row(row_id=TRENDING_ROW_ID, title=TRENDING_TITLE, purpose=TRENDING_PURPOSE,
               items=tuple(items), channel_mix={SOURCE_POPULARITY: len(items)} if items else {})
```
- `user.seen`은 `contracts.UserState.seen` 프로퍼티(L131-134) — 시드 제외는 계약이 이미 제공.
- `FALLBACK_GLOBAL_POP` import는 `api.py`가 `RecommendResponse.fallback_level`에 쓸 때 필요 — `fallback.py`가 `level` 상수를 노출하려면 여기서 재수출하지 말고 `api.py`가 `contracts`에서 직접 import(별 의존 그대로).

**Validation / Error handling:** 없음 — 예외는 `api.py`가 감싼다(D-13 안전성: 가짜 fallback이 예외를 던져도 200).

---

### `src/millie_rec/serving/api.py` (controller, request-response)

**Analog:** `src/millie_rec/serving/schemas.py` L14-22(import 관례) · L56-64(`HealthOut`) · L164-187(`RecommendOut.from_contract`); `tests/serving/test_schemas.py` L41-52(`RecommendResponse` 조립). FastAPI 라우터 analog는 저장소에 없음 → 아래 골격은 `.claude/rules/serving.md` L18·L34 + 백엔드 01 §0·§1·§5에서 도출. 예상 90줄(아키 §9-3).

**Imports pattern** (`schemas.py` L8-22 형식 그대로 — stdlib / pydantic·fastapi / `millie_rec.contracts` / 같은 슬라이스 `millie_rec.serving.<x>`):
```python
# schemas.py L8-22 (analog 원문)
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
```
→ `api.py`:
```python
"""FastAPI create_app · lifespan · GET /health · GET /api/recommend (백엔드 서빙 01 §0·§1·§5)."""

import logging
import uuid
from collections.abc import Iterator
from contextlib import asynccontextmanager
from time import perf_counter
from typing import Annotated

from fastapi import FastAPI, HTTPException, Query

from millie_rec.contracts import (
    FALLBACK_GLOBAL_POP,
    MODEL_VERSION_FALLBACK,
    BookStatsSource,
    Catalog,
    Neighbors,
    Pipeline,
    RecommendResponse,
    UserState,
)
from millie_rec.serving.db import Database
from millie_rec.serving.fallback import trending_row
from millie_rec.serving.schemas import API_VERSION, HealthOut, RecommendOut

log = logging.getLogger(__name__)
K_DEFAULT, K_MAX = 40, 100  # 백엔드 01 §0 "k ≤ 100" · §5 "k 기본 40"
ZERO_WEIGHTS = {"alpha": 0.0, "beta": 0.0, "gamma": 0.0}  # §5 "익명은 3, 가중치 전부 0"
```
- `tests/test_architecture.py` L39-40: serving 파일은 `millie_rec.contracts`·`millie_rec.serving.*`만 import — 위 목록이 그 범위 안. `millie_rec.app` import 금지(L37-38).
- `test_no_layer_folders_inside_slices`(L50-63)는 **디렉터리** 이름 `api`만 금지 — 파일 `api.py`는 허용.

**직렬화 표면(변경 금지, 그대로 호출)** — `schemas.py` L56-64 · L181-187:
```python
class HealthOut(_Strict):
    status: str
    api_version: str = API_VERSION
    model_version: str | None = None  # 스켈레톤(Day 2) 은 None
    artifacts_loaded_at: str | None = None
    db_ok: bool
    db_row_count: dict[str, int] = {}
    nearline_last_run: str | None = None
    uptime_s: float

    @classmethod
    def from_contract(cls, r: RecommendResponse, *, forced: bool = False) -> "RecommendOut":
        d: dict[str, Any] = asdict(r)
        d["items"] = [asdict(i) for i in r.items]
        d["rows"] = [asdict(row) for row in r.rows]
        d["forced"] = forced
        return cls.model_validate(d)
```
→ `api.py`는 DTO(`RecommendResponse`)를 만들고 `RecommendOut.from_contract(resp, forced=model is not None)`만 호출한다(로직 중복 금지, CONTEXT '재사용 자산').

**`RecommendResponse` 조립 패턴** — analog `tests/serving/test_schemas.py` L41-52 를 level 3 값으로 치환(D-01~D-04):
```python
# test_schemas.py L41-52 (analog 원문)
    return RecommendResponse(
        items=(Recommendation(book_id=1, score=0.83, title="t"),),
        model_version=f"{VARIANTS[3]}{MODEL_VERSION_SUFFIX}",
        fallback_level=FALLBACK_PERSONALIZED,
        latency_ms=36.3,
        recommendation_id="rec_8f3a2c",
        rows=(row,),
        latency_breakdown={"total": 36.3},
        user_state_weights={"alpha": 1.0},
        user_key="u",
        cell="B",
    )
```
→ Phase 1 level 3:
```python
def _new_rec_id() -> str:
    return "rec_" + uuid.uuid4().hex[:6]  # 백엔드 01 §0 ID 형식 rec_<6hex> (D-03)


def _level3(fallback: Pipeline, user: UserState, k: int, t0: float, context: str | None) -> RecommendResponse:
    try:
        items = fallback.recommend(user, k)
    except Exception:  # noqa: BLE001 — 추천 API 장애 ≠ 메인 장애 (D-13 안전성)
        log.exception("fallback pipeline failed; serving empty trending row")
        items = []
    ms = (perf_counter() - t0) * 1000
    return RecommendResponse(
        items=(),
        model_version=MODEL_VERSION_FALLBACK,
        fallback_level=FALLBACK_GLOBAL_POP,
        latency_ms=ms,
        recommendation_id=_new_rec_id(),
        rows=(trending_row(items),),
        latency_breakdown={"total": ms},
        user_state_weights=dict(ZERO_WEIGHTS),
        context=context,
    )
```
- ruff `select = ["E","F","I","UP","B"]`에는 `BLE`가 없으므로 `noqa: BLE001`은 불필요 — 넣지 말고 주석만("왜").

**Core pattern — `create_app` + lifespan + 동기 `def` 핸들러** (시그니처는 D-09 = `.claude/rules/serving.md` L18 고정; Phase 1에 없는 인자만 `| None = None`):
```python
def create_app(
    pipelines: dict[str, Pipeline],
    fallback: Pipeline,
    catalog: Catalog | None = None,
    db: Database | None = None,
    neighbors: Neighbors | None = None,
    book_stats: BookStatsSource | None = None,
    state=None,
) -> FastAPI:
    """주입만 받는다. 비즈니스 규칙은 슬라이스 함수에."""
    started = {"t": perf_counter()}

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> Iterator[None]:
        db.apply_schema()  # D-06: 행은 쓰지 않는다. 스키마·PRAGMA 만
        started["t"] = perf_counter()
        yield

    app = FastAPI(title="millie-rec", version=API_VERSION, lifespan=lifespan)

    @app.get("/health", response_model=HealthOut)
    def health() -> HealthOut:  # 동기 def — 스레드풀 (serving.md L34)
        return HealthOut(status="ok", db_ok=db.ok(), db_row_count=db.row_counts(),
                         uptime_s=perf_counter() - started["t"])

    @app.get("/api/recommend", response_model=RecommendOut)
    def recommend(
        seeds: Annotated[str | None, Query()] = None,
        k: Annotated[int, Query(ge=1, le=K_MAX)] = K_DEFAULT,
        model: Annotated[str | None, Query()] = None,
        context: Annotated[str | None, Query()] = None,
    ) -> RecommendOut:
        t0 = perf_counter()
        user = UserState(user_id=None, explicit_seeds=_parse_seeds(seeds))
        # Phase 2 가 pipelines["pop"] 을 주입하면 이 분기가 level 0 이 된다 (CONTEXT '통합 지점')
        resp = _level3(fallback, user, k, t0, context)
        return RecommendOut.from_contract(resp, forced=model is not None)

    return app
```
- `Annotated[..., Query(...)]` 형식을 쓴다 — ruff `B008`(기본값에 함수 호출) 회피. `k: int = Query(40)` 형태는 lint 실패 위험.
- `db: Database | None = None`은 시그니처 호환용이지만 Phase 1 호출은 항상 `db=Database(path)`를 넘긴다(D-09). `None` 분기를 만들지 않는다(미래 요구 선제 구현 금지).
- **lifespan 함정:** `TestClient(app)`를 컨텍스트 매니저 없이 쓰면 lifespan이 돌지 않아 `apply_schema()`가 실행되지 않는다 → `test_smoke.py`는 반드시 `with TestClient(app) as client:` 형태(아래 참조). uvicorn(`make serve`·`make smoke`)은 lifespan을 자동 실행.

**Validation pattern** (백엔드 01 §0 오류 규약 "검증 실패 422 {detail:[…]}"):
```python
def _parse_seeds(raw: str | None) -> tuple[int, ...]:
    """'1,2,3' → (1, 2, 3). 정수가 아니면 FastAPI 규약대로 422."""
    if not raw:
        return ()
    try:
        return tuple(int(s) for s in raw.split(",") if s.strip())
    except ValueError as e:
        raise HTTPException(
            status_code=422,
            detail=[{"loc": ["query", "seeds"], "msg": "seeds must be comma-separated integers", "type": "value_error"}],
        ) from e
```

---

### `src/millie_rec/app/server.py` (composition root, request-response)

**Analog:** 없음(조립 코드 첫 파일). 진입점 이름은 `Makefile` L30-31·L34, `Dockerfile` L13이 이미 `millie_rec.app.server:app`으로 고정. 경로 상수는 `contracts.ROOT`(L20, `Path(__file__).resolve().parents[2]` → 로컬 `millie-rec/`, Docker `/app` — `COPY demo ./demo`가 `/app/demo`이므로 일치). Advisor 직접 편집.

**진입점 정본** (`Makefile` L30-31, `Dockerfile` L13):
```make
serve:        ## FastAPI 로컬 서빙 (데모 http://localhost:8000/?source=api). 아티팩트 없어도 뜬다(fallback level 3)
	uv run uvicorn millie_rec.app.server:app --port 8000
```
```dockerfile
CMD ["sh", "-c", "uv run --no-sync uvicorn millie_rec.app.server:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]
```

**Docstring 관례** (`app/__init__.py` L1):
```python
"""조립 전용. 슬라이스 공개 API 를 Pipeline 으로 엮는다. 누구도 app 을 import 하지 않는다."""
```

**Core pattern** (D-09 · D-11; `tests/test_architecture.py` L41-42 "app 은 공개 표면(millie_rec.<slice>)만 import" → `from millie_rec.serving import …` 한 줄, `millie_rec.serving.api` 같은 3단 경로 금지):
```python
"""uvicorn 진입점. create_app 주입 + demo/ StaticFiles 마운트(마지막). CORS 없음 — 같은 origin 이 설계."""

from fastapi.staticfiles import StaticFiles

from millie_rec.contracts import ROOT
from millie_rec.serving import Database, GlobalPopularFallback, create_app, resolve_db_path

app = create_app(pipelines={}, fallback=GlobalPopularFallback(None), db=Database(resolve_db_path()))
app.mount("/", StaticFiles(directory=ROOT / "demo", html=True), name="demo")  # 반드시 마지막
```
- `resolve_db_path`를 공개 표면에 올리는 대신 `Database(path: Path | None = None)`이 내부에서 해석하게 해도 된다 — 어느 쪽이든 **환경변수 해석은 `db.py` 안**(D-08). 전자는 테스트에서 `tmp_path`를 명시적으로 넘기는 D-13 형태와 잘 맞는다.
- `/` 마운트가 라우트 등록 뒤에 와야 `/health`·`/api/*`가 StaticFiles에 가려지지 않는다.

---

### `tests/serving/test_smoke.py` (test, request-response)

**Analog:** `tests/serving/test_schemas.py` 전체(exact — 같은 디렉터리·같은 슬라이스), `tests/test_architecture.py` L1-13(모듈 docstring·상수), `.claude/rules/python-tdd.md` L37(네이밍 `test_<기능>_<시나리오>_<기대결과>`).

**모듈 docstring + import 관례** (`test_schemas.py` L1-17):
```python
"""HTTP 계약 스키마 — 계약 준수(백엔드 01 §5·§6) + 열거값이 contracts 상수로만 검증되는지."""

import pytest
from pydantic import ValidationError

from millie_rec.contracts import (
    BADGE_TYPES,
    FALLBACK_PERSONALIZED,
    MODEL_VERSION_SUFFIX,
    VARIANTS,
    Badge,
    Recommendation,
    RecommendResponse,
    Row,
    ScoredItem,
)
from millie_rec.serving.schemas import EventIn, RecommendOut
```

**단정 스타일** (`test_schemas.py` L55-63 — `model_dump()` dict 위에서 여러 단정을 `and`로 묶음):
```python
def test_recommend_roundtrip_matches_contract_fields():
    out = RecommendOut.from_contract(_response(), forced=True)
    d = out.model_dump()
    assert d["latency_ms"] == 36.3 and isinstance(d["latency_ms"], float)
    assert d["forced"] is True and d["fallback_level"] == 0
```

**Core pattern — D-13 직접 조립 + 3종 테스트** (`tests/`는 무엇이든 import 가능 — `test_architecture.py` 대상은 `src/`만):
```python
"""서빙 스켈레톤 스모크 — 계약(HealthOut·RecommendOut 파싱) · 정확성(level 3 값) · 안전성(예외 → 200)."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from millie_rec.contracts import FALLBACK_GLOBAL_POP, MODEL_VERSION_FALLBACK, ScoredItem, UserState
from millie_rec.serving.api import create_app
from millie_rec.serving.db import Database
from millie_rec.serving.fallback import GlobalPopularFallback
from millie_rec.serving.schemas import HealthOut, RecommendOut

MUST_TABLES = ("users", "preference_snapshots", "events", "recommendations")


class _Boom:
    """recommend 가 항상 예외 — '추천 API 장애 ≠ 메인 장애' 증거용 가짜 Pipeline."""

    name = "boom"

    def recommend(self, user: UserState, k: int) -> list[ScoredItem]:
        raise RuntimeError("boom")


@pytest.fixture
def client(tmp_path: Path):
    app = create_app(pipelines={}, fallback=GlobalPopularFallback(None), db=Database(tmp_path / "millie.db"))
    with TestClient(app) as c:  # with 블록이어야 lifespan(스키마 적용)이 돈다
        yield c


def test_health_returns_200_and_parses_health_out(client):
    r = client.get("/health")
    assert r.status_code == 200
    out = HealthOut.model_validate(r.json())
    assert out.status == "ok" and out.db_ok is True and out.model_version is None


def test_health_db_row_count_has_must_tables(client):
    counts = client.get("/health").json()["db_row_count"]
    assert all(counts.get(t) == 0 for t in MUST_TABLES), counts


def test_schema_creates_must_tables_in_tmp_db(tmp_path: Path):
    db = Database(tmp_path / "millie.db")
    db.apply_schema()
    assert set(MUST_TABLES) <= set(db.table_names())


def test_recommend_without_pipeline_returns_level3_trending(client):
    r = client.get("/api/recommend", params={"seeds": "1,2,3", "k": 5})
    assert r.status_code == 200
    out = RecommendOut.model_validate(r.json())
    assert out.fallback_level == FALLBACK_GLOBAL_POP
    assert out.model_version == MODEL_VERSION_FALLBACK
    assert out.rows[0].row_id == "trending" and out.recommendation_id.startswith("rec_")


def test_recommend_bad_seeds_returns_422(client):
    assert client.get("/api/recommend", params={"seeds": "1,x"}).status_code == 422


def test_recommend_when_fallback_raises_still_200(tmp_path: Path):
    app = create_app(pipelines={}, fallback=_Boom(), db=Database(tmp_path / "millie.db"))
    with TestClient(app) as c:
        r = c.get("/api/recommend", params={"seeds": "1"})
    assert r.status_code == 200 and r.json()["fallback_level"] == FALLBACK_GLOBAL_POP


def test_server_module_serves_demo_index_at_root():
    from millie_rec.app.server import app  # 실제 data/local 경로가 아닌 것을 보장하려면 monkeypatch DATA_DIR

    with TestClient(app) as c:
        r = c.get("/")
    assert r.status_code == 200 and "<html" in r.text.lower()
```
- **함정:** 마지막 테스트가 `millie_rec.app.server`를 import하면 `Database(resolve_db_path())`가 `data/local/millie.db`를 열려 한다(D-13 "실제 `data/local/millie.db`는 테스트가 건드리지 않는다"). 해결: `monkeypatch.setenv("DATA_DIR", str(tmp_path))` **후** `importlib.import_module("millie_rec.app.server")`(모듈 캐시 주의 — `sys.modules.pop` 또는 테스트 파일 안 단 1회 import). `ENV_DATA_DIR` 상수를 쓰면 `monkeypatch.setenv(ENV_DATA_DIR, …)`.
- TDD Red: 위 테스트를 먼저 커밋 대상 트리에 만들고 `uv run pytest tests/serving/test_smoke.py -q --no-header` → `ImportError`는 Red가 아니다(`python-tdd.md` L18). Red를 `AssertionError`로 찍으려면 최소 골격(빈 `create_app`이 아무 라우트도 없는 `FastAPI()` 반환) 상태에서 404 단정 실패를 보여주는 것이 정직한 Red.

---

### `src/millie_rec/contracts.py` (수정 — 상수 1개, Advisor)

**Analog:** 자기 자신 L60-62(`VARIANTS`·`MODEL_VERSION_SUFFIX` 주석 스타일), L84-86(fallback 상수 블록).

**기존 패턴** (L60-62):
```python
# variant 이름의 유일한 정본: 평가표 행 · /recommend?model= · 인스펙터 라디오 · demo mock 파일명
VARIANTS = ("pop", "cf", "hybrid", "hybrid_div")
MODEL_VERSION_SUFFIX = "_v1"  # model_version = f"{variant}{MODEL_VERSION_SUFFIX}"
```

**추가 위치·형태** (D-01; L62 바로 아래 또는 L86 fallback 블록 아래 — "기본값 있는 optional 상수 추가"만, 삭제·개명 없음):
```python
MODEL_VERSION_FALLBACK = "fallback_v1"  # level 3 응답의 model_version. VARIANTS 이름을 빌리지 않는다(숫자 불혼합)
```
- `tests/test_architecture.py::test_contracts_has_no_logic`(L66-70)은 최상위 **함수 정의**만 금지 — 상수 추가는 통과.
- 변경 후 `/codex:review --scope working-tree` 필수(`.claude/rules/codex-review.md` 표 1행).

---

### `src/millie_rec/serving/__init__.py` (수정 — `__all__`)

**Analog:** 자기 자신 L1-5.

**기존 원문**:
```python
"""serving 슬라이스 공개 표면. 다른 슬라이스는 여기 있는 이름만 import 할 수 있다."""

from millie_rec.serving.schemas import API_VERSION, EventIn, RecommendOut

__all__ = ["API_VERSION", "EventIn", "RecommendOut"]
```

**수정 형태** (`app/server.py`가 `from millie_rec.serving import …`로만 접근 — `test_architecture.py` L41-42):
```python
from millie_rec.serving.api import create_app
from millie_rec.serving.db import Database, resolve_db_path
from millie_rec.serving.fallback import GlobalPopularFallback
from millie_rec.serving.schemas import API_VERSION, EventIn, RecommendOut

__all__ = [
    "API_VERSION",
    "Database",
    "EventIn",
    "GlobalPopularFallback",
    "RecommendOut",
    "create_app",
    "resolve_db_path",
]
```
- `__init__`이 `api.py`를 import하므로 `api.py`가 다시 `millie_rec.serving`(패키지)를 import하면 순환 — `api.py`는 반드시 `millie_rec.serving.schemas`·`.db`·`.fallback` **모듈 경로**로 import(위 api.py 패턴대로).

## Shared Patterns

### Import 순서·star 의존
**Source:** `src/millie_rec/serving/schemas.py` L8-22 · `tests/test_architecture.py` L27-43
**Apply to:** `db.py` `fallback.py` `api.py` `server.py` `test_smoke.py`
```python
# test_architecture.py L37-42 — 위반 판정 3종
if target == "app" and top != "app":
    bad.append(f"{rel}: '{mod}' — 누구도 app 을 import 하지 않는다")
elif top in SLICES and target in SLICES and target != top:
    bad.append(f"{rel}: '{mod}' — 슬라이스는 contracts 와 자기 내부만 import 한다")
elif top == "app" and target in SLICES and len(parts) > 2:
    bad.append(f"{rel}: '{mod}' — app 은 공개 표면(millie_rec.{target})만 import 한다")
```
- serving 파일: `millie_rec.contracts` + `millie_rec.serving.<module>`만. `app/server.py`: `millie_rec.contracts` + `millie_rec.serving`(2단)만.
- ruff `I`(isort) + `src = ["src", "tests"]` → `millie_rec`는 first-party 그룹. `UP` → `X | None`(Optional 금지). `B` → 기본값 함수 호출 금지(`Annotated[..., Query()]`로 회피).

### 모듈 헤더 · 상수 · docstring
**Source:** `scripts/export_millie_serving.py` L1-17 · `scripts/millie_parse.py` L1-15 · `contracts.py` L1-6
**Apply to:** 모든 신규 `.py`
```python
"""processed parquet → artifacts/serving/*.json (US-006, 적재 계획 §3·§7).

description·curator_note 는 TF-IDF 입력 전용이므로 서빙 산출물에 넣지 않는다
(밀리 저작 텍스트 화면·API 미노출 규칙).
"""
…
MAX_BYTES = 50 * 1024 * 1024
```
- 1줄(필요 시 2~3줄 "왜") 한국어 docstring + 설계서 § 참조. 설정은 모듈 상단 대문자 상수. 주석은 "왜"만. `logging.getLogger(__name__)` 기본(`scripts/`는 print를 쓰지만 서빙은 `logging` — simplicity.md "로깅은 logging 기본").
- 파일 ≤150줄(`schemas.py`만 예외). 아키 §9-3 예산: `schema.sql` 45 · `db.py` 70 · `api.py` 90 · `fallback.py` 60.

### 계약 DTO 조립 (frozen dataclass, 키워드 인자)
**Source:** `tests/serving/test_schemas.py` L20-52 · `contracts.py` L242-269
**Apply to:** `fallback.py`(`Row`·`ScoredItem`) · `api.py`(`RecommendResponse`)
```python
# contracts.py L254-269 — 필수 4 + optional 나머지
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
    user_key: str | None = None
    cell: str | None = None
    dedup_removed: int = 0
    context: str | None = None
```
- 컬렉션은 **tuple**(`items=()`, `rows=(row,)`), dict는 새 객체. `RecommendOut.from_contract`가 `asdict`로 풀기 때문에 dict를 API 경계로 직접 넘기지 않는다(python.md L11).
- `row_id="trending"`(`ROW_IDS` L65-73 안)·`purpose="fallback"`(`ROW_PURPOSES` L75 안) — `schemas.py` L36-46 검증기를 통과하는 값만 쓴다.

### 경로·환경변수
**Source:** `contracts.py` L20-28 · L94-97 · `Dockerfile` L12
**Apply to:** `db.py` `server.py`
```python
ROOT = Path(__file__).resolve().parents[2]
…
# 런타임 저장 경로. 환경변수 해석은 serving/db.py 가 한다 (contracts 는 I/O 없음)
DIR_DATA_LOCAL = ROOT / "data" / "local"
ENV_DATA_DIR = "DATA_DIR"  # 환경변수 '이름' 상수
DB_FILENAME = "millie.db"
```
- 하드코딩 절대경로 금지(python.md L15). 환경변수는 `os.environ.get(ENV_DATA_DIR)` 한 곳(db.py)에서만. `.gitignore`가 `data/local/`·`*.db`를 이미 제외.

### 테스트 관례
**Source:** `tests/serving/test_schemas.py` · `.claude/rules/python-tdd.md` L35-40 · `.claude/rules/serving.md` L45-46
**Apply to:** `tests/serving/test_smoke.py`
- 위치 미러링 `tests/serving/` ↔ `src/millie_rec/serving/`. 네이밍 `test_<기능>_<시나리오>_<기대결과>`.
- SQLite는 `tmp_path` 파일. 네트워크 없음. 가짜 `Pipeline`으로 Model 레인과 독립.
- 3종: 계약(`HealthOut`·`RecommendOut.model_validate`) · 정확성(`fallback_level==3`·`model_version==MODEL_VERSION_FALLBACK`·`rows[0].row_id=="trending"`·Must 4 테이블) · 안전성(예외 Pipeline → 200, 잘못된 seeds → 422).
- 실행은 `uv run pytest -q`만(`python-tdd.md` L12-18). 전체 30초 이내. 기준선 95 passed, 2 skipped.

### 완료 기준 명령(전 브리프 공통)
**Source:** `Makefile` L33-40 · `.claude/rules/python.md` L16
```make
smoke:        ## 로컬 기동 스모크 — 모든 브리프의 완료 기준(.claude/rules/local-run.md). 서버를 8010 포트로 띄워 3개 확인 후 종료
	@uv run uvicorn millie_rec.app.server:app --port 8010 --log-level warning & echo $$! > .uvicorn.pid; sleep 3; \
	 curl -fsS localhost:8010/health >/dev/null && echo "smoke: /health 200" || ok=0; \
	 curl -fsS -o /dev/null localhost:8010/ && echo "smoke: / (demo static) 200" || ok=0; \
	 curl -fsS "localhost:8010/api/recommend?seeds=1,2,3&k=5" >/dev/null && echo "smoke: /api/recommend 200" || ok=0; \
```
- 순서: `uv run ruff format . && uv run ruff check . && uv run pytest -q` → `make smoke`(3점 PASS). `make smoke`는 `data/local/millie.db`를 실제로 생성한다(gitignore 대상, 정상).

## No Analog Found

| File | Role | Data Flow | Reason | 대체 정본 |
|---|---|---|---|---|
| `src/millie_rec/serving/schema.sql` | migration | file-I/O | 저장소에 `.sql`·DDL 없음 | 아키텍처 01 §3-4 데이터 저장 DDL(위 발췌) |
| `src/millie_rec/serving/api.py`(라우터 부분) | controller | request-response | FastAPI 앱·라우트가 아직 없음 | `.claude/rules/serving.md` L18(`create_app` 시그니처)·L34(동기 `def`) + 백엔드 01 §0·§1·§5 + 위 골격 |
| `src/millie_rec/app/server.py` | composition root | request-response | `app/`에 `__init__.py`만 | `Makefile`·`Dockerfile` 진입점 + `.claude/rules/local-run.md` "서빙 스켈레톤의 최소 형태" + 위 골격 |

## Metadata

**Analog search scope:** `src/millie_rec/**`(contracts·serving·app) · `tests/**` · `scripts/*.py` · `Makefile` `Dockerfile` `pyproject.toml` `.gitignore` `.dockerignore` `railway.json` · `../.claude/rules/{serving,python-tdd,python,architecture,simplicity,local-run}.md` · 설계서 아키텍처 01 §3-2·§3-4·§3-11·§9-3 · 백엔드 서빙 01 §0·§1·§5. `demo/`는 읽지 않음(범위 외).
**Files scanned:** 21 (Python 9 · 설정 6 · 규칙 6) + 설계서 2
**Empirical checks:** hatchling wheel에 `serving/schema.sql` 포함 확인(스크래치패드 `uv build --wheel`, 2026-09-05) · `.venv` editable 설치 확인(`_editable_impl_millie_rec.pth`) · `demo/index.html` 존재 확인(1,040B)
**Pattern extraction date:** 2026-09-05
