"""행 빌더 — Must 5행의 조립 단위. 순서·dedup·배지는 compose.py 가 얹는다.

아키 §9-3 목록 외 신설(compose.py 150줄 유지, Advisor 승인 2026-09-06) — PROGRESS 1줄은 Plan 05-09.
"""

from collections import Counter
from collections.abc import Sequence
from dataclasses import replace
from itertools import zip_longest

from millie_rec.contracts import ROW_ANCHOR_PREFIX, Catalog, Neighbors, Row, ScoredItem
from millie_rec.serving.fallback import SOURCE_POPULARITY, trending_row

Items = Sequence[ScoredItem]
Cats = Sequence[str]

ROW_SIZE = 12  # D-03(.planning/phases/05-must/05-CONTEXT.md) 모든 행 12권
ANCHOR_NEIGHBORS = 20  # D-03 Neighbors.neighbors(seed₁, 20)
FRESH_POOL_N = 30  # D-02 fresh_picks 카테고리별 인기 풀
SOURCE_CONTENT = "content"  # data.md 표기 — 데모 카탈로그의 이웃은 콘텐츠 유사도다
CH_CONTENT, CH_POP = (SOURCE_CONTENT,), (SOURCE_POPULARITY,)  # ScoredItem.source_channels
META_KEYS = ("title", "authors", "image_url", "book_format")  # + difficulty·subcategories = 6필드
TITLE_CONTINUE, TITLE_FRESH = "이어 읽기", "새로운 발견"
TITLE_PERSONA, TITLE_PERSONA_DEFAULT = "{name}의 서가", "회원님의 서가"
SUBTITLE_ANCHOR = "결이 비슷한 책"
REASON_ANCHOR = "『{title}』을 좋아하셨다면"  # 조사 '을' 통일(D-03)


def with_meta(items: Items, catalog: Catalog | None) -> tuple[ScoredItem, ...]:
    """catalog.meta 6필드 조인. catalog None 이면 원본(스켈레톤 기동 보장)."""
    if catalog is None:
        return tuple(items)
    meta = {int(m["book_id"]): m for m in catalog.meta([i.book_id for i in items])}
    return tuple(
        replace(
            i,
            difficulty=i.difficulty if i.difficulty is not None else m.get("difficulty"),
            subcategories=tuple(m.get("subcategories") or ()),  # 리스트라 META_KEYS 에 못 넣는다
            **{key: m.get(key) for key in META_KEYS},
        )
        for i in items
        for m in (meta.get(i.book_id, {}),)
    )


def mix(items: Items) -> dict[str, int]:
    """행의 channel_mix = items 의 source_channels 집계."""
    return dict(Counter(ch for i in items for ch in i.source_channels))


def title_of(catalog: Catalog, book_id: int) -> str:
    return (catalog.meta([book_id]) or [{}])[0].get("title") or str(book_id)


def neighbor_row(
    row_id: str,
    title: str,
    subtitle: str | None,
    seed: int,
    nbrs: Sequence[tuple[int, float]],
    catalog: Catalog,
    exclude: set[int],
) -> Row | None:
    """앵커·after_completion 공용 행. 자격·중복·시드를 뺀 가중 상위 ROW_SIZE, 비면 None."""
    ok = set(catalog.eligible([b for b, _ in nbrs])) - exclude - {int(seed)}
    picked = [(b, w) for b, w in nbrs if b in ok][:ROW_SIZE]
    items = tuple(
        ScoredItem(b, float(w), SOURCE_CONTENT, title, position=n, source_channels=CH_CONTENT)
        for n, (b, w) in enumerate(picked)
    )
    if not items:
        return None
    joined = with_meta(items, catalog)
    return Row(row_id, title, "discover", joined, subtitle, {SOURCE_CONTENT: len(joined)})


def fresh_row(
    catalog: Catalog, leftover: Items, categories: Cats, all_categories: Cats, exclude: set[int]
) -> Row:
    """D-02: 선택 카테고리 밖 탐색 + 미선택 카테고리 인기 라운드로빈 보충."""
    chosen = set(categories)
    cats = {
        int(m["book_id"]): set(m.get("categories") or [])
        for m in catalog.meta([i.book_id for i in leftover])
    }
    out = [
        i
        for i in leftover
        if i.book_id not in exclude and not (cats.get(i.book_id, set()) & chosen)
    ][:ROW_SIZE]
    used = set(exclude) | {i.book_id for i in out}
    others = [c for c in all_categories if c not in chosen] or list(all_categories)
    pools = [[b for b in catalog.popular([c], n=FRESH_POOL_N) if b not in used] for c in others]
    for b in (b for grp in zip_longest(*pools) for b in grp if b is not None):
        if len(out) >= ROW_SIZE:
            break
        if b not in used:
            used.add(b)
            out.append(ScoredItem(b, 0.0, SOURCE_POPULARITY, source_channels=CH_POP))
    ranked = with_meta([replace(i, position=n) for n, i in enumerate(out)], catalog)
    return Row("fresh_picks", TITLE_FRESH, "explore", ranked, None, mix(ranked))


def personal_rows(
    items: Items,
    catalog: Catalog,
    neighbors: Neighbors | None,
    seeds: Sequence[int],
    categories: Cats,
    persona_name: str | None,
    continue_ids: Sequence[int],
    all_categories: Cats,
) -> tuple[Row, ...]:
    """level 0·1 의 Must 5행. 이웃·시드가 없거나 전부 자격 미달이면 앵커 행은 생략된다."""
    exclude = {int(s) for s in seeds}
    conts = tuple(
        ScoredItem(int(b), float(len(continue_ids) - n), position=n)
        for n, b in enumerate(continue_ids[:ROW_SIZE])
    )
    rows = [Row("continue_reading", TITLE_CONTINUE, "resume", with_meta(conts, catalog))]
    exclude |= {i.book_id for i in conts}
    if neighbors is not None and seeds:
        seed1 = int(seeds[0])
        head = REASON_ANCHOR.format(title=title_of(catalog, seed1))
        nbrs = neighbors.neighbors(seed1, ANCHOR_NEIGHBORS)
        anchor = neighbor_row(
            f"{ROW_ANCHOR_PREFIX}{seed1}", head, SUBTITLE_ANCHOR, seed1, nbrs, catalog, exclude
        )
        if anchor is not None:
            rows.append(anchor)
            exclude |= {i.book_id for i in anchor.items}
    rest = tuple(i for i in items if i.book_id not in exclude)
    shelf, leftover = rest[:ROW_SIZE], rest[ROW_SIZE:]
    name = TITLE_PERSONA.format(name=persona_name) if persona_name else TITLE_PERSONA_DEFAULT
    rows.append(Row("persona_shelf", name, "discover", with_meta(shelf, catalog), None, mix(shelf)))
    exclude |= {i.book_id for i in shelf}
    ids = [b for b in catalog.popular([], n=ROW_SIZE + len(exclude)) if b not in exclude][:ROW_SIZE]
    pop = tuple(
        ScoredItem(b, float(ROW_SIZE - n), SOURCE_POPULARITY, position=n, source_channels=CH_POP)
        for n, b in enumerate(ids)
    )
    trend = trending_row(with_meta(pop, catalog))
    exclude |= {i.book_id for i in trend.items}
    rows += [trend, fresh_row(catalog, leftover, categories, all_categories, exclude)]
    return tuple(rows)
