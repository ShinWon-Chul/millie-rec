"""popularity_kr — 계약(컬럼·segment) · 정확성(rank == pop_rank · score == shelf_count).

안전성: 결측 shelf 0.0 · rank 1..N 연속.
"""

import importlib.util
import re
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "tests" / "fixtures" / "millie" / "sample_records.jsonl"

# 스크립트 상수를 import 하지 않고 손으로 적어 둔다(결정 D-15 'popularity_kr 스키마 지금 고정'
# (.planning/phases/03-millie-catalog/03-CONTEXT.md)).
EXPECTED_COLUMNS = ["book_id", "segment", "score", "rank"]
N_FIXTURE_BOOKS = 12
FIRST_RANK, LAST_RANK = 1, 12  # 픽스처 pop_rank 1 = 불편한 편의점(shelf 9,814), 12 = shelf 결측
FIRST_SHELF_COUNT = 9814.0


def _load(name: str):
    """scripts/ 는 패키지가 아니므로 경로로 직접 로드한다."""
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def pop_mod():
    return _load("build_millie_popularity")


@pytest.fixture(scope="module")
def books(tmp_path_factory) -> pd.DataFrame:
    out = tmp_path_factory.mktemp("processed")
    _load("build_millie_catalog").build(FIXTURE, out, raw_dir=out)
    return pd.read_parquet(out / "books_kr.parquet")


@pytest.fixture(scope="module")
def pop(pop_mod, books) -> pd.DataFrame:
    return pop_mod.build(books)


def _all_rows(pop: pd.DataFrame) -> pd.DataFrame:
    """단정은 segment == 'all' 행 위에서만 — Plan 07 세그먼트 행이 붙어도 안 바뀐다(D-15)."""
    return pop[pop["segment"] == "all"]


def test_popularity_columns_and_all_segment(pop):
    assert list(pop.columns) == EXPECTED_COLUMNS
    assert "all" in set(pop["segment"])
    all_rows = _all_rows(pop)
    assert len(all_rows) == N_FIXTURE_BOOKS
    assert all_rows["book_id"].is_unique


def test_rank_equals_books_pop_rank(pop, books):
    """인기 순위 정본은 books_kr.pop_rank 1곳 — 여기서 재계산하지 않는다."""
    all_rows = _all_rows(pop)
    assert all_rows.set_index("book_id")["rank"].to_dict() == (
        books.set_index("book_id")["pop_rank"].astype(int).to_dict()
    )


def test_rank_is_contiguous_from_one(pop):
    assert sorted(_all_rows(pop)["rank"]) == list(range(1, N_FIXTURE_BOOKS + 1))


def test_score_is_shelf_count_desc_with_missing_zero(pop, books):
    """score = shelf_count, 결측(NO_SHELF_BOOK)은 0.0 이고 rank 순으로 단조 감소한다."""
    all_rows = _all_rows(pop)
    by_rank = all_rows.set_index("rank")["score"].to_dict()
    assert by_rank.get(FIRST_RANK) == FIRST_SHELF_COUNT
    assert by_rank.get(LAST_RANK) == 0.0
    assert all_rows.sort_values("rank")["score"].is_monotonic_decreasing
    assert pop["score"].dtype.kind == "f"


def test_main_writes_parquet(tmp_path, pop_mod, books, monkeypatch):
    books_path, out_path = tmp_path / "b.parquet", tmp_path / "p.parquet"
    books.to_parquet(books_path, index=False)
    monkeypatch.setattr(
        sys, "argv", ["build_millie_popularity", "--books", str(books_path), "--out", str(out_path)]
    )
    pop_mod.main()
    written = pd.read_parquet(out_path)
    assert list(written.columns) == EXPECTED_COLUMNS
    assert len(written[written["segment"] == "all"]) == N_FIXTURE_BOOKS


# ── Plan 07(DATA-08) 연령×성별 세그먼트 인기 ────────────────────────────────
# 결정 D-15 'popularity_kr 는 all 만 Must, 12세그먼트는 Should 꼬리로 같은 파일 증분'
# (.planning/phases/03-millie-catalog/03-CONTEXT.md).
SEGMENT_LABEL_RE = re.compile(r"^(10대|20대|30대|40대|50대|60대~) (남성|여성)$")
SEG_DIST_MISSING_MILLIE_ID = "8192a3b4c5d60009"  # 픽스처 seg_dist 결측 책
NO_SHELF_MILLIE_ID = "92a3b4c5d6e7000a"  # 픽스처 shelf 결측 + seg_dist 있음
FIRST_BOOK_TOP_SHARE = 0.31  # FIRST_BOOK seg_dist["40대"]["여"]


