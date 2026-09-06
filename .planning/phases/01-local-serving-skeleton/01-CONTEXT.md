# Phase 1: 로컬 서빙 스켈레톤 - Context

**Gathered:** 2026-09-05
**Status:** Ready for planning

<domain>
## Phase Boundary

아티팩트·DB·네트워크·클라우드 없이 `make serve`로 FastAPI 서버가 뜨고, 이후 모든 슬라이스가 "떠 있는 서버에 붙어" 로컬 검증되는 기반을 만든다(walking skeleton, `../.claude/rules/local-run.md`).

이 페이즈가 만드는 것(전부 Must, Should 꼬리 없음):
- `GET /health` → 200, `HealthOut`(`model_version`·`artifacts_loaded_at` null) — **SKEL-01** `make serve` 기동·`/health` 200
- `GET /` → `demo/` 정적 데모가 같은 origin에서 서빙(StaticFiles) — **SKEL-02** 정적 데모 같은 origin 서빙
- `GET /api/recommend?seeds=1,2,3` → 파이프라인 미주입 상태에서 `fallback_level=3` 200(`RecommendOut`) — **SKEL-03** 파이프라인 없을 때 fallback 200 = 수용 기준 '파이프라인 예외 → 인기 row 200'(`../.assets/PRD/PRD_메인_추천_시스템.md` §9 수용 기준 표, AC6)의 최소 형태
- `contracts.DIR_DATA_LOCAL/millie.db` 자동 생성 + `schema.sql` 적용(Must 4테이블 존재) — **SKEL-04** SQLite 자동 생성·Must 4테이블
- `uv run pytest --no-header` + `make smoke`(3점) PASS — **SKEL-05** `make smoke` 3점 확인

쓰기 영역: Worker = `src/millie_rec/serving/{schema.sql,db.py,api.py,fallback.py}` + `tests/serving/test_smoke.py`. Advisor 직접 = `src/millie_rec/app/server.py`, `contracts.py`(상수 1개 추가), 필요 시 `Makefile`.
**건드리지 않는 것:** `demo/` 27파일(Phase 6 '데모 재구성' 몫 — 구 `api.js`가 `hf.space`를 가리키므로 `?source=api`에서 fallback 배너가 뜨는 것이 정상), `serving/schemas*.py`(freeze), 다른 슬라이스.

</domain>

<decisions>
## Implementation Decisions

### fallback 응답 형태 (level 3, 파이프라인·카탈로그 없음)
- **D-01:** `model_version`은 `contracts.MODEL_VERSION_FALLBACK = "fallback_v1"` 상수를 **신설**해 쓴다(Advisor 직접, 기본값 있는 optional 상수 추가라 freeze 규칙 안. `RecommendOut.model_version`은 필수 str이라 null 불가). VARIANTS 이름(`pop_v1` 등)을 빌려 쓰지 않는다 — Track A 비교표 행 이름과의 혼동(숫자 불혼합 원칙) 방지. `contracts.py` 변경이므로 구현 후 `/codex:review --scope working-tree` **필수**(`../.claude/rules/codex-review.md` 표).
- **D-02:** 카탈로그가 없으면 `rows = [Row(row_id="trending", title="지금 많이 읽는 책", purpose="fallback", items=())]`, `items = ()`. Must 5행 뼈대를 미리 내리지 않는다(행 순서 정본은 Phase 5의 `compose.py`). 카탈로그가 주입되면(Phase 3) 같은 `trending` 행에 `catalog.popular()` 결과가 채워진다.
- **D-03:** level 3 응답에도 `recommendation_id = "rec_" + 6hex`(uuid4 기반)를 **매 응답 발급**한다(백엔드 서빙 01 §0 ID 규약). `recommendations` 테이블 기록은 Phase 5 몫 — Phase 1은 발급만.
- **D-04:** (문서 확정 사항, 재확인) `fallback_level = contracts.FALLBACK_GLOBAL_POP`(3), `user_state_weights`는 전부 0(백엔드 01 §5 "익명은 3, 가중치 전부 0"), `latency_ms`는 `perf_counter` 실측 float, `latency_breakdown = {"total": …}`, `forced`는 `model` 쿼리 유무, `cell`·`user_key`·`preference_snapshot_id`는 null(셀 배정은 Phase 5).

