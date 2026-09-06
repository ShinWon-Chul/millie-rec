"""밀리 3depth 세부 카테고리 수집기 — 2depth 29종 → 3depth 목록 → 각 목록 상위 100권 id.

저장은 id·이름·순위만. 3depth 1건이 끝난 뒤에만 JSON 한 줄 append 하므로 중단·재시작은 멱등.
실행: uv run --with playwright==1.62.0 python scripts/collect_millie_subcats.py --parallel 5
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

from playwright.async_api import async_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
from millie_subcat_browser import block_assets, depth2, depth3  # noqa: E402
from millie_subcat_parse import CATEGORY_SEQ2, UA, read_index, write_index  # noqa: E402

PAUSE_MS = 500  # 컨텍스트당 페이지 사이 간격(예절 규칙 05 §2-4 의 연장)


async def worker(browser, queue: asyncio.Queue, out: Path, st: dict, log) -> None:
    ctx = await browser.new_context(user_agent=UA)
    await ctx.route("**/*", block_assets)
    page = await ctx.new_page()
    while not queue.empty() and st["strikes"] < 3:
        cat, seq2, seq3, name = queue.get_nowait()
        t0 = time.time()
        try:
            ids = await depth3(page, seq2, seq3)
            st["strikes"] = 0
            ts = datetime.now(UTC).isoformat(timespec="seconds")
            row = {
                "category": cat, "depth2_seq": seq2, "depth3_seq": seq3, "subcategory": name,
                "millie_ids": ids, "n": len(ids), "status": "ok", "collected_at": ts,
            }  # fmt: skip
            with out.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
            st["ok"] += 1
            log(f"{cat}/{name} ({seq3}) n={len(ids)} {time.time() - t0:.1f}s")
        except Exception as e:  # noqa: BLE001 — 실패는 기록만, 재시작 시 재시도
            st["fail"] += 1
            if "blocked" in str(e):
                st["strikes"] += 1
            log(f"FAIL {cat}/{name} ({seq3}) {str(e)[:80]}")
        await page.wait_for_timeout(PAUSE_MS)
    if st["strikes"] >= 3:
        log("STOP_BLOCK 연속 차단 3회 — 중단")
    await ctx.close()


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--parallel", type=int, default=5)
    ap.add_argument("--limit", type=int, default=0, help="처음 N개 카테고리만(시범)")
    ap.add_argument("--out", type=Path, default=Path("data/raw/millie_subcats.jsonl"))
    ap.add_argument("--index", type=Path, default=Path("data/raw/subcat_index.tsv"))
    ap.add_argument("--log", type=Path, default=Path("data/raw/collect_subcats.log"))
    ap.add_argument(
        "--from-index", action="store_true", help="2depth 단계 생략, 기존 index.tsv 사용"
    )
    a = ap.parse_args()
    a.out.parent.mkdir(parents=True, exist_ok=True)
    logf = a.log.open("a", encoding="utf-8")

    def log(msg: str) -> None:
        line = f"[{datetime.now().strftime('%H:%M:%S')}] {msg}"
        print(line, flush=True)
        logf.write(line + "\n")
        logf.flush()

    cats = list(CATEGORY_SEQ2.items())[: a.limit or None]
    done = set()
    if a.out.exists():
        for line in a.out.read_text(encoding="utf-8").splitlines():
            r = json.loads(line)
            if r.get("status") == "ok":
                done.add(r["depth3_seq"])
    t0 = time.time()
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        ctx = await browser.new_context(user_agent=UA)
        await ctx.route("**/*", block_assets)
        page = await ctx.new_page()
        index: list[tuple[str, str, str, str]] = []
        if a.from_index:  # discover_millie_subcats.py 가 보강한 인덱스를 그대로 쓴다
            index, cats = read_index(a.index), []
        for cat, seq2 in cats:  # 1단계: 2depth 29페이지 순차(예절)
            try:
                links = await depth2(page, cat, seq2)
            except Exception as e:  # noqa: BLE001
                log(f"FAIL depth2 {cat} ({seq2}) {str(e)[:80]}")
                links = []
            index += [(cat, seq2, s3, n) for s3, n in links]
            log(f"depth2 {cat} ({seq2}) 3depth {len(links)}개: {[n for _, n in links][:12]}")
            await page.wait_for_timeout(PAUSE_MS)
        await ctx.close()
        if not a.from_index:
            write_index(a.index, index)
        queue: asyncio.Queue = asyncio.Queue()
        for r in index:
            if r[2] not in done:
                queue.put_nowait(r)
        st = {"ok": 0, "fail": 0, "strikes": 0}
        log(f"3depth 대상 {len(index)} (이미 완료 {len(done)}) 병렬 {a.parallel}")
        await asyncio.gather(*(worker(browser, queue, a.out, st, log) for _ in range(a.parallel)))
        await browser.close()
    log(
        f"SUMMARY 카테고리 {len(cats)} 3depth {len(index)} ok {st['ok']} fail {st['fail']}"
        f" 소요 {(time.time() - t0) / 60:.1f}분"
    )


if __name__ == "__main__":
    asyncio.run(main())
