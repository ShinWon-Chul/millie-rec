"""after_completion 행 — 완독 직후 Nearline 사전 계산 → 다음 응답 최상단 행(D-13 · SERV-11).

아키 §9-3 목록 외 신설(after_completion, 150줄 유지, Advisor 승인 2026-09-06).
PROGRESS 1줄은 Advisor.
쓰기(precompute)는 Nearline 스레드 한 곳뿐이다(SERV-09) — 요청 경로는 stored 로 읽기만 한다.
store.after_completion 은 dict 한 칸 교체라 GIL 아래에서 원자적이고, 쓰는 스레드가 하나다.
"""

from collections.abc import Sequence

from millie_rec.contracts import Catalog, Neighbors, Row
from millie_rec.serving.rows import neighbor_row, title_of

AFTER_COMPLETION_N = 20  # D-13: Neighbors.neighbors(book, 20)
ROW_ID_AFTER = "after_completion"  # contracts.ROW_IDS 안. 렌더 순서는 compose.ROW_ORDER 맨 앞
TITLE_AFTER = "『{title}』을 완독하셨네요, 다음은"

Pair = tuple[int, tuple[tuple[int, float], ...]]
Hit = tuple[tuple[Row, ...], str]


def precompute(store, user_key: str, book_id: int, neighbors: Neighbors) -> None:
    """Nearline 전용 사전 계산 — 새 완독이 이전 것을 덮어쓴다(D-13)."""
    nbrs = neighbors.neighbors(int(book_id), AFTER_COMPLETION_N)
    store.after_completion[user_key] = (int(book_id), tuple((int(b), float(w)) for b, w in nbrs))


def stored(store, user_key: str) -> Pair | None:
    """요청 경로의 읽기 — store 가 없으면(스켈레톤 기동) None."""
    return store.after_completion.get(user_key) if store is not None else None


def prepend_after(rows: Sequence[Row], pair: Pair | None, catalog: Catalog, seeds: Sequence[int]):
    """완독 행을 맨 앞에 붙인다(D-13 최상단). 자격 있는 이웃이 없으면 기존 행 그대로."""
    if pair is None:
        return tuple(rows)
    seed, nbrs = pair
    title = TITLE_AFTER.format(title=title_of(catalog, int(seed)))
    row = neighbor_row(ROW_ID_AFTER, title, None, int(seed), nbrs, catalog, {int(s) for s in seeds})
    return (row, *rows) if row is not None else tuple(rows)


def fresh_cache(hit: Hit | None, store, cache, user_key: str) -> Hit | None:
    """D-10: 완독 뒤 after_completion 이 없는 옛 캐시는 무효화하고 미스로 만든다(T-05-10-03)."""
    if hit is None or stored(store, user_key) is None:
        return hit
    if any(r.row_id == ROW_ID_AFTER for r in hit[0]):
        return hit
    cache.invalidate(user_key)
    return None