### SQLite 스켈레톤 범위
- **D-05:** `schema.sql`은 **Must 4 + Should 3 전부**(`users`·`preference_snapshots`·`events`·`recommendations` + `ratings`·`candidate_sets`·`book_stats`)를 아키텍처 01 §3-4 DDL 그대로 `CREATE TABLE IF NOT EXISTS`로 쓴다. Phase 5에서 DDL을 다시 건드리지 않기 위함. **검증(SKEL-04)은 Must 4만** 단정한다.
- **D-06:** Phase 1의 서버는 SQLite에 **행을 쓰지 않는다**(스키마 적용·PRAGMA·연결만). 추천 로그·`users` 행은 Phase 5 '서빙 Must 완성'(SERV-06 노출 로그)의 몫.
- **D-07:** `/health.db_row_count`는 **`schema.sql`에 있는 테이블 전부의 `COUNT(*)`**를 내고 0건도 키를 포함한다. 테이블 존재의 관측 가능한 증거이자, 배포 02 §3-2 "events 엔드포인트가 없으면 `/health`의 `db_row_count`로 볼륨 영구성 확인"의 전제.
- **D-08:** (문서 확정 사항, 재확인) 표준 `sqlite3`, `threading.local()` 연결, 최초 1회 `PRAGMA journal_mode=WAL; busy_timeout=5000; synchronous=NORMAL`. 경로는 환경변수 `contracts.ENV_DATA_DIR`(`DATA_DIR`)가 있으면 `$DATA_DIR/millie.db`, 없으면 `contracts.DIR_DATA_LOCAL / contracts.DB_FILENAME`. 디렉터리는 `mkdir(parents=True, exist_ok=True)`. 해석은 `db.py`만(`contracts`는 I/O 없음).

### create_app 주입 표면
- **D-09:** `create_app` 시그니처는 `../.claude/rules/serving.md`의 인자 이름·순서를 그대로 유지한다. **(2026-09-05 아키텍트 리뷰 W-1 채택)** `fallback` 뒤는 keyword-only(`*`)이고 `db: Database`는 기본값 없는 필수 인자다 — `catalog=None` 뒤에 필수 위치 인자를 둘 수 없다는 파이썬 제약을 `db=None`으로 회피하지 않는다. 원문: — `create_app(pipelines: dict[str, Pipeline], fallback: Pipeline, catalog: Catalog | None = None, db: Database, neighbors: Neighbors | None = None, book_stats: BookStatsSource | None = None, state=None) -> FastAPI`(인자 이름·순서 유지, Phase 1에 없는 것만 `| None = None` 기본값). Phase 1 호출은 `create_app(pipelines={}, fallback=GlobalPopularFallback(None), db=Database(path))`. Phase 5가 인자를 채울 때 시그니처 변경 없음. `app/`에 빈 스텁 구현을 두지 않는다.
- **D-10:** level 3 로직은 `serving/fallback.py`의 **`contracts.Pipeline` 구현체** `GlobalPopularFallback(catalog: Catalog | None)`(`name = "fallback"`, `recommend(user, k)` → catalog 없으면 `[]`, 있으면 `catalog.popular()` 상위 k를 `ScoredItem(source="popularity")`로)이며, `api.py`가 이를 `RecommendResponse`(D-02 rows)로 감싸 `RecommendOut.from_contract`로 직렬화한다. level 1(캐시)·2(세그먼트 인기) cascade는 Phase 5에 **같은 파일에 증분**.
- **D-11:** `app/server.py`에 CORS 미들웨어를 넣지 않는다(같은 origin 설계가 곧 증거, 아키텍처 01 §9-3). `server.py` = `create_app(...)` 호출 + `StaticFiles(directory=<ROOT>/demo, html=True)`를 **마지막에** `/`로 마운트 + uvicorn 진입점 `app` 객체. 비즈니스 규칙 없음.

