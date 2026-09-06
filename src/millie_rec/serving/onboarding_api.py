"""온보딩 메타·후보 API(백엔드 서빙 01 §2·§3) — APIRouter 팩토리.

Advisor 확정 17 B2 로 demo_api 에서 분리(아키 §9-3 목록 외 신설).
"""

import itertools
import json
import uuid
from collections import Counter
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from millie_rec.contracts import Catalog
from millie_rec.serving.db import Database
from millie_rec.serving.schemas import (
    CandidateItem,
    CandidateSet,
    CategoryMeta,
    Criterion,
    OnboardingMeta,
)

META_PATH = Path(__file__).parent / "onboarding_meta.json"  # db.py SCHEMA_PATH 관례
SURVEY_VARIANT = "v1"  # 백엔드 01 §2 survey_variant
N_DEFAULT, N_MAX = 30, 60  # 백엔드 01 §3 기본 30 · §0 "n ≤ 60"
SUPPORTED_MIN = 20  # D-14 supported = eligible ≥ 20
CATEGORIES_MAX = 3  # 후보 쿼리 categories ≤3
ALL_BOOKS_N = 10**6  # Catalog Protocol 에 "전 카테고리 목록" 이 없어 popular 전량으로 대신한다
SQL_CAND_INS = (
    "INSERT INTO candidate_sets(candidate_set_id, user_key, ts, book_ids, survey_variant)"
    " VALUES(?,?,?,?,?)"
)


def _422(param: str, msg: str) -> HTTPException:
    return HTTPException(422, detail=[{"loc": ["query", param], "msg": msg, "type": "value_error"}])


def _j(value) -> str:
    return json.dumps(value, ensure_ascii=False)


def _iso(dt: datetime) -> str:
    """UTC Z 정규화(revision C3). demo_api 도 이 헬퍼를 쓴다(같은 슬라이스)."""
    return dt.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def new_id(prefix: str) -> str:
    return prefix + uuid.uuid4().hex[:6]  # 백엔드 01 §0 ID 형식 (compose.new_rec_id 관례)


def load_meta(path: Path = META_PATH) -> dict:
    """onboarding_meta.json 1벌을 읽는다(D-14 — 서버는 demo/config 를 읽지 않는다)."""
    return json.loads(path.read_text(encoding="utf-8"))


def catalog_categories_meta(catalog, subcategories) -> list[CategoryMeta]:
    """카탈로그 전량의 카테고리 빈도 → supported. compose.catalog_categories 와 중복 허용(C11)."""
    if catalog is None:
        return []
    counts = Counter(
        c for m in catalog.meta(catalog.popular(n=ALL_BOOKS_N)) for c in (m.get("categories") or [])
    )
    return [
        CategoryMeta(name=c, supported=n >= SUPPORTED_MIN, subcategories=subcategories.get(c, []))
        for c, n in counts.most_common()
    ]


def _round_robin(catalog, cats: list[str], n: int) -> list[int]:
    """선택 카테고리에서 pop_rank 순으로 1권씩 돌아가며 n 까지(D-15). 카테고리 간 중복 제거."""
    lists = [catalog.popular([c], n=n) for c in cats]
    seen: set[int] = set()
    ids: list[int] = []
    for row in itertools.zip_longest(*lists):
        for b in row:
            if b is not None and b not in seen and len(ids) < n:
                seen.add(b)
                ids.append(b)
    return catalog.eligible(ids)


def build_router(
    *,
    db: Database,
    catalog: Catalog | None = None,
    meta_path: Path = META_PATH,
    now: Callable[[], datetime] | None = None,
) -> APIRouter:
    """의존을 클로저로 받는다 — create_app 배선은 Plan 05-06(Advisor 확정 2)."""
    meta = load_meta(meta_path)
    clock = now or (lambda: datetime.now(UTC))
    cache: dict[str, list[CategoryMeta] | None] = {"cats": None}  # C11 1회 캐시
    router = APIRouter(prefix="/api")

    @router.get("/meta/onboarding", response_model=OnboardingMeta)
    def meta_onboarding() -> OnboardingMeta:  # 동기 def — 스레드풀(serving.md)
        if cache["cats"] is None:
            cache["cats"] = catalog_categories_meta(catalog, meta["subcategories"])
        return OnboardingMeta(
            survey_variant=meta["survey_variant"],
            reading_times=meta["reading_times"],
            criteria=[Criterion(**c) for c in meta["criteria"]],
            categories=cache["cats"],
        )

    @router.get("/candidates/onboarding", response_model=CandidateSet)
    def candidates(
        categories: Annotated[str, Query()],
        n: Annotated[int, Query(ge=1, le=N_MAX)] = N_DEFAULT,
        user_key: Annotated[str | None, Query()] = None,
        subcategories: Annotated[str | None, Query()] = None,
    ) -> CandidateSet:
        cats = [c.strip() for c in categories.split(",") if c.strip()]
        if len(cats) > CATEGORIES_MAX:
            raise _422("categories", f"at most {CATEGORIES_MAX} categories")
        ids = [] if catalog is None else _round_robin(catalog, cats, n)
        metas = catalog.meta(ids) if ids else []
        items = [
            CandidateItem(
                book_id=m["book_id"],
                title=m.get("title") or "",
                authors=m.get("authors"),
                image_url=m.get("image_url"),
                position=i,
                book_format=m.get("book_format"),
            )
            for i, m in enumerate(metas)
        ]
        cid, ts = new_id("cand_"), _iso(clock())
        with db.connect() as con:  # 확정 16: with con 으로 커밋
            con.execute(SQL_CAND_INS, (cid, user_key, ts, _j(ids), SURVEY_VARIANT))
        return CandidateSet(
            candidate_set_id=cid, survey_variant=SURVEY_VARIANT, created_at=ts, items=items
        )

    return router
