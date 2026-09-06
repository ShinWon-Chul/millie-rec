// 우측 인스펙터 — 폰 화면 옆에서 "그 순간 시스템이 받는 신호"를 보여주는 6개 섹션.
// 취향 설정 단계 문구는 화면설계 01 §4-1 표, 페이지 문구는 화면 구성 02 §2 인스펙터 행이 정본이다.
import { esc } from "./screens/ui.js";

const BUDGET_MS = 200;
const MODELS = [["pop", "Pop"], ["cf", "CF"], ["hybrid", "Hybrid"], ["hybrid_div", "+Diversity"]];
const STAGES = ["feature", "retrieval", "ranking", "rerank", "pipeline", "compose"];
const TIMELINE = [["reader_open", "reader_open"], ["qualified_read", "qualified_read"],
  ["completion", "completion"], ["rating", "rating"]];

const SIGNALS = {
  S0: { type: "—", read: "건너뛰기 시 consent=absent → fallback: diverse popular (§7 개인정보 graceful degradation)" },
  S1: { type: "Context prior(맥락 사전 정보)", read: "장르 규칙 금지, ranker의 context×format 피처", extra: "consent=granted" },
  S2: { type: "Broad taste prior", read: "후보 생성 필터/부스팅 채널" },
  S3: { type: "Selection-policy preference", read: "랭킹 피처 가중 + 노출 배지 타입 결정 (Netflix Artwork Personalization)" },
  S4: { type: "Fine-grained taste prior", read: "prior 정밀화" },
  S5: { type: "Strong explicit positive seeds", read: "노출 로그 테이블 실시간 누적 candidate_set_id / book_id / position / selected → \"미선택 ≠ negative\"", extra: "library_add(source=onboarding) 이벤트" },
  S6: { type: "UX layer — 모델 입력 아님", read: "설명 문구가 실제 explicit state에서 생성됨을 표시 (밀리 현행은 고정 템플릿으로 보임 → 개선점)" },
  home: { type: "Serving — Page Composition", read: "recommendation_id / model_version / snapshot_id / cell / fallback_level · latency_breakdown · U_t · 행별 channel_mix · dedup_removed" },
  book: { type: "Implicit positive (detail_click)", read: "카드 탭 → detail_click 기록. 바로 읽기 → reader_open → Nearline 세션·이어 읽기 행" },
  reader: { type: "Implicit positive (reader_open · qualified_read · completion)", read: "가상 15분 도달 = Qualified Reading Start(주 지표 분자) · 완독 → Nearline 웨이크 → after_completion 행 · β↑" },
  library: { type: "열람·삭제·철회권 + U_t", read: "GET …/state · GET …/data · DELETE …/personalization → consent=false · 이후 level 3" },
  refresh: { type: "Preference Refresh ≠ Profile Reset", read: "snap_01 → snap_02 · 독서 기록·이어 읽기 유지 · α +0.15(24h)" },
};

const snapId = (state) => state.snapshots[state.snapshots.length - 1]?.id || "none";
const kv = (rows) => `<dl class="kv">${rows
  .map(([k, v]) => `<dt>${esc(k)}</dt><dd>${esc(v)}</dd>`).join("")}</dl>`;

function sec(title, inner, hint = "") {
  return `<section class="insp-sec"><h2 class="insp-sec__title">${esc(title)}</h2>
    ${hint ? `<p class="insp-sec__hint">${esc(hint)}</p>` : ""}${inner}</section>`;
}

/** 취향 설정 중이면 단계(S0~S6), 아니면 페이지. 재설정 중에는 단계 위에 refresh 해석을 겹친다. */
function signalKey(state) {
  const page = state.route?.page;
  if (page === "onboarding" || page === "refresh") return state.resetting ? "refresh" : state.screen;
  return SIGNALS[page] ? page : state.screen;
}

