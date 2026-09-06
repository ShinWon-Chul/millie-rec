"""authors.py — 계약(반환 튜플) · 정확성(역할어·구분자) · 안전성(None·비인물) + 배지 회귀.

작가 정규화. 공백 없이 역할어로 끝나는 실제 이름(에이든토저·송기역)을 훼손하지 않는 것이
이 슬라이스의 핵심 단정이다 — 카탈로그 9,447권 실측에서 그런 세그먼트가 24개 있었다.
"""

import pytest

from millie_rec.contracts import Badge, Row, ScoredItem
from millie_rec.serving.authors import display_of, key, split_authors
from millie_rec.serving.badges import attach_badges, badge_for


# ── 계약·정확성 ──────────────────────────────────────────────────────────
@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("안제이사프콥스키, 함미라 옮김", ("안제이사프콥스키",)),
        ("히가시노 게이고, 양윤옥 옮김", ("히가시노 게이고",)),
        ("히가시노게이고", ("히가시노게이고",)),
        ("김영하 (지음)", ("김영하",)),
        ("루이스 캐럴 글, 존 테니얼 그림, 손영미 옮김", ("루이스 캐럴", "존 테니얼")),
        ("셰익스피어 원작 / 김철 편역", ("셰익스피어",)),
        ("저자 1", ("저자 1",)),
    ],
)
def test_split_authors_drops_roles_and_translator_segments(value: str, expected: tuple[str, ...]):
    assert split_authors(value) == expected


@pytest.mark.parametrize("value", ["에이든토저", "로베르토발저", "송기역", "억만장자 메신저"])
def test_split_authors_keeps_names_ending_with_role_word_without_space(value: str):
    assert split_authors(value) == (value,)


def test_split_authors_strips_repeated_author_roles_and_keeps_display_space():
    assert split_authors("홍길동 글 그림") == ("홍길동",)
    assert split_authors("루이스 캐럴 지음") == ("루이스 캐럴",)


def test_split_authors_dedupes_by_key_keeping_first_display():
    assert split_authors("히가시노 게이고, 히가시노게이고 글") == ("히가시노 게이고",)


# ── 안전성 ──────────────────────────────────────────────────────────────
@pytest.mark.parametrize(
    "value", [None, "", "   ", "편집부", "저작권팀", "Disney Books", "이종인 역", "김"]
)
def test_split_authors_excludes_non_person_and_empty(value):
    assert split_authors(value) == ()


def test_key_ignores_inner_space_and_case():
    assert key("히가시노 게이고") == key("히가시노게이고")
    assert key("B. A. 패리스") == key("b.a.패리스")


def test_display_of_takes_majority_then_lexicographic_min():
    assert display_of({"히가시노게이고": 27, "히가시노 게이고": 35}) == "히가시노 게이고"
    assert display_of({"나": 3, "가": 3}) == "가"  # 동률 tie-break 는 사전순(결정성)


# ── 회귀: 역자가 달라도 같은 작가면 배지가 붙는다 ────────────────────────
def test_badge_for_author_matches_across_different_translators():
    seed = frozenset(split_authors("히가시노 게이고, 양윤옥 옮김"))
    cand = {"book_id": 1, "authors": "히가시노게이고, 김난주 옮김", "pop_rank": 3}
    hit = badge_for(cand, criterion="author", seed_authors=seed)
    assert hit == Badge("author", "히가시노게이고 작가")
    other = {"book_id": 2, "authors": "김초엽, 김난주 옮김", "pop_rank": 4}
    assert badge_for(other, criterion="author", seed_authors=seed) is None


def test_badge_for_author_does_not_match_translator_only_overlap():
    seed = frozenset(split_authors("히가시노 게이고, 양윤옥 옮김"))
    assert seed == frozenset({"히가시노 게이고"})  # 역자 양윤옥 은 시드에 들어가지 않는다
    cand = {"book_id": 3, "authors": "양윤옥 지음", "pop_rank": 5}
    assert badge_for(cand, criterion="author", seed_authors=seed) is None