### 검증·완료 형태
- **D-12:** SKEL-04 판정 = `tests/serving/test_smoke.py`가 `tmp_path` DB에서 Must 4테이블 존재를 단정 + `/health` 응답의 `db_row_count` 키에 Must 4테이블이 있음을 단정. `make smoke`는 SKEL-05 문구 그대로 **3점 유지**(Makefile·REQUIREMENTS 불변).
- **D-13:** `test_smoke.py`는 `create_app(pipelines={}, fallback=GlobalPopularFallback(None), db=Database(tmp_path / "millie.db"))`를 **직접 조립**해 serving 레인 단독으로 검증하고(계약: `HealthOut`·`RecommendOut` 파싱 / 정확성: `fallback_level==3`·`model_version==MODEL_VERSION_FALLBACK`·`rows[0].row_id=="trending"` / 안전성: `recommend`가 예외를 던지는 가짜 Pipeline을 `fallback`으로 주입해도 200), 별도 1건이 `millie_rec.app.server:app`을 import해 `GET /` 200(StaticFiles·index.html)을 확인한다. 실제 `data/local/millie.db`는 테스트가 건드리지 않는다. TDD: Red는 `AssertionError`로 확인(`../.claude/rules/python-tdd.md`).
- **D-14:** Phase 1 검증 통과 후 **로컬 커밋 1개, push 없음**(사용자 승인 후 실행). 커밋 전 `git ls-files | grep -iE "pdf|png|assets"` 빈 결과 확인. 원격 레포(`origin` = github.com/ShinWon-Chul/millie-rec, 09-05 오전 생성·스캐폴드 push 완료)로의 push는 별도 승인. `.gitignore`의 `data/local/`·`*.db`는 09-05 오전 다른 세션이 이미 추가함(확인됨).

### Claude's Discretion
- `seeds` 쿼리 파싱(정수 CSV, 잘못된 값은 FastAPI 422 — 백엔드 01 §0 오류 규약), `k` 기본 40·상한 100, `context` echo.
- `db_ok` 판정 방식(`SELECT 1` + 스키마 적용 성공), `uptime_s` 기준(프로세스 시작 `perf_counter`), `status` 문자열은 `"ok"`.
- lifespan 구성(스키마 적용·시작 시각 기록만. Nearline·리플레이·아티팩트 로드는 Phase 5), FastAPI 메타(`title`, `version=API_VERSION` — `/docs` 캡처용).
- `schema.sql` 로딩 방식(`Path(__file__).parent / "schema.sql"`)과 **패키지 포함 여부 확인**(hatchling wheel이 `.sql`을 포함하는지 — Dockerfile이 `uv sync`로 설치하므로 빠지면 배포 시점에만 드러난다. `uv build` 또는 설치본 경로 확인을 완료 기준에 넣을지 planner 판단).
- 인덱스(`events(user_key, ts)` 등) 추가 시점 — Phase 1은 DDL만, Phase 5에서 필요 시.
- 행 제목 문자열("지금 많이 읽는 책")의 상수 위치 — `fallback.py` 모듈 상단 상수로 두고 Phase 5 `compose.py`가 같은 슬라이스 안에서 재사용.
- 브리프 분할 — 권장 Worker 1명(`schema.sql`+`db.py`+`fallback.py`+`api.py`+`test_smoke.py`, 각 ≤150줄) + Advisor `server.py`·`contracts` 상수·`make smoke`. 파일 의존(api→db·fallback)이 있어 2명 병렬의 이득이 작다. 최종은 planner 판단.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.** 경로는 `millie-rec/` 기준 상대 경로.

