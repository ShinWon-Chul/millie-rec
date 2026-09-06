"""Track B 데모 카탈로그 어댑터 — artifacts/serving/*.json 기동 1회 로드 (DATA-06).

Catalog·Neighbors·BookStatsSource 를 한 클래스가 만족한다(적재 계획 02 §3·§7).
pandas 를 import 하지 않는다(.claude/rules/serving.md).
"""

import json
from collections.abc import Sequence
from pathlib import Path
from urllib.parse import urlsplit

from millie_rec.contracts import DIR_ARTIFACTS, BookStats, UserState

SERVING_SUBDIR = "serving"
DIR_SERVING = (
    DIR_ARTIFACTS / SERVING_SUBDIR
)  # app/export.py 와 중복 정의 — data 는 app 을 import 못 한다
BOOKS_KR_JSON = "books_kr.json"
EDGES_KR_JSON = "item_edges_kr.json"
COVER_HOST_SUFFIX = ".millie.co.kr"  # D-14: img.·image.·cover. 3종 실측 → endswith
ADULT_COVER_MARK = "adult-cover"
EXCLUDED_META_KEYS = (
    "description",
    "curator_note",
    "seg_dist",
)  # DATA-06 — export 도 빼지만 어댑터가 한 번 더 막는다
POP_RANK_COL = "pop_rank"
DEFAULT_STATS_SOURCE = "prior"  # contracts.STATS_SOURCES


def is_eligible(book: dict) -> bool:
    """D-14: title 있음 ∧ 표지 호스트 *.millie.co.kr ∧ 성인 플레이스홀더 아님.

    평가·인기·난이도 결측은 자격에 넣지 않는다(결측 책은 가드 모집단 제외일 뿐 노출은 허용).
    """
    url = book.get("image_url") or ""
    host = urlsplit(url).hostname or ""
    return (
        bool(book.get("title")) and host.endswith(COVER_HOST_SUFFIX) and ADULT_COVER_MARK not in url
    )


class CatalogKR:
    """contracts.Catalog + Neighbors + BookStatsSource. 인덱스·인기 순서는 __init__ 에서 1회."""

    def __init__(self, books: Sequence[dict], edges: dict[str, list[list]] | None = None) -> None:
        self._by_id: dict[int, dict] = {
            int(b["book_id"]): {k: v for k, v in b.items() if k not in EXCLUDED_META_KEYS}
            for b in books
        }
        self._edges = edges or {}
        ok = [b for b in self._by_id.values() if is_eligible(b)]
        self._pop_order: list[int] = [
            int(b["book_id"])
            for b in sorted(
                ok,
                key=lambda b: (
                    b.get(POP_RANK_COL) is None,  # pop_rank 결측은 마지막
                    b.get(POP_RANK_COL) or 0,
                    int(b["book_id"]),
                ),
            )
        ]

    @classmethod
    def load(cls, serving_dir: Path = DIR_SERVING) -> "CatalogKR":
        """books_kr.json 필수(없으면 FileNotFoundError, 부재 처리는 app 로더 몫)·엣지는 선택."""
        books = json.loads((serving_dir / BOOKS_KR_JSON).read_text(encoding="utf-8"))
        edges_path = serving_dir / EDGES_KR_JSON
        edges = json.loads(edges_path.read_text(encoding="utf-8")) if edges_path.exists() else {}
        return cls(books, edges)

    def meta(self, book_ids: Sequence[int]) -> list[dict]:
        return [self._by_id[int(b)] for b in book_ids if int(b) in self._by_id]

    def popular(self, categories: Sequence[str] = (), n: int = 50) -> list[int]:
        if not categories:
            return self._pop_order[:n]
        wanted = set(categories)
        return [b for b in self._pop_order if wanted & set(self._by_id[b].get("categories") or [])][
            :n
        ]

    def eligible(self, book_ids: Sequence[int]) -> list[int]:
        return [
            int(b) for b in book_ids if int(b) in self._by_id and is_eligible(self._by_id[int(b)])
        ]

    def neighbors(self, book_id: int, n: int = 20) -> list[tuple[int, float]]:
        edges = self._edges.get(str(int(book_id)), [])  # json 키는 문자열
        return [(int(dst), float(w)) for dst, w, _source in edges[:n]]

    def stats(self, book_ids: Sequence[int]) -> list[BookStats]:
        out: list[BookStats] = []
        for b in book_ids:
            row = self._by_id.get(int(b))
            if row is None:
                continue
            prob = row.get("completion_prob")
            out.append(
                BookStats(
                    book_id=int(b),
                    difficulty=row.get("difficulty"),  # 결측 None 보존(DATA-04)
                    completion_rate=(prob / 100.0) if prob is not None else None,
                    rating_mean=row.get("average_rating"),
                    source=row.get("difficulty_source") or DEFAULT_STATS_SOURCE,
                    completion_prob=prob,
                    category_avg_prob=row.get("category_avg_prob"),
                    expected_min=row.get("expected_min"),
                    category_avg_min=row.get("category_avg_min"),
                    resid_z=row.get("resid_z"),
                    len_z=row.get("len_z"),
                )
            )
        return out

    def user_level(self, user: UserState) -> float | None:
        return None  # Phase 4 가드 몫 — 완독 이력 평균은 state.py 이후
