// D8 쇼케이스 랜딩 #/ — 심사자가 처음 보는 화면 (화면 구성 02 §2 D8)
// 숫자·문장은 전부 state.showcase(ShowcaseOut)에서만 온다. 이 파일에 지표 값·철학·고지 하드코딩 0.
import { esc, cover, badge, demoLabel } from "./ui.js";

const MODELS = { pop: "Pop", cf: "CF", hybrid: "Hybrid", hybrid_div: "+Diversity" }; // contracts.VARIANTS 와 동일 키
const STAGES_COMPOSE = "Page Composition"; // metric_mapping 3행 뒤 지표 없는 4번째 칸(main 설계서 §5-1 [4])
const TITLE = "밀리의서재 메인 추천 시스템 설계 데모";

const num = (v, d = 3) => (v == null ? "-" : Number(v).toFixed(d));
/** 응답 route 를 해시 경로로만 강제한다(javascript: URL 차단 — 06-05 위협 T-06-05-02). */
const routeTail = (r) => { const s = String(r ?? ""); return s.startsWith("#/") ? s.slice(2) : ""; };

function header(s, state) {
  return `<div class="page-head"><div><h1><img class="page-head__mark" src="assets/brand/millie-mark.png" alt="밀리의서재" width="40" height="40">${TITLE}</h1>
    <p class="philosophy">${esc(s.philosophy)}</p></div>
    <div class="page-head__meta">model_version ${esc(state.health?.model_version ?? "-")}, source ${esc(state.source)},
      <a href="/docs" target="_blank" rel="noreferrer">/docs</a></div></div>`;
}

/** 단계↔지표 1:1 대응 그림(CSS만) — main 설계서 §6 */
function mapping(s) {
  const cells = (s.metric_mapping ?? []).map((m) =>
    `<div class="mapping__stage"><div class="mapping__name">${esc(m.stage)}</div>
      <span class="mapping__metric">${esc(m.metric)}</span></div>`).join("");
  return `<div class="mapping">${cells}<div class="mapping__stage is-compose">
    <div class="mapping__name">${STAGES_COMPOSE}</div>
    <span class="mapping__metric">지표 없음, 행 구성</span></div></div>`;
}

function metricsTable(s) {
  const t = s.eval_table ?? {};
  const mode = t.split_mode ?? "-";
  const rows = t.rows ?? [];
  const best = Math.max(...rows.map((r) => r.recall_at_20 ?? -1), -1);
  const noP95 = rows.every((r) => r.p95_ms == null);
  const body = rows.map((r) => `<tr${r.recall_at_20 === best ? ' class="is-best"' : ""}>
      <td>${esc(MODELS[r.variant] ?? r.variant)} <small class="mono">${esc(r.variant)}</small></td>
      <td class="num">${num(r.recall_at_20)}</td><td class="num">${num(r.ndcg_at_10)}</td>
      <td class="num">${num(r.ild_at_10)}</td>
      <td class="num">${r.p95_ms == null ? "-" : num(r.p95_ms, 1)}</td></tr>`).join("");
  // 이 표는 n=0(온보딩 직후) 한 상태다 — n>=k 표는 제출 문서 전용(app/export.py D-09).
  // 상태를 밝히지 않으면 처음 보는 사람이 콜드스타트 수치를 대표 성능으로 읽는다.
  return `<section><h2>평가 3지표 비교표 <span class="ref-label">Track A</span>
      <span class="ref-label">온보딩 직후 n=0</span></h2>${mapping(s)}
    <table class="dt"><thead><tr><th>variant</th><th>Recall@20</th><th>NDCG@10</th><th>ILD@10</th><th>p95 ms</th></tr></thead>
    <tbody>${body || '<tr><td colspan="5" class="empty">비교표가 아직 없습니다</td></tr>'}</tbody></table>
    <p class="caption">취향 설정 5권만 주고 독서 이력은 전부 가린 상태입니다.
      후보를 좁히지 않고 카탈로그 전체에서 20권을 고르게 했습니다(네거티브 샘플링 없음).
      이력이 쌓인 상태(n≥20)의 같은 표는 제출 문서 4장에 함께 싣습니다.</p>
    <p class="caption">split_mode: ${esc(mode)}${mode === "temporal" ? " (train.ts.max < test.ts.min 단언 통과)" : ""},
      출처 ${esc(t.source?.metrics)}, p95 출처 ${esc(t.source?.p95)}(로컬 bench${noP95 ? ", 아직 없음" : ""})</p></section>`;
}

