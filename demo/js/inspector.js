// 우측 인스펙터 — 폰 화면 옆에서 "그 순간 시스템이 받는 신호"를 보여주는 6개 섹션.
// 신호 해석 문구는 화면설계 문서 §4-1 표의 인스펙터 열을 그대로 옮긴 것이다.
import { esc } from "./screens/ui.js";

const BUDGET_MS = 200;
const MODELS = [["pop", "Pop"], ["cf", "CF"], ["hybrid", "Hybrid"], ["hybrid_div", "+Diversity"]];

const SIGNALS = {
  S0: { type: "—", read: "건너뛰기 시 consent=absent → fallback: diverse popular (§7 개인정보 graceful degradation)" },
  S1: { type: "Context prior(맥락 사전 정보)", read: "장르 규칙 금지, ranker의 context×format 피처", extra: "consent=granted" },
  S2: { type: "Broad taste prior", read: "후보 생성 필터/부스팅 채널" },
  S3: { type: "Selection-policy preference", read: "랭킹 피처 가중 + 노출 배지 타입 결정 (Netflix Artwork Personalization)" },
  S4: { type: "Fine-grained taste prior", read: "prior 정밀화" },
  S5: { type: "Strong explicit positive seeds", read: "노출 로그 테이블 실시간 누적 candidate_set_id / book_id / position / selected → \"미선택 ≠ negative\"", extra: "library_add(source=onboarding) 이벤트" },
  S6: { type: "UX layer — 모델 입력 아님", read: "설명 문구가 실제 explicit state에서 생성됨을 표시 (밀리 현행은 고정 템플릿으로 보임 → 개선점)" },
  S7: { type: "Serving — Page Composition", read: "recommendation_id / model_version / snapshot_id / fallback_level · 단계별 latency · U_t 가중치 · 행별 후보 출처 믹스" },
  S8: { type: "Implicit positive", read: "reader_open·qualified_read 기록 → U_t의 β 상승" },
  S9: { type: "Preference Refresh ≠ Profile Reset", read: "snapshot_01 → snapshot_02 · 독서 기록·\"이어 읽기\" 유지 · α 일시 상승" },
};

const PRESETS = [
  ["newUser", "신규 유저 A"],
  ["skipUser", "건너뛰기 유저"],
  ["resetUser", "재설정 유저"],
];

const snapId = (state) => state.snapshots[state.snapshots.length - 1]?.id || "none";

function sec(title, inner, hint = "") {
  return `<section class="insp-sec"><h2 class="insp-sec__title">${esc(title)}</h2>
    ${hint ? `<p class="insp-sec__hint">${esc(hint)}</p>` : ""}${inner}</section>`;
}

function signalSection(state) {
  // 재설정 중(S9)에는 온보딩 단계 위에 S9 해석을 겹쳐 보여준다
  const key = state.resetting && SIGNALS[state.screen] ? "S9" : state.screen;
  const s = SIGNALS[key] || SIGNALS.S7;
  const rows = [["단계", state.resetting ? `${state.screen} (재설정)` : state.screen],
    ["신호 유형", s.type], ["해석", s.read]];
  if (s.extra) rows.push(["부가", s.extra]);
  if (state.resetting) rows.push(["스냅샷", `${snapId(state)} → 재설정 완료 시 새 스냅샷 추가`]);
  if (state.screen === "S5") {
    const imp = state.candidateSet.impressions;
    rows.push(["노출 로그", `${imp.length}건 누적 · selected ${imp.filter((i) => i.selected).length}건`]);
    rows.push(["candidate_set_id", state.candidateSet.id || "—"]);
  }
  if (state.screen === "S3" && state.prefs.criterion === "좋아하는 출판사") {
    rows.push(["배지", "데모 데이터 미지원 (Goodbooks-10k에 출판사 컬럼 없음) → 배지 생략"]);
  }
  const unsup = state.prefs.categories.filter((c) => state.unsupported.includes(c));
  if (unsup.length) rows.push(["미지원 카테고리", `${unsup.join(", ")} — 데모 데이터 미지원`]);
  return sec(`현재 단계의 신호 해석 (${state.screen})`,
    `<dl class="kv">${rows.map(([k, v]) => `<dt>${esc(k)}</dt><dd>${esc(v)}</dd>`).join("")}</dl>`);
}

function logSection(state) {
  const rows = state.events.slice(-20).reverse();
  const inner = rows.length
    ? rows.map((e) => `<div class="log__row"><span class="log__t">${esc(e.t)}</span>
        <span class="log__k">${esc(e.event_type)}</span> ${esc(e.detail)}</div>`).join("")
    : '<div class="log__empty">아직 이벤트가 없습니다.</div>';
  return sec(`이벤트 로그 (최근 20건 / 총 ${state.events.length}건)`, `<div class="log">${inner}</div>`);
}

