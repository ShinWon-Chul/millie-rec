---
phase: 05-must
plan: 12
subsystem: Serving (GET /api/dashboard 최소형 · dashboard_agg 신설)
tags: [serving, dashboard, kpi, latency, sqlite-aggregation, tdd, should]
requires:
  - src/millie_rec/serving/schemas_should.py (freeze — DashboardOut · KpiValue · AbRow · LatencyBlock)
  - src/millie_rec/serving/db.py (Database.query — 05-03 인계)
  - src/millie_rec/serving/schema.sql (recommendations · events · users · candidate_sets)
  - "Plan 05-06 rec_log.log_recommendation (모든 응답을 recommendations 에 1행 — D-12, 이 집계의 유일한 원천)"
  - "Plan 05-04 POST /api/events 품질 게이트 (events.quality_flag · selected · candidate_set_id)"
  - "Plan 05-07 dashboard_api.build_router(*, db, …) 의 db 인자 (이 플랜이 처음 사용)"
provides:
  - "GET /api/dashboard → DashboardOut (kpi 6 · latency p50/p95/p99 + by_stage · quality 3 · events_recent ≤50 · impressions_log · by_variant · by_hour · ab_table · mde_note)"
  - "serving.dashboard_agg.build_dashboard(db, *, now=None) → DashboardOut"
  - "serving.dashboard_agg.percentile · KPI_KEYS · EVENTS_RECENT_N · MDE_NOTE · P95_NOTE · ERROR_NOTE"
  - "serving.dashboard_agg SQL 상수 6종(SQL_RECS · SQL_USERS · SQL_EV_USERS · SQL_EV_RECENT · SQL_IMPRESSIONS · SQL_QUALITY)"
affects:
  - "Phase 6 '데모 재구성'(.planning/ROADMAP.md) DEMO-08 관제 대시보드 화면(#/dashboard, ../.assets/설계서/화면 구성 및 디자인/02_화면구성_v2_8페이지.md §2)"
  - "src/millie_rec/serving/api.py — 무수정. 05-06 이 dashboard_api.build_router(db=db) 를 이미 include 하므로 라우트가 자동 노출된다"
tech-stack:
  added: []
  patterns:
    - "집계 전담 파일 분리(Advisor 확정 17 B6) — dashboard_api 는 라우트 배선만, SQL·백분위·조립은 dashboard_agg"
    - "SELECT 4종 + 집계 1종만으로 전 KPI — 파라미터는 상수 LIMIT 뿐(사용자 입력 0, T-05-12-03)"
    - "예외·빈 DB 를 같은 강하 경로로 — try 밖에서 만든 iso 로 kpi 0.0 · latency 0.0 페이로드 반환(500 없음)"
    - "부분 dict + ** 언팩으로 pydantic 모델 조립 — ruff format 의 인자 한 줄 전개를 피해 150줄 한도 안에 둔다(05-07 과 같은 기법)"
key-files:
  created:
    - src/millie_rec/serving/dashboard_agg.py
    - tests/serving/test_dashboard.py
  modified:
    - src/millie_rec/serving/dashboard_api.py
decisions:
  - "events 집계 쿼리 3개(flagged · last_ts · impression 수신율)를 SQL_QUALITY 1개의 조건부 COUNT 로 병합 — 쿼리 3→1, 줄 수 절약"
  - "SQL_EV_USERS 는 GROUP BY 대신 DISTINCT — 같은 결과이고 한 줄에 든다"
  - "feature_freshness_s 는 max(0.0, …) 로 하한 — ts_future 플래그 이벤트가 마지막이면 음수가 나온다(05-04 SUMMARY 가 경고한 상황)"
  - "AbRow.reader_open 은 None — primary 와 정의가 같아(그 셀에서 reader_open 을 남긴 유저 비율) 중복 기입하지 않는다. 계약상 optional"
  - "percentile 은 bench.percentile 과 같은 규칙을 중복 정의(PLAN 지시) — bench 는 CLI 모듈이라 import 하지 않는다"
requirements-completed: [SERV-13]
metrics:
  tasks: 3
  tests_added: 10
  duration: "~55min"
  completed: 2026-09-06
commits: 0   # no_commit
---

# Phase 5 Plan 12: 관제 대시보드 최소형(GET /api/dashboard) Summary

