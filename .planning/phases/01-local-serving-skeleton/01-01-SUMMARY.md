---
phase: 01-local-serving-skeleton
plan: 01
subsystem: serving
tags: [fastapi, sqlite, fallback, walking-skeleton, tdd]
requires: []
provides:
  - "millie_rec.serving.create_app (pipelines·fallback·db 주입, GET /health · GET /api/recommend)"
  - "millie_rec.serving.Database · resolve_db_path (SQLite 연결·PRAGMA·schema.sql 적용·경로 해석)"
  - "millie_rec.serving.GlobalPopularFallback (contracts.Pipeline 구현, level 3)"
  - "millie_rec.contracts.MODEL_VERSION_FALLBACK = \"fallback_v1\""
affects:
  - "Plan 02 (app/server.py) — from millie_rec.serving import create_app, Database, GlobalPopularFallback, resolve_db_path"
  - "Phase 2 'Track A 정량 평가 기반' — pipelines[\"pop\"] 주입 지점(api.py recommend 핸들러 주석)"
  - "Phase 5 '서빙 Must 완성' — fallback.py level 1·2 증분, db.py 쓰기, api.py 시그니처 유지"
tech-stack:
  added: []   # 의존성 추가 0 (fastapi·uvicorn·httpx 는 기존)
  patterns:
    - "create_app + asynccontextmanager lifespan + 동기 def 핸들러(스레드풀)"
    - "threading.local() 스레드당 SQLite 연결 1개 + 연결마다 PRAGMA 3종"
    - "Annotated[..., Query()] 로 ruff B008 회피"
    - "RecommendOut.from_contract 로만 직렬화(로직 중복 금지)"
key-files:
  created:
    - src/millie_rec/serving/schema.sql
    - src/millie_rec/serving/db.py
    - src/millie_rec/serving/fallback.py
    - src/millie_rec/serving/api.py
    - tests/serving/test_smoke.py
  modified:
    - src/millie_rec/contracts.py
    - src/millie_rec/serving/__init__.py
decisions:
  - "D-01 MODEL_VERSION_FALLBACK 상수 신설 — VARIANTS 이름을 빌리지 않아 Track A 비교표 행과 혼동 방지"
  - "D-09 + 아키텍트 리뷰 W-1 — create_app 의 fallback 뒤는 keyword-only, db: Database 는 기본값 없는 필수 인자"
  - "ruff format(line-length 100) 이 contracts.py 상수 줄을 3줄로 감싸 주석을 줄여 1줄 유지 — 플랜 수용 기준 `1\t0` 충족"
metrics:
  tasks: 3
  files-created: 5
  files-modified: 2
  tests-added: 10
  suite: "103 passed, 2 skipped"
  completed: 2026-09-05
---

# Phase 1 '로컬 서빙 스켈레톤' Plan 01: 서빙 스켈레톤(create_app · SQLite · level 3 fallback) Summary

**한 줄:** 파이프라인·카탈로그·아티팩트·네트워크 없이 `create_app(pipelines={}, fallback=GlobalPopularFallback(None), db=Database(path))` 가 `GET /health` 200(`HealthOut`, Must 4테이블 `db_row_count` 0)과 `GET /api/recommend` 200(`fallback_level=3`, `model_version="fallback_v1"`, `trending` 1행)을 내고, 예외를 던지는 Pipeline 을 주입해도 500 이 아닌 200 을 유지한다.

## RED (Task 1)

`contracts.py` 상수 1줄 추가 후, 시그니처만 있고 값은 틀린 스텁 4파일(`schema.sql` 주석 1줄 · `db.py` 빈 반환 · `fallback.py` 빈 목록 · `api.py` 라우트 0개 `FastAPI()`)을 먼저 두고 `tests/serving/test_smoke.py` 10건을 작성했다. 스텁을 둔 이유는 모듈이 없으면 `ModuleNotFoundError` 로 죽어 RED 가 아니기 때문(`../.claude/rules/python-tdd.md`).

실패 사유:
- 라우트가 없어 `/health`·`/api/recommend` 가 404 → 상태 코드 단정 실패 (HTTP 6건)
- `Database.table_names()` 가 `[]`, `ok()` 가 `False` → Must 4테이블·`db_ok` 단정 실패
- `resolve_db_path()` 가 `Path()` → 경로 단정 실패
- `GlobalPopularFallback(_FakeCatalog()).recommend(...)` 가 `[]` → `[2,3,4,5]` 단정 실패

`ImportError`·`ModuleNotFoundError`·`NotImplementedError`·`KeyError`·`SyntaxError` 0건(grep 실측), 예상외 통과(unexpected GREEN) 0건. `tests/test_architecture.py` 는 스텁 상태에서도 3 passed.

