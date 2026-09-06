# Phase 6: 데모 재구성 - Context

**Gathered:** 2026-09-06
**Status:** Ready for planning

<domain>
## Phase Boundary

기존 `demo/` 27파일(v1 — Goodbooks-10k mock, S0~S8 선형 상태 머신, `hf.space` API_BASE)을 화면 구성 v2(D1~D8 해시 라우팅 8페이지, 밀리 카탈로그, 새 HTTP 계약 `serving/schemas.py`) 위로 재구성한다. 심사자가 쇼케이스(`#/`) → 취향 설정(`#/onboarding`) → 메인(`#/home`) → 책 상세(`#/book/:id`) → 뷰어 시뮬레이션(`#/reader/:id`) → 내 서재(`#/library`) → 취향 재설정(`#/refresh`) → 관제 대시보드(`#/dashboard`)를 눌러보며 설계 주장을 확인하고, `?source=api`에서는 로컬 서버의 실제 응답으로 그려진다.

**쓰기 영역:** `millie-rec/demo/**`만 (`demo/scripts/make_mock.py` 포함). `src/`·`contracts.py`·`serving/schemas*.py`·`app/`·`Makefile`은 건드리지 않는다 — Phase 5 '서빙 Must 완성'(`.planning/ROADMAP.md`)이 다른 세션에서 동시 진행 중이며 쓰기 영역이 겹치지 않는다(`src/millie_rec/serving/` ↔ `demo/`). 두 레인은 HTTP 계약(`serving/schemas.py`, freeze됨)으로만 만난다.

**이 페이즈가 아닌 것:** 서버 엔드포인트 구현(Phase 5) · 배포(Phase 7) · PDF 문장(Phase 8) · 새 화면 추가(v2 8페이지가 상한).

</domain>

<decisions>
## Implementation Decisions

### mock 모드의 상태 시뮬레이션 깊이
- **D-01 (경량 시뮬레이션, 스코어링 없음):** `?source=mock`은 밀리 카탈로그 위에서 **브라우저 내 상태 시뮬레이션**을 한다 — 스냅샷 append·완독 상태 변경·재설정 시 새 seed₁의 정적 이웃 top-20으로 앵커 행 교체·완독 시 `after_completion` 행 추가. **점수 계산은 하지 않는다**(이중 구현 금지, `.claude/rules/simplicity.md`). 이웃은 사전 계산된 테이블 조회만. mock 응답도 `serving/schemas.py` 형태(`latency_ms` float·`latency_breakdown`·`fallback_level`·`cell`·`user_state_weights`)를 그대로 채운다 — 값은 결정적 상수(예: α/β/γ는 스냅샷 수·완독 수로 계산한 표시값).
- **D-02 (아티팩트 축약본):** `demo/scripts/make_mock.py`가 빌드 시 `artifacts/serving/books_kr.json`에서 **카드 필드만**(book_id·title·authors·image_url·categories·millie_label·completion_prob·expected_min·category_avg·pop_rank·difficulty·formats) 뽑아 `demo/mock/catalog_kr.json`(≈2MB 목표)을, `artifacts/serving/item_edges_kr.json`에서 책별 이웃 top-20만 뽑아 `demo/mock/neighbors_kr.json`을 생성한다. **밀리 설명문·리뷰·큐레이터 노트 필드는 자동 제외**(`.claude/rules/data.md` 저작권 규칙 — 책 소개는 TF-IDF 입력 전용·미노출). mock은 이 두 파일만 읽는다. `make demo-serve` 단독(서버 없음)에서 동작해야 한다. **Phase 3 인계(STATE.md·03-06 SUMMARY §6): 현재 `make mock`은 v1 생성기가 v1 `popular.json`을 덮어쓰므로 재작성 전 실행 금지** — `make_mock.py` 재작성(wave 1)이 끝난 뒤에만 실행한다. `Makefile mock` 타겟은 `uv run python -m millie_rec.app.cli mock`을 호출하는데 `cli.py`에 `mock` 명령이 없다 → 생성기 진입점은 `demo/scripts/make_mock.py` 직접 실행으로 두고, `Makefile`·`cli.py` 정정은 Advisor(Phase 5 세션)에 제안.
- **D-03 (D7 대시보드 = 세션 이벤트 직접 집계):** mock 모드의 관제 대시보드는 이 브라우저 세션이 발생시킨 이벤트(sessionStorage 로그: impression·detail_click·reader_open·qualified_read·completion·rating·preference_*)를 **직접 집계**해 표시한다 — 노출 수신율·fallback 비율·행별 read-start·첫 완독 도달. A/B 표는 이 세션 1건이므로 하단에 v2 §2 D7 문구 그대로 "데모 표본으로 검정하지 않음 — MDE +1%p 검출에 셀당 n만 명" 고지. 고정 예시 숫자 금지(`숫자 = results/만` 규칙과 충돌).

