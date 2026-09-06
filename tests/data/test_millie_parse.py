"""밀리 도서 페이지 파서 단위 테스트 — 축약 픽스처 8건 (설계 §7).

픽스처는 실제 렌더 텍스트를 축약한 것이며 리뷰 본문·회원 필명·큐레이터 실명은 제거했다.
"""

import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from millie_parse import (  # noqa: E402
    CATEGORY_WHITELIST,
    MILLIE_LABELS,
    extract_book_links,
    parse_book_text,
)

FIXTURES = ROOT / "tests" / "fixtures" / "millie"

# 픽스처별 기대값: (제목, 카테고리, 출간일, 별점, 완독확률, 예상시간, 라벨, 포맷수, 서재수, 리뷰수)
EXPECTED = {
    "normal_1_소설": ("나무", "소설", "2013.07.25", 4.0, 50, 231, "마니아", 2, 47000, 162),
    "normal_2_에세이_시": (
        "아무튼, 발레",
        "에세이/시",
        "2018.11.30",
        3.8,
        62,
        95,
        "홀릭",
        3,
        6598,
        44,
    ),
    "normal_3_경제경영": (
        "제로 투 원",
        "경제경영",
        "2019.09.25",
        4.4,
        53,
        280,
        "마니아",
        2,
        59000,
        228,
    ),
    "normal_4_x": (
        "마흔에 읽는 손자병법",
        "에세이/시",
        "2012.08.17",
        None,
        50,
        316,
        "마니아",
        1,
        4060,
        10,
    ),
    "variant_header": (
        "2억 빚을 진 내게 우주님이 가르쳐준 운이 풀리는 말버릇",
        "자기계발",
        "2017.08.14",
        4.4,
        67,
        167,
        "밀리 픽",
        3,
        27000,
        134,
    ),
    "chatbook": (
        "도무지 내 맘 같지 않은 사람들과 잘 지내는 법",
        "챗북",
        "2018.07.30",
        None,
        57,
        31,
        "마니아",
        3,
        5128,
        8,
    ),
    "no_completion": ("부활 1", "소설", "2014.01.28", None, None, None, None, 1, 4801, 8),
    "no_rating": ("아리랑 10", "소설", "2020.12.30", None, 94, 394, "밀리 픽", 1, 4307, 5),
    "badge_docent": (
        "12가지 인생의 법칙 (40만 부 기념 스페셜 에디션)",
        "인문",
        "2023.02.10",
        4.1,
        33,
        384,
        "마니아",
        3,
        110000,
        189,
    ),
    "badge_free_chatbook": (
        "따박따박 경제상식 [ETF 첫걸음]",
        "챗북",
        "2025.04.14",
        4.8,
        64,
        21,
        "홀릭",
        1,
        22000,
        23,
    ),
}
NAMES = sorted(EXPECTED)
LEAKS = ("팔로우", "좋아요", "님의 추천", "추천사입니다", "별점을 남겨주세요", "저자 소개")
# 밀리 기능 배지 라벨 실측 7종(03-UAT Test 9 Gaps) — 추측 확장 금지
BADGE_LABELS = (
    "읽던 지점 그대로 이어듣기",
    "도슨트북",
    "무료",
    "오브제북",
    "웹소설",
    "웹툰",
    "오디오웹소설",
)


def _parse(name: str) -> dict:
    text = (FIXTURES / f"{name}.txt").read_text(encoding="utf-8")
    url = re.search(r"# url: (\S+)", text).group(1)
    return parse_book_text(text, url)


def test_all_fixtures_present() -> None:
    assert sorted(p.stem for p in FIXTURES.glob("*.txt")) == NAMES


@pytest.mark.parametrize("name", NAMES)
def test_core_fields(name: str) -> None:
    title, cat, date, rating, prob, minutes, label, n_fmt, shelf, reviews = EXPECTED[name]
    d = _parse(name)
    assert d["title"] == title
    assert d["category"] == cat
    assert d["pub_date"] == date
    assert d["average_rating"] == rating
    assert d["completion_prob"] == prob
    assert d["expected_min"] == minutes
    assert d["millie_label"] == label
    assert len(d["formats"]) == n_fmt
    assert d["shelf_count"] == shelf
    assert d["review_count"] == reviews


