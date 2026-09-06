---
phase: 06-demo-rebuild
plan: 06
subsystem: Demo (메인·상세·인스펙터 + mock 완주 검증)
tags: [demo, D2, D3, inspector, walkthrough]
requires: [06-01, 06-02, 06-03, 06-04, 06-05]
provides:
  - "demo/js/screens/d2_home.js render(state) — D2 메인"
  - "demo/js/screens/d3_detail.js render(state) + dots() 재사용 — D3 책 상세"
  - "demo/js/inspector.js render(state) — 6섹션(신호 해석·여정·로그·latency·U_t·모델)"
affects: [06-07]
tech-stack:
  added: []
  patterns: [render(state) → string 순수 화면 파일, data-act 위임, 색은 tokens.css var() 전용]
key-files:
  created:
    - demo/js/screens/d2_home.js
    - demo/js/screens/d3_detail.js
  modified:
    - demo/js/inspector.js
    - demo/css/home.css
    - demo/css/inspector.css
  deleted:
    - demo/js/screens/s7_home.js
    - demo/js/screens/s8_detail.js
decisions:
  - "배너는 d2_home.js 가 그리지 않는다 — app.js 가 폰 셸에 이미 그린다(06-02 인계 2). 플랜의 `banner(state.banner)` 지시를 따르면 배너가 두 번 보인다"
  - "인스펙터의 클라이언트 fallback 판정은 client_fallback_reason 존재 여부 하나로 한다 — fallback_level 3 은 정상 익명 응답에도 나온다(06-03 인계)"
  - "home.css·inspector.css 의 색 리터럴 6개를 기존 토큰으로 치환(--dim·--chip·--bg·--panel-line·--kpi-bg) — 새 토큰 추가 없음"
  - "브라우저가 없는 실행 환경이라 완주 검증을 Node 구동 시뮬레이션으로 했다 — 실제 app.js·actions.js·router.js·mock.js·화면 8개를 그대로 돌리고 DOM·storage·fetch·location 만 shim"
metrics:
  duration: 약 75분
  tasks: 3
  files: 7
  completed: 2026-09-06
---

# Phase 6 '데모 재구성' Plan 06: 마지막 조립 Summary

`s7_home.js`·`s8_detail.js` 를 새 HTTP 계약 위의 `d2_home.js`·`d3_detail.js` 로 옮기고, 인스펙터를 페이지 기준 6섹션(`latency_breakdown` 막대 · `cell`/`forced` · 행별 `channel_mix` · `dedup_removed` · 모델 라디오 5 · Nearline 반영 · D3/D4 여정)으로 넓혔다. wave 1~3 산출물 6벌이 처음 한자리에서 만나는 지점이라 쇼케이스부터 관제 대시보드까지 완주를 실행해 74개 확인 항목 전부 통과, 콘솔 오류 0·404 0 을 실측했다.

## 무엇을 했나

| Task | 내용 | 커밋 |
|---|---|---|
| 1 | `d2_home.js`(← `s7_home.js`) · `d3_detail.js`(← `s8_detail.js`) · `home.css` | `6e01e27` |
| 2 | `inspector.js` 6섹션 확장 · `inspector.css` | `a03e83e` |
| 3 | 정적 게이트 + mock 완주 체크리스트(코드 변경 0) | 이 SUMMARY 커밋 |

두 커밋 모두 스테이징 목록을 확인하고 올렸다. `git show --stat` 에 이 플랜 소유 7경로 외의 파일은 0건이다.

## 변경 파일과 줄 수

| 파일 | 줄 | 플랜 상한 | 내용 |
|---|---|---|---|
| `demo/js/screens/d2_home.js` | 67 | 120 | 헤더(인사·프로필 칩·셀 배지) · 행(빈 행 숨김·subtitle) · 카드(배지·reason·저자·format pill·난이도 점) · TabBar |
| `demo/js/screens/d3_detail.js` | 51 | 90 | D2 배경 + 바텀시트(표지·제목·저자·배지·format·reason·source_channels·난이도 적합도·버튼 3) |
| `demo/js/inspector.js` | 180 | 200 | 신호 해석(page/screen) · D3/D4 여정 · 이벤트 로그 · latency · U_t · 모델 전환 |
| `demo/css/home.css` | 125 | 160 | 배지 6종 · `.cell-chip` · `.tile__fmt` · `.dots` · `.sheet__disabled` 추가, `.fb-note`·`.sheet__finish` 삭제 |
| `demo/css/inspector.css` | 75 | 110 | `.presets`·`.preset` 삭제, `.timeline-mini`·`.insp-flag` 추가 |

