"""세부 카테고리 가점 — Ranking 단계 가산(main 설계서 §3 Fine-grained taste prior).

가점은 blend_channels 안에서 합으로 들어간다. 재순위화(MMR·난이도 가드)가 그 위에서
마지막 판단을 하고, 그 뒤에 점수 정렬을 다시 하지 않는다 — 마지막 테스트가 그 회귀 가드다.
가짜는 파일마다 복제한다(tests/ranking/test_hybrid.py 관례).
"""

import numpy as np
import pytest

from millie_rec.app.staged import StagedPipeline
from millie_rec.contracts import BookStats, Candidate, UserState
from millie_rec.ranking.hybrid import W_SUBCAT, blend_channels
from millie_rec.reranking import GUARD_TOP_N, DifficultyGuard, MMRReranker

WANT = "추리/스릴러"
OTHER = "한국 소설"
# 간격이 0.1 인 12권 — book4(0.7) 와 book5(0.69) 만 W_SUBCAT(0.06) 로 뒤집히게 둔다
RAW = {1: 12.0, 2: 11.0, 3: 10.0, 4: 9.0, 5: 8.9, 6: 8.0, 7: 7.0, 8: 6.0, 9: 5.0, 10: 4.0,
       11: 3.0, 12: 2.0}  # fmt: skip


class _Cat:
    """contracts.Catalog 가짜 — meta 의 subcategories 만 쓴다. 호출 횟수를 센다."""

    def __init__(self, marked: dict[int, list[str]]) -> None:
        self.marked, self.meta_calls = marked, 0

    def meta(self, book_ids):
        self.meta_calls += 1
        return [{"book_id": int(b), "subcategories": self.marked.get(int(b), [])} for b in book_ids]

    def popular(self, categories=(), n: int = 50):
        return sorted(self.marked)[:n]

    def eligible(self, book_ids):
        return list(book_ids)


class _Stats:
    """contracts.BookStatsSource 가짜 — level·difficulty·resid_z 표만."""

    def __init__(self, level, difficulty=None, resid_z=None) -> None:
        self.level = level
        self.difficulty = difficulty or {}
        self.resid_z = resid_z or {}

    def stats(self, book_ids):
        return [
            BookStats(
                book_id=int(b),
                difficulty=self.difficulty.get(int(b)),
                resid_z=self.resid_z.get(int(b)),
                source="millie_index",
            )
            for b in book_ids
        ]

    def user_level(self, user):
        return self.level


class _Vecs:
    """contracts.ItemVectors 가짜 — 전부 같은 벡터. MMR 다양성 항이 상수라 원 순위를 유지한다."""

    def vectors(self, book_ids):
        return np.ones((len(list(book_ids)), 4), dtype=float)


class _Fixed:
    """contracts.CandidateGenerator 가짜 — 고정 후보를 그대로 돌려준다."""

    name = "cf"

    def __init__(self, cands) -> None:
        self.cands = list(cands)

    def fit(self, train):
        return self

    def retrieve(self, user, k):
        return self.cands[:k]


def _user(subcategories: str = "", n_completed: str = "0") -> UserState:
    ctx = {"n_completed": n_completed, "subcategories": subcategories}
    return UserState(None, context=ctx)


def _cf(book_ids=tuple(RAW)) -> dict[str, list[Candidate]]:
    return {"cf": [Candidate(b, "itemknn", RAW[b]) for b in book_ids]}


def _pairs(items) -> list[tuple[int, float]]:
    return [(i.book_id, i.score) for i in items]


# ── 계약 ──────────────────────────────────────────────────────────────
def test_catalog_none_leaves_scores_identical_track_a_invariant() -> None:
    """Track A 불변 — app/pipeline.py 는 catalog 를 넘기지 않으므로 평가 숫자가 그대로다."""
    cat = _Cat({1: [WANT], 5: [WANT]})
    user = _user(WANT)
    base = blend_channels(user, _cf(), weights={"cf": 1.0})
    with_cat_none = blend_channels(user, _cf(), weights={"cf": 1.0}, catalog=None)
    assert _pairs(with_cat_none) == _pairs(base)
    assert _pairs(blend_channels(user, _cf(), weights={"cf": 1.0}, catalog=cat)) != _pairs(base)


