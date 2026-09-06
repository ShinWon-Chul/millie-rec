---
phase: 02-track-a
plan: 04
subsystem: serving
tags: [serving, fastapi, level0, tdd, compose]
requires:
  - "contracts.Pipeline / RecommendResponse / Recommendation / VARIANTS / MODEL_VERSION_SUFFIX (freeze, 무변경)"
  - "serving/fallback.py::trending_row · GlobalPopularFallback (Phase 1, 무변경)"
  - "serving/schemas.py::RecommendOut.from_contract (freeze, 무변경)"
provides:
  - "serving/compose.py::build_response — level 0·level 3 공용 RecommendResponse 조립 (trending 1행)"
  - "serving/compose.py::default_variant — D-11 기본 variant (등록된 것 중 VARIANTS 순서상 마지막)"
  - "serving/compose.py::new_rec_id · ZERO_WEIGHTS"
  - "serving/api.py::_personalized_response — seeds + 등록 variant 면 fallback_level=0"
affects:
  - "Plan 05 (app/pipeline·server) — pipelines={'pop': …} 주입 시 /api/recommend 가 level 0"
  - "Phase 5 '서빙 Must 완성'(.planning/ROADMAP.md) — compose.py 에 Must 5행 증분"
tech-stack:
  added: []
  patterns:
    - "응답 조립 단일화(이중 구현 금지): api.py 에 RecommendResponse( 리터럴 0개, compose.py 에 1개"
    - "Pipeline 예외는 except Exception → log.exception → level 3 200 (본문에 예외 문자열 없음)"
key-files:
  created:
    - src/millie_rec/serving/compose.py
    - tests/serving/test_recommend_level0.py
  modified:
    - src/millie_rec/serving/api.py
decisions:
  - "compose.py 를 Phase 2 에 신설 (api.py 150줄 예산 · 아키텍처 01 §9-3 파일 목록)"
  - "/health.model_version·artifacts_loaded_at 채우기는 Phase 5 로 연기"
metrics:
  duration: "약 25분"
  completed: 2026-09-05
  tasks: 3
  files_changed: 3
  commits: 0
---

# Phase 2 Plan 04: `/api/recommend` level 0 분기 Summary

`GET /api/recommend` 에 level 0 분기를 TDD 한 사이클로 붙였다 — `seeds` 가 있고 `pipelines` 에 등록 variant 가 있으면 그 파이프라인을 호출해 `fallback_level=0`·`model_version=f"{variant}_v1"`·`trending` 1행 + `items` 상위 k 평탄화로 응답하고, 익명·파이프라인 예외는 level 3 200 을 유지한다. 응답 조립은 신설 `serving/compose.py::build_response` 하나로 모아 level 3 경로와 공유했다.

## 변경 파일 (커밋 없음 — 사용자 승인 대기)

| 파일 | 상태 | 줄 수 | 비고 |
|---|---|---|---|
| `src/millie_rec/serving/compose.py` | 신규(untracked) | 60 | `build_response` · `default_variant` · `new_rec_id` · `ZERO_WEIGHTS` |
| `src/millie_rec/serving/api.py` | 수정(untracked — Phase 1 도 미커밋) | 128 → 135 | level 0 분기 + `_personalized_response` 신설, 조립 로직 이동 |
| `tests/serving/test_recommend_level0.py` | 신규(untracked) | 156 | 계약·정확성·안전성 7건 |

`git status --short` 발췌 (이 플랜 몫만):
```
?? src/millie_rec/serving/api.py
?? src/millie_rec/serving/compose.py
?? tests/serving/test_recommend_level0.py
```
`api.py` 가 `??` 인 것은 Phase 1 산출물 전체가 아직 미커밋이기 때문이다(결정 'Phase 1 실행 방식'(../.assets/개발일지/2026-09-05_Day1_GSD_초기화와_계약_freeze.md 항목 D55) · D-18). **커밋하지 않는다 — 작업 트리에 남기고 SUMMARY 에 변경 파일 목록을 적는다.**

## Task별 결과