function personalCase(s) {
  const pc = s.personal_case;
  if (!pc) return `<section><h2>본인 5권 정성 케이스</h2><div class="case__wait">5권 선정 대기</div></section>`;
  // 카탈로그에 같은 제목 다른 book_id 가 있다(D-07b ③) — 저자로 구분하고, 없을 때만 book_id 를 쓴다.
  const book = (b) => `<div class="case__book">${cover(b)}
    <div>${esc(b.title ?? "(제목 없음)")}</div>
    <div class="case__author">${b.authors ? esc(b.authors) : `book_id ${esc(b.book_id)}`}</div>
    ${b.reason ? `<div class="case__reason">${esc(b.reason)}</div>` : ""}${badge(b.badge)}</div>`;
  const seeds = pc.seeds ?? [];
  const recs = pc.recommendations ?? [];
  return `<section><h2>본인 5권 정성 케이스 <span class="ref-label">Track B 밀리 카탈로그</span></h2>
    <div class="case">
      <div class="case__col"><h3>내가 읽은 ${seeds.length}권</h3><div class="case__grid">${seeds.map(book).join("")}</div></div>
      <div class="case__col"><h3>추천 상위 ${recs.length}</h3><div class="case__grid">${recs.map(book).join("")}</div></div>
    </div></section>`;   // 이웃이 콘텐츠 유사도라는 고지는 데이터 고지 절과 책 상세 시트에 있다
}

function memorable(s) {
  if (!s.memorable_5?.length) return "";
  const cards = s.memorable_5.map((m) => `<div class="memo__card">
    <div class="memo__claim">${esc(m.claim)}</div>
    <div class="memo__how">${esc(m.how_to_verify)}</div>
    <a href="#/${esc(routeTail(m.route))}">#/${esc(routeTail(m.route))} →</a></div>`).join("");
  return `<section><h2>이 설계의 핵심 5가지</h2><div class="memo">${cards}</div></section>`;
}

function start() {
  return `<section><h2>직접 눌러보기</h2><div class="start">
    <button class="cta is-on" data-act="startFresh">신규 유저로 체험하기</button>
    <button class="start__preset" data-act="preset" data-preset="newUser">신규 유저 A</button>
    <button class="start__preset" data-act="preset" data-preset="skipUser">건너뛰기 유저</button>
    <button class="start__preset" data-act="preset" data-preset="resetUser">재설정 유저</button>
    <button class="start__preset" data-act="nav" data-to="#/dashboard">관제 대시보드</button></div>
    <p class="caption">동선: 취향 설정 → 메인 → 상세 → 뷰어(완독, 별점) → 메인 "다음은" 행 → 서재(재설정, 철회) → 대시보드</p></section>`;
}

// 로드맵 칩 절은 걷었다(사용자 결정 2026-09-06) — '설계만' 범위는 제출 문서 5장이 다룬다.
// 서버 ShowcaseOut.roadmap 필드는 계약 freeze 라 남겨 두고 화면만 그리지 않는다.

export function render(state) {
  const s = state.showcase;
  const head = demoLabel();
  if (!s) {
    return `${head}<div class="page-head"><h1>${TITLE}</h1></div>
      <div class="empty">이 항목은 아직 없습니다. 쇼케이스 데이터를 불러오지 못했습니다(GET /api/showcase).</div>${start()}`;
  }
  return `${head}${header(s, state)}${metricsTable(s)}${start()}${personalCase(s)}${memorable(s)}
    <section><h2>데이터 고지</h2><p class="caption">${esc(s.data_notice)}
      밀리의서재 로고는 상표권자의 자산이며, 이 사전과제 데모가 무엇에 관한 것인지 식별하기 위해서만 사용한다.</p></section>`;
}
