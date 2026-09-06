// 화면 파일들이 공유하는 순수 함수: 이스케이프 · 표지 마크업 · 인라인 SVG · 한글 조사
// (화면 파일 한 개당 250줄 상한을 지키려고 공통부를 분리했다)

export function esc(v) {
  return String(v ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

/** 제목 해시 → 색상. 표지 링크가 죽어도 그리드가 비지 않게 하는 플레이스홀더용. */
function hue(text) {
  let h = 0;
  for (const ch of String(text)) h = (h * 31 + ch.codePointAt(0)) % 360;
  return h;
}

/** 표지 1장. img가 로드 실패하면 스스로 제거되고 CSS ::before의 첫 글자가 드러난다. */
export function cover(book, inner = "") {
  const ch = String(book.title || "?").trim().charAt(0).toUpperCase();
  return `<div class="cover" data-ch="${esc(ch)}" style="--ph:hsl(${hue(book.title)} 30% 33%)"
    ><img src="${esc(book.image_url)}" alt="" loading="lazy" referrerpolicy="no-referrer"
      onerror="this.remove()">${inner}</div>`;
}

export function badge(b) {
  if (!b) return "";
  return `<span class="badge" data-type="${esc(b.type)}">${esc(b.text)}</span>`;
}

/** 받침 유무로 조사 선택. 한글 음절이 아니면 받침 없음으로 취급한다. */
export function josa(word, withFinal, without) {
  const s = String(word ?? "");
  if (!s) return without;
  const code = s.codePointAt(s.length - 1);
  const final = code >= 0xac00 && code <= 0xd7a3 ? (code - 0xac00) % 28 : 0;
  if (final === 8 && without === "로") return without; // ㄹ 받침은 '으로'가 아니라 '로'
  return final ? withFinal : without;
}

const SVG = {
  back: '<path d="M14 4 6.5 11.5 14 19" stroke="currentColor" stroke-width="2.2" fill="none" stroke-linecap="round" stroke-linejoin="round"/>',
  chev: '<path d="M7 4l5 5-5 5" stroke="currentColor" stroke-width="1.8" fill="none" stroke-linecap="round" stroke-linejoin="round"/>',
  check: '<path d="M3 8.5 6.8 12 14 4" stroke="currentColor" stroke-width="2.2" fill="none" stroke-linecap="round" stroke-linejoin="round"/>',
  info: '<circle cx="9" cy="9" r="8" fill="#8E8E93"/><path d="M9 4.6v5.2" stroke="#17181A" stroke-width="1.8" stroke-linecap="round"/><circle cx="9" cy="12.9" r="1.05" fill="#17181A"/>',
  signal: '<rect x="0" y="7.5" width="2.6" height="3" rx="0.7" fill="currentColor"/><rect x="4" y="5.2" width="2.6" height="5.3" rx="0.7" fill="currentColor"/><rect x="8" y="2.6" width="2.6" height="7.9" rx="0.7" fill="currentColor" opacity=".35"/><rect x="12" y="0" width="2.6" height="10.5" rx="0.7" fill="currentColor" opacity=".35"/>',
  wifi: '<path d="M1 3.4a10.5 10.5 0 0 1 13 0" stroke="currentColor" stroke-width="1.7" fill="none" stroke-linecap="round"/><path d="M3.6 6.4a6.7 6.7 0 0 1 7.8 0" stroke="currentColor" stroke-width="1.7" fill="none" stroke-linecap="round"/><circle cx="7.5" cy="9.6" r="1.5" fill="currentColor"/>',
  battery: '<rect x="0.6" y="0.6" width="21" height="10.8" rx="3" stroke="currentColor" stroke-opacity=".4" fill="none"/><rect x="2.2" y="2.2" width="17" height="7.6" rx="1.8" fill="#34C759"/><path d="M23 4.2v3.6a2 2 0 0 0 0-3.6z" fill="currentColor" fill-opacity=".4"/><path d="M11.4 3.1 8.2 7h2.2l-.6 2.6L13.4 5.6h-2.3z" fill="#0B2B12"/>',
};

export function icon(name, w, h, cls = "") {
  return `<svg class="${cls}" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}"
    fill="none" aria-hidden="true">${SVG[name]}</svg>`;
}

/** 상태바 — 캡처와 같은 고정 시각 23:36 (데모 스크린샷 일관성용). */
export function statusbar() {
  return `<div class="statusbar">
    <span class="statusbar__time">23:36</span>
    <span class="statusbar__icons">${icon("signal", 15, 11)}${icon("wifi", 15, 11)}${icon("battery", 24, 12)}</span>
  </div>`;
}

export function navbar({ back = true, action = "", label = "" } = {}) {
  return `<div class="navbar">
    <span>${back ? `<button class="navbar__back" data-act="back">${icon("back", 20, 23)}</button>` : ""}</span>
    ${label ? `<span class="navbar__label">${esc(label)}</span>` : ""}
    <span>${action ? `<button class="navbar__action" data-act="${esc(action.act)}">${esc(action.text)}</button>` : ""}</span>
  </div>`;
}

export function cta(text, on, act) {
  return `<button class="cta${on ? " is-on" : ""}" data-act="${esc(act)}"${on ? "" : " disabled"}>${esc(text)}</button>`;
}

/** 하단 탭바 — 홈·서재 2개만(화면 구성 02 §3 공통 컴포넌트 표). D4 뷰어는 전체화면이라 쓰지 않는다. */
export function tabbar(active) {
  const tab = (id, to, label) =>
    `<button class="tabbar__tab${active === id ? " is-on" : ""}" data-act="nav" data-to="${to}">${label}</button>`;
  return `<nav class="tabbar">${tab("home", "#/home", "홈")}${tab("library", "#/library", "서재")}</nav>`;
}

/** 밀리 앱에 없는 화면(D4·D7·D8)에 붙이는 24px 고지 띠. */
export const demoLabel = (text = "데모 전용 · 실제 밀리 화면 아님") =>
  `<div class="demo-label">${esc(text)}</div>`;

export const banner = (text) => (text ? `<div class="banner">${esc(text)}</div>` : "");

/** inner 는 호출자가 이미 esc() 한 마크업만 넘긴다(원문 문자열 금지 — XSS). */
export const modal = (inner) =>
  `<div class="modal-wrap"><div class="modal-wrap__dim" data-act="closeModal"></div><div class="modal">${inner}</div></div>`;
