"""data/catalog_kr.py — 계약(Protocol 3종 형태) · 정확성(popular·eligible·neighbors·stats·meta
제외키) · 안전성(미지 id·파일 부재·손상)."""

from pathlib import Path

import numpy as np
import pytest

from millie_rec.contracts import BookStats, UserState
from millie_rec.data import BOOKS_KR_JSON, DIR_SERVING, CatalogKR, is_eligible

ELIGIBLE_IDS = list(range(1, 18))  # 18(외부 호스트)·19(title None)·20(성인 표지) 제외


@pytest.fixture(scope="module")
def cat(millie_serving_sample: Path) -> CatalogKR:
    return CatalogKR.load(millie_serving_sample)


# ── 계약 ──
def test_catalog_kr_satisfies_three_protocol_shapes(cat: CatalogKR) -> None:
    rows = cat.meta([1, 2])
    assert len(rows) == 2 and all(isinstance(r, dict) for r in rows)
    pop = cat.popular(n=3)
    assert len(pop) == 3 and all(isinstance(b, int) for b in pop)
    assert cat.eligible([1, 18]) == [1]
    nb = cat.neighbors(1, n=3)
    assert len(nb) == 3
    assert all(isinstance(b, int) and isinstance(w, float) for b, w in nb)
    st = cat.stats([1])
    assert len(st) == 1 and isinstance(st[0], BookStats)
    assert cat.user_level(UserState(None)) is None


# ── 정확성 ──
def test_popular_is_pop_rank_order_of_eligible_only(cat: CatalogKR) -> None:
    assert cat.popular(n=20) == ELIGIBLE_IDS
    assert cat.popular(n=5) == [1, 2, 3, 4, 5]


def test_popular_with_categories_filters_by_intersection(cat: CatalogKR) -> None:
    ids = cat.popular(categories=["소설"], n=50)
    assert ids and ids == sorted(ids)
    assert all("소설" in cat.meta([b])[0]["categories"] for b in ids)
    assert set(ids) <= set(ELIGIBLE_IDS)
    assert cat.popular(categories=["없는분야"]) == []


def test_eligible_rules_title_host_suffix_adult_cover(cat: CatalogKR) -> None:
    assert cat.eligible([1, 17, 18, 19, 20]) == [1, 17]
    assert is_eligible({"title": "x", "image_url": "https://img.millie.co.kr/a.jpg"})
    assert not is_eligible({"title": "x", "image_url": "https://millie.co.kr.evil.com/a.jpg"})
    assert not is_eligible({"title": "x", "image_url": None})
    assert not is_eligible({"title": "", "image_url": "https://cover.millie.co.kr/a.jpg"})
    assert not is_eligible(
        {"title": "x", "image_url": "https://image.millie.co.kr/adult-cover-b.webp"}
    )


def test_neighbors_weight_desc_and_n_cap(cat: CatalogKR) -> None:
    assert cat.neighbors(1, n=3) == [(2, 0.9), (3, 0.8), (4, 0.7)]
    assert len(cat.neighbors(1)) == 5
    assert cat.neighbors(999) == []


def test_stats_maps_book_stats_and_keeps_none_difficulty(cat: CatalogKR) -> None:
    s = cat.stats([2, 15])
    assert len(s) == 2
    assert s[0].book_id == 2
    assert s[0].source == "millie_index"
    assert s[0].completion_prob == 52
    assert s[0].completion_rate == pytest.approx(0.52)
    assert s[0].rating_mean == pytest.approx(3.9)
    assert s[0].difficulty == pytest.approx(1 / (1 + np.exp(s[0].resid_z)), abs=1e-4)
    assert s[1].source == "category_prior"
    assert s[1].difficulty is None
    assert s[1].resid_z == 0.0


def test_meta_returns_rows_in_order_and_drops_excluded_keys(cat: CatalogKR) -> None:
    rows = CatalogKR(
        [
            {
                "book_id": 7,
                "title": "t",
                "image_url": "https://img.millie.co.kr/7.jpg",
                "pop_rank": 1,
                "categories": ["소설"],
                "description": "밀리 저작",
                "curator_note": "x",
                "seg_dist": "{}",
            }
        ]
    ).meta([7])
    assert len(rows) == 1
    row = rows[0]
    assert "description" not in row and "curator_note" not in row and "seg_dist" not in row
    assert row["title"] == "t" and row["pop_rank"] == 1
    assert [r["book_id"] for r in cat.meta([2, 1])] == [2, 1]


# ── 안전성 ──
def test_unknown_ids_are_skipped_not_raised(cat: CatalogKR) -> None:
    assert cat.meta([999]) == []
    assert cat.eligible([999]) == []
    assert cat.stats([999]) == []


def test_load_without_edges_file_gives_empty_neighbors(
    tmp_path: Path, millie_serving_sample: Path
) -> None:
    (tmp_path / BOOKS_KR_JSON).write_text(
        (millie_serving_sample / BOOKS_KR_JSON).read_text(encoding="utf-8"), encoding="utf-8"
    )
    only_books = CatalogKR.load(tmp_path)
    assert only_books.neighbors(1) == []
    assert only_books.popular(n=1) == [1]


def test_load_missing_books_raises_file_not_found(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        CatalogKR.load(tmp_path)


def test_load_corrupt_books_raises_value_error(tmp_path: Path) -> None:
    (tmp_path / BOOKS_KR_JSON).write_text("not json", encoding="utf-8")
    with pytest.raises(ValueError):
        CatalogKR.load(tmp_path)


def test_dir_serving_constant_points_to_artifacts_serving() -> None:
    assert DIR_SERVING.name == "serving"
    assert DIR_SERVING.parent.name == "artifacts"
    assert BOOKS_KR_JSON == "books_kr.json"
