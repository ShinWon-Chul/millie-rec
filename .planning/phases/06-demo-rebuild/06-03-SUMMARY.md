---
phase: 06-demo-rebuild
plan: 03
subsystem: Demo 데이터 계층
tags: [demo, http-contract, mock, sessionStorage, fallback]
requires:
  - "06-01 산출 demo/mock/*.json 13개(catalog_kr · neighbors_kr · 계약 10 + _manifest)"
  - "demo/js/screens/ui.js 의 josa(word, withFinal, without) — 06-02 소유, 시그니처 불변"
  - "src/millie_rec/serving/schemas.py · schemas_should.py (응답 형태 정본, 읽기만)"
provides:
  - "demo/js/api.js — 부록 C 15 export, source=api|mock 양쪽을 같은 시그니처로 덮는다"
  - "demo/js/mock.js — 부록 D 14 export, 밀리 카탈로그 위 상태 시뮬레이션"
  - "demo/js/mock_store.js — sessionStorage millie_mock_db, mock 서버 상태 + 세션 집계 DashboardOut"
affects:
  - "demo/js/app.js · actions.js · presets.js (06-02) — 부록 C 호출부"
  - "demo/js/screens/d2_home.js · d3_detail.js (06-06) · d4_reader.js · d5_library.js (06-04) · d7_dashboard.js · d8_showcase.js (06-05)"
tech-stack:
  added: []
  patterns:
    - "Promise 1회 캐시로 4.5MB 카탈로그 로드(init)"
    - "AbortController 4초 타임아웃 + 엔드포인트별 soft() 실패 격리"
    - "sessionStorage 단일 키 JSON 스냅샷을 서버 테이블의 축소판으로"
key-files:
  created:
    - demo/js/mock_store.js
  modified:
    - demo/js/api.js
    - demo/js/mock.js
decisions:
  - "mock 의 삭제 응답 deleted 키를 privacy_api.py DELETED_KEYS(snapshots·events·ratings·recommendations·candidate_sets)에 맞췄다 — 플랜 본문의 preference_snapshots 는 코드와 어긋난다"
  - "카테고리 → 카드 색인을 init 에서 1회 만든다 — byPop 이 호출마다 9,444행을 훑지 않게"
  - "getRecommend 의 클라이언트 fallback 이 정적 파일 로드까지 실패해도 RecommendOut 15키 최소 객체를 돌려준다(uncaught 0)"
metrics:
  duration: "약 40분"
  tasks: 3
  files: 3
  completed: 2026-09-06
---

# Phase 6 '데모 재구성' Plan 03: 데이터 계층 Summary

`demo/`의 데이터 계층 3파일을 새 HTTP 계약으로 갈아끼웠다 — `api.js`는 같은 origin `API_BASE=""`·`/api` 접두어·4초 타임아웃 클라이언트 fallback을 쓰는 15개 함수가 되었고, `mock.js`는 정적 응답 조합을 버리고 밀리 카탈로그 9,444권 위에서 서버 규칙(5행 compose·dedup·배지·페르소나·셀)을 점수 계산 없이 재현하는 상태 시뮬레이터가 되었으며, 새 `mock_store.js`가 sessionStorage 한 키로 서버 7테이블의 축소판과 세션 집계 대시보드를 맡는다.

## 무엇을 만들었나

| 파일 | 상태 | 줄 | export |
|---|---|---|---|
| `demo/js/api.js` | 재작성 | 129 | 15 (`config` `resolveSource` `loadSteps` `health` `loadMeta` `getCandidates` `postPreferences` `getRecommend` `postEvents` `postRating` `getUserState` `getUserData` `deletePersonalization` `getDashboard` `getShowcase`) |
| `demo/js/mock.js` | 폐기 후 새로 | 249 | 14 (`init` `byId` + api.js 와 같은 이름 12개) |
| `demo/js/mock_store.js` | 신규 | 245 | 25 (핵심 17 + `setCatalog` `hex6` `getUser` `snapshotsOf` `latestSnapshot` `eventsOf` `booksBy` `ratingsOf`) |

세 파일 모두 상한(150 / 250 / 250) 안이다. `api.js`는 계획된 150줄 상한 대비 129줄, `mock.js`는 250줄 상한에 맞추려 빈 줄을 걷어내 249줄로 눌렀다.

