"""onboarding_api.py — 계약(스키마 파싱) · 정확성(라운드로빈) · 안전성(상한·catalog None).

Phase 5 '서빙 Must 완성'(.planning/ROADMAP.md) Plan 05-04. 05-CONTEXT D-14·D-15.
가짜는 파일마다 복제한다(tests/serving/test_api_weights.py 관례).
"""

import json
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from millie_rec.contracts import DB_FILENAME
from millie_rec.serving.db import Database
from millie_rec.serving.onboarding_api import build_router
from millie_rec.serving.schemas import CandidateSet, OnboardingMeta

CATS = ("소설", "에세이", "경제경영", "인문")  # tests/conftest.py::_sample_book 순환
FORMATS = ("전자책", "오디오북", "챗북")
INELIGIBLE = {18, 19, 20}  # conftest 자격 없는 3권(외부 호스트·title None·성인 표지)
FIXED_NOW = datetime(2026, 9, 7, 12, 0, 0, tzinfo=UTC)


def _iso(dt: datetime) -> str:
    return dt.isoformat(timespec="seconds").replace("+00:00", "Z")


def _no_trace(r) -> bool:
    return "Traceback" not in r.text


class _Cat:
    """20권 합성 카탈로그 + extra_it 권의 IT 책. popular 는 eligible 을 거르지 않는다."""

    def __init__(self, extra_it: int = 0) -> None:
        self.popular_calls = 0
        self.books = [
            {
                "book_id": i,
                "title": f"밀리 표본 도서 {i}",
                "authors": f"저자 {i}",
                "image_url": f"https://img.millie.co.kr/cover/{i}.jpg",
                "book_format": FORMATS[(i - 1) % len(FORMATS)],
                "categories": [CATS[(i - 1) % len(CATS)]],
                "pop_rank": i,
            }
            for i in range(1, 21)
        ] + [
            {
                "book_id": i,
                "title": f"IT 표본 도서 {i}",
                "authors": "저자 IT",
                "image_url": f"https://img.millie.co.kr/cover/{i}.jpg",
                "book_format": "전자책",
                "categories": ["IT"],
                "pop_rank": i,
            }
            for i in range(21, 21 + extra_it)
        ]

    def meta(self, book_ids: Sequence[int]) -> list[dict]:
        by = {b["book_id"]: b for b in self.books}
        return [by[b] for b in book_ids if b in by]

    def popular(self, categories: Sequence[str] = (), n: int = 50) -> list[int]:
        self.popular_calls += 1
        want = set(categories)
        return [b["book_id"] for b in self.books if not want or want & set(b["categories"])][:n]

    def eligible(self, book_ids: Sequence[int]) -> list[int]:
        return [b for b in book_ids if b not in INELIGIBLE]


def _build(tmp_path: Path, catalog=None) -> tuple[Database, TestClient]:
    db = Database(tmp_path / DB_FILENAME)
    db.apply_schema()
    app = FastAPI()
    app.include_router(build_router(db=db, catalog=catalog, now=lambda: FIXED_NOW))
    return db, TestClient(app)


@pytest.fixture
def cat() -> _Cat:
    return _Cat()


# ── 계약 ────────────────────────────────────────────────────────────────
def test_meta_onboarding_parses_and_lists_criteria_reading_times(tmp_path: Path, cat: _Cat):
    _, client = _build(tmp_path, cat)
    r = client.get("/api/meta/onboarding")
    assert r.status_code == 200, r.text
    out = OnboardingMeta.model_validate(r.json())
    assert out.survey_variant == "v1"
    assert len(out.reading_times) == 5 and out.reading_times[0] == "아침, 하루를 시작할 때"
    assert [c.id for c in out.criteria] == ["author", "publisher", "bestseller", "buzz", "review"]
    assert out.criteria[2].label == "베스트셀러"


