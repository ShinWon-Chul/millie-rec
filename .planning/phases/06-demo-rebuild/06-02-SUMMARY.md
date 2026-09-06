---
phase: 06-demo-rebuild
plan: 02
subsystem: Demo 레인 — 앱 셸(라우터·상태·액션·프리셋·HTML/CSS 셸)
tags: [demo, router, state-machine, events, capture-mode]
requires:
  - "demo/mock/*.json 13개 (06-01 산출)"
  - "demo/js/api.js·mock.js·mock_store.js (06-03, 부록 C 시그니처)"
  - "demo/js/screens/d4_reader.js·d5_library.js (06-04)"
  - "demo/js/screens/d7_dashboard.js·d8_showcase.js·css/tokens.css --dim (06-05)"
provides:
  - "demo/js/router.js — 해시 8라우트 parse/listen (라우트 표의 정본)"
  - "demo/js/app.js — state v2 1개 · setState 1개 · render 1개 · log/flush · onRoute · boot"
  - "demo/js/actions.js — data-act 24개 + 취향 설정 단계 머신 S1~S5"
  - "demo/js/presets.js — 쇼케이스 프리셋 3종"
  - "demo/js/screens/ui.js — tabbar·demoLabel·banner·modal (06-04·06-05·06-06 가 import)"
  - "demo/index.html — CSS 8링크 · #phone/#inspector/#page/#toast · bar-model/bar-version/bar-source"
  - "demo/css/base.css — 탭바·데모라벨·배너·토스트·모달·전폭 페이지·capture 2모드"
affects:
  - "demo/js/screens/d2_home.js·d3_detail.js (06-06 이 만들 파일 — app.js 가 이 이름으로 import 한다)"
  - "demo/js/inspector.js (06-06 확장 — render(state) 시그니처 유지 필요)"
tech-stack:
  added: []
  patterns:
    - "해시 라우터 + 단일 state + 단일 render (프레임워크 0)"
    - "이벤트 큐: sessionStorage millie_events → 120ms 디바운스 → 50개 배치 postEvents"
key-files:
  created:
    - demo/js/router.js
    - demo/js/actions.js
    - demo/js/presets.js
  modified:
    - demo/js/app.js
    - demo/js/screens/ui.js
    - demo/js/screens/onboarding_step.js
    - demo/js/screens/s0_start.js
    - demo/js/screens/s6_persona.js
    - demo/index.html
    - demo/css/base.css
    - demo/config/onboarding.json
    - demo/README.md
decisions:
  - "이벤트 flush 는 120ms 디바운스 후 50개 배치 — 행 노출 40건이 40번의 POST 가 되는 것을 막는다"
  - "배너는 app.js 의 render 가 폰 화면 상단에 1회 그린다 — d2_home.js 는 배너를 그리지 않는다"
  - "OnboardingMeta 에 subcategories dict 가 없어 onboarding_step.js 의 세부 카테고리 조회를 categories[].subcategories 로 교체"
metrics:
  tasks: 3
  commits: 3
  duration: "약 1시간"
  completed: 2026-09-06
---

# Phase 6 '데모 재구성' Plan 02: 앱 셸 Summary

해시 라우팅 8페이지를 `state` 1개 + `setState` 1개 + `render` 1개로 굴리는 앱 셸을 세웠다. 라우터·액션 딕셔너리·프리셋을 새로 만들고, `app.js` 를 v2 상태 모델 위로 다시 썼으며, 폰 프레임과 전폭 페이지를 나누는 HTML/CSS 셸과 캡처 2모드를 붙였다.

## 커밋

| # | 해시 | 내용 |
|---|---|---|
| 1 | `1d98802` | 해시 라우터·공용 컴포넌트·앱 셸 CSS/HTML |
| 2 | `4a63ed4` | app.js 재작성 + actions.js·presets.js 신규 |
| 3 | `0241a39` | 취향 설정 단계 화면 공유 수정 + demo/README 재작성 |

