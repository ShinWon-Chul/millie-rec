// D7 관제 대시보드 #/dashboard — DashboardOut 한 형태만 렌더 (화면 구성 02 §2 D7)
// api 모드 = 서버 집계, mock 모드 = 이 브라우저 세션 이벤트 집계(06-CONTEXT D-03). 고정 예시 숫자 0.
import { esc, demoLabel } from "./ui.js";

const BUDGET_MS = 200; // contracts.BUDGET_MS

// kpi 이름 6개는 05-CONTEXT '대시보드 KPI 6' — 여기에는 [이름, 표시 라벨, 형식, 색 규칙] 만 둔다.
const KPI = [
  ["qualified_reading_start_rate", "Qualified Reading Start rate", "pct", ""],
  ["first_completion_rate_new", "첫 완독 도달률 (신규)", "pct", ""],
  ["fallback_rate", "fallback %", "pct", "low"],
  ["p95_latency_ms", "p95 latency", "ms", "budget"],
  ["error_rate", "오류율", "pct", "low"],
  ["active_user_keys", "활성 user_key", "int", ""],
];

const pct = (v) => (v == null ? "-" : `${(v * 100).toFixed(1)}%`);
const ms = (v) => (v == null ? "-" : `${Number(v).toFixed(1)}ms`);
const fmt = (v, kind) => (v == null ? "-" : kind === "pct" ? pct(v) : kind === "ms" ? ms(v) : String(Math.round(v)));
const tone = (rule, v) => {
  if (v == null || !rule) return "";
  if (rule === "budget") return v > BUDGET_MS ? "is-bad" : "is-good"; // 예산선 contracts.BUDGET_MS
  return v > 0.1 ? "is-warn" : "is-good"; // "low" — 낮을수록 좋은 비율
};

function kpis(d) {
  const cards = KPI.map(([name, label, kind, rule]) => {
    const k = (d.kpi ?? {})[name] ?? {};
    const ref = rule === "budget" ? '<span class="ref-label">서버 실측 참고용</span>' : "";
    return `<div class="kpi__card ${tone(rule, k.value)}">
      <div class="kpi__name">${esc(label)}${ref}</div>
      <div class="kpi__v">${fmt(k.value, kind)}</div>
      <div class="kpi__n">n = ${k.n ?? "-"}</div>
      ${k.note ? `<div class="kpi__note">${esc(k.note)}</div>` : ""}</div>`;
  }).join("");
  return `<div class="kpi">${cards}</div>`;
}

function abTable(d) {
  const rows = (d.ab_table ?? []).map((r) => `<tr>
      <td>${esc(r.cell)}</td><td>${esc(r.segment)}</td><td class="num">${esc(r.n)}</td>
      <td class="num">${pct(r.primary)}</td><td class="num">${pct(r.reader_open)}</td>
      <td class="num">${pct(r.completion)}</td>
      <td class="num">${r.rating_mean == null ? "-" : Number(r.rating_mean).toFixed(2)}</td>
      <td class="num">${pct(r.first_completion)}</td>
      <td class="num">${r.p95_ms == null ? "-" : Number(r.p95_ms).toFixed(1)}</td>
      <td class="num">${pct(r.fallback_rate)}</td></tr>`).join("");
  return `<section><h2>A/B 표 <span class="ref-label">Primary, Secondary, Guardrail</span></h2>
    <table class="dt"><thead><tr><th>cell</th><th>segment</th><th>n</th><th>QRS(primary)</th><th>reader_open</th>
      <th>완독</th><th>별점 평균</th><th>첫 완독</th><th>p95 ms</th><th>fallback</th></tr></thead>
    <tbody>${rows || '<tr><td colspan="10" class="empty">아직 표본이 없습니다</td></tr>'}</tbody></table>
    <p class="caption">${esc(d.mde_note)}</p></section>`;
}

