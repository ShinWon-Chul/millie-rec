// S0 시작 화면. 밀리 3D 캐릭터는 자사 에셋이라 이모지로 대체한다.
import { navbar } from "./ui.js";

export function render(state) {   // 인자는 쓰지 않지만 화면 파일 규약(render(state))을 맞춘다
  return `${navbar({ back: false, action: { text: "건너뛰기", act: "skip" } })}
  <div class="screen">
    <div class="screen__body start">
      <h1 class="start__title">나와 비슷한 책 속의<br>주인공을 찾아볼까요?</h1>
      <div class="start__art"><span>🧝</span><span>👩‍🦱</span></div>
    </div>
    <div class="screen__foot">
      <button class="cta is-light" data-act="start">지금 시작하기</button>
    </div>
  </div>`;
}