삭제: `demo/js/screens/s7_home.js`(53줄) · `demo/js/screens/s8_detail.js`(29줄). `git mv` 로 옮긴 뒤 내용을 다시 썼다.

## 1. 정적 게이트 (실행 출력)

```
$ cd demo && grep -rnE 'hf\.space|"/recommend"|\btimestamp\b|"format"\s*:|"type"\s*:\s*"rating"|\btype:\s*"rating"|static_popular|REPLACE-ME|books\.json|zygmuntz|CSV_URL' --include='*.js' --include='*.json' --include='*.html' --include='*.py' --include='*.md' --include='*.css' . | wc -l
0
$ for f in js/*.js js/screens/*.js; do node --check "$f" || echo "FAIL $f"; done      # FAIL 0건
$ wc -l js/*.js js/screens/*.js css/*.css | awk '$1>250{print "OVER", $0}'            # OVER 0건
$ grep -rn 'innerHTML' js/screens | wc -l        → 0
$ grep -rn 'href="javascript' js | wc -l         → 0
$ grep -rn 's7_home\|s8_detail' js | wc -l       → 0
```

페이즈 전역 게이트(오케스트레이터 지정)도 같이 확인했다.

```
$ grep -rnE 'hf\.space|REPLACE-ME|zygmuntz|static_popular|"timestamp"|books\.json' demo/     → 0건
```

`demo/README.md:91` 과 `demo/mock/showcase.json` 의 `data_notice` 에 있는 `Goodbooks-10k` 는 필수 데이터셋 귀속 표기라 그대로 뒀다.

테스트:

```
$ uv run pytest tests/demo tests/test_architecture.py -q     → 13 passed
$ uv run pytest -q --no-header                               → 529 dot, exit 0 (실패 0)
```

색 리터럴: `home.css` 0 · `inspector.css` 0(치환 전 6개 — `rgba(0,0,0,.6)`·`#232326`·`#202124`·`#101113`·`#232427`·`#1D1E21`).

## 2. mock 완주 체크리스트

### 검증 방법과 그 한계 — 먼저 읽을 것

이 실행 환경에는 사람이 조작할 브라우저가 없다. Playwright 류 자동화는 `../.claude/rules/demo.md` 가 Worker 에게 금지한다. 그래서 **실제 코드를 그대로 구동하는 Node 시뮬레이션**으로 완주했다: `demo/js/app.js` 를 그대로 import 하고, `document`·`localStorage`·`sessionStorage`·`fetch`·`location` 만 최소 shim 한 뒤 `data-act` 클릭과 라디오 change 를 실제 위임 핸들러에 흘려보냈다. `app.js`·`actions.js`·`router.js`·`api.js`·`mock.js`·`mock_store.js`·화면 8개·인스펙터는 손대지 않은 진짜 코드다. 하네스는 `.planning/` 밖(임시 디렉터리)에 있고 repo 에 남기지 않았다.

- **이 방법으로 확인되는 것:** 렌더 크래시·uncaught 예외·console.warn/error·404·라우팅·상태 전이·마크업에 있어야 할 문자열과 속성·이벤트 순서·인스펙터 값.
- **이 방법으로 확인되지 않는 것:** 실제 레이아웃·색·폰트·스크롤·표지 이미지 로드(`*.millie.co.kr` 핫링크)·애니메이션. **아래 표에서 "시각"으로 표시한 항목은 06-07 Advisor 가 브라우저에서 한 번 봐야 한다.**

`make demo-serve`(`python3 -m http.server 8080`) 는 별도로 띄워 HTTP 응답 코드를 확인했다: `/?source=mock` `/index.html` `/js/app.js` `/js/screens/d2_home.js` `/js/screens/d3_detail.js` `/js/inspector.js` `/css/home.css` `/css/inspector.css` `/mock/*.json` 4개 `/config/onboarding.json` 전부 **200**, 지운 `/js/screens/s7_home.js` 는 **404**(의도대로).

### 체크리스트 17항목

