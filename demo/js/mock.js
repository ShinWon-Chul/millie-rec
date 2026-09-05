// mock 모드 엔진 — 서버 없이도 심사자가 고른 책에 반응하도록 계약 형태의 응답을 조립한다.
// 응답 스키마는 백엔드 문서 §3이 정본. 여기서 형태를 바꾸면 api 모드와 어긋난다.
import { josa } from "./screens/ui.js";

const PERSONAS = [
  ["오디세우스", "오디세이아", "지혜로 승리하리라!", ["경제경영", "자기계발", "IT"]],
  ["셜록 홈즈", "주홍색 연구", "사소한 것이 가장 중요하다.", ["소설", "과학", "철학"]],
  ["돈키호테", "돈키호테", "이룰 수 없는 꿈을 꾸리라!", ["인문", "역사", "사회"]],
  ["제인 에어", "제인 에어", "나는 나 자신의 주인입니다.", ["에세이/시", "라이프스타일"]],
];
const ROW_TITLES = {
  continue_reading: ["이어 읽기", "resume"],
  similar_readers: ["비슷한 독자들이 읽은 책", "discover"],
  trending: ["지금 많이 읽는 책", "fallback"],
  fresh_picks: ["새로운 발견", "explore"],
};
const N = 12;

let pool = [];
let index = new Map();
let snapSeq = 0;

const rid = (p) => p + Math.random().toString(36).slice(2, 8);
const byPop = (a, b) => b.ratings_count - a.ratings_count;
const byRating = (a, b) => b.average_rating - a.average_rating;
const byYear = (a, b) => (b.year || 0) - (a.year || 0);

export function init(books) {
  pool = books;
  index = new Map(books.map((b) => [b.book_id, b]));
}
export const byId = (id) => index.get(Number(id));
export const catalog = () => pool;
export const resetSnapshots = () => { snapSeq = 0; };

/** 선택 카테고리·세부 카테고리에 걸리는 책을 인기순으로 n권. 노출 로그 대조용 id를 발급한다. */
export function getCandidates(categories, subcategories, n = 30) {
  const cats = new Set(categories);
  const subs = new Set(subcategories);
  const hit = (b) => b.categories.some((c) => cats.has(c)) || b.subcategories.some((s) => subs.has(s));
  const picked = (cats.size || subs.size ? pool.filter(hit) : pool).slice().sort(byPop).slice(0, n);
  return {
    candidate_set_id: rid("cand_"),
    survey_variant: "v1",
    items: picked.map((b, i) => ({ ...b, position: i })),
  };
}

function personaFor(categories, criterion) {
  const hit = PERSONAS.find((p) => categories.some((c) => p[3].includes(c))) || PERSONAS[0];
  const [name, work, quote] = hit;
  const head = categories.length > 1
    ? `${categories[0]}${josa(categories[0], "과", "와")} ${categories[1]}`
    : categories[0] || "다양한 분야";
  const crit = criterion || "나만의 기준";
  return {
    name, work, quote,
    description: `회원님은 ${head}${josa(head, "을", "를")} 즐기고, `
      + `${crit}${josa(crit, "으로", "로")} 책을 고르는 독서가입니다.`,
  };
}

/** 스냅샷은 추가만 한다 (Preference Refresh ≠ Profile Reset). */
export function postPreferences({ prefs, consent, userKey }) {
  snapSeq += 1;
  return {
    user_key: userKey || rid("u_"),
    preference_snapshot_id: `snap_${String(snapSeq).padStart(2, "0")}`,
    created_at: new Date().toISOString(),
    consent,
    persona: personaFor(prefs.categories, prefs.criterion),
  };
}

const reviewsKo = (n) => (n >= 10000 ? `${Math.round(n / 10000)}만`
  : n >= 1000 ? `${Math.round(n / 1000)}천` : String(n));

/** §4-4: S3 선택 기준이 배지 타입을 결정한다 (Netflix Artwork Personalization). */
function badgeFor(book, criterion, seedAuthors) {
  if (criterion === "베스트셀러") return { type: "bestseller", text: `인기 ${book.pop_rank}위` };
  if (criterion === "리뷰, 별점 등 대중의 평가") {
    return { type: "rating", text: `★ ${book.average_rating.toFixed(2)} · 리뷰 ${reviewsKo(book.ratings_count)}` };
  }
  if (criterion === "좋아하는 작가") {
    const first = String(book.authors).split(",")[0].trim();
    return seedAuthors.has(first) ? { type: "author", text: `${first}의 다른 책` } : null;
  }
  if (criterion === "화제작 (SNS,셀럽 추천, 수상도서)") {
    return { type: "buzz", text: (book.year || 0) >= 2010 ? "요즘 화제" : "수상작" };
  }
  return null; // 좋아하는 출판사 — Goodbooks-10k에 출판사 컬럼이 없어 배지 생략
}

/** 카테고리 라운드로빈 — hybrid_div의 다양성이 눈에 보이도록 섞는다. */
function interleave(items) {
  const groups = new Map();
  for (const b of items) {
    const k = b.categories[0] || "-";
    if (!groups.has(k)) groups.set(k, []);
    groups.get(k).push(b);
  }
  const out = [];
  for (let guard = 0; out.length < items.length && guard < items.length + 1; guard += 1) {
    let moved = false;
    for (const g of groups.values()) if (g.length) { out.push(g.shift()); moved = true; }
    if (!moved) break;
  }
  return out;
}

