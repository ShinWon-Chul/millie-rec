"""로컬 bench(D-11): user_key 50 → warmup 50 → 500 요청 → results/latency.json. 표준 urllib 만."""

import argparse
import json
import logging
import random
import subprocess
import urllib.parse
import urllib.request
import uuid
from collections import Counter
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter

from millie_rec.contracts import DIR_RESULTS, FALLBACK_GLOBAL_POP, ROOT, SEED

log = logging.getLogger(__name__)

BASE_URL = "http://localhost:8000"  # 로컬 uvicorn 1 worker (../.claude/rules/serving.md 숫자 규칙)
N_USERS, WARMUP, N_REQUESTS, K = 50, 50, 500, 40  # D-11 모집단
OUT_PATH = DIR_RESULTS / "latency.json"  # PDF 의 유일한 지연 숫자
TIMEOUT_S, SEEDS_PER_USER, CAND_N, CATS_MAX = 10.0, 5, 60, 3
SERVE_HINT, UA, CRITERION = "make serve 를 먼저 실행하세요", "millie-rec-bench/0.1", "bestseller"
PRINT_KEYS = ("p50", "p95", "p99", "n", "fallback_levels")
DESC = "로컬 p95 bench → results/latency.json (D-11)"


def git_sha() -> str | None:
    """짧은 sha. evaluation/report.py 와 같은 함수의 중복 정의 — star 의존이라 import 불가."""
    cmd = ["git", "rev-parse", "--short", "HEAD"]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, check=False, cwd=ROOT, timeout=5)
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout.strip() or None if out.returncode == 0 else None


def percentile(sorted_ms: Sequence[float], p: float) -> float:
    """정렬 표본의 p 백분위 — ceil(p/100*n)-1 인덱스(정수 올림). 빈 표본은 0.0."""
    n = len(sorted_ms)
    if not n:
        return 0.0
    return float(sorted_ms[min(n - 1, max(0, -(-int(p * n) // 100) - 1))])


def summarize(
    records: Sequence[tuple[float, int, str]],
    *,
    n_users: int,
    warmup: int,
    k: int,
    base_url: str,
    n_books: int | None,
    created_at: str,
    git_sha: str | None,
    seed: int = SEED,
) -> dict:
    """(ms, fallback_level, model_version) 표본 → latency.json 페이로드. user_key 자리가 없다."""
    ms = sorted(r[0] for r in records)
    seen = Counter(str(level) for _ms, level, _v in records)
    levels = {str(lv): seen.get(str(lv), 0) for lv in range(FALLBACK_GLOBAL_POP + 1)}
    pcts = {f"p{p}": percentile(ms, p) for p in (50, 95, 99)}
    counts = {"n": len(records), "warmup": warmup, "users": n_users, "k": k, "seed": seed}
    dist = {"fallback_levels": levels, "variants": dict(Counter(v for _m, _l, v in records))}
    origin = {"created_at": created_at, "git_sha": git_sha, "base_url": base_url}
    return {**pcts, **counts, **dist, "catalog": {"n_books": n_books}, **origin}


def _req(url: str, body: dict | None = None) -> dict:
    """GET(body 없음) 또는 POST JSON. 예외는 호출자가 본다 — bench 는 CLI 다."""
    data = None if body is None else json.dumps(body).encode("utf-8")
    headers = {"User-Agent": UA, "Content-Type": "application/json"}
    req = urllib.request.Request(url, data, headers)
    with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
        return json.loads(resp.read())


def make_users(base: str, n: int, rng: random.Random) -> list[str]:
    """POST /api/preferences × n → user_key 목록. 시드 5권은 서버 후보 응답에서만 뽑는다(D-11)."""
    meta = _req(f"{base}/api/meta/onboarding")
    named = [c["name"] for c in meta["categories"] if c.get("supported")]
    cats = (named or [c["name"] for c in meta["categories"]])[:CATS_MAX]
    query = urllib.parse.urlencode({"categories": ",".join(cats), "n": CAND_N})
    cand = _req(f"{base}/api/candidates/onboarding?{query}")
    pool = [item["book_id"] for item in cand["items"]]
    keys = [uuid.uuid4().hex for _ in range(n)]
    for key in keys:
        seeds = rng.sample(pool, min(SEEDS_PER_USER, len(pool)))
        body = {"user_key": key, "categories": cats, "criterion": CRITERION, "seeds": seeds}
        _req(f"{base}/api/preferences", {**body, "candidate_set_id": cand["candidate_set_id"]})
    return keys


def run(
    base: str,
    *,
    n_users: int,
    warmup: int,
    n_requests: int,
    k: int,
    out: Path,
    seed: int,
    n_books: int | None = None,
) -> dict:
    """서버 확인 → user_key 생성 → warmup → 측정 → latency.json. 서버 없으면 안내 후 종료 1."""
    try:
        _req(f"{base}/health")
    except OSError:  # urllib.error.URLError 는 OSError 하위 — 닫힌 포트·미기동 전부
        print(SERVE_HINT)
        raise SystemExit(1) from None
    keys = make_users(base, n_users, random.Random(seed))
    samples = []
    for i in range(warmup + n_requests):
        t0 = perf_counter()
        d = _req(f"{base}/api/recommend?user_key={keys[i % len(keys)]}&k={k}")
        elapsed = (perf_counter() - t0) * 1000  # 클라이언트 측 전체 응답 시간 = 게이트 기준
        samples.append((elapsed, int(d["fallback_level"]), str(d["model_version"])))
    now = datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
    kw = dict(n_users=n_users, warmup=warmup, k=k, base_url=base, n_books=n_books, seed=seed)
    payload = summarize(samples[warmup:], created_at=now, git_sha=git_sha(), **kw)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    log.info("bench n=%d p50=%.1f p95=%.1f → %s", payload["n"], payload["p50"], payload["p95"], out)
    return payload


def build_parser() -> argparse.ArgumentParser:
    """인자 없이 돌아야 한다(Makefile bench 타깃) — 전부 기본값."""
    ap = argparse.ArgumentParser(prog="millie_rec.serving.bench", description=DESC)
    ap.add_argument("--base", default=BASE_URL)
    ap.add_argument("--out", type=Path, default=OUT_PATH)
    ints = (("--users", N_USERS), ("--warmup", WARMUP), ("--n", N_REQUESTS), ("--k", K))
    for flag, default in (*ints, ("--seed", SEED), ("--n-books", None)):
        ap.add_argument(flag, type=int, default=default)
    return ap


def main(argv: list[str] | None = None) -> None:
    """make bench 진입점 — 요약 5개를 stdout 에 한 줄로."""
    a = build_parser().parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    kw = dict(n_users=a.users, warmup=a.warmup, n_requests=a.n, k=a.k, out=a.out, seed=a.seed)
    payload = run(a.base, n_books=a.n_books, **kw)
    print(json.dumps({key: payload[key] for key in PRINT_KEYS}, ensure_ascii=False))


if __name__ == "__main__":
    main()
