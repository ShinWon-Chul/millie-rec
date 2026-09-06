"""서빙 측 BookStatsSource 어댑터 — stats 위임, user_level 만 계산.

완독 책 difficulty 평균, 완독 0권이면 선택 카테고리 prior(05-CONTEXT.md D-07).
"""

from collections.abc import Sequence

from millie_rec.contracts import BookStats, Catalog, UserState
from millie_rec.serving.state import StateStore

PRIOR_POPULAR_N = 200  # D-07 카테고리 prior 표본 크기(05-CONTEXT Claude's Discretion)


def _mean_difficulty(catalog: Catalog, book_ids: Sequence[int]) -> float | None:
    """결측(difficulty=None) 을 뺀 평균. 표본이 없으면 None(D-07)."""
    metas = catalog.meta(list(book_ids))
    vals = [m["difficulty"] for m in metas if m.get("difficulty") is not None]
    return sum(vals) / len(vals) if vals else None


class ServingBookStats:
    """catalog(Catalog+BookStatsSource) 를 감싸 user_level 만 서빙 상태로 계산한다. app 이 주입."""

    def __init__(self, catalog: Catalog, store: StateStore) -> None:
        self.catalog = catalog
        self.store = store
        self._prior: dict[tuple[str, ...], float | None] = {}

    def stats(self, book_ids: Sequence[int]) -> list[BookStats]:
        return self.catalog.stats(book_ids)  # type: ignore[attr-defined]  # CatalogKR 은 세 Protocol 만족

    def user_level(self, user: UserState) -> float | None:
        """완독 책 difficulty 평균, 완독 0권이면 선택 카테고리 인기 표본의 평균(D-07)."""
        key = user.context.get("user_key")
        completed = self.store.completed_books(key) if key else ()
        level = _mean_difficulty(self.catalog, completed) if completed else None
        if level is not None:
            return level
        cats = tuple(c for c in user.context.get("categories", "").split(",") if c)
        return self._category_prior(cats) if cats else None

    def _category_prior(self, cats: tuple[str, ...]) -> float | None:
        """카테고리 조합당 popular 조회 1회만(캐시)."""
        if cats not in self._prior:
            popular = self.catalog.popular(list(cats), n=PRIOR_POPULAR_N)
            self._prior[cats] = _mean_difficulty(self.catalog, popular)
        return self._prior[cats]