## GREEN (Task 2)

- **`schema.sql`** — 아키텍처 01 §3-4 데이터 저장 DDL 7테이블(Must 4 `users`·`preference_snapshots`·`events`·`recommendations` + Should 3 `ratings`·`candidate_sets`·`book_stats`)을 `CREATE TABLE IF NOT EXISTS` 로. 제약은 PRIMARY KEY 만, 인덱스 0, `NOT NULL` 0(Phase 5 쓰기 규칙을 선결하지 않음).
- **`db.py`** — `resolve_db_path()`(`os.environ.get(ENV_DATA_DIR)` → `$DATA_DIR/millie.db`, 없으면 `contracts.DIR_DATA_LOCAL/millie.db`), `Database`(`threading.local()` 연결 · 연결마다 `journal_mode=WAL`·`busy_timeout=5000`·`synchronous=NORMAL` · `executescript` 멱등 적용 · `sqlite_master` 기준 `table_names`/`row_counts` · `SELECT 1` 기반 `ok()`). 행 쓰기 0(`INSERT` grep 0건, D-06).
- **`fallback.py`** — `contracts.Pipeline` 구현 `GlobalPopularFallback`(catalog 없으면 `[]`, 있으면 `catalog.popular()` 에서 `UserState.seen` 제외 후 상위 k 를 `ScoredItem(source="popularity", source_channels=("popularity",), position=i)` 로) + `trending_row()`(`row_id="trending"` · `title="지금 많이 읽는 책"` · `purpose="fallback"`).
- **`api.py`** — `create_app`(lifespan 에서 `db.apply_schema()` + 시작 시각 기록), `GET /health`(동기 `def`), `GET /api/recommend`(`k` `Query(ge=1, le=100)`, `model ∉ VARIANTS` → 422, `seeds` 정수 CSV 파싱 실패 → 422, `_fallback_response` 가 `except Exception` 으로 파이프라인 예외를 흡수해 빈 `trending` 행으로 200, `recommendation_id = "rec_" + 6hex`, `user_state_weights` 전부 0, `latency_breakdown={"total": …}`), 직렬화는 `RecommendOut.from_contract` 만.

## REFACTOR (Task 3)

- `serving/__init__.py` 공개 표면을 3 → 7 이름으로 확장(`API_VERSION`·`Database`·`EventIn`·`GlobalPopularFallback`·`RecommendOut`·`create_app`·`resolve_db_path`). `api.py` 가 패키지가 아니라 `millie_rec.serving.db`·`.fallback`·`.schemas` **모듈 경로**를 import 하므로 순환 없음(`import millie_rec.serving` 실행 확인).
- `uv run ruff format` + `uv run ruff check src tests` → `All checks passed!`. 행동 변경 없음(상수·시그니처·응답 값 불변).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `ruff format` 이 `contracts.py` 상수 줄을 3줄로 감쌈**
- **Found during:** Task 3-b (`uv run ruff format`)
- **Issue:** 플랜 1-a 가 지정한 주석을 그대로 쓰면 줄 길이가 105자 → ruff `line-length = 100`(pyproject.toml `[tool.ruff]`)에 걸려 `MODEL_VERSION_FALLBACK = (\n    "fallback_v1"  # …\n)` 3줄로 재포맷됐다. 이 상태로는 플랜 수용 기준 `git diff --numstat src/millie_rec/contracts.py` == `1\t0` 과 artifact `contains: MODEL_VERSION_FALLBACK = "fallback_v1"`(1줄 리터럴)을 동시에 만족할 수 없다.
- **Fix:** 주석을 `# level 3 응답의 model_version.` → `# level 3 응답.` 로 줄여 82자 1줄로 복원. 상수 이름·값은 플랜 그대로.
- **Files modified:** `src/millie_rec/contracts.py`
- **Result:** `git diff --numstat src/millie_rec/contracts.py` = `1	0`, `ruff format --check` exit 0.
- **Commit:** 없음(커밋 금지 플랜)

그 외 편차 없음 — Task 1·2 의 코드는 플랜 원문 그대로 사용했다.

## TDD Gate Compliance

커밋 게이트(`test(...)` RED · `feat(...)` GREEN)는 **프로젝트 커밋 정책으로 생략**했다(플랜 frontmatter `no_commit: true`; `../CLAUDE.md` §6 "커밋/푸시는 항상 사용자 승인 후"; 사용자 지시 2026-09-05 "아직 커밋 진행하지 않습니다"). 대체 증거 = `uv run pytest` 출력:

