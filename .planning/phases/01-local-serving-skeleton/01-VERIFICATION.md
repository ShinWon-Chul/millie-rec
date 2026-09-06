---
phase: 01-local-serving-skeleton
verified: 2026-09-05T00:00:00Z
status: passed
score: 6/6 must-haves verified
overrides_applied: 0
---

# Phase 1 '로컬 서빙 스켈레톤'(.planning/ROADMAP.md) Verification Report

**Phase Goal:** 개발자가 아티팩트·DB·네트워크·클라우드 없이 서버를 띄울 수 있고, 이후 모든 슬라이스를 "떠 있는 서버에 붙여" 검증할 수 있다.
**Verified:** 2026-09-05
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|---|---|---|
| 1 | `make serve` 진입점이 아티팩트·DB·네트워크 없이 뜨고 `GET /health` 200 `HealthOut`(`model_version` null) | ✓ VERIFIED | `make smoke` 실행 결과 `smoke: /health 200`; 실응답(01-02-SUMMARY.md) `"model_version":null,"db_ok":true`; `tests/serving/test_smoke.py::test_health_returns_200_and_parses_health_out` |
| 2 | `GET /` 이 `demo/` 정적 데모를 같은 origin에서 서빙(StaticFiles, 마지막 마운트) | ✓ VERIFIED | `src/millie_rec/app/server.py` L10-12 — `create_app(...)` 뒤에 `app.mount("/", StaticFiles(...))`; `make smoke` `smoke: / (demo static) 200`; `test_server_module_serves_demo_index_and_keeps_api_routes` (`/`·`/health`·`/docs`·`/api/recommend` 모두 200, 마운트가 라우트를 가리지 않음을 증명) |
| 3 | 파이프라인 미주입 상태에서 `GET /api/recommend?seeds=1,2,3` 이 `fallback_level=3` 200 | ✓ VERIFIED | `src/millie_rec/serving/api.py` L110-126, `_fallback_response`(L50-76); `make smoke` `smoke: /api/recommend 200`; 실응답 `"fallback_level":3,"model_version":"fallback_v1"`; 예외를 던지는 `_Boom` Pipeline 을 주입해도 200(`test_recommend_when_fallback_raises_still_200_level3`) — "추천 API 장애 ≠ 메인 장애" 코드 증거 |
| 4 | `contracts.DIR_DATA_LOCAL/millie.db` 자동 생성 + Must 4테이블(users·preference_snapshots·events·recommendations) | ✓ VERIFIED | 재실행 확인: `data/local/millie.db` 존재, `sqlite_master` 7개 테이블(`book_stats candidate_sets events preference_snapshots ratings recommendations users`) ⊇ Must 4, `PRAGMA journal_mode` = `wal`, `git check-ignore` 통과(커밋 대상 아님) |
| 5 | `잘못된 seeds·model·k` 는 422 | ✓ VERIFIED | `test_recommend_invalid_query_returns_422` (4개 케이스); `api.py` L120-121 `_422("model", …)`, `_parse_seeds` L40-47, `Query(ge=1, le=K_MAX)` |
| 6 | `uv run pytest --no-header` + `make smoke` PASS — 이후 모든 페이즈의 공통 완료 기준 | ✓ VERIFIED | 재실행: `104 passed, 2 skipped`(기준선 93 + 11); `tests/test_architecture.py` 3 passed; `make smoke` 4줄(`smoke: PASS`) exit 0, 종료 후 포트·pid 정리 확인 |

