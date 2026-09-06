# Phase 6: 데모 재구성(demo-rebuild) - Pattern Map

**Mapped:** 2026-09-06
**Files analyzed:** 33 (JS 11 · CSS 4 · HTML 1 · 생성기 1 · 테스트 1 · 생성 산출물 15)
**Analogs found:** 30 / 33 (exact 12 · role-match 14 · 서버 정본 대응 4 · 없음 3)

> 쓰기 영역은 `demo/**` + `tests/demo/`만. `src/millie_rec/**`는 **읽기 전용 analog**이며 발췌는 "mock이 흉내낼 규칙의 정본"으로만 쓴다(Phase 5 '서빙 Must 완성'(.planning/ROADMAP.md) 세션이 동시 편집 중). 모든 경로는 `millie-rec/` 기준.

## 0. 계획 전에 알아야 할 실측 3가지 (CONTEXT와 어긋난 점)

| # | 실측 | CONTEXT 가정 | 계획에 미치는 영향 |
|---|---|---|---|
| A | `demo/fallback/popular.json`은 **이미 밀리 기반**(`model_version: "fallback_v1"`, `recommendation_id: "rec_static"`, 첫 항목 『불편한 편의점』, 40권, `latency_ms: 0.0` float). 생성기는 `scripts/export_millie_fallback.py`(`make millie-export`) | D-06 "Goodbooks `popular.json` 삭제 후 `make_mock.py`가 재생성" | `make_mock.py`는 `fallback/popular.json`을 **쓰지 않는다**(소유권: `.claude/rules/architecture.md` "artifacts/serving export가 `demo/fallback/popular.json`을 갱신하는 것만 허용"). 존재·형태 검증만. v1 생성기의 `write("fallback/popular.json", …)` 블록(407줄본 369~402행)은 폐기 — 이것이 Phase 3 인계 "실행 금지" 경고의 원인 |
| B | `tests/fixtures/millie/serving_sample/` 폴더는 **없다**. 20권 표본은 `tests/conftest.py`의 session fixture `millie_serving_sample(tmp_path_factory) -> Path`가 tmp에 생성(`books_kr.json`·`item_edges_kr.json`·`popularity_kr.json`·`content_vectors_kr.npz`) | "fixture는 `tests/fixtures/millie/serving_sample/` 20권" | `tests/demo/test_make_mock.py`는 `millie_serving_sample` fixture 인자를 받아 `make_mock.build(serving_dir, out_dir)` 형태로 호출한다. `tests/demo/conftest.py` 불필요(루트 conftest가 session scope) |
| C | `artifacts/serving/item_edges_kr.json`은 책당 평균 37개 엣지(`content_sim` 172,751 + `category_best` 177,329), 값 형태 `[dst, weight, source]`. `popularity_kr.json`은 13 세그먼트(`all` + 연령×성별 12) 98,055행 | "이웃 top-20" | `neighbors_kr.json`은 책별 상위 20개로 절단(`[dst, weight]`만, source 제외해도 됨). `catalog_kr.json`의 `pop_rank`는 `books_kr.json` 행에 이미 있으므로 `popularity_kr.json`은 읽지 않아도 된다(`segment=="all"`의 rank == `pop_rank`) |

## 1. File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `demo/js/router.js` (신규 ≤30줄) | utility(라우터) | event-driven(hashchange) | `demo/js/app.js` 254~262행 이벤트 위임 | role-match |
| `demo/js/app.js` (재작성) | store+controller | event-driven | `demo/js/app.js`(현행) `state`·`setState`·`render`·`log`·`ACTIONS`·`boot` | exact(패턴 계승) |
| `demo/js/mock.js` (재작성) | service(브라우저 내 시뮬레이터) | transform(조회+상태) | `demo/js/mock.js`(현행) 골격 + 서버 정본 `serving/compose.py`·`badges.py`·`persona.py` | role-match + 정본 |
| `demo/js/api.js` (재작성) | service(fetch 래퍼) | request-response | `demo/js/api.js`(현행) `get/post/local/config/TIMEOUT_MS` | exact |
| `demo/js/screens/d2_home.js` (← `s7_home.js`) | component | transform(state→HTML) | `demo/js/screens/s7_home.js` | exact(개명+필드 수정) |
| `demo/js/screens/d3_detail.js` (← `s8_detail.js`) | component | transform | `demo/js/screens/s8_detail.js` | exact |
| `demo/js/screens/d4_reader.js` (신규) | component | transform | `s8_detail.js`(바텀시트·액션 버튼) + `onboarding_step.js`(progress bar) | role-match |
| `demo/js/screens/d5_library.js` (신규) | component | transform | `s7_home.js`(tile·row) + `inspector.js` `kv` dl | role-match |
| `demo/js/screens/d7_dashboard.js` (신규, PC 페이지) | component | batch(sessionStorage 집계→HTML) | `inspector.js` `latencySection`·`weightsSection`(막대·KPI 카드) | role-match |
| `demo/js/screens/d8_showcase.js` (신규, PC 페이지) | component | transform(showcase.json→HTML) | `inspector.js` `modelSection` 표 + `s0_start.js` CTA | role-match |
| `demo/js/inspector.js` (확장) | component | transform | `demo/js/inspector.js`(현행) `sec()`·섹션 함수 | exact |
| `demo/css/reader.css` (신규) | style | — | `demo/css/home.css` §시트(`.sheet*`) + `onboarding.css` `.progress` | role-match |
| `demo/css/library.css` (신규) | style | — | `home.css` `.tile`·`.row` + `inspector.css` `.kv` | role-match |
| `demo/css/dashboard.css` (신규, D7·D8 공용) | style | — | `inspector.css` `.lat*`·`.weight*`·`.kv` | role-match |
| `demo/css/tokens.css` (§6 토큰 추가) | config | — | 자기 자신 | exact |
| `demo/index.html` (CSS 링크·탭바 슬롯) | config | — | 자기 자신 | exact |
| `demo/scripts/make_mock.py` (재작성) | generator(script) | file-I/O(json→json) | 현행 `make_mock.py` `main`·`write`·`item`·`josa` + `scripts/export_millie_fallback.py` `_item`·`payload`·`is_eligible` | role-match |
| `tests/demo/test_make_mock.py` (신규) | test | file-I/O | `tests/data/test_millie_export.py`(`_load`·module fixture·키 집합·누출 0건) + `tests/serving/test_schemas.py`(pydantic `model_validate`) | exact |
| `demo/mock/catalog_kr.json` | data | — | `artifacts/serving/books_kr.json` 행(28키) → 카드 12키 | 정본 |
| `demo/mock/neighbors_kr.json` | data | — | `artifacts/serving/item_edges_kr.json` | 정본 |
| `demo/mock/meta_onboarding.json` | data | — | `serving/schemas.py::OnboardingMeta` · `serving/onboarding_meta.json` | 정본 |
| `demo/mock/candidates_onboarding.json` | data | — | `schemas.py::CandidateSet`/`CandidateItem` | 정본 |
| `demo/mock/preferences_response.json` | data | — | `schemas.py::PreferencesResponse`/`PersonaOut` | 정본 |
| `demo/mock/recommend_{pop,cf,hybrid,hybrid_div}.json` | data | — | `schemas.py::RecommendOut`/`RowOut`/`ItemOut`/`BadgeOut` + `demo/fallback/popular.json`(실물 예시) | 정본 |
| `demo/mock/state.json` | data | — | `schemas.py::UserStateOut`/`LibraryBook`/`SnapshotSummary` | 정본 |
| `demo/mock/dashboard.json` | data | — | `schemas_should.py::DashboardOut`/`KpiValue`/`AbRow`/`LatencyBlock` | 정본 |
| `demo/mock/showcase.json` | data | — | `schemas_should.py::ShowcaseOut`/`EvalTable`/`EvalRow`/`PersonalCase` + `artifacts/serving/eval_table.json` | 정본 |
| `demo/fallback/popular.json` | data | — | **이미 존재·밀리 기반** (§0-A) | 재생성 안 함 |
| `demo/mock/book_stats.json`(화면 02 §8 목록) | data | — | `contracts.BookStats` | 없음 — Should(난이도 점) 필드는 `catalog_kr.json`의 `difficulty`로 충분. 생성 보류 권장 |