def test_empty_context_subcategories_is_identity_and_skips_catalog() -> None:
    cat = _Cat({1: [WANT], 5: [WANT]})
    base = blend_channels(_user(), _cf(), weights={"cf": 1.0})
    same = blend_channels(_user(), _cf(), weights={"cf": 1.0}, catalog=cat)
    assert _pairs(same) == _pairs(base)
    assert cat.meta_calls == 0  # p95 예산 — 선택이 없으면 카탈로그를 아예 부르지 않는다
    assert _pairs(blend_channels(_user(" , "), _cf(), weights={"cf": 1.0}, catalog=cat)) == _pairs(
        base
    )


# ── 정확성 ────────────────────────────────────────────────────────────
def test_matched_books_gain_w_subcat_and_rise_in_rank() -> None:
    cat = _Cat({1: [WANT], 5: [OTHER, WANT], 6: [OTHER]})
    out = blend_channels(_user(WANT), _cf(), weights={"cf": 1.0}, catalog=cat)
    by = dict(_pairs(out))
    assert by[1] == pytest.approx(1.0 + W_SUBCAT)
    assert by[5] == pytest.approx(0.69 + W_SUBCAT)
    assert by[4] == pytest.approx(0.7) and by[6] == pytest.approx(0.6)  # 안 겹친 책 무변경
    assert [i.book_id for i in out][:5] == [1, 2, 3, 5, 4]  # book5 가 book4 를 넘었다
    assert [i.position for i in out] == list(range(len(out)))


def test_negative_total_rises_by_addition_not_multiplication() -> None:
    """gap 3항으로 total 이 음수인 책도 올라간다 — 곱(score * (1 + b))이면 내려간다."""
    stats = _Stats(level=0.0, difficulty={1: 0.0, 2: 1.0})  # gap: book1 0.0 · book2 1.0
    cat = _Cat({2: [WANT]})
    kw = {"weights": {"cf": 1.0}, "book_stats": stats}
    channels = {"cf": [Candidate(1, "itemknn", 4.0), Candidate(2, "itemknn", 2.0)]}
    plain = dict(_pairs(blend_channels(_user(WANT), channels, **kw)))
    assert plain[2] == pytest.approx(-0.30)  # -0.10*1 - 0.20*1 - 0.01*0*1
    boosted = dict(_pairs(blend_channels(_user(WANT), channels, **kw, catalog=cat)))
    assert boosted[2] == pytest.approx(-0.30 + W_SUBCAT)  # = -0.24, 곱이면 -0.318
    assert boosted[2] > plain[2] and boosted[1] == pytest.approx(plain[1])


# ── 안전성(회귀) ──────────────────────────────────────────────────────
def test_mmr_and_guard_order_survives_the_subcat_bonus() -> None:
    """가점 뒤에 점수 재정렬이 없어야 한다 — 위반 책(book1)이 상단 N 밖에 남는다."""
    stats = _Stats(level=None, resid_z={1: -2.0})  # book1 만 가드 위반, gap 가중은 0
    cat = _Cat({1: [WANT], 5: [WANT]})
    pipe = StagedPipeline("hybrid_div", {"cf": _Fixed(_cf()["cf"])}, weights={"cf": 1.0},
                          book_stats=stats, catalog=cat,
                          rerankers=(MMRReranker(_Vecs()), DifficultyGuard(stats)))  # fmt: skip
    out = pipe.recommend(_user(WANT), len(RAW))
    ids = [i.book_id for i in out]
    assert ids == [2, 3, 5, 4, 6, 7, 8, 9, 10, 11, 1, 12]
    assert ids.index(1) >= GUARD_TOP_N  # 가드 강등이 살아 있다
    assert out[ids.index(1)].score == pytest.approx(1.0 + W_SUBCAT)  # 최고점인데도 상단 밖
    assert ids.index(5) < ids.index(4)  # 가점 자체는 여전히 유효