**Score:** 6/6 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|---|---|---|---|
| `src/millie_rec/contracts.py` | `MODEL_VERSION_FALLBACK = "fallback_v1"` 상수 1줄 | ✓ VERIFIED | L63 확인, `git diff --numstat` 기록상 `1 0`(SUMMARY) |
| `src/millie_rec/serving/schema.sql` | SQLite DDL Must 4 + Should 3, `CREATE TABLE IF NOT EXISTS` | ✓ VERIFIED | 35줄, 7테이블 전부 `IF NOT EXISTS`, PRIMARY KEY만(NOT NULL 없음) |
| `src/millie_rec/serving/db.py` | `Database`(thread-local·PRAGMA·apply_schema·table_names·row_counts·ok) + `resolve_db_path` | ✓ VERIFIED | 60줄, 실기동 테이블 7개·WAL 확인. 쓰기(`INSERT`) 0건(grep, D-06 준수) |
| `src/millie_rec/serving/fallback.py` | `GlobalPopularFallback` + `trending_row` | ✓ VERIFIED | 45줄, `Pipeline` Protocol 구현, `UserState.seen` 기반 시드 제외 |
| `src/millie_rec/serving/api.py` | `create_app · lifespan · GET /health · GET /api/recommend(level 3)` | ✓ VERIFIED | 128줄(≤150), 라우트 2개, `_fallback_response`가 예외를 흡수 |
| `src/millie_rec/serving/__init__.py` | 공개 표면 `__all__`에 `create_app`·`Database`·`GlobalPopularFallback`·`resolve_db_path` | ✓ VERIFIED | 7개 이름(`API_VERSION`·`Database`·`EventIn`·`GlobalPopularFallback`·`RecommendOut`·`create_app`·`resolve_db_path`) |
| `src/millie_rec/app/server.py` | uvicorn 진입점 — `create_app` 주입 + StaticFiles(마지막), CORS 없음 | ✓ VERIFIED | 12줄(≤30), `app = create_app(...)` 뒤에 `app.mount("/", ...)`, `CORSMiddleware`·`os.environ`·`@app.` 0건 |
| `tests/serving/test_smoke.py` | 계약·정확성·안전성 3종 스모크(11건) | ✓ VERIFIED | `grep -c "def test_"` = 11, 전부 통과 |

### Key Link Verification

| From | To | Via | Status | Details |
|---|---|---|---|---|
| `serving/api.py` | `serving/db.py` | `db.apply_schema()`(lifespan), `db.ok()`·`db.row_counts()`(/health) | ✓ WIRED | L94, L102, L106 |
| `serving/api.py` | `serving/fallback.py` | `trending_row(items)` | ✓ WIRED | L72 |
| `serving/api.py` | `serving/schemas.py` | `RecommendOut.from_contract(resp, forced=...)` | ✓ WIRED | L126 |
| `serving/db.py` | `contracts.py` | `os.environ.get(ENV_DATA_DIR)` | ✓ WIRED | L20 |
| `app/server.py` | `serving/__init__.py` | `from millie_rec.serving import Database, GlobalPopularFallback, create_app, resolve_db_path` | ✓ WIRED | L6 (2단 공개 표면 경로, 3단 경로 0건) |
| `app/server.py` | `demo/index.html` | `app.mount("/", StaticFiles(...))` 라우트 등록 뒤 마지막 | ✓ WIRED | L12, 마운트 순서가 `/health`·`/docs`·`/api/recommend` 를 가리지 않음(테스트로 고정) |

### Data-Flow Trace (Level 4)