### Task 1 (RED) — `tests/serving/test_recommend_level0.py` 7건
가짜 Pipeline 3종(`_FakePop`·`_FakeNamed`·`_Boom`)과 로컬 `_app(tmp_path, pipelines=None)` 을 `tests/serving/test_smoke.py` 패턴 그대로 복사해 작성했다(`test_smoke.py` 는 열어 보기만 — 소유자 02-05). `millie_rec.retrieval|data|evaluation|app` import 0건.

### Task 2 (GREEN) — `compose.py` 신설 + `api.py` level 0 분기
`api.py` 변경 요지 5개:
1. `uuid`·`ZERO_WEIGHTS`·`_new_rec_id`·`RecommendResponse(...)` 조립이 `compose.py` 로 이동(`api.py` 에서 삭제, `grep -c "RecommendResponse(" api.py` == 0).
2. `_fallback_response` 시그니처(`*, level: int = FALLBACK_GLOBAL_POP` 포함) **불변** — 본문만 `build_response(..., level=level, ...)` 호출로(오케스트레이터 승인 조건 ①).
3. `default_variant` 는 `compose.py` 에(줄 예산), `_personalized_response` 는 `api.py` 에 신설.
4. 핸들러 분기 2줄: `name = model if model in pipelines else default` (D-11) / `if user.explicit_seeds and name:` (D-13).
5. `/health` 본문·`create_app` 시그니처·422 규칙·쿼리 인자 이름 무변경.

`build_response` 는 `level == FALLBACK_PERSONALIZED` 일 때만 `items` 를 상위 k 로 평탄화하므로 level 3 응답은 Phase 1 과 바이트 단위로 동일한 형태(`items=[]`, `rows=[trending]`, weights 0)를 유지한다.

### Task 3 (REFACTOR) — 자기 경로 ruff + 스코프 게이트
`ruff format` 결과 `3 files left unchanged`(처음부터 포맷 준수), `ruff check src/millie_rec/serving tests/serving` → `All checks passed!`, `ruff format --check src/millie_rec/serving tests/serving` → `10 files already formatted`. `serving/__init__.py` 는 건드리지 않았다(`build_response`·`default_variant` 미노출 — 승인 조건 ②).

## TDD Gate Compliance

커밋 게이트(`test(...)` → `feat(...)`)는 **생략**한다 — 이 프로젝트는 사용자 승인 전 커밋 0(D-18 · 결정 'Phase 1 실행 방식'(../.assets/개발일지/2026-09-05_Day1_GSD_초기화와_계약_freeze.md 항목 D55)). 대체 증거는 아래 pytest 출력이다.

**RED** — `uv run pytest tests/serving/test_recommend_level0.py --no-header` (구현 전, 현재 `api.py` 기준):
```
FAILED tests/serving/test_recommend_level0.py::test_level0_with_pop_pipeline_returns_personalized_recommend_out
FAILED tests/serving/test_recommend_level0.py::test_level0_items_exclude_seeds_and_are_score_sorted
FAILED tests/serving/test_recommend_level0.py::test_default_variant_is_last_registered_in_variants_order
FAILED tests/serving/test_recommend_level0.py::test_registered_only_pop_but_model_cf_uses_default_without_error
4 failed, 3 passed, 2 warnings in 0.26s
```
실패 사유는 전부 `AssertionError` 다(`KeyError`·`TypeError`·`ImportError` 0건 — `grep -cE "KeyError|TypeError|ImportError"` == 0):
```
E       AssertionError: assert 3 == 0
E        +  where 3 = RecommendOut(recommendation_id='rec_ca02a6', model_version='fallback_v1', ...).fallback_level
E       assert [] == [1, 2, 3]
E       AssertionError: assert 'fallback_v1' == 'cf_v1'
E       AssertionError: assert 'fallback_v1' == 'pop_v1'
```
**의도된 사전 통과 3건**(회귀 방지용): `test_anonymous_request_without_seeds_stays_level3` · `test_pipeline_exception_degrades_to_level3_200_without_leaking_error` · `test_empty_pipelines_regression_stays_level3` — 현재 코드가 이미 level 3 이므로 RED 단계에서 통과하는 것이 정상이며, GREEN 이후에도 통과해야 "Phase 1 동작 불변" 이 증명된다.

