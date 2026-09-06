// fetch 래퍼. 부록 C 의 13개 함수가 source=api|mock 양쪽을 덮는다 — 응답 형태는 항상 serving/schemas.py.
import * as mock from "./mock.js";

const API_BASE = "";           // 같은 origin — FastAPI 가 demo/ 를 / 에 서빙(../.claude/rules/demo.md). ?api=<URL> 로만 덮어쓴다
const TIMEOUT_MS = 4000;       // 서버가 늦어도 메인 화면은 4초 안에 fallback(main 설계서 §7)
const qs = new URLSearchParams(location.search);

export const config = {
  source: ["api", "mock"].includes(qs.get("source")) ? qs.get("source") : null,
  apiBase: (qs.get("api") || API_BASE).replace(/\/$/, ""),
  capture: ["1", "2"].includes(qs.get("capture")) ? qs.get("capture") : null,
};

// 정적 인기 목록 파일조차 못 읽을 때의 최소 level 3 형태 — RecommendOut 15키를 유지해 화면이 깨지지 않는다
const FALLBACK_EMPTY = {
  recommendation_id: null, model_version: "fallback_v1", preference_snapshot_id: null,
  user_key: null, cell: null, forced: false, fallback_level: 3, context: null,
  latency_ms: 0.0, latency_breakdown: {}, user_state_weights: { alpha: 0, beta: 0, gamma: 0 },
  dedup_removed: 0, nearline_lag_s: null, items: [], rows: [],
};

/** get/post/del 공용 — AbortController 로 4초에서 끊는다. */
async function req(path, init = {}) {
  const ctl = new AbortController();
  const timer = setTimeout(() => ctl.abort(), TIMEOUT_MS);
  try {
    const res = await fetch(config.apiBase + path, {
      ...init, signal: ctl.signal,
      headers: init.body ? { "Content-Type": "application/json" } : undefined,
    });
    if (!res.ok) throw new Error(`HTTP ${res.status} ${path}`);
    return res.status === 204 ? null : await res.json();
  } finally { clearTimeout(timer); }
}

const get = (p) => req(p);
const post = (p, body) => req(p, { method: "POST", body: JSON.stringify(body) });
const del = (p) => req(p, { method: "DELETE" });
const local = (p) => fetch(p).then((r) => {
  if (!r.ok) throw new Error(`HTTP ${r.status} ${p}`);
  return r.json();
});

/** 엔드포인트별 실패 격리 — 아직 없는 경로(404)·네트워크 오류는 null(화면이 "서버 준비 중"). uncaught 0. */
const soft = (p) => p.catch((err) => { console.warn("[api]", String(err.message || err)); return null; });
/** mock 분기 공통 — 카탈로그 1회 로드 후 같은 이름의 mock 함수로 위임한다. */
const useMock = async (source) => { if (source !== "mock") return false; await mock.init(); return true; };

export async function resolveSource() {
  if (config.source) return config.source;
  try { await get("/health"); return "api"; } catch { return "mock"; }
}

export async function loadSteps() {
  return local("config/onboarding.json").then((d) => d.steps);
}

export async function health(source) {
  return (await useMock(source)) ? mock.health() : soft(get("/health"));
}

export async function loadMeta(source) {
  return (await useMock(source)) ? mock.loadMeta() : soft(get("/api/meta/onboarding"));
}

export async function getCandidates(source, { categories, subcategories = [], n = 30, userKey }) {
  if (await useMock(source)) return mock.getCandidates({ categories, subcategories, n, userKey });
  const p = new URLSearchParams({
    categories: categories.join(","), subcategories: subcategories.join(","),
    n: String(n), user_key: userKey || "",
  });
  return soft(get("/api/candidates/onboarding?" + p));
}

export async function postPreferences(source, body) {
  if (await useMock(source)) return mock.postPreferences(body);
  return soft(post("/api/preferences", body));
}

/** 이 함수만 클라이언트 fallback — 타임아웃·네트워크 오류면 정적 인기 목록으로 대체한다. */
export async function getRecommend(source, { userKey, snapshotId, model, k = 40, context }) {
  if (await useMock(source)) return mock.getRecommend({ userKey, snapshotId, model, k, context });
  const p = new URLSearchParams({ user_key: userKey || "", k: String(k) });
  if (snapshotId) p.set("snapshot_id", snapshotId);
  if (model) p.set("model", model);
  if (context) p.set("context", context);
  try {
    return await get("/api/recommend?" + p);
  } catch (err) {
    const fb = await soft(local("fallback/popular.json"));
    return { ...(fb || FALLBACK_EMPTY), client_fallback_reason: String(err.message || err) };
  }
}

export async function postEvents(source, events) {
  if (!events || !events.length) return null;
  if (await useMock(source)) return mock.postEvents(events);
  return soft(post("/api/events", { events: events.slice(0, 50) }));
}

export async function postRating(source, body) {
  if (await useMock(source)) return mock.postRating(body);
  return soft(post("/api/ratings", body));
}

export async function getUserState(source, userKey) {
  if (await useMock(source)) return mock.getUserState(userKey);
  return soft(get("/api/users/" + encodeURIComponent(userKey) + "/state"));
}

export async function getUserData(source, userKey) {
  if (await useMock(source)) return mock.getUserData(userKey);
  return soft(get("/api/users/" + encodeURIComponent(userKey) + "/data"));
}

export async function deletePersonalization(source, userKey) {
  if (await useMock(source)) return mock.deletePersonalization(userKey);
  return soft(del("/api/users/" + encodeURIComponent(userKey) + "/personalization"));
}

export async function getDashboard(source) {
  if (await useMock(source)) return mock.getDashboard();
  return soft(get("/api/dashboard"));
}

export async function getShowcase(source) {
  if (await useMock(source)) return mock.getShowcase();
  const out = await soft(get("/api/showcase"));
  // 본인 5권 정성 케이스는 빌드 시점 산출물이라 서버가 계산하지 않는다(Phase 5 보류 —
  // 임의 방문자에게 "본인이 읽은 5권"을 서버가 만들어 줄 수는 없다). 같은 이미지 안의
  // 정적 파일에서 채운다. 나머지 필드는 전부 서버 응답 그대로다.
  if (out && out.personal_case == null) {
    out.personal_case = await fetch("mock/showcase.json")
      .then((r) => (r.ok ? r.json() : null))
      .then((s) => s?.personal_case ?? null)
      .catch(() => null);
  }
  return out;
}