| # | 항목 | 기대 | 결과 | 콘솔 에러 |
|---|---|---|---|---|
| 1 | 쇼케이스 `#/`(D8) | 전폭 `#page` · 데모 라벨 · 비교표 4행(pop/cf/hybrid/hybrid_div) · `split_mode` 캡션 · 프리셋 3 · 데이터 고지 · 본인 5권 케이스 | ✅ (그림 3+1칸 배치는 시각) | 0 |
| 2 | `#/onboarding` S0 | "나와 비슷한 책 속의 주인공을 찾아볼까요?" · 건너뛰기 · 인스펙터 S0 해석 | ✅ | 0 |
| 3 | S1~S6 | S1 5택1 → S2 카테고리 ≤3(미지원 '미분류'·'오브제북' 비활성) → S3 기준 → S4 세부칩 → S5 후보 **30권** · 인스펙터 "30건 누적 · selected 5건" · `cand_84c3f6` → S6 페르소나 문장에 실제 카테고리·기준 삽입 | ✅ | 0 |
| 4 | `#/home`(D2) | 인사 "셜록 홈즈님, 저녁 독서 어때요?" · 셀 배지 `cell B · 데모 표시용` · 행 `anchor_1004`("『불편한 편의점』을 좋아하셨다면", 부제 "결이 비슷한 책") → `persona_shelf`("셜록 홈즈의 서가") → `trending` → `fresh_picks` · 빈 `continue_reading` 숨김 · 카드 43장 전부 저자 병기 · reason 9건 · format pill 오디오북·챗북 · 난이도 점 39개 · TabBar 홈 | ✅ | 0 |
| 5 | 인스펙터(D2) | `rec_f493a7` · `hybrid_v1` · `snap_d7b329` · `cell A [셀 배정]` · `fallback_level 0` · `dedup_removed 9권` · `Nearline 반영 1.0초` · latency 막대 5 + total 38.0 + `BUDGET 200ms` · `U_t = 0.70·explicit + …` · 행별 channel_mix `content`·`popularity` 만 | ✅ | 0 |
| 6 | 모델 라디오 | `Pop` → `pop_v1` · `cell A [forced (model= 지정)]` / `auto(셀 배정)` → `[셀 배정]` 복귀 | ✅ | 0 |
| 7 | 카드 탭 → `#/book/:id`(D3) | 바텀시트 · 채널 문구 "콘텐츠 유사도 이웃 — 제목·소개 TF-IDF(협업 필터링 아님)" · "난이도 적합도 ●●○ 가볍게" · 비활성 "이 책 추천하지 않기"(툴팁 production roadmap) · `data-act="read" data-book` · 인스펙터 `detail_click` | ✅ | 0 |
| 8 | 바로 읽기 → `#/reader/:id`(D4) | 데모 라벨 "실제 뷰어 아님" · 10분 읽기 ×2 → 16%·20분 · 인스펙터 타임라인 `● reader_open ● qualified_read ○ completion ○ rating` · T=15분 문구 · positivity bias 문구 | ✅ | 0 |
| 9 | 완독 → 별점 | "어떠셨나요?" ★×5 → ★4 → 토스트 "다음 책을 준비하고 있어요" → `#/home` 최상단 `after_completion` "『불편한 편의점』을 완독하셨네요, 다음은" | ✅ | 0 |
| 10 | 이어 읽기 등장 | 다른 책 열람 후 홈 → `continue_reading` 행 등장 | ✅ (아래 주의 참조) | 0 |
| 11 | `#/library`(D5) | 담은 책 5 · 읽는 중 1 · 완독 1 · 타임라인 `snap_…` · U_t 막대 · 버튼 3 | ✅ (저자 미상 5건 — 재위임 2번) | 0 |
| 12 | 서재 타일 → D3 | `rowId="library"`(authors·reason·badge·format·difficulty 전부 null) 에서 크래시 0 · "내 서재" 표시 · "저자 미상" · "난이도 적합도 — 완독지수 없음 · 카테고리 평균 기준" | ✅ | 0 |
| 13 | `#/refresh`(D6) | 헤더 "취향 다시 설정" · S0 생략 S1 부터 · 인스펙터 "Preference Refresh ≠ Profile Reset" · S5 CTA "새 취향으로 추천 받기" → 홈 앵커 시드 `anchor_1004`→`anchor_621` 로 교체 · `snapshot_id` 새 값 · 서재 타임라인 2개 | ✅ | 0 |
| 14 | 열람 · 철회 | "내 데이터 보기" JSON 모달(snapshots 2) → 닫기 → 철회 확인 모달 → 철회 → `#/home` 배너 "비개인화 인기 도서"(**1회만**) · 행 `trending`+`fresh_picks` · `fallback_v1` · `fallback_level 3` · 가중치 0 | ✅ | 0 |
| 15 | `#/dashboard`(D7) | 전폭 렌더 · KPI(QRS·p95·fallback) · MDE 고지 · BUDGET 200 | ✅ (KPI 6칸 배치·막대는 시각) | 0 |
| 16 | 프리셋 3 | `건너뛰기 유저` → 배너 비개인화·`fallback_v1` / `신규 유저 A` → `anchor_2623` 개인화 / `재설정 유저` → 타임라인 2개(`snap_98bc2d`,`snap_9a4635`) | ✅ | 0 |
| 17 | `?capture=1` / `=2` | body class `is-capture`(상단바+인스펙터 숨김) / `is-capture-2`(상단바만) | ✅ (실제 숨김은 `base.css` 규칙, 시각) | 0 |

