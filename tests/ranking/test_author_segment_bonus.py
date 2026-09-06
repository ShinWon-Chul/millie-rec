"""작가·대표 독자층 가점 — Ranking 단계 가산(main 설계서 §3 explicit prior).

세부 분류 가점과 같은 자리에서 합으로 들어가고, 세 가점의 합에 상한(= 채널 최소 가중)이 있다.
가짜는 파일마다 복제한다(tests/ranking/test_hybrid.py 관례).
"""

import pytest

from millie_rec.contracts import Candidate, UserState
from millie_rec.ranking import authors, hybrid, prefs

WANT = "추리/스릴러"
OTHER = "한국 소설"
SEG_A = "20대 남성"
SEG_B = "30대 여성"
HIGASHINO = "히가시노 게이고, 양윤옥 옮김"


class _Cat:
    """contracts.Catalog 가짜 — meta 의 authors·subcategories·top_segment. 호출 횟수를 센다."""

    def __init__(self, rows: dict[int, dict]) -> None:
        self.rows, self.meta_calls = rows, 0

    def meta(self, book_ids):
        self.meta_calls += 1
        return [{"book_id": int(b), **self.rows.get(int(b), {})} for b in book_ids]

    def popular(self, categories=(), n: int = 50):
        return sorted(self.rows)[:n]

    def eligible(self, book_ids):
        return list(book_ids)


def _user(seeds=(), *, subcategories="", picked="", criteria="") -> UserState:
    ctx = {
        "n_completed": "0",
        "subcategories": subcategories,
        "authors": picked,
        "criteria": criteria,
    }
    return UserState(None, explicit_seeds=tuple(seeds), context=ctx)


# ── authors.py 파서 (카탈로그 9,447권 실측 기대값) ────────────────────
@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("안제이사프콥스키, 함미라 옮김", ("안제이사프콥스키",)),
        (HIGASHINO, ("히가시노 게이고",)),
        ("김영하 (지음)", ("김영하",)),
        ("루이스 캐럴 글, 존 테니얼 그림, 손영미 옮김", ("루이스 캐럴", "존 테니얼")),
        ("에이든토저", ("에이든토저",)),  # 공백 없는 역할어는 사람 이름이다
        ("송기역", ("송기역",)),
        ("편집부", ()),
        ("Disney Books", ()),
        ("이종인 역", ()),
        (None, ()),
        ("", ()),
    ],
)
def test_split_authors_matches_catalog_measurements(raw, expected) -> None:
    assert authors.split_authors(raw) == expected


def test_key_ignores_inner_spacing_and_case() -> None:
    assert authors.key("히가시노 게이고") == authors.key("히가시노게이고")
    assert authors.keys_of(HIGASHINO) == authors.keys_of("히가시노게이고")


# ── 작가 가점 ─────────────────────────────────────────────────────────
def test_seed_author_overlap_gains_w_author() -> None:
    cat = _Cat({1: {"authors": "김영하 (지음)"}, 101: {"authors": "김영하"}})
    out = prefs.bonus(_user((101,)), [1], cat)
    assert out == {1: pytest.approx(prefs.W_AUTHOR)}


def test_other_author_gets_no_bonus_at_all() -> None:
    cat = _Cat({1: {"authors": "정세랑"}, 101: {"authors": "김영하"}})
    assert prefs.bonus(_user((101,)), [1], cat) == {}


def test_criterion_author_raises_the_weight() -> None:
    cat = _Cat({1: {"authors": "김영하"}, 101: {"authors": "김영하"}})
    picked = prefs.bonus(_user((101,), criteria="bestseller,author"), [1], cat)
    assert picked == {1: pytest.approx(prefs.W_AUTHOR_PICKED)}
    assert prefs.W_AUTHOR_PICKED > prefs.W_AUTHOR


def test_picked_author_applies_without_any_seed_book() -> None:
    cat = _Cat({1: {"authors": "김영하 지음"}})
    out = prefs.bonus(_user(picked="김영하"), [1], cat)
    assert out == {1: pytest.approx(prefs.W_AUTHOR)}


def test_author_matches_across_spacing_variants() -> None:
    cat = _Cat({1: {"authors": "히가시노게이고"}, 101: {"authors": HIGASHINO}})
    assert prefs.bonus(_user((101,)), [1], cat) == {1: pytest.approx(prefs.W_AUTHOR)}