### 계약·규칙 (코드 정본)
- `src/millie_rec/contracts.py` — `FALLBACK_GLOBAL_POP`·`BUDGET_MS`·`ROW_IDS`·`DIR_DATA_LOCAL`·`ENV_DATA_DIR`·`DB_FILENAME`·`RecommendResponse`·`Row`·`ScoredItem`·`Pipeline`·`Catalog` Protocol. **D-01의 `MODEL_VERSION_FALLBACK` 상수는 Advisor가 추가**(optional 상수 추가만 허용, 결정 '두 계약 Day 1 freeze'(../.assets/개발일지/2026-09-04_Day0.5_브레인스토밍과_데모명세.md 항목 D44))
- `src/millie_rec/serving/schemas.py` — `HealthOut`(§1)·`RecommendOut.from_contract`(§5). **변경 금지**
- `tests/serving/test_schemas.py` — `_response()` 헬퍼: `RecommendResponse` 조립 예시(test_smoke.py 작성 패턴)
- `tests/test_architecture.py` — star 의존 검사. `serving`은 `millie_rec.contracts`와 자기 내부만 import, `app`은 `from millie_rec.serving import …` 공개 표면만. **테스트를 고치지 않는다**
- `../.claude/rules/serving.md` — `create_app` 시그니처·파일 분할·SQLite PRAGMA·동기 핸들러·fallback 규칙·테스트 목록
- `../.claude/rules/local-run.md` — 스켈레톤 최소 형태(`app/server.py`·`api.py`·`db.py`·`tests/serving/test_smoke.py`)·`make smoke`
- `../.claude/rules/architecture.md` — 레인·슬라이스·import·산출물 소유권(`$DATA_DIR/millie.db`는 serving 소유, `serving/db.py`로만)
- `../.claude/rules/python-tdd.md` — `uv run pytest`만, Red = `AssertionError`, 3종 테스트
- `../.claude/rules/simplicity.md` — 파일 ≤150줄, 함수 우선, 클래스는 Protocol 만족 시만(D-10 `GlobalPopularFallback`이 그 경우)
- `../.claude/rules/codex-review.md` — `contracts.py` 변경 시 `/codex:review --scope working-tree` 필수
- `../.claude/rules/references.md` — 약호 단독 금지, 이름 + 경로 표기

### 설계서 (Phase 1 착수 전 ① 전수 조사 대상 절)
- `../.assets/설계서/시스템 아키텍처, 기술 스택 및 배포(프론트, 백엔드 서빙)/01_시스템_아키텍처_기술스택_배포.md` §3-2 API 계층(`create_app` 시그니처·주입 순서·`/health`·`/api/recommend` 역할) · §3-4 데이터 저장(SQLite DDL 7테이블·연결 전략·경로) · §3-11 fallback cascade·이벤트 루프(동기 `def`·`--workers 1`) · §9-3 serving 파일 분할(`schema.sql` 45줄·`db.py` 70·`api.py` 90·`fallback.py` 60)
- `../.assets/설계서/백엔드 서빙/01_백엔드_서버_구성.md` §0 공통 규약(접두어·`ts`·ID 형식 `rec_<6hex>`·오류 규약·`k ≤ 100`) · §1 `GET /health`(스켈레톤은 `model_version: null`·`artifacts_loaded_at: null`) · §5 `GET /api/recommend`(쿼리·응답 JSON·level 3 규칙)
- `../.assets/설계서/시스템 아키텍처, 기술 스택 및 배포(프론트, 백엔드 서빙)/02_배포_절차_및_설정.md` §3-2 검증 — `/health.db_row_count`로 볼륨 영구성 확인(D-07의 근거), `DATA_DIR=/data` 변수
- `../.assets/설계서/구현 마일스톤/01_마일스톤_착수_프롬프트.md` §0 착수 전 4단계 · §1 현재 구현 인벤토리 · "마일스톤 '로컬 서빙 스켈레톤'" 절(브리프 원문·완료 기준)
- `../.assets/PRD/PRD_메인_추천_시스템.md` §9 수용 기준 표 — '파이프라인 예외 → 인기 row 200'(AC6)
- `.planning/ROADMAP.md` "Phase 1: 로컬 서빙 스켈레톤" · `.planning/REQUIREMENTS.md` SKEL-01~05

