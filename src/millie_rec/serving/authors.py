"""저자 이름 정규화 — 표시 이름 분리와 비교 키(순수 함수, I/O 없음).

badges.py 의 작가 배지와 authors_api.py 의 작가 목록이 같은 규칙을 쓴다.
"""

import re
from collections.abc import Mapping

_PAREN = re.compile(r"\([^)]*\)")  # "김영하 (지음)" 의 괄호 안은 버린다
_SPLIT = re.compile(r"[,/·&]")
AUTHOR_ROLES = ("지음", "글", "그림", "사진", "저", "엮음", "편저", "원작", "각본", "구성")
NON_AUTHOR_ROLES = ("옮김", "역", "번역", "감수", "해설", "편역")
NON_PERSON = ("편집부", "저작권팀", "Disney Books")
MIN_LEN = 2  # 한 글자는 이름이 아니다


def key(name: str) -> str:
    """비교용 키. 내부 공백 제거 + 소문자화 — '히가시노 게이고' == '히가시노게이고'."""
    return "".join(name.split()).lower()


_NON_PERSON_KEYS = frozenset(key(n) for n in NON_PERSON)


def _spaced(text: str, role: str) -> bool:
    """역할어 앞에 공백이 있나. 없으면 이름의 일부다 — '에이든토저'·'송기역' 훼손 방지."""
    head = text[: -len(role)]
    return bool(head) and head[-1].isspace()


def _strip_roles(segment: str) -> str | None:
    """끝의 역할어를 반복 제거. 비저자 역할이면 조각째 버린다(역자가 작가가 되는 것을 막는다)."""
    text = segment.strip()
    while True:
        if any(text.endswith(r) and _spaced(text, r) for r in NON_AUTHOR_ROLES):
            return None
        for role in AUTHOR_ROLES:
            if text.endswith(role) and _spaced(text, role):
                text = text[: -len(role)].strip()
                break
        else:
            return text


def split_authors(value: str | None) -> tuple[str, ...]:
    """표시용 이름들. 괄호 제거 → , / · & 분리 → 끝의 역할어 제거 → 역자·비인물 제외."""
    if not value:
        return ()
    names: list[str] = []
    seen: set[str] = set()
    for segment in _SPLIT.split(_PAREN.sub(" ", value)):
        name = _strip_roles(segment)
        if not name or len(name) < MIN_LEN or key(name) in _NON_PERSON_KEYS:
            continue
        if key(name) not in seen:
            seen.add(key(name))
            names.append(name)
    return tuple(names)


def display_of(counts: Mapping[str, int]) -> str:
    """같은 키의 표기 중 최다. 동률은 사전순 최소(결정성)."""
    return min(counts, key=lambda name: (-counts[name], name))