function weightsFor({ consent, readerOpens, resetBoost }) {
  if (consent === false) return { alpha: 0, beta: 0, gamma: 0 };
  // reader_open 1회당 장기 취향 β가 오르고 explicit α가 내려간다. 재설정 직후에만 α가 일시 상승.
  const alpha = Math.max(0.1, 0.6 + (resetBoost ? 0.15 : 0) - readerOpens * 0.05);
  return { alpha: +alpha.toFixed(2), beta: +(0.3 + readerOpens * 0.05).toFixed(2), gamma: 0.1 };
}

function mkRow(rowId, items, channels, criterion, seedAuthors, reason, override = {}) {
  const [title, purpose] = ROW_TITLES[rowId];
  return {
    row_id: rowId, title, purpose, ...override,
    channel_mix: { content: 0, itemknn: 0, popularity: 0, [channels[0]]: items.length },
    items: items.map((b, i) => ({
      book_id: b.book_id, title: b.title, authors: b.authors, image_url: b.image_url,
      format: b.format, position: i, score: +(0.9 - i * 0.03).toFixed(3),
      source_channels: channels, badge: badgeFor(b, criterion, seedAuthors),
      reason: reason || null,
    })),
  };
}

export function getRecommend({ model, prefs, history, consent, resetBoost, snapshotId, persona }) {
  const criterion = prefs.criterion;
  const seeds = prefs.seedBooks.map(byId).filter(Boolean);
  const seedIds = new Set(seeds.map((b) => b.book_id));
  const seedAuthors = new Set(seeds.map((b) => String(b.authors).split(",")[0].trim()));
  const seedCats = new Set(seeds.flatMap((b) => b.categories));
  const opens = history.readerOpens.length;
  const jitter = () => Math.round((Math.random() - 0.5) * 6);

  let rows = [];
  if (consent === false) {
    rows = [mkRow("trending", pool.slice().sort(byPop).slice(0, N), ["popularity"], null, seedAuthors)];
  } else {
    const inCat = pool.filter((b) => !seedIds.has(b.book_id) && b.categories.some((c) => seedCats.has(c)));
    const rest = pool.filter((b) => !seedIds.has(b.book_id) && !b.categories.some((c) => seedCats.has(c)));
    let shelf = inCat.slice().sort(byRating);
    let similar = rest.slice().sort(byPop);
    let fresh = pool.slice().sort(byYear);
    if (model === "pop") { shelf = similar = fresh = pool.slice().sort(byPop); }
    if (model === "hybrid_div") { shelf = interleave(shelf); similar = interleave(similar); }

    const last = history.readerOpens[history.readerOpens.length - 1];
    if (last) {
      const b = byId(last);
      if (b) rows.push(mkRow("continue_reading", [b], ["content"], criterion, seedAuthors, "읽던 곳부터 이어서"));
    }
    if (history.lastCompleted) {
      const done = byId(history.lastCompleted);
      const near = pool.filter((b) => b.book_id !== done?.book_id
        && b.categories.some((c) => (done?.categories || []).includes(c))).sort(byRating).slice(0, N);
      if (done && near.length) {
        rows.push(mkRow("similar_readers", near, ["itemknn"], criterion, seedAuthors, null, {
          row_id: "after_completion", title: `『${done.title}』을 완독하셨네요, 다음은`, purpose: "resume",
        }));
      }
    }
    if (model !== "cf" && shelf.length) {
      const seedTitle = seeds[0]?.title;
      rows.push(mkRow("similar_readers", shelf.slice(0, N), ["content"], criterion, seedAuthors,
        seedTitle ? `『${seedTitle}』을 좋아하셨다면` : null,
        { row_id: "persona_shelf", title: `${persona?.name || "나"}의 서가`, purpose: "discover" }));
    }
    rows.push(mkRow("similar_readers", similar.slice(0, N), ["itemknn"], criterion, seedAuthors));
    rows.push(mkRow("trending", pool.slice().sort(byPop).slice(0, N), ["popularity"], criterion, seedAuthors));
    rows.push(mkRow("fresh_picks", fresh.slice(0, N), ["content"], criterion, seedAuthors));
  }

  // 행 간 중복 제거 — 인스펙터가 dedup_removed로 보여준다
  const seen = new Set();
  let removed = 0;
  for (const row of rows) {
    row.items = row.items.filter((it) => {
      if (seen.has(it.book_id)) { removed += 1; return false; }
      seen.add(it.book_id);
      return true;
    }).map((it, i) => ({ ...it, position: i }));
    for (const k of ["content", "itemknn", "popularity"]) {
      if (row.channel_mix[k]) row.channel_mix[k] = row.items.length;
    }
  }
  // 고정값 + ±3ms 지터. 실제 서버 측정값이 아니므로 PDF 숫자로 쓰지 않는다.
  const lat = { feature: 3, retrieval: 21, ranking: 14, rerank: 4, compose: 2 };
  for (const k of Object.keys(lat)) lat[k] = Math.max(1, lat[k] + jitter());
  lat.total = Object.values(lat).reduce((a, b) => a + b, 0);
  return {
    recommendation_id: rid("rec_"), model_version: `${model}_mock`,
    preference_snapshot_id: snapshotId, user_key: null,
    fallback_level: consent === false ? 3 : 0, cell: "B",
    latency_ms: lat,
    user_state_weights: weightsFor({ consent, readerOpens: opens, resetBoost }),
    dedup_removed: removed, rows,
  };
}

export const postEvent = () => ({ ok: true });
