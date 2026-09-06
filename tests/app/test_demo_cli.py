"""cli demo(REC-07, D-12·D-13) — --find 부분 일치 · --seeds 표(seed 5 + hybrid_div 1 + α/β/γ +
가드 + 고정 문장) · description 미출력 · 카탈로그 없음 SystemExit.
실 artifacts/serving 은 읽지 않는다.
"""

import re

import pytest

from millie_rec.app.cli import main

HEADER = "| # | 책 | 저자 | 분야 | 난이도 | 근거 |"
FIXED = (
    "데모 카탈로그의 앵커 이웃은 콘텍츠 유사도다. 협업 필터링(Item-KNN)의 Recall·NDCG는 "
    "유저 단위 로그가 있는 Goodbooks(Track A)에서만 측정하며 두 트랙의 숫자를 섞지 않는다."
)


def _run(capsys, *argv: str, serving) -> str:
    main(["demo", *argv, "--serving", str(serving)])
    return capsys.readouterr().out


# ── 계약 ────────────────────────────────────────────────────────────────
def test_find_matches_title_and_author_ignoring_case_and_spaces(capsys, millie_serving_sample):
    out = _run(capsys, "--find", "표본도서 1", serving=millie_serving_sample)
    assert "| book_id | 제목 | 저자 | 분야 |" in out
    assert re.search(r"^\| 1 \|", out, re.M) and "| 10 |" in out
    assert "| 19 |" not in out  # title None → eligible 아님
    out = _run(capsys, "--find", "저자 4", serving=millie_serving_sample)
    assert "| 4 |" in out


def test_seeds_prints_five_anchor_tables_and_hybrid_div_table(capsys, millie_serving_sample):
    out = _run(capsys, "--seeds", "1,2,3,4,5", serving=millie_serving_sample)
    assert out.count("을 좋아하셨다면") == 5
    assert "『밀리 표본 도서 1』" in out
    assert "hybrid_div" in out
    assert out.count(HEADER) == 6  # seed 5 + hybrid_div 1
    assert "alpha" in out and "1.0" in out and "beta" in out
    assert "content" in out  # 근거 셀


# ── 정확성 ──────────────────────────────────────────────────────────────
def test_seeds_output_declares_content_neighbors_and_guard_state(capsys, millie_serving_sample):
    out = _run(capsys, "--seeds", "1,2,3,4,5", serving=millie_serving_sample)
    assert FIXED in out
    assert "이웃은 콘텍츠 유사도(제목·소개 TF-IDF)" in out
    assert "가드" in out and "n_completed=0" in out
    tail = out.split("### hybrid_div 상위")[1]  # 검사 범위는 hybrid_div 절만(앵커 표엔 7 이 정당)
    assert re.search(r"^\| \d+ \| 밀리 표본 도서 (7|14) \|", tail, re.M) is None
    assert "resid_z<−1(millie_index) 0권" in tail


# ── 안전성 ──────────────────────────────────────────────────────────────
def test_seeds_never_prints_description_or_curator_note(capsys, millie_serving_sample):
    out = _run(capsys, "--seeds", "1,2,3", serving=millie_serving_sample)
    assert "description" not in out and "curator_note" not in out
    assert "resid_z" not in out.replace("resid_z<−1(millie_index)", "")  # 내부 수치 미노출


def test_seeds_without_catalog_exits(tmp_path):
    with pytest.raises(SystemExit):
        main(["demo", "--seeds", "1,2", "--serving", str(tmp_path)])
    with pytest.raises(SystemExit):
        main(["demo", "--find", "x", "--serving", str(tmp_path)])
    with pytest.raises(SystemExit):
        main(["demo", "--serving", str(tmp_path)])


def test_row_escapes_pipe_inside_cells():
    """실 카탈로그 저자 문자열의 '|' 가 표 열을 깨뜨렸다(09-06 5권 실측) — 셀 안 '|' 는 전각."""
    from millie_rec.app.demo_cli import _row

    line = _row(1, {"title": "a|b", "authors": "c | d", "categories": ["e|f"]}, "—", "x")
    assert line.count("|") == 7
    assert "a｜b" in line and "c ｜ d" in line
