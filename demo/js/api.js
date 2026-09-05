// fetch 래퍼. 같은 4개 함수가 source=api|mock 양쪽을 덮는다 — 응답 형태는 항상 백엔드 §3 계약.
import * as mock from "./mock.js";

// ▼▼ 배포 시 교체 지점 — Hugging Face Spaces 주소를 여기에 넣는다 ▼▼
const API_BASE = "https://REPLACE-ME.hf.space";
// ▲▲ 로컬 백엔드와 함께 보려면 URL에 ?api=http://localhost:8000 ▲▲

const TIMEOUT_MS = 4000;
const qs = new URLSearchParams(location.search);

export const config = {
  source: qs.get("source") || null,   // null이면 mock 파일 존재 여부로 자동 결정
  apiBase: (qs.get("api") || API_BASE).replace(/\/$/, ""),
  capture: qs.get("capture") === "1",
};

/** 서버가 늦거나 죽어도 메인 화면이 깨지지 않게 4초에서 끊는다 (설계서 §7). */
async function get(path) {
  const ctl = new AbortController();
  const timer = setTimeout(() => ctl.abort(), TIMEOUT_MS);
  try {
    const res = await fetch(config.apiBase + path, { signal: ctl.signal });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } finally {
    clearTimeout(timer);
  }
}

const local = (path) => fetch(path).then((r) => {
  if (!r.ok) throw new Error(`HTTP ${r.status} ${path}`);
  return r.json();
});

/** mock 풀을 한 번만 읽어 메모리에 둔다. 실패하면 mock 모드를 쓸 수 없다는 뜻. */
let poolReady = null;
function ensurePool() {
  if (!poolReady) {
    poolReady = local("mock/books.json").then((d) => { mock.init(d.books); return d.books; });
  }
  return poolReady;
}

/** source 결정: 명시 파라미터 우선, 없으면 mock 파일이 있으면 mock. */
export async function resolveSource() {
  if (config.source === "api" || config.source === "mock") return config.source;
  try {
    await ensurePool();
    return "mock";
  } catch {
    return "api";
  }
}

export const loadSteps = () => local("config/onboarding.json").then((d) => d.steps);

/** 시나리오 프리셋이 깨끗한 상태에서 시작하도록 mock의 스냅샷 번호를 되돌린다. */
export const resetMockState = () => mock.resetSnapshots();

export async function loadMeta(source) {
  if (source === "mock") { await ensurePool(); return local("mock/meta_onboarding.json"); }
  return get("/meta/onboarding");
}

export async function getCandidates(source, { categories, subcategories, n = 30 }) {
  if (source === "mock") { await ensurePool(); return mock.getCandidates(categories, subcategories, n); }
  const p = new URLSearchParams({ categories: categories.join(","), subcategories: subcategories.join(","), n });
  return get(`/candidates/onboarding?${p}`);
}

export async function postPreferences(source, body) {
  if (source === "mock") { await ensurePool(); return mock.postPreferences(body); }
  return post("/preferences", body);
}

/** api 모드에서 타임아웃·네트워크 오류면 정적 인기 목록으로 대체한다 (클라이언트 fallback). */
export async function getRecommend(source, args) {
  if (source === "mock") { await ensurePool(); return mock.getRecommend(args); }
  const p = new URLSearchParams({
    user_key: args.userKey || "", snapshot_id: args.snapshotId || "",
    model: args.model, context: args.context || "",
  });
  try {
    return await get(`/recommend?${p}`);
  } catch (err) {
    const fb = await local("fallback/popular.json");
    return { ...fb, client_fallback_reason: String(err.message || err) };
  }
}

export async function postEvent(source, ev) {
  if (source === "mock") return mock.postEvent(ev);
  try {
    return await post("/events", ev);
  } catch {
    return { ok: false };   // 이벤트 유실은 화면을 막지 않는다
  }
}

async function post(path, body) {
  const ctl = new AbortController();
  const timer = setTimeout(() => ctl.abort(), TIMEOUT_MS);
  try {
    const res = await fetch(config.apiBase + path, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body), signal: ctl.signal,
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } finally {
    clearTimeout(timer);
  }
}
