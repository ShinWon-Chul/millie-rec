"""세그먼트 인기 로더 — 계약(rank 순 고정) · 정확성(상위 n) · 안전성(부재·손상은 None).

폴백 2단계 재료. 실제 artifacts/serving/popularity_kr.json(98,055행 · 13 세그먼트)은 읽지 않고
tmp_path 소형 JSON 으로 검증한다.
"""

import json

from millie_rec.data import SegmentPopularity

SEG_A, SEG_B = "30대 여성", "40대 남성"
ROWS = [
    {"book_id": 11, "segment": SEG_A, "score": 30.0, "rank": 3},
    {"book_id": 12, "segment": SEG_A, "score": 50.0, "rank": 1},
    {"book_id": 21, "segment": SEG_B, "score": 9.0, "rank": 1},
    {"book_id": 13, "segment": SEG_A, "score": 40.0, "rank": 2},
]


def _dir(tmp_path, rows):
    (tmp_path / "popularity_kr.json").write_text(json.dumps(rows), encoding="utf-8")
    return tmp_path


# ── 계약 ────────────────────────────────────────────────────────────────
def test_load_freezes_rank_order_not_file_order(tmp_path):
    sp = SegmentPopularity.load(_dir(tmp_path, ROWS))
    assert sp is not None
    assert sp.ranked(SEG_A, 10) == [12, 13, 11]  # 파일 순서(11, 12, 13)가 아니다


def test_segments_lists_loaded_names(tmp_path):
    sp = SegmentPopularity.load(_dir(tmp_path, ROWS))
    assert sp.segments() == (SEG_A, SEG_B)


# ── 정확성 ──────────────────────────────────────────────────────────────
def test_ranked_returns_top_n_only(tmp_path):
    sp = SegmentPopularity.load(_dir(tmp_path, ROWS))
    assert sp.ranked(SEG_A, 2) == [12, 13]
    assert sp.ranked(SEG_A, 0) == []
    assert sp.ranked(SEG_B, 5) == [21]  # n 이 세그먼트 크기보다 커도 있는 만큼


def test_ranked_unknown_segment_is_empty(tmp_path):
    sp = SegmentPopularity.load(_dir(tmp_path, ROWS))
    assert sp.ranked("50대 여성", 3) == []
    assert sp.ranked("", 3) == []


def test_ranked_is_deterministic_across_calls(tmp_path):
    sp = SegmentPopularity.load(_dir(tmp_path, ROWS))
    assert sp.ranked(SEG_A, 3) == sp.ranked(SEG_A, 3) == [12, 13, 11]


# ── 안전성 ──────────────────────────────────────────────────────────────
def test_load_missing_file_is_none(tmp_path):
    assert SegmentPopularity.load(tmp_path) is None  # 아티팩트 없이도 서버가 뜬다


def test_load_broken_json_or_missing_field_is_none(tmp_path):
    (tmp_path / "popularity_kr.json").write_text("{not json", encoding="utf-8")
    assert SegmentPopularity.load(tmp_path) is None
    assert SegmentPopularity.load(_dir(tmp_path, [{"segment": SEG_A, "rank": 1}])) is None
    assert SegmentPopularity.load(_dir(tmp_path, {"segment": SEG_A})) is None