## 2. Pattern Assignments

### 2-1. `demo/js/app.js` (store+controller, event-driven) — 재작성

**Analog:** `demo/js/app.js` (현행 275줄). 파일은 새로 쓰되 아래 5개 패턴은 그대로 계승.

**Imports 패턴** (현행 2~9행) — 화면 파일은 `render`만 named import, `as` 별칭으로 화면 코드명:
```js
import * as api from "./api.js";
import * as inspector from "./inspector.js";
import { statusbar } from "./screens/ui.js";
import { render as s0 } from "./screens/s0_start.js";
import { render as stepView } from "./screens/onboarding_step.js";
import { render as s6 } from "./screens/s6_persona.js";
// 신규: d2_home d3_detail d4_reader d5_library d7_dashboard d8_showcase + router.js
```

**상태 1개 + setState 1개 + render 1개** (현행 18~35행, 70~77행). v2 §4 필드(`route`·`userKey`·`cell`·`reading`·`ratings`·`library`·`dashboard`·`showcase`·`nearlineLagSec`)를 이 객체에 추가:
```js
const state = {
  screen: "S0", source: "mock", consent: null,
  prefs: { readingTime: null, categories: [], criterion: null, subcategories: [], seedBooks: [] },
  candidateSet: { id: null, items: [], impressions: [] },
  snapshots: [], userKey: null,
  history: { readerOpens: [], libraryAdds: [], lastCompleted: null },
  model: "hybrid_div", recommend: null, events: [],
  steps: [], meta: { categories: [], subcategories: {} }, unsupported: [],
  resetting: false, resetBoost: false, chipHot: false, detail: null,
};
const $phone = document.getElementById("phone");
const $insp = document.getElementById("inspector");
function setState(patch) { Object.assign(state, patch); render(); }

function render() {
  $phone.innerHTML = statusbar() + screenHTML();
  $insp.innerHTML = inspector.render(state);
  document.getElementById("bar-model").textContent = state.model;
  const dot = document.getElementById("bar-source");
  dot.textContent = state.source; dot.dataset.source = state.source;
}
```
- v2에서 `screenHTML()`은 `state.route.page`로 분기(`home`→d2, `book`→d3, `reader`→d4, `library`→d5, `onboarding`/`refresh`→S0~S6 단계 머신, `dashboard`→d7, `showcase`→d8). D7·D8은 폰 프레임 밖 PC 페이지이므로 `$phone` 대신 별도 컨테이너에 그리거나 `.layout`에 body class를 토글한다(재량).

**`log()` 이벤트 기록 유틸** (현행 40~47행) — **필드명 `timestamp` → `ts`로 교체**(D-07 grep 0건 대상), `event_id`(uuid) 추가, `EventIn` 필드로 정리:
```js
function log(event_type, detail = "") {
  state.events.push({ t: new Date().toTimeString().slice(0, 8), event_type, detail });
  api.postEvent(state.source, {
    event_type, user_key: state.userKey, recommendation_id: state.recommend?.recommendation_id,
    model_version: state.recommend?.model_version,
    preference_snapshot_id: snap()?.id, timestamp: new Date().toISOString(),   // ← ts 로
  });
}
```
- v2 추가: D-03 대시보드용으로 `sessionStorage`에도 append(키 네이밍 재량, 예 `millie_demo_events`). `EventIn` 필수 필드: `event_id`·`user_key`·`event_type`·`ts`; 선택 `book_id`·`row_id`·`position`·`selected`·`candidate_set_id`·`payload: dict[str,str]`.

**이벤트 위임 1곳 + ACTIONS 딕셔너리** (현행 151~220행, 254~262행) — 화면 파일은 `data-act`만 찍고 앱이 처리:
```js
const ACTIONS = {
  start: () => { log("preference_started"); setState({ screen: "S1" }); },
  pick: (el) => togglePick(el.dataset.step, el.dataset.val),
  detail: (el) => {
    const row = state.recommend.rows.find((r) => r.row_id === el.dataset.row);
    const item = row?.items.find((i) => i.book_id === Number(el.dataset.book));
    if (!item) return;
    log("detail_click", `book=${item.book_id} row=${row.row_id} pos=${item.position}`);
    setState({ screen: "S8", detail: { item, rowId: row.row_id } });
  },
  model: async (el) => { state.model = el.value; await requestRecommend(); render(); },
  noop: () => {},
};
document.addEventListener("click", (e) => {
  const el = e.target.closest("[data-act]");
  if (!el || el.tagName === "INPUT") return;   // 라디오는 change 이벤트에서만 처리
  if (ACTIONS[el.dataset.act]) ACTIONS[el.dataset.act](el);
});
document.addEventListener("change", (e) => {
  const el = e.target.closest("[data-act]");
  if (el && el.type === "radio" && ACTIONS[el.dataset.act]) ACTIONS[el.dataset.act](el);
});
```
- v2: `detail`은 `location.hash = "#/book/" + id`로 바꾸고 라우터가 `setState({route})`. `book_id`로만 동일성 판단(D-07b ③).

**boot + capture** (현행 264~275행) — `?capture=1|2`는 body class 토글로 확장(`is-capture` 기존 CSS `base.css` 97~100행 재사용, `is-capture-2`는 인스펙터 유지):
```js
(async function boot() {
  if (api.config.capture) document.body.classList.add("is-capture");
  state.source = await api.resolveSource();
  state.steps = await api.loadSteps();
  try { state.meta = await api.loadMeta(state.source); }
  catch { state.meta = await fetch("mock/meta_onboarding.json").then((r) => r.json()); }
  state.unsupported = state.meta.categories.filter((c) => !c.supported).map((c) => c.name);
  render();
})();
```

**폐기 대상**(계승하지 않음): `PRESET_PREFS`(11~16행)·`ORDER` 선형 머신(136~149행 — `onboarding_step.js` 안으로)·`PRESETS`/`runOnboarding`(222~252행, 시나리오 프리셋은 v2 명세에 없음)·`state.screen` 문자열 라우팅.

---

### 2-2. `demo/js/router.js` (utility, hashchange) — 신규