**`recommendations`(D-12 전 응답 로그)와 `events`(품질 게이트 플래그)만 SELECT 5회로 훑어 KPI 6개·지연 백분위·품질 3키·A/B 셀 표를 만드는 `GET /api/dashboard` 를, 집계 전담 신설 파일 `serving/dashboard_agg.py`(149줄) 에 넣고 `dashboard_api.py`(147줄) 에는 라우트 6줄만 붙였다. 파일도 사용자 입력도 읽지 않으며 빈 DB·손상 JSON·예외 어느 쪽도 200 이다.**

## 변경 파일 (커밋 0 — 작업 트리에 남긴다)

| 경로 | 상태 | 줄 수 | 내용 |
|---|---|---|---|
| `src/millie_rec/serving/dashboard_agg.py` | 신규 | **149** (≤150) | SQL 6 · `percentile` · `_parse` · `_rate` · `_ms` · `_by_stage` · `_kpi` · `_ab` · `build_dashboard` |
| `src/millie_rec/serving/dashboard_api.py` | 수정 | **147** (≤150, 140 → 147) | `GET /api/dashboard` 라우트 1개 + `build_dashboard`·`DashboardOut` import. showcase 라우트·상수·`build_router` 시그니처 불변 |
| `tests/serving/test_dashboard.py` | 신규 | 264 (`def test_` 10건) | 계약 1 · 정확성 7 · 안전성 2 |

`must_not_touch` 목록의 파일은 하나도 건드리지 않았다. `tests/serving/test_dashboard_api.py`(05-07) 는 무수정이고 8건 그대로 통과한다. 병렬 실행 중인 05-10(`state`·`nearline`·`compose`·`cascade`·`rows`·`levels`·`after_completion`)·05-11(`ratings_api`·`api`) 과 파일이 겹치지 않는다.

## TDD 증거

### RED (Task 1 — 스텁 `build_dashboard` 가 빈 `kpi`·0.0 `latency` 만 반환)

`uv run pytest tests/serving/test_dashboard.py --no-header` 의 실패 유형(`grep -E "^E +.*Error"` 요약) — 10건 전부 `AssertionError`, `ImportError`·collection error 없음:

```
E       AssertionError: assert set() == {'active_user...g_start_rate'}     (× 2)
E       AssertionError: assert 0.0 == 30.0
E       AssertionError: kpi 에 fallback_rate 가 없다: []
E       AssertionError: assert set() == {'feature_fre...receipt_rate'}
E       AssertionError: assert 0 == 11
E       AssertionError: assert 0 == 5
E       AssertionError: assert {} == {'hybrid_v1':...llback_v1': 1}
E       AssertionError: assert None == '데모 표본으로 검정하지 않음 — read-start +1%p 검출에 필요한 셀당 n 은 실서비스 트래픽으로 산정한다'
E       AssertionError: 손상 행이 by_stage 를 없애면 안 된다
```

```
FAILED tests/serving/test_dashboard.py::test_dashboard_parses_kpi_six_keys_all_with_n_and_note
FAILED tests/serving/test_dashboard.py::test_latency_percentiles_and_by_stage_hand_computed
FAILED tests/serving/test_dashboard.py::test_kpi_rates_hand_computed - Assert...
FAILED tests/serving/test_dashboard.py::test_quality_block_three_keys - Asser...
FAILED tests/serving/test_dashboard.py::test_events_recent_capped_50_latest_first_keys
FAILED tests/serving/test_dashboard.py::test_impressions_log_joined_with_survey_variant
FAILED tests/serving/test_dashboard.py::test_by_variant_and_by_hour - Asserti...
FAILED tests/serving/test_dashboard.py::test_ab_table_cells_by_segment_and_mde_note
FAILED tests/serving/test_dashboard.py::test_empty_db_is_200_zero_values - As...
FAILED tests/serving/test_dashboard.py::test_corrupt_breakdown_skipped_and_no_file_or_query_access_grep
10 failed, 2 warnings in 0.25s
```

같은 시점의 회귀(`tests/serving/test_dashboard_api.py tests/test_architecture.py`): `11 passed, 2 warnings in 0.19s`.

### GREEN + REFACTOR (Task 2·3)

`uv run ruff format --check … && uv run ruff check … && uv run pytest tests/serving/test_dashboard.py tests/serving/test_dashboard_api.py tests/test_architecture.py --no-header`:

```
3 files already formatted
All checks passed!
21 passed, 2 warnings in 0.58s
```

`wc -l` → `dashboard_agg.py` 149 · `dashboard_api.py` 147. `pytest.skip` 0건.

## TDD Gate Compliance