### 재구성 vs 재작성 경계
- **D-04 (`app.js` 새로 쓴다):** 기존 275줄(S0~S8 선형 `ORDER`·`PRESET_PREFS`·`ACTIONS` 상태 머신)은 8페이지 해시 라우터와 구조가 맞지 않아 **새로 작성**한다. 계승하는 것: `state` 1개 + `setState` 1개 + `render` 1개 패턴, `log()` 이벤트 기록 유틸, 인스펙터 갱신 흐름. S0~S6 온보딩 단계 머신은 `js/screens/onboarding_step.js` 안으로 내려가 D1·D6이 공유한다. `js/router.js`(해시 파싱·`:id` 매칭, ≤30줄)를 추가한다.
- **D-05 (`mock.js` 폐기 후 새로):** 기존 206줄(정적 응답 조합 + 구 배지 타입 `rating`)은 D-01 시뮬레이션 구조와 맞지 않아 폐기. 새 `mock.js`는 `catalog_kr.json`·`neighbors_kr.json`을 읽어 D-01의 상태 시뮬레이션을 수행하고, 배지 6종(`bestseller`·`review` 3단 폴백·`author`·`publisher`·`buzz`·`light`)은 **표시 규칙**으로서 서버 `compose.py`와 같은 조건을 JS로 둔다(백엔드 서빙 01 §16 대응표 준수; 배지는 스코어링이 아니라 표시 규칙이므로 이중 구현 금지의 예외).
- **D-06 (구 데이터 전부 삭제):** `demo/mock/*.json` 7개(Goodbooks 400권 기반)와 `demo/fallback/popular.json`(Goodbooks)은 **삭제**하고 `make_mock.py`가 밀리 기반으로 재생성한다 — mock 10개(v2 §8 목록) + `fallback/popular.json`(`artifacts/serving/popularity_kr.json` 상위). Goodbooks 영문 제목이 데모 화면에 남을 경로 0. 데이터 2트랙 규칙(`../CLAUDE.md` §3-6): 데모 = 밀리 표본만.
- **D-07 (재사용 확정):** v2 §8 목록 그대로 — `css/tokens.css` `base.css` `onboarding.css` `home.css` `inspector.css`, `config/onboarding.json`, `js/screens/onboarding_step.js` `s0_start.js` `s6_persona.js` `ui.js`. `s7_home.js`·`s8_detail.js`는 D2·D3로 이름 변경 + 새 계약 필드로 수정(`latency_ms` float·`badge.type` 6종·`reason`). 완료 기준에 **구 형태 grep 0건**(`hf.space` · `"/recommend"` · `timestamp` · `"format"` · `"rating"` · `goodbooks` · `static_popular`)을 넣는다.
- **D-07b (Phase 3 인계 화면 이슈, 03-06 SUMMARY 관측):** ① `inspector.js` `"static_popular"` 라벨 → `fallback_v1`(model_version 그대로 표시) ② `latency_ms`가 float라 breakdown 막대가 비어도 크래시 없이 렌더 ③ 카탈로그에 **같은 제목 다른 book_id**('도슨트북' 2권)·플레이스홀더성 제목('무료')이 있다 — 화면은 `book_id`로 dedup·라우팅하고 제목만으로 동일성 판단 금지, 카드에 저자를 함께 표시해 구분. 서버 측 eligible 규칙 변경은 Phase 5 몫 ④ 익명 level 3 응답 `title` None 가능(Phase 5 fallback meta 조인 전) → 카드 렌더는 `title ?? '(제목 없음)'` 방어.

### D8 쇼케이스의 정적 데이터 원천
- **D-08 (showcase.json 복사 + api 모드 `/api/showcase`):** `make_mock.py`가 `artifacts/serving/eval_table.json`(Track A 비교표 4행·`split_mode`·`data_notice`)을 `demo/mock/showcase.json`으로 복사하고, 본인 5권 앵커 케이스는 `uv run millie-rec demo --seeds …` stdout(Phase 4 D-13 형식)을 같은 파일에 `anchor_case` 필드로 넣는다(5권 book_id는 사용자가 정한 뒤 — 미정이면 필드 비움 + "5권 선정 대기" 표시). `?source=api`에서는 `GET /api/showcase`(Phase 5 SERV-13)를 읽는다. **숫자 원천은 여전히 `results/` → `eval_table.json` 1곳** — 복사를 손으로 하지 않고 `make mock`이 한다. Phase 5 완료 전에도 mock 쇼케이스가 실측 숫자로 뜬다.