def _seg_frame() -> pd.DataFrame:
    """손계산 3행 — all 은 A>B>C, '10대 남성'은 B>A, '40대 여성'은 A>B."""
    return pd.DataFrame(
        {
            "book_id": [1, 2, 3],
            "shelf_count": [1000, 900, 800],
            "pop_rank": [1, 2, 3],
            "seg_dist": [
                '{"10대": {"남": 10, "여": 10}, "40대": {"남": 5, "여": 75}}',
                '{"10대": {"남": 50, "여": 40}, "40대": {"남": 5, "여": 5}}',
                None,
            ],
        }
    )


def _cell(seg: pd.DataFrame, segment: str, book_id: int, column: str):
    row = seg[(seg["segment"] == segment) & (seg["book_id"] == book_id)]
    assert len(row) == 1, (segment, book_id, len(row))
    return row[column].iloc[0]


def test_segment_rows_labels_are_millie_style(pop_mod):
    """라벨 = 연령 키 + ' ' + 남성/여성 — top_segment('40대 여성')와 같은 표기."""
    seg = pop_mod.segment_rows(_seg_frame())
    assert list(seg.columns) == EXPECTED_COLUMNS
    assert set(seg["segment"]) == {"10대 남성", "10대 여성", "40대 남성", "40대 여성"}


def test_segment_score_is_shelf_times_share(pop_mod):
    """score = shelf_count × seg_dist[연령][성별](적재 계획 02 §6 행 소스 분리)."""
    seg = pop_mod.segment_rows(_seg_frame())
    assert float(_cell(seg, "10대 남성", 2, "score")) == 900 * 50
    assert float(_cell(seg, "40대 여성", 1, "score")) == 1000 * 75
    assert seg["score"].dtype.kind == "f"


def test_segment_rank_is_contiguous_and_can_differ_from_all(pop_mod):
    """세그먼트 1위가 all 1위(book 1)와 다르다 — fallback level 2 가 전역 인기와 갈릴 전제."""
    seg = pop_mod.segment_rows(_seg_frame())
    assert int(_cell(seg, "10대 남성", 2, "rank")) == 1
    assert int(_cell(seg, "10대 남성", 1, "rank")) == 2
    assert int(_cell(seg, "40대 여성", 1, "rank")) == 1
    for label in set(seg["segment"]):
        ranks = sorted(seg[seg["segment"] == label]["rank"])
        assert ranks == list(range(1, len(ranks) + 1)), label


def test_books_without_seg_dist_only_in_all(pop_mod):
    """seg_dist 결측 책은 all 행에만 남고, all 행 값은 Plan 04 결과 그대로다."""
    full = pop_mod.build(_seg_frame())
    all_rows = _all_rows(full)
    seg_only = full[full["segment"] != "all"]
    assert set(all_rows["book_id"]) == {1, 2, 3}
    assert set(seg_only["book_id"]) == {1, 2}
    assert 3 not in set(seg_only["book_id"])
    assert all_rows.set_index("book_id")["rank"].to_dict() == {1: 1, 2: 2, 3: 3}
    assert all_rows.set_index("book_id")["score"].to_dict() == {1: 1000.0, 2: 900.0, 3: 800.0}


def test_fixture_build_has_all_plus_segments(pop, books):
    """픽스처 12권: all + 세그먼트 라벨 정규식 · 손계산 score · 결측 제외 · shelf 결측 0.0 꼴찌."""
    by_millie = books.set_index("millie_id")["book_id"].astype(int).to_dict()
    seg_rows = pop[pop["segment"] != "all"]
    assert "all" in set(pop["segment"])
    assert [s for s in set(seg_rows["segment"]) if not SEGMENT_LABEL_RE.match(s)] == []
    assert float(_cell(seg_rows, "40대 여성", 1, "score")) == pytest.approx(
        FIRST_SHELF_COUNT * FIRST_BOOK_TOP_SHARE
    )
    assert by_millie[SEG_DIST_MISSING_MILLIE_ID] not in set(seg_rows["book_id"])
    no_shelf_rows = seg_rows[seg_rows["book_id"] == by_millie[NO_SHELF_MILLIE_ID]]
    assert len(no_shelf_rows) > 0
    assert set(no_shelf_rows["score"]) == {0.0}
    for label, rank in zip(no_shelf_rows["segment"], no_shelf_rows["rank"], strict=True):
        assert int(rank) == len(seg_rows[seg_rows["segment"] == label]), label
