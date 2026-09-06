// D8 쇼케이스의 시나리오 프리셋 3종. 심사자가 한 번 눌러 상태를 만들어 두고 화면을 둘러보게 한다.
// 프리셋은 항상 깨끗한 상태에서 시작한다(스냅샷 번호까지 초기화).

export const PRESET_NAMES = ["newUser", "skipUser", "resetUser"];

const EMPTY_PREFS = () => ({ readingTime: null, categories: [], criterion: null, subcategories: [], seedBooks: [] });
const FIRST_CATS = ["IT", "소설", "철학"];
const SECOND_CATS = ["인문", "역사", "에세이/시"];
const SUBS = ["개발/프로그래밍", "SF", "서양"];

function resetAll(state) {
  sessionStorage.removeItem("millie_mock_db");
  sessionStorage.removeItem("millie_events");
  localStorage.removeItem("millie_user_key");
  state.userKey = crypto.randomUUID();
  localStorage.setItem("millie_user_key", state.userKey);
  Object.assign(state, {
    consent: null, snapshots: [], recommend: null, detail: null, reading: null, ratings: {},
    library: { added: [], reading: [], completed: [] }, events: [], banner: null, model: null,
    cell: null, resetting: false, prefs: EMPTY_PREFS(),
    candidateSet: { id: null, items: [], impressions: [] },
  });
}

/** 화면 텍스트는 meta 에서 가져온다 — 하드코딩은 카테고리·세부 이름뿐이고 미지원이면 대체한다. */
function prefsFor(state, categories) {
  const cats = state.meta?.categories ?? [];
  const supported = cats.filter((c) => c.supported).map((c) => c.name);
  const picked = categories
    .map((c) => (supported.includes(c) ? c : supported[0]))
    .filter((c, i, a) => c && a.indexOf(c) === i);
  const allowed = picked.flatMap((c) => cats.find((x) => x.name === c)?.subcategories ?? []);
  return {
    readingTime: (state.meta?.reading_times ?? [])[2] ?? null,
    categories: picked,
    criterion: (state.meta?.criteria ?? []).find((c) => c.id === "bestseller")?.label ?? null,
    subcategories: SUBS.filter((s) => allowed.includes(s)),
    seedBooks: [],
  };
}

/** 취향 설정 7단계를 자동 완주해 스냅샷 1개를 만든다(단계 머신과 같은 이벤트 순서). */
async function runOnboarding(ctx, categories) {
  const { state, log, api, criterionId } = ctx;
  log("preference_started", { payload: { preset: "1" } });
  state.consent = true;
  state.prefs = prefsFor(state, categories);
  const set = await api.getCandidates(state.source, {
    categories: state.prefs.categories, subcategories: state.prefs.subcategories,
    n: 30, userKey: state.userKey,
  });
  if (!set) return;
  state.candidateSet = {
    id: set.candidate_set_id, items: set.items,
    impressions: set.items.map((b) => ({ book_id: b.book_id, position: b.position, selected: false })),
  };
  set.items.forEach((b) => log("impression", {
    book_id: b.book_id, position: b.position, selected: false,
    candidate_set_id: set.candidate_set_id, surface: "onboarding",
  }));
  state.candidateSet.impressions.slice(0, 5).forEach((im) => {
    im.selected = true;
    state.prefs.seedBooks.push(im.book_id);
    log("preference_book_selected", {
      book_id: im.book_id, position: im.position, selected: true,
      candidate_set_id: state.candidateSet.id, surface: "onboarding",
    });
  });
  const res = await api.postPreferences(state.source, {
    user_key: state.userKey, consent: true, reading_time: state.prefs.readingTime,
    categories: state.prefs.categories, criterion: criterionId(),
    subcategories: state.prefs.subcategories, seeds: state.prefs.seedBooks,
    candidate_set_id: state.candidateSet.id, restart: state.resetting,
  });
  if (!res) return;
  state.cell = res.cell;
  state.snapshots.push({
    id: res.preference_snapshot_id, createdAt: res.created_at,
    prefs: { ...state.prefs }, persona: res.persona, cell: res.cell,
  });
  log("preference_completed", {
    candidate_set_id: state.candidateSet.id,
    payload: { seeds: String(state.prefs.seedBooks.length), restart: String(state.resetting) },
  });
}

/** 재설정 유저: 스냅샷 1 → 열람 2건 → 재설정 스냅샷 2. Refresh ≠ Reset 을 눈으로 보여준다. */
async function resetUser(ctx) {
  const { state, log, snap, requestRecommend } = ctx;
  await runOnboarding(ctx, FIRST_CATS);
  await requestRecommend();
  const row = (state.recommend?.rows ?? []).find((r) => (r.items ?? []).length && r.row_id !== "trending");
  (row?.items ?? []).slice(0, 2).forEach((it) =>
    log("reader_open", { book_id: it.book_id, row_id: row.row_id, surface: "preset" }));
  log("preference_restarted", { payload: { from: snap()?.id ?? "none" } });
  state.resetting = true;
  await runOnboarding(ctx, SECOND_CATS);
  state.resetting = false;
}

export async function run(name, ctx) {
  const { state, render, requestRecommend } = ctx;
  if (!PRESET_NAMES.includes(name)) return;
  resetAll(state);
  if (name === "skipUser") state.consent = false;
  if (name === "newUser") await runOnboarding(ctx, FIRST_CATS);
  if (name === "resetUser") await resetUser(ctx);
  // 프리셋은 D8·D7 에서 눌린다 — 이미 #/home 이면 hashchange 가 안 뜨므로 직접 갱신한다
  if (location.hash === "#/home") { await requestRecommend(); render(); }
  else location.hash = "#/home";
}