### 빌드·배포 (읽기만, Phase 1 변경 없음)
- `Makefile` — `serve`(8000)·`smoke`(8010, 3점)는 이미 `millie_rec.app.server:app`을 가리킴
- `Dockerfile` — 같은 진입점, `ENV DATA_DIR=/data`, 두 번째 `uv sync`(src-layout 설치 → `schema.sql` 패키지 포함 여부가 여기서 드러남)
- `pyproject.toml` — hatchling `packages = ["src/millie_rec"]`, dev `httpx`(TestClient 의존) 이미 포함. 의존성 추가 없음

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `serving/schemas.py`: `HealthOut`, `RecommendOut.from_contract(RecommendResponse)` — api.py는 DTO를 만들고 이 메서드로만 직렬화한다(로직 중복 금지)
- `contracts.py`: `RecommendResponse(items, model_version, fallback_level, latency_ms, recommendation_id, rows, latency_breakdown, user_state_weights, …)`, `Row(row_id, title, purpose, items, channel_mix)`, `UserState(user_id=None, explicit_seeds=seeds)`, `Pipeline` Protocol(`name`, `recommend(user, k)`)
- `tests/serving/test_schemas.py::_response()` — `RecommendResponse` 조립 예시
- `tests/conftest.py` — 합성 fixture(이 페이즈엔 불필요, 건드리지 않음)
- 기준선: `uv run pytest --no-header` **93 passed, 2 skipped**(HEAD 8e5172b, 2026-09-05 재측정 — 첫 정찰의 95는 skipped 2건을 passed 에 합산한 오기), Python 3.11.6(착수 전 ④ 충족). 주의: pyproject `addopts="-q"` 가 이미 있어 CLI 에 `-q` 를 더 붙이면 `-qq` 로 요약 줄이 사라진다 — 테스트 명령은 `uv run pytest <대상> --no-header`

### Established Patterns
- star 의존: `serving/*`는 `from millie_rec.contracts import …`와 `from millie_rec.serving.<x> import …`만. `app/server.py`는 `from millie_rec.serving import create_app, Database, GlobalPopularFallback`처럼 **공개 표면만** — 따라서 `serving/__init__.py`의 `__all__`에 `create_app`·`Database`·`GlobalPopularFallback` 추가 필요(Worker 범위)
- `schemas.py` 열거값 검증은 `contracts` 상수로만 — `row_id="trending"`·`purpose="fallback"`은 이미 허용 집합 안
- 파일 ≤150줄, docstring 1줄, 설정은 모듈 상단 대문자 상수, `logging` 기본
- 현재 저장소는 `serving/schemas*.py`·`__init__.py`만 있고 `api.py`·`db.py`·`fallback.py`·`schema.sql`·`app/server.py` **전부 신규**(재구성 대상 없음)

### Integration Points
- `app/server.py`(신규, Advisor): `app = create_app(pipelines={}, fallback=GlobalPopularFallback(None), db=Database(<resolved path>))` → `app.mount("/", StaticFiles(directory=ROOT/"demo", html=True))` 마지막. `uvicorn millie_rec.app.server:app`
- Phase 2 'Track A 정량 평가 기반'이 `pipelines["pop"]`을 주입하면 `/api/recommend`가 level 0으로 바뀐다 — Phase 1의 `pipelines` dict 분기가 그 자리
- Phase 3 '밀리 카탈로그 빌드'가 `catalog=catalog_kr`을 주입하면 D-02의 빈 `trending` 행이 밀리 인기 도서로 채워진다
- Phase 5 '서빙 Must 완성'은 `api.py`(엔드포인트 추가는 `demo_api.py`·`privacy_api.py` 별 파일)·`fallback.py`(level 1·2)·`state.py`·`nearline.py`로 증분. Phase 1 시그니처(D-09)가 그대로 유효해야 한다
- `Makefile smoke`가 8010 포트에서 같은 `data/local/millie.db`를 연다(WAL·busy_timeout으로 `serve`와 공존)
- 09-05 오전 **다른 세션**이 스캐폴드 커밋(`8e5172b`)을 `origin/main`에 push했고 `.gitignore`에 `data/local/`·`*.db`를 추가함. 이 세션의 `.planning/phases/01-local-serving-skeleton/01-DISCUSS-CHECKPOINT.json`도 그 커밋에 포함됨 → CONTEXT.md 확정 시 삭제(`git rm`)

</code_context>

<specifics>
## Specific Ideas