**GREEN** — 구현 후:
```
tests/serving/test_recommend_level0.py: 7 passed, 2 warnings in 0.25s
tests/serving/test_smoke.py -k "not server_module": 10 passed, 1 deselected, 2 warnings in 0.18s
tests/test_architecture.py: 3 passed in 0.02s
tests/serving tests/test_architecture.py -k "not server_module": 22 passed, 1 deselected, 2 warnings in 0.37s
```

**REFACTOR** — `ruff format` 무변경(이미 포맷 준수), 정리할 중복 없음. 이번 브리프가 건드린 파일 밖은 손대지 않았다(최소 변경 원칙).

## planner 결정 2개 (Advisor 가 개발일지 D 항목으로 옮길 수 있게)

1. **`compose.py` 를 Phase 2 에 신설한다.** `api.py` 는 128줄이었고 level 0 분기·기본 variant·개인화 응답 헬퍼를 넣으면 `RecommendResponse` 조립이 두 벌이 되어 160줄을 넘는다(파일 ≤150줄, `../.claude/rules/simplicity.md`). 조립을 `build_response` 하나로 빼면 level 3 도 같은 함수를 쓰고 `api.py` 는 135줄로 남는다. 아키텍처 01 §9-3 serving 파일 목록에 `compose.py` 가 이미 있고, Phase 1 이 `fallback.py` 를 level 3 만으로 만든 것과 같은 증분 방식이다. **Must 5행·행 순서 정본은 Phase 5 '서빙 Must 완성'(.planning/ROADMAP.md) 에 남는다** — Phase 2 는 `trending` 1행(D-12)만 만든다. 되돌리는 조건: Phase 5 가 행 순서 정본을 다른 파일로 옮기기로 하면 `build_response` 를 그쪽으로 이동.
2. **`/health.model_version`·`artifacts_loaded_at` 은 Phase 2 에서 채우지 않는다(Phase 5 로 연기).** 스키마 optional 이라 계약 영향 0이고, `api.py` 150줄 예산이 빡빡하며 Phase 5 가 `nearline_last_run` 으로 `/health` 를 어차피 다시 연다. 기존 단정 `out.model_version is None`(`tests/serving/test_smoke.py`)도 그대로 유효하다.

## Deviations from Plan

### 1. [검증 도구 보정] `awk 'length > 100'` 대신 문자 단위 E501 검사
- **발견 시점:** Task 1 acceptance 확인
- **문제:** 이 머신의 `awk` 는 로케일과 무관하게 **바이트** 길이를 센다. 한글 1자 = 3바이트라 한글이 있는 줄이 전부 걸린다 — 정본 파일 `tests/serving/test_smoke.py`(Phase 1, ruff 클린)조차 12줄이 걸렸다.
- **조치:** 코드는 바꾸지 않고, E501 판정은 권위 있는 `uv run ruff check`(전부 통과) + 문자 단위 파이썬 검사(`len(line) > 100` → 0줄)로 대체했다. 플랜 acceptance 의 `awk` 는 프록시였고 의도(E501 없음)는 충족된다.
- **영향 파일:** 없음(검증 절차만)

### 2. [환경 사실] `git diff --stat` 기반 acceptance 는 미커밋 상태에서 성립하지 않음
- **발견 시점:** Task 1·Task 3 acceptance
- **문제:** Phase 1 산출물이 전부 미커밋(D-18)이라 `serving/api.py`·`fallback.py`·`db.py` 는 `??`(untracked), `serving/__init__.py` 는 HEAD 대비 ` M` 이다. 따라서 "`git diff --stat src/millie_rec/serving/` → 출력 없음"·"`__init__.py` diff 없음" 은 이 플랜의 변경과 무관하게 실패한다.
- **조치:** 대신 **작업 시작 시점 md5 스냅샷 ↔ 종료 시점 md5** 비교로 "이 플랜이 건드리지 않았음" 을 증명했다. 대상 9개(`contracts.py` `serving/schemas.py` `schemas_should.py` `fallback.py` `db.py` `serving/__init__.py` `tests/serving/test_smoke.py` `tests/test_architecture.py` `Makefile`) 전부 `UNCHANGED`.
- **영향 파일:** 없음(검증 절차만)

