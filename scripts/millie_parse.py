"""밀리의서재 도서 페이지 렌더 텍스트 → dict 파서 (순수 함수, stdlib only).

설계: `.assets/설계서/데이터 소스/02_밀리_데이터_적재_계획.md` §7.
라벨 기반 파싱만 쓴다 — 절대 위치 인덱스에 의존하지 않는다.
저장하지 않는 것: 리뷰 텍스트·회원 필명·큐레이터 실명 (§7 "미저장").
"""

import re

CATEGORY_WHITELIST = frozenset(
    "소설 인문 경제경영 자기계발 에세이/시 라이프스타일 어린이 과학 외국어 철학 "
    "역사 매거진 사회 부모 청소년 종교 IT 여행 만화 웹툰/웹소설".split()
)
FORMAT_TOKENS = ("전자책", "오디오북", "챗북")
MILLIE_LABELS = ("홀릭", "밀리 픽", "히든", "마니아")


def _set(spec: str) -> frozenset[str]:
    return frozenset(spec.split("|"))


# 제목 앞 네비·배지 잡음 (챗북·전자책은 카테고리 자리에도 오므로 '제목 앞' 구간에서만 버린다)
_NAV_NOISE = _set("전자책|오디오북|챗북|종이책|종이책에서 읽던 지점 바로 이어읽기|미서비스|pdf")
# 헤더 블록의 끝 앵커 — 하나도 없으면 도서 페이지가 아니다 (로그인 월·404)
_HEADER_END = (
    "이 책이 담긴 서재",
    "바로 읽기",
    "챗북 읽기",
    "내서재에 담기",
    "성별 · 연령별 인기 분포",
)
_DESC_END = _set(
    "책 소개 더보기|목차|저자 소개|책 정보|출판사 서평|한 줄 리뷰|밀리 완독지수|이 책의 포스트"
)
_BEST_NOISE = _set("전자책|오디오북|챗북|pdf|무료|OPEN|오늘|종이책 구매하러 가기|바로보네|미서비스")

_DATE = re.compile(r"^\d{4}\.\d{2}\.\d{2}$")
_RATING = re.compile(r"^[0-5]\.\d$")
_AGE = re.compile(r"^\d0대~?$")
_NUM = re.compile(r"^\d+(?:\.\d+)?$")
_ID = re.compile(r"/v4/book/([0-9a-f]{16})")


def _lines(text: str) -> list[str]:
    return [ln.replace("\u00a0", " ").strip() for ln in text.splitlines()]


def _find(lines: list[str], *, eq: str | None = None, pref: str | None = None) -> int:
    for i, ln in enumerate(lines):
        if (eq is not None and ln == eq) or (pref is not None and ln.startswith(pref)):
            return i
    return -1


def _first(pattern: str, text: str, cast=int):  # noqa: ANN001, ANN202
    m = re.search(pattern, text)
    return cast(m.group(1)) if m else None


def _shelf_count(raw: str) -> int | None:
    m = re.search(r"이 책이 담긴 서재\s*([\d,.]+)(만)?\+?", raw)
    if not m:
        return None
    n = float(m.group(1).replace(",", ""))
    return int(n * 10000) if m.group(2) else int(n)


def _header(lines: list[str]) -> dict:
    """제목~출간일 헤더 블록. 읽는 순서: 제목 [부제] 저자 [별점] 출판사 카테고리 [출간일]."""
    start = _find(lines, eq="로그인")
    i = start + 1 if start >= 0 else 0
    while i < len(lines) and (not lines[i] or lines[i] in _NAV_NOISE):
        i += 1
    end = -1
    for j in range(i, len(lines)):
        if any(lines[j].startswith(p) for p in _HEADER_END):
            end = j
            break
    out = {k: None for k in ("title", "subtitle", "authors", "publisher", "category", "pub_date")}
    out["average_rating"] = None
    if end < 0:
        return out  # 헤더 종료 앵커 없음 (로그인 월·404 등) → 페이지 전체를 헤더로 오인하지 않는다
    block = [ln for ln in lines[i:end] if ln]
    if not block:
        return out
    if _DATE.match(block[-1]):
        out["pub_date"] = block.pop()
    if len(block) >= 2:
        out["category"] = block.pop()
        out["publisher"] = block.pop()
    if block and _RATING.match(block[-1]):
        out["average_rating"] = float(block.pop())
    if block:
        out["authors"] = re.sub(r"\s*지음(?=\s*[,/]|\s*$)", "", block.pop()).strip()
    if block:
        out["title"] = block[0]
        if len(block) > 1:
            out["subtitle"] = block[1]
    return out


def _pub_date_fallback(lines: list[str]) -> str | None:
    for label in ("전자책 출간일", "종이책 출간일", "출간일"):
        i = _find(lines, eq=label)
        if i >= 0:
            for ln in lines[i + 1 : i + 3]:
                if _DATE.match(ln):
                    return ln
    return None