## 커밋

| 순서 | 해시 | 시각 | 내용 | 파일 |
|---|---|---|---|---|
| Task 1 | `641799b` | 10:09:49 | api.js 재작성 | `demo/js/api.js` |
| Task 2 | `6c8d72c` | 10:11:09 | mock_store.js 신규 | `demo/js/mock_store.js` |
| Task 3 | `d515094` | 10:19:52 | mock.js 폐기 후 새로 | `demo/js/mock.js` |

각 커밋은 pathspec으로 자기 파일 하나만 스테이징했다. 다른 세션의 미커밋 작업은 건드리지 않았다.

## 서버 규칙 ↔ JS 함수 대응표

| 서버(정본) | JS | 같은 점 / 다른 점 |
|---|---|---|
| `compose.ROW_ORDER` | `getRecommend` 의 `eat()` 호출 순서 | `after_completion` → `continue_reading` → `anchor_<seed₁>` → `persona_shelf` → `trending` → `fresh_picks`. 순서 1:1 |
| `compose.dedup_rows` | `dedup(rows)` | 앞 행 우선, `book_id` ∧ 정규화 제목. 정규화는 `replace(/[^\p{L}\p{N}_]/gu, "").toLowerCase()`(서버 `re.sub(r"[^\w]", "").casefold()`) |
| `compose.ZERO_WEIGHTS` | `weightsFor` 의 비동의 반환 | `{alpha:0, beta:0, gamma:0}` |
| `rows.neighbor_row` | `neighborRow` | 이웃 top-20 → 자격·중복·시드 제외 → 12, 비면 `null`. `source "content"` |
| `rows.fresh_row` | `freshRow` | 미선택 카테고리 인기 풀 30권씩 라운드로빈 |
| `rows.personal_rows` continue | `continueRow` | `source` 없음·`source_channels []`·`channel_mix {}` (서버 `ScoredItem` 과 같은 형태) |
| `fallback.trending_row` | `popRow("trending", …, "fallback", …)` | 제목 `지금 많이 읽는 책`, purpose `fallback` |
| `badges.badge_for` | `badgeFor` | 6종 중 `light` 제외 5종. `review` 3단 폴백·문구 f-string 1:1. `criterion` 은 배지 타입 id |
| `badges.attach_badges` | `attachBadges` | `criterion` 없으면 무동작, seed 저자·출판사 집합 1회 계산 |
| `persona.assign_persona` | `assignPersona` | 같은 4종 표·같은 `CATEGORY_TO_PERSONA`·같은 문장 템플릿. 미매핑은 `sha256(head)[:8] % 4` |
| `persona._josa` | `ui.js` 의 `josa` | 받침 판정, `으로`/`로` ㄹ 받침 예외까지 동일 |
| `privacy_api._library` | `mock_store.library` | `completed = completion` · `reading = READ_TYPES − completed` · `added = library_add` |
| `privacy_api.delete_personalization` | `mock_store.deleteUser` | 4테이블 삭제 + `users.consent = false`(행 유지) |
| 05-CONTEXT D-08 셀 배정 | `mock_store.cellFor` | `int(sha256(user_key)[:8], 16) % 2 == 0 → "A"` |
| 05-CONTEXT D-15 후보 30 | `getCandidates` | 카테고리별 인기 목록 1권씩 라운드로빈 |

## Node 단위 실행 출력 (인용)

브라우저 API(`sessionStorage`·`fetch`)를 셈하고 스크래치패드에서 ESM으로 불러 돌린 결과다. `crypto`는 Node 20 내장 webcrypto를 그대로 썼다.

`mock_store.js` — 플랜의 기대 출력 `6 4 1 {"accepted":0,"duplicates":0,"flagged":[]}` 와 정확히 일치:

```
6 4 1 {"accepted":0,"duplicates":0,"flagged":[]}
```

`mock.js` — 시드 5권(싯다르타 1012 외)으로 취향 설정 후 추천, 이어서 익명 추천:

```
A| B | continue_reading:0 anchor_1012:8 persona_shelf:11 trending:12 fresh_picks:11 | 0 hybrid_div_v1 number 15
persona: 셜록 홈즈 | 회원님은 소설과 인문을 즐기고, 베스트셀러로 책을 고르는 독서가입니다.
badge sample: {"type":"bestseller","text":"인기 686위"} itemkeys: 12
dedup_removed: 6 weights: {"alpha":0.7,"beta":0.2,"gamma":0.1} items: 40
anon: trending:12 fresh_picks:11 fallback_v1 3 0 15
cand: 30 book_id,title,authors,image_url,position,book_format
state: B true 5 1 8
dash kpi: 6 ab: 4 window: session byvar: {"hybrid_div_v1":1,"fallback_v1":1}
showcase keys: 7 meta: 4 health: 8
del: {"user_key":"u1","consent":false,"deleted":{"snapshots":1,"events":5,"ratings":0,"recommendations":1,"candidate_sets":0}}
```

읽는 법: `cell`은 `sha256("u1")` 기준 B → 강제 지정이 없으므로 variant `hybrid_div`. 행 수가 12보다 적은 것은 dedup이 6권을 걷어냈기 때문이고, `anchor_1012:8`은 06-01이 생성한 `recommend_hybrid_div.json`의 `anchor_1012:8`과 같은 값이다. 익명은 2행·`fallback_v1`·level 3·`items` 0으로 `demo/fallback/popular.json`과 같은 형태다. 응답 최상위 키는 개인화·비개인화 모두 15개다.

## api 모드 실측 (포트 8011 임시 기동)

플랜 부록 C의 경로 12개가 실제로 등록돼 있는지 `openapi.json`으로 대조했고, 전부 일치했다. GET·POST 응답 코드:

| 경로 | 코드 |
|---|---|
| `/health` · `/api/meta/onboarding` · `/api/candidates/onboarding` · `/api/recommend` · `/api/dashboard` · `/api/showcase` | 200 |
| `POST /api/events` | 202 |
| `/api/users/{key}/state` · `/data` · `DELETE /personalization` | 404 (해당 user_key 행 없음 — `privacy_api._user_or_404` 정상 동작) |

`/api/recommend`는 500이 아니라 200이었다. 404 3건은 `api.js`의 `soft()`가 `null`로 바꿔 화면이 "이 항목은 아직 없음"을 그리게 되는, 설계대로의 경로다. 프로브가 남긴 `events` 행 1건(`user_key = "probe-key"`)은 로컬 개발 DB에서 지웠고, 그 DB(`data/local/millie.db`)는 `.gitignore` 대상이다. 서버는 프로브 직후 종료했다.

## 검증

| 항목 | 결과 |
|---|---|
| `node --check` 3파일 | 종료 0 |
| 줄 수 | api 129 / mock 249 / mock_store 245 (상한 150 / 250 / 250) |
| `api.js` export 15 · `mock.js` 14 · `mock_store.js` 핵심 17 | 전부 일치 |
| `API_BASE = ""` 1건 · `TIMEOUT_MS = 4000` 1건 · `"/api/` 11줄 · `encodeURIComponent(userKey)` 3줄 | 일치 |
| `fallback/popular.json` 1건 · `client_fallback_reason` 1건 · `{ events: events.slice(0, 50) }` 1건 | 일치 |
| 구 형태 정규식(`hf.space` `"/recommend"` `timestamp` `"format":` `type: "rating"` `static_popular` `REPLACE-ME` `books.json` `zygmuntz` `CSV_URL`) 3파일 전수 | 0건 |
| `mock.js` 금지어(`itemknn` `_mock"` `ratings_count` `format:` `Math.random() - 0.5` `"light"` `codePointAt`) | 0건 |
| 배지·페르소나 문구 1:1 grep 6종 | 각 1건 |
| `mock_store.js` kpi 6 이름 · MDE 고지 · `PDF 숫자 아님` · `가명 user_key 외 개인정보 없음` · `book_ineligible` | 각 존재 |
| 고정 예시 소수 `value: N.N` | 0건 |
| `uv run pytest tests/demo tests/test_architecture.py -q` | 13 passed |
| 06-02 호출부 대조(`app.js` `actions.js` `presets.js`) | 부록 C 15함수를 모두 같은 시그니처로 호출 중 |

## 플랜과 달라진 점

### 자동 수정