@pytest.mark.parametrize("name", NAMES)
def test_identity_and_types(name: str) -> None:
    d = _parse(name)
    assert re.fullmatch(r"[0-9a-f]{16}", d["millie_id"])
    assert d["millie_id"] in d["url"]
    assert isinstance(d["shelf_count"], int)
    assert isinstance(d["review_count"], int)
    assert d["publisher"] and d["authors"]
    assert "지음" not in d["authors"].split("/")[0].split(",")[0]
    assert d["category_in_whitelist"] == (d["category"] in CATEGORY_WHITELIST)
    assert d["millie_label"] is None or d["millie_label"] in MILLIE_LABELS


@pytest.mark.parametrize("name", NAMES)
def test_completion_block_is_all_or_nothing(name: str) -> None:
    d = _parse(name)
    quartet = ("completion_prob", "category_avg_prob", "expected_min", "category_avg_min")
    present = [k for k in quartet if d[k] is not None]
    assert len(present) in (0, 4), present
    if present:
        assert 0 < d["completion_prob"] <= 100
        assert d["expected_min"] > 0


@pytest.mark.parametrize("name", NAMES)
def test_description_and_formats(name: str) -> None:
    d = _parse(name)
    assert d["description"] and 20 <= len(d["description"]) <= 400
    assert d["formats"], "도서 타입 선택 블록이 있으면 formats 는 비지 않는다"
    assert set(d["formats"]) <= {"전자책", "오디오북", "챗북"}
    assert d["formats"] == list(dict.fromkeys(d["formats"]))


@pytest.mark.parametrize("name", NAMES)
def test_best_block(name: str) -> None:
    d = _parse(name)
    assert d["best_category"]
    assert 1 <= len(d["best_titles"]) <= 10
    for best_title, best_author in d["best_titles"]:
        assert best_title and best_author
        assert best_title != d["title"]


@pytest.mark.parametrize("name", NAMES)
def test_segments(name: str) -> None:
    d = _parse(name)
    if d["seg_dist"] is None:
        assert d["top_segment"] is None
        return
    assert set(d["seg_dist"]) == {"10대", "20대", "30대", "40대", "50대", "60대~"}
    total = sum(v["남"] + v["여"] for v in d["seg_dist"].values())
    assert 90 <= total <= 110, total
    assert re.fullmatch(r"\d0대~? (남성|여성)", d["top_segment"])


@pytest.mark.parametrize("name", NAMES)
def test_no_review_or_nickname_leakage(name: str) -> None:
    d = _parse(name)
    blob = " ".join(v for v in d.values() if isinstance(v, str))
    for token in LEAKS:
        assert token not in blob, f"{token} 유출: {name}"
    assert not re.search(r"_\d{4,}", blob), "회원 필명(_숫자) 유출"


def test_missing_blocks_are_none() -> None:
    d = _parse("no_completion")
    for key in ("completion_prob", "expected_min", "millie_label", "seg_dist", "top_segment"):
        assert d[key] is None
    assert _parse("no_rating")["average_rating"] is None


def test_curator_note_is_one_line_without_real_name() -> None:
    text = (
        "로그인\n전자책\n제목\n저자 지음\n출판사\n소설\n2020.01.01\n이 책이 담긴 서재 10\n"
        "<밀리의 발견> 큐레이터 허세진 추천\n짧은 단어에 숨겨진 엄청난 이야기\n"
        "저자 소개\n무시할 본문\n"
    )
    d = parse_book_text(text, "https://www.millie.co.kr/v4/book/0123456789abcdef")
    assert d["curator_note"] == "짧은 단어에 숨겨진 엄청난 이야기"
    assert "허세진" not in d["curator_note"]
    assert len(d["curator_note"]) <= 100


