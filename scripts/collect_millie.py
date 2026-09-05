"""밀리 공개 도서 페이지 수집기 — sitemap 발견 → 헤드리스 렌더 → JSONL 체크포인트.

설계: `.assets/설계서/데이터 소스/02_밀리_데이터_적재_계획.md` §7.
HTML 은 저장하지 않는다. 파서 dict + 메타만 `data/raw/millie_pages.jsonl` 에 append 한다.

실행 (playwright 는 dev 전용, 런타임 이미지에 포함하지 않는다):

    uv run --with playwright playwright install chromium        # 최초 1회
    uv run --with playwright python scripts/collect_millie.py --limit 20 --no-expand
    uv run --with playwright python scripts/collect_millie.py   # 전량(≈70분)

예절: 단일 스레드 · 요청 간 2.5초 · UA 고정 · HTTP 4xx 3연속 시 즉시 중단.
멱등: 기존 JSONL 의 millie_id 는 건너뛴다 → 중단 후 같은 명령으로 재시작.
"""

import argparse
import json
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter, deque
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from millie_parse import extract_book_links, parse_book_text  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
JSONL = RAW / "millie_pages.jsonl"
CATALOG = RAW / "catalog_urls.txt"
DISCOVERED = RAW / "discovered_urls.txt"
LOG = RAW / "collect_millie.log"

BASE = "https://www.millie.co.kr"
UA = "millie-rec-demo-assignment/0.1 (+eddy@cdri.pro)"
AWARDS = (f"{BASE}/v4/awards/2025/bestseller", f"{BASE}/v4/awards/2025/result")
DELAY_S = 2.5
TIMEOUT_MS = 20000
MAX_4XX_STREAK = 3


def book_url(millie_id: str) -> str:
    return f"{BASE}/v4/book/{millie_id}"


class Log:
    """stdout + data/raw/collect_millie.log 동시 기록."""

    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._fh = path.open("a", encoding="utf-8")

    def __call__(self, msg: str) -> None:
        line = f"{datetime.now(UTC).isoformat(timespec='seconds')} {msg}"
        print(line, flush=True)
        self._fh.write(line + "\n")
        self._fh.flush()

    def close(self) -> None:
        self._fh.close()


def _get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310
        return resp.read()


def _locs(xml_bytes: bytes) -> list[str]:
    root = ET.fromstring(xml_bytes)
    return [el.text.strip() for el in root.iter() if el.tag.endswith("loc") and el.text]


def discover_from_sitemap(log: Log) -> list[str]:
    """sitemap.xml → sitemap_book_*.xml → 고유 millie_id (사전순)."""
    children = [u for u in _locs(_get(f"{BASE}/sitemap.xml")) if "sitemap_book_" in u]
    log(f"sitemap: 도서 sitemap {len(children)}개")
    ids: set[str] = set()
    for url in children:
        found = extract_book_links(_locs(_get(url)))
        ids.update(found)
        log(f"sitemap: {url.rsplit('/', 1)[-1]} → {len(found)}건 (누적 고유 {len(ids)})")
        time.sleep(DELAY_S)
    out = sorted(ids)
    CATALOG.parent.mkdir(parents=True, exist_ok=True)
    CATALOG.write_text("\n".join(book_url(i) for i in out) + "\n", encoding="utf-8")
    log(f"sitemap: 고유 {len(out)}건 → {CATALOG.relative_to(ROOT)}")
    return out


def load_done() -> set[str]:
    if not JSONL.exists():
        return set()
    done = set()
    for line in JSONL.read_text(encoding="utf-8").splitlines():
        if line.strip():
            mid = json.loads(line).get("millie_id")
            if mid:
                done.add(mid)
    return done


def append_discovered(rows: list[tuple[str, str]]) -> None:
    with DISCOVERED.open("a", encoding="utf-8") as fh:
        for mid, source in rows:
            fh.write(f"{mid}\t{book_url(mid)}\t{source}\n")


# 표지 URL: og:image 우선, 없으면 JSON-LD Book/Product 의 image. 핫링크만 저장(다운로드 없음).
_COVER_JS = """() => {
  const og = document.querySelector('meta[property="og:image"]');
  if (og && og.content) return og.content;
  for (const s of document.querySelectorAll('script[type="application/ld+json"]')) {
    try {
      const parsed = JSON.parse(s.textContent);
      for (const o of (Array.isArray(parsed) ? parsed : [parsed])) {
        if (o && (o['@type'] === 'Book' || o['@type'] === 'Product') && o.image)
          return Array.isArray(o.image) ? o.image[0] : o.image;
      }
    } catch (e) { /* 잘못된 JSON-LD 는 건너뛴다 */ }
  }
  return null;
}"""


def render(page, url: str) -> tuple[str, list[str], int | None, str | None]:
    """페이지 1건 렌더 → (body 텍스트, book href 목록, HTTP status, 표지 URL)."""
    resp = page.goto(url, wait_until="networkidle", timeout=TIMEOUT_MS)
    for _ in range(10):
        page.mouse.wheel(0, 4000)
        page.wait_for_timeout(120)
    page.wait_for_timeout(800)
    hrefs = page.eval_on_selector_all(
        'a[href*="/v4/book/"]', "els => els.map(e => e.getAttribute('href'))"
    )
    return (
        page.inner_text("body"),
        [h for h in hrefs if h],
        (resp.status if resp else None),
        page.evaluate(_COVER_JS),
    )