def test_meta_categories_supported_when_eligible_ge_20_subcategories_static_and_cached(
    tmp_path: Path, cat: _Cat
):
    _, client = _build(tmp_path, cat)
    out = OnboardingMeta.model_validate(client.get("/api/meta/onboarding").json())
    assert {c.name for c in out.categories} == set(CATS)
    assert all(c.supported is False for c in out.categories)  # 각 5권 < 20
    client.get("/api/meta/onboarding")
    assert cat.popular_calls == 1  # 라우터 클로저 1회 캐시(revision C11)

    rich = _Cat(extra_it=25)
    _, client2 = _build(tmp_path / "b", rich)
    out2 = OnboardingMeta.model_validate(client2.get("/api/meta/onboarding").json())
    by = {c.name: c for c in out2.categories}
    assert by["IT"].supported is True and len(by["IT"].subcategories) == 6
    assert len(by["소설"].subcategories) == 7 and by["에세이"].subcategories == []


def test_meta_without_catalog_has_empty_categories(tmp_path: Path):
    _, client = _build(tmp_path, None)
    out = OnboardingMeta.model_validate(client.get("/api/meta/onboarding").json())
    assert out.categories == [] and len(out.reading_times) == 5


def test_candidates_round_robin_pop_rank_and_persists_candidate_set(tmp_path: Path, cat: _Cat):
    db, client = _build(tmp_path, cat)
    r = client.get("/api/candidates/onboarding", params={"categories": "소설,에세이", "n": 6})
    assert r.status_code == 200, r.text
    out = CandidateSet.model_validate(r.json())
    assert out.candidate_set_id.startswith("cand_") and len(out.candidate_set_id) == 11
    assert out.survey_variant == "v1" and out.created_at == _iso(FIXED_NOW)
    assert [i.book_id for i in out.items] == [1, 2, 5, 6, 9, 10]
    assert [i.position for i in out.items] == [0, 1, 2, 3, 4, 5]
    assert all(i.title and i.book_format in FORMATS for i in out.items)
    rows = (
        db.connect()
        .execute("SELECT candidate_set_id, user_key, book_ids, survey_variant FROM candidate_sets")
        .fetchall()
    )
    assert len(rows) == 1
    assert rows[0][0] == out.candidate_set_id and rows[0][1] is None
    assert json.loads(rows[0][2]) == [1, 2, 5, 6, 9, 10] and rows[0][3] == "v1"


# ── 정확성 ──────────────────────────────────────────────────────────────
def test_candidates_three_categories_share_evenly_and_exclude_ineligible(tmp_path: Path, cat: _Cat):
    _, client = _build(tmp_path, cat)
    r = client.get(
        "/api/candidates/onboarding", params={"categories": "소설,경제경영,인문", "n": 9}
    )
    ids = [i.book_id for i in CandidateSet.model_validate(r.json()).items]
    assert ids == [1, 3, 4, 5, 7, 8, 9, 11, 12]  # 세 카테고리 각 3권(D-15 라운드로빈)
    solo = client.get("/api/candidates/onboarding", params={"categories": "에세이", "n": 6})
    solo_ids = [i.book_id for i in CandidateSet.model_validate(solo.json()).items]
    assert solo_ids == [2, 6, 10, 14]  # 18 은 자격 없음
    assert not INELIGIBLE & set(ids + solo_ids)


# ── 안전성 ──────────────────────────────────────────────────────────────
def test_candidates_limits_422_unknown_category_empty(tmp_path: Path, cat: _Cat):
    _, client = _build(tmp_path, cat)
    assert (
        client.get(
            "/api/candidates/onboarding", params={"categories": "소설", "n": 100}
        ).status_code
        == 422
    )
    assert (
        client.get("/api/candidates/onboarding", params={"categories": "소설", "n": 0}).status_code
        == 422
    )
    over = client.get("/api/candidates/onboarding", params={"categories": "소설,에세이,인문,과학"})
    assert over.status_code == 422
    assert over.json()["detail"][0]["loc"] == ["query", "categories"]
    unknown = client.get("/api/candidates/onboarding", params={"categories": "없는분류"})
    assert unknown.status_code == 200 and CandidateSet.model_validate(unknown.json()).items == []


def test_candidates_without_catalog_is_200_empty_no_trace(tmp_path: Path):
    _, client = _build(tmp_path, None)
    r = client.get("/api/candidates/onboarding", params={"categories": "소설,에세이"})
    assert r.status_code == 200 and _no_trace(r)
    assert CandidateSet.model_validate(r.json()).items == []