**Analog:** 없음(직접 대응 파일 없음). 가장 가까운 것은 `app.js` 254~262행의 "전역 리스너 1개 → 딕셔너리 디스패치". 같은 스타일로:
```js
// 해시 → {page, params}. 라우트 표는 이 파일에만. 기본 "#/" = showcase(demo.md).
const ROUTES = [
  ["", "showcase"], ["onboarding", "onboarding"], ["home", "home"], ["book/:id", "book"],
  ["reader/:id", "reader"], ["library", "library"], ["refresh", "refresh"], ["dashboard", "dashboard"],
];
export function parse(hash = location.hash) { /* "#/book/12" → {page:"book", params:{id:12}} */ }
export function listen(onRoute) { addEventListener("hashchange", () => onRoute(parse())); onRoute(parse()); }
```
- `:id`는 `Number()`로 변환(카탈로그 `book_id`는 int). 화면 문자열은 `demo.md` 라우팅 목록 그대로.

---

### 2-3. `demo/js/api.js` (service, request-response) — 재작성

**Analog:** `demo/js/api.js`(현행 113줄). 골격 유지, 상수·경로·함수 추가.

**config + API_BASE** (현행 4~15행) — `API_BASE = ""`(같은 origin, `.claude/rules/demo.md`), `capture`를 `"1"|"2"|null`로:
```js
const API_BASE = "https://REPLACE-ME.hf.space";   // ← "" 로. hf.space 는 D-07 grep 0건 대상
const TIMEOUT_MS = 4000;
const qs = new URLSearchParams(location.search);
export const config = {
  source: qs.get("source") || null,
  apiBase: (qs.get("api") || API_BASE).replace(/\/$/, ""),
  capture: qs.get("capture") === "1",
};
```

**get/post 타임아웃 래퍼** (현행 17~28행, 100~113행) — 그대로. 경로에 `/api` 접두어:
```js
async function get(path) {
  const ctl = new AbortController();
  const timer = setTimeout(() => ctl.abort(), TIMEOUT_MS);
  try {
    const res = await fetch(config.apiBase + path, { signal: ctl.signal });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } finally { clearTimeout(timer); }
}
const local = (path) => fetch(path).then((r) => {
  if (!r.ok) throw new Error(`HTTP ${r.status} ${path}`);
  return r.json();
});
```

**source 분기 시그니처** (현행 60~89행) — 각 함수가 `(source, args)`를 받아 mock/api를 덮는 구조 유지. 클라이언트 fallback은 `fallback/popular.json` + 사유 필드:
```js
export async function getRecommend(source, args) {
  if (source === "mock") { await ensurePool(); return mock.getRecommend(args); }
  const p = new URLSearchParams({ user_key: args.userKey || "", snapshot_id: args.snapshotId || "",
    model: args.model, context: args.context || "" });
  try { return await get(`/recommend?${p}`); }            // ← `/api/recommend`
  catch (err) {
    const fb = await local("fallback/popular.json");
    return { ...fb, client_fallback_reason: String(err.message || err) };
  }
}
```
- `ensurePool()`(35~42행)은 `mock/books.json` 1개 → `mock/catalog_kr.json` + `mock/neighbors_kr.json` 2개 `Promise.all`로.
- 신규 함수(api 경로 · mock 대응): `postEvents(/api/events, 배치 ≤50)` · `postRating(/api/ratings)` · `getState(/api/users/{k}/state)` · `deletePersonalization(DELETE /api/users/{k}/personalization)` · `getDashboard(/api/dashboard)` · `getShowcase(/api/showcase, mock은 local("mock/showcase.json"))`.
- **D-07 grep 0건**: `"/recommend"` 문자열은 `"/api/recommend"`로, `resetMockState`·`static_popular`(인스펙터)는 제거.

---

### 2-4. `demo/js/mock.js` (service, 상태 시뮬레이션) — 폐기 후 새로

**Analog(골격):** `demo/js/mock.js`(현행 206줄) — `init/byId/index Map`(19~33행)·`rid()`(23행)·`interleave`(95~109행)·dedup 루프(179~191행)·응답 조립(196~203행). **Analog(규칙 정본):** `src/millie_rec/serving/compose.py`·`badges.py`·`persona.py`·`onboarding_api.py`·`privacy_api.py`·`ranking/blend.py`.

**풀 초기화 + ID 발급** (현행 19~34행) — `catalog_kr.json`(배열)·`neighbors_kr.json`(`{book_id: [[dst, w], …]}`) 두 개:
```js
let pool = []; let index = new Map(); let snapSeq = 0;
const rid = (p) => p + Math.random().toString(36).slice(2, 8);   // 서버 형식 rec_<6hex>·snap_<6hex>·cand_<6hex>
export function init(books) { pool = books; index = new Map(books.map((b) => [b.book_id, b])); }
export const byId = (id) => index.get(Number(id));
```

**행 순서·크기·제목 상수 — `compose.py` 35~45행 그대로 JS 상수로 옮긴다:**
```python
ROW_SIZE = 12
ANCHOR_NEIGHBORS = 20
ROW_ORDER = ("continue_reading", ROW_ANCHOR_PREFIX, "persona_shelf", "trending", "fresh_picks")
SOURCE_CONTENT = "content"           # 데모 카탈로그 이웃은 콘텐츠 유사도 — itemknn 아님(/contract-sync 5번 검사)
TITLE_CONTINUE, TITLE_FRESH = "이어 읽기", "새로운 발견"
TITLE_PERSONA, TITLE_PERSONA_DEFAULT = "{name}의 서가", "회원님의 서가"
SUBTITLE_ANCHOR = "결이 비슷한 책"
REASON_ANCHOR = "『{title}』을 좋아하셨다면"       # 조사 '을' 통일(D-03)
```
- `trending` 상수는 `serving/fallback.py` 13~16행: `TRENDING_ROW_ID="trending"`, `TRENDING_TITLE="지금 많이 읽는 책"`, `TRENDING_PURPOSE="fallback"`, `SOURCE_POPULARITY="popularity"`.
- purpose: `continue_reading`→`resume`, `anchor_*`/`persona_shelf`→`discover`, `trending`→`fallback`, `fresh_picks`→`explore`.

**앵커 행 = 이웃 조회 (`compose.py` 95~114행)** — mock은 `neighbors_kr.json[seed1]` 상위 20 → 시드·제외 제거 → 12권:
```python
def _neighbor_row(row_id, title, subtitle, seed, nbrs, catalog, exclude):
    ok = set(catalog.eligible([b for b, _ in nbrs])) - exclude - {int(seed)}
    picked = [(b, w) for b, w in nbrs if b in ok][:ROW_SIZE]
    items = tuple(ScoredItem(b, float(w), SOURCE_CONTENT, title, position=n, source_channels=CH_CONTENT) ...)
    if not items: return None
    return Row(row_id, title, "discover", joined, subtitle, {SOURCE_CONTENT: len(joined)})
```
- row_id = `"anchor_" + seed1` (`contracts.ROW_ANCHOR_PREFIX`), seed1 = 최신 스냅샷 `seeds[0]`. `after_completion` 행도 같은 함수로(완독한 책의 이웃, D-01) — row_id `"after_completion"`, purpose `"resume"`.

