---
phase: 06-demo-rebuild
verified: 2026-09-06T12:00:00Z
status: human_needed
score: 9/9 must-haves verified (mock 완주 기준) + 2/2 Should 확인
overrides_applied: 0
human_verification:
  - test: "스크래치패드 캡처 12장(pw_demo06/shots/)을 화면 구성 v2(02_화면구성_v2_8페이지.md) 목업과 나란히 눈으로 대조 — 배지 위치·색·앵커 타일 레이아웃·PC 페이지(D7·D8) 그리드"
    expected: "심사자가 '가짜' 티를 느끼지 않을 시각 완성도(06-CONTEXT '심사자가 mock으로 눌러봐도...' 절)"
    why_human: "시각적 완성도·레이아웃 미감은 자동 검사 대상이 아니다"
  - test: "내 서재(#/library)·쇼케이스(#/) 본인 5권 케이스에서 저자가 '저자 미상'으로 뜨는 것이 Day 8 PDF 캡처 품질로 수용 가능한지 판단(PROGRESS.md 09-06 제안 13번 — LibraryBook·ShowcaseBook에 authors optional 추가 여부)"
    expected: "저자 표시 없이도 book_id 병기로 동일 제목 도서 구분이 충분한지, 계약을 건드려서라도 고칠지 결정"
    why_human: "계약 변경 여부는 Day 3 freeze 예외 승인이 필요한 제품 판단이라 자동 검사로 대신할 수 없다"
  - test: "배지 6종 중 `light`('가볍게') 미구현을 PDF 문장 '6종 중 5종 실측'으로 그대로 쓸지 확인"
    expected: "Should 항목 의도적 축소를 인지한 상태에서 승인"
    why_human: "PDF 문구 승인은 developer 판단"
---

# Phase 6 '데모 재구성'(.planning/ROADMAP.md "Phase 6: 데모 재구성") Verification Report

**Phase Goal:** v1 데모 27파일을 8페이지 해시 라우팅·새 스키마·밀리 카탈로그로 재구성해 로컬 API에 붙인다.
**Verified:** 2026-09-06T12:00:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

이 검증은 오케스트레이터가 작성한 `06-VERIFICATION-NOTES.md`의 주장을 그대로 믿지 않고, 같은
명령을 직접 재실행하거나 코드를 직접 읽어 재현했다. 아래 표의 "재현 방법" 열은 이 세션이 실행한
명령·파일이다.

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|---|---|---|
| 1 | 구 v1 형태(hf.space·구 필드·Goodbooks)가 `demo/` 어디에도 남지 않는다 | ✓ VERIFIED | `grep -rnE 'hf\.space|"/recommend"|...` `demo` 전체 재실행 → 0건(직접 재현, 저작권 고지 2곳은 예외로 유지) |
| 2 | `/contract-sync` 형태 검사가 mock 10개 + fallback 1개 전부 통과한다 | ✓ VERIFIED | `uv run python`으로 `RecommendOut`·`OnboardingMeta`·`CandidateSet`·`PreferencesResponse`·`UserStateOut`·`schemas_should.DashboardOut`·`ShowcaseOut` 11개 파일 `model_validate` 직접 재실행 → 11/11 ok(첫 시도에서 `DashboardOut`이 `schemas.py`가 아니라 `schemas_should.py`에 있음을 확인 — 이름 정본 위치 재검증) |
| 3 | 8페이지 해시 라우팅이 실제 화면 렌더러로 연결돼 있다(빈 라우트 없음) | ✓ VERIFIED | `router.js` `ROUTES` 8항목 직접 읽음 + `app.js` `screenHTML()`·`onRoute()`를 라인 단위로 추적 — `showcase→d8`, `onboarding→s0/stepView/s6`, `home→d2`, `book→d3`, `reader→d4`, `library→d5`, `refresh→stepView`(온보딩 단계 재사용, 의도된 설계), `dashboard→d7`. 8개 전부 실제 렌더 함수 존재·연결 확인(그래프 추적, grep만으로 끝내지 않음) |
| 4 | 취향 설정 7단계(S0~S6)가 `config/onboarding.json` 1벌 + 공용 렌더러로 그려지고, 건너뛰기는 `consent=false` | ✓ VERIFIED | `onboarding.json`에 `steps` 5개(S1~S5) + S0·S6 = 7단계, `onboarding_step.js` 공용 렌더러 확인. `actions.js:100` `skip: () => { state.consent = false; ... }` 직접 확인 |
| 5 | mock.js가 서버와 같은 점수 계산을 다시 하지 않는다(이중 구현 금지) | ✓ VERIFIED | `mock.js` 249줄 전체를 직접 읽음. `shelfRow()`는 `neighbors_kr.json`에서 미리 계산된 weight를 `Math.max`로만 조회·정렬(재계산 없음), `item()`의 `score`는 `ROW_SIZE - position` 표시값, `weightsFor()`는 주석대로 "스코어링이 아니라 U_t 설명용 숫자"(D-01 그대로). `badgeFor()`·`dedup()`은 D-05가 명시적으로 허용한 표시 규칙 미러링 |
| 6 | 쇼케이스(D8)의 모든 수치가 `results/`에서만 온다(하드코딩 0) | ✓ VERIFIED | `d8_showcase.js` 소스에 `[0-9]\.[0-9]{2,}` 리터럴 0건(테이블 헤더 텍스트만 검색됨). `demo/mock/showcase.json`의 `eval_table.rows` 4행이 `results/latest.csv` 4행과 숫자 완전 일치(pop 0.063/0.054/0.764, hybrid 0.118/0.110/0.606/79.5 등) 직접 대조 |
| 7 | 관제 대시보드(D7)의 예산선·KPI가 상수·데이터 기반이지 하드코딩이 아니다 | ✓ VERIFIED | `d7_dashboard.js`에서 `BUDGET_MS = 200`(주석 `contracts.BUDGET_MS`) 외 리터럴 지표값 없음 |
| 8 | `tests/test_architecture.py`(star 의존)가 여전히 통과하고, Phase 6이 `src/`를 건드리지 않았다 | ✓ VERIFIED | 직접 재실행 100% pass. `git status --short src` 빈 출력, Phase 6 커밋 21개(`73e3357`~`844fb74`) 로그 확인 — 전부 `demo/`·`tests/demo` 대상 |
| 9 | 전 과정 로컬 기동·테스트가 가능하다(`local-run.md`) | ✓ VERIFIED | `uv run pytest --no-header` 직접 재실행 → `529 passed, 2 warnings`(노트와 동일) 재확인, `tests/demo` 10 passed, `ruff check` clean, `make smoke` PASS 전부 직접 재실행 |

