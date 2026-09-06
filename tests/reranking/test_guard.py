"""reranking/guard.py — 계약(개수·집합·position) · 정확성(12권 손계산 재배열)
· 안전성(None·이력 충분·결측 제외·stats 1회).
"""

import inspect

from millie_rec.contracts import BookStats, ScoredItem, UserState
from millie_rec.reranking import guard as guard_module
from millie_rec.reranking.guard import DifficultyGuard


class _FakeStats:
    """contracts.BookStatsSource 가짜 — (resid_z, source) 표. 없는 id 는 0.0 millie_index."""

    def __init__(self, table: dict[int, tuple[float | None, str]]) -> None:
        self.table, self.calls = table, 0

    def stats(self, book_ids):
        self.calls += 1
        out = []
        for b in book_ids:
            resid_z, source = self.table.get(int(b), (0.0, "millie_index"))
            out.append(BookStats(book_id=int(b), resid_z=resid_z, source=source, difficulty=0.5))
        return out

    def user_level(self, user):
        return None


TABLE = {3: (-1.5, "millie_index"), 11: (-1.2, "millie_index"), 5: (-2.0, "category_prior")}


def _items(n: int = 12) -> list[ScoredItem]:
    return [ScoredItem(book_id=i, score=float(n + 1 - i), position=i - 1) for i in range(1, n + 1)]


NEW = UserState(None, explicit_seeds=(100,))
OLD = UserState(None, explicit_seeds=(100,), history=(200, 201, 202))


# ── 정확성 ──
def test_new_user_violators_in_top_n_are_pushed_out_and_next_ok_promoted() -> None:
    """bad={3, 11}: 3 은 상단 10 밖으로, 11 은 위반이라 승격 안 됨 → 12 가 승격."""
    out = DifficultyGuard(_FakeStats(TABLE), top_n=10).rerank(NEW, _items(), 12)
    assert [i.book_id for i in out] == [1, 2, 4, 5, 6, 7, 8, 9, 10, 12, 3, 11]


def test_k_truncation_after_reorder() -> None:
    out = DifficultyGuard(_FakeStats(TABLE), top_n=10).rerank(NEW, _items(), 10)
    assert [i.book_id for i in out] == [1, 2, 4, 5, 6, 7, 8, 9, 10, 12]


def test_category_prior_and_none_resid_are_not_population() -> None:
    """resid_z None(millie_index)·category_prior(−2.0) 은 모집단 제외 → 움직이지 않는다."""
    table2 = {**TABLE, 2: (None, "millie_index")}
    out = DifficultyGuard(_FakeStats(table2), top_n=10).rerank(NEW, _items(), 12)
    assert [i.book_id for i in out] == [1, 2, 4, 5, 6, 7, 8, 9, 10, 12, 3, 11]
    assert out[3].book_id == 5


# ── 계약 ──
def test_count_and_set_preserved_positions_contiguous() -> None:
    original = {i.book_id: i.score for i in _items()}
    out = DifficultyGuard(_FakeStats(TABLE), top_n=10).rerank(NEW, _items(), 12)
    assert len(out) == 12
    assert {i.book_id for i in out} == set(range(1, 13))
    assert [i.position for i in out] == list(range(12))
    assert all(isinstance(i, ScoredItem) for i in out)
    assert all(i.score == original[i.book_id] for i in out)


# ── 안전성 ──
def test_history_ge_3_passes_through() -> None:
    out = DifficultyGuard(_FakeStats(TABLE), top_n=10).rerank(OLD, _items(), 12)
    assert [i.book_id for i in out] == list(range(1, 13))


def test_none_book_stats_passes_through_track_a() -> None:
    out = DifficultyGuard(None).rerank(NEW, _items(), 5)
    assert [i.book_id for i in out] == [1, 2, 3, 4, 5]
    assert [i.position for i in out] == [0, 1, 2, 3, 4]


def test_no_violators_keeps_order_and_empty_input() -> None:
    g = DifficultyGuard(_FakeStats({}), top_n=10)
    assert [i.book_id for i in g.rerank(NEW, _items(), 12)] == list(range(1, 13))
    assert g.rerank(NEW, [], 5) == []


def test_stats_called_once_and_docstring_declares_proxy() -> None:
    s = _FakeStats(TABLE)
    DifficultyGuard(s).rerank(NEW, _items(), 12)
    assert s.calls == 1
    src = inspect.getsource(guard_module)
    assert "대리값" in src
    assert "Phase 5" in src
    assert "len(user.history)" in src


def test_context_n_completed_overrides_history_proxy() -> None:
    """D-07: context["n_completed"] 가 있으면 대리값 대신 그 값으로 발동 여부를 정한다."""
    u_pass = UserState(None, explicit_seeds=(50,), history=(7, 8), context={"n_completed": "3"})
    s_pass = _FakeStats(TABLE)
    out = DifficultyGuard(s_pass, top_n=10).rerank(u_pass, _items(), 12)
    assert [i.book_id for i in out] == [i.book_id for i in _items()]  # 완독 3 → 패스스루
    assert s_pass.calls == 0

    u_fire = UserState(
        None, explicit_seeds=(50,), history=(1, 2, 3, 4), context={"n_completed": "0"}
    )
    s_fire = _FakeStats(TABLE)
    out2 = DifficultyGuard(s_fire, top_n=10).rerank(u_fire, _items(), 12)
    assert s_fire.calls == 1  # 이력 4 권이어도 완독 0 → 가드 발동
    assert [i.book_id for i in out2] == [1, 2, 4, 5, 6, 7, 8, 9, 10, 12, 3, 11]
