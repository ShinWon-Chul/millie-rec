// 상태 1개(state) · 변경 1곳(setState) · 그리기 1곳(render) — 화면 구성 01 §6, 02 §4 상태 모델 v2.
// 라우팅은 router.js, data-act 처리는 actions.js, D8 프리셋은 presets.js가 맡는다.
import * as api from "./api.js";
import * as router from "./router.js";
import * as inspector from "./inspector.js";
import { createActions } from "./actions.js";
import * as presets from "./presets.js";
import { statusbar, banner, modal, esc } from "./screens/ui.js";
import { render as s0 } from "./screens/s0_start.js";
import { render as stepView } from "./screens/onboarding_step.js";
import { render as s6 } from "./screens/s6_persona.js";
import { render as d2 } from "./screens/d2_home.js";
import { render as d3 } from "./screens/d3_detail.js";
import { render as d4 } from "./screens/d4_reader.js";
import { render as d5 } from "./screens/d5_library.js";
import { render as d7 } from "./screens/d7_dashboard.js";
import { render as d8 } from "./screens/d8_showcase.js";

const VARIANTS = ["pop", "cf", "hybrid", "hybrid_div"];
const QUALIFIED_READ_MINUTES = 15;
const BATCH = 50;
const EMPTY_PREFS = () => ({ readingTime: null, categories: [], criterion: null, subcategories: [], seedBooks: [] });

const state = {
  route: { page: "showcase", params: {} },
  source: "mock",
  userKey: null,
  cell: null,
  consent: null,
  screen: "S0",
  resetting: false,
  prefs: EMPTY_PREFS(),
  steps: [],
  meta: null,
  candidateSet: { id: null, items: [], impressions: [] },
  snapshots: [],
  model: null,
  recommend: null,
  detail: null,
  reading: null,
  ratings: {},
  library: { added: [], reading: [], completed: [] },
  libraryTab: "added",
  userState: null,
  mydata: null,
  dashboard: null,
  showcase: null,
  health: null,
  nearlineLagSec: null,
  events: [],
  toast: null,
  banner: null,
  modal: null,
};

const $phone = document.getElementById("phone");
const $insp = document.getElementById("inspector");
const $page = document.getElementById("page");
const $toast = document.getElementById("toast");

function setState(patch) {
  Object.assign(state, patch);
  render();
}

const snap = () => state.snapshots[state.snapshots.length - 1];
const criterionId = () => state.meta?.criteria?.find((c) => c.label === state.prefs.criterion)?.id ?? null;

let flushTimer = null;
let impressedRecId = null;

/** EventIn 1건을 만들어 인스펙터 로그 + sessionStorage 큐에 넣는다(필드 이름은 contracts.Event 그대로). */
function log(event_type, fields = {}) {
  const ev = {
    event_id: crypto.randomUUID(),
    user_key: state.userKey,
    event_type,
    ts: new Date().toISOString(),
    recommendation_id: state.recommend?.recommendation_id ?? null,
    model_version: state.recommend?.model_version ?? null,
    preference_snapshot_id: snap()?.id ?? null,
    ...fields,
  };
  const bits = [ev.book_id != null && `book=${ev.book_id}`, ev.row_id && `row=${ev.row_id}`,
    ev.position != null && `pos=${ev.position}`, ev.payload && JSON.stringify(ev.payload)];
  state.events.push({ t: ev.ts.slice(11, 19), event_type, detail: bits.filter(Boolean).join(" ") });
  if (state.events.length > 200) state.events = state.events.slice(-200);
  const q = JSON.parse(sessionStorage.getItem("millie_events") || "[]");
  q.push(ev);
  sessionStorage.setItem("millie_events", JSON.stringify(q));
  flush();
}