### Phase 5 대기 지점과 완료 판정
- **D-09 (Phase 6 verify = mock 완주):** Phase 6 완료 판정은 `?source=mock`에서 쇼케이스 → 관제 대시보드 완주 콘솔 에러 0 + `?capture=1|2` 동작 + `/contract-sync` 전부 통과 + `uv run pytest -q`·`make smoke` PASS. **`?source=api` 완주는 Phase 7 '배포' 사전 게이트로 이관** — Phase 7 Day 2 스켈레톤 배포 전 로컬 `make serve` + `?source=api` 완주를 게이트로 둔다. REQUIREMENTS.md DEMO-09 문구를 "mock 완주(Phase 6) + api 완주(Phase 7 배포 전 게이트)"로 1줄 수정 — **Phase 5 세션(Advisor)에 `PROGRESS.md` 미결로 제안**(이 세션은 `.planning/REQUIREMENTS.md`를 편집하지 않는다).
- **D-10 (Phase 5 산출물 의존 최소화):** Phase 6은 `serving/schemas.py`(freeze)와 `artifacts/serving/*`(Phase 3 산출)만 읽는다. `serving/onboarding_meta.json`(Phase 5 D-14)은 아직 없을 수 있으므로 mock의 온보딩 메타는 `config/onboarding.json`에서 생성하고, 두 파일의 동일성 검사는 Phase 5 완료 후 `/contract-sync`가 한다.

### Claude's Discretion
- `router.js` 파일 구조·해시 매칭 방식, 폰 프레임 밖 PC 페이지(D7·D8) 그리드 레이아웃 세부, 인스펙터 시각화(막대·라디오)의 CSS, 뷰어 시뮬레이션 D4의 "10분 읽기" 연출(타이머 vs 즉시 버튼 — 단 `qualified_read`는 T=15분 상수 표기 유지), `?capture=1|2` 구현 방식(body class 토글), sessionStorage 키 네이밍, mock 결정적 지연값 상수.
- Worker 분할(권장, 최종은 planner): wave 1 = `make_mock.py` 재작성 + 축약본 생성(선행, 나머지의 입력) → wave 2 병렬 = `router.js`+`app.js` ‖ `mock.js`+`api.js` ‖ `d4_reader.js`+`d5_library.js`+css ‖ `d7_dashboard.js`+`d8_showcase.js`+css → wave 3 = D2·D3 수정 + 인스펙터 + 완주 검증.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 화면 정본
- `../.assets/설계서/화면 구성 및 디자인/02_화면구성_v2_8페이지.md` — D1~D8 페이지별 명세(§2), 공통 컴포넌트(§3), 상태 모델 v2(§4), UI 행동→이벤트→서버 효과 13종(§5), 토큰 추가분(§6), 캡처 계획(§7), **구현 계획·재사용/추가/수정 파일 목록(§8)**, 티어(§9)
- `../.assets/설계서/화면 구성 및 디자인/01_기술스택_및_화면설계.md` — PC 레이아웃 `[폰 390×844][인스펙터 560]`(§3), 온보딩 JSON 정본(§4-2), 배지 6종(§4-4), 페르소나 4종(§4-5), 디자인 토큰(§5), 상태 패턴(§6). §8 카테고리 매핑표는 폐기(밀리 분류 직접 사용)

### HTTP 계약 (읽기 전용 — freeze)
- `src/millie_rec/serving/schemas.py` · `schemas_should.py` — 응답 형태 코드 정본. mock은 이 형태를 그대로 채운다
- `../.assets/설계서/백엔드 서빙/01_백엔드_서버_구성.md` — 엔드포인트 14개 요청/응답 JSON(§3~§15), **§16 mock·코드 대응표**(배지 규칙·필드 이름)
- `src/millie_rec/contracts.py` — `VARIANTS`·`ROW_IDS` 7종·`BADGE_TYPES` 6종·`EVENT_TYPES` 13종·`FALLBACK_*`·`BUDGET_MS=200` (이름 정본)

### 데이터·아티팩트
- `artifacts/serving/books_kr.json` · `item_edges_kr.json` · `popularity_kr.json` · `eval_table.json` — Phase 3·4 산출. `make_mock.py`의 입력
- `../.assets/설계서/데이터 소스/02_밀리_데이터_적재_계획.md` §3 스키마 — 카드 필드 이름·결측 규칙(완독지수 없음 → `difficulty=None`)
- `../.claude/rules/data.md` — 밀리 저작 텍스트(설명문·리뷰) 미노출·표지 핫링크만

### 이전 페이즈 결정 (재사용)
- `.planning/phases/05-must/05-CONTEXT.md` — D-01~D-04 compose 5행·dedup 순서, D-14 온보딩 메타, D-15 후보 30권 라운드로빈, D-16 페르소나 매핑 → mock이 같은 규칙으로 흉내낸다
- `.planning/phases/04-freeze/04-CONTEXT.md` — D-13 `cli demo --seeds` stdout 형식(쇼케이스 본인 5권), D-14 freeze 4종
- `../.assets/개발일지/2026-09-04_Day0.5_브레인스토밍과_데모명세.md` D40 — 버리는 순서(대시보드 → 별점 모달 → 완독 직후 행 순으로 늦게)

