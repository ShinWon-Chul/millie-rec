"""authors_api.py — 계약(AuthorSet 파싱) · 정확성(대표 책·가나다) · 안전성(상한·catalog None).

가짜는 파일마다 복제한다(tests/serving/test_onboarding_api.py 관례). DB 는 쓰지 않는다 —
작가 목록은 저장하지 않으므로 build_router 가 db 를 받지 않는다.
"""

from collections.abc import Sequence
from datetime import UTC, datetime

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from millie_rec.serving.authors_api import build_router
from millie_rec.serving.schemas import AuthorSet

FIXED_NOW = datetime(2026, 9, 7, 12, 0, 0, tzinfo=UTC)
# (book_id, authors, pop_rank, category) — 1권짜리(외톨이작가)와 비인물(편집부)은 빠져야 한다
BOOKS = (
    (1, "히가시노 게이고, 양윤옥 옮김", 5, "소설"),
    (2, "히가시노게이고, 김난주 옮김", 2, "소설"),
    (3, "김초엽", 3, "소설"),
    (4, "김초엽 지음", 9, "소설"),
    (5, "B. A. 패리스, 이수영 옮김", 1, "소설"),
    (6, "B. A. 패리스", 8, "소설"),
    (7, "강보라", 4, "소설"),
    (8, "강보라 글", 10, "에세이"),
    (9, "외톨이작가", 6, "소설"),
    (10, "편집부", 7, "소설"),
    (11, "히가시노 게이고", 12, "소설"),
)


class _Cat:
    """authors 문자열만 다른 11권. popular 는 eligible 을 거르지 않는다."""

    def __init__(self) -> None:
        self.popular_calls = 0
        self.books = [
            {
                "book_id": bid,
                "title": f"표본 도서 {bid}",
                "authors": authors,
                "image_url": f"https://img.millie.co.kr/cover/{bid}.jpg",
                "categories": [cat],
                "pop_rank": rank,
            }
            for bid, authors, rank, cat in BOOKS
        ]

    def meta(self, book_ids: Sequence[int]) -> list[dict]:
        by = {b["book_id"]: b for b in self.books}
        return [by[b] for b in book_ids if b in by]

    def popular(self, categories: Sequence[str] = (), n: int = 50) -> list[int]:
        self.popular_calls += 1
        want = set(categories)
        return [b["book_id"] for b in self.books if not want or want & set(b["categories"])][:n]

    def eligible(self, book_ids: Sequence[int]) -> list[int]:
        return list(book_ids)


def _client(catalog=None) -> TestClient:
    app = FastAPI()
    app.include_router(build_router(catalog=catalog, now=lambda: FIXED_NOW))
    return TestClient(app)


@pytest.fixture
def cat() -> _Cat:
    return _Cat()


def _get(client: TestClient, **params) -> AuthorSet:
    r = client.get("/api/candidates/authors", params=params)
    assert r.status_code == 200, r.text
    return AuthorSet.model_validate(r.json())


# ── 계약 ────────────────────────────────────────────────────────────────
def test_authors_parses_and_sorts_hangul_first_then_alphabetically(cat: _Cat):
    client = _client(cat)
    out = _get(client, categories="소설", n=60)
    assert out.survey_variant == "v1"
    assert out.created_at == "2026-09-07T12:00:00Z"
    assert [i.name for i in out.items] == ["강보라", "김초엽", "히가시노 게이고", "B. A. 패리스"]
    _get(client, categories="소설")
    assert cat.popular_calls == 1  # 인덱스는 첫 요청에 1회(onboarding_api C11 관례)


# ── 정확성 ──────────────────────────────────────────────────────────────
def test_authors_excludes_single_book_and_non_person(cat: _Cat):
    names = {i.name for i in _get(_client(cat), categories="소설").items}
    assert "외톨이작가" not in names and "편집부" not in names  # 1권 · 비인물
    assert names == {"강보라", "김초엽", "히가시노 게이고", "B. A. 패리스"}


def test_authors_representative_book_is_min_pop_rank_and_counts_all_books(cat: _Cat):
    by = {i.name: i for i in _get(_client(cat), categories="소설").items}
    top = by["히가시노 게이고"]
    assert top.book_id == 2 and top.title == "표본 도서 2"  # pop_rank 2 < 5 < 12
    assert top.image_url == "https://img.millie.co.kr/cover/2.jpg" and top.n_books == 3
    assert by["강보라"].book_id == 7 and by["강보라"].n_books == 2  # 에세이 책까지 센다


def test_authors_takes_top_n_by_pop_rank_before_hangul_sort(cat: _Cat):
    out = _get(_client(cat), categories="소설", n=2)
    # 대표 책 pop_rank 상위 2명(패리스 1 · 히가시노 2) 을 고른 뒤 가나다 정렬
    assert [i.name for i in out.items] == ["히가시노 게이고", "B. A. 패리스"]


def test_authors_filters_by_requested_categories(cat: _Cat):
    assert [i.name for i in _get(_client(cat), categories="에세이").items] == ["강보라"]


# ── 안전성 ──────────────────────────────────────────────────────────────
def test_authors_without_catalog_is_200_empty(cat: _Cat):
    out = _get(_client(None), categories="소설")
    assert out.items == [] and out.survey_variant == "v1"


def test_authors_limits_422(cat: _Cat):
    client = _client(cat)
    over = client.get("/api/candidates/authors", params={"categories": "소설,에세이,인문,과학"})
    assert over.status_code == 422
    assert over.json()["detail"][0]["loc"] == ["query", "categories"]
    assert (
        client.get("/api/candidates/authors", params={"categories": "소설", "n": 61}).status_code
        == 422
    )
    assert (
        client.get("/api/candidates/authors", params={"categories": "소설", "n": 0}).status_code
        == 422
    )
