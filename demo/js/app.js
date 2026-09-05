// 상태를 바꾸는 곳은 setState 하나, 화면을 그리는 곳은 render 하나 (화면설계 §6).
import * as api from "./api.js";
import * as inspector from "./inspector.js";
import { statusbar } from "./screens/ui.js";
import { render as s0 } from "./screens/s0_start.js";
import { render as stepView } from "./screens/onboarding_step.js";
import { render as s6 } from "./screens/s6_persona.js";
import { render as s7 } from "./screens/s7_home.js";
import { render as s8 } from "./screens/s8_detail.js";

const PRESET_PREFS = {
  readingTime: "저녁, 하루를 마치며",
  categories: ["IT", "소설", "철학"],
  criterion: "베스트셀러",
  subcategories: ["개발/프로그래밍", "SF", "서양"],
};

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

function setState(patch) {
  Object.assign(state, patch);
  render();
}

const step = (id) => state.steps.find((s) => s.id === id);
const snap = () => state.snapshots[state.snapshots.length - 1];

function log(event_type, detail = "") {
  state.events.push({ t: new Date().toTimeString().slice(0, 8), event_type, detail });
  api.postEvent(state.source, {
    event_type, user_key: state.userKey, recommendation_id: state.recommend?.recommendation_id,
    model_version: state.recommend?.model_version,
    preference_snapshot_id: snap()?.id, timestamp: new Date().toISOString(),
  });
}

/** 프리셋은 항상 깨끗한 상태에서 시작한다 (스냅샷 번호까지 초기화). */
function resetAll() {
  api.resetMockState();
  Object.assign(state, {
    consent: null, snapshots: [], userKey: null, recommend: null, events: [], detail: null,
    prefs: { readingTime: null, categories: [], criterion: null, subcategories: [], seedBooks: [] },
    candidateSet: { id: null, items: [], impressions: [] },
    history: { readerOpens: [], libraryAdds: [], lastCompleted: null },
    resetting: false, resetBoost: false, chipHot: false,
  });
}

function screenHTML() {
  if (state.screen === "S0") return s0();
  if (state.screen === "S6") return s6(state);
  if (state.screen === "S7") return s7(state);
  if (state.screen === "S8") return s8(state);
  const st = step(state.screen);
  return st ? stepView(state, st, state.meta) : s0();
}

function render() {
  $phone.innerHTML = statusbar() + screenHTML();
  $insp.innerHTML = inspector.render(state);
  document.getElementById("bar-model").textContent = state.model;
  const dot = document.getElementById("bar-source");
  dot.textContent = state.source;
  dot.dataset.source = state.source;
}

async function loadCandidates() {
  const res = await api.getCandidates(state.source, {
    categories: state.prefs.categories, subcategories: state.prefs.subcategories, n: 30,
  });
  // 노출 로그 = candidate_set_id / book_id / position / selected. "미선택 ≠ negative"의 근거.
  state.candidateSet = {
    id: res.candidate_set_id,
    items: res.items,
    impressions: res.items.map((b) => ({ book_id: b.book_id, position: b.position, selected: false })),
  };
  log("impression", `set=${res.candidate_set_id} n=${res.items.length}`);
}

async function requestRecommend() {
  state.recommend = await api.getRecommend(state.source, {
    model: state.model, prefs: state.prefs, history: state.history,
    consent: state.consent, resetBoost: state.resetBoost,
    snapshotId: snap()?.id, persona: snap()?.persona, userKey: state.userKey,
    context: state.prefs.readingTime,
  });
  log("recommend", `model=${state.model} fallback=${state.recommend.fallback_level}`);
}

async function completeOnboarding() {
  const res = await api.postPreferences(state.source, {
    prefs: state.prefs, consent: state.consent, userKey: state.userKey,
  });
  state.userKey = res.user_key;
  // 스냅샷은 추가만 한다 — 독서 기록과 "이어 읽기"는 그대로 남는다
  state.snapshots.push({
    id: res.preference_snapshot_id, createdAt: res.created_at,
    prefs: { ...state.prefs }, persona: res.persona,
  });
  state.resetBoost = state.resetting;
  log("preference_completed", `snapshot=${res.preference_snapshot_id} seeds=${state.prefs.seedBooks.length}`);
  for (const id of state.prefs.seedBooks) log("library_add", `book=${id} source=onboarding`);
  setState({ screen: "S6", resetting: false, chipHot: false });
}

function togglePick(stepId, val) {
  const st = step(stepId);
  const cur = state.prefs[st.field];
  if (!Array.isArray(cur)) {
    state.prefs[st.field] = cur === val ? null : val;
  } else if (cur.includes(val)) {
    state.prefs[st.field] = cur.filter((v) => v !== val);
  } else if (cur.length < st.max) {
    state.prefs[st.field] = [...cur, val];
  }
  if (stepId === "S2") {
    const allowed = state.prefs.categories.flatMap((c) => state.meta.subcategories[c] || []);
    state.prefs.subcategories = state.prefs.subcategories.filter((s) => allowed.includes(s));
  }
  log("preference_step", `${stepId} ${st.field}=${JSON.stringify(state.prefs[st.field])}`);
  render();
}

