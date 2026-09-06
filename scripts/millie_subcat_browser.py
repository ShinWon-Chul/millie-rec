"""밀리 2depth·3depth 페이지 브라우저 조작 — collect_millie_subcats.py 의 Playwright 헬퍼."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from millie_subcat_parse import (  # noqa: E402
    BLOCK_RE,
    DEPTH2_URL,
    DEPTH3_URL,
    LOGIN_WALL_MAX,
    extract_book_ids,
    parse_depth3_links,
)

ANCHORS_JS = "els => els.map(e => [e.getAttribute('href') || '', (e.innerText || '').trim()])"
HREFS_JS = "els => els.map(e => e.getAttribute('href') || '')"


async def block_assets(route) -> None:
    if route.request.resource_type in {"image", "media", "font"}:
        await route.abort()
    else:
        await route.continue_()


async def load(page, url: str) -> int:
    resp = await page.goto(url, wait_until="domcontentloaded", timeout=30000)
    await page.wait_for_timeout(1500)
    status = resp.status if resp else 0
    body = await page.inner_text("body")
    if status >= 400 or BLOCK_RE.search(body):
        raise RuntimeError(f"blocked status={status}")
    return status


async def scroll_stable(page, count_js: str, cap: int) -> None:
    prev = -1
    for _ in range(12):
        cur = await page.evaluate(count_js)
        if cur == prev or cur >= cap:
            break
        prev = cur
        await page.mouse.wheel(0, 30000)
        await page.wait_for_timeout(1000)


async def depth2(page, category: str, seq2: str) -> list[tuple[str, str]]:
    await load(page, DEPTH2_URL.format(seq2=seq2))
    await scroll_stable(page, "document.querySelectorAll('a[href*=\"3depth\"]').length", 10**6)
    anchors = await page.eval_on_selector_all("a[href]", ANCHORS_JS)
    return parse_depth3_links([tuple(a) for a in anchors], seq2)


async def depth3(page, seq2: str, seq3: str) -> list[str]:
    await load(page, DEPTH3_URL.format(seq2=seq2, seq3=seq3))
    await scroll_stable(
        page, "document.querySelectorAll('a[href*=\"/v4/book/\"]').length", LOGIN_WALL_MAX * 2
    )
    return extract_book_ids(await page.eval_on_selector_all("a[href]", HREFS_JS))