RED → GREEN → REFACTOR 순서를 지켰고 각 게이트의 pytest 출력이 위에 있다. `no_commit: true` 플랜이라 `test(...)`/`feat(...)` 게이트 커밋은 만들지 않았다 — 게이트 증거는 이 SUMMARY 의 pytest 출력이다(`tdd_gate_evidence: pytest-output`).

## `GET /api/dashboard` 응답 키

| 키 | 형태 | 원천 |
|---|---|---|
| `generated_at` · `window` | ISO-8601 Z · `"all"` | 서버 시각(주입 가능한 `now`) |
| `kpi` | 6키 × `{value, n, note?}` | `recommendations` + `events` + `users` |
| `latency` | `{p50, p95, p99, by_stage}` | `recommendations.latency_total_ms` · `latency_breakdown` JSON |
| `quality` | `impression_receipt_rate` · `flagged_events` · `feature_freshness_s` | `events` 1회 집계 SELECT |
| `events_recent` | ≤50, 최신순, 7키 | `events ORDER BY ts DESC, rowid DESC LIMIT 50` |
| `impressions_log` | `candidate_set_id·book_id·position·selected·survey_variant` | `events` × `candidate_sets` LEFT JOIN (없으면 `'v1'`) |
| `by_variant` | `{model_version: n}` | `recommendations.model_version` |
| `by_hour` | `[{hour, n}]` UTC 시각 오름차순 | `recommendations.ts`(파싱 실패 행 건너뜀) |
| `ab_table` · `mde_note` | 셀×신규/기존 행 + 고정 문장 | `users.cell`·`is_new` + 그 셀의 `recommendations` |

### KPI 6개 정의 (분자 / 분모)

| 키 | value | n | note |
|---|---|---|---|
| `qualified_reading_start_rate` | `qualified_read` 유저 ∩ `reader_open` 유저 / `reader_open` 유저 | `reader_open` 유저 수 | — |
| `first_completion_rate_new` | `is_new` 유저 중 `completion` 남긴 수 / `is_new` 유저 | `is_new` 유저 수 | — |
| `fallback_rate` | `fallback_level ≥ 1` 응답 / 전체 응답 | 전체 응답 수 | — |
| `p95_latency_ms` | `latency_total_ms` 정렬 p95 | 측정된 응답 수 | `서버 실측·참고용` |
| `error_rate` | 상수 0.0 | 전체 응답 수 | `5xx 없음 — cascade 가 항상 200` |
| `active_user_keys` | `users` 행 수 | 같은 값 | — |

분모 0 이면 전부 `value = 0.0`(빈 DB 200). 백분위는 `ceil(p/100·n) − 1` 정렬 인덱스로 `bench.percentile` 과 같은 규칙이다. 손계산 검증: 지연 표본 `[10,20,30,40,50,60]` → p50 30.0 · p95 60.0 · p99 60.0, `by_stage["feature"]`(`[1..6]`) → `[3.0, 6.0]`.

### Phase 6 DEMO-08 관제 대시보드 화면이 읽는 필드

`#/dashboard`(../.assets/설계서/화면 구성 및 디자인/02_화면구성_v2_8페이지.md §2) 는 이 응답 하나로 그린다 — 상단 KPI 카드 6장은 `kpi[*].value` + `n` 병기, 지연 카드는 `latency.p50/p95/p99` 와 단계 막대 `latency.by_stage`(`feature/pipeline/retrieval/ranking/rerank/compose` 중 존재하는 키), 품질 3칸은 `quality`, 실시간 목록은 `events_recent`(최신 50) 와 `impressions_log`, 분포 차트는 `by_variant`·`by_hour`, 하단 A/B 표는 `ab_table` + 각주 `mde_note`. `p95_latency_ms.note` 문구를 화면에 그대로 노출해야 PDF 숫자(`results/latency.json`)와 혼동되지 않는다(../.claude/rules/serving.md 숫자 규칙).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] 테스트의 라우트 introspection 이 빈 목록을 반환**
- **Found during:** Task 2 (GREEN 첫 실행 — 10건 중 9건 통과, 1건 `IndexError`)
- **Issue:** `TestClient(app).app.routes` 로 `/api/dashboard` 엔드포인트를 찾으려 했으나 TestClient 가 감싼 앱에서 경로가 잡히지 않았다.
- **Fix:** `build_router(db=db).routes` 에서 직접 찾고 `assert len(endpoints) == 1` 을 앞에 뒀다. 단정을 약화한 것이 아니라 헬퍼 버그를 고친 것이고, 그 앞의 by_stage·p95 단정은 이미 통과 상태였다.
- **Files modified:** `tests/serving/test_dashboard.py`

