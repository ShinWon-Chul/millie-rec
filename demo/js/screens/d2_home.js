// D2 메인 화면(#/home). 행 구성·행 제목·부제는 서버(compose)가 정하고 프론트는 빈 행만 숨긴다.
// 배너는 app.js 가 폰 셸에 그린다(06-02 인계 2) — 여기서 또 그리면 두 번 보인다.
import { badge, cover, esc, icon, tabbar } from "./ui.js";

const FMT_PILL = ["오디오북", "챗북"];   // 전자책은 pill 없음(book_format 3값)

/** 난이도 3분위 점(Should). 완독지수 결측(difficulty=null)이면 아무것도 그리지 않는다. */
export const dots = (d) =>
  (d == null
    ? ""
    : `<span class="dots" title="난이도 ${esc(Number(d).toFixed(2))}">${[1, 2, 3]
        .map((i) => `<i class="${d >= (i - 0.5) / 3 ? "is-on" : ""}"></i>`).join("")}</span>`);

/** 카드 1장. 동일성·라우팅은 book_id 로만 한다 — 같은 제목 다른 책이 있다(06-CONTEXT D-07b ③). */
function tile(item, rowId) {
  const fmt = FMT_PILL.includes(item.book_format)
    ? `<span class="tile__fmt">${esc(item.book_format)}</span>`
    : "";
  return `<button class="tile" data-act="card" data-book="${esc(item.book_id)}"
    data-row="${esc(rowId)}" data-pos="${esc(item.position ?? 0)}">
    ${cover(item, fmt)}
    <div class="tile__title">${esc(item.title ?? "(제목 없음)")}</div>
    <div class="tile__author">${esc(item.authors ?? "저자 미상")}</div>
    ${badge(item.badge)}${dots(item.difficulty)}
    ${item.reason ? `<div class="tile__reason">${esc(item.reason)}</div>` : ""}
  </button>`;
}

function row(r) {
  return `<section class="row" data-row="${esc(r.row_id)}">
    <div class="row__head">
      <span class="row__title">${esc(r.title)}</span>
      <span class="row__chev">${icon("chev", 16, 16)}</span>
    </div>
    ${r.subtitle ? `<p class="row__sub">${esc(r.subtitle)}</p>` : ""}
    <div class="row__strip">${(r.items ?? []).map((it) => tile(it, r.row_id)).join("")}</div>
  </section>`;
}

export function render(state) {
  const rec = state.recommend;
  const name = state.snapshots[state.snapshots.length - 1]?.persona?.name ?? "회원";
  const ctx = String(state.prefs.readingTime ?? rec?.context ?? "").split(",")[0];
  const anon = state.consent === false;
  const hello = anon ? "지금 많이 읽는 책을 모았어요" : `${name}님, ${ctx || "오늘"} 독서 어때요?`;
  const sub = anon
    ? "취향을 등록하면 나에게 맞는 책을 추천해 드려요"
    : (state.prefs.readingTime ?? "");
  // 빈 continue_reading 은 숨긴다 — 서버·mock 모두 빈 행을 그대로 내려보낸다(06-03 인계)
  const rows = (rec?.rows ?? []).filter((r) => (r.items ?? []).length);
  return `<div class="screen">
    <div class="screen__body">
      <div class="home__head">
        <img class="home__mark" src="assets/brand/millie-mark.png" alt="밀리의서재" width="24" height="24">
        <div class="home__hello">${esc(hello)}<small>${esc(sub)}</small></div>
        <button class="profile-chip" data-act="nav" data-to="#/library">내 서재</button>
      </div>
      ${rec?.cell
        ? `<span class="cell-chip">cell ${esc(rec.cell)}${rec.forced ? ", forced" : ""}, 데모 표시용</span>`
        : ""}
      ${rows.length
        ? rows.map(row).join("")
        : `<p class="row__sub">${rec ? "추천 행이 비어 있습니다" : "추천을 불러오는 중…"}</p>`}
      <div style="height:24px"></div>
    </div>
    ${tabbar("home")}
  </div>`;
}