function signalSection(state) {
  const key = signalKey(state);
  const s = SIGNALS[key] || SIGNALS.home;
  const where = state.resetting ? `${state.screen} (재설정)` : key;
  const rows = [["위치", where], ["신호 유형", s.type], ["해석", s.read]];
  if (s.extra) rows.push(["부가", s.extra]);
  if (state.resetting) rows.push(["스냅샷", `${snapId(state)} → 재설정 완료 시 새 스냅샷 추가`]);
  if (state.screen === "S5" && key === "S5") {
    const imp = state.candidateSet.impressions;
    rows.push(["노출 로그", `${imp.length}건 누적 · selected ${imp.filter((i) => i.selected).length}건`]);
    rows.push(["candidate_set_id", state.candidateSet.id || "—"]);
  }
  const unsupported = (state.meta?.categories ?? []).filter((c) => !c.supported).map((c) => c.name);
  const unsup = state.prefs.categories.filter((c) => unsupported.includes(c));
  if (unsup.length) rows.push(["미지원 카테고리", `${unsup.join(", ")} — 데모 데이터 미지원`]);
  return sec(`현재 위치의 신호 해석 (${where})`, kv(rows));
}

/** D3·D4 전용 — 카드 탭 한 번과 뷰어 타임라인이 어떤 이벤트가 되는지. */
function journeySection(state) {
  const page = state.route?.page;
  if (page === "book") {
    const it = state.detail?.item;
    if (!it) return "";
    const last = [...state.events].reverse().find((e) => e.event_type === "detail_click");
    return sec("책 상세 — 암묵 신호", kv([
      ["detail", `book_id ${it.book_id} · row ${state.detail.rowId ?? "—"} · position ${it.position ?? 0}`],
      ["detail_click", last ? `${last.t} ${last.detail}` : "아직 기록 없음"],
      ["다음 신호", "바로 읽기 → reader_open · 서재 담기 → library_add(surface=main)"],
    ]));
  }
  if (page === "reader") {
    const seen = new Set(state.events.map((e) => e.event_type));
    const marks = TIMELINE.map(([id, label]) =>
      `<span class="${seen.has(id) ? "is-on" : ""}">${seen.has(id) ? "●" : "○"} ${esc(label)}</span>`).join("");
    const r = state.reading;
    return sec("뷰어 — QRS 타임라인",
      `<div class="timeline-mini">${marks}</div>${kv([
        ["가상 독서 시간", r ? `${r.virtualMinutes}분 · 진행률 ${r.progressPct}%` : "—"],
        ["qualified / completed", r ? `${r.qualified ? "도달" : "미도달"} / ${r.completed ? "완독" : "읽는 중"}` : "—"],
        ["임계", "T=15분은 데모 상수, production은 로그 분포로 보정"],
        ["별점", "리뷰 리워드는 positivity bias 유발 → 라벨은 별점 원본, 리워드는 UX 제안만"],
      ])}`);
  }
  return "";
}

function logSection(state) {
  const rows = state.events.slice(-20).reverse();
  const inner = rows.length
    ? rows.map((e) => `<div class="log__row"><span class="log__t">${esc(e.t)}</span>
        <span class="log__k">${esc(e.event_type)}</span> ${esc(e.detail)}</div>`).join("")
    : '<div class="log__empty">아직 이벤트가 없습니다.</div>';
  return sec(`이벤트 로그 (최근 20건 / 총 ${state.events.length}건)`, `<div class="log">${inner}</div>`);
}

/** latency_ms 는 float 총합, latency_breakdown 은 비어 있을 수 있다(06-CONTEXT D-07b ②). */
function latencySection(state) {
  const rec = state.recommend;
  if (!rec) return "";
  const br = rec.latency_breakdown ?? {};
  const total = Number(rec.latency_ms ?? br.total ?? 0);
  const stages = STAGES.filter((k) => br[k] != null);
  const max = Math.max(...stages.map((k) => Number(br[k])), 1);
  const bars = stages.map((k) => `<span class="lat__name">${esc(k)}</span>
    <span class="lat__track"><span class="lat__fill" style="width:${(Number(br[k]) / max) * 100}%"></span></span>
    <span class="lat__val">${esc(Number(br[k]).toFixed(1))}ms</span>`).join("");
  const totalPct = Math.min(100, (total / BUDGET_MS) * 100);
  return sec("파이프라인 · latency",
    `<div class="lat">${bars}
      <span class="lat__name lat__total">total</span>
      <span class="lat__track lat__total"><span class="lat__fill" style="width:${totalPct}%"></span></span>
      <span class="lat__val lat__total">${esc(total.toFixed(1))}ms</span>
      <span class="lat__budget"><span style="left:100%">BUDGET ${BUDGET_MS}ms</span></span>
    </div>`,
    state.source === "mock"
      ? "mock 지연은 결정적 표시값 — PDF 숫자가 아님(PDF p95 는 results/latency.json)"
      : "서버 실측 · 참고용 — PDF p95 는 로컬 bench(results/latency.json)");
}