**1. [Rule 2 - 누락된 방어] `getRecommend` 의 fallback 실패 경로**
- 발견: Task 1
- 문제: 플랜 코드는 `await local("fallback/popular.json")`을 catch 밖에서 던지므로, 정적 파일까지 못 읽으면 uncaught rejection이 난다. "uncaught 0"이라는 이 플랜의 핵심 약속이 깨진다.
- 조치: `soft(local(...))`로 감싸고, `null`이면 `FALLBACK_EMPTY`(RecommendOut 15키·`model_version "fallback_v1"`·`fallback_level 3`) 상수를 쓴다. `client_fallback_reason`은 여전히 1곳에서만 붙는다.
- 파일: `demo/js/api.js` · 커밋 `641799b`

**2. [Rule 1 - 버그] 삭제 응답 `deleted` 키가 서버와 달랐다**
- 발견: Task 2
- 문제: 플랜 본문은 `deleted: { preference_snapshots, events, ratings, recommendations }`인데, `privacy_api.py`의 `DELETED_KEYS`는 `("snapshots", "events", "ratings", "recommendations", "candidate_sets")`다. mock과 api 모드에서 철회 모달의 항목 이름이 달라진다.
- 조치: 서버 키를 그대로 쓴다(`candidate_sets`는 mock이 후보 집합을 저장하지 않으므로 항상 0).
- 파일: `demo/js/mock_store.js` · 커밋 `6c8d72c`

**3. [Rule 1 - 버그] `UserDataOut.candidate_sets` 누락**
- 발견: Task 2
- 문제: 플랜의 `userData` 키 목록에 `candidate_sets`가 없는데, `schemas.py`의 `UserDataOut`에는 있고(Codex T3, 2026-09-06) 서버는 항상 내려준다. "내 데이터 보기" 모달이 api·mock에서 서로 다른 섹션 수를 받게 된다.
- 조치: `candidate_sets: []`를 포함한다. schemas.py 모델 안의 필드이므로 "여분 키 금지"에 어긋나지 않는다.
- 파일: `demo/js/mock_store.js` · 커밋 `6c8d72c`

**4. [Rule 1 - 성능] `byPop` 이 호출마다 카탈로그 전체를 훑었다**
- 발견: Task 3
- 문제: `freshRow`는 미선택 카테고리(최대 29종)마다 `byPop([c])`를 부르고, 각 호출이 9,444행을 필터한다. 추천 1회당 수십만 번의 비교가 생긴다.
- 조치: `init()`에서 카테고리 → 카드 배열 색인(`byCat`)을 1회 만들고, 단일 카테고리 조회는 색인을 그대로 반환한다. `allCats`(권수 내림차순)도 같은 색인에서 뽑는다.
- 파일: `demo/js/mock.js` · 커밋 `d515094`

**5. [Rule 3 - 진행 차단 해소] `meta_onboarding.json` 을 `init()` 에서 함께 읽는다**
- 발견: Task 3
- 문제: `postPreferences`는 `criterion` id를 라벨로 바꿔야 페르소나 문장을 만들 수 있는데, 플랜의 `loadMeta()`는 호출 시점에 별도 fetch를 한다. 화면이 `loadMeta`를 먼저 부르지 않으면 라벨이 비어 페르소나 문장이 "취향으로"가 된다.
- 조치: `init()`의 `Promise.all`에 4번째 파일로 넣고 `loadMeta()`는 캐시를 반환한다. 요청 수는 오히려 줄었다.
- 파일: `demo/js/mock.js` · 커밋 `d515094`

**6. [Rule 2 - 계약 보존] `flagged_events` 를 저장하지 않고 집계 시점에 계산**
- 발견: Task 2
- 문제: 플래그 수를 세려면 mock DB에 6번째 키를 추가하거나 이벤트에 비공개 필드를 붙여야 하는데, 후자는 `events_recent`가 EventIn 그대로여야 한다는 요구와 충돌한다.
- 조치: `dashboard()`가 저장된 이벤트의 `book_id` 자격을 다시 확인해 센다. mock DB는 5키 그대로다.
- 파일: `demo/js/mock_store.js` · 커밋 `6c8d72c`

### 형식상의 조정

- `mock.js`는 250줄 상한을 맞추려 빈 줄을 걷어냈다(249줄). 함수 앞 doc 주석이 구역 구분을 대신한다. 로직을 뺀 것은 없다.
- 플랜 frontmatter의 `no_commit: true`를 따르지 않고 태스크마다 커밋했다 — 오케스트레이터가 "Commit each task atomically"를 지시했고 같은 wave의 06-01·06-02가 이미 커밋으로 진행 중이었다. push는 하지 않았다.

