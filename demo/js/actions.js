// data-act 딕셔너리 1벌 + 취향 설정 단계 머신(S1~S5). 화면 파일은 data-act 만 찍고 여기로 모인다.
// 정본: 화면 구성 02 §5 UI 행동 → 이벤트 표(contracts.EVENT_TYPES 13종과 1:1).

export function createActions(ctx) {
  const { state, setState, render, log, snap, criterionId, requestRecommend,
    api, presets, VARIANTS, QUALIFIED_READ_MINUTES, toast } = ctx;

  const ORDER = ["S1", "S2", "S3", "S4", "S5"];
  const step = (id) => state.steps.find((s) => s.id === id);
  const subsOf = (cat) => (state.meta?.categories ?? []).find((c) => c.name === cat)?.subcategories ?? [];

  /** 스칼라 필드는 토글, 배열 필드는 max 까지 추가. S2 를 바꾸면 남은 세부 카테고리를 정리한다. */
  function togglePick(stepId, val) {
    const st = step(stepId);
    if (!st) return;
    const cur = state.prefs[st.field];
    if (!Array.isArray(cur)) state.prefs[st.field] = cur === val ? null : val;
    else if (cur.includes(val)) state.prefs[st.field] = cur.filter((v) => v !== val);
    else if (cur.length < st.max) state.prefs[st.field] = [...cur, val];
    if (stepId === "S2") {
      const allowed = state.prefs.categories.flatMap(subsOf);
      state.prefs.subcategories = state.prefs.subcategories.filter((s) => allowed.includes(s));
    }
    log("preference_step", { payload: { step: stepId, field: st.field } });
    render();
  }

  /** S5 진입 시 후보 30권. "미선택 ≠ negative"의 근거가 되는 노출 로그를 함께 남긴다. */
  async function loadCandidates() {
    const res = await api.getCandidates(state.source, {
      categories: state.prefs.categories, subcategories: state.prefs.subcategories,
      n: 30, userKey: state.userKey,
    });
    if (!res) return;
    state.candidateSet = {
      id: res.candidate_set_id, items: res.items,
      impressions: res.items.map((b) => ({ book_id: b.book_id, position: b.position, selected: false })),
    };
    res.items.forEach((b) => log("impression", {
      book_id: b.book_id, position: b.position, selected: false,
      candidate_set_id: res.candidate_set_id, surface: "onboarding",
    }));
  }

  /** 스냅샷은 append only — 재설정도 push 한다(Refresh ≠ Reset). 시드 5권 서재 담기는 서버가 기록한다. */
  async function completeOnboarding() {
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
    state.consent = true;
    log("preference_completed", {
      candidate_set_id: state.candidateSet.id,
      payload: { seeds: String(state.prefs.seedBooks.length), restart: String(state.resetting) },
    });
    setState({ screen: "S6" });
  }

  async function goNext() {
    const i = ORDER.indexOf(state.screen);
    if (state.screen === "S1") state.consent = true;
    if (i === ORDER.length - 1) return completeOnboarding();
    const nextId = ORDER[i + 1];
    if (nextId === "S5") await loadCandidates();
    setState({ screen: nextId });
  }

  function goBack() {
    const i = ORDER.indexOf(state.screen);
    if (i === 0 && state.resetting) { location.hash = "#/home"; return; }
    setState({ screen: i > 0 ? ORDER[i - 1] : "S0" });
  }

  /** 서재 타일은 LibraryBook 3필드뿐이라 ItemOut 형태의 최소 detail 을 만들어 넘긴다. */
  function libraryDetail(bookId) {
    const b = [...state.library.added, ...state.library.reading, ...state.library.completed]
      .find((x) => x.book_id === bookId);
    if (!b) return null;
    return {
      item: {
        book_id: b.book_id, title: b.title ?? null, image_url: b.image_url ?? null,
        authors: null, reason: null, badge: null, source: null, source_channels: [],
        score: 0, position: 0, book_format: null, difficulty: null,
      },
      rowId: "library",
    };
  }

  const ACTIONS = {
    start: () => { log("preference_started"); setState({ screen: "S1" }); },
    skip: () => {
      state.consent = false;
      state.snapshots = [];
      location.hash = "#/home";
    },
    back: () => goBack(),
    pick: (el) => togglePick(el.dataset.step, el.dataset.val),
    pickbook: (el) => {
      const id = Number(el.dataset.book);
      const cur = state.prefs.seedBooks;
      const on = cur.includes(id);
      state.prefs.seedBooks = on ? cur.filter((v) => v !== id) : [...cur, id];
      const imp = state.candidateSet.impressions.find((x) => x.book_id === id);
      if (imp) imp.selected = !on;
      log(on ? "preference_book_deselected" : "preference_book_selected", {
        book_id: id, position: Number(el.dataset.pos), selected: !on,
        candidate_set_id: state.candidateSet.id, surface: "onboarding",
      });
      render();
    },
    next: () => goNext(),
    toHome: () => { state.resetting = false; location.hash = "#/home"; },
    nav: (el) => { location.hash = el.dataset.to; },
    preset: (el) => presets.run(el.dataset.preset, ctx),
    startFresh: () => presets.startFresh(ctx),
    card: (el) => {
      const bookId = Number(el.dataset.book);
      const rowId = el.dataset.row;
      if (rowId === "library") {
        const d = libraryDetail(bookId);
        if (!d) return;
        state.detail = d;
        log("detail_click", { book_id: bookId, surface: "library" });
        location.hash = "#/book/" + bookId;
        return;
      }
      const row = (state.recommend?.rows ?? []).find((r) => r.row_id === rowId);
      const item = (row?.items ?? []).find((i) => i.book_id === bookId);
      if (!item) return;
      log("detail_click", { book_id: item.book_id, row_id: row.row_id, position: item.position });
      state.detail = { item, rowId: row.row_id };
      location.hash = "#/book/" + item.book_id;
    },
    closeSheet: () => { location.hash = "#/home"; },
    read: (el) => { location.hash = "#/reader/" + el.dataset.book; },
    library: (el) => {
      const id = Number(el.dataset.book);
      log("library_add", { book_id: id, surface: "main" });
      const it = state.detail?.item;
      state.library.added.push({ book_id: id, title: it?.title ?? null, image_url: it?.image_url ?? null });
      toast("서재에 담았어요");
    },
    read10: () => {
      const r = state.reading;
      if (!r) return;
      r.progressPct = Math.min(100, r.progressPct + 8);
      r.virtualMinutes += 10;
      if (!r.qualified && r.virtualMinutes >= QUALIFIED_READ_MINUTES) {
        r.qualified = true;
        log("qualified_read", { book_id: r.bookId, payload: { virtual_minutes: String(r.virtualMinutes) } });
      }
      render();
    },
    complete: () => {
      const r = state.reading;
      if (!r) return;
      r.completed = true;
      r.progressPct = 100;
      log("completion", { book_id: r.bookId });
      setState({ modal: "rating" });
    },
    rate: async (el) => {
      const r = state.reading;
      const stars = Number(el.dataset.stars);
      if (!r) return;
      state.ratings[r.bookId] = stars;
      await api.postRating(state.source, {
        rating_id: "rat_" + crypto.randomUUID().replace(/-/g, "").slice(0, 6),
        user_key: state.userKey, book_id: r.bookId, stars,
        ts: new Date().toISOString(),
        recommendation_id: state.recommend?.recommendation_id ?? null,
      });
      log("rating", { book_id: r.bookId, payload: { stars: String(stars) } });
      state.modal = null;
      toast("다음 책을 준비하고 있어요");
      location.hash = "#/home";
    },
    rateLater: () => {
      state.modal = null;
      toast("다음 책을 준비하고 있어요");
      location.hash = "#/home";
    },
    libTab: (el) => setState({ libraryTab: el.dataset.tab }),
    mydata: async () => {
      state.mydata = await api.getUserData(state.source, state.userKey);
      setState({ modal: "mydata" });
    },
    withdraw: () => setState({ modal: "withdraw" }),
    withdrawConfirm: async () => {
      await api.deletePersonalization(state.source, state.userKey);
      Object.assign(state, { consent: false, snapshots: [], recommend: null, modal: null, banner: "비개인화 인기 도서", library: { added: [], reading: [], completed: [] } });
      location.hash = "#/home";
    },
    closeModal: () => setState({ modal: null }),
    model: async (el) => {
      state.model = VARIANTS.includes(el.value) ? el.value : null;
      await requestRecommend();
      render();
    },
    noop: () => {},
  };

  return ACTIONS;
}