# ── 다중 기준 + 고른 작가 (attach_badges) ────────────────────────────────
# 실측 결함: 작가를 첫 기준으로 고르면 배지가 사라졌다 — 고른 작가가 seed_authors 에 없고,
# 첫 기준이 실패해도 다음 기준으로 넘어가지 않았다(대조군보다 나빠졌다).
PICKED = "김동식"
SEED_ID = 100
BOOKS = {
    SEED_ID: {"book_id": SEED_ID, "authors": "시드 저자", "pop_rank": 500},
    1: {"book_id": 1, "authors": f"{PICKED} 지음", "pop_rank": 1953, "title": "하나의 인간"},
    2: {"book_id": 2, "authors": f"{PICKED}, 아무개 옮김", "pop_rank": 77, "title": "회색 인간"},
    3: {"book_id": 3, "authors": "남의 작가", "pop_rank": 42, "title": "남의 책"},
    4: {"book_id": 4, "authors": "무순위 작가", "title": "순위 없는 책"},
}


class _CountingCat:
    """meta 호출 횟수를 센다 — 기준이 늘어도 시드 1회 + 전 행 1회여야 한다."""

    def __init__(self) -> None:
        self.meta_calls = 0

    def meta(self, book_ids):
        self.meta_calls += 1
        return [BOOKS[b] for b in book_ids if b in BOOKS]

    def popular(self, categories=(), n=50):
        return list(BOOKS)[:n]

    def eligible(self, book_ids):
        return list(book_ids)


def _rows(*book_ids: int) -> tuple[Row, ...]:
    items = tuple(
        ScoredItem(book_id=b, score=1.0, position=i, authors=BOOKS[b].get("authors"))
        for i, b in enumerate(book_ids)
    )
    return (Row(row_id="persona_shelf", title="취향 책장", purpose="discover", items=items),)


def _texts(rows) -> list[str | None]:
    return [(i.badge.text if i.badge else None) for r in rows for i in r.items]


def test_attach_badges_criteria_falls_through_to_next_criterion():
    cat = _CountingCat()
    out = attach_badges(
        _rows(1, 3),
        cat,
        "author",
        (SEED_ID,),
        criteria=("author", "bestseller"),
        picked_authors=(PICKED,),
    )
    # 고른 작가 책은 작가 배지, 아닌 책은 두 번째 기준으로 폴스루
    assert _texts(out) == [f"{PICKED} 작가", "인기 42위"]


def test_attach_badges_picked_authors_need_not_be_seed_authors():
    cat = _CountingCat()
    out = attach_badges(_rows(2), cat, "author", (SEED_ID,), criteria=("author",),
                        picked_authors=(PICKED,))  # fmt: skip
    assert _texts(out) == [f"{PICKED} 작가"]  # 시드 저자는 '시드 저자' 뿐이다
    plain = attach_badges(_rows(2), _CountingCat(), "author", (SEED_ID,))
    assert _texts(plain) == [None]  # picked_authors 없이는 여전히 안 붙는다


def test_attach_badges_criteria_order_is_priority():
    out = attach_badges(
        _rows(1),
        _CountingCat(),
        "bestseller",
        (SEED_ID,),
        criteria=("bestseller", "author"),
        picked_authors=(PICKED,),
    )
    assert _texts(out) == ["인기 1953위"]  # 첫 기준이 성공하면 작가 배지를 보지 않는다


def test_attach_badges_empty_criteria_matches_single_criterion_path():
    rows = _rows(1, 3)
    single = attach_badges(rows, _CountingCat(), "bestseller", (SEED_ID,))
    multi = attach_badges(rows, _CountingCat(), "bestseller", (SEED_ID,), criteria=())
    assert _texts(single) == _texts(multi) == ["인기 1953위", "인기 42위"]


def test_attach_badges_meta_calls_unchanged_when_criteria_grow():
    one, many = _CountingCat(), _CountingCat()
    attach_badges(_rows(1, 2, 3), one, "author", (SEED_ID,), picked_authors=(PICKED,))
    attach_badges(
        _rows(1, 2, 3),
        many,
        "author",
        (SEED_ID,),
        criteria=("author", "review", "bestseller", "buzz"),
        picked_authors=(PICKED,),
    )
    assert one.meta_calls == many.meta_calls == 2  # 시드 1회 + 전 행 1회


def test_attach_badges_none_criterion_and_empty_criteria_returns_rows_unchanged():
    rows = _rows(1, 3)
    assert attach_badges(rows, _CountingCat(), None, (SEED_ID,), criteria=()) == tuple(rows)
    # 기준이 전부 실패하면 배지는 None (pop_rank 결측 + 작가 불일치)
    out = attach_badges(_rows(4), _CountingCat(), "author", (SEED_ID,),
                        criteria=("author", "bestseller"), picked_authors=(PICKED,))  # fmt: skip
    assert _texts(out) == [None]
