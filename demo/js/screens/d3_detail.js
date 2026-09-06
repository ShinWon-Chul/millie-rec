// D3 책 상세(#/book/:id). D2 위에 겹쳐 그리는 바텀시트라 배경 화면은 그대로 남는다.
// 평점 숫자는 ItemOut 에 없다 — 대중 평가는 review 배지 문구가 대신한다.
import { badge, cover, esc } from "./ui.js";
import { render as home, dots } from "./d2_home.js";

// 후보 통로 문구. co-read 계열 표현은 데이터가 없어 쓰지 않는다(../.claude/rules/data.md).
// 서비스 화면에는 "(협업 필터링 아님)" 같은 부정형 단서를 두지 않는다(사용자 결정 2026-09-06).
// 방법 고지는 쇼케이스 데이터 고지 절이 맡는다 — 통로 이름 자체가 이미 co-read 를 주장하지 않는다.
const CHANNEL_TEXT = {
  content: "콘텐츠 유사도 이웃 — 제목·소개 TF-IDF",
  popularity: "지금 많이 읽는 책 — 인기 순위(pop_rank) 기반",
};

// 세부 분류(밀리 3depth) — 이름만 나열하면 무엇인지 알 수 없어 라벨을 앞에 둔다. 시트가 좁아 3개까지.
const SUBCATS_LABEL = "세부 분류", SUBCATS_MAX = 3;

const FIT = (d) => (d < 0.34 ? "가볍게" : d < 0.67 ? "비슷한 수준" : "조금 도전적");

// 커버리지 42.6% — 비어 있으면 요소 자체를 그리지 않는다(빈 줄·구분점만 남는 자리 금지).
// 취향 설정에서 고른 분류를 앞으로 보내 강조한다 — 3개 상한에 잘려 안 보이는 것을 막고,
// 가점이 어디서 왔는지가 화면에서 읽힌다(가점 자체는 ranking/hybrid.py 가 준다).
function subcatsLine(it, picks) {
  const all = it.subcategories ?? [];
  if (!all.length) return "";
  const want = new Set(picks ?? []);
  const ordered = [...all.filter((s) => want.has(s)), ...all.filter((s) => !want.has(s))];
  const shown = ordered.slice(0, SUBCATS_MAX)
    .map((s) => (want.has(s) ? `<b>${esc(s)}</b>` : esc(s))).join(" · ");
  const more = all.length > SUBCATS_MAX ? ` +${all.length - SUBCATS_MAX}` : "";
  return `<p class="sheet__subcats">${SUBCATS_LABEL} · ${shown}${more}</p>`;
}

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
          ${subcatsLine(it, state.prefs?.subcategories)}
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