**dedup — book_id + 정규화 제목 (`compose.py` 58~60행, 159~176행)**:
```python
def normalize_title(s): return re.sub(r"[^\w]", "", str(s or "")).casefold()

def _dedup(rows):
    seen_ids, seen_titles, removed, out = set(), set(), 0, []
    for row in rows:
        kept = []
        for i in row.items:
            key = normalize_title(i.title)
            if i.book_id in seen_ids or (key and key in seen_titles): removed += 1; continue
            seen_ids.add(i.book_id); (key and seen_titles.add(key)); kept.append(replace(i, position=len(kept)))
        out.append(replace(row, items=tuple(kept), channel_mix=_mix(kept)))
    return tuple(out), removed
```
- JS: `s.replace(/[^\p{L}\p{N}_]/gu, "").toLowerCase()`. 이것이 '도슨트북' 2권(D-07b ③) 처리 규칙이다.

**비개인화(익명·consent=false·철회 후) = trending + fresh_picks만 (`compose.py` 240~243행, 05-CONTEXT D-04)**:
```python
if level >= FALLBACK_SEGMENT_POP:
    trend = trending_row(with_meta(tuple(items)[:ROW_SIZE], catalog))
    rows = (trend, _fresh(catalog, (), (), all_categories, exclude))
```

**fresh_picks = 선택 카테고리 밖 + 미선택 카테고리 인기 라운드로빈 (`compose.py` 127~156행)** — mock은 `pool.filter(pop_rank순)`으로 카테고리별 30권 풀을 `zip_longest`식으로 섞는다(현행 mock.js `interleave` 95~109행이 같은 라운드로빈 골격).

**배지 6종 — `badges.py` 11~40행을 JS로 1:1 (이중 구현 예외 = 표시 규칙)**:
```python
REVIEW_MIN_COUNT = 3
REVIEW_MIN_COUNT_NO_RATING = 10

def badge_for(meta, *, criterion, seed_authors=frozenset(), seed_publishers=frozenset()):
    rank, avg = meta.get("pop_rank"), meta.get("average_rating")
    n = meta.get("review_count") or 0
    best = Badge("bestseller", f"인기 {rank}위") if rank is not None else None
    if criterion == "bestseller": return best
    if criterion == "review":
        if avg is not None and n >= REVIEW_MIN_COUNT: return Badge("review", f"★{avg:.1f} · 리뷰 {n}")
        if n >= REVIEW_MIN_COUNT_NO_RATING: return Badge("review", f"리뷰 {n}")
        return best
    if criterion == "author" and meta.get("authors") in seed_authors: return Badge("author", f"{meta['authors']} 작가")
    if criterion == "publisher" and meta.get("publisher") in seed_publishers: return Badge("publisher", f"{meta['publisher']} 출판")
    if criterion == "buzz" and meta.get("millie_label"): return Badge("buzz", str(meta["millie_label"]))
    return None
```
- `criterion`은 **배지 타입 id**(`author publisher bestseller buzz review`)이며 화면 라벨("베스트셀러")이 아니다 — `onboarding_meta.json` `criteria[].id`↔`label` 매핑을 mock.js가 들고 S3 선택 라벨을 id로 바꿔야 한다. 현행 mock.js 78~92행의 `criterion === "베스트셀러"` 라벨 비교·`type: "rating"`은 폐기. `authors` 비교는 문자열 전체(서버는 split 안 함).
- 카드 필드로 `review_count`·`average_rating`·`publisher`·`millie_label`·`pop_rank`가 필요하다 → D-02 `catalog_kr.json` 카드 필드 목록에 `review_count`·`average_rating`·`publisher` 추가 필요(D-02 목록에 빠져 있음).

**페르소나 4종 — `persona.py` 13~34행, 53~80행 (미매핑은 sha256 → JS는 `crypto.subtle` 비동기라 부담. 대안: 결정적 문자열 해시(현행 `ui.js hue()` 방식) 사용 — 서버와 결과가 다를 수 있음을 주석에 명시)**:
```python
PERSONAS = (("오디세우스","오디세이아","지혜로 승리하리라!"), ("셜록 홈즈","주홍색 연구","사소한 것이 가장 중요하다."),
            ("돈키호테","돈키호테","이룰 수 없는 꿈을 꾸리라!"), ("제인 에어","제인 에어","나는 나 자신의 주인입니다."))
CATEGORY_TO_PERSONA = {"경제경영":0,"자기계발":0,"IT":0,"소설":1,"과학":1,"철학":1,"인문":2,"역사":2,"사회":2,"에세이/시":3,"라이프스타일":3}
DESCRIPTION = "회원님은 {cats}{eul} 즐기고, {criterion}{ro} 책을 고르는 독서가입니다."
CATS_NONE, CRITERION_NONE = "다양한 분야", "취향"
# shown = f"{cats[0]}{_josa(cats[0],'과','와')} {cats[1]}" (2개) / cats[0] / CATS_NONE
# ro = _josa(crit, "으로", "로")  — ㄹ 받침은 '로'
```
- 조사 함수는 `ui.js` `josa(word, withFinal, without)` 30~37행 재사용(현행 mock.js도 이미 import).

**후보 30권 라운드로빈 (`onboarding_api.py` 73~83행, D-15)**:
```python
def _round_robin(catalog, cats, n):
    lists = [catalog.popular([c], n=n) for c in cats]      # 카테고리별 pop_rank 순
    seen, ids = set(), []
    for row in itertools.zip_longest(*lists):
        for b in row:
            if b is not None and b not in seen and len(ids) < n: seen.add(b); ids.append(b)
    return catalog.eligible(ids)
```
- 현행 mock.js `getCandidates` 37~47행은 카테고리 합집합 인기순이라 소설이 독식 → 라운드로빈으로 교체. `subcategories`는 필터에 쓰지 않는다.

**가중치 표시값 — `ranking/blend.py` 10~15행, 18~43행 (mock은 이 공식으로 결정적 표시값만 계산; 스코어링 아님)**:
```python
ALPHA0, BETA0, GAMMA0 = 0.6, 0.3, 0.1
TAU = 20; ALPHA_FLOOR = 0.2; ROUND = 3
n = len(user.history)                       # reader_open·qualified_read·completion distinct 책 수(D-05)
alpha = max(ALPHA_FLOOR, ALPHA0 * math.exp(-n / TAU)); rest = 1.0 - alpha
raw = {"alpha": alpha, "beta": rest * 0.75, "gamma": rest * 0.25}
present = {"alpha": bool(seeds), "beta": bool(history), "gamma": bool(session)}   # session = 30분 내 reader_open·detail_click
kept = {k: v for k, v in raw.items() if present[k]}; total = sum(kept.values())
if total <= 0: return {alpha:0,beta:0,gamma:0}   # 익명
return {k: round(kept.get(k, 0) / total, 3) for k in ("alpha","beta","gamma")}
```
- 재설정 부스트 α+0.15(D-08: `snapshots_count ≥ 2` ∧ 24h 이내), 세션 활성 γ+0.1은 표시 규칙으로 더한 뒤 재정규화.

**A/B 셀 (`demo_api.py` 78~80행)** — `"A" if int(sha256(user_key)[:8],16) % 2 == 0 else "B"`. mock은 `userKey` 생성 시 1회 결정(비동기 회피용으로 간단 해시 허용, 주석 명시). 셀 A→`hybrid`, B→`hybrid_div`(05-CONTEXT D-01); `model=` 강제 시 `forced: true`.