def test_translator_never_counts_as_author() -> None:
    cat = _Cat({1: {"authors": "함미라"}, 101: {"authors": "안제이사프콥스키, 함미라 옮김"}})
    assert prefs.bonus(_user((101,)), [1], cat) == {}


# ── 대표 독자층 가점 ──────────────────────────────────────────────────
def test_segment_majority_of_seeds_gains_w_segment() -> None:
    cat = _Cat({
        1: {"top_segment": SEG_B}, 2: {"top_segment": SEG_A},
        101: {"top_segment": SEG_B}, 102: {"top_segment": SEG_B}, 103: {"top_segment": SEG_A},
    })  # fmt: skip
    out = prefs.bonus(_user((101, 102, 103)), [1, 2], cat)
    assert out == {1: pytest.approx(prefs.W_SEGMENT)}


def test_segment_tie_breaks_on_smallest_label_deterministically() -> None:
    metas = [{"top_segment": SEG_B}, {"top_segment": SEG_A}]
    assert prefs.estimate_segment(metas) == SEG_A  # 동률 → 사전순 최소
    assert prefs.estimate_segment([{}, {"top_segment": None}]) is None
    cat = _Cat(
        {1: {"top_segment": SEG_A}, 101: {"top_segment": SEG_B}, 102: {"top_segment": SEG_A}}
    )
    assert prefs.bonus(_user((101, 102)), [1], cat) == {1: pytest.approx(prefs.W_SEGMENT)}


def test_missing_authors_and_segment_columns_are_safe() -> None:
    cat = _Cat({1: {}, 101: {"authors": None, "top_segment": None}})
    assert prefs.bonus(_user((101,), picked="김영하"), [1, 2], cat) == {}


# ── 계약·예산 ─────────────────────────────────────────────────────────
def test_no_signal_skips_catalog_meta_entirely() -> None:
    cat = _Cat({1: {"authors": "김영하", "subcategories": [WANT], "top_segment": SEG_A}})
    assert prefs.bonus(_user(), [1], cat) == {}
    assert cat.meta_calls == 0  # p95 예산 — 신호가 없으면 카탈로그를 부르지 않는다


def test_catalog_none_leaves_blend_scores_identical() -> None:
    user = _user((101,), subcategories=WANT, picked="김영하", criteria="author")
    channels = {"cf": [Candidate(1, "itemknn", 4.0), Candidate(2, "itemknn", 2.0)]}
    assert prefs.bonus(user, [1, 2], None) == {}
    base = hybrid.blend_channels(user, channels, weights={"cf": 1.0})
    none = hybrid.blend_channels(user, channels, weights={"cf": 1.0}, catalog=None)
    assert [(i.book_id, i.score) for i in none] == [(i.book_id, i.score) for i in base]


def test_three_signals_are_capped_at_bonus_cap() -> None:
    cat = _Cat({
        1: {"authors": "김영하", "subcategories": [WANT, OTHER], "top_segment": SEG_A},
        101: {"authors": "김영하", "top_segment": SEG_A},
    })  # fmt: skip
    user = _user((101,), subcategories=WANT, picked="김영하", criteria="author")
    uncapped = prefs.W_SUBCAT + prefs.W_AUTHOR_PICKED + prefs.W_SEGMENT
    assert uncapped == pytest.approx(0.26) and uncapped > prefs.BONUS_CAP
    assert prefs.bonus(user, [1], cat) == {1: pytest.approx(prefs.BONUS_CAP)}
    assert cat.meta_calls == 1  # 후보 + 시드를 한 번에 조회한다


def test_bonus_cap_stays_within_the_smallest_channel_weight() -> None:
    assert prefs.BONUS_CAP <= hybrid.W_POP  # 넘으면 가점이 통로 순서를 뒤집는다


def test_bonus_is_deterministic_across_calls() -> None:
    cat = _Cat({
        1: {"authors": "김영하", "subcategories": [WANT]}, 2: {"top_segment": SEG_A},
        101: {"authors": "김영하", "top_segment": SEG_A},
    })  # fmt: skip
    user = _user((101,), subcategories=WANT)
    assert prefs.bonus(user, [1, 2], cat) == prefs.bonus(user, [1, 2], cat)
