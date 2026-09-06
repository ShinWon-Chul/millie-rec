// mock 모드의 "서버 상태" — sessionStorage millie_mock_db 1키. 서버(SQLite 7테이블)의 축소판이며 형태는 serving/schemas 와 1:1.
const KEY = "millie_mock_db";
const EMPTY = () => ({ users: {}, snapshots: [], events: [], ratings: [], recommendations: [] });
const SESSION_WINDOW_S = 1800;                                     // 05-CONTEXT 세션 창
const READ_TYPES = ["reader_open", "qualified_read"];              // privacy_api._library
const HISTORY_TYPES = ["reader_open", "qualified_read", "completion"];
const STAGES = ["feature", "retrieval", "ranking", "rerank", "compose"];
const MDE_NOTE = "데모 표본으로 검정하지 않음 — MDE +1%p 검출에 셀당 n만 명";
const NOTE_P95 = "mock 상수 · 참고용 — PDF 숫자 아님";
const NOTE_QRS = "QRS = 가상 15분 도달 / 뷰어 진입";
const NOTE_ERR = "mock 은 오류를 내지 않는다";
const NOTE_PRIVACY = "가명 user_key 외 개인정보 없음";
const FLAG_INELIGIBLE = "book_ineligible";

let db = null;
let isEligible = () => true;   // mock.js 가 카탈로그로 주입한다. 없으면 전부 통과

function load() {
  if (!db) { try { db = JSON.parse(sessionStorage.getItem(KEY)) || EMPTY(); } catch { db = EMPTY(); } }
  return db;
}
function save() { sessionStorage.setItem(KEY, JSON.stringify(db)); }
const nowIso = () => new Date().toISOString();

export function setCatalog(fn) { isEligible = fn || (() => true); }
export const hex6 = () => crypto.randomUUID().replace(/-/g, "").slice(0, 6);   // 서버 ID 형식 rec_/snap_/cand_/rat_ + 6hex

/** sha256 첫 8 hex — 서버 hashlib.sha256(...).hexdigest()[:8] 과 같은 값(셀·페르소나 공용). */
export async function sha256Hex8(text) {
  const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
  return [...new Uint8Array(buf)].slice(0, 4).map((b) => b.toString(16).padStart(2, "0")).join("");
}

/** 05-CONTEXT D-08 그대로: int(sha256(user_key)[:8], 16) % 2 == 0 → "A". */
export async function cellFor(userKey) {
  return parseInt(await sha256Hex8(String(userKey)), 16) % 2 === 0 ? "A" : "B";
}

// ── users ───────────────────────────────────────────────────────────────────
export function upsertUser(userKey, { consent = true, cell = "A" } = {}) {
  const d = load();
  d.users[userKey] = { user_key: userKey, consent, cell, created_at: d.users[userKey]?.created_at ?? nowIso() };
  save();
  return d.users[userKey];
}
export function getUser(userKey) { return load().users[userKey] ?? null; }

// ── preference_snapshots (append only — 05-CONTEXT D-08) ────────────────────
export function addSnapshot(row) {
  const d = load();
  const snap = { snapshot_id: "snap_" + hex6(), created_at: nowIso(), ...row };
  d.snapshots.push(snap);
  save();
  return snap;
}
export function snapshotsOf(userKey) {
  return load().snapshots.filter((s) => s.user_key === userKey).reverse();
}
export function latestSnapshot(userKey) { return snapshotsOf(userKey)[0] ?? null; }