**서재 버킷 (`privacy_api.py` 25행, 79~89행)** — `state.json`·D5 내 서재의 규칙:
```python
READ_TYPES = ("reader_open", "qualified_read")
completed = _ids(rows, ("completion",))
buckets = {"added": _ids(rows, ("library_add",)),
           "reading": [b for b in _ids(rows, READ_TYPES) if b not in completed],
           "completed": completed}
# _book → {"book_id", "title", "image_url"}; snapshots[i] = {snapshot_id, created_at, criterion, categories, active: i==0}
```

**응답 조립 — 현행 mock.js 196~203행을 `RecommendOut` 필드로 고친 형태**(`latency_ms` **float**, 단계별은 `latency_breakdown`, `total` 포함 — `compose.py` 300행 `{**breakdown, "total": ms}`):
```js
return {
  recommendation_id: rid("rec_"), model_version: `${model}_v1`,      // contracts.MODEL_VERSION_SUFFIX
  preference_snapshot_id: snapshotId, user_key: userKey, cell, forced,
  fallback_level: level, context: readingTime,
  latency_ms: total, latency_breakdown: { feature: 3, retrieval: 21, ranking: 14, rerank: 4, compose: 2, total },
  user_state_weights: weightsFor(...), dedup_removed: removed, nearline_lag_s: null,
  items: [], rows,                                                     // items 평탄화는 level ≤1 상위 40
};
```
- 항목(ItemOut)은 `{book_id, score, source, reason, title, authors, image_url, position, source_channels, badge, book_format, difficulty}` 12필드(`export_millie_fallback.py` 61~76행 `_item`이 실물 예시). `format`·`year`·`timestamp` 키는 D-07 grep 0건 대상.

---

### 2-5. `demo/js/screens/d2_home.js` (← `s7_home.js`) — 개명 + 필드 수정

**Analog:** `demo/js/screens/s7_home.js`(53줄) 전체. 바꾸는 곳만:
```js
// 7~16행 tile()
${cover(item, item.format === "PDF" ? '<span class="cover__pdf">PDF</span>' : "")}   // ← item.book_format ("오디오북"|"챗북"이면 뱃지, "전자책"은 생략)
<div class="tile__title">${esc(item.title)}</div>                                      // ← esc(item.title ?? "(제목 없음)")  D-07b ④
<div class="tile__author">${esc(item.authors)}</div>                                   // 유지 — 같은 제목 다른 book_id 구분(D-07b ③)
${badge(item.badge)}                                                                    // ui.js badge(): data-type=6종 그대로
// 30~53행 render()
const clientFb = rec?.model_version === "static_popular";      // ← rec?.client_fallback_reason != null (model_version 은 fallback_v1)
const rows = (rec?.rows || []).filter((r) => r.items.length);   // 유지 — 빈 continue_reading 은 숨김
```
- 행 부제: `r.subtitle`(앵커 "결이 비슷한 책")을 그대로 쓰고 4~5행의 `subtitle()` 하드코딩은 제거. 셀 배지·fallback 배너(`Banner` 컴포넌트, `--banner-bg`)는 `home__head` 아래 추가. 탭바(`TabBar` 홈·서재)는 `screen__foot`.

---

### 2-6. `demo/js/screens/d3_detail.js` (← `s8_detail.js`) — 개명 + 필드 수정

**Analog:** `demo/js/screens/s8_detail.js`(29줄). 배경으로 `home(state)`를 먼저 그리고 시트를 덮는 구조(5~8행) 유지:
```js
import { render as home } from "./s7_home.js";      // ← "./d2_home.js"
export function render(state) {
  const d = state.detail; if (!d) return home(state);
  return `${home(state)}
  <div class="sheet-wrap"><div class="sheet-wrap__dim" data-act="closeSheet"></div>
    <div class="sheet"> ... ${badge(d.item.badge)} ... ${d.item.reason ? `<p class="sheet__reason">…` : ""}
      <div class="sheet__actions">
        <button class="cta is-on" data-act="read">바로 읽기</button>          // → location.hash = "#/reader/:id"
        <button class="sheet__ghost" data-act="library">서재 담기</button>
      </div>
      <button class="sheet__finish" data-act="complete">완독 처리 (데모용)</button>   // ← 제거(완독은 D4에서)
```
- v2 §2 D3: 비활성 버튼(선호 교정 — 설계만) 추가, (Should) 적합도·`DifficultyDots`(`difficulty==null`이면 미표시).

---

### 2-7. `demo/js/screens/d4_reader.js` (신규) · `demo/css/reader.css`

**Analog(마크업):** `s8_detail.js` 시트 액션 구조 + `onboarding_step.js` 77행 진행바:
```js
<div class="progress"><div class="progress__fill" style="width:${step.progress * 100}%"></div></div>
```
- "진행률 %"만 표시(가짜 페이지 번호 금지, `demo.md`). `qualified_read` 임계는 `contracts.QUALIFIED_READ_MINUTES = 15` 상수 표기("T=15분"). 별점 모달(`RatingModal`, 별 44px, 1탭 즉시 `POST /api/ratings` `{rating_id, user_key, book_id, stars 1~5, ts, recommendation_id}`)은 Should.
- `DemoLabel` 띠("데모 전용 · 실제 밀리 화면 아님", `--demo-label`)를 상단에.

**Analog(CSS):** `home.css` `.sheet*`(시트·딤·액션 버튼) + `onboarding.css` `.progress`. 색 리터럴 금지 — `tokens.css`에 §6 토큰 추가 후 `var(--star)`·`var(--star-off)`.

---

### 2-8. `demo/js/screens/d5_library.js` (신규) · `demo/css/library.css`

**Analog(마크업):** `s7_home.js` 7~16행 `tile()`(108px 카드) + `inspector.js` 29~32행 `sec()`/`kv` dl 패턴(스냅샷 타임라인 항목):
```js
function sec(title, inner, hint = "") {
  return `<section class="insp-sec"><h2 class="insp-sec__title">${esc(title)}</h2>
    ${hint ? `<p class="insp-sec__hint">${esc(hint)}</p>` : ""}${inner}</section>`;
}
```
- 3버킷(`added`·`reading`·`completed`)은 `state.json`/`UserStateOut.library` 형태(`LibraryBook {book_id,title,image_url}`) → `title ?? "(제목 없음)"`. `Timeline`은 `snapshots[]`(`active` 강조). 동의 철회 버튼 → `deletePersonalization` → 이후 level 3(`trending`+`fresh_picks`만).

---

### 2-9. `demo/js/screens/d7_dashboard.js` (신규) · `demo/js/screens/d8_showcase.js` (신규) · `demo/css/dashboard.css`

**Analog(마크업·집계):** `inspector.js` 65~82행 `latencySection`(막대 = `.lat__track/.lat__fill` width %) 및 84~99행 `weightsSection`(KPI 카드 3열):
```js
const stages = ["feature", "retrieval", "ranking", "rerank", "compose"];
const max = Math.max(...stages.map((k) => lat[k] || 0), 1);
const bars = stages.map((k) => `<span class="lat__name">${k}</span>
  <span class="lat__track"><span class="lat__fill" style="width:${((lat[k] || 0) / max) * 100}%"></span></span>
  <span class="lat__val">${lat[k]}ms</span>`).join("");