function latency(d) {
  const L = d.latency ?? {};
  const stages = Object.entries(L.by_stage ?? {});
  const max = Math.max(BUDGET_MS, L.p95 ?? 0, ...stages.map(([, v]) => (v ?? [])[1] ?? 0));
  const w = (v) => Math.min(100, ((v ?? 0) / max) * 100);
  const bar = (name, p50, p95) => `<div class="bar"><span>${esc(name)}</span>
    <span class="bar__track"><span class="bar__fill is-p95" style="width:${w(p95)}%"></span>
      <span class="bar__fill" style="width:${w(p50)}%"></span></span>
    <span class="bar__v">${Number(p50 ?? 0).toFixed(1)} / ${Number(p95 ?? 0).toFixed(1)}</span></div>`;
  return `<section><h2>latency <span class="ref-label">서버 실측 참고용, PDF 수치는 로컬 bench</span></h2>
    ${bar("total", L.p50, L.p95)}${stages.map(([k, v]) => bar(k, (v ?? [])[0], (v ?? [])[1])).join("")}
    <div class="bar__budget"><span style="left:${w(BUDGET_MS)}%">BUDGET ${BUDGET_MS}ms</span></div>
    <p class="caption">막대 = p50, 옅은 막대 = p95, p99 ${ms(L.p99)}</p></section>`;
}

function quality(d) {
  const q = d.quality ?? {};
  return `<section><h2>데이터 품질</h2><table class="dt"><tbody>
    <tr><td>impression 수신율 (응답 item 수 대비)</td><td class="num">${pct(q.impression_receipt_rate)}</td></tr>
    <tr><td>quality_flag 건수</td><td class="num">${q.flagged_events ?? "-"}</td></tr>
    <tr><td>feature freshness</td><td class="num">${q.feature_freshness_s == null ? "-" : `${q.feature_freshness_s}s`}</td></tr>
    </tbody></table></section>`;
}

const clock = (v) => esc(String(v ?? "").slice(11, 19));

function streams(d) {
  const evs = d.events_recent ?? [];
  const ev = evs.map((e) => `<div class="stream__row"><span>${clock(e.ts)}</span>
    <span><b>${esc(e.event_type)}</b> ${esc(e.book_id ?? "")}</span>
    <span>${esc(e.recommendation_id ?? "")} ${esc(e.model_version ?? "")} ${esc(e.preference_snapshot_id ?? "")}</span></div>`).join("");
  const imp = (d.impressions_log ?? []).map((i) => `<div class="stream__row"><span>${clock(i.ts)}</span>
    <span>${esc(i.candidate_set_id ?? "")}</span>
    <span>book ${esc(i.book_id ?? "")}, pos ${esc(i.position ?? "")}, selected ${esc(i.selected ?? "")}</span></div>`).join("");
  const bv = d.by_variant ?? {};
  const bvMax = Math.max(1, ...Object.values(bv));
  const byv = Object.entries(bv).map(([k, v]) => `<div class="bar"><span>${esc(k)}</span>
    <span class="bar__track"><span class="bar__fill" style="width:${Math.min(100, (v / bvMax) * 100)}%"></span></span>
    <span class="bar__v">${esc(v)}</span></div>`).join("");
  return `<div class="two">
    <section><h2>이벤트 스트림 <span class="ref-label">최근 ${evs.length}</span></h2>
      <div class="stream">${ev || '<div class="empty">아직 이벤트가 없습니다</div>'}</div></section>
    <section><h2>노출 로그 <span class="ref-label">survey_variant=v1</span></h2>
      <div class="stream">${imp || '<div class="empty">아직 노출 로그가 없습니다</div>'}</div>
      <p class="caption">candidate_set_id / position / selected 를 남깁니다. 미선택 ≠ negative</p></section></div>
    <section><h2>모델별 요청 분포</h2>${byv || '<div class="empty">아직 요청이 없습니다</div>'}</section>`;
}

export function render(state) {
  const d = state.dashboard;
  const head = `${demoLabel()}<div class="page-head"><div><h1>관제 대시보드</h1>
    <p class="caption">generated_at ${esc(d?.generated_at ?? "-")}, window ${esc(d?.window ?? "-")}, source ${esc(state.source)}</p></div>
    <div class="page-head__meta"><a href="#/">← 쇼케이스</a>, <a href="#/home">메인</a>,
      <a href="/docs" target="_blank" rel="noreferrer">/docs</a></div></div>`;
  if (!d) {
    return `${head}<div class="empty">이 항목은 아직 없습니다. 서버 준비 중입니다(GET /api/dashboard).
      mock 모드에서는 이 브라우저 세션의 이벤트가 집계됩니다.</div>`;
  }
  return `${head}${kpis(d)}${abTable(d)}${latency(d)}${quality(d)}${streams(d)}`;
}