### 규칙
- `../.claude/rules/demo.md` — demo 레인 규칙(JS/CSS 250줄, 라이브러리 0, mock JSON 손편집 금지·생성기만, `/contract-sync`)
- `../.claude/rules/simplicity.md` — 이중 구현 금지, 범위 4분류
- `../.claude/skills/contract-sync/SKILL.md` — mock ↔ schemas 검증 절차

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `demo/css/tokens.css`(43줄)·`base.css`·`onboarding.css`·`home.css`·`inspector.css`: 디자인 토큰·폰 프레임·카드·인스펙터 스타일 — 그대로 재사용
- `demo/config/onboarding.json`(75줄): 7단계 텍스트 정본 — 화면 텍스트의 유일한 원천, 재사용
- `demo/js/screens/onboarding_step.js`(85줄) `ui.js`(72줄) `s0_start.js` `s6_persona.js`: 공용 렌더러·단계 화면 — 재사용(D1·D6 공유)
- `demo/js/app.js`의 `state`+`setState`+`render` 패턴, `log()` 유틸 — **패턴만** 계승(파일은 새로)
- `demo/js/inspector.js`(132줄): 신호 해석 패널 — 새 계약 필드(`latency_breakdown`·`cell`·`channel_mix`)로 확장
- `demo/scripts/make_mock.py`(407줄): 생성기 골격(pool 로드·배정·JSON 출력) — 입력을 Goodbooks CSV → 밀리 아티팩트로 교체하며 재작성

### Established Patterns
- 상태 1개 / 렌더 1개 / 이벤트 로그 1개 — v2 §4 상태 모델도 같은 원칙. 라우터는 `state.route`를 바꾸는 하나의 진입점
- `api.js`가 `source=api|mock` 양쪽을 같은 함수 시그니처로 덮는 구조(`loadMeta`·`getCandidates`·`postPreferences`·`getRecommend`) — 유지하되 함수 추가(events·ratings·state·dashboard·showcase·personalization DELETE)
- 서버가 `/`에 `demo/`를 StaticFiles로 서빙(Phase 1) → `API_BASE=""` 같은 origin

### Integration Points
- `GET /api/recommend`(Phase 1 존재, Phase 5에서 5행 완성)·`/health` — 현재 서버 라우트는 이 둘만. 나머지 엔드포인트는 Phase 5가 만든다 → mock이 먼저, api는 Phase 7 게이트
- `artifacts/serving/*` → `make_mock.py` → `demo/mock/*` (빌드 시 1회, `make mock`)
- `/contract-sync` 스킬이 `demo/mock/*.json` ↔ `serving/schemas.py` 검증

### 현재 상태 (scout 실측)
- `demo/` 27파일, JS 최대 275줄(app.js) · mock JSON은 Goodbooks 400권 · `api.js` `API_BASE="https://REPLACE-ME.hf.space"` · 서버 라우트 2개
- `artifacts/serving/`: books_kr 8.3MB · item_edges 11MB · popularity 7.7MB · content_vectors 4.9MB · eval_table 1KB (2026-09-06 00:31 생성)

</code_context>

<specifics>
## Specific Ideas

- "심사자가 mock으로 눌러봐도 '가짜'가 티나지 않아야 한다" — 그래서 고정 스냅샷이 아닌 상태 시뮬레이션(D-01), 고정 예시 숫자가 아닌 세션 집계(D-03)
- 쇼케이스는 Phase 5 없이도 실측 숫자를 보여야 한다(D-08) — 스크린샷 6장 중 D8이 P4·P5의 근거
- 구 형태 grep 0건 = 재작성 완료의 기계적 판정(D-07)
- 두 세션 병렬: 이 세션은 `demo/`만, STATE.md·REQUIREMENTS.md는 Phase 5 세션이 최종 병합

</specifics>

<deferred>
## Deferred Ideas

- **REQUIREMENTS.md DEMO-09 분리 문구 수정** — Phase 5 세션(Advisor)에 `PROGRESS.md` 미결로 제안(D-09). 이 세션은 편집하지 않음
- **`?source=api` 완주 게이트** — Phase 7 '배포' 착수 전으로 이관(D-09)
- **`serving/onboarding_meta.json` ↔ `config/onboarding.json` 동일성 검사** — Phase 5 완료 후 `/contract-sync`(D-10)
- **본인 5권 book_id 선정** — 사용자 몫(Phase 4 D-12 `cli demo --find`). 미정 시 쇼케이스 `anchor_case` 비움

None beyond these — discussion stayed within phase scope.

</deferred>

---

*Phase: 06-demo-rebuild*
*Context gathered: 2026-09-06*