const totalPct = Math.min(100, (lat.total / BUDGET_MS) * 100);
```
- D7 mock: sessionStorage 이벤트를 **직접 집계**(D-03) → `DashboardOut` 형태로 만들어 렌더(`kpi: {name: {value, n, note}}`, `ab_table: [{cell, segment, n, primary, reader_open, completion, rating_mean, first_completion, p95_ms, fallback_rate}]`, `latency: {p50,p95,p99,by_stage}`, `mde_note`). 고정 예시 숫자 금지. 하단 문구 v2 §2 D7 그대로("데모 표본으로 검정하지 않음 — MDE +1%p 검출에 셀당 n만 명").
- D8: `showcase.json`(`ShowcaseOut`) → `MetricsTable`(`eval_table.rows[]` 4행 `variant`·`recall_at_20`·`ndcg_at_10`·`ild_at_10`, `split_mode`) + `personal_case`(`seeds[]`·`recommendations[]` 각 `ShowcaseBook {book_id,title,image_url,reason,badge}`) + `data_notice`(2트랙 문장) + 시작 버튼(`#/onboarding`). `s0_start.js` CTA 마크업(`<button class="cta is-light" data-act="start">`) 재사용.
- `inspector.js` 6행 `MODELS = [["pop","Pop"],["cf","CF"],["hybrid","Hybrid"],["hybrid_div","+Diversity"]]` 라벨을 비교표 행 이름에 재사용(variant 문자열은 `contracts.VARIANTS`와 동일해야 `/contract-sync` 1번 통과).

**Analog(CSS):** `inspector.css` 1~40행(`.insp-sec`·`.kv` grid `148px 1fr`·`.log` monospace) — 카드 배경은 신규 토큰 `--kpi-bg`, 상태색 `--kpi-good/warn/bad`. D7·D8 공용 파일 1개(`dashboard.css`)로 250줄 안에.

---

### 2-10. `demo/js/inspector.js` (확장)

**Analog:** 자기 자신. 바꾸는 곳:
```js
// 65~82행 latencySection — lat 은 이제 float 총합. breakdown 으로 교체(D-07b ②: 비어도 크래시 0)
const lat = state.recommend?.latency_ms;              // ← const br = state.recommend?.latency_breakdown || {}; const total = state.recommend?.latency_ms ?? 0;
// 106행·110행 modelSection
rec?.model_version === "static_popular" ? " → client fallback" : ""    // ← rec?.client_fallback_reason ? " → client fallback" : ""   (라벨은 model_version 그대로 = fallback_v1)
// 8~19행 SIGNALS 표: 키를 route/page 기준으로(S7→home, S8→book, S9→refresh, 신규 reader·library)
// 21~25행 PRESETS·125~126행 프리셋 섹션 — 폐기(v2 명세 없음)
// 48행 "Goodbooks-10k에 출판사 컬럼 없음" 문구 — 폐기(D-07 grep `goodbooks` 0건)
```
- 신규 항목: D3·D4 신호(reader_open→β, qualified_read T=15, completion→after_completion), `cell`/`forced`, `nearline_lag_s`, `channel_mix`는 113~117행 그대로(`content`·`popularity`만 나와야 함 — `itemknn` 0건).

---

### 2-11. `demo/css/tokens.css` (§6 토큰 추가) · `demo/index.html`

**tokens.css** — 43행 `:root` 블록 끝에 화면 02 §6 블록을 그대로 추가(리터럴은 이 파일에만):
```css
--difficulty-on: var(--accent);  --difficulty-off: var(--line);
--star: #F5E06E;  --star-off: #3A3A3C;
--banner-bg: var(--accent-dim);  --banner-text: #FFF3B0;
--kpi-bg: #1C1D20;  --kpi-good: #7ED37E;  --kpi-warn: #F5C46E;  --kpi-bad: #F57E7E;
--light-badge: #9AD8FF;
--demo-label: #6E6E73;
```

**index.html** — 8~12행 `<link>` 5개 뒤에 `reader.css`·`library.css`·`dashboard.css` 3줄 추가. 21~26행 `.layout`(폰+인스펙터)은 유지하고 D7·D8용 PC 컨테이너(예 `<section id="page" hidden>`)를 `main` 안에 추가하는 방식이 최소 변경. `base.css` 97~100행 `body.is-capture`(topbar·inspector 숨김)은 `?capture=1`, `?capture=2`는 새 클래스로 인스펙터만 남김.

---

### 2-12. `demo/scripts/make_mock.py` (재작성, 표준 라이브러리·시드 42)

**Analog(골격):** 현행 `make_mock.py` — **계승**: `main()`의 argparse+`write()` 클로저(295~306행), `item()`(188~200행, 필드는 ItemOut 12개로), `josa()`(151~159행), `build_rows()`의 dedup 루프(281~292행), `SEED = 42`. **Analog(형태 실물):** `scripts/export_millie_fallback.py` `_item`(61~76행)·`payload`(79~114행)·`is_eligible`(51~58행) — level 3 응답의 정확한 키 집합이 여기 있다.

**계승 골격** (현행 295~306행):
```python
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default="/tmp/goodbooks_books.csv", help="books.csv 캐시 경로")   # ← --serving (기본 artifacts/serving)
    ap.add_argument("--out", default=str(Path(__file__).resolve().parent.parent))               # 유지: demo/
    args = ap.parse_args()
    out = Path(args.out)
    (out / "mock").mkdir(parents=True, exist_ok=True)
    (out / "fallback").mkdir(parents=True, exist_ok=True)                                        # ← 제거(§0-A)
    def write(p, o):
        (out / p).write_text(json.dumps(o, ensure_ascii=False, indent=1), encoding="utf-8")
```
- 테스트 가능하게 `build(serving_dir: Path, out_dir: Path) -> dict[str, int]`(파일명→크기)를 분리하고 `main()`은 인자 파싱만(`export_millie_fallback.py` 117~123행 `export_fallback(books_path, out_path) -> int` 관례).

**ItemOut 12필드 조립 실물** (`export_millie_fallback.py` 61~76행 — `item()` 교체본):
```python
def _item(row: dict, position: int, n: int) -> dict:
    return {"book_id": int(row["book_id"]), "score": float(n - position), "source": SOURCE_POPULARITY,
            "reason": None, "title": row.get("title"), "authors": row.get("authors"), "image_url": row.get("image_url"),
            "position": position, "source_channels": [SOURCE_POPULARITY], "badge": None,
            "book_format": row.get("book_format"), "difficulty": row.get("difficulty")}
```

**노출 자격 (`export_millie_fallback.py` 51~58행)** — `catalog_kr.json`에 넣을 책 필터에 그대로:
```python
def is_eligible(row):
    url = row.get("image_url") or ""; host = urlsplit(url).hostname or ""
    return bool(row.get("title")) and host.endswith(".millie.co.kr") and "adult-cover" not in url
```

**카드 필드 화이트리스트(D-02 + 배지 필요 필드)** — `books_kr.json` 28키 중:
`book_id title authors image_url categories millie_label completion_prob expected_min category_avg_prob pop_rank difficulty book_format formats publisher average_rating review_count`. 제외 확정: `tags subtitle pub_date shelf_count resid_z len_z difficulty_source top_segment ratings_count original_publication_year subcategories`(빈 배열). `description`·`curator_note`는 books_kr.json에 이미 없음(테스트로 0건 재확인).