// ── events ──────────────────────────────────────────────────────────────────
/** event_id 중복은 duplicates, 자격 미달 도서는 flagged(저장은 한다). → EventsAccepted */
export function addEvents(events) {
  const d = load();
  const seen = new Set(d.events.map((e) => e.event_id));
  let accepted = 0, duplicates = 0;
  const flagged = [];
  for (const e of events || []) {
    if (seen.has(e.event_id)) { duplicates += 1; continue; }
    seen.add(e.event_id);
    if (e.book_id != null && !isEligible(e.book_id)) flagged.push({ event_id: e.event_id, quality_flag: FLAG_INELIGIBLE });
    d.events.push(e);
    accepted += 1;
  }
  save();
  return { accepted, duplicates, flagged };
}
export function eventsOf(userKey, types = null) {
  return load().events
    .filter((e) => e.user_key === userKey && (!types || types.includes(e.event_type)))
    .reverse();
}
/** distinct book_id, 최신순 — privacy_api._ids 와 같은 규칙. */
export function booksBy(userKey, types) {
  return [...new Set(eventsOf(userKey, types).map((e) => e.book_id).filter((b) => b != null))];
}
export function library(userKey) {
  const completed = booksBy(userKey, ["completion"]);
  return {
    added: booksBy(userKey, ["library_add"]),
    reading: booksBy(userKey, READ_TYPES).filter((b) => !completed.includes(b)),
    completed,
  };
}
export function continueIds(userKey) {
  const done = new Set(booksBy(userKey, ["completion"]));
  return booksBy(userKey, ["reader_open"]).filter((b) => !done.has(b));
}
export function lastCompleted(userKey) { return booksBy(userKey, ["completion"])[0] ?? null; }
export function sessionActive(userKey, now) {
  const t = Date.parse(now) || Date.now();
  return eventsOf(userKey, ["reader_open", "detail_click"])
    .some((e) => t - Date.parse(e.ts) <= SESSION_WINDOW_S * 1000);
}
export function nHistory(userKey) { return booksBy(userKey, HISTORY_TYPES).length; }
export function nCompleted(userKey) { return booksBy(userKey, ["completion"]).length; }

// ── ratings · recommendations ───────────────────────────────────────────────
export function addRating(row) { const d = load(); d.ratings.push(row); save(); return row; }
export function ratingsOf(userKey) { return load().ratings.filter((r) => r.user_key === userKey); }
export function logRecommendation(row) { const d = load(); d.recommendations.push(row); save(); return row; }

// ── 열람권 · 철회 (백엔드 서빙 01 §9~§10) ───────────────────────────────────
export function userData(userKey) {
  const d = load();
  return {
    user: d.users[userKey] ?? { user_key: userKey },
    snapshots: snapshotsOf(userKey),
    events: d.events.filter((e) => e.user_key === userKey),
    ratings: ratingsOf(userKey),
    recommendations: d.recommendations.filter((r) => r.user_key === userKey),
    candidate_sets: [],
    exported_at: nowIso(),
    note: NOTE_PRIVACY,
  };
}
export function deleteUser(userKey) {
  const d = load();
  const counts = {};
  for (const [name, table] of [["snapshots", "snapshots"], ["events", "events"],
    ["ratings", "ratings"], ["recommendations", "recommendations"]]) {
    const before = d[table].length;
    d[table] = d[table].filter((x) => x.user_key !== userKey);
    counts[name] = before - d[table].length;
  }
  counts.candidate_sets = 0;
  if (d.users[userKey]) d.users[userKey].consent = false;   // users 행은 남긴다(§10 재동의)
  save();
  return { user_key: userKey, consent: false, deleted: counts };
}
export function reset() { db = EMPTY(); save(); }

// ── DashboardOut — 이 세션의 이벤트 직접 집계(06-CONTEXT D-03). 고정 예시 숫자 없음 ──
const pct = (a, b) => (b ? Math.round((a / b) * 1000) / 1000 : 0);
function percentile(arr, p) {
  if (!arr.length) return 0;
  const s = [...arr].sort((x, y) => x - y);
  return s[Math.min(s.length - 1, Math.floor(p * s.length))];
}
const pairsOf = (evs, types) => new Set(evs
  .filter((e) => types.includes(e.event_type) && e.book_id != null)
  .map((e) => e.user_key + ":" + e.book_id));
const usersWith = (evs, type) => new Set(evs.filter((e) => e.event_type === type).map((e) => e.user_key));

function kpiBlock(d) {
  const ev = d.events, recs = d.recommendations;
  const opens = pairsOf(ev, ["reader_open"]), qrs = pairsOf(ev, ["qualified_read"]);
  const snapN = {};
  for (const s of d.snapshots) snapN[s.user_key] = (snapN[s.user_key] || 0) + 1;
  const fresh = Object.keys(snapN).filter((u) => snapN[u] === 1);
  const done = usersWith(ev, "completion");
  const fb = recs.filter((r) => (r.fallback_level ?? 0) >= 1).length;
  return {
    qualified_reading_start_rate: { value: pct(qrs.size, opens.size), n: opens.size, note: NOTE_QRS },
    first_completion_rate_new: { value: pct(fresh.filter((u) => done.has(u)).length, fresh.length), n: fresh.length, note: null },
    fallback_rate: { value: pct(fb, recs.length), n: recs.length, note: null },
    p95_latency_ms: { value: percentile(recs.map((r) => r.latency_ms ?? 0), 0.95), n: recs.length, note: NOTE_P95 },
    error_rate: { value: 0, n: recs.length, note: NOTE_ERR },
    active_user_keys: { value: new Set(ev.map((e) => e.user_key)).size, n: ev.length, note: null },
  };
}

