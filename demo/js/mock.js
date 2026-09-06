// mock 모드의 서버 흉내 — 밀리 카탈로그 위 상태 시뮬레이션(06-CONTEXT D-01). 점수 계산 없음:
// 이웃은 사전 계산 테이블 조회, 배지·가중치·페르소나는 서버와 같은 조건의 표시 규칙이다.
import { josa } from "./screens/ui.js";
import * as store from "./mock_store.js";

const ROW_SIZE = 12, ANCHOR_NEIGHBORS = 20, FRESH_POOL_N = 30;
const REVIEW_MIN_COUNT = 3, REVIEW_MIN_COUNT_NO_RATING = 10;
const VARIANTS = ["pop", "cf", "hybrid", "hybrid_div"];
const LATENCY = { feature: 4.0, retrieval: 12.0, ranking: 9.0, rerank: 6.0, compose: 7.0, total: 38.0 };  // 표시값 — PDF 숫자 아님
const NEARLINE_LAG_S = 1.0;                 // mock 은 즉시 반영, 표시용 결정적 상수
const T_CONTINUE = "이어 읽기", T_TREND = "지금 많이 읽는 책", T_FRESH = "새로운 발견";
const T_PERSONA_DEFAULT = "회원님의 서가", SUBTITLE_ANCHOR = "결이 비슷한 책";
const CATS_NONE = "다양한 분야", CRITERION_NONE = "취향";
const REASON_ANCHOR = (t) => `『${t}』을 좋아하셨다면`, TITLE_AFTER = (t) => `『${t}』을 완독하셨네요, 다음은`;
const PERSONAS = [["오디세우스", "오디세이아", "지혜로 승리하리라!"], ["셜록 홈즈", "주홍색 연구", "사소한 것이 가장 중요하다."],
  ["돈키호테", "돈키호테", "이룰 수 없는 꿈을 꾸리라!"], ["제인 에어", "제인 에어", "나는 나 자신의 주인입니다."]];
const CATEGORY_TO_PERSONA = { 경제경영: 0, 자기계발: 0, IT: 0, 소설: 1, 과학: 1, 철학: 1,
  인문: 2, 역사: 2, 사회: 2, "에세이/시": 3, 라이프스타일: 3 };