**폐기 대상(Goodbooks 전용)**: `CSV_URL`·`POOL_SIZE`·`load_pool()`(21~22행, 108~116행) · `UNSUPPORTED`·`CATEGORIES`·`SUBCATEGORIES`·`WEIGHTS`·`assign()`(25~89행, 119~148행 — 카테고리 임의 배정) · `badge_for()`의 `"rating"` 타입·라벨 비교(170~185행) · `PERSONAS` dict(90~105행 → `persona.py` 매핑표로) · `fallback/popular.json` 쓰기(369~402행, §0-A) · `mock/books.json`(`_note` 포함, 308~311행 → `catalog_kr.json`으로).

**생성 목록과 pydantic 대응(백엔드 01 §16 표 + Phase 6 추가)**:
| 출력 | 모델 | 입력 |
|---|---|---|
| `mock/catalog_kr.json` | (카드 dict 배열 — 계약 외, 테스트가 키 집합 단정) | `books_kr.json` eligible 행 |
| `mock/neighbors_kr.json` | (`{str(book_id): [[dst, w], …≤20]}`) | `item_edges_kr.json` |
| `mock/meta_onboarding.json` | `OnboardingMeta`(`survey_variant`·`reading_times`·`criteria[{id,label}]`·`categories[{name,supported,subcategories}]`) | `config/onboarding.json` S1/S3 옵션(D-10) + 카탈로그 카테고리 빈도(`supported = n ≥ 20`, `onboarding_api.py` 30행 `SUPPORTED_MIN`) |
| `mock/candidates_onboarding.json` | `CandidateSet`(`candidate_set_id`·`survey_variant`·`created_at`·`items[CandidateItem]`) | 라운드로빈 30권 예시 |
| `mock/preferences_response.json` | `PreferencesResponse`(`user_key`·`preference_snapshot_id`·`created_at`·`cell`·`snapshots_count`·`persona`) | 고정 예시(현행 335~343행 골격, `cell`·`snapshots_count` 추가) |
| `mock/recommend_{v}.json` ×4 | `RecommendOut` (`model_version=f"{v}_v1"`, `latency_ms` float) | Must 5행 예시(현행 344~367행 골격 — `latency_ms` 객체 → float+`latency_breakdown`) |
| `mock/state.json` | `UserStateOut`(`user_key`·`consent`·`cell`·`is_new`·`library{added,reading,completed}`·`snapshots[]`·`user_state_weights`·`nearline_lag_s`) | 예시 |
| `mock/dashboard.json` | `DashboardOut`(`generated_at`·`window`·`kpi`·`ab_table`·`mde_note`·`latency{p50,p95,p99,by_stage}`·`quality`·`events_recent`·`impressions_log`·`by_variant`·`by_hour`) | 빈 집계 예시(값은 mock.js가 세션 집계로 채움, D-03) |
| `mock/showcase.json` | `ShowcaseOut`(`philosophy`·`eval_table{split_mode,source,rows[EvalRow]}`·`metric_mapping[]`·`personal_case`·`memorable_5`·`roadmap`·`data_notice`) | `eval_table.json`: `rows[].{"recall@20","ndcg@10","ild@10"}`(문자열!) → `EvalRow.{recall_at_20,ndcg_at_10,ild_at_10}` float 변환, `meta.split_mode`·`meta.dataset`→`source`. `anchor_case`(D-08)는 `personal_case` 필드에(스키마에 `anchor_case` 없음 — `extra="forbid"`) |

**`cli demo --seeds` stdout 형식(D-08 `personal_case` 원천, `app/demo_cli.py` 16~24행, 96~103행)**:
```python
HEADER = "| # | 책 | 저자 | 분야 | 난이도 | 근거 |"
RULE = "|---|---|---|---|---|---|"
print(f"### 『{m['title']}』을 좋아하셨다면 — {NEIGHBOR_NOTE}")   # seed 당 이웃 5행 표
print(f"### hybrid_div 상위 {k} — alpha=… beta=… gamma=… · 가드 활성(n_completed=…) · …")
print(FIXED_SENTENCE)   # data.md 고정 문장 — showcase data_notice 후보
```
- 5권 미정이면 `personal_case: null` + 화면 "5권 선정 대기"(D-08). 파싱보다 `--seeds` 결과를 JSON으로 다시 만들 때 `catalog_kr.json`으로 `ShowcaseBook`을 조립하는 편이 단순.

---

### 2-13. `tests/demo/test_make_mock.py` (신규)

**Analog:** `tests/data/test_millie_export.py`(스크립트 로드·module fixture·키 집합·누출 0건·크기 상한) + `tests/serving/test_schemas.py`(pydantic 검증).

**스크립트 로드 + module fixture** (`test_millie_export.py` 76~117행):
```python
ROOT = Path(__file__).resolve().parents[2]
MAX_BYTES = 50 * 1024 * 1024        # → catalog_kr 는 2MB 목표(D-02) 별도 상수

def _load(name: str):
    """scripts/ 는 패키지가 아니므로 경로로 직접 로드한다."""
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")   # → ROOT / "demo" / "scripts" / "make_mock.py"
    module = importlib.util.module_from_spec(spec); sys.modules[name] = module; spec.loader.exec_module(module)
    return module

@pytest.fixture(scope="module")
def exported(tmp_path_factory) -> tuple[Path, dict]:
    """합성 픽스처 체인 → tmp 로 export. 실 artifacts/serving 은 건드리지 않는다."""
```
- Phase 6 판: `@pytest.fixture(scope="module") def built(tmp_path_factory, millie_serving_sample)` → `mm = _load_make_mock(); sizes = mm.build(millie_serving_sample, out)`; `millie_serving_sample`은 session scope라 module fixture에서 받아도 된다. **주의:** `millie_serving_sample`에는 `eval_table.json`이 없다 → `build()`는 없으면 `showcase.json`을 건너뛰거나 `eval_table`을 선택 인자로(테스트에서 tmp에 1KB 예시를 써 넣는 방법이 단순).

**키 집합·누출 0건 단정** (`test_millie_export.py` 129~143행):
```python
def test_books_json_rows_have_exactly_meta_fields(books_json):
    for row in books_json:
        assert set(row) == set(EXPECTED_BOOK_KEYS)

def test_books_json_excludes_author_text_and_raw_ids(exported):
    raw = (out / "books_kr.json").read_text(encoding="utf-8")
    for key in ('"description"', '"curator_note"', '"seg_dist"', '"millie_id"'):
        assert raw.count(key) == 0
```
- Phase 6: `catalog_kr.json` 카드 키 집합 == 화이트리스트, `description`·`curator_note`·`tags`·`shelf_count` 0건, 자격 없는 3권(18·19·20) 제외, `neighbors_kr.json` 각 값 ≤20·가중치 내림차순(`test_millie_export.py` 157~164행 `test_edges_json_unchanged_shape`가 같은 단정).

