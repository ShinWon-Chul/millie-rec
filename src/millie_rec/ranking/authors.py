"""저자 표기 파서 — serving/authors.py 와 중복 정의(중복 < 결합)."""

import re

_PARENS = re.compile(r"\([^)]*\)")
_SPLIT = re.compile(r"[,/·&]")
# 조각 끝의 역할어. 저자 역할은 떼고 이름을 남기고, 비저자 역할은 조각째 버린다
_AUTHOR_ROLES = ("지음", "그림", "사진", "엮음", "편저", "원작", "각본", "구성", "글", "저")
_NON_AUTHOR_ROLES = ("옮김", "번역", "감수", "해설", "편역", "역")
_NON_PERSON = frozenset({"편집부", "저작권팀", "Disney Books"})


def _ends_with_spaced(name: str, role: str) -> bool:
    """카탈로그 9,447권 실측 — 공백 없이 역할어로 끝나는 24건은 전부 사람 이름('에이든토저')."""
    return name.endswith(role) and len(name) > len(role) and name[-len(role) - 1].isspace()


def _clean(segment: str) -> str | None:
    """역할어를 반복 제거한 이름. 역자·비인물·한 글자는 None."""
    name = segment.strip()
    stripped = True
    while stripped and name:
        stripped = False
        if any(_ends_with_spaced(name, r) for r in _NON_AUTHOR_ROLES):
            return None  # '함미라 옮김' 을 이름으로 남기면 역자가 작가가 된다
        for role in _AUTHOR_ROLES:
            if _ends_with_spaced(name, role):
                name, stripped = name[: -len(role)].strip(), True
                break
    if len(name) <= 1 or name in _NON_PERSON:
        return None
    return name


def split_authors(value: str | None) -> tuple[str, ...]:
    """표시용 이름들. 괄호 제거 → , / · & 분리 → 끝의 역할어 제거 → 역자·비인물 제외."""
    if not value:
        return ()
    names = (_clean(s) for s in _SPLIT.split(_PARENS.sub(" ", value)))
    return tuple(dict.fromkeys(n for n in names if n))


def key(name: str) -> str:
    """비교용 키. 내부 공백 제거 + 소문자화 — '히가시노 게이고' == '히가시노게이고'."""
    return "".join(name.split()).lower()


def keys_of(value: str | None) -> frozenset[str]:
    """한 authors 문자열의 비교 키 집합. 가점 계산이 쓰는 형태."""
    return frozenset(key(n) for n in split_authors(value))
