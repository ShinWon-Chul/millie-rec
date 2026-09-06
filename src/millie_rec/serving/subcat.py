"""취향 세부 분류(밀리 3depth) 후보 정렬 — Retrieval 단계의 순수 함수만.

세부 분류를 가진 책이 카탈로그의 42.6% 뿐이라 하드 필터가 아니라 "겹치는 책을 앞으로" 다.
못 채운 자리는 호출자가 기존 인기순으로 채운다. 점수 가산은 ranking/hybrid.py 가 한다.
"""

from collections.abc import Iterable, Sequence

from millie_rec.contracts import Catalog

POOL_FACTOR = 3  # 후보 정렬용 풀 배수
KEY = "subcategories"

Want = Iterable[str]


def wanted(value: str | Sequence[str] | None) -> frozenset[str]:
    """csv 문자열(UserState.context)·시퀀스(Resolved) 두 형태를 다 받는다. 빈 항목은 버린다."""
    parts = value.split(",") if isinstance(value, str) else list(value or ())
    return frozenset(s.strip() for s in parts if s and s.strip())


def matched(meta: dict, want: Want) -> tuple[str, ...]:
    """겹친 이름들을 meta 의 등장 순서로. 키 부재·None 도 견딘다(가짜 카탈로그·미수집 도서)."""
    return tuple(s for s in (meta.get(KEY) or ()) if s in want)


def prioritize(book_ids: Sequence[int], catalog: Catalog | None, want: Want) -> list[int]:
    """겹치는 책 먼저, 나머지 뒤 — 양쪽 원래 순서 유지. meta 에 없는 id 도 버리지 않는다."""
    ids = list(book_ids)
    if not want or catalog is None:
        return ids
    meta = {int(m["book_id"]): m for m in catalog.meta(ids)}
    hit = [b for b in ids if matched(meta.get(b, {}), want)]
    rest = set(hit)
    return hit + [b for b in ids if b not in rest]
