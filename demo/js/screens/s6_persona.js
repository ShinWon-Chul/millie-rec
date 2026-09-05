// S6 페르소나 결과. 설명 레이어이며 모델 입력이 아니다 — 문구만 실제 선택값에서 생성된다.
import { esc, josa, navbar } from "./ui.js";

const ART = { "오디세우스": "🏛️", "셜록 홈즈": "🔎", "돈키호테": "🐴", "제인 에어": "🕯️" };

export function render(state) {
  const p = state.snapshots[state.snapshots.length - 1]?.persona;
  if (!p) return `${navbar()}<div class="screen"><div class="screen__body"></div></div>`;
  return `${navbar({ action: { text: "이미지 저장", act: "noop" } })}
  <div class="screen">
    <div class="persona">
      <p class="persona__who">${esc(state.userKey)}님은</p>
      <h1 class="persona__name">${esc(p.name)}</h1>
      <p class="persona__work">《${esc(p.work)}》</p>
      <div class="persona__art">${ART[p.name] || "📖"}</div>
      <p class="persona__quote">“${esc(p.quote)}”</p>
      <p class="persona__desc">${esc(p.description)}</p>
      <button class="persona__cta" data-act="toHome"
        >${esc(p.name)}${esc(josa(p.name, "이", "가"))} 추천하는 책 보기</button>
      <button class="persona__share" data-act="noop">결과 공유하기</button>
    </div>
  </div>`;
}