def test_unknown_category_kept_but_flagged() -> None:
    text = "로그인\n전자책\n제목\n저자 지음\n출판사\n신설분야\n2020.01.01\n이 책이 담긴 서재 10\n"
    d = parse_book_text(text, "https://www.millie.co.kr/v4/book/0123456789abcdef")
    assert d["category"] == "신설분야"
    assert d["category_in_whitelist"] is False


def test_empty_text_does_not_raise() -> None:
    d = parse_book_text("", "https://www.millie.co.kr/v4/book/0123456789abcdef")
    assert d["millie_id"] == "0123456789abcdef"
    assert d["title"] is None
    assert d["formats"] == []
    assert d["best_titles"] == []


def test_extract_book_links() -> None:
    hrefs = [
        "/v4/book/0123456789abcdef",
        "https://www.millie.co.kr/v4/book/0123456789abcdef?from=best",
        "https://www.millie.co.kr/v4/book/fedcba9876543210",
        "/v4/awards/2025/bestseller",
        "/v4/book/NOTHEX",
        "",
    ]
    assert extract_book_links(hrefs) == ["0123456789abcdef", "fedcba9876543210"]
    assert extract_book_links([]) == []


def test_login_wall_page_yields_no_header() -> None:
    """헤더 종료 앵커가 없는 페이지(로그인 월)를 본문으로 오인하지 않는다."""
    text = (
        "로그인\n이용 안내\n로그인 후 이용 가능한 서비스입니다.\n"
        "로그인\n회원가입\n고객센터\n이용약관\n"
    )
    d = parse_book_text(text, "https://www.millie.co.kr/v4/book/037440414ca94672")
    for key in ("title", "authors", "publisher", "category", "pub_date"):
        assert d[key] is None
    assert d["category_in_whitelist"] is False


def test_description_ignores_toc_entry_named_book_intro() -> None:
    """목차에 '책 소개' 항목이 있는 페이지에서도 실제 본문을 고른다."""
    text = (
        "로그인\n전자책\n제목\n저자 지음\n출판사\n외국어\n2020.01.01\n이 책이 담긴 서재 10\n"
        "책 추천\n책 소개\n리뷰 14\n"
        "책 소개\n하루 10분, 일본어 어휘도 익히고 문학도 감상하는 일본어 원서 읽기 안내서다.\n"
        "책 소개 더보기\n목차\n책 소개\n저자 소개\n단어풀이\n목차 더보기\n"
    )
    d = parse_book_text(text, "https://www.millie.co.kr/v4/book/04003a1c262241de")
    assert d["description"] is not None
    assert d["description"].startswith("하루 10분")
    assert "단어풀이" not in d["description"]


@pytest.mark.parametrize(
    "name,title,subtitle",
    [
        ("badge_docent", "12가지 인생의 법칙 (40만 부 기념 스페셜 에디션)", "혼돈의 해독제"),
        (
            "badge_free_chatbook",
            "따박따박 경제상식 [ETF 첫걸음]",
            "3화. 재테크 초보도 할 수 있는 ETF 투자 첫걸음",
        ),
    ],
)
def test_badge_header_lines_are_not_title(name: str, title: str, subtitle: str) -> None:
    """헤더 첫 줄이 기능 배지(도슨트북·무료 …)인 페이지 — 배지는 title·subtitle 이 아니다."""
    d = _parse(name)
    assert d["title"] == title
    assert d["subtitle"] == subtitle
    assert d["title"] not in BADGE_LABELS and d["subtitle"] not in BADGE_LABELS


def test_countdown_badge_line_is_not_title() -> None:
    """'종료 D-N' 카운트다운 배지(실측 9건) — 정규식 스킵. 픽스처 텍스트에 한 줄을 끼워 합성."""
    text = (FIXTURES / "badge_docent.txt").read_text(encoding="utf-8")
    text = text.replace("로그인\n", "로그인\n종료 D-4\n", 1)
    d = parse_book_text(text, "https://www.millie.co.kr/v4/book/35d1ad08e9c94e13")
    assert d["title"] == "12가지 인생의 법칙 (40만 부 기념 스페셜 에디션)"
    assert d["subtitle"] == "혼돈의 해독제"