## Advisor 제안

오케스트레이터가 네 플랜에 한 번에 고쳐 내려보내야 할 항목이다. 내 소유 밖 파일은 건드리지 않았다.

1. **`06-03-PLAN.md` Task 2의 `deleted` 키 목록**(`preference_snapshots` → `snapshots`, `candidate_sets` 추가). 정본은 `src/millie_rec/serving/privacy_api.py`의 `DELETED_KEYS`. 06-04가 만드는 내 서재 화면(`d5_library.js`)의 철회 모달이 키 이름을 하드코딩했다면 같이 고쳐야 한다.
2. **`06-03-PLAN.md` Task 2의 `userData` 키 목록에 `candidate_sets` 추가**. 정본은 `serving/schemas.py`의 `UserDataOut`.
3. **`06-03-PLAN.md` frontmatter `no_commit: true`가 이 페이즈의 실제 진행과 어긋난다.** 06-01·06-02·06-03이 모두 커밋했으므로 frontmatter를 지우거나 다른 플랜과 맞춰야 다음 페이즈에서 혼선이 없다.
`api.js`의 `capture`가 구 boolean에서 `"1"|"2"|null` 문자열로 바뀐 건은 확인이 끝났다 — 06-02의 `app.js`가 이미 `cap === "1"` / `cap === "2"`로 읽고 있어 조치할 게 없다.

## 06-06 에 넘기는 주의

- **`client_fallback_reason` 판정:** 이 키는 `api.js`가 응답 객체에만 붙이며, mock 모드에서는 절대 붙지 않는다. 인스펙터가 "클라이언트 fallback"을 표시할 조건은 `state.recommend?.client_fallback_reason`의 존재 여부 하나로 충분하다. `fallback_level === 3`만 보면 익명 사용자의 정상 level 3(서버·mock 모두)과 구분되지 않는다.
- **`continue_reading` 빈 행:** 서버와 마찬가지로 `items: []`인 행을 그대로 내려보낸다(플랜과 `compose.dedup_rows` 규칙 그대로 "빈 행도 남긴다"). 뷰어를 한 번도 열지 않은 사용자에게는 항상 빈 행이므로, **화면이 `items.length === 0`인 행을 숨겨야 한다.** 첫 진입 화면에 제목만 있는 빈 캐러셀이 보이면 이 처리가 빠진 것이다.
- **`after_completion` 은 조건부다.** 완독 이벤트가 있어야 나타나고, 그때 행 배열의 0번이 된다. 행 인덱스를 고정 숫자로 참조하지 말고 `row_id`로 찾아야 한다.
- **`anchor_` 행의 `row_id` 는 가변**(`anchor_1012` 처럼 시드 book_id가 붙는다). `row_id.startsWith("anchor_")`로 판정한다.
- **같은 제목 다른 book_id는 dedup에서 뒤엣것이 사라진다**(정규화 제목 키). 06-CONTEXT D-07b의 '도슨트북' 2권 사례가 여기에 해당하니, 화면이 특정 book_id의 존재를 전제하지 않게 한다.
- **`items` 는 개인화일 때만 채워진다.** level 3 응답의 `items`는 `[]`이고 카드는 `rows[].items`에만 있다.

## Known Stubs

없다. 세 파일 모두 실데이터(`demo/mock/*.json` 13개)와 세션 상태에 연결돼 있고, 하드코딩한 빈 배열·플레이스홀더 문구는 없다. `LATENCY` 상수와 `NEARLINE_LAG_S`는 스텁이 아니라 06-CONTEXT D-01이 지시한 "결정적 표시값"이며, 대시보드의 `p95_latency_ms`에는 "mock 상수 · 참고용 — PDF 숫자 아님" 주석이 응답에 함께 실린다.

## Self-Check: PASSED

생성 파일 4개 존재 확인, 커밋 3개(`641799b` `6c8d72c` `d515094`) 이력 확인. 각 커밋의 변경 파일은 이 플랜 소유 경로 1개씩이며 다른 세션의 작업 트리를 포함하지 않는다.