**총계: 확인 항목 74개 전부 통과 · console.warn/error 0 · unhandledRejection 0 · fetch 404 0(총 5건 요청 전부 200).**

10번 주의: 앞 행(`after_completion` 등)에 이미 실린 책을 열람하면 dedup 규칙(`book_id` ∧ 정규화 제목)에 걸려 `continue_reading` 에서 빠진다. 처음엔 실패로 보였으나 `compose.dedup_rows` 사양대로 동작하는 것이었다. `trending` 의 책으로 다시 하니 `after_completion | continue_reading | anchor_1004 | persona_shelf | trending | fresh_picks` 로 정상. **06-07 검증 때도 이어 읽기 확인은 앞 행에 없는 책으로 해야 한다.**

### 배지 6종 확인 (DEMO-05)

S3 기준 5개를 각각 골라 완주해 실제로 렌더되는 배지 타입을 셌다.

| S3 선택 기준 | 렌더된 배지 타입 |
|---|---|
| 좋아하는 작가 | `author` 7개 |
| 좋아하는 출판사 | `publisher` 8개 |
| 베스트셀러 | `bestseller` 43개 |
| 화제작 | `buzz` 34개 |
| 리뷰·별점 | `review` + 3단 폴백 `bestseller` 39개 |

6종 중 5종이 mock 에서 실제로 나온다. `light`("가볍게")는 `mock.js:86` 주석대로 Should 라 생성기가 만들지 않는다 — CSS 는 `home.css` 에 준비돼 있어 서버가 내려주면 바로 그려진다. 범위 4분류상 정상이다.

### api 모드 (참고 — 완주 게이트는 Phase 7)

Phase 5 세션이 `src/millie_rec/serving/**` 를 편집 중이라 8000 포트를 피해 8021 로 잠깐 띄워 **읽기 요청만** 보냈다(쓰기 요청은 그 세션의 SQLite 카운트를 흔들 수 있어 하지 않았다).

| 경로 | 상태 |
|---|---|
| `/health` | 200 — `model_version: hybrid_div_v1`, `db_ok: true`, `artifacts_loaded_at: 2026-09-06T01:48:41Z` |
| `/` (데모 정적) · `/js/screens/d2_home.js` | 200 |
| `/api/recommend?seeds=1,2,3` · `/api/meta/onboarding` · `/api/showcase` · `/api/dashboard` | 전부 200 |
| `/js/screens/s7_home.js` | 404 (삭제 반영) |

`?source=api` 완주 자체는 06-CONTEXT D-09 대로 Phase 7 '배포' 사전 게이트다.

## 3. 06-CONTEXT 결정 이행

| 결정 | 이행 |
|---|---|
| D-07 개명 + 새 계약 필드 | `s7_home.js`→`d2_home.js`, `s8_detail.js`→`d3_detail.js`(`git mv`), `item.format`→`book_format`, `data-act="detail"`→`"card"`, 하드코딩 subtitle → `r.subtitle` |
| D-07b ① `static_popular` → `fallback_v1` | 인스펙터가 `model_version` 을 그대로 표시. `static_popular` 문자열은 `demo/` 전체에서 0건 |
| D-07b ② `latency_ms` float · 막대 비어도 크래시 0 | `STAGES.filter((k) => br[k] != null)` · breakdown 이 비면 total 막대 1개 · 전부 `Number(...).toFixed(1)` |
| D-07b ③ 같은 제목 다른 `book_id` | 라우팅·dedup 전부 `data-book`(book_id). 제목 비교 0. 카드·시트에 저자 병기(없으면 "저자 미상") |
| D-07b ④ `title` null | 카드·시트 모두 `title ?? "(제목 없음)"`. 이번 완주에서는 발동하지 않았다(모든 응답에 제목 있음) |