const ORDER = ["S1", "S2", "S3", "S4", "S5"];

async function next() {
  const order = ORDER;
  const i = order.indexOf(state.screen);
  if (state.screen === "S1" && state.consent !== true) {
    state.consent = true;
    log("consent_granted", "맞춤형 서비스 제공 동의");
  }
  if (i === order.length - 1) return completeOnboarding();
  const nextId = order[i + 1];
  if (nextId === "S5") await loadCandidates();
  setState({ screen: nextId });
}

const ACTIONS = {
  start: () => { log("preference_started"); setState({ screen: "S1" }); },
  skip: async () => {
    state.consent = false;
    state.snapshots = [];
    log("preference_skipped", "consent=absent → fallback: diverse popular");
    await requestRecommend();
    setState({ screen: "S7" });
  },
  back: () => {
    const i = ORDER.indexOf(state.screen);
    if (i === 0 && state.resetting) return setState({ screen: "S7", resetting: false });
    setState({ screen: i > 0 ? ORDER[i - 1] : "S0" });
  },
  pick: (el) => togglePick(el.dataset.step, el.dataset.val),
  pickbook: (el) => {
    const id = Number(el.dataset.book);
    const cur = state.prefs.seedBooks;
    const on = cur.includes(id);
    state.prefs.seedBooks = on ? cur.filter((v) => v !== id) : [...cur, id];
    const imp = state.candidateSet.impressions.find((x) => x.book_id === id);
    if (imp) imp.selected = !on;
    log("preference_book_selected", `book=${id} pos=${el.dataset.pos} selected=${!on}`);
    render();
  },
  next,
  toHome: async () => { await requestRecommend(); setState({ screen: "S7" }); },
  detail: (el) => {
    const row = state.recommend.rows.find((r) => r.row_id === el.dataset.row);
    const item = row?.items.find((i) => i.book_id === Number(el.dataset.book));
    if (!item) return;
    log("detail_click", `book=${item.book_id} row=${row.row_id} pos=${item.position}`);
    setState({ screen: "S8", detail: { item, rowId: row.row_id } });
  },
  closeSheet: () => setState({ screen: "S7", detail: null }),
  read: async () => {
    const id = state.detail.item.book_id;
    state.history.readerOpens.push(id);
    log("reader_open", `book=${id} row=${state.detail.rowId}`);
    log("qualified_read", `book=${id}`);
    state.resetBoost = false;
    await requestRecommend();
    setState({ screen: "S7", detail: null });
  },
  library: () => {
    const id = state.detail.item.book_id;
    state.history.libraryAdds.push(id);
    log("library_add", `book=${id} source=main`);
    render();
  },
  complete: async () => {
    const id = state.detail.item.book_id;
    state.history.lastCompleted = id;
    log("completion", `book=${id}`);
    await requestRecommend();
    setState({ screen: "S7", detail: null });
  },
  reset: () => {
    log("preference_restarted", `from=${snap()?.id || "none"} (history 유지)`);
    state.prefs = { readingTime: null, categories: [], criterion: null, subcategories: [], seedBooks: [] };
    setState({ screen: "S1", resetting: true, detail: null, chipHot: false });
  },
  model: async (el) => {
    state.model = el.value;
    await requestRecommend();
    render();
  },
  preset: (el) => PRESETS[el.dataset.preset](),
  noop: () => {},
};

/** 온보딩을 자동 완주해 S6까지 보낸다 (신규 유저 A 프리셋의 공통부). */
async function runOnboarding() {
  state.consent = true;
  state.prefs = { ...PRESET_PREFS, seedBooks: [] };
  log("preference_started", "preset");
  log("consent_granted", "맞춤형 서비스 제공 동의");
  await loadCandidates();
  state.prefs.seedBooks = state.candidateSet.items.slice(0, 5).map((b) => b.book_id);
  for (const im of state.candidateSet.impressions.slice(0, 5)) {
    im.selected = true;
    log("preference_book_selected", `book=${im.book_id} pos=${im.position} selected=true`);
  }
  await completeOnboarding();
}

const PRESETS = {
  newUser: async () => { resetAll(); await runOnboarding(); },
  skipUser: async () => { resetAll(); await ACTIONS.skip(); },
  resetUser: async () => {
    resetAll();
    await runOnboarding();
    await requestRecommend();
    for (const it of state.recommend.rows[0].items.slice(0, 2)) {
      state.history.readerOpens.push(it.book_id);
      log("reader_open", `book=${it.book_id} row=${state.recommend.rows[0].row_id}`);
    }
    state.resetBoost = false;
    await requestRecommend();
    setState({ screen: "S7", chipHot: true });
  },
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

(async function boot() {
  if (api.config.capture) document.body.classList.add("is-capture");
  state.source = await api.resolveSource();
  state.steps = await api.loadSteps();
  try {
    state.meta = await api.loadMeta(state.source);
  } catch {
    state.meta = await fetch("mock/meta_onboarding.json").then((r) => r.json());
  }
  state.unsupported = state.meta.categories.filter((c) => !c.supported).map((c) => c.name);
  render();
})();