/** 셀 A/B × 세그먼트 new/existing 4행 — n=0 이어도 행은 남긴다(표가 비지 않게). */
function abTable(d) {
  const out = [];
  for (const cell of ["A", "B"]) for (const segment of ["new", "existing"]) {
    const keys = Object.keys(d.users).filter((u) => (d.users[u].cell || "A") === cell
      && (d.snapshots.filter((s) => s.user_key === u).length <= 1) === (segment === "new"));
    const n = keys.length;
    if (!n) {
      out.push({ cell, segment, n: 0, primary: null, reader_open: null, completion: null,
        rating_mean: null, first_completion: null, p95_ms: null, fallback_rate: null });
      continue;
    }
    const set = new Set(keys);
    const ev = d.events.filter((e) => set.has(e.user_key));
    const recs = d.recommendations.filter((r) => set.has(r.user_key));
    const stars = d.ratings.filter((r) => set.has(r.user_key)).map((r) => r.stars);
    const comp = usersWith(ev, "completion").size;
    out.push({
      cell, segment, n,
      primary: pct(pairsOf(ev, ["qualified_read"]).size, pairsOf(ev, ["reader_open"]).size),
      reader_open: pct(usersWith(ev, "reader_open").size, n),
      completion: pct(comp, n),
      rating_mean: stars.length ? Math.round((stars.reduce((a, b) => a + b, 0) / stars.length) * 100) / 100 : null,
      first_completion: pct(comp, n),
      p95_ms: percentile(recs.map((r) => r.latency_ms ?? 0), 0.95),
      fallback_rate: pct(recs.filter((r) => (r.fallback_level ?? 0) >= 1).length, recs.length),
    });
  }
  return out;
}

function latencyBlock(recs) {
  const total = recs.map((r) => r.latency_ms ?? 0);
  const by_stage = {};
  for (const s of STAGES) {
    const v = recs.map((r) => (r.latency_breakdown || {})[s]).filter((x) => typeof x === "number");
    by_stage[s] = [percentile(v, 0.5), percentile(v, 0.95)];
  }
  return { p50: percentile(total, 0.5), p95: percentile(total, 0.95), p99: percentile(total, 0.99), by_stage };
}

function byHour(ev) {
  const c = new Array(24).fill(0);
  for (const e of ev) { const h = new Date(e.ts).getHours(); if (!Number.isNaN(h)) c[h] += 1; }
  return c.map((n, hour) => ({ hour, n })).filter((r) => r.n > 0);
}

export function dashboard(now) {
  const d = load();
  const ev = d.events, recs = d.recommendations;
  const imps = ev.filter((e) => e.event_type === "impression");
  const shown = recs.reduce((a, r) => a + (r.n_items || 0), 0);
  return {
    generated_at: now || nowIso(),
    window: "session",
    kpi: kpiBlock(d),
    ab_table: abTable(d),
    mde_note: MDE_NOTE,
    latency: latencyBlock(recs),
    quality: {
      impression_receipt_rate: pct(imps.filter((e) => e.surface === "home").length, shown),
      flagged_events: ev.filter((e) => e.book_id != null && !isEligible(e.book_id)).length,
      feature_freshness_s: 1.0,
    },
    events_recent: ev.slice(-50).reverse(),
    impressions_log: imps.filter((e) => e.candidate_set_id).slice(-50).reverse().map((e) => ({
      event_id: e.event_id, candidate_set_id: e.candidate_set_id, book_id: e.book_id,
      position: e.position ?? null, selected: e.selected ?? null, ts: e.ts,
    })),
    by_variant: recs.reduce((a, r) => ({ ...a, [r.model_version]: (a[r.model_version] || 0) + 1 }), {}),
    by_hour: byHour(ev),
  };
}
