// D3 책 상세(#/book/:id). D2 위에 겹쳐 그리는 바텀시트라 배경 화면은 그대로 남는다.
// 평점 숫자는 ItemOut 에 없다 — 대중 평가는 review 배지 문구가 대신한다.
import { badge, cover, esc } from "./ui.js";
import { render as home, dots } from "./d2_home.js";

// 후보 통로 문구. co-read 계열 표현은 데이터가 없어 쓰지 않는다(../.claude/rules/data.md).
const CHANNEL_TEXT = {
  content: "콘텐츠 유사도 이웃 — 제목·소개 TF-IDF(협업 필터링 아님)",
  popularity: "지금 많이 읽는 책 — 인기 순위(pop_rank) 기반",
};

const FIT = (d) => (d < 0.34 ? "가볍게" : d < 0.67 ? "비슷한 수준" : "조금 도전적");

function fitLine(it) {
  return it.difficulty == null
    ? `<p class="sheet__fit">난이도 적합도 — 완독지수 없음 · 카테고리 평균 기준</p>`
    : `<p class="sheet__fit">난이도 적합도 ${dots(it.difficulty)} ${esc(FIT(it.difficulty))}</p>`;
}

export function render(state) {
  const d = state.detail;
  if (!d) return home(state);
  const it = d.item;
  const ch = (it.source_channels ?? []).map((c) => CHANNEL_TEXT[c] ?? c).join(" · ");
  const where = d.rowId === "library" ? "내 서재" : (d.rowId ?? "");
  return `${home(state)}
  <div class="sheet-wrap">
    <div class="sheet-wrap__dim" data-act="closeSheet"></div>
    <div class="sheet">
      <div class="sheet__grip"></div>
      <div class="sheet__top">
        <div class="sheet__cover">${cover(it)}</div>
        <div class="sheet__meta">
          <h2 class="sheet__title">${esc(it.title ?? "(제목 없음)")}</h2>
          <p class="sheet__author">${esc(it.authors ?? "저자 미상")}</p>
          <small>${esc(it.book_format ?? "")}${it.book_format && where ? " · " : ""}${esc(where)}</small>
          ${badge(it.badge)}${dots(it.difficulty)}
        </div>
      </div>
      ${it.reason ? `<p class="sheet__reason">${esc(it.reason)}</p>` : ""}
      ${ch ? `<p class="sheet__channels">${esc(ch)}</p>` : ""}
      ${fitLine(it)}
      <div class="sheet__actions">
        <button class="cta is-on" data-act="read" data-book="${esc(it.book_id)}">바로 읽기</button>
        <button class="sheet__ghost" data-act="library" data-book="${esc(it.book_id)}">서재 담기</button>
      </div>
      <button class="sheet__disabled" disabled
        title="production roadmap — 선호 교정 루프">이 책 추천하지 않기</button>
    </div>
  </div>`;
}