### 3. [범위 준수] 전역 게이트 미실행
- `uv run pytest --no-header`(전체)·`ruff check .`·`make smoke` 는 이 플랜에서 돌리지 않았다 — wave 2 의 02-05 가 `app/**`·`tests/serving/test_smoke.py` 를 병렬로 수정 중이라 결과를 신뢰할 수 없다(플랜 3-c, checker B3). wave 종료 후 Advisor 가 1회 실행한다.

자동 수정(Rule 1~3)에 해당하는 버그·누락은 없었다. `_fallback_response` 리팩토링은 플랜이 명시한 유일한 허용 변경(줄 수 예산)이며 시그니처는 그대로다.

## 사용자 지시와의 긴장 (없음에 가까움)

- "모듈화" 지시와 플랜의 `compose.py` 신설이 일치. `compose.py` = 응답 조립만, `api.py` = 라우팅·분기만, 각각 60줄·135줄로 ≤150줄.
- "부수효과 없음" 지시: `pipelines={}` 경로는 `build_response` 를 통과해도 level 3·`items=[]`·`rows=[trending]`·weights 0 로 동일하며, `test_smoke.py` serving 단독 10건이 무변경으로 통과해 이를 증명한다. `/health` 는 한 글자도 바뀌지 않았다.

## Known Stubs

없음. `compose.py` 는 Phase 2 범위(trending 1행)를 완전히 구현하며, Must 5행은 스텁이 아니라 Phase 5 '서빙 Must 완성'(.planning/ROADMAP.md) 의 계획된 증분이다(D-12).

## Threat Flags

없음 — 플랜 `<threat_model>` 의 `mitigate` 2건(T-02-18 파이프라인 예외 격리, T-02-19 미등록 `model` 의 `KeyError` 제거)은 코드와 테스트에 모두 존재하고, 새 네트워크 표면·인증 경로·스키마 변경은 없다.

## Verification

| 검사 | 명령 | 결과 |
|---|---|---|
| level 0 7건 | `uv run pytest tests/serving/test_recommend_level0.py --no-header` | `7 passed` |
| Phase 1 회귀 | `uv run pytest tests/serving/test_smoke.py -k "not server_module" --no-header` | `10 passed, 1 deselected` |
| 아키텍처(star 의존) | `uv run pytest tests/test_architecture.py --no-header` | `3 passed` |
| 스코프 스위트 | `uv run pytest tests/serving tests/test_architecture.py -k "not server_module" --no-header` | `22 passed`, failed 0 |
| lint | `uv run ruff check src/millie_rec/serving tests/serving` | `All checks passed!` |
| format | `uv run ruff format --check src/millie_rec/serving tests/serving` | `10 files already formatted` |
| 줄 수 | `wc -l` | `api.py` 135 · `compose.py` 60 (각 ≤150) |
| 슬라이스 경계 | `grep -rn "millie_rec\.(data\|retrieval\|evaluation\|app)" src/millie_rec/serving/` | 출력 없음 |
| 커밋 0 | `git log --oneline \| head -1` | `8e5172b chore: project scaffold …` (불변) |

## Self-Check: PASSED

- `src/millie_rec/serving/compose.py` — FOUND
- `src/millie_rec/serving/api.py` — FOUND (135줄)
- `tests/serving/test_recommend_level0.py` — FOUND (`def test_` 7개)
- 커밋 해시 — 해당 없음 (no commit — 사용자 승인 대기, D-18). `git log` HEAD 는 `8e5172b` 로 작업 전후 동일
- must-not-touch 9개 파일 md5 — 작업 전후 동일(UNCHANGED)
