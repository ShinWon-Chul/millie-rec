// S7 메인 화면. 행 구성은 서버(compose)가 정하고 프론트는 비어 있는 행만 숨긴다.
import { badge, cover, esc, icon } from "./ui.js";

const subtitle = (rowId, seedCount) =>
  (rowId === "persona_shelf" ? `회원님이 고른 ${seedCount}권과 비슷한 책` : "");

function tile(item, rowId) {
  return `<button class="tile" data-act="detail" data-book="${item.book_id}"
    data-row="${esc(rowId)}" data-pos="${item.position}">
    ${cover(item, item.format === "PDF" ? '<span class="cover__pdf">PDF</span>' : "")}
    <div class="tile__title">${esc(item.title)}</div>
    <div class="tile__author">${esc(item.authors)}</div>
    ${badge(item.badge)}
    ${item.reason ? `<div class="tile__reason">${esc(item.reason)}</div>` : ""}
  </button>`;
}

function row(r, seedCount) {
  const sub = subtitle(r.row_id, seedCount);
  return `<section class="row">
    <div class="row__head">
      <span class="row__title">${esc(r.title)}</span>
      <span class="row__chev">${icon("chev", 16, 16)}</span>
    </div>
    ${sub ? `<p class="row__sub">${esc(sub)}</p>` : ""}
    <div class="row__strip">${r.items.map((it) => tile(it, r.row_id)).join("")}</div>
  </section>`;
}

export function render(state) {
  const rec = state.recommend;
  const name = state.snapshots[state.snapshots.length - 1]?.persona?.name;
  const hello = name ? `안녕하세요, ${name}님` : "안녕하세요";
  const sub = state.consent === false
    ? "취향을 등록하면 나에게 맞는 책을 추천해 드려요"
    : `${state.prefs.readingTime || "언제든"} 읽기 좋은 책을 모았어요`;
  const rows = (rec?.rows || []).filter((r) => r.items.length);
  const clientFb = rec?.model_version === "static_popular";
  return `<div class="screen">
    <div class="screen__body">
      <div class="home__head">
        <div class="home__hello">${esc(hello)}<small>${esc(sub)}</small></div>
        <button class="profile-chip${state.chipHot ? " is-hot" : ""}" data-act="reset">취향 다시 설정</button>
      </div>
      ${clientFb ? `<p class="fb-note">추천 서버 응답이 없어 정적 인기 목록으로 대체했습니다
        (fallback_level 3 · client). 메인 화면은 깨지지 않습니다.</p>` : ""}
      ${rows.length
        ? rows.map((r) => row(r, state.prefs.seedBooks.length)).join("")
        : '<p class="row__sub">추천을 불러오는 중…</p>'}
      <div style="height:24px"></div>
    </div>
  </div>`;
}