- **Phase 1 `/health` 기대 응답 예시**
  ```json
  {"status":"ok","api_version":"v2","model_version":null,"artifacts_loaded_at":null,"db_ok":true,
   "db_row_count":{"users":0,"preference_snapshots":0,"events":0,"recommendations":0,"ratings":0,"candidate_sets":0,"book_stats":0},
   "nearline_last_run":null,"uptime_s":12.3}
  ```
- **Phase 1 `GET /api/recommend?seeds=1,2,3&k=5` 기대 응답 예시**
  ```json
  {"recommendation_id":"rec_8f3a2c","model_version":"fallback_v1","preference_snapshot_id":null,"user_key":null,"cell":null,
   "forced":false,"fallback_level":3,"context":null,"latency_ms":0.4,"latency_breakdown":{"total":0.4},
   "user_state_weights":{"alpha":0.0,"beta":0.0,"gamma":0.0},"dedup_removed":0,"nearline_lag_s":null,
   "items":[],"rows":[{"row_id":"trending","title":"지금 많이 읽는 책","purpose":"fallback","items":[],"subtitle":null,"channel_mix":{}}]}
  ```
- 브라우저 확인: `make serve` 후 `http://localhost:8000/?source=api`에서 구 데모가 **fallback 배너와 함께** 뜨면 정상(구 `api.js`가 `hf.space`를 가리킴). `?source=mock`은 mock 완주. 콘솔 에러 0은 Phase 6 기준이라 Phase 1에선 요구하지 않는다.
- "추천 API 장애 ≠ 메인 장애"의 코드 증거 = 예외를 던지는 가짜 `fallback` Pipeline을 주입해도 `/api/recommend`가 200(D-13 안전성 테스트). 이 테스트 이름은 PDF P5 문장의 근거로 `report/draft.md`에 한 줄 남길 수 있다(Advisor 몫).

</specifics>

<deferred>
## Deferred Ideas

- **SQLite 쓰기(추천 로그·`users` 행·셀 배정 sha256)** → Phase 5 '서빙 Must 완성'(SERV-04·SERV-06). Phase 1은 스키마만(D-06).
- **fallback level 1(캐시)·2(세그먼트 인기) cascade·`state.py`** → Phase 5(SERV-03). `fallback.py`에 같은 파일 증분(D-10).
- **CORS(localhost:8080)** → 필요해지면 Phase 6 '데모 재구성'에서. 같은 origin이 설계(D-11).
- **Should 3 테이블(`ratings`·`candidate_sets`·`book_stats`) 사용** → Phase 5(SERV-12·SERV-14)·Phase 4(BookStatsSource). Phase 1은 DDL만(D-05).
- **`make smoke` 4번째 점(테이블 확인)** → 채택하지 않음. `/health.db_row_count`와 pytest로 대체(D-12).
- **`origin/main` push** → 사용자 승인 시점에 별도(D-14). Phase 7 '배포' Day 2 스켈레톤 배포는 push가 전제.
- **PROGRESS 미결 8 '난이도 4층 피처 contracts 반영'의 optional 필드 여부** → Phase 4 계획에서. 이 페이즈 무관.

- **`db.py` thread-local 커넥션 `close()`·lifespan shutdown 훅** → Phase 5 '서빙 Must 완성'에서 Nearline·쓰기가 붙을 때 재검토(아키텍트 리뷰 I-3, 2026-09-05). Phase 1은 WAL 단일 볼륨이라 무해.
- **`contracts.ROOT = parents[2]`가 editable 설치 전제** → 비-editable 휠이면 `ROOT/"demo"`가 site-packages 밖을 가리켜 StaticFiles가 기동 시 죽는다. Phase 7 '배포'에서 `Dockerfile`에 `--no-editable`을 넣지 않는다는 주석 1줄(아키텍트 리뷰 I-2).
- **wheel에 `schema.sql` 포함 확인 단계** → 채택하지 않음. `01-PATTERNS.md`가 `uv build --wheel`로 이미 실측(포함됨), 로컬·Docker 모두 editable.

### Reviewed Todos (not folded)
없음 — `todo match-phase 1` 결과 0건.

</deferred>

---

*Phase: 01-local-serving-skeleton*
*Context gathered: 2026-09-05*
