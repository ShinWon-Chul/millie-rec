---
phase: 06-demo-rebuild
plan: 05
subsystem: Demo (PC 전폭 페이지 — 쇼케이스·관제 대시보드)
tags: [demo, showcase, dashboard, css-tokens, DEMO-06, DEMO-08]
requires:
  - "demo/mock/showcase.json · demo/mock/dashboard.json (06-01 산출)"
  - "demo/js/screens/ui.js 의 esc·cover·badge·demoLabel (06-02 소유)"
  - "demo/js/api.js getShowcase()·getDashboard() (06-03 소유)"
provides:
  - "demo/js/screens/d8_showcase.js — render(state) → 쇼케이스 랜딩 HTML"
  - "demo/js/screens/d7_dashboard.js — render(state) → 관제 대시보드 HTML"
  - "demo/css/dashboard.css — D7·D8 공용 스타일"
  - "demo/css/tokens.css — 화면 02 §6 토큰 12개 + 모달 딤 --dim"
affects:
  - "demo/index.html (06-02 가 css/dashboard.css 링크 · app.js 가 d7·d8 import — 이미 반영됨)"
  - "demo/css/base.css (06-02 가 .modal-wrap__dim 에서 var(--dim) 사용 가능)"
tech-stack:
  added: []
  patterns:
    - "화면 파일 = 순수 함수 render(state) → string, 이벤트는 data-act 만 (부록 E)"
    - "차트는 CSS 막대·inline 계산만 — 프론트 의존성 0"
    - "색 리터럴은 css/tokens.css 한 곳, 나머지 CSS 는 var(--…) 만"
key-files:
  created:
    - demo/js/screens/d8_showcase.js
    - demo/js/screens/d7_dashboard.js
    - demo/css/dashboard.css
  modified:
    - demo/css/tokens.css
decisions:
  - "ShowcaseBook 에 authors 필드가 없어 동명 도서 구분은 book_id 병기로 대체 (D-07b 저자 병기의 이 화면 한정 대체)"
  - "memorable_5[].route 를 href=\"#/\" + 꼬리 문자열로만 조립해 javascript: URL 을 구조적으로 차단"
  - "KPI 색 규칙을 KPI 표의 4번째 원소로 이동 — kpi 이름 문자열이 파일에 한 번만 나오게"
metrics:
  duration: "약 45분"
  tasks: 3
  files: 4
  completed: 2026-09-06
---

# Phase 6 Plan 05: 쇼케이스(D8) · 관제 대시보드(D7) Summary

`ShowcaseOut`·`DashboardOut` 응답 하나만으로 PC 전폭 2페이지를 그리는 순수 렌더러 2개와 그 공용 CSS, 그리고 화면 구성 02 §6 토큰 13개를 추가했다. 화면에 뜨는 숫자는 전부 응답에서 오고 파일 안에 지표 값 하드코딩은 0건이다.

## 1. 변경 파일 (커밋 3개)

| 파일 | 상태 | 줄 수 | 상한 | 커밋 |
|---|---|---|---|---|
| `demo/css/tokens.css` | 토큰 13개 추가(기존 43줄 보존) | 52 | 60 | `5322007` |
| `demo/css/dashboard.css` | 신규 | 113 | 250 | `5322007` |
| `demo/js/screens/d8_showcase.js` | 신규 | 101 | 200 | `a1286a9` |
| `demo/js/screens/d7_dashboard.js` | 신규 | 114 | 200 | `df4171d` |

커밋은 전부 `git commit --no-verify … -- <경로>` 형태로 소유 파일만 지정해 넣었다. 삭제된 파일 0건, 다른 플랜의 파일이 섞인 커밋 0건.

> 플랜 frontmatter 는 `no_commit: true`(2026-09-05 관례)였으나, 이번 실행 지시는 태스크별 원자 커밋을 명시했다. 병렬 4개 세션이 같은 작업 트리를 쓰는 상황에서 경로 지정 커밋이 오히려 서로의 변경을 지키는 방향이라 지시를 따랐다. push 는 하지 않았다.

## 2. 토큰 13개 확인 (화면 구성 02 §6 + 모달 딤)