**RED (Task 1)**
```
10 failed, 2 warnings in 0.24s
```
```
    def test_recommend_invalid_query_returns_422(client):
>       assert client.get("/api/recommend", params={"seeds": "1,x"}).status_code == 422
E       AssertionError: assert 404 == 422
E        +  where 404 = <Response [404 Not Found]>.status_code
E        +    where <Response [404 Not Found]> = get('/api/recommend', params={'seeds': '1,x'})
tests/serving/test_smoke.py:136: AssertionError
```
`passed` 0건, 금지 오류(`ImportError`·`ModuleNotFoundError`·`NotImplementedError`·`KeyError`·`SyntaxError`) grep 0건, 단정 실패 표현(`AssertionError` 또는 `E assert …`) 20행.

**GREEN (Task 2)**
```
10 passed, 2 warnings in 0.22s
```

**전체 스위트 (Task 3)**
```
103 passed, 2 skipped, 2 warnings in 1.23s
```
기준선 93 passed / 2 skipped(HEAD `8e5172b`) + 신규 10 = 103. 기존 테스트 실패 0.
`uv run pytest tests/test_architecture.py --no-header` → `3 passed` (RED 단계·GREEN 단계 모두).

## 변경 파일 (`git status --short -- src tests`)

```
 M src/millie_rec/contracts.py
 M src/millie_rec/serving/__init__.py
?? src/millie_rec/serving/api.py
?? src/millie_rec/serving/db.py
?? src/millie_rec/serving/fallback.py
?? src/millie_rec/serving/schema.sql
?? tests/serving/test_smoke.py
```

허용 경로 7개 정확히 일치. `git diff --stat -- demo src/millie_rec/serving/schemas.py src/millie_rec/serving/schemas_should.py tests/test_architecture.py tests/serving/test_schemas.py Makefile pyproject.toml Dockerfile` = **빈 출력**. `data/local/` 은 생성되지 않았다(테스트가 `tmp_path` 만 사용).

## 줄 수 (`wc -l`)

| 파일 | 줄 | 예산 |
|---|---|---|
| `src/millie_rec/serving/db.py` | 60 | ≈70 ✅ |
| `src/millie_rec/serving/fallback.py` | 45 | ≈60 ✅ |
| `src/millie_rec/serving/api.py` | 128 | ≈90~110 (≤150 ✅) |
| `src/millie_rec/serving/schema.sql` | 35 | ≈45~60 ✅ |
| `src/millie_rec/serving/__init__.py` | 16 | — |
| `tests/serving/test_smoke.py` | 146 | min 60 ✅ |

`.py` 전부 ≤150줄. `api.py` 는 권장 110 을 18줄 초과했으나 상한 150 이내이며, 관심사는 하나(HTTP 표면)라 분할하지 않았다.

## Requirements

| ID | 상태 | 근거 |
|---|---|---|
| SKEL-01 | 코드·테스트 충족 | `test_health_returns_200_and_parses_health_out` (서버 기동 `make serve` 확인은 Plan 02) |
| SKEL-03 | 충족 | `test_recommend_without_pipeline_parses_recommend_out_level3` · `test_recommend_level3_has_single_trending_row_and_rec_id` · `test_recommend_when_fallback_raises_still_200_level3` |
| SKEL-04 | 충족 | `test_database_apply_schema_creates_must_tables` · `test_health_db_row_count_has_must_tables_at_zero` · `test_resolve_db_path_prefers_env_then_local_default` |

## Known Stubs

없음. `create_app` 의 `pipelines`·`catalog`·`neighbors`·`book_stats`·`state` 는 시그니처 유지용 미사용 인자이며(D-09, Phase 2·3·5 가 채운다) 스텁 로직·`None` 분기를 두지 않았다 — 값이 주입되지 않은 상태의 정의된 동작이 level 3 fallback 이다.

## 커밋

**커밋 없음** — Advisor 가 `/codex:review --scope working-tree` 후 사용자 승인으로 커밋 (`contracts.py` 변경이므로 `../.claude/rules/codex-review.md` 표 1행에 따라 Codex 리뷰 필수). `git log -1 --format=%h` = `8e5172b` (플랜 시작 시점과 동일).

## Self-Check: PASSED

- 생성 파일 5개 전부 존재 확인(`wc -l` 출력)
- 수정 파일 2개 `git status --short` 에 `M` 으로 확인
- 커밋 0건 — `git log -1 --format=%h` = `8e5172b` 불변 (해시 검증 대상 없음: 이 플랜은 의도적으로 커밋을 만들지 않음)
- `.planning/STATE.md`·`.planning/ROADMAP.md` 미변경(이 실행자는 쓰지 않음)