## 4. 계획과 달라진 점

### 1. [Rule 1 - 버그] `d2_home.js` 는 배너를 그리지 않는다 — 플랜 지시와 반대

- **플랜:** `banner(state.banner)` 를 D2 에 넣고 acceptance 로 `grep -c 'banner(state.banner)' == 1` 요구.
- **실제:** `app.js:134` 가 `statusbar() + banner(state.banner) + screenHTML() + …` 로 이미 폰 셸에 그린다. 06-02-SUMMARY "wave 3(06-06)에 넘기는 주의" 2번이 "`d2_home.js` 는 배너를 다시 그리지 말 것(중복 표시)" 이라고 못박았다. 플랜대로 하면 철회 후 홈에서 "비개인화 인기 도서" 배너가 **두 줄** 보인다.
- **판단:** 06-02 는 플랜이 쓰인 뒤에 구현됐고, 실제 셸이 정본이다. 배너 호출을 넣지 않았다. 완주 14번에서 배너가 정확히 1회만 나오는 것을 실측했다.
- **영향:** 플랜 acceptance 1줄 미충족(`banner(state.banner)` 0건). 나머지 acceptance 는 전부 충족.

### 2. [Rule 3] 커밋했다 — 플랜 frontmatter `no_commit: true` 와 다름

06-01~06-05 는 전부 태스크 단위로 커밋했고(`git log`), 오케스트레이터 지시도 "commit each task atomically" 였다. 같은 관례를 따랐다. 두 커밋 모두 스테이징 목록을 확인해 이 플랜 소유 경로만 담았다.

### 3. `git mv` 로 옮겼다 — 플랜은 "새 파일 + rm"

히스토리에 개명이 남도록 `git mv` 후 내용을 다시 썼다. 내용이 절반 이상 바뀌어 git 이 rename 으로 표시하지는 않지만 결과 파일 집합은 같다.

### 4. `.insp-flag` 를 실제로 쓴다

플랜은 CSS 규칙만 추가하라고 했으나 쓰이지 않는 CSS 가 남는다. `cell` 의 `forced`/`셀 배정`, `fallback_level` 의 `client`, `source` 의 client fallback 사유를 이 클래스로 렌더하도록 `modelSection` 의 행 구조를 `[key, value, flag]` 3튜플로 바꿨다.

### 5. 저자 결측 표기를 "저자 미상" 으로

플랜 예시는 `esc(item.authors ?? "")` 였다. 06-04 의 `d5_library.js` 가 이미 "저자 미상" 을 쓰고 있어 화면 간 문구를 맞췄다. D-07b ③(저자로 동명 도서 구분)의 취지에도 빈 칸보다 낫다.

### 6. 색 리터럴 치환에 새 토큰을 만들지 않았다

`--dim`(모달·시트 딤) · `--chip`(`#232326` → 추천 이유 박스) · `--bg`(`#101113` → 이벤트 로그) · `--panel-line`(`#232427` → latency 트랙) · `--kpi-bg`(`#1D1E21` → U_t 카드). 육안 차이 없는 근사값이고 `tokens.css`(06-05 소유)는 건드리지 않았다.

## 5. 재위임 목록 (06-07 Advisor 가 라우팅)

이 플랜 소유 5파일 밖의 관측이다. 하나도 고치지 않았다.

