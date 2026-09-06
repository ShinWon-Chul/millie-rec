// S1~S5 공용 렌더러. 단계가 늘어도 코드는 1벌 — 차이는 config/onboarding.json이 만든다.
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

/** OnboardingMeta.categories[] = {name, supported, subcategories} — 세부 카테고리는 여기서만 나온다. */
function subsOf(meta, cat) {
  return (meta?.categories ?? []).find((c) => c.name === cat)?.subcategories ?? [];
}

function chipGroups(state, step, meta) {
  const sel = picked(state, step);
  const full = sel.length >= step.max;
  const cats = state.prefs.categories;
  if (!cats.length) {
    return `<p class="step__counter">먼저 카테고리를 선택해 주세요.</p>`;
  }
  // 밀리 공개 도서 페이지는 대분류만 노출한다. 세부 분류가 없는 카테고리를 숨기면 고른 사람이
  // "내 선택이 빠졌다"고 느낀다 — 전부 보여주고, 없는 것은 없다고 말한다(S4 는 min 0 이라 넘어갈 수 있다).
  const anySubs = cats.some((c) => subsOf(meta, c).length);
  const note = anySubs ? "" :
    `<p class="step__counter">선택하신 카테고리는 세부 분류가 없어요. 카테고리 전체로 추천합니다.</p>`;
  return note + cats.map((cat) => {
    const subs = subsOf(meta, cat);
    const body = subs.length
      ? `<div class="chips">${subs.map((s) => {
          const on = sel.includes(s);
          return `<button class="chip${on ? " is-on" : ""}" data-act="pick"
            data-step="${esc(step.id)}" data-val="${esc(s)}"${full && !on ? " disabled" : ""}
            >${esc(s)}</button>`;
        }).join("")}</div>`
      : `<p class="group__none">세부 분류 없음, 카테고리 전체로 추천합니다</p>`;
    return `<section class="group"><h2 class="group__title">${esc(cat)}</h2>${body}</section>`;
  }).join("");
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
        ${["오디오북", "챗북"].includes(b.book_format) ? `<span class="cover__pdf">${esc(b.book_format)}</span>` : ""}`)}
      <div class="book__title">${esc(b.title ?? "(제목 없음)")}</div>
      <div class="book__author">${esc(b.authors)}</div>
    </button>`;
  }).join("")}</div>`;
}

/** 고른 작가 칩. × 도 같은 pick 이라 다시 누르면 토글로 해제된다. */
function authorPicks(state, step) {
  const sel = picked(state, step);
  if (!sel.length) return "";
  return `<div class="picks">${sel.map((name) => `<button class="pick" data-act="pick"
    data-step="${esc(step.id)}" data-val="${esc(name)}"
    >${esc(name)}<span class="pick__x">\u00d7</span></button>`).join("")}</div>`;
}

/** 작가 목록(S3A). 서버가 가나다 순으로 주므로 정렬 방식은 하나뿐 — 토글 버튼 대신 상태만 적는다. */
function authorList(state, step) {
  const sel = picked(state, step);
  const items = state.authorSet.items;
  if (!items.length) return `<p class="step__counter">작가를 불러오는 중…</p>`;
  return `<div class="authors">${items.map((a) => {
    const on = sel.includes(a.name);
    return `<button class="author${on ? " is-on" : ""}" data-act="pick"
      data-step="${esc(step.id)}" data-val="${esc(a.name)}">
      ${cover({ title: a.title, image_url: a.image_url })}
      <span class="author__body">
        <span class="author__name">${esc(a.name)}</span>
        <span class="author__book">${esc(a.title || "-")}</span>
      </span>
      <span class="author__check">${on ? icon("check", 17, 16) : ""}</span>
    </button>`;
  }).join("")}</div>`;
}

export function render(state, step, meta) {
  const sel = picked(state, step);
  const authors = step.layout === "author-list";
  const body = step.layout === "chips-grouped" ? chipGroups(state, step, meta)
    : step.layout === "book-grid3" ? bookGrid(state, step)
    : authors ? authorList(state, step)
    : optionList(state, step, meta);
  // 정렬 방식이 하나뿐이라 버튼이 아니라 상태 표시다(누르면 아무 일도 안 하는 버튼보다 정직하다)
  const sort = authors ? `<span class="step__sort">가나다 순</span>` : "";
  const counter = step.counter
    ? `<p class="step__counter">${esc(step.counter.replace("{n}", sel.length))}${sort}</p>` : "";
  const notice = step.consentNotice ? `<div class="notice">
    <span class="notice__icon">${icon("info", 18, 18)}</span>
    <span>맞춤형 서비스 제공을 위해 정보를 수집활용합니다. 동의하시면 아래 버튼을 눌러주세요</span>
    <span class="notice__chev">${icon("chev", 18, 18)}</span>
  </div>` : "";
  // S2 는 진행바가 없다(캡처 실측 — config/onboarding.json 의 progress: null)
  const bar = step.progress == null ? ""
    : `<div class="progress"><div class="progress__fill" style="width:${step.progress * 100}%"></div></div>`;
  const ctaText = state.resetting && step.id === "S5" ? "새 취향으로 추천 받기" : step.cta;
  return `${navbar({ label: state.resetting ? "취향 다시 설정" : "" })}
  ${bar}
  <div class="screen" data-layout="${esc(step.layout)}">
    <div class="screen__body">
      <h1 class="step__title">${esc(step.title)}</h1>
      ${authors ? authorPicks(state, step) : ""}${counter}${body}${notice}
    </div>
    <div class="screen__foot">${cta(ctaText, sel.length >= step.min, "next")}</div>
  </div>`;
}
