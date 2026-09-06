"""신규 사용자 난이도 가드 — contracts.Reranker 구현(main §5-6, D-08).

상단 N 안의 source=millie_index ∧ resid_z < GUARD_RESID_Z 책을
N 밖으로 내리고 다음 비위반 책을 끌어올린다(후보 삭제 아님).
발동 조건 n_completed < GUARD_MIN_COMPLETED 의 n_completed 는
Phase 4 에서 len(user.history) 대리값 — Phase 5 state.py 가
completion 이벤트 수로 교체한다(PDF 각주와 같은 문장).
(교체됨: context["n_completed"], Phase 5 05-08)
결측(difficulty None·category_prior·resid_z None) 은 모집단 제외.
book_stats None(Track A) 은 패스스루.
"""

from dataclasses import replace

from millie_rec.contracts import K_RANK, STATS_SOURCES, BookStatsSource, ScoredItem, UserState

GUARD_RESID_Z = -1.0  # main §5-6 resid_z < −1. freeze(D-14 ①)
GUARD_MIN_COMPLETED = 3  # main §5-6 완독 <3 신규 사용자
GUARD_TOP_N = K_RANK  # 상단 N = 10
MILLIE_INDEX = STATS_SOURCES[0]  # "millie_index" — 정본은 contracts


def _reposition(items: list[ScoredItem]) -> list[ScoredItem]:
    return [replace(i, position=n) for n, i in enumerate(items)]


class DifficultyGuard:
    """위반 책을 상단 N 밖으로 내리는 재배열 — 후보 삭제·추가 없음."""

    def __init__(
        self,
        book_stats: BookStatsSource | None = None,
        *,
        top_n: int = GUARD_TOP_N,
        resid_z_max: float = GUARD_RESID_Z,
        min_completed: int = GUARD_MIN_COMPLETED,
    ) -> None:
        self.book_stats = book_stats
        self.top_n, self.resid_z_max, self.min_completed = top_n, resid_z_max, min_completed

    def _violates(self, ids: list[int]) -> set[int]:
        """모집단 = 실측(millie_index) ∧ resid_z 존재. 경계 −1.0 은 위반 아님(엄격 부등호)."""
        if self.book_stats is None:
            return set()
        stats = self.book_stats.stats(ids)  # rerank 1회당 1회
        return {
            s.book_id
            for s in stats
            if s.source == MILLIE_INDEX and s.resid_z is not None and s.resid_z < self.resid_z_max
        }

    def rerank(self, user: UserState, items: list[ScoredItem], k: int) -> list[ScoredItem]:
        n_completed = int(user.context.get("n_completed", len(user.history)))
        if self.book_stats is None or n_completed >= self.min_completed or not items:
            return _reposition(list(items[:k]))  # 패스스루 — Track A · 이력 충분(대리값)
        bad = self._violates([i.book_id for i in items])  # items 전체 — 승격 후보도 검사
        head, rest = list(items[: self.top_n]), list(items[self.top_n :])
        head_ok = [i for i in head if i.book_id not in bad]
        head_bad = [i for i in head if i.book_id in bad]
        promoted: list[ScoredItem] = []
        leftover: list[ScoredItem] = []
        for i in rest:
            if len(promoted) < len(head_bad) and i.book_id not in bad:
                promoted.append(i)
            else:
                leftover.append(i)
        return _reposition((head_ok + promoted + head_bad + leftover)[:k])