const local = (p) => fetch(p).then((r) => { if (!r.ok) throw new Error(`HTTP ${r.status} ${p}`); return r.json(); });
let ready = null, pool = [], index = new Map(), nbrs = {}, byCat = new Map(), allCats = [], showcaseData = null, metaData = null;
/** 카탈로그·이웃·계약 JSON 1회 로드(Promise 캐시). pool 은 pop_rank 오름차순이다. */
export function init() {
  if (ready) return ready;
  ready = Promise.all([local("mock/catalog_kr.json"), local("mock/neighbors_kr.json"),
    local("mock/showcase.json"), local("mock/meta_onboarding.json")]).then(([cat, nb, sc, mt]) => {
    [pool, nbrs, showcaseData, metaData] = [cat, nb, sc, mt];
    index = new Map(cat.map((b) => [b.book_id, b]));
    byCat = new Map();
    for (const b of cat) for (const c of b.categories || []) byCat.set(c, [...(byCat.get(c) ?? []), b]);
    allCats = [...byCat.entries()].sort((a, b) => b[1].length - a[1].length).map(([c]) => c);
    store.setCatalog((id) => index.has(id));
  });
  return ready;
}
export function byId(bookId) { return index.get(Number(bookId)); }
function byPop(cats) {   // 카테고리 교집합, pop_rank 순. 단일 카테고리는 init 의 색인을 그대로 쓴다
  if (!cats || !cats.length) return pool;
  if (cats.length === 1) return byCat.get(cats[0]) ?? [];
  const want = new Set(cats);
  return pool.filter((b) => (b.categories || []).some((c) => want.has(c)));
}
/** subcat.py prioritize 1:1 — 선택 세부 분류와 겹치는 책을 앞으로(하드 필터 아님 · 커버리지 42.6%). 점수 계산이 아니라 표시 순서다. */
function prioritize(cards, picks) {
  if (!picks || !picks.length) return cards;   // 선택 없으면 항등
  const want = new Set(picks), hit = [], rest = [];
  for (const b of cards) ((b.subcategories || []).some((s) => want.has(s)) ? hit : rest).push(b);
  return [...hit, ...rest];
}
const mix = (its) => its.reduce((a, i) => { for (const c of i.source_channels) a[c] = (a[c] || 0) + 1; return a; }, {});
export function health() {   // HealthOut 8키
  return { status: "ok", api_version: "v2", model_version: "hybrid_div_v1", artifacts_loaded_at: null, db_ok: true, db_row_count: {}, nearline_last_run: null, uptime_s: 0 };
}
export function loadMeta() { return metaData; }
/** 05-CONTEXT D-15 — 선택 카테고리별 인기 목록을 1권씩 라운드로빈해 n 권. */
export function getCandidates({ categories = [], subcategories = [], n = 30 } = {}) {
  const lists = (categories.length ? categories : allCats.slice(0, 3)).map((c) => prioritize(byPop([c]), subcategories));
  const picked = [], seen = new Set();
  for (let i = 0; picked.length < n && lists.some((l) => l[i]); i += 1) for (const l of lists)
    if (l[i] && !seen.has(l[i].book_id) && picked.length < n) { seen.add(l[i].book_id); picked.push(l[i]); }
  return { candidate_set_id: "cand_" + store.hex6(), survey_variant: metaData?.survey_variant ?? "v1",
    created_at: new Date().toISOString(), items: picked.map((b, i) => ({ book_id: b.book_id, title: b.title,
      authors: b.authors, image_url: b.image_url, position: i, book_format: b.book_format })) };
}
/** persona.py·05-CONTEXT D-16 1:1. 미매핑 카테고리는 서버와 같은 sha256 결정적 선택. */
async function assignPersona(categories, criterionLabel) {
  const cats = (categories || []).slice(0, 2);
  const idx = !cats.length ? 0
    : CATEGORY_TO_PERSONA[cats[0]] ?? parseInt(await store.sha256Hex8(cats[0]), 16) % PERSONAS.length;
  const [name, work, quote] = PERSONAS[idx];
  const shown = cats.length >= 2 ? `${cats[0]}${josa(cats[0], "과", "와")} ${cats[1]}` : (cats[0] ?? CATS_NONE);
  const crit = criterionLabel || CRITERION_NONE;
  return { name, work, quote,
    description: `회원님은 ${shown}${josa(shown, "을", "를")} 즐기고, ${crit}${josa(crit, "으로", "로")} 책을 고르는 독서가입니다.` };
}
export async function postPreferences(body) {
  const uk = body.user_key, consent = body.consent !== false, ts = new Date().toISOString();
  const cell = await store.cellFor(uk);
  store.upsertUser(uk, { consent, cell });
  const persona = await assignPersona(body.categories,
    (metaData?.criteria || []).find((c) => c.id === body.criterion)?.label);
  const seeds = consent ? (body.seeds || []) : [];
  const snap = store.addSnapshot({ user_key: uk, reading_time: body.reading_time ?? null, seeds, persona,
    categories: body.categories || [], criterion: body.criterion ?? null, consent,
    subcategories: body.subcategories || [], candidate_set_id: body.candidate_set_id ?? null });
  store.addEvents(seeds.map((b) => ({ event_id: crypto.randomUUID(), user_key: uk, book_id: b,   // 서버 자동 기록 흉내
    event_type: "library_add", ts, surface: "onboarding", payload: {} })));
  return { user_key: uk, preference_snapshot_id: snap.snapshot_id, created_at: snap.created_at,
    cell, snapshots_count: store.snapshotsOf(uk).length, persona };
}
/** badges.py 1:1. light 는 Should 라 만들지 않는다. review 는 3단 폴백(3단 = bestseller). */
function badgeFor(card, criterion, seedAuthors, seedPublishers) {
  const best = card.pop_rank != null ? { type: "bestseller", text: `인기 ${card.pop_rank}위` } : null;
  const n = card.review_count ?? 0;
  if (criterion === "bestseller") return best;
  if (criterion === "review") {
    if (card.average_rating != null && n >= REVIEW_MIN_COUNT) return { type: "review", text: `★${card.average_rating.toFixed(1)}, 리뷰 ${n}` };
    return n >= REVIEW_MIN_COUNT_NO_RATING ? { type: "review", text: `리뷰 ${n}` } : best;
  }
  if (criterion === "author" && seedAuthors.has(card.authors)) return { type: "author", text: `${card.authors} 작가` };
  if (criterion === "publisher" && seedPublishers.has(card.publisher)) return { type: "publisher", text: `${card.publisher} 출판` };
  if (criterion === "buzz" && card.millie_label) return { type: "buzz", text: String(card.millie_label) };
  return null;
}
function attachBadges(rows, criterion, seeds) {
  if (!criterion) return;
  const cards = (seeds || []).map(byId).filter(Boolean);
  const au = new Set(cards.map((c) => c.authors).filter(Boolean)), pu = new Set(cards.map((c) => c.publisher).filter(Boolean));
  for (const r of rows) for (const i of r.items) if (index.has(i.book_id)) i.badge = badgeFor(index.get(i.book_id), criterion, au, pu);
}
/** ItemOut 13키 화이트리스트 — 카탈로그 원문을 그대로 흘리지 않는다(T-06-03-04). */
const item = (card, position, source, reason = null, score = null) => ({
  book_id: card.book_id, score: score ?? ROW_SIZE - position, source, reason, title: card.title ?? null,
  authors: card.authors ?? null, image_url: card.image_url ?? null, position, badge: null, source_channels: source ? [source] : [],
  book_format: card.book_format ?? null, difficulty: card.difficulty ?? null, subcategories: card.subcategories ?? [] });
