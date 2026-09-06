// D5 내 서재 #/library — 3버킷 · 스냅샷 타임라인 · U_t 카드 · 열람/재설정/철회.
// 정본: ../.assets/설계서/화면 구성 및 디자인/02_화면구성_v2_8페이지.md §2 D5 · schemas.UserStateOut.
// render(state) → HTML 문자열만. 모달(내 데이터·철회 확인)은 app.js 가 state.modal 로 그린다.
import { cover, esc, navbar, tabbar } from "./ui.js";

const TABS = [
  ["added", "담은 책"],
  ["reading", "읽는 중"],
  ["completed", "완독"],
];
const EMPTY = {
  added: "취향 설정에서 고른 책과 서재에 담은 책이 여기에 모입니다",
  reading: "뷰어에서 읽기 시작한 책이 여기에 모입니다",
  completed: "완독한 책이 여기에 모입니다",
};
// 타임라인 표시용 축약(id → 라벨). 화면 텍스트 정본은 meta.criteria — 있으면 그 label 이 이긴다.
const CRITERION_LABEL = {
  author: "좋아하는 작가",
  publisher: "좋아하는 출판사",
  bestseller: "베스트셀러",
  buzz: "화제작",
  review: "리뷰와 별점",
};

/** 저자 정본은 응답의 LibraryBook.authors — 없을 때만 추천 응답에서 같은 book_id 를 찾는다(D-07b ③). */
function authorOf(state, book) {
  if (book.authors) return book.authors;
  const items = (state.recommend?.rows ?? []).flatMap((r) => r.items ?? []);
  return items.find((i) => i.book_id === book.book_id)?.authors ?? "";
}

/** 서재 타일. 라우팅·중복 제거는 book_id 로만 한다(제목이 같은 다른 책이 카탈로그에 있다). */
function tile(b, state) {
  return `<button class="tile" data-act="card" data-book="${esc(b.book_id)}"
    data-row="library" data-pos="0">
    ${cover(b)}
    <div class="tile__title">${esc(b.title ?? "(제목 없음)")}</div>
    <div class="tile__author">${esc(authorOf(state, b) || "저자 미상")}</div>
  </button>`;
}

function tabs(state) {
  const lib = state.library ?? {};
  const books = lib[state.libraryTab] ?? [];
  const head = TABS.map(([id, label]) =>
    `<button class="lib__tab${state.libraryTab === id ? " is-on" : ""}"
      data-act="libTab" data-tab="${id}">${label} <small>${(lib[id] ?? []).length}</small></button>`
  ).join("");
  const grid = books.length
    ? books.map((b) => tile(b, state)).join("")
    : `<p class="lib__empty">${esc(EMPTY[state.libraryTab] ?? EMPTY.added)}</p>`;
  return `<div class="lib__tabs">${head}</div><div class="lib__grid">${grid}</div>`;
}

function timeline(state) {
  const snaps = state.userState?.snapshots ?? [];
  const label = (id) =>
    state.meta?.criteria?.find((c) => c.id === id)?.label ?? CRITERION_LABEL[id] ?? id ?? "-";
  const when = (ts) => String(ts ?? "").slice(5, 16).replace("T", " ");
  const items = snaps.map((s) => `<li class="timeline__item${s.active ? " is-on" : ""}">
      <span class="timeline__id">${esc(s.snapshot_id)}</span>
      <span class="timeline__t">${esc(when(s.created_at))}</span>
      <span class="timeline__cats">${esc((s.categories ?? []).join(", "))} / ${esc(label(s.criterion))}</span>
    </li>`).join("");
  return `<section class="lib__sec">
    <h2>취향 히스토리</h2>
    ${snaps.length
      ? `<ol class="timeline">${items}</ol>`
      : `<p class="lib__empty">아직 취향 설정이 없습니다</p>`}
    <p class="lib__hint">재설정해도 독서 기록은 유지됩니다</p>
  </section>`;
}

function utCard(state) {
  const w = state.userState?.user_state_weights ?? {};
  const bar = (k, v, note) => `<div class="ut__row">
      <span class="ut__k">${k}</span>
      <span class="ut__track"><span class="ut__fill" style="width:${Math.round((Number(v) || 0) * 100)}%"></span></span>
      <span class="ut__v">${(Number(v) || 0).toFixed(2)}</span>
      <span class="ut__n">${esc(note)}</span>
    </div>`;
  return `<section class="lib__sec">
    <h2>U_t 가중치</h2>
    ${bar("α", w.alpha, "explicit (온보딩 선택)")}
    ${bar("β", w.beta, "long-term (독서 기록)")}
    ${bar("γ", w.gamma, "session (현재 세션)")}
    <p class="lib__hint">완독이 쌓일수록 행동(β) 비중이 커집니다</p>
  </section>`;
}

export function render(state) {
  return `${navbar({ back: false, label: "내 서재" })}
  <div class="screen">
    <div class="screen__body">
      ${state.consent === false
        ? `<p class="lib__banner">맞춤 추천 동의가 없어 비개인화 인기 도서만 보입니다</p>`
        : ""}
      ${tabs(state)}
      ${timeline(state)}
      ${utCard(state)}
      <div class="lib__actions">
        <button class="cta is-on" data-act="nav" data-to="#/refresh">취향 다시 설정</button>
        <button class="sheet__ghost" data-act="mydata">내 데이터 보기</button>
        <button class="lib__danger" data-act="withdraw"${state.consent === false ? " disabled" : ""}>맞춤 추천 동의 철회</button>
      </div>
      <div class="lib__tail"></div>
    </div>
    ${tabbar("library")}
  </div>`;
}