function weightsSection(state) {
  const w = state.recommend?.user_state_weights ?? {};
  const cells = [
    ["α", w.alpha ?? 0, "explicit (온보딩 선택)"],
    ["β", w.beta ?? 0, "long-term (독서 기록)"],
    ["γ", w.gamma ?? 0, "session (현재 세션)"],
  ].map(([k, v, n]) => `<div class="weight"><div class="weight__k">${k}</div>
    <div class="weight__v">${esc(Number(v).toFixed(2))}</div><div class="weight__n">${esc(n)}</div></div>`).join("");
  const note = !state.recommend
    ? "아직 추천 응답이 없습니다 — 취향 설정을 마치면 가중치가 채워집니다."
    : state.consent === false
      ? "consent=false → 개인화 차단, 가중치 전부 0"
      : `U_t = ${Number(w.alpha ?? 0).toFixed(2)}·explicit + ${Number(w.beta ?? 0).toFixed(2)}·long`
        + ` + ${Number(w.gamma ?? 0).toFixed(2)}·session`
        + (state.snapshots.length >= 2 ? " · 재설정 스냅샷 ≥2 → α 부스트 후보" : "");
  return sec("U_t 가중치", `<div class="weights">${cells}</div>`, note);
}

function modelSection(state) {
  const rec = state.recommend;
  const radio = (v, label) => `<label><input type="radio" name="model" value="${v}"
    data-act="model"${state.model === v ? " checked" : ""}>${esc(label)}</label>`;
  // 빈 값 = 셀 배정으로 되돌리기. actions.model 이 VARIANTS 밖 값을 null 로 되돌린다(부록 B).
  const radios = MODELS.map(([v, l]) => radio(v, l)).join("")
    + `<label><input type="radio" name="model" value="" data-act="model"${
      state.model == null ? " checked" : ""}>auto(셀 배정)</label>`;
  // 클라이언트 fallback 판정은 client_fallback_reason 의 존재 여부로만 한다
  // — fallback_level 3 은 정상 익명 응답에도 나온다(06-03 인계).
  const client = rec?.client_fallback_reason;
  const rows = [
    ["source", state.source, client ? `client fallback: ${client}` : ""],
    ["recommendation_id", rec?.recommendation_id || "—", ""],
    ["model_version", rec?.model_version || "—", ""],
    ["snapshot_id", rec?.preference_snapshot_id || "—", ""],
    ["cell", rec?.cell ?? "—", rec?.cell ? (rec.forced ? "forced (model= 지정)" : "셀 배정") : ""],
    ["fallback_level", rec ? rec.fallback_level : "—", client ? "client" : ""],
    ["dedup_removed", rec ? `${rec.dedup_removed}권 (book_id ∧ 정규화 제목)` : "—", ""],
    ["Nearline 반영", rec?.nearline_lag_s != null ? `${Number(rec.nearline_lag_s).toFixed(1)}초` : "—", ""],
  ];
  const mix = (rec?.rows ?? []).map((r) => {
    const parts = Object.entries(r.channel_mix ?? {}).filter(([, v]) => v)
      .map(([k, v]) => `${k}:${v}`).join(" ");
    return `<div class="chan"><b>${esc(r.row_id)}</b> ${esc(parts || "—")} (${(r.items ?? []).length}권)</div>`;
  }).join("");
  return sec("모델 전환 · 응답 ID",
    `<div class="models">${radios}</div>
     <dl class="kv">${rows.map(([k, v, f]) => `<dt>${esc(k)}</dt><dd class="mono">${esc(v)}${
       f ? `<span class="insp-flag">${esc(f)}</span>` : ""}</dd>`).join("")}</dl>
     ${mix ? `<p class="insp-sec__hint" style="margin:12px 0 6px">행별 후보 출처 믹스</p>${mix}` : ""}`);
}

export function render(state) {
  return `${signalSection(state)}
    ${journeySection(state)}
    ${logSection(state)}
    ${latencySection(state)}
    ${weightsSection(state)}
    ${modelSection(state)}`;
}
