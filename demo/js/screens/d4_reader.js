// D4 뷰어 시뮬레이션 #/reader/:id — 본문 없는 "독서 행동 이벤트 생성 장치"(데모 전용).
// 정본: ../.assets/설계서/화면 구성 및 디자인/02_화면구성_v2_8페이지.md §2 D4 · §3 RatingModal.
// render(state) → HTML 문자열만. 이벤트 처리는 actions.js 가 data-act 로 위임받는다.
import { cover, demoLabel, esc, icon, modal } from "./ui.js";

const QUALIFIED_READ_MINUTES = 15; // contracts.QUALIFIED_READ_MINUTES 와 같은 값 — 데모 상수
const IDLE = { progressPct: 0, virtualMinutes: 0, qualified: false, completed: false };

/** 읽는 책의 카드 정보. 같은 제목 다른 책이 있으므로 book_id 로만 찾는다(06-CONTEXT D-07b ③). */
function book(state) {
  const id = state.reading?.bookId;
  const opened = state.detail?.item;   // D3 를 거쳐 왔으면 카드 정보가 이미 있다
  if (opened && opened.book_id === id) return opened;
  const items = (state.recommend?.rows ?? []).flatMap((r) => r.items ?? []);
  return items.find((i) => i.book_id === id)
    ?? { book_id: id, title: null, authors: null, image_url: null };
}

function status(r) {
  if (r.completed) return "완독 (completion)";
  return r.qualified ? "유효 독서 중 (qualified_read 기록됨)" : "열람 (reader_open)";
}

/** 1탭 별점 — 자유 입력 없이 버튼 5개만(별점 값 조작 표면 최소화). */
function ratingModal() {
  const stars = [1, 2, 3, 4, 5].map((s) =>
    `<button class="rating__star" data-act="rate" data-stars="${s}" aria-label="${s}점">★</button>`
  ).join("");
  return modal(`<h3 class="rating__title">어떠셨나요?</h3>
    <div class="rating__stars">${stars}</div>
    <button class="rating__later" data-act="rateLater">나중에</button>
    <p class="rating__note">1탭 즉시 전송 · 라벨은 별점 원본, 리워드는 UX 제안만</p>`);
}

export function render(state) {
  const r = { ...IDLE, ...(state.reading ?? {}) };
  const b = book(state);
  const title = b.title ?? "(제목 없음)";
  const pct = Math.max(0, Math.min(100, Number(r.progressPct) || 0));
  const minutes = Number(r.virtualMinutes) || 0;
  return `${demoLabel("데모 전용 · 실제 뷰어 아님")}
  <div class="navbar">
    <button class="navbar__back" data-act="nav" data-to="#/home">${icon("back", 20, 23)}</button>
    <span class="navbar__label">${esc(title)}</span>
    <span></span>
  </div>
  <div class="screen reader">
    <div class="progress"><div class="progress__fill" style="width:${pct}%"></div></div>
    <div class="screen__body">
      <div class="reader__head">
        ${cover(b)}
        <div class="reader__meta">
          <h1 class="reader__title">${esc(title)}</h1>
          <p class="reader__author">${esc(b.authors ?? "저자 미상")}</p>
          <p class="reader__pct">진행률 ${pct}%</p>
        </div>
      </div>
      <div class="reader__paper"><p>아래 버튼으로 독서를 시뮬레이션합니다</p></div>
      <dl class="reader__sim">
        <dt>가상 독서 시간</dt>
        <dd>${minutes}분</dd>
        <dt>Qualified Reading Start</dt>
        <dd>${r.qualified ? "도달 ✓" : `T=${QUALIFIED_READ_MINUTES}분 도달 시 qualified_read 1회`}</dd>
        <dt>상태</dt>
        <dd>${esc(status(r))}</dd>
      </dl>
      <p class="reader__note">T=15분은 데모 상수, production은 로그 분포로 보정 (main 설계서 §4)</p>
    </div>
    <div class="screen__foot reader__actions">
      <button class="cta is-on" data-act="read10"${r.completed ? " disabled" : ""}>10분 읽기 <small>+8% · +10분</small></button>
      <button class="sheet__ghost" data-act="complete"${r.completed ? " disabled" : ""}>완독</button>
    </div>
  </div>
  ${state.modal === "rating" ? ratingModal() : ""}`;
}
