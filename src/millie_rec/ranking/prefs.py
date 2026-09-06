"""취향 가점 — 세부 분류·작가·대표 독자층(main 설계서 §3 explicit prior)을 합으로 가산.

가점은 blend_channels 안에서 합으로 들어간다. 위에서 재순위화(MMR·난이도 가드)가 마지막 판단을
하므로 여기서는 정렬하지 않는다. 합에 상한을 두는 이유는 BONUS_CAP 주석에 있다.
"""

from collections import Counter
from collections.abc import Sequence

from millie_rec.contracts import Catalog, UserState
from millie_rec.ranking import authors

KEY_SUBCAT = "subcategories"  # UserState.context 키 — 채우는 곳은 serving/state.py
KEY_AUTHORS = "authors"
KEY_CRITERIA = "criteria"
KEY_TOP_SEGMENT = "top_segment"  # catalog.meta() 컬럼 (21.8% 결측)
CRITERION_AUTHOR = "author"

W_SUBCAT = 0.06  # 세부 분류 겹침
W_AUTHOR = 0.08  # 시드 저자와 겹침
W_AUTHOR_PICKED = 0.16  # 취향 설정에서 직접 고른 작가
W_SEGMENT = 0.04  # 대표 독자층 일치
# = hybrid.W_POP. 가점 합이 채널 최소 가중을 넘으면 통로 순서가 뒤집혀 혼합의 의미가 사라진다
BONUS_CAP = 0.2


def _csv(value: str | None) -> set[str]:
    """쉼표로 결합된 context 값 → 공백 제거 집합."""
    return {s.strip() for s in (value or "").split(",") if s.strip()}


def estimate_segment(seed_meta: Sequence[dict]) -> str | None:
    """시드 top_segment 다수결. 결측 무시, 동률은 사전순 최소(결정성), 전부 결측이면 None."""
    counts = Counter(s for m in seed_meta if (s := m.get(KEY_TOP_SEGMENT)))
    if not counts:
        return None
    return min(counts, key=lambda s: (-counts[s], s))


def bonus(user: UserState, book_ids: Sequence[int], catalog: Catalog | None) -> dict[int, float]:
    """세부 분류 + 작가 + 세그먼트 가점. 합은 BONUS_CAP 이하. catalog None 이면 {}."""
    if catalog is None:
        return {}  # Track A 불변 — app/pipeline.py 는 catalog 를 넘기지 않는다
    wanted_subs = _csv(user.context.get(KEY_SUBCAT))
    picked_keys = frozenset(authors.key(n) for n in _csv(user.context.get(KEY_AUTHORS)))
    seeds = tuple(dict.fromkeys(int(b) for b in user.explicit_seeds))
    if not wanted_subs and not picked_keys and not seeds:
        return {}  # 신호가 없으면 catalog.meta 를 아예 부르지 않는다(p95 예산)
    books = [int(b) for b in book_ids]
    wanted = list(dict.fromkeys(books + list(seeds)))  # meta 는 한 번만 부른다
    metas = {int(m["book_id"]): m for m in catalog.meta(wanted)}
    seed_metas = [metas[s] for s in seeds if s in metas]
    seed_keys = frozenset().union(*(authors.keys_of(m.get(KEY_AUTHORS)) for m in seed_metas)) \
        if seed_metas else frozenset()  # fmt: skip
    author_keys = picked_keys | seed_keys
    criteria = _csv(user.context.get(KEY_CRITERIA))
    author_w = W_AUTHOR_PICKED if CRITERION_AUTHOR in criteria else W_AUTHOR
    segment = estimate_segment(seed_metas)
    out: dict[int, float] = {}
    for b in books:
        m = metas.get(b)
        if m is None:
            continue
        total = W_SUBCAT if wanted_subs & set(m.get(KEY_SUBCAT) or ()) else 0.0
        if author_keys & authors.keys_of(m.get(KEY_AUTHORS)):
            total += author_w
        if segment is not None and m.get(KEY_TOP_SEGMENT) == segment:
            total += W_SEGMENT
        if total > 0.0:
            out[b] = min(total, BONUS_CAP)
    return out