/** 큐를 50개씩 잘라 보낸다. 이벤트 유실은 화면을 막지 않는다 — await 하지 않고 성공 여부와 무관하게 비운다. */
function flush() {
  if (flushTimer) return;
  flushTimer = setTimeout(() => {
    flushTimer = null;
    const q = JSON.parse(sessionStorage.getItem("millie_events") || "[]");
    sessionStorage.setItem("millie_events", "[]");
    for (let i = 0; i < q.length; i += BATCH) {  // 전송 실패는 삼킨다 — 수신율은 관제 대시보드가 드러낸다
      Promise.resolve().then(() => api.postEvents(state.source, q.slice(i, i + BATCH))).catch(() => {});
    }
  }, 120);
}

function screenHTML() {
  const p = state.route.page;
  if (p === "home") return d2(state);
  if (p === "book") return d3(state);
  if (p === "reader") return d4(state);
  if (p === "library") return d5(state);
  if (state.screen === "S0") return s0(state);
  if (state.screen === "S6") return s6(state);
  const st = state.steps.find((s) => s.id === state.screen);
  return st ? stepView(state, st, state.meta) : s0(state);
}

/** modal() 에 넘기는 마크업은 여기서 이미 esc() 한 것만. "rating" 모달은 D4 화면 파일이 그린다. */
function modalHTML() {
  if (state.modal === "mydata") return modal(`<h3>내 데이터</h3><pre>${esc(JSON.stringify(state.mydata, null, 1))}</pre><button class="cta is-on" data-act="closeModal">닫기</button>`);
  if (state.modal === "withdraw") return modal(`<h3>맞춤 추천 동의를 철회할까요?</h3><p>스냅샷, 이벤트, 별점, 추천 로그가 삭제되고 이후에는 비개인화 인기 도서만 보입니다.</p><button class="cta is-on" data-act="withdrawConfirm">철회</button><button class="sheet__ghost" data-act="closeModal">취소</button>`);
  return "";
}

function render() {
  const pc = state.route.page === "dashboard" || state.route.page === "showcase";
  document.body.classList.toggle("is-page", pc);
  document.body.classList.toggle("is-showcase", state.route.page === "showcase");  // "← 처음 화면" 숨김
  $page.hidden = !pc;
  if (pc) {
    $page.innerHTML = state.route.page === "dashboard" ? d7(state) : d8(state);
  } else {
    $page.innerHTML = "";
    const key = state.route.page + state.screen;  // 같은 화면을 다시 그릴 때만 .screen 스크롤 유지 — 옵션 클릭마다 맨 위로 튀지 않게
    const top = key === render.last ? ($phone.querySelector(".screen")?.scrollTop ?? 0) : 0; render.last = key;
    $phone.innerHTML = statusbar() + banner(state.banner) + screenHTML() + modalHTML();
    if (top) $phone.querySelector(".screen").scrollTop = top;
    $insp.innerHTML = inspector.render(state);
  }
  document.getElementById("bar-model").textContent = state.model ?? (state.cell === "A" ? "hybrid" : state.cell === "B" ? "hybrid_div" : "auto");
  document.getElementById("bar-version").textContent = state.health?.model_version ?? "-";
  const dot = document.getElementById("bar-source");
  dot.textContent = state.source; dot.dataset.source = state.source;
  $toast.hidden = !state.toast;
  $toast.textContent = state.toast ?? "";
}

function toast(msg) {
  state.toast = msg;
  render();
  setTimeout(() => { state.toast = null; render(); }, 3000);
}

