"""배지 제목 재수집 대상 목록 — JSONL 최신 줄 기준 title 이 배지 라벨인 millie_id·source.

parquet 스냅샷이 아니라 JSONL 을 읽는다: 배치는 구 파서를 메모리에 올린 채 돌아 그 뒤 수집분에도
배지 제목이 있다. 출력은 collect_millie.py --recollect 의 입력이며, source 열을 보존해
재수집 레코드의 출처(best:… 등)가 바뀌지 않게 한다 (03-UAT Test 9 gap).

    uv run python scripts/millie_recollect_list.py
"""

import argparse
import sys
from pathlib import Path

from millie_rec.contracts import DIR_RAW

SCRIPTS_DIR = str(Path(__file__).resolve().parent)  # scripts/ 는 패키지가 아니다(테스트 importlib)
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)
from build_millie_catalog import is_badge_title, read_records  # noqa: E402

OUT_DEFAULT = DIR_RAW / "recollect_badge_titles.txt"


def badge_title_rows(records: list[dict]) -> list[tuple[str, str]]:
    """title 이 배지 라벨인 (millie_id, source), millie_id 사전순. source 없으면 'recollect'."""
    return sorted(
        (r["millie_id"], r.get("source") or "recollect")
        for r in records
        if is_badge_title(r.get("title"))
    )


def main() -> None:
    ap = argparse.ArgumentParser(description="배지 제목 재수집 대상 목록")
    ap.add_argument("--jsonl", type=Path, default=DIR_RAW / "millie_pages.jsonl")
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()
    records, _ = read_records(args.jsonl)
    rows = badge_title_rows(records)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("".join(f"{m}\t{s}\n" for m, s in rows), encoding="utf-8")
    print(f"recollect targets={len(rows)} / valid={len(records)} → {args.out}")


if __name__ == "__main__":
    main()