def collect(limit: int | None, expand: bool) -> None:
    from playwright.sync_api import sync_playwright

    log = Log(LOG)
    started = time.time()
    sitemap_ids = discover_from_sitemap(log)
    done = load_done()
    log(f"체크포인트: 기존 {len(done)}건 수집됨 → skip")

    seen = set(sitemap_ids)
    source = dict.fromkeys(sitemap_ids, "sitemap")
    frontier: deque[str] = deque(i for i in sitemap_ids if i not in done)
    # 재시작 시 이전 실행에서 발견했지만 아직 수집하지 않은 id 를 프론티어에 되살린다.
    # (수집된 페이지는 다시 렌더하지 않으므로, 복원하지 않으면 그 링크들이 영구 유실된다)
    if DISCOVERED.exists():
        restored = 0
        for line in DISCOVERED.read_text(encoding="utf-8").splitlines():
            parts = line.split("\t")
            if not parts or not parts[0] or parts[0] in seen:
                continue
            seen.add(parts[0])
            source[parts[0]] = parts[-1] if len(parts) > 1 else "discovered"
            if parts[0] not in done:
                frontier.append(parts[0])
                restored += 1
        log(f"체크포인트: 이전 발견분 {restored}건을 프론티어에 복원")
    stats = {"collected": 0, "skipped": len(done), "failed": 0, "new_from_expansion": 0}
    streak_4xx = 0

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        ctx = browser.new_context(user_agent=UA)
        page = ctx.new_page()

        if expand:
            for url in AWARDS:
                try:
                    _, hrefs, _, _ = render(page, url)
                except Exception as exc:  # noqa: BLE001
                    log(f"awards FAIL {url}: {type(exc).__name__}")
                    continue
                new = [i for i in extract_book_links(hrefs) if i not in seen]
                for mid in new:
                    seen.add(mid)
                    source[mid] = "awards"
                    frontier.append(mid)
                append_discovered([(i, "awards") for i in new])
                stats["new_from_expansion"] += len(new)
                log(f"awards {url.rsplit('/', 1)[-1]}: href {len(hrefs)} → 신규 {len(new)}")
                time.sleep(DELAY_S)

        while frontier:
            if limit is not None and stats["collected"] >= limit:
                log(f"--limit {limit} 도달 → 중단")
                break
            mid = frontier.popleft()
            if mid in done:
                continue
            url = book_url(mid)
            t0 = time.time()
            text = hrefs = status = cover = None
            for attempt in (1, 2):
                try:
                    text, hrefs, status, cover = render(page, url)
                    break
                except Exception as exc:  # noqa: BLE001
                    log(f"  retry {attempt} {mid}: {type(exc).__name__}: {exc}")
                    time.sleep(DELAY_S)
            if text is None:
                stats["failed"] += 1
                log(f"FAIL {mid} (2회 실패, skip)")
                time.sleep(DELAY_S)
                continue

            if status is not None and 400 <= status < 500:
                streak_4xx += 1
                if streak_4xx >= MAX_4XX_STREAK:
                    log(f"STOP_4xx {mid} status={status} — 4xx {streak_4xx}연속, 즉시 중단")
                    break
            else:
                streak_4xx = 0

            rec = parse_book_text(text, url)
            best = extract_book_links(hrefs)
            rec.update(
                image_url=cover,
                status=status,
                collected_at=datetime.now(UTC).isoformat(timespec="seconds"),
                best_links=best,
                source=source.get(mid, "sitemap"),
            )
            with JSONL.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            done.add(mid)
            stats["collected"] += 1

            if expand:
                new = [i for i in best if i not in seen]
                for nid in new:
                    seen.add(nid)
                    source[nid] = f"best:{mid}"
                    frontier.append(nid)
                if new:
                    append_discovered([(i, f"best:{mid}") for i in new])
                    stats["new_from_expansion"] += len(new)

            log(
                f"{stats['collected']}/{len(seen)} {mid} status={status} "
                f"cat={rec['category']} {time.time() - t0:.1f}s "
                f"(frontier {len(frontier)})"
            )
            time.sleep(DELAY_S)

        ctx.close()
        browser.close()

    # 발견 출처별 id 수 (상한 없음 — 새 링크가 안 나올 때까지 폐쇄, 절대 잘라내지 않는다)
    by_source = Counter("best" if s.startswith("best:") else s for s in (source[i] for i in seen))
    log("DISCOVERY " + " · ".join(f"{k} {v}" for k, v in sorted(by_source.items())))
    log(
        f"SUMMARY 발견 {len(seen)} (sitemap {len(sitemap_ids)} + 확장 "
        f"{stats['new_from_expansion']}) · 수집 {stats['collected']} · "
        f"skip {stats['skipped']} · 실패 {stats['failed']} · "
        f"{(time.time() - started) / 60:.1f}분"
    )
    log.close()


def main() -> None:
    ap = argparse.ArgumentParser(description="밀리 공개 도서 페이지 수집")
    ap.add_argument("--limit", type=int, default=None, help="이번 실행에서 수집할 최대 권수")
    ap.add_argument("--no-expand", action="store_true", help="어워즈·분야 BEST 확장 생략")
    args = ap.parse_args()
    collect(limit=args.limit, expand=not args.no_expand)


if __name__ == "__main__":
    main()
