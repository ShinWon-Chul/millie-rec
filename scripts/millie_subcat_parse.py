"""밀리 3depth(세부 카테고리) 링크·도서 id 파서 + index.tsv 읽기/쓰기 — Playwright 없음.

밀리 분류는 2depth(카탈로그 `categories` 29종) 아래 3depth 가 있다(실측 2026-09-06).
2depth 페이지 `/v3/search/2depth/<seq2>` 의 앵커 중 `/v3/search/3depth/<seq3>/?parentSeq=<seq2>`
가 3depth 이고, `op=total`(전체보기)·`op=best`(인기 도서)는 3depth 가 아니다.
"""

from __future__ import annotations

import re
from pathlib import Path

from millie_review_parse import UA  # noqa: F401 — 수집기가 같은 식별 UA 를 쓴다

DEPTH2_URL = "https://www.millie.co.kr/v3/search/2depth/{seq2}?nav_hidden=y"
DEPTH3_URL = "https://www.millie.co.kr/v3/search/3depth/{seq3}/?parentSeq={seq2}&nav_hidden=y"
BLOCK_RE = re.compile(r"접속이 일시적으로 제한|비정상적인 접근")
DEPTH3_RE = re.compile(r"/v3/search/3depth/(\d+)/?\?[^\"']*parentSeq=(\d+)")
BOOK_RE = re.compile(r"/v4/book/([0-9a-f]{16})")
LOGIN_WALL_MAX = 100  # 비로그인 3depth 목록 상한(실측 100, "로그인하고 더 보기")

# 카탈로그 category 라벨 → 밀리 2depth seq (도서 페이지 29종 실측 2026-09-06)
CATEGORY_SEQ2: dict[str, str] = {
    "IT": "2068",
    "경제경영": "1319",
    "과학": "1312",
    "도슨트북": "2137",
    "디즈니": "2032",
    "라이프스타일": "1353",
    "만화": "1827",
    "매거진": "1610",
    "미분류": "1395",
    "밀리 오리지널": "1705",
    "부모": "1343",
    "빨간펜 동화": "2131",
    "사회": "1253",
    "세계문학전집": "1194",
    "소설": "1223",
    "어린이": "1785",
    "에세이/시": "1332",
    "여행": "1269",
    "역사": "1336",
    "오디오북": "1474",
    "오브제북": "2141",
    "외국어": "2076",
    "웹툰/웹소설": "2170",
    "인문": "1240",
    "자기계발": "1287",
    "종교": "1362",
    "챗북": "1779",
    "철학": "1208",
    "청소년": "2110",
}


def parse_depth3_links(anchors: list[tuple[str, str]], seq2: str) -> list[tuple[str, str]]:
    """(href, text) 앵커 → 이 parentSeq 의 (seq3, 이름) 페이지 순서·중복 제거."""
    out: list[tuple[str, str]] = []
    seen: set[str] = set()
    for href, text in anchors:
        if not href or "op=" in href:
            continue
        m = DEPTH3_RE.search(href)
        name = " ".join((text or "").split())
        if not m or m.group(2) != seq2 or m.group(1) in seen or not name:
            continue
        seen.add(m.group(1))
        out.append((m.group(1), name))
    return out


def extract_book_ids(hrefs: list[str]) -> list[str]:
    """href 목록 → 16-hex millie_id, DOM 순서(=인기순) 유지·중복 제거."""
    out: list[str] = []
    seen: set[str] = set()
    for h in hrefs:
        m = BOOK_RE.search(h or "")
        if m and m.group(1) not in seen:
            seen.add(m.group(1))
            out.append(m.group(1))
    return out


INDEX_HEADER = "category\tdepth2_seq\tdepth3_seq\tsubcategory\n"


def read_index(path: Path) -> list[tuple[str, str, str, str]]:
    rows = []
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines()):
        c = line.split("\t")
        if i and len(c) == 4:
            rows.append((c[0], c[1], c[2], c[3]))
    return rows


def write_index(path: Path, rows: list[tuple[str, str, str, str]]) -> None:
    path.write_text(INDEX_HEADER + "".join("\t".join(r) + "\n" for r in rows), encoding="utf-8")