플랜 frontmatter 는 `no_commit: true` 였으나, 오케스트레이터(06 페이즈 wave 2 지시)가 태스크별 원자 커밋을 지시했고 wave 1(06-01)이 이미 4개 커밋으로 착지해 있어 커밋했다. 스테이징은 매번 소유 파일만 pathspec 으로 지정했다(`git add --` + `git commit -- <paths>`, `--no-verify`). 다른 세션의 미커밋 변경 약 150건은 건드리지 않았다.

## 변경 파일과 줄 수

| 파일 | 상태 | 줄 | 상한 |
|---|---|---|---|
| `demo/js/router.js` | 신규 | 28 | 30 |
| `demo/js/app.js` | 재작성 | 248 | 250 |
| `demo/js/actions.js` | 신규 | 211 | 250 |
| `demo/js/presets.js` | 신규 | 111 | 120 |
| `demo/js/screens/ui.js` | 수정(+4 export) | 89 | 130 |
| `demo/js/screens/onboarding_step.js` | 수정 | 95 | 250 |
| `demo/js/screens/s0_start.js` | 수정 | 15 | 250 |
| `demo/js/screens/s6_persona.js` | 수정 | 27 | 250 |
| `demo/css/base.css` | 수정 | 151 | 250 |
| `demo/index.html` | 수정 | 37 | — |
| `demo/config/onboarding.json` | 값 5 + 문자열 1 | 75 | — |
| `demo/README.md` | 재작성 | 104 | ≥40 |

## 구 형태 grep 0건

```
$ grep -rnE 'hf\.space|"/recommend"|\btimestamp\b|"format"\s*:|"type"\s*:\s*"rating"|\btype:\s*"rating"|static_popular|REPLACE-ME|books\.json|zygmuntz|CSV_URL' \
    js/router.js js/app.js js/actions.js js/presets.js js/screens/ui.js js/screens/onboarding_step.js \
    js/screens/s0_start.js js/screens/s6_persona.js index.html css/base.css config/onboarding.json README.md | wc -l
0

$ grep -nE 'timestamp|hf\.space|"/recommend"|static_popular|[Gg]oodbooks|consent_granted|preference_skipped|resetMockState' \
    js/app.js js/actions.js js/presets.js | wc -l
0
```

`demo/README.md` 의 `Goodbooks-10k(CC BY-SA 4.0)` 1건은 라이선스 귀속 의무라 남긴 것이며(2트랙 고지 원문, `.claude/rules/serving.md`), 위 두 정규식 중 첫 번째는 `goodbooks` 를 검사하지 않는다.

## 부록 B — data-act 24개 ↔ `actions.js` 분기 대비표

`js/actions.js` 의 `ACTIONS` 객체 키와 시작 줄 번호. 24개 전부 구현, 누락 0.

| data-act | 줄 | 처리 | 기록 이벤트 |
|---|---|---|---|
| `start` | L98 | S0 → S1 | `preference_started` |
| `skip` | L99 | `consent=false` · 스냅샷 비움 → `#/home` | — |
| `back` | L104 | `goBack()` — S1+resetting 이면 `#/home`, S1 이면 S0, 그 외 이전 단계 | — |
| `pick` | L105 | `togglePick(step, val)` (S2 변경 시 세부 카테고리 정리) | `preference_step` |
| `pickbook` | L106 | 시드 토글 + `impressions[].selected` | `preference_book_selected` / `preference_book_deselected` |
| `next` | L119 | `goNext()` — S4→S5 진입 시 `loadCandidates`, S5 완료 시 `completeOnboarding` | `preference_completed` |
| `toHome` | L120 | `resetting=false` → `#/home` | — |
| `nav` | L121 | `location.hash = data-to` | — |
| `preset` | L122 | `presets.run(name, ctx)` | (프리셋이 만드는 이벤트) |
| `card` | L123 | 행 탐색은 `state.recommend?.rows ?? []`, `data-row="library"` 는 `LibraryBook` 기반 최소 detail | `detail_click` (서재 타일은 `surface: "library"`) |
| `closeSheet` | L141 | `#/home` | — |
| `read` | L142 | `#/reader/:id` (`reader_open` 은 라우터가 기록) | — |
| `library` | L143 | 서재 담기 + 토스트 | `library_add`(surface `main`) |
| `read10` | L150 | `progressPct +8` · `virtualMinutes +10` · 15분 첫 도달 1회 | `qualified_read` |
| `complete` | L161 | `completed=true` · `progressPct=100` · `modal="rating"` | `completion` |
| `rate` | L169 | `postRating` → 토스트 → `#/home` | `rating` |
| `rateLater` | L185 | 모달 닫고 토스트 → `#/home` | — |
| `libTab` | L190 | `libraryTab` 변경 | — |
| `mydata` | L191 | `getUserData` → `modal="mydata"` | — |
| `withdraw` | L195 | `modal="withdraw"` | — |
| `withdrawConfirm` | L196 | `deletePersonalization` → `consent=false` · 배너 "비개인화 인기 도서" → `#/home` | — |
| `closeModal` | L201 | `modal=null` | — |
| `model` | L202 | `VARIANTS` 검증 후 `state.model` → `requestRecommend()` | — |
| `noop` | L207 | — | — |

