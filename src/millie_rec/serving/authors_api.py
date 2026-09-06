"""작가 후보 API(취향 설정 작가 선택 화면) — APIRouter 팩토리.

onboarding_api.py 관례를 따르되 db 를 받지 않는다 — 작가 목록은 저장하지 않는다.
"""

from collections import Counter, defaultdict
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from millie_rec.contracts import Catalog
from millie_rec.serving.authors import display_of, key, split_authors
from millie_rec.serving.schemas import AuthorItem, AuthorSet

SURVEY_VARIANT = "v1"  # 백엔드 01 §2 survey_variant
N_DEFAULT, N_MAX = 60, 60
CATEGORIES_MAX = 3  # 후보 쿼리 categories ≤3
ALL_BOOKS_N = 10**6  # Catalog Protocol 에 전량 순회가 없어 popular 로 대신한다(onboarding_api 관례)
MIN_BOOKS = 2  # 1권짜리 작가를 넣으면 "고른 작가의 다른 책" 이 안 나와 선택이 무의미하다
POP_LAST = float("inf")  # pop_rank 결측은 뒤로
HANGUL_FIRST, HANGUL_LAST = "가", "힣"


def _422(param: str, msg: str) -> HTTPException:
    return HTTPException(422, detail=[{"loc": ["query", param], "msg": msg, "type": "value_error"}])


def _iso(dt: datetime) -> str:
    return dt.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _kr_sort(name: str) -> tuple[int, str]:
    """가나다 정렬. 한글로 시작하지 않는 이름은 뒤로(실측 소설 상위 60명 중 4명)."""
    return (0 if HANGUL_FIRST <= name[0] <= HANGUL_LAST else 1, name)


def build_index(catalog: Catalog) -> list[dict]:
    """카탈로그 전량 1회 순회 → 작가별 표시 이름·대표 책·카테고리. 대표 = pop_rank 최상위."""
    names: dict[str, Counter] = defaultdict(Counter)
    books: dict[str, list[tuple[float, int]]] = defaultdict(list)
    cats: dict[str, set[str]] = defaultdict(set)
    for m in catalog.meta(catalog.popular(n=ALL_BOOKS_N)):
        rank = m.get("pop_rank")
        for name in split_authors(m.get("authors")):
            k = key(name)
            names[k][name] += 1
            books[k].append((POP_LAST if rank is None else float(rank), int(m["book_id"])))
            cats[k].update(m.get("categories") or [])
    return [
        {
            "name": display_of(names[k]),
            "books": sorted(pairs),
            "categories": cats[k],
        }
        for k, pairs in books.items()
    ]


def build_router(
    *,
    catalog: Catalog | None = None,
    now: Callable[[], datetime] | None = None,
) -> APIRouter:
    """의존을 클로저로 받는다 — onboarding_api.build_router 와 같은 관례."""
    clock = now or (lambda: datetime.now(UTC))
    cache: dict[str, list[dict] | None] = {"index": None}  # 첫 요청에 1회 계산
    router = APIRouter(prefix="/api")

    @router.get("/candidates/authors", response_model=AuthorSet)
    def candidates_authors(  # 동기 def — 스레드풀(serving.md)
        categories: Annotated[str, Query()],
        n: Annotated[int, Query(ge=1, le=N_MAX)] = N_DEFAULT,
    ) -> AuthorSet:
        cats = [c.strip() for c in categories.split(",") if c.strip()]
        if len(cats) > CATEGORIES_MAX:
            raise _422("categories", f"at most {CATEGORIES_MAX} categories")
        created_at = _iso(clock())
        if catalog is None:  # 아티팩트 없이도 서버가 뜬다(.claude/rules/local-run.md)
            return AuthorSet(survey_variant=SURVEY_VARIANT, created_at=created_at, items=[])
        if cache["index"] is None:
            cache["index"] = build_index(catalog)
        want = set(cats)
        picked = [
            a
            for a in cache["index"]
            if len(a["books"]) >= MIN_BOOKS and (not want or want & a["categories"])
        ]
        picked.sort(key=lambda a: a["books"][0])  # 대표 책 pop_rank 오름차순
        picked = sorted(picked[:n], key=lambda a: _kr_sort(a["name"]))
        metas = {int(m["book_id"]): m for m in catalog.meta([a["books"][0][1] for a in picked])}
        items = [
            AuthorItem(
                name=a["name"],
                book_id=a["books"][0][1],
                title=(metas.get(a["books"][0][1]) or {}).get("title") or "",
                image_url=(metas.get(a["books"][0][1]) or {}).get("image_url"),
                n_books=len(a["books"]),
            )
            for a in picked
        ]
        return AuthorSet(survey_variant=SURVEY_VARIANT, created_at=created_at, items=items)

    return router
