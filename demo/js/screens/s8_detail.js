// S8 책 상세 바텀시트. S7 위에 겹쳐 그려지므로 배경 화면은 그대로 남는다.
import { badge, cover, esc } from "./ui.js";
import { render as home } from "./s7_home.js";

export function render(state) {
  const d = state.detail;
  if (!d) return home(state);
  return `${home(state)}
  <div class="sheet-wrap">
    <div class="sheet-wrap__dim" data-act="closeSheet"></div>
    <div class="sheet">
      <div class="sheet__grip"></div>
      <div class="sheet__top">
        <div class="sheet__cover">${cover(d.item)}</div>
        <div class="sheet__meta">
          <h2 class="sheet__title">${esc(d.item.title)}</h2>
          <p class="sheet__author">${esc(d.item.authors)}</p>
          ${badge(d.item.badge)}
        </div>
      </div>
      ${d.item.reason ? `<p class="sheet__reason">${esc(d.item.reason)}</p>` : ""}
      <div class="sheet__actions">
        <button class="cta is-on" data-act="read">바로 읽기</button>
        <button class="sheet__ghost" data-act="library">서재 담기</button>
      </div>
      <button class="sheet__finish" data-act="complete">완독 처리 (데모용)</button>
    </div>
  </div>`;
}