| # | 파일(소유 플랜) | 증상 | 제안 수정 |
|---|---|---|---|
| 1 | `demo/js/app.js:134`(06-02) | 배너를 폰 셸에서 모든 화면에 그린다. 철회 후 `#/library` 로 가도 "비개인화 인기 도서" 배너가 따라온다(화면 구성 02 §2 는 D2 요소로 규정) | 그대로 둘지 D2 전용으로 옮길지 Advisor 판단. 옮긴다면 `app.js` 의 `banner(state.banner)` 를 빼고 `d2_home.js` 에 한 줄 추가(내 파일 수정은 재위임으로 받겠다) |
| 2 | `demo/js/screens/d5_library.js:26-29`(06-04) + `serving/schemas.py:239 LibraryBook`(계약) | 서재 "담은 책" 5권 전부 저자가 "저자 미상". `authorOf` 가 `state.recommend.rows` 에서 찾는데 시드 5권은 dedup `exclude` 로 행에 실리지 않는다. D-07b ③ 의 동명 도서 구분이 D5 에서만 깨진다 | `LibraryBook` 에 `authors: str \| None = None` optional 추가(06-05 가 `ShowcaseBook` 에 대해 낸 제안과 같은 종류) → mock `card()` 와 `authorOf` 폴백 한 줄. 계약 freeze 중이라 Advisor 결정 |
| 3 | `demo/css/base.css`(06-02) 7건 · `demo/css/onboarding.css`(재사용 원본) 9건 | 색 리터럴이 `tokens.css` 밖에 남아 있다. `base.css:18 #1F2024` `:40 #000` `:41 rgba(0,0,0,.55)` `:71 rgba(18,18,18,0)` `:80 rgba(255,255,255,.45)` `:84 #FFFFFF/#1A1A1A` `:144 #1A1B1E` / `onboarding.css:13,44,74,79,85,91,107,118,122` | Should. `base.css:129 .modal-wrap__dim` 은 이미 `var(--dim)` 이라 치환이 끝났다. 나머지는 06-07 이 일괄 판단 |
| 4 | `demo/js/mock.js:86`(06-03) | `light` 배지를 생성하지 않아 6종 중 5종만 실제로 보인다 | 의도된 Should 미구현. 고칠 필요 없음 — PDF·검증 문구에서 "6종 중 5종 실측"으로 쓰면 된다 |
| 5 | `demo/js/inspector.js`(내 파일) + `demo/js/app.js`(06-02) | 미지원 카테고리 인스펙터 행이 실전에서 뜰 수 없다. S2 에서 미지원 카테고리 버튼이 `disabled` 라 `prefs.categories` 에 들어갈 경로가 없다 | 방어 코드로 남겨 둔다(프리셋·api 응답이 미지원 이름을 넣을 수 있다). 조치 불필요 |
| 6 | `demo/fallback/popular.json` | 내 작업 시작 전부터 워킹 트리에 수정 상태로 있다(내가 만든 변경 아님) | 06-07 또는 Phase 5 세션이 커밋 여부 판단 |

## 6. 위협 모델 이행

| Threat ID | 이행 |
|---|---|
| T-06-06-01 XSS | 제목·저자·reason·행 제목·배지·채널 문구·`data-*` 값 전부 `esc()`. 화면 파일 `innerHTML` 0(게이트) |
| T-06-06-02 `data-book` 조작 | `book_id` 없으면 `actions.card` 가 무동작, `onRoute` 가 `#/home` 으로 되돌린다(06-02) — 수정 없음 |
| T-06-06-03 `client_fallback_reason` 노출 | 클라이언트 문자열(`HTTP 404 /api/…`)만. mock 에서는 아예 붙지 않음 |
| T-06-06-04 표지 핫링크 | `ui.cover` 의 `referrerpolicy="no-referrer"` + onerror 플레이스홀더 그대로 사용 |
| T-06-06-05 빈 breakdown 크래시 | `br[k] != null` 필터 + total 폴백. 철회 직후 `recommend: null` 경로도 완주 14번에서 크래시 0 |
| T-06-06-06 mock latency 오인 | 인스펙터 힌트가 source 별로 갈린다("mock 지연은 결정적 표시값 — PDF 숫자가 아님" / "서버 실측 · 참고용") |

## Known Stubs

없다. 다섯 파일 모두 실제 응답(`RecommendOut`)과 세션 상태에 연결돼 있고, 하드코딩한 빈 배열·플레이스홀더 문구는 없다. `light` 배지 CSS 는 스텁이 아니라 서버가 내려주면 즉시 쓰이는 표시 규칙이다.

## Threat Flags

없다. 새 네트워크 엔드포인트·인증 경로·파일 접근·스키마 변경을 만들지 않았다(순수 렌더러 3 + CSS 2).

## Self-Check: PASSED

```
FOUND: demo/js/screens/d2_home.js        FOUND: demo/js/screens/d3_detail.js
FOUND: demo/js/inspector.js              FOUND: demo/css/home.css
FOUND: demo/css/inspector.css            GONE : demo/js/screens/s7_home.js (의도된 삭제)
GONE : demo/js/screens/s8_detail.js (의도된 삭제)
FOUND: 6e01e27  FOUND: a03e83e
```
