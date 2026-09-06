"""배지 6종 규칙(serving.md · 화면 01 §4-4).

compose 가 행 조립 마지막 단계에 부른다. Advisor 확정 17 B1 로 신설(아키 §9-3 목록 외).
"""

from collections.abc import Sequence
from dataclasses import replace

from millie_rec.contracts import Badge, Catalog, Row
from millie_rec.serving.authors import key, split_authors

REVIEW_MIN_COUNT = 3  # 별점이 있을 때 "★4.2 · 리뷰 128" 최소 리뷰 수
REVIEW_MIN_COUNT_NO_RATING = 10  # 별점 결측 시 "리뷰 128" 최소 리뷰 수


def badge_for(
    meta: dict,
    *,
    criterion: str | None,
    seed_authors: frozenset[str] = frozenset(),
    seed_publishers: frozenset[str] = frozenset(),
) -> Badge | None:
    """serving.md 배지 규칙. light 는 Should → None. review 3단 폴백의 3단은 bestseller."""
    rank, avg = meta.get("pop_rank"), meta.get("average_rating")
    n = meta.get("review_count") or 0
    best = Badge("bestseller", f"인기 {rank}위") if rank is not None else None
    if criterion == "bestseller":
        return best
    if criterion == "review":
        if avg is not None and n >= REVIEW_MIN_COUNT:
            return Badge("review", f"★{avg:.1f}, 리뷰 {n}")  # shelf_count 는 넣지 않는다
        if n >= REVIEW_MIN_COUNT_NO_RATING:
            return Badge("review", f"리뷰 {n}")
        return best
    if criterion == "author":
        return _author_badge(meta, seed_authors)
    if criterion == "publisher" and meta.get("publisher") in seed_publishers:
        return Badge("publisher", f"{meta['publisher']} 출판")
    if criterion == "buzz" and meta.get("millie_label"):
        return Badge("buzz", str(meta["millie_label"]))
    return None


def _author_badge(meta: dict, seed_authors: frozenset[str]) -> Badge | None:
    """authors 문자열 전체가 아니라 이름 단위로 본다 — 역자가 달라도 같은 작가면 붙는다."""
    seed_keys = {key(a) for a in seed_authors}
    for name in split_authors(meta.get("authors")):
        if key(name) in seed_keys:
            return Badge("author", f"{name} 작가")
    return None


def _first_badge(
    meta: dict, order: Sequence[str | None], authors: frozenset[str], pubs: frozenset[str]
) -> Badge | None:
    """고른 순서대로 보고 처음 성공한 배지를 쓴다 — 첫 기준이 배지를 독점하지 않는다."""
    for c in order:
        hit = badge_for(meta, criterion=c, seed_authors=authors, seed_publishers=pubs)
        if hit is not None:
            return hit
    return None


def attach_badges(
    rows: Sequence[Row],
    catalog: Catalog,
    criterion: str | None,
    seeds: Sequence[int],
    *,
    criteria: Sequence[str] = (),
    picked_authors: Sequence[str] = (),
) -> tuple[Row, ...]:
    """기준이 없으면 그대로. seed·전 행 meta 는 각각 1회만 조회(기준이 늘어도 불변)."""
    if criterion is None and not criteria:
        return tuple(rows)
    order = tuple(criteria) if criteria else (criterion,)
    seed_meta = catalog.meta([int(s) for s in seeds]) if seeds else []
    # 고른 작가는 시드 저자가 아니어도 배지 대상이다(실측 결함 09-07)
    authors = frozenset(n for m in seed_meta for n in split_authors(m.get("authors")))
    authors |= frozenset(picked_authors)
    publishers = frozenset(m["publisher"] for m in seed_meta if m.get("publisher"))
    meta = {int(m["book_id"]): m for m in catalog.meta([i.book_id for r in rows for i in r.items])}
    return tuple(
        replace(
            r,
            items=tuple(
                replace(
                    i,
                    badge=_first_badge(meta.get(i.book_id, {}), order, authors, publishers),
                )
                for i in r.items
            ),
        )
        for r in rows
    )