**Score:** 9/9 truths verified(전부 직접 재현)

### Required Artifacts

| Artifact | Expected | Status | Details |
|---|---|---|---|
| `demo/js/router.js` | 해시 → {page, params}, 8라우트 | ✓ VERIFIED | 28줄, `ROUTES` 8항목, `parse()`/`listen()` 구현체 존재(플레이스홀더 아님) |
| `demo/js/app.js` | state+setState+render 1개씩, 8페이지 dispatch | ✓ VERIFIED | 248줄, `onRoute()`가 8개 page 분기 전부 실제 side-effect(API 호출·state 갱신) 수행 |
| `demo/js/mock.js` | 밀리 카탈로그 위 상태 시뮬레이션, 점수계산 없음 | ✓ VERIFIED (Level 4 데이터 흐름 확인) | `init()`이 `catalog_kr.json`·`neighbors_kr.json`·`showcase.json`·`meta_onboarding.json` 4개 실 파일을 fetch, `getRecommend()`가 이 데이터로 실제 행을 구성(빈 배열 반환 없음) |
| `demo/js/screens/d2_home.js`~`d8_showcase.js` | 화면 6개(D2·D3·D4·D5·D7·D8) | ✓ VERIFIED | 6개 파일 모두 존재, `app.js`가 전부 import·dispatch, `render(state)→string` 순수 함수 패턴 |
| `demo/scripts/make_mock.py` + `demo/mock/*.json` 10개 + `demo/fallback/popular.json` | 생성기 산출물, 밀리 기반 | ✓ VERIFIED (Level 4) | `_manifest.json`에 seed 42·입력 4개 md5 기록, `catalog_kr.json` 9,444권 `book_format` 값 정확히 3종(`전자책`·`오디오북`·`챗북`), `description`/`curator_note` 0건 |
| `demo/js/api.js` | `API_BASE=""`, `/api` 접두어, 13함수 | ✓ VERIFIED | `grep -c 'const API_BASE = ""'` = 1, `postRating`이 `POST /api/ratings` 호출 확인 |

### Key Link Verification