### 계획과 다르게 구현한 것 (전부 동작 동일)

| 항목 | PLAN | 실제 | 이유 |
|---|---|---|---|
| events 보조 쿼리 | `SQL_FLAGGED`·`SQL_LAST_TS` 2개 + impression 카운트 | `SQL_QUALITY` 1개(조건부 COUNT 4열) | 쿼리 3→1, 150줄 한도 |
| `SQL_EV_USERS` | `GROUP BY user_key, event_type` | `SELECT DISTINCT` | 같은 결과, 한 줄에 든다 |
| `SQL_RECS`·`SQL_EV_RECENT`·`MDE_NOTE` | 여러 줄 문자열 | 한 줄 + `# noqa: E501` | 05-07 `DATA_NOTICE` 와 같은 기법(문자열은 formatter 가 못 쪼갠다) |
| `AbRow.reader_open` | 채움 후보 | `None` | `primary` 와 정의가 같아 중복 기입하지 않는다(계약상 optional) |
| `feature_freshness_s` | `now − MAX(events.ts)` | 같되 `max(0.0, …)` | `ts_future` 플래그 이벤트가 마지막이면 음수가 된다(05-04 SUMMARY 4번 경고) |

`percentile` 은 PLAN 지시대로 `bench.py` 에서 import 하지 않고 같은 규칙으로 중복 정의했다.

## Known Stubs

없음. 모든 필드가 실제 테이블에서 계산되며 하드코딩 상수는 `error_rate`(0.0 — cascade 가 5xx 를 만들지 않는다는 사실의 표현, `note` 로 고지)와 고정 문장 `mde_note` 둘뿐이다. `GET /metrics`·24h 집계는 이 페이즈에서 설계만(SERV-14, 05-CONTEXT D-13)이므로 스텁조차 만들지 않았다.

## Threat Flags

없음. 새 네트워크 표면은 비인증 읽기 전용 `GET /api/dashboard` 1개이고 이미 플랜의 위협 등록부(T-05-12-01~04)에 있다. 파라미터 바인딩은 상수 `LIMIT` 뿐이고(`execute(f` 0건), `open(`·`Path(` 는 집계 파일에 없다 — 테스트가 grep 으로 단정한다.

## PROGRESS 1줄 후보 (Advisor 기입)

> `serving/dashboard_agg.py` 신설 — 아키 §9-3 파일 목록 외. `dashboard_api.py` 가 140줄이라 `GET /api/dashboard` 집계 SQL·백분위·조립을 분리했다(Advisor 확정 17 B6, 2026-09-06). serving 슬라이스 내부 import 이므로 star 의존 위반 아님(`tests/test_architecture.py` 통과).

## Advisor 보고

- **완료 기준 전부 충족:** 자기 경로 ruff format/check 클린, `tests/serving/test_dashboard.py`(10) + `test_dashboard_api.py`(8) + `tests/test_architecture.py`(3) = **21 passed**. 두 파일 149·147줄로 한도 안. 커밋 0.
- **전체 스위트·`make smoke` 는 돌리지 않았다.** 같은 작업 트리에서 05-10·05-11 이 동시에 파일을 쓰고 있어 지시대로 자기 경로만 검증했다. 통합 확인은 wave 4 게이트에서.
- **`api.py` 무수정으로 노출된다.** 05-06 이 `dashboard_api.build_router(db=db)` 를 이미 include 하므로 같은 라우터에 라우트를 추가한 것만으로 `/api/dashboard` 가 뜬다. 다만 실서버 스모크(`make serve` → `curl /api/dashboard`)는 이 플랜에서 하지 않았으니 wave 4 통합 시 1회 확인이 필요하다.
- **판단이 필요한 것 하나:** `dashboard_agg.py` 를 149줄에 맞추느라 `build_dashboard` 가 30줄 안에서 수집·조립을 함께 한다. 파일 하나 = 관심사 하나 기준에서 경계선이다. 더 쪼개려면 파일이 하나 더 필요해 Advisor 결정 사항으로 남긴다.

## Self-Check: PASSED

- `src/millie_rec/serving/dashboard_agg.py` — FOUND (149줄)
- `src/millie_rec/serving/dashboard_api.py` — FOUND (147줄, 라우트 1개 추가)
- `tests/serving/test_dashboard.py` — FOUND (`def test_` 10건)
- 커밋 해시 검증 대상 없음 — `no_commit: true`(사용자 지시 2026-09-05, Advisor 확정 10). `git` 쓰기 명령 0회 실행.
