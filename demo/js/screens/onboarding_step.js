// S1~S5 공용 렌더러. 단계가 5개여도 코드는 1벌 — 차이는 config/onboarding.json이 만든다.
import { cover, cta, esc, icon, navbar } from "./ui.js";

/** 현재 단계에서 선택된 값 (스칼라 필드는 배열로 감싸 한 갈래로 처리) */
export function picked(state, step) {
  const v = state.prefs[step.field];
  return Array.isArray(v) ? v : v == null ? [] : [v];
}

function option(label, on, off, step) {
  return `<button class="option${on ? " is-on" : ""}${off ? " is-off" : ""}"
    data-act="pick" data-step="${esc(step.id)}" data-val="${esc(label)}"${off ? " disabled" : ""}
    >${esc(label)}${on ? `<span class="option__check">${icon("check", 17, 16)}</span>` : ""}</button>`;
}

function optionList(state, step, meta) {
  const sel = picked(state, step);
  const opts = step.optionsFrom === "meta.categories"
    ? meta.categories
    : step.options.map((name) => ({ name, supported: true }));
  const full = sel.length >= step.max;
  const cls = step.layout === "grid2" ? "step__grid" : "step__list";
  return `<div class="${cls}">${opts.map((o) => {
    const on = sel.includes(o.name);
    // 미지원 카테고리(§8 "대응 태그 없음")와 최대 선택 초과는 같은 비활성 스타일로 묶는다
    return option(o.name, on, !o.supported || (full && !on && step.max > 1), step);
  }).join("")}</div>`;
}

function chipGroups(state, step, meta) {
  const sel = picked(state, step);
  const full = sel.length >= step.max;
  const cats = state.prefs.categories.filter((c) => (meta.subcategories[c] || []).length);
  if (!cats.length) {
    return `<p class="step__counter">먼저 카테고리를 선택해 주세요.</p>`;
  }
  return cats.map((cat) => `<section class="group">
    <h2 class="group__title">${esc(cat)}</h2>
    <div class="chips">${meta.subcategories[cat].map((s) => {
      const on = sel.includes(s);
      return `<button class="chip${on ? " is-on" : ""}" data-act="pick"
        data-step="${esc(step.id)}" data-val="${esc(s)}"${full && !on ? " disabled" : ""}
        >${esc(s)}</button>`;
    }).join("")}</div>
  </section>`).join("");
}

function bookGrid(state, step) {
  const sel = picked(state, step);
  const items = state.candidateSet.items;
  if (!items.length) return `<p class="step__counter">후보를 불러오는 중…</p>`;
  return `<div class="books">${items.map((b) => {
    const on = sel.includes(b.book_id);
    return `<button class="book${on ? " is-on" : ""}" data-act="pickbook"
      data-book="${b.book_id}" data-pos="${b.position}">
      ${cover(b, `<span class="cover__check">${icon("check", 15, 14)}</span>
        ${b.format === "PDF" ? '<span class="cover__pdf">PDF</span>' : ""}`)}
      <div class="book__title">${esc(b.title)}</div>
      <div class="book__author">${esc(b.authors)}</div>
    </button>`;
  }).join("")}</div>`;
}

export function render(state, step, meta) {
  const sel = picked(state, step);
  const body = step.layout === "chips-grouped" ? chipGroups(state, step, meta)
    : step.layout === "book-grid3" ? bookGrid(state, step)
    : optionList(state, step, meta);
  const counter = step.counter
    ? `<p class="step__counter">${esc(step.counter.replace("{n}", sel.length))}</p>` : "";
  const notice = step.consentNotice ? `<div class="notice">
    <span class="notice__icon">${icon("info", 18, 18)}</span>
    <span>맞춤형 서비스 제공을 위해 정보를 수집활용합니다. 동의하시면 아래 버튼을 눌러주세요</span>
    <span class="notice__chev">${icon("chev", 18, 18)}</span>
  </div>` : "";
  return `${navbar({ label: state.resetting ? "취향 다시 설정" : "" })}
  <div class="progress"><div class="progress__fill" style="width:${step.progress * 100}%"></div></div>
  <div class="screen">
    <div class="screen__body">
      <h1 class="step__title">${esc(step.title)}</h1>
      ${counter}${body}${notice}
    </div>
    <div class="screen__foot">${cta(step.cta, sel.length >= step.min, "next")}</div>
  </div>`;
}