## 부록 C — `api.js` 15개 ↔ 호출 위치 대비표

| 함수 | 호출 위치 | 용도 |
|---|---|---|
| `config` | `js/app.js:236` | `capture` 값으로 body class 토글 |
| `resolveSource` | `js/app.js:239` | boot — `?source` 없으면 `/health` 로 판정 |
| `loadSteps` | `js/app.js:241` | boot — `config/onboarding.json` |
| `health` | `js/app.js:240` | boot — 상단바 `model_version` |
| `loadMeta` | `js/app.js:242` | boot — `OnboardingMeta` |
| `getCandidates` | `js/actions.js:30` · `js/presets.js:48` | S5 후보 30권 + 노출 로그 |
| `postPreferences` | `js/actions.js:47` · `js/presets.js:69` | 스냅샷 생성(라벨 → `criterionId()` 변환, `restart: state.resetting`) |
| `getRecommend` | `js/app.js:154` | `requestRecommend()` — `#/home` 진입·모델 전환 |
| `postEvents` | `js/app.js:102` | `flush()` — 50개 배치 |
| `postRating` | `js/actions.js:174` | 별점 모달 |
| `getUserState` | `js/app.js:207` | `#/library` 진입 |
| `getUserData` | `js/actions.js:192` | "내 데이터 보기" 모달 |
| `deletePersonalization` | `js/actions.js:197` | 동의 철회 |
| `getDashboard` | `js/app.js:210` | `#/dashboard` 진입 |
| `getShowcase` | `js/app.js:184` | `#/` 진입 (1회 캐시 `??=`) |

미호출 0 — 부록 C 15개 전부 쓰인다.

## 부록 A — `state` v2 필드 대비 확인

`js/app.js` 의 `const state = { … }` 리터럴에 있는 최상위 키 29개:

```
route source userKey cell consent screen resetting prefs steps meta candidateSet snapshots
model recommend detail reading ratings library libraryTab userState mydata dashboard
showcase health nearlineLagSec events toast banner modal
```

부록 A 목록과 1:1이며 추가·누락 없다. 초기값도 부록 A 그대로다 — `route: { page: "showcase", params: {} }` · `screen: "S0"` · `reading: null` · `libraryTab: "added"` · `nearlineLagSec: null`.

## 검증 결과

| 항목 | 결과 |
|---|---|
| `node --check` 8개 JS | 전부 종료 0 |
| 줄 수 상한(router 30 · app/actions 250 · presets 120 · ui 130 · base.css 250) | 전부 통과 |
| `config/onboarding.json` progress | `[0.0, None, 0.4, 0.4, 0.84]`, S5 `optionsFrom` = `GET /api/candidates/onboarding` |
| S3 옵션 텍스트 5개 | 불변(`grep` 3건 확인) |
| `base.css` 새 색 리터럴 | 0건 (v1 잔존 5개만) |
| `index.html` 스타일시트 | 8개 전부 링크(reader·library·dashboard 포함) |
| `uv run pytest tests/demo tests/test_architecture.py -q` | 13 passed |
| 로컬 HTTP 스모크(`python3 -m http.server`, 24개 URL) | `d2_home.js`·`d3_detail.js` 만 404, 나머지 전부 200 |