function latencySection(state) {
  const lat = state.recommend?.latency_ms;
  if (!lat) return "";
  const stages = ["feature", "retrieval", "ranking", "rerank", "compose"];
  const max = Math.max(...stages.map((k) => lat[k] || 0), 1);
  const bars = stages.map((k) => `<span class="lat__name">${k}</span>
    <span class="lat__track"><span class="lat__fill" style="width:${((lat[k] || 0) / max) * 100}%"></span></span>
    <span class="lat__val">${lat[k]}ms</span>`).join("");
  const totalPct = Math.min(100, (lat.total / BUDGET_MS) * 100);
  return sec("파이프라인 · latency",
    `<div class="lat">${bars}
      <span class="lat__name lat__total">total</span>
      <span class="lat__track lat__total"><span class="lat__fill" style="width:${totalPct}%"></span></span>
      <span class="lat__val lat__total">${lat.total}ms</span>
      <span class="lat__budget"><span style="left:100%">BUDGET ${BUDGET_MS}ms</span></span>
    </div>`,
    "mock 고정값 + 지터. 서버 측정값이 아니므로 PDF 숫자로 쓰지 않는다.");
}

function weightsSection(state) {
  const w = state.recommend?.user_state_weights || { alpha: 0, beta: 0, gamma: 0 };
  const cells = [
    ["α", w.alpha, "explicit (온보딩 선택)"],
    ["β", w.beta, "long-term (독서 기록)"],
    ["γ", w.gamma, "session (현재 세션)"],
  ].map(([k, v, n]) => `<div class="weight"><div class="weight__k">${k}</div>
    <div class="weight__v">${Number(v).toFixed(2)}</div><div class="weight__n">${esc(n)}</div></div>`).join("");
  const note = !state.recommend
    ? "아직 /recommend 응답이 없습니다 — 온보딩을 완료하면 가중치가 채워집니다."
    : state.consent === false
      ? "consent=false → 개인화 차단, 가중치 전부 0"
      : `U_t = ${w.alpha.toFixed(2)}·explicit + ${w.beta.toFixed(2)}·long + ${w.gamma.toFixed(2)}·session`
        + (state.resetBoost ? " · 재설정 직후 α 일시 상승" : "");
  return sec("U_t 가중치", `<div class="weights">${cells}</div>`, note);
}

function modelSection(state) {
  const rec = state.recommend;
  const radios = MODELS.map(([v, label]) => `<label><input type="radio" name="model" value="${v}"
    data-act="model"${state.model === v ? " checked" : ""}>${esc(label)}</label>`).join("");
  const rows = [
    ["source", `${state.source}${rec?.model_version === "static_popular" ? " → client fallback" : ""}`],
    ["recommendation_id", rec?.recommendation_id || "—"],
    ["model_version", rec?.model_version || "—"],
    ["snapshot_id", rec?.preference_snapshot_id || "—"],
    ["fallback_level", rec ? `${rec.fallback_level}${rec.model_version === "static_popular" ? " (client)" : ""}` : "—"],
    ["dedup_removed", rec ? `${rec.dedup_removed}권` : "—"],
  ];
  const mix = (rec?.rows || []).map((r) => {
    const m = r.channel_mix || {};
    const parts = Object.entries(m).filter(([, v]) => v).map(([k, v]) => `${k}:${v}`).join(" ");
    return `<div class="chan"><b>${esc(r.row_id)}</b> ${esc(parts || "—")} (${r.items.length}권)</div>`;
  }).join("");
  return sec("모델 전환 · 응답 ID",
    `<div class="models">${radios}</div>
     <dl class="kv">${rows.map(([k, v]) => `<dt>${esc(k)}</dt><dd class="mono">${esc(v)}</dd>`).join("")}</dl>
     ${mix ? `<p class="insp-sec__hint" style="margin:12px 0 6px">행별 후보 출처 믹스</p>${mix}` : ""}`);
}

export function render(state) {
  return `${sec("시나리오 프리셋", `<div class="presets">${PRESETS.map(([act, label]) =>
      `<button class="preset" data-act="preset" data-preset="${act}">${esc(label)}</button>`).join("")}</div>`)}
    ${signalSection(state)}
    ${logSection(state)}
    ${latencySection(state)}
    ${weightsSection(state)}
    ${modelSection(state)}`;
}