`--difficulty-on` `--difficulty-off` `--star` `--star-off` `--banner-bg` `--banner-text` `--kpi-bg` `--kpi-good` `--kpi-warn` `--kpi-bad` `--light-badge` `--demo-label` `--dim` — 13개 전부 문자 단위로 §6 블록과 동일하다. 기존 `--accent: #F5E06E;` 등 43줄의 값은 하나도 바뀌지 않았다.

`demo/` 전체 CSS·JS 가 참조하는 커스텀 속성을 `tokens.css` 정의와 대조한 결과 미정의는 `--ph` 하나뿐이고, 이는 `ui.js` 의 `cover()` 가 인라인 `style` 로 직접 넣는 표지 플레이스홀더 색이라 토큰이 아니다. 즉 **wave 2 시점에 빠진 토큰은 없다.** `dashboard.css` 의 색 리터럴은 0건이다.

## 3. 화면 구성 02 §2 표 ↔ 마크업 대응

### D8 쇼케이스 랜딩 (`#/`)

| §2 D8 요소 | 티어 | 마크업 | 데이터 출처 |
|---|---|---|---|
| 헤더 + 철학 2줄 + `model_version` + `/docs` | Must | `.page-head` `.philosophy` `.page-head__meta` | `state.showcase.philosophy` · `state.health.model_version` |
| 평가 3지표 비교표(variant 4행 × Recall@20·NDCG@10·ILD@10 + p95) | **Must** | `table.dt` 5열, 최고 Recall 행에 `.is-best` | `eval_table.rows[]` |
| `split_mode` 캡션 + 출처 캡션 | **Must** | `.caption` — `temporal` 일 때만 `(train.ts.max < test.ts.min 단언 통과)` 덧붙임 | `eval_table.split_mode` · `source.metrics` · `source.p95` |
| 단계↔지표 1:1 대응 그림(CSS) | **Must** | `.mapping` 4칸, 화살표는 `::before` | `metric_mapping[]` 3 + 지표 없는 `Page Composition` 칸 |
| 시작 버튼 + 프리셋 3 | Must | `data-act="nav" data-to="#/onboarding"` · `data-act="preset"` × 3 | — |
| 데이터 고지(2트랙) | Must | 마지막 `section` `.caption` | `data_notice` 원문 그대로 |
| 카드 5 "기억할 5가지" | Should | `.memo__card` × 5 + 바로가기 링크 | `memorable_5[]` |
| 본인 5권 → 추천 10 + 캡션 | Should | `.case` 2열 · `.case__grid` · `데모 이웃 = 콘텐츠 유사도(협업 필터링 아님)` | `personal_case` (없으면 `.case__wait` "5권 선정 대기") |
| 로드맵 회색 카드 | Could | `.roadmap__card` + `roadmap` 태그 | `roadmap[]` |
| 문장 카드 3 | Could | **생략** (§9 티어대로) | — |

### D7 관제 대시보드 (`#/dashboard`)

| §2 D7 요소 | 마크업 | 비고 |
|---|---|---|
| KPI 카드 6 + 표본 n 병기 | `.kpi__card` × 6, `.kpi__v` 32px monospace, `.kpi__n` | 이름 6개는 `kpi` 딕셔너리 키 그대로 |
| p95 카드 "서버 실측 · 참고용" 라벨 | `.ref-label` | p95 카드에만 |
| A/B 표 10열 + MDE 고지 | `table.dt` + `.caption` | 고지는 `mde_note` 원문("데모 표본으로 검정하지 않음 — MDE +1%p 검출에 셀당 n만 명") |
| latency 단계별 p50/p95 막대 + 예산선 | `.bar` `.bar__fill.is-p95` `.bar__budget` | 예산선은 `BUDGET_MS = 200`(`contracts.BUDGET_MS`) 하나만 상수 |
| latency 헤더 "서버 실측(참고용) · PDF 수치는 로컬 bench" | `.ref-label` | |
| 품질 패널 3(수신율·flag·freshness) | `table.dt` | |
| 이벤트 스트림 최근 50 | `.stream__row` — 시각·`event_type`+book_id·rec/model/snapshot | `user_key` 컬럼 없음(T-06-05-04) |
| 노출 로그 + "미선택 ≠ negative" + `survey_variant=v1` | `.stream__row` + `.caption` + `.ref-label` | |
| 모델별 요청 분포 | `.bar` (최댓값 정규화) | |
| 시간대 분포(Could) | **생략** — `by_hour` 참조 0건 | |

