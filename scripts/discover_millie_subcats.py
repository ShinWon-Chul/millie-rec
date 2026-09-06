"""2depth 페이지가 렌더하지 않는 숨은 3depth 를 3depth 페이지의 휠 피커에서 발견한다.

실측(2026-09-06): 2depth 페이지는 3depth 섹션을 최대 11개만 렌더하지만, 3depth 페이지 상단의
분류 버튼을 누르면 형제 3depth 전체가 `smooth-picker` 휠로 뜬다. 항목은 클릭이 아니라 드래그로
선택하고 '확인' 을 누르면 `/v3/search/3depth/<seq3>` 로 이동한다 — 그 URL 에서 seq3 를 얻는다.
결과는 `data/raw/subcat_index.tsv` 에 append 하고, 수집기는 `--from-index` 로 이를 읽는다.
"""

from __future__ import annotations

import argparse
import asyncio
import re
import sys
import time
from pathlib import Path

from playwright.async_api import async_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
from millie_subcat_parse import DEPTH3_URL, UA, read_index  # noqa: E402

ITEMS_JS = "() => [...document.querySelectorAll('.smooth-item')].map(e => (e.innerText||'').trim())"
SELECTED_JS = (
    "() => { const e = document.querySelector('.smooth-item-selected');"
    " return e ? (e.innerText||'').trim() : null }"
)
PX_PER_ITEM = 30  # 실측 120px 드래그 = 4항목
SEQ_RE = re.compile(r"/3depth/(\d+)")


def missing_names(picker_items: list[str], known: set[str]) -> list[str]:
    """피커 항목 중 인덱스에 없는 이름(페이지 순서·중복 제거)."""
    out, seen = [], set()
    for n in picker_items:
        n = " ".join(n.split())
        if n and n not in known and n not in seen:
            seen.add(n)
            out.append(n)
    return out


async def open_picker(page, current: str) -> list[str]:
    await page.locator(f"text='{current}'").first.click(timeout=5000)
    await page.wait_for_timeout(800)
    return await page.evaluate(ITEMS_JS)


async def close_picker(page) -> None:
    await page.locator("text='취소'").last.click(force=True, timeout=3000)
    await page.wait_for_timeout(500)


async def drag_to(page, items: list[str], target: str) -> bool:
    box = await page.locator(".smooth-group").first.bounding_box()
    cx, cy = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
    for _ in range(8):
        sel = await page.evaluate(SELECTED_JS)
        if sel == target:
            return True
        if sel not in items:
            return False
        delta = items.index(target) - items.index(sel)
        await page.mouse.move(cx, cy)
        await page.mouse.down()
        await page.mouse.move(cx, cy - delta * PX_PER_ITEM, steps=8)
        await page.mouse.up()
        await page.wait_for_timeout(500)
    return (await page.evaluate(SELECTED_JS)) == target


async def discover(browser, cat: str, seq2: str, known: list[tuple[str, str]], log) -> list:
    """known=(seq3, name) 1개 이상 필요. 발견한 (cat, seq2, seq3, name) 목록을 돌려준다."""
    ctx = await browser.new_context(user_agent=UA, viewport={"width": 480, "height": 900})
    page = await ctx.new_page()
    found: list[tuple[str, str, str, str]] = []
    # 3depth 이름 == 대분류(예: 부모/부모)면 헤더 2depth 링크가 먼저 잡힌다 → 다른 이름으로 시작
    seq3, current = next(((s, n) for s, n in known if n != cat), known[0])
    try:
        await page.goto(DEPTH3_URL.format(seq2=seq2, seq3=seq3), wait_until="domcontentloaded")
        await page.wait_for_timeout(1500)
        items = await open_picker(page, current)
        todo = missing_names(items, {n for _, n in known})
        log(f"{cat}: 피커 {len(items)}개, 인덱스 {len(known)}개, 숨은 {len(todo)}개 {todo}")
        await close_picker(page)
        for name in todo:
            items = await open_picker(page, current)
            if not await drag_to(page, items, name):
                log(f"FAIL {cat}/{name} 드래그 선택 실패")
                await close_picker(page)
                continue
            await page.locator("text='확인'").last.click(force=True, timeout=3000)
            await page.wait_for_timeout(2500)
            m = SEQ_RE.search(page.url)
            if not m:
                log(f"FAIL {cat}/{name} URL 에 seq 없음 {page.url}")
                continue
            found.append((cat, seq2, m.group(1), name))
            current = name
            log(f"{cat}/{name} → {m.group(1)}")
    except Exception as e:  # noqa: BLE001
        log(f"FAIL {cat} {str(e)[:80]}")
    await ctx.close()
    return found


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--index", type=Path, default=Path("data/raw/subcat_index.tsv"))
    ap.add_argument("--log", type=Path, default=Path("data/raw/collect_subcats.log"))
    ap.add_argument("--parallel", type=int, default=5)
    ap.add_argument("--only", default="", help="쉼표 구분 카테고리(시범)")
    a = ap.parse_args()
    logf = a.log.open("a", encoding="utf-8")

    def log(msg: str) -> None:
        line = f"[{time.strftime('%H:%M:%S')}] discover {msg}"
        print(line, flush=True)
        logf.write(line + "\n")
        logf.flush()

    rows = read_index(a.index)
    by_cat: dict[str, tuple[str, list[tuple[str, str]]]] = {}
    for cat, seq2, seq3, name in rows:
        by_cat.setdefault(cat, (seq2, []))[1].append((seq3, name))
    cats = [c for c in by_cat if not a.only or c in a.only.split(",")]
    sem = asyncio.Semaphore(a.parallel)

    async def one(browser, cat):
        async with sem:
            return await discover(browser, cat, by_cat[cat][0], by_cat[cat][1], log)

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        results = await asyncio.gather(*(one(browser, c) for c in cats))
        await browser.close()
    new = [r for rs in results for r in rs if r[2] not in {x[2] for x in rows}]
    with a.index.open("a", encoding="utf-8") as fh:
        fh.writelines("\t".join(r) + "\n" for r in new)
    log(f"SUMMARY 카테고리 {len(cats)} 신규 3depth {len(new)} → {a.index}")


if __name__ == "__main__":
    asyncio.run(main())