Phase 1은 동적 데이터를 렌더링하는 컴포넌트가 아니라 스켈레톤(파이프라인·카탈로그 미주입 상태의 정의된 fallback 동작)이므로 Level 4는 해당 없음. `db_row_count`가 실제 `sqlite_master` COUNT(*) 결과임을 실기동으로 확인(정적 값 아님) — `db.py::row_counts()`가 하드코딩 없이 쿼리 결과를 반환.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|---|---|---|---|
| 서버 기동 후 `/health` 200 | `make smoke` (8010) | `smoke: /health 200` | ✓ PASS |
| 데모 정적 서빙 | `make smoke` | `smoke: / (demo static) 200` | ✓ PASS |
| fallback 추천 200 | `make smoke` | `smoke: /api/recommend 200` | ✓ PASS |
| 전체 스위트 회귀 없음 | `uv run pytest --no-header` | `104 passed, 2 skipped` | ✓ PASS |
| 아키텍처 star 의존 준수 | `uv run pytest tests/test_architecture.py --no-header` | `3 passed` | ✓ PASS |
| 코드 스타일 | `uv run ruff check src tests` | `All checks passed!` | ✓ PASS |
| SQLite 실기동 | `sqlite3` 직접 조회 | 7테이블 + `wal` | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|---|---|---|---|---|
| SKEL-01 | 01-01-PLAN, 01-02-PLAN | `make serve` 기동·`/health` 200 | ✓ SATISFIED | `make smoke` 실측 + `test_health_returns_200_and_parses_health_out` + `test_server_module_serves_demo_index_and_keeps_api_routes` |
| SKEL-02 | 01-02-PLAN | 정적 데모 같은 origin 서빙 | ✓ SATISFIED | `app/server.py` StaticFiles 마운트, `make smoke` `/ (demo static) 200` |
| SKEL-03 | 01-01-PLAN | 파이프라인 없을 때 fallback 200 | ✓ SATISFIED | `_fallback_response` + 예외 흡수 테스트 + `make smoke` `/api/recommend 200` |
| SKEL-04 | 01-01-PLAN | SQLite 자동 생성·Must 4테이블 | ✓ SATISFIED | `data/local/millie.db` 실기동 7테이블(Must4+Should3) |
| SKEL-05 | 01-02-PLAN | `make smoke` 3점 확인 | ✓ SATISFIED | `make smoke` 4줄 출력, exit 0 |

REQUIREMENTS.md의 상태 열(`Pending`)·체크박스는 이 검증 시점에 아직 갱신되지 않았다(문서 상태 갱신은 오케스트레이터/커밋 후 몫이며 코드 증거와는 별개) — 5개 ID 전부 두 PLAN의 `requirements:` frontmatter에 정확히 분배되어 있고 orphan 없음.

### Anti-Patterns Found

없음. `TODO|FIXME|XXX|HACK|PLACEHOLDER|not yet implemented` 등 grep 0건(신규 5개 소스 파일). `db.py`·`api.py`에 `INSERT` 0건(D-06 "행을 쓰지 않는다" 준수). `create_app`의 미사용 인자(`catalog`·`neighbors`·`book_stats`·`state`)는 시그니처 유지용 정의된 미주입 상태이며 스텁 분기 없음.

### Human Verification Required

없음. Phase 1의 성공 기준(서버 기동·같은 origin 서빙·fallback 200·SQLite 자동 생성·`make smoke`)은 전부 자동화된 테스트(`uv run pytest`)와 실측 명령(`make smoke`, 직접 `sqlite3` 조회)으로 프로그래밍적으로 검증 가능했다. 브라우저 시각 확인(`http://localhost:8000/?source=api`에서 구 데모 + fallback 배너)은 CONTEXT D-13/`<specifics>`가 명시적으로 "Advisor/사용자 몫"으로 분류했고, 콘솔 에러 0 등 데모 품질 기준은 Phase 6 '데모 재구성'의 범위이지 Phase 1 성공 기준이 아니다.

### Gaps Summary

갭 없음. 6개 관찰 가능한 진실 전부 VERIFIED, 8개 아티팩트 전부 존재·실질적(substantive)·연결(wired) 확인, 6개 핵심 연결 전부 WIRED, 5개 요구사항(SKEL-01~05) 전부 SATISFIED, 안티패턴 0건, 인간 검증 필요 항목 0건. `uv run pytest --no-header` 전체 스위트 104 passed / 2 skipped(회귀 없음), `tests/test_architecture.py` 3 passed(star 의존 위반 없음), `make smoke` 4줄 PASS, `data/local/millie.db` 실기동 확인. 사용자 제약(커밋 금지·no_commit) 준수 확인 — `git log` 해시는 두 SUMMARY가 기록한 시작 시점과 동일하며(8e5172b) 이번 검증 세션은 어떤 커밋도 만들지 않았다.

---

_Verified: 2026-09-05_
_Verifier: Claude (gsd-verifier)_
