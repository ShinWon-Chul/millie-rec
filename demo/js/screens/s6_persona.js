// S6 페르소나 결과. 설명 레이어이며 모델 입력이 아니다 — 문구만 실제 선택값에서 생성된다.
import { esc, josa, navbar } from "./ui.js";

export function render(state) {
  const p = state.snapshots[state.snapshots.length - 1]?.persona;
  if (!p) return `${navbar()}<div class="screen"><div class="screen__body"></div></div>`;
  // D6(취향 재설정) 완료 화면에서는 CTA 문구가 바뀐다(화면 구성 02 §2 D6)
  const cta = state.resetting
    ? "새 취향으로 추천 받기"
    : `${p.name}${josa(p.name, "이", "가")} 추천하는 책 보기`;
  return `${navbar({ action: { text: "이미지 저장", act: "noop" } })}
  <div class="screen">
    <div class="persona">
      <p class="persona__who">회원님은</p>
      <h1 class="persona__name">${esc(p.name)}</h1>
      <p class="persona__work">《${esc(p.work)}》</p>
      <div class="persona__art">${esc(String(p.name ?? "").slice(0, 1))}</div>
      <p class="persona__quote">“${esc(p.quote)}”</p>
      <p class="persona__desc">${esc(p.description)}</p>
      <button class="persona__cta" data-act="toHome"
        >${esc(cta)}</button>
      <button class="persona__share" data-act="noop">결과 공유하기</button>
    </div>
  </div>`;
}