def _segments(lines: list[str]) -> tuple[dict | None, str | None]:
    i = _find(lines, eq="성별 · 연령별 인기 분포")
    seg = None
    if i >= 0:
        toks = []
        for ln in lines[i + 1 :]:
            if ln.startswith("(단위") or ln in ("남성", "여성"):
                break
            if _AGE.match(ln) or _NUM.match(ln):
                toks.append(ln)
        seg = {}
        for k, tok in enumerate(toks):
            if not _AGE.match(tok):
                continue
            male = toks[k - 1] if k > 0 and _NUM.match(toks[k - 1]) else None
            female = toks[k + 1] if k + 1 < len(toks) and _NUM.match(toks[k + 1]) else None
            if male is not None and female is not None:
                seg[tok] = {"남": float(male), "여": float(female)}
        seg = seg or None
    top = None
    j = _find(lines, eq="1위")
    if j >= 0:
        for ln in lines[j + 1 : j + 3]:
            if re.match(r"^\d0대~? *(남성|여성)$", ln):
                top = ln
                break
    return seg, top


def _millie_label(lines: list[str]) -> str | None:
    for i, ln in enumerate(lines):
        if ln.endswith("분야 평균 대비"):
            for prev in reversed(lines[max(0, i - 3) : i]):
                if prev in MILLIE_LABELS:
                    return prev
    return None


def _curator_note(lines: list[str]) -> str | None:
    i = _find(lines, pref="<밀리의 발견> 큐레이터")
    if i < 0:
        i = _find(lines, pref="〈밀리의 발견〉 큐레이터")
    if i < 0:
        return None
    for ln in lines[i + 1 : i + 4]:
        if ln:
            return ln[:100]
    return None


def _description(lines: list[str]) -> str | None:
    """'책 소개' 헤더는 탭·목차 항목으로도 나타난다 → 후보 중 본문이 가장 긴 것을 고른다."""
    best = ""
    for i, header in enumerate(lines):
        if header != "책 소개":
            continue
        body: list[str] = []
        for ln in lines[i + 1 :]:
            if not ln:
                continue
            if ln in _DESC_END or re.match(r"^리뷰 \d+$", ln) or ln.endswith("더보기"):
                break
            body.append(ln)
        text = " ".join(body).strip()
        if len(text) > len(best):
            best = text
    return best[:400] if len(best) >= 20 else None


def _review_count(lines: list[str]) -> int | None:
    for pattern in (r"^한 줄 리뷰 (\d+)$", r"^리뷰 (\d+)$"):
        for ln in lines:
            m = re.match(pattern, ln)
            if m:
                return int(m.group(1))
    return None


def _formats(lines: list[str]) -> list[str]:
    i = _find(lines, eq="도서 타입 선택")
    if i < 0:
        return []
    out: list[str] = []
    for ln in lines[i + 1 :]:
        if not ln:
            continue
        if ln not in FORMAT_TOKENS:
            break
        if ln not in out:
            out.append(ln)
    return out


def _best(lines: list[str], own_title: str | None) -> tuple[str | None, list[tuple[str, str]]]:
    idx, cat = -1, None
    for i, ln in enumerate(lines):
        m = re.match(r"^(.+) 분야 BEST$", ln)
        if m:
            idx, cat = i, m.group(1)
            break
    if idx < 0:
        return None, []
    items: list[str] = []
    for ln in lines[idx + 1 :]:
        if not ln or ln in _BEST_NOISE:
            continue
        if ln == "도서 타입 선택" or (own_title and ln == own_title):
            break
        items.append(ln)
        if len(items) >= 20:
            break
    pairs = [(items[k], items[k + 1]) for k in range(0, len(items) - 1, 2)]
    return cat, pairs[:10]


def parse_book_text(text: str, url: str) -> dict:
    """렌더 텍스트 1건 → 계약 필드 dict. 블록이 없으면 해당 필드는 None/[]."""
    lines = _lines(text)
    raw = text
    head = _header(lines)
    seg, top = _segments(lines)
    cat = head["category"]
    best_cat, best_titles = _best(lines, head["title"])
    return {
        "millie_id": (_ID.search(url).group(1) if _ID.search(url) else None),
        "url": url,
        "title": head["title"],
        "subtitle": head["subtitle"],
        "authors": head["authors"],
        "publisher": head["publisher"],
        "category": cat,
        "category_in_whitelist": cat in CATEGORY_WHITELIST if cat else False,
        "pub_date": head["pub_date"] or _pub_date_fallback(lines),
        "average_rating": head["average_rating"],
        "shelf_count": _shelf_count(raw),
        "review_count": _review_count(lines),
        "seg_dist": seg,
        "top_segment": top,
        "completion_prob": _first(r"완독할 확률 (\d+)%", raw),
        "category_avg_prob": _first(r"평균 (\d+)% 대비", raw),
        "expected_min": _first(r"완독 예상 시간 (\d+)분", raw),
        "category_avg_min": _first(r"평균 (\d+)분 대비", raw),
        "millie_label": _millie_label(lines),
        "curator_note": _curator_note(lines),
        "description": _description(lines),
        "formats": _formats(lines),
        "best_category": best_cat,
        "best_titles": best_titles,
    }


def extract_book_links(hrefs: list[str]) -> list[str]:
    """`/v4/book/<16hex>` href 목록 → 중복 제거된 millie_id 목록 (등장 순서 유지)."""
    out: list[str] = []
    for href in hrefs:
        m = _ID.search(href or "")
        if m and m.group(1) not in out:
            out.append(m.group(1))
    return out