## 4. 숫자 출처 확인

- **D8** — `demo/mock/showcase.json` 을 그대로 넣고 렌더한 결과 문자열에 `0.063` `0.764` `holdout` `79.5` `results/latest.csv` `Goodbooks-10k`(고지문 안) 가 그대로 나온다. 반올림·보정·예시 행 추가 0건. `p95_ms` 가 `null` 인 `pop`·`cf` 는 `—` 로, 전 행이 null 이면 캡션에 "로컬 bench — 아직 없음" 이 붙는다.
- **D7** — `demo/mock/dashboard.json`(빈 세션 골격)을 넣으면 KPI 6개가 전부 `0.0%`/`0`, A/B 표는 "아직 표본이 없습니다", 스트림은 "아직 이벤트가 없습니다" 로 그려진다. **빈 세션에 0이 뜨는 것이 정상 동작이다.** 세션 이벤트가 들어온 형태(`by_stage` 2단계·A/B 1행·스트림 1건)를 넣으면 단계별 막대·`25.0%`·`is-bad`(p95 412ms > 예산 200ms) 가 모두 정상 렌더된다.
- mock 모드의 세션 집계 자체는 06-03 의 `getDashboard()`/`mock_store.js` 몫이다. 이 플랜은 **집계 결과를 그리는 쪽**만 담당하며 자체 집계·보정을 하지 않는다.

## 5. 검증 결과

| 항목 | 결과 |
|---|---|
| `node --check` (d7·d8) | 종료 0 |
| 줄 수 상한 4파일 | 52 / 113 / 101 / 114 — 전부 통과 |
| `tokens.css` 토큰 13개 문자 단위 | 13/13 존재, `--accent: #F5E06E;` 보존 |
| `dashboard.css` 색 리터럴 | 0건 |
| d8 하드코딩 금지 정규식(`innerHTML`·`fetch(`·`0.0NN`·철학 첫 구절·`Goodbooks-10k`) | 0건 |
| d7 하드코딩 금지 정규식(`innerHTML`·`fetch(`·`value: N`) · `by_hour` | 0건 / 0건 |
| kpi 이름 6개 라인 수 | 정확히 6 |
| 구 형태 정규식(`hf.space`·`timestamp`·`"format":`·`type:"rating"`·`static_popular`·`books.json` 등) 소유 4파일 | 0건 |
| import | 두 화면 모두 `./ui.js` 한 줄만 |
| XSS | 응답 문자열 전부 `esc()` 통과 — `mde_note` 에 `<img onerror>` 를 넣으면 `&lt;img` 로 출력됨 |
| `uv run pytest tests/demo tests/test_architecture.py -q` | 13 passed |

렌더 스모크는 repo 밖 스크래치패드에서 `ui.js` + 화면 파일을 CommonJS 로 합쳐 실행했다(브라우저 자동화 금지 규칙 준수, `../.claude/rules/demo.md`). 실제 브라우저 확인은 06-06·06-07 몫이다.

## 6. 위협 모델 이행

| Threat ID | 처리 |
|---|---|
| T-06-05-01 응답 문자열 XSS | 전 삽입 지점 `esc()`, 화면 파일은 문자열 반환만, `innerHTML` 0건 |
| T-06-05-02 `route` 에 `javascript:` URL | `href="#/${routeTail(route)}"` — `#/` 로 시작하지 않는 값은 꼬리가 빈 문자열이 되어 `#/` 로 떨어진다. 스킴 URL 자체를 만들 수 없다 |
| T-06-05-03 D7 숫자를 PDF 숫자로 오인 | p95 카드 "서버 실측 · 참고용", latency 헤더 "PDF 수치는 로컬 bench", D8 출처 캡션 2종 |
| T-06-05-04 스트림의 user_key 노출 | 스트림에 `user_key` 컬럼 없음(시각·event_type·book_id·rec/model/snapshot 만) |
| T-06-05-05 null·빈 배열 크래시 | `state.dashboard`·`state.showcase` null 분기 + 전 필드 `?.`/`?? []`. 빈 `dashboard.json`·`null` 양쪽 렌더 확인 |
| T-06-05-06 `window.opener` | `/docs` 링크에 `rel="noreferrer"` |