async function requestRecommend() {
  state.recommend = await api.getRecommend(state.source, {
    userKey: state.userKey, snapshotId: snap()?.id ?? null,
    model: state.model, k: 40, context: state.prefs.readingTime,
  });
  const r = state.recommend;
  state.nearlineLagSec = r?.nearline_lag_s ?? null;
  state.cell = r?.cell ?? state.cell;
  const lvl = r?.fallback_level ?? 3;
  // 위에서 먼저 맞는 것 1개. 건너뛰기·철회(②)가 서버측 폴백(③)보다 앞이라 문구가 유지된다.
  if (r?.client_fallback_reason) {
    state.banner = "추천 서버 응답이 없어 정적 인기 목록으로 대체했습니다 (fallback_level 3, client)";
  } else if (state.consent === false || (lvl === 3 && !snap()?.id)) {
    state.banner = "비개인화 인기 도서";
  } else if (lvl >= 1) {
    state.banner = `개인화 응답이 지연되어 캐시와 인기 도서로 대체했습니다 (level ${lvl})`;
  } else {
    state.banner = null;
  }
  const recId = r?.recommendation_id ?? null;
  if (recId && recId !== impressedRecId) {
    impressedRecId = recId;
    (r.rows ?? []).forEach((row) => (row.items ?? []).forEach((i) =>
      log("impression", { book_id: i.book_id, row_id: row.row_id, position: i.position, surface: "home" })));
  }
}

async function onRoute(route) {
  state.route = route;
  const p = route.page;
  try {
    if (p === "showcase") state.showcase ??= await api.getShowcase(state.source);
    if (p === "onboarding" && !state.prefs.readingTime && state.screen !== "S6") {
      Object.assign(state, { resetting: false, screen: "S0" });
    }
    if (p === "refresh") {
      if (!state.resetting) log("preference_restarted", { payload: { from: snap()?.id ?? "none" } });
      Object.assign(state, { prefs: EMPTY_PREFS(), resetting: true, screen: "S1" });
    }
    if (p === "home") await requestRecommend();
    if (p === "book") {
      const id = route.params.id;
      if (state.detail?.item.book_id !== id) {
        const found = (state.recommend?.rows ?? [])
          .flatMap((r) => (r.items ?? []).map((i) => [r.row_id, i])).find(([, i]) => i.book_id === id);
        state.detail = found ? { item: found[1], rowId: found[0] } : null;
      }
      if (!state.detail) location.hash = "#/home";
    }
    if (p === "reader" && state.reading?.bookId !== route.params.id) {
      state.reading = { bookId: route.params.id, progressPct: 0, virtualMinutes: 0, qualified: false, completed: false };
      log("reader_open", { book_id: route.params.id, row_id: state.detail?.rowId ?? null, surface: "detail" });
    }
    if (p === "library") {
      state.userState = await api.getUserState(state.source, state.userKey);
      state.library = state.userState?.library ?? { added: [], reading: [], completed: [] };
    }
    if (p === "dashboard") state.dashboard = await api.getDashboard(state.source);
  } catch (e) {
    console.warn("[route]", p, e);
  }
  render();
}

const ACTIONS = createActions({
  state, setState, render, log, snap, criterionId, requestRecommend,
  api, presets, VARIANTS, QUALIFIED_READ_MINUTES, toast,
});

document.addEventListener("click", (e) => {
  const el = e.target.closest("[data-act]");
  if (!el || el.tagName === "INPUT") return;   // 라디오는 change 이벤트에서만 처리
  ACTIONS[el.dataset.act]?.(el);
});
document.addEventListener("change", (e) => {
  const el = e.target.closest("[data-act]");
  if (el && el.type === "radio") ACTIONS[el.dataset.act]?.(el);
});

(async function boot() {
  try {
    state.userKey = localStorage.getItem("millie_user_key") || crypto.randomUUID();
    localStorage.setItem("millie_user_key", state.userKey);
    const cap = api.config.capture;
    if (cap === "1") document.body.classList.add("is-capture");
    if (cap === "2") document.body.classList.add("is-capture-2");
    state.source = await api.resolveSource();
    state.health = await api.health(state.source);
    state.steps = await api.loadSteps();
    state.meta = (await api.loadMeta(state.source))
      ?? { survey_variant: "v1", reading_times: [], criteria: [], categories: [] };
  } catch (e) {
    console.warn("[boot]", e);
  }
  router.listen(onRoute);
})();