const row = (id, title, purpose, items, subtitle = null) => ({ row_id: id, title, purpose, items, subtitle, channel_mix: mix(items) });
/** rows.neighbor_row — 앵커·after_completion 공용. 자격·중복·시드를 뺀 가중 상위 12, 비면 null. */
function neighborRow(rowId, title, subtitle, seed, exclude, purpose = "discover") {
  const picked = (nbrs[String(seed)] || []).slice(0, ANCHOR_NEIGHBORS)
    .filter(([d]) => index.has(d) && !exclude.has(d) && d !== Number(seed)).slice(0, ROW_SIZE);
  return picked.length ? row(rowId, title, purpose,
    picked.map(([d, w], i) => item(index.get(d), i, "content", title, w)), subtitle) : null;
}
const popRow = (id, title, purpose, cards, ex) => row(id, title, purpose, cards.filter((b) => !ex.has(b.book_id)).slice(0, ROW_SIZE).map((b, i) => item(b, i, "popularity")));
// source 없음 — rows.personal_rows 의 continue ScoredItem 과 같은 형태
const continueRow = (ids, ex) => row("continue_reading", T_CONTINUE, "resume", ids.filter((b) => index.has(b) && !ex.has(b)).slice(0, ROW_SIZE).map((b, i) => item(index.get(b), i, null)));
/** rows.fresh_row — 선택 카테고리 밖의 미선택 카테고리 인기 라운드로빈. */
function freshRow(categories, exclude) {
  const chosen = new Set(categories || []), others = allCats.filter((c) => !chosen.has(c));
  const pools = (others.length ? others : allCats).map((c) => byPop([c]).slice(0, FRESH_POOL_N));
  const out = [], used = new Set(exclude);
  for (let i = 0; out.length < ROW_SIZE && i < FRESH_POOL_N; i += 1) for (const p of pools)
    if (p[i] && !used.has(p[i].book_id) && out.length < ROW_SIZE) { used.add(p[i].book_id); out.push(p[i]); }
  return row("fresh_picks", T_FRESH, "explore", out.map((b, i) => item(b, i, "popularity")));
}
/** 카테고리 라운드로빈 — hybrid_div 의 다양성이 눈에 보이게 한다(재순위화가 아니라 표시 순서). */
function interleave(cards) {
  const g = new Map();
  for (const b of cards) { const k = (b.categories || [])[0] || "-"; g.set(k, [...(g.get(k) || []), b]); }
  const gs = [...g.values()], out = [];
  for (let i = 0; i < cards.length && out.length < cards.length; i += 1) for (const a of gs) if (a[i]) out.push(a[i]);
  return out;   // 카테고리별 큐를 1권씩 번갈아 꺼낸 순서
}
function shelfRow(variant, snap, persona, exclude) {
  let picked = [];
  if (variant !== "pop") {                      // 시드 이웃 합집합(weight 내림차순) — 테이블 조회만
    const sc = new Map();
    for (const s of snap.seeds || []) for (const [d, w] of (nbrs[String(s)] || []).slice(0, ANCHOR_NEIGHBORS))
      if (index.has(d) && !exclude.has(d)) sc.set(d, Math.max(sc.get(d) ?? 0, w));
    let cards = [...sc.entries()].sort((a, b) => b[1] - a[1]).map(([d]) => index.get(d));
    cards = prioritize(cards, snap.subcategories);   // Ranking 단계 가점에 대응 — 다양성이 그 위에서 판단한다
    if (variant === "hybrid_div") cards = interleave(cards);
    picked = cards.slice(0, ROW_SIZE).map((b) => [b, "content"]);
  }
  const have = new Set(picked.map(([b]) => b.book_id));
  for (const b of byPop(snap.categories)) {     // 부족분은 선택 카테고리 인기로 보충
    if (picked.length >= ROW_SIZE) break;
    if (!exclude.has(b.book_id) && !have.has(b.book_id)) { have.add(b.book_id); picked.push([b, "popularity"]); }
  }
  return row("persona_shelf", persona?.name ? `${persona.name}의 서가` : T_PERSONA_DEFAULT, "discover",
    picked.map(([b, src], i) => item(b, i, src)));
}
const normalizeTitle = (s) => String(s ?? "").replace(/[^\p{L}\p{N}_]/gu, "").toLowerCase();
/** compose.dedup_rows — 렌더 순서 앞 행 우선, book_id 와 정규화 제목 둘 다. 빈 행도 남긴다. */
function dedup(rows) {
  const ids = new Set(), titles = new Set();
  let removed = 0;                     // dedup_removed 로 응답에 실린다
  const out = rows.map((r) => {
    const kept = [];
    for (const i of r.items) {
      const key = normalizeTitle(i.title);
      if (ids.has(i.book_id) || (key && titles.has(key))) { removed += 1; continue; }
      ids.add(i.book_id); if (key) titles.add(key);
      kept.push({ ...i, position: kept.length });   // position 재부여
    }
    return { ...r, items: kept, channel_mix: mix(kept) };
  });
  return [out, removed];
}
/** 표시 규칙 — 스코어링이 아니라 U_t 설명용 숫자(06-CONTEXT D-01). */
function weightsFor(uk, snaps, consent, now) {
  if (!consent || !snaps.length) return { alpha: 0, beta: 0, gamma: 0 };
  const n = store.nHistory(uk), b = 0.2 + 0.05 * n;
  let a = Math.max(0.2, 0.7 - 0.05 * n), g = 0.1;
  if (store.sessionActive(uk, now)) g += 0.1;
  if (snaps.length >= 2 && Date.now() - Date.parse(snaps[0].created_at) < 86400e3) a += 0.15;
  const s = a + b + g, r3 = (x) => Math.round((x / s) * 1000) / 1000;   return { alpha: r3(a), beta: r3(b), gamma: r3(g) };
}
export function getRecommend({ userKey, snapshotId, model, k = 40, context } = {}) {
  const uk = userKey || "", now = new Date().toISOString();
  const snaps = store.snapshotsOf(uk), user = store.getUser(uk);
  const snap = (snapshotId && snaps.find((s) => s.snapshot_id === snapshotId)) || snaps[0] || null;
  const personalized = !!(user?.consent && snap && snap.consent);
  const forced = VARIANTS.includes(model);
  const variant = forced ? model : (user?.cell === "B" ? "hybrid_div" : "hybrid");
  const rows = [], exclude = new Set(personalized ? (snap.seeds || []) : []);
  const eat = (r) => { if (r) { rows.push(r); for (const i of r.items) exclude.add(i.book_id); } };
  let level = 0, modelVersion = variant + "_v1";
  if (!personalized) {                                     // SERV-08 비개인화 2행
    [level, modelVersion] = [3, "fallback_v1"];
    eat(popRow("trending", T_TREND, "fallback", pool, exclude));
    eat(freshRow([], exclude));
  } else {
    const seeds = snap.seeds || [], seed1 = seeds[0], done = store.lastCompleted(uk);
    if (done && byId(done))                                // D-13: after_completion 이 최상단
      eat(neighborRow("after_completion", TITLE_AFTER(byId(done).title), null, done, exclude, "resume"));
    eat(continueRow(store.continueIds(uk), exclude));
    if (seed1 != null) eat(neighborRow(`anchor_${seed1}`,
      REASON_ANCHOR(byId(seed1)?.title ?? String(seed1)), SUBTITLE_ANCHOR, seed1, exclude));
    eat(shelfRow(variant, snap, snap.persona, exclude));
    eat(popRow("trending", T_TREND, "fallback", pool, exclude));
    eat(freshRow(snap.categories, exclude));
  }
  const [deduped, dedupRemoved] = dedup(rows);
  if (personalized) attachBadges(deduped, snap.criterion, snap.seeds);
  const res = {
    recommendation_id: "rec_" + store.hex6(), model_version: modelVersion, forced, fallback_level: level,
    preference_snapshot_id: personalized ? snap.snapshot_id : null, user_key: uk || null,
    cell: user?.cell ?? null, context: context ?? snap?.reading_time ?? null,
    latency_ms: LATENCY.total, latency_breakdown: { ...LATENCY }, dedup_removed: dedupRemoved,
    user_state_weights: weightsFor(uk, snaps, personalized, now), nearline_lag_s: NEARLINE_LAG_S,
    items: personalized ? deduped.flatMap((r) => r.items).slice(0, k) : [], rows: deduped,
  };
  store.logRecommendation({ recommendation_id: res.recommendation_id, user_key: uk, ts: now,
    model_version: res.model_version, cell: res.cell, forced, fallback_level: level,
    latency_ms: res.latency_ms, latency_breakdown: { ...LATENCY },
    rows: deduped.flatMap((r) => r.items.map((i) => ({ row_id: r.row_id, book_id: i.book_id, position: i.position }))),
    n_items: deduped.reduce((a, r) => a + r.items.length, 0) });
  return res;
}
export function postEvents(events) { return store.addEvents(events); }
export function postRating(body) {
  store.addRating(body);   // rating 이벤트도 함께 — 대시보드 집계가 서버와 같아진다
  store.addEvents([{ event_id: crypto.randomUUID(), user_key: body.user_key, book_id: body.book_id,
    event_type: "rating", ts: body.ts, recommendation_id: body.recommendation_id ?? null, payload: { stars: String(body.stars) } }]);
  return { ok: true, rating_id: body.rating_id };
}
export async function getUserState(userKey) {
  const uk = userKey || "", user = store.getUser(uk), snaps = store.snapshotsOf(uk), lib = store.library(uk);
  const card = (b) => ({ book_id: b, title: byId(b)?.title ?? null, authors: byId(b)?.authors ?? null, image_url: byId(b)?.image_url ?? null });
  return { user_key: uk, consent: user?.consent ?? false, cell: user?.cell ?? await store.cellFor(uk),
    is_new: snaps.length <= 1, nearline_lag_s: NEARLINE_LAG_S,
    library: { added: lib.added.map(card), reading: lib.reading.map(card), completed: lib.completed.map(card) },
    snapshots: snaps.map((s, i) => ({ snapshot_id: s.snapshot_id, created_at: s.created_at,
      categories: s.categories || [], criterion: s.criterion ?? null, active: i === 0 })),
    user_state_weights: weightsFor(uk, snaps, !!user?.consent, new Date().toISOString()) };
}
export function getUserData(userKey) { return store.userData(userKey); }
export function deletePersonalization(userKey) { return store.deleteUser(userKey); }
export function getDashboard() { return store.dashboard(new Date().toISOString()); }
export function getShowcase() { return showcaseData; }