| From | To | Via | Status | Details |
|---|---|---|---|---|
| `router.js` ROUTES | `app.js` screenHTML()/render() | page 문자열 매칭 | ✓ WIRED | 8개 전부 실 렌더 함수로 연결(표 위 truth #3) |
| `d4_reader.js` 별점 모달 | `serving/schemas.py RatingOut` | `actions.js:174` `api.postRating()` → `POST /api/ratings` | ✓ WIRED | mock 모드는 `mock.postRating()`이 `store.addRating` + rating 이벤트 동시 기록 |
| `d8_showcase.js` 비교표 | `results/latest.csv` | `make_mock.py`가 `artifacts/serving/eval_table.json` 복사 → `showcase.json.eval_table` | ✓ WIRED (Level 4 데이터 흐름 확인) | 4행 숫자 완전 일치 직접 대조 |
| `demo/js/mock.js shelfRow()` | `demo/mock/neighbors_kr.json` | 사전 계산 이웃 테이블 조회(`nbrs[String(seed)]`) | ✓ WIRED | 재계산 없이 조회+정렬만(위 truth #5) |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|---|---|---|---|---|
| `d8_showcase.js` `metricsTable()` | `state.showcase.eval_table.rows` | `showcase.json` ← `make_mock.py` ← `artifacts/serving/eval_table.json` ← `results/latest.csv` | Yes(4행 숫자 소스 파일과 완전 일치 확인) | ✓ FLOWING |
| `d2_home.js`(배지) | `item.badge` | `mock.js badgeFor()` ← `catalog_kr.json`(`pop_rank`·`millie_label`·`average_rating` 등) | Yes | ✓ FLOWING |
| `d7_dashboard.js` KPI | `state.dashboard` | `mock.js getDashboard()` → `mock_store.dashboard()`(세션 이벤트 직접 집계, D-03) | Yes | ✓ FLOWING |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|---|---|---|---|---|
| **DEMO-01** | 06-03-PLAN | `api.js` 새 계약·구 형태 grep 0 [Must] | ✓ SATISFIED | 직접 재실행 grep 0건 + `API_BASE=""` 확인 |
| **DEMO-02** | 06-01/06-03-PLAN | mock 재생성 + `/contract-sync` 전부 통과 [Must] | ✓ SATISFIED | 11/11 model_validate 직접 재실행 |
| **DEMO-03** | 06-02/06-04/06-06-PLAN | 해시 라우팅 8페이지 [Must] | ✓ SATISFIED | 8라우트 전부 실 렌더러 연결 직접 추적 |
| **DEMO-04** | 06-02-PLAN | 취향 설정 7단계 + 건너뛰기 [Must] | ✓ SATISFIED | config 5+2단계, `consent=false` 확인 |
| **DEMO-05** | 06-06-PLAN | 배지 6종 + 인스펙터 6섹션 [Must] | ✓ SATISFIED (조건부 — 아래 주) | 배지 5/6 실측(`light`은 `.claude/rules/simplicity.md`의 범위 4분류 "가능하면(Should)" `light_start` 항목에 해당해 의도적 축소) |
| **DEMO-06** | 06-05-PLAN | 쇼케이스 비교표·그림·고지 [Must] | ✓ SATISFIED | 수치 하드코딩 0, `results/latest.csv`와 완전 일치 |
| **DEMO-07** | 06-04-PLAN | 뷰어 이벤트 3종 + 별점 모달 [Should] | ✓ SATISFIED | `POST /api/ratings` 연결 확인. `?source=api` 완주는 Phase 7 게이트로 이관(D-09, PROGRESS.md 09-06 제안 11번에 기록됨 — 문서화된 이관) |
| **DEMO-08** | 06-05-PLAN | 관제 대시보드 [Should] | ✓ SATISFIED | KPI가 세션 이벤트 실제 집계에서 옴(하드코딩 아님) |
| **DEMO-09** | 06-02/06-07-PLAN | mock+api 완주 콘솔 에러 0 [Must] | ✓ SATISFIED (mock만 — 범위 내) | mock 완주 17/17 재확인(pw_demo06/result.json), `?source=api`는 Phase 7 '배포' 사전 게이트로 CONTEXT D-09가 명시적으로 이관하고 PROGRESS.md에 REQUIREMENTS.md 문구 수정 제안까지 기록돼 있어 은폐된 축소가 아니다 |

모든 DEMO-01~09가 06-01~06-07 플랜의 `requirements:` 프런트매터에 최소 1곳 이상 매핑돼 있고, 고아
요구사항(REQUIREMENTS.md에는 있는데 어느 플랜도 주장하지 않은 것)은 없다.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|---|---|---|---|---|
| `demo/css/base.css` | 7건(18·40·41·71·80·84·144) | 토큰 밖 색 리터럴 | ℹ️ Info | v1 계승 파일, PDF 결과에 영향 없음 — 노트의 "수용" 판단에 동의(범위 4분류상 시간 대비 이득 없음) |
| `demo/css/onboarding.css` | 9건 | 토큰 밖 색 리터럴 | ℹ️ Info | Phase 6 어느 플랜도 소유하지 않는 v1 재사용 파일 — 이번 페이즈 책임 아님 |
| `demo/js/screens/d5_library.js` + `serving/schemas.py LibraryBook` | — | 시드 5권 저자 "저자 미상" | ⚠️ Warning | 계약 미변경(Day 3 freeze) 상태로 미결 이관됨(PROGRESS.md 09-06 제안 13번). 라우팅·dedup은 `book_id` 기준이라 기능 결함은 아니나 PDF 캡처 품질에 영향 — 아래 human_verification 항목 2번 |
| `demo/js/mock.js:86` | — | `light` 배지 미생성 | ℹ️ Info | 의도된 Should 축소(`.claude/rules/simplicity.md` 범위표) |

TODO/FIXME/placeholder 계열 문자열은 `demo/js`·`demo/css` 전체에서 0건(직접 재검색).

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|---|---|---|---|
| 전체 테스트 스위트 | `uv run pytest --no-header` | `529 passed, 2 warnings in 4.66s` | ✓ PASS |
| demo 전용 테스트 | `uv run pytest tests/demo -q` | `10 passed` | ✓ PASS |
| lint | `uv run ruff check demo/scripts tests/demo` | `All checks passed!` | ✓ PASS |
| 로컬 스모크 | `make smoke` | `/health 200 · / 200 · /api/recommend 200 · PASS` | ✓ PASS |
| 아키텍처 경계 | `uv run pytest tests/test_architecture.py -q` | 100% pass | ✓ PASS |
| mock 계약 검증 | `uv run python`으로 11개 파일 `model_validate` | `ok=11 fail=0` | ✓ PASS |
| Playwright mock 완주(오케스트레이터 산출물 검토) | `<scratchpad>/pw_demo06/result.json` 읽기 | 17/17 OK · console_errors=0 · page_errors=0 · not_found=0 | ✓ PASS(재실행은 하지 않고 원문 로그 검토 — Playwright 재설치·재실행은 이 세션 범위 밖) |

### Human Verification Required

#### 1. 캡처 12장 시각 대조

**Test:** `<scratchpad>/pw_demo06/shots/` 12장을 화면 구성 v2 목업(`.assets/설계서/화면 구성 및 디자인/02_화면구성_v2_8페이지.md` §2·§7)과 나란히 놓고 배지 위치·색·앵커 타일·PC 페이지(D7·D8) 그리드를 확인한다. 이 세션이 2장(`p3_home_badges_anchor.png`·`p4_showcase.png`)을 직접 열어본 결과 배지·비교표·본인 5권 케이스·철학 문장·인스펙터 6섹션이 모두 그려져 있었으나, 나머지 10장·미세한 레이아웃 어긋남까지는 스크린샷 판독만으로 단정할 수 없다.
**Expected:** "가짜" 티가 나지 않는 시각 완성도(06-CONTEXT 특기사항).
**Why human:** 시각적 완성도 판단은 자동 검사 범위 밖.

#### 2. 저자 미상 표시의 PDF 캡처 수용 여부

**Test:** `#/library`·`#/`(쇼케이스 본인 5권)에서 시드 5권 저자가 "저자 미상"으로 뜨는 것을 확인하고, `LibraryBook`·`ShowcaseBook` 계약에 `authors: str | None = None`을 추가할지(Day 3 freeze 예외) 아니면 이대로 캡처할지 결정한다.
**Expected:** developer가 계약 변경 비용 대비 PDF 캡처 품질 이득을 판단.
**Why human:** 계약 freeze 예외는 Advisor 승인이 필요한 제품 판단.

#### 3. 배지 "6종 중 5종" 문구 승인

**Test:** `light`(가볍게) 배지가 CSS만 준비돼 있고 mock 데이터는 생성하지 않는 상태에서, PDF 문장을 "6종 중 5종 실측"으로 쓰는 것에 동의하는지 확인.
**Expected:** Should 항목 의도적 축소를 알고 승인.
**Why human:** PDF 문구는 developer 승인 사항.

### Gaps Summary

기계적으로 재현 가능한 모든 Must 항목(DEMO-01~04, 06, 09-mock)과 Should 항목(DEMO-07·08)이
직접 재검증으로 통과했다. 차단 사유(gaps_found)로 분류할 항목은 없다 — 남은 것은 (a) 시각
완성도처럼 원래 사람만 판단할 수 있는 항목, (b) `light` 배지·색 리터럴처럼 프로젝트가 이미
Should로 분류하고 "수용"으로 기록한 항목, (c) 저자 미상처럼 계약 freeze 때문에 developer 승인이
필요한 미결 항목(PROGRESS.md에 제안으로 이미 남아 있음)이다. 이 셋 다 코드를 더 고쳐서 해소할
"gap"이 아니라 사람의 결정을 기다리는 항목이므로 상태를 `human_needed`로 판정한다.

---

_Verified: 2026-09-06T12:00:00Z_
_Verifier: Claude (gsd-verifier)_
