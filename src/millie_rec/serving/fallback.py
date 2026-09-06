"""fallback cascade 재료 — level 3 GlobalPopularFallback · level 2 segment_popular.

level 1 Level1Cache · 예산 판정 over_budget (아키텍처 01 §3-11, 05-CONTEXT D-10).
오케스트레이션(0 → 1 → 2 → 3)은 cascade.py(plan 05-06).
"""

import threading
import time
from collections.abc import Callable, Sequence

from millie_rec.contracts import BUDGET_MS, CACHE_TTL_S, Catalog, Row, ScoredItem, UserState

TRENDING_ROW_ID = "trending"  # contracts.ROW_IDS 안
TRENDING_TITLE = "지금 많이 읽는 책"  # 백엔드 01 §5 응답 예시. Phase 5 compose.py 가 재사용
TRENDING_PURPOSE = "fallback"  # contracts.ROW_PURPOSES 안
SOURCE_POPULARITY = "popularity"  # contracts.Candidate.source 허용값
CacheKey = tuple[str, str, str]  # (user_key, snapshot_id, variant) — D-10 캐시 키


class GlobalPopularFallback:
    """contracts.Pipeline 구현. catalog 없으면 빈 목록(level 3, 스켈레톤)."""

    name = "fallback"

    def __init__(self, catalog: Catalog | None) -> None:
        self.catalog = catalog

    def recommend(self, user: UserState, k: int) -> list[ScoredItem]:
        return segment_popular(self.catalog, user, (), k)


def trending_row(items: Sequence[ScoredItem]) -> Row:
    """D-02: level 3 응답의 유일한 행. Must 5행 뼈대는 Phase 5 compose.py."""
    return Row(
        row_id=TRENDING_ROW_ID,
        title=TRENDING_TITLE,
        purpose=TRENDING_PURPOSE,
        items=tuple(items),
        channel_mix={SOURCE_POPULARITY: len(items)} if items else {},
    )


def segment_popular(
    catalog: Catalog | None, user: UserState, categories: Sequence[str], k: int
) -> list[ScoredItem]:
    """level 2 재료 — popular(categories) 에서 seen 을 뺀 상위 k. categories 가 비면 전역."""
    if catalog is None:
        return []
    pool = catalog.popular(list(categories), n=k + len(user.seen))
    ids = [b for b in pool if b not in user.seen][:k]
    return [
        ScoredItem(
            book_id=b,
            score=float(len(ids) - i),
            source=SOURCE_POPULARITY,
            position=i,
            source_channels=(SOURCE_POPULARITY,),
        )
        for i, b in enumerate(ids)
    ]


def over_budget(elapsed_ms: float) -> bool:
    """D-10: feature+pipeline 누적 > BUDGET_MS. 모듈 전역을 호출 시점에 읽는다."""
    return elapsed_ms > BUDGET_MS


class Level1Cache:
    """D-10 level 1 — 직전 level 0 rows. 키 (user_key, snapshot_id, variant), TTL CACHE_TTL_S."""

    def __init__(
        self, *, ttl_s: float = CACHE_TTL_S, now: Callable[[], float] | None = None
    ) -> None:
        self._ttl = ttl_s
        self._now = now or time.time
        self._d: dict[CacheKey, tuple[float, tuple[Row, ...], str]] = {}
        self._lock = threading.Lock()

    def put(
        self,
        user_key: str,
        snapshot_id: str,
        variant: str,
        rows: Sequence[Row],
        model_version: str,
    ) -> None:
        """매 level 0 성공 시 저장(D-10). 값 = (만료시각, rows, model_version)."""
        with self._lock:
            self._d[(user_key, snapshot_id, variant)] = (
                self._now() + self._ttl,
                tuple(rows),
                model_version,
            )

    def get(
        self, user_key: str, snapshot_id: str, variant: str
    ) -> tuple[tuple[Row, ...], str] | None:
        """fallback 경로에서만 읽는다. 만료면 제거하고 None."""
        key = (user_key, snapshot_id, variant)
        with self._lock:
            hit = self._d.get(key)
            if hit is None:
                return None
            expires_at, rows, model_version = hit
            if self._now() > expires_at:
                del self._d[key]
                return None
            return rows, model_version

    def invalidate(self, user_key: str) -> int:
        """새 스냅샷·DELETE·완독 시 그 user_key 의 키를 전부 지운다. 지운 수 반환."""
        with self._lock:
            gone = [k for k in self._d if k[0] == user_key]
            for k in gone:
                del self._d[k]
            return len(gone)

    def __len__(self) -> int:
        return len(self._d)