## 7. 06-06 · 06-07 로 넘기는 확인 항목

1. **프리셋 3 버튼 실제 동작** — 이 플랜은 `data-act="preset" data-preset="newUser|skipUser|resetUser"` 마크업만 찍는다. 실행은 06-02 `presets.js`. 버튼 3개가 실제로 상태를 바꾸는지 브라우저에서 확인 필요.
2. **`#page` 전폭 컨테이너 분기** — D7·D8 이 `#phone` 이 아닌 `#page` 로 들어가는지(06-02 `app.js` 소관). `.page .demo-label { margin:-32px -40px 20px }` 는 `#page` 패딩이 40px 좌우 / 32px 상단이라는 전제로 쓴 값이라, 06-02 의 실제 패딩과 다르면 이 한 줄만 맞추면 된다.
3. **`.cta` `.cover` `.badge` `.demo-label` 기본 스타일** — `base.css`(06-02) 소유. `dashboard.css` 는 `.start .cta { width:auto }` 처럼 덮어쓰기만 한다.
4. **api 모드 `/api/dashboard` 404** — 06-03 계층이 `null` 을 주면 "이 항목은 아직 없음" 이 뜬다. 서버가 200 인데 필드가 빠진 경우도 방어돼 있으나 실제 응답으로 한 번 확인 권장.
5. **캡처(화면 구성 02 §7)** — D7 은 P4 근거, D8 은 P4·P5 근거. `?capture=` 처리는 06-02·06-06 소관이며 이 두 화면은 전폭이라 폰 프레임 캡처 모드와 무관하다.

## Advisor 제안

이 플랜의 소유 밖이라 손대지 않고 남긴다.

1. **`ShowcaseBook` 에 `authors` 를 optional 로 추가** — D-07b 는 동명 도서 구분을 위해 카드에 저자를 함께 표시하라고 정했는데, `schemas_should.py` 의 `ShowcaseBook` 은 `book_id·title·image_url·reason·badge` 5필드뿐이라 저자를 그릴 수 없다. 임시로 `book_id` 를 병기해 구분은 되게 했다. 계약은 freeze 상태이므로 기본값 있는 optional 추가 판단은 Advisor 몫이고, 추가되면 `make_mock.py`(06-01)와 이 화면의 `.case__author` 한 줄만 바꾸면 된다. 카탈로그의 '도슨트북' 2권처럼 제목이 겹치는 케이스가 쇼케이스 5권/추천 10권에 들어오면 실제로 헷갈린다.
2. **`base.css` 의 모달 딤을 `var(--dim)` 으로** — `--dim: rgba(0,0,0,.6)` 를 `tokens.css` 에 넣어 뒀다. `base.css` 의 `.modal-wrap__dim` 이 아직 리터럴을 쓰고 있으면 06-02 쪽에서 치환하면 색 리터럴이 완전히 한 파일로 모인다.

## Known Stubs

없다. 두 화면 모두 실제 데이터 경로에 연결돼 있고, 비어 보이는 화면(빈 세션 0, `personal_case` 없음, `/api/dashboard` 404)은 스텁이 아니라 명세된 정상 상태다.

## Self-Check: PASSED

- `demo/js/screens/d8_showcase.js` FOUND · `demo/js/screens/d7_dashboard.js` FOUND · `demo/css/dashboard.css` FOUND · `demo/css/tokens.css` FOUND
- 커밋 `5322007` FOUND · `a1286a9` FOUND · `df4171d` FOUND
- 세 커밋의 변경 파일은 소유 4개뿐, 삭제 0건