**pydantic 검증** (`test_schemas.py` 55~74행 + `/contract-sync` process 2):
```python
from millie_rec.serving.schemas import RecommendOut, OnboardingMeta, CandidateSet, PreferencesResponse, UserStateOut
from millie_rec.serving.schemas_should import DashboardOut, ShowcaseOut
d = json.loads((out / "mock" / "recommend_hybrid_div.json").read_text("utf-8"))
out_model = RecommendOut.model_validate(d)            # extra="forbid" 라 여분 키가 있으면 실패
assert isinstance(d["latency_ms"], float) and d["model_version"] == "hybrid_div_v1"
assert all(i["badge"] is None or i["badge"]["type"] in BADGE_TYPES for r in d["rows"] for i in r["items"])
assert "itemknn" not in {ch for r in d["rows"] for i in r["items"] for ch in i["source_channels"]}
```
- `tests/`는 무엇이든 import 가능(`.claude/rules/architecture.md`). 스크립트 상수는 import하지 말고 손으로 적는다(`test_millie_export.py` 22행 주석 관례). 전체 30초 이내·`uv run pytest`만.

---

## 3. Shared Patterns

### 3-1. HTML 이스케이프·표지·배지·조사 (`demo/js/screens/ui.js`)
**Apply to:** 모든 화면 파일(d2~d8)·mock.js(josa)
```js
export function esc(v) { return String(v ?? "").replace(/[&<>"']/g, (c) => ({ "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;" }[c])); }   // 4~7행
export function cover(book, inner = "") { … <img src="${esc(book.image_url)}" alt="" loading="lazy" referrerpolicy="no-referrer" onerror="this.remove()"> … }   // 17~22행 — 죽은 표지 = 플레이스홀더
export function badge(b) { if (!b) return ""; return `<span class="badge" data-type="${esc(b.type)}">${esc(b.text)}</span>`; }   // 24~27행
export function josa(word, withFinal, without) { … }   // 30~37행 (persona._josa 와 같은 규칙)
export function navbar({ back = true, action = "", label = "" } = {}) { … }   // 62~68행
export function cta(text, on, act) { … }   // 70~72행
```
- `cover()`는 `book.title`이 null이면 `"?"` 첫 글자 — `title ?? "(제목 없음)"` 방어는 호출 쪽(D-07b ④).

### 3-2. 화면 파일 계약: `render(state) → HTML 문자열`, 이벤트는 `data-act`
**Source:** `onboarding_step.js` 64~85행, `s6_persona.js` 6~23행 · **Apply to:** d2~d8 전부. 화면 파일은 `import`를 `./ui.js`로만 한정(현행 전 화면 파일 동일). 상태 변경·fetch 금지.

### 3-3. 이름 정본은 `contracts.py` (문자열 하드코딩 시 값 일치 필수)
**Source:** `src/millie_rec/contracts.py` 38~92행 · **Apply to:** mock.js·api.js·inspector.js·make_mock.py·테스트
```python
EVENT_TYPES = ("impression","detail_click","library_add","reader_open","qualified_read","completion",
               "rating","preference_started","preference_step","preference_book_selected","preference_book_deselected",
               "preference_completed","preference_restarted")          # 13종 — consent_granted·preference_skipped·recommend 는 없음(현행 app.js 143·156·99행 폐기)
VARIANTS = ("pop","cf","hybrid","hybrid_div"); MODEL_VERSION_SUFFIX = "_v1"; MODEL_VERSION_FALLBACK = "fallback_v1"
ROW_IDS = ("after_completion","continue_reading","persona_shelf","similar_readers","trending","fresh_picks","light_start"); ROW_ANCHOR_PREFIX = "anchor_"
ROW_PURPOSES = ("resume","discover","fallback","explore")
BADGE_TYPES = ("bestseller","review","author","publisher","buzz","light")
BUDGET_MS = 200; QUALIFIED_READ_MINUTES = 15
FALLBACK_PERSONALIZED, FALLBACK_CACHE, FALLBACK_SEGMENT_POP, FALLBACK_GLOBAL_POP = 0, 1, 2, 3
```

### 3-4. 형태 정본은 `serving/schemas.py` (`extra="forbid"`)
**Source:** `schemas.py` 51~52행 `class _Strict(BaseModel): model_config = ConfigDict(extra="forbid")` · **Apply to:** 모든 `mock/*.json`·mock.js 응답. 여분 키 1개도 검증 실패 → mock.js가 붙이는 디버그 필드(`client_fallback_reason`)는 **api.js의 클라이언트 fallback 응답에만**, 파일에는 넣지 않는다.

### 3-5. 생성기 출력 관례
**Source:** `export_millie_fallback.py` 117~123행 · `make_mock.py` 305~306행 · **Apply to:** `make_mock.py`
- `json.dumps(o, ensure_ascii=False, indent=1)` · `encoding="utf-8"` · 반환값은 바이트 크기 · stdout 1줄 요약(`print(f"[make_mock] …")`) · 파일 상단 `_note`는 계약 외 파일(`catalog_kr.json`)에만(계약 파일은 `extra="forbid"`).

### 3-6. 디자인 값은 `tokens.css`에만
**Source:** `tokens.css` 1행 주석·`demo.md` · **Apply to:** `reader.css`·`library.css`·`dashboard.css`. 기존 클래스 접두 관례(BEM 축약 `.block__elem.is-state`, 예 `.tile__title`·`.cta.is-on`) 유지.

## 4. No Analog Found

| File | Role | Data Flow | Reason / 대체 |
|---|---|---|---|
| `demo/js/router.js` | utility | hashchange | 코드베이스에 라우터 없음 — 화면 02 §1 라우팅 표 + `app.js` 이벤트 위임 스타일로 신규(≤30줄) |
| `demo/js/screens/d7_dashboard.js` 집계 로직 | service-ish | batch | sessionStorage 집계 선례 없음 — `DashboardOut` 필드 정의(`schemas_should.py` 15~52행)에서 역으로 설계. `privacy_api._library`(버킷 = `dict.fromkeys` distinct) 관례 차용 |
| `demo/mock/book_stats.json` | data | — | `BookStats` DTO는 있으나 HTTP 모델·엔드포인트 예시 없음. 난이도 점은 `catalog_kr.json.difficulty`로 충분하므로 생성 보류(Should) 권장 |

## 5. Metadata

**Analog search scope:** `demo/**`(27파일 전부 읽음) · `src/millie_rec/serving/{schemas,schemas_should,badges,compose,persona,fallback,onboarding_api,demo_api,privacy_api,state}.py` · `src/millie_rec/ranking/blend.py` · `src/millie_rec/app/demo_cli.py` · `src/millie_rec/contracts.py` · `scripts/export_millie_fallback.py` · `tests/{conftest,serving/test_schemas,data/test_millie_export,data/test_millie_catalog,app/test_server_catalog}.py` · `artifacts/serving/*.json`(형태만) · `Makefile` · `../.claude/skills/contract-sync/SKILL.md` · 백엔드 서빙 01 §16 · 화면 02 §3~§9 · 05-CONTEXT D-01~D-04·D-14~D-16
**Files scanned:** 52
**Pattern extraction date:** 2026-09-06
**CodeGraph:** MCP 도구가 이 에이전트 세션에 노출되지 않아 Read/Grep으로 대체(`.claude/rules/codegraph.md` 프리플라이트 불가 보고).