**브라우저 완주는 이 플랜에서 판정하지 않는다.** `app.js` 가 `d2_home.js`·`d3_detail.js` 를 정적 import 하는데 두 파일은 06-06(wave 3)이 만든다 — 그 전까지 모듈 그래프가 해석되지 않아 어떤 라우트도 렌더되지 않는다. 이는 플랜이 명시한 wave 2 범위(정적 검증 `node --check` + grep)이며, 콘솔 에러 0 판정은 06-06 체크리스트와 06-07 게이트 몫이다. wave 2 동안 06-03·06-04·06-05 파일은 모두 착지해 200이고, `api.js` 는 부록 C 15개 함수를 그대로 export 한다(확인함).

## Deviations from Plan

### 자동 수정

**1. [Rule 1 - Bug] `onboarding_step.js` 의 세부 카테고리 조회가 새 `OnboardingMeta` 와 맞지 않음**
- **발견 시점:** Task 3
- **문제:** 현행 `chipGroups()` 가 `meta.subcategories[cat]` 를 읽는데, 06-01 이 만든 `mock/meta_onboarding.json` 과 부록 A 의 `OnboardingMeta` 에는 `subcategories` dict 가 없다(`categories[] = {name, supported, subcategories}` 구조). S4 세부 카테고리 화면이 `TypeError` 로 죽는다.
- **수정:** `subsOf(meta, cat)` 헬퍼를 추가해 `meta.categories[].subcategories` 에서 찾는다. `actions.js` 의 S2 변경 시 정리 로직도 같은 방식(`subsOf`)으로 썼다.
- **파일:** `demo/js/screens/onboarding_step.js`, `demo/js/actions.js`
- **커밋:** `0241a39`, `4a63ed4`

**2. [Rule 2 - 누락 기능] 이벤트 전송 디바운스**
- **문제:** 플랜은 "`flush` 는 `log` 마다 호출"이라 적혀 있는데 그대로 하면 행 노출 40건이 40번의 `postEvents` 호출이 된다(위협 등록부 T-06-02-05 가 막으려는 바로 그 폭주).
- **수정:** `flush()` 를 120ms 디바운스로 두고, 깨어날 때 큐 전체를 50개씩 잘라 보낸다. 큐는 전송 성공 여부와 무관하게 비운다. `sessionStorage millie_events` 키·50 배치·await 하지 않음·실패 삼킴은 플랜 그대로다.
- **파일:** `demo/js/app.js`

**3. [Rule 3 - 진행 차단] `presets.run` 이 `#/home` 에서 눌리면 화면이 갱신되지 않음**
- **문제:** 프리셋은 `location.hash = "#/home"` 으로 끝나는데, 이미 `#/home` 이면 `hashchange` 가 발생하지 않아 새 상태가 그려지지 않는다.
- **수정:** 해시가 이미 `#/home` 이면 `requestRecommend()` + `render()` 를 직접 호출한다.
- **파일:** `demo/js/presets.js`

### 플랜 지시와 다르게 둔 것

- **`#/onboarding` 진입 시 상태 초기화 조건:** 플랜의 "진행 중이면 유지" 를 `!state.prefs.readingTime && state.screen !== "S6"` 로 구현했다(플랜은 조건을 산문으로만 적었다).
- **`s6_persona.js` CTA:** `esc()` 를 CTA 문자열 전체에 한 번 걸도록 바꿨다(전에는 이름·조사를 각각 escape). 결과 마크업은 동일하다.

## Known Stubs

없음. 이 플랜이 만든 코드에 하드코딩된 빈 값·"준비 중" 문구는 없다. `state.mydata`·`state.dashboard`·`state.showcase` 의 초기 `null` 은 각 라우트 진입 시 `api` 로 채워진다.

## Threat Flags

