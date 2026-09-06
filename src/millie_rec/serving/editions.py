"""같은 작품의 다른 판본 판정 — 시드 자신의 판본을 이웃·행에서 뺀다.

카탈로그에 정규화 제목이 같은 레코드가 1,478 작품 3,644권 있다(실측 2026-09-06).
콘텐츠 유사도 이웃에서 그 중복은 가중치 1.0 으로 항상 1위에 올라, 방금 읽은 책의
다른 판본이 "결이 비슷한 책" 1번 칸을 차지했다(사용자 보고 2026-09-06).
compose.dedup_rows 는 행 사이 중복만 보므로 시드 자신은 걸러지지 않았다.
판정은 demo/scripts/make_mock.py personal_case 의 seen_titles 와 같은 규칙(정규화 제목).
"""

import re
from collections import Counter
from collections.abc import Sequence
from dataclasses import replace

from millie_rec.contracts import Catalog, Row, ScoredItem

# 이어 읽기는 "지금 읽는 중인 책"이라 시드와 같은 작품이어도 남아야 한다(데모 동선)
KEEP_ROWS = ("continue_reading",)


def normalize_title(s: object) -> str:
    """D-04 dedup 키 — 공백·기호 제거 + casefold. app/demo_cli._norm 의 확장 중복 정의."""
    return re.sub(r"[^\w]", "", str(s or "")).casefold()


def same_work(catalog: Catalog | None, candidates: Sequence[int], refs: Sequence[int]) -> set[int]:
    """refs 와 정규화 제목이 같은 candidates 의 book_id. catalog.meta 는 2회만 부른다."""
    ref_ids = [int(r) for r in refs]
    cand_ids = [int(c) for c in candidates]
    if catalog is None or not ref_ids or not cand_ids:
        return set()
    # 빈 제목은 제외 — 제목 결측인 책끼리 같은 작품으로 묶이면 안 된다
    want = {t for m in catalog.meta(ref_ids) if (t := normalize_title(m.get("title")))}
    if not want:
        return set()
    return {
        int(m["book_id"]) for m in catalog.meta(cand_ids) if normalize_title(m.get("title")) in want
    }


def drop_same_work(
    rows: Sequence[Row], catalog: Catalog | None, refs: Sequence[int]
) -> tuple[Row, ...]:
    """모든 행에서 refs 와 같은 작품인 item 을 뺀다. 걸릴 게 없으면 입력 그대로(항등)."""
    bad = same_work(catalog, [i.book_id for r in rows for i in r.items], refs)
    if not bad:
        return tuple(rows)
    out: list[Row] = []
    for row in rows:
        if row.row_id in KEEP_ROWS:
            out.append(row)
            continue
        kept: list[ScoredItem] = [
            replace(i, position=n)
            for n, i in enumerate(i for i in row.items if i.book_id not in bad)
        ]
        chan = dict(Counter(ch for i in kept for ch in i.source_channels))
        out.append(replace(row, items=tuple(kept), channel_mix=chan))
    return tuple(out)
