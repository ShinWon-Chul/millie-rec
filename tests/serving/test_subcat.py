"""취향 세부 분류(밀리 3depth) 반영 — 스냅샷 적재 · context 전달 · 온보딩 후보 정렬.

점수 가산은 ranking 단계다 — tests/ranking/test_subcat_bonus.py.
세부 분류 커버리지가 42.6% 뿐이라 하드 필터가 아니라 "겹치는 책을 앞으로" 만 검사한다.
가짜는 파일마다 복제한다(tests/serving/test_onboarding_api.py 관례).
"""

import json
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from millie_rec.contracts import DB_FILENAME
from millie_rec.serving import subcat
from millie_rec.serving.db import Database
from millie_rec.serving.onboarding_api import build_router
from millie_rec.serving.resolve import Resolved, resolve_user, user_state_of
from millie_rec.serving.schemas import CandidateSet
from millie_rec.serving.state import StateStore

CATS = ("소설", "에세이", "경제경영", "인문")  # tests/conftest.py::_sample_book 순환
INELIGIBLE = {18, 19, 20}
FIXED_NOW = datetime(2026, 9, 7, 12, 0, 0, tzinfo=UTC)
CAND = "/api/candidates/onboarding"
USER = "u_subcat"
SNAP = "snap_sub001"
WANT_ONE = "영화/드라마 원작"
WANT_TWO = "기타 국가 소설"
MARKED = {13: [WANT_ONE], 17: [WANT_TWO, WANT_ONE]}  # 소설 카테고리의 뒤쪽 두 권


class _Cat:
    """20권 합성 카탈로그. MARKED 만 subcategories 를 갖고 나머지는 키가 아예 없다."""

    def __init__(self) -> None:
        self.meta_calls = 0
        self.books = []
        for i in range(1, 21):
            book = {
                "book_id": i,
                "title": f"밀리 표본 도서 {i}",
                "authors": f"저자 {i}",
                "image_url": f"https://img.millie.co.kr/cover/{i}.jpg",
                "book_format": "전자책",
                "categories": [CATS[(i - 1) % len(CATS)]],
                "pop_rank": i,
            }
            if i in MARKED:
                book["subcategories"] = MARKED[i]
            self.books.append(book)

    def meta(self, book_ids: Sequence[int]) -> list[dict]:
        self.meta_calls += 1
        by = {b["book_id"]: b for b in self.books}
        return [by[b] for b in book_ids if b in by]

    def popular(self, categories: Sequence[str] = (), n: int = 50) -> list[int]:
        want = set(categories)
        return [b["book_id"] for b in self.books if not want or want & set(b["categories"])][:n]

    def eligible(self, book_ids: Sequence[int]) -> list[int]:
        return [b for b in book_ids if b not in INELIGIBLE]


@pytest.fixture
def cat() -> _Cat:
    return _Cat()


def _client(tmp_path: Path, catalog) -> TestClient:
    db = Database(tmp_path / DB_FILENAME)
    db.apply_schema()
    app = FastAPI()
    app.include_router(build_router(db=db, catalog=catalog, now=lambda: FIXED_NOW))
    return TestClient(app)


def _ids(response) -> list[int]:
    return [i.book_id for i in CandidateSet.model_validate(response.json()).items]


# ── 계약 ────────────────────────────────────────────────────────────────
def test_resolved_carries_snapshot_subcategories(tmp_path: Path):
    db = Database(tmp_path / DB_FILENAME)
    db.apply_schema()
    db.execute(
        "INSERT INTO users(user_key, created_at, consent, cell, is_new) VALUES(?,?,1,?,1)",
        (USER, "2026-09-06T00:00:00Z", "A"),
    )
    db.execute(
        "INSERT INTO preference_snapshots(snapshot_id, user_key, created_at, categories,"
        " criterion, subcategories, seeds, persona) VALUES(?,?,?,?,?,?,?,?)",
        (
            SNAP,
            USER,
            "2026-09-06T01:00:00Z",
            json.dumps(["소설"], ensure_ascii=False),
            "review",
            json.dumps([WANT_TWO, WANT_ONE], ensure_ascii=False),
            json.dumps([1, 2]),
            "{}",
        ),
    )
    r = resolve_user(db, USER, None)
    assert r.snapshot_id == SNAP and r.categories == ("소설",) and r.seeds == (1, 2)
    assert r.subcategories == (WANT_TWO, WANT_ONE)


def test_user_state_of_puts_subcategories_csv_in_context():
    r = Resolved(USER, True, True, "A", SNAP, (1, 2), ("소설",), subcategories=(WANT_TWO, WANT_ONE))
    with_store = user_state_of(StateStore(), r, "저녁")
    assert with_store.context["subcategories"] == f"{WANT_TWO},{WANT_ONE}"
    assert with_store.context["categories"] == "소설" and with_store.explicit_seeds == (1, 2)
    skeleton = user_state_of(None, r, None)  # store 없는 스켈레톤 경로도 같은 키를 만든다
    assert skeleton.context["subcategories"] == f"{WANT_TWO},{WANT_ONE}"
    assert user_state_of(None, Resolved(USER), None).context["subcategories"] == ""


# ── 정확성 ──────────────────────────────────────────────────────────────
def test_candidates_put_chosen_subcategory_books_first(tmp_path: Path, cat: _Cat):
    client = _client(tmp_path, cat)
    params = {"categories": "소설,에세이", "n": 6, "subcategories": WANT_ONE}
    ids = _ids(client.get("/api/candidates/onboarding", params=params))
    assert ids[:2] == [13, 17]  # 세부 분류 일치 2권이 앞으로
    assert ids == [13, 17, 1, 2, 5, 6]  # 나머지는 기존 라운드로빈 순서 유지


# ── 안전성 ──────────────────────────────────────────────────────────────
def test_candidate_count_unchanged_without_selection_or_with_no_match(tmp_path: Path, cat: _Cat):
    client = _client(tmp_path, cat)
    base = {"categories": "소설,에세이", "n": 6}
    plain = _ids(client.get("/api/candidates/onboarding", params=base))
    assert plain == [1, 2, 5, 6, 9, 10]  # 기존 경로 회귀 방지
    assert _ids(client.get(CAND, params={**base, "subcategories": ""})) == plain
    miss = _ids(client.get(CAND, params={**base, "subcategories": "없는분류"}))
    assert miss == plain  # 매칭 0 이어도 후보 수가 줄지 않는다(하드 필터 아님)


def test_wanted_and_matched_tolerate_missing_and_dirty_values(cat: _Cat):
    assert subcat.wanted(None) == frozenset() and subcat.wanted("") == frozenset()
    assert subcat.wanted(f" {WANT_ONE} , ,{WANT_TWO}") == frozenset({WANT_ONE, WANT_TWO})
    assert subcat.wanted([WANT_ONE, "", WANT_ONE]) == frozenset({WANT_ONE})
    assert subcat.matched({}, {WANT_ONE}) == ()
    assert subcat.matched({"subcategories": None}, {WANT_ONE}) == ()
    assert subcat.matched(cat.books[16], {WANT_ONE, WANT_TWO}) == (WANT_TWO, WANT_ONE)  # meta 순서
    assert subcat.prioritize([9, 13, 1], cat, frozenset()) == [9, 13, 1]
    assert subcat.prioritize([9, 99, 13], cat, {WANT_ONE}) == [13, 9, 99]  # meta 없는 id 도 유지