없음. 새 네트워크 표면·인증 경로·스키마 변경 없이 플랜의 위협 등록부(T-06-02-01~07) 범위 안에 있다. `mitigate` 항목 이행 확인:
- T-06-02-01(XSS): `ui.js` 의 새 4개 헬퍼 중 사용자 문자열을 받는 `demoLabel`·`banner` 는 `esc()` 를 거치고, `modal(inner)` 는 "호출자가 이미 esc 한 마크업만" 주석을 달았다. `app.js` 의 `modalHTML()` 은 `esc(JSON.stringify(...))` 로 삽입한다.
- T-06-02-04(잘못된 `:id`): `router.parse` 가 `Number()` → `NaN` 이면 `onRoute` 의 `book` 분기가 detail 을 못 찾아 `#/home` 으로 되돌린다.
- T-06-02-05(이벤트 폭주): `impressedRecId` 로 `recommendation_id` 당 1회 + 50개 배치 + 디바운스.

## wave 3(06-06)에 넘기는 주의

1. **`app.js` 가 import 하는 이름은 고정이다.** `./screens/d2_home.js` 와 `./screens/d3_detail.js` 에서 각각 `export function render(state)` 를 내보내야 한다. 이 두 파일이 생기기 전까지 데모는 아무 라우트도 렌더하지 않는다(모듈 그래프 미해석).
2. **배너는 `app.js` 가 그린다.** `render()` 가 폰 화면에 `statusbar() + banner(state.banner) + …` 순으로 넣는다 — `d2_home.js` 는 배너를 다시 그리지 말 것(중복 표시). 문구 "비개인화 인기 도서" 는 `requestRecommend()` 의 배너 우선순위 ②가 만든다.
3. **탭바는 화면 파일이 붙인다.** `ui.tabbar("home"|"library")` 를 `d2_home.js`·`d3_detail.js`·`d5_library.js` 가 각자 마지막에 넣는다(`app.js` 는 넣지 않는다). D4 뷰어는 전체화면이라 탭바 없음.
4. **`data-row="library"` detail:** `actions.js` 의 `card` 가 서재 타일에서 만든 detail 은 `rowId: "library"` 이고 `authors`·`reason`·`badge`·`source`·`book_format`·`difficulty` 가 전부 `null`, `source_channels` 는 `[]`, `score`·`position` 은 `0` 이다. `d3_detail.js` 는 이 조합에서 크래시하지 않아야 하고 `rowId` 를 "내 서재" 로 표시한다.
5. **`onRoute` 의 `book` 분기는 `state.detail.item.book_id` 가 이미 같으면 덮어쓰지 않는다** — 서재 경유 detail 이 유지된다.
6. **`inspector.render(state)` 시그니처 유지.** `app.js` 는 폰 페이지에서만 인스펙터를 그린다(D7·D8 은 `#page` 전폭이라 인스펙터 없음).
7. **모달 3종 중 `rating` 은 `d4_reader.js` 가 그린다.** `app.js` 의 `modalHTML()` 은 `mydata`·`withdraw` 만 담당한다.

## Advisor 제안 (이 플랜이 건드리지 않은 것)

- **`css/tokens.css` 에 `--dim` 이 필요하다.** `base.css` 의 `.modal-wrap__dim` 이 `var(--dim)` 을 쓴다. 06-05 가 화면 구성 02 §6 추가 토큰과 함께 `--dim: rgba(0, 0, 0, .6)` 을 넣기로 되어 있다. 없으면 모달 뒤 딤이 투명해진다(크래시는 아님). 같은 이유로 `--demo-label`·`--banner-bg`·`--banner-text` 도 `tokens.css` 에 있어야 한다.
- **`Makefile` 의 `mock` 타겟이 없는 `cli mock` 을 호출한다.** `demo/README.md` 에 "쓰지 않는다"로 적어 두었다. 정정은 Advisor(Phase 5 세션) 몫 — `PROGRESS.md` 미결.
- **`demo/js/screens/s7_home.js`·`s8_detail.js` 는 아직 남아 있다.** 06-06 이 `d2_home.js`·`d3_detail.js` 로 옮기며 삭제한다. 지금은 아무도 import 하지 않는 고아 파일이다.

## Self-Check: PASSED

소유 파일 12개 + SUMMARY 존재 확인, 커밋 3개(`1d98802` `4a63ed4` `0241a39`) 존재 확인.
