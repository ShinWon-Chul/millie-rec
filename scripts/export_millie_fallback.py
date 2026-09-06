"""books_kr.parquet → demo/fallback/popular.json (DATA-07, 백엔드 01 fallback 절).

RecommendOut level 3 형태로 쓴다. architecture.md 소유권 예외 — export 가
demo/fallback/popular.json 을 갱신하는 것만 허용.
문자열 상수는 serving/fallback.py 와 같은 값이다. scripts 는 serving 슬라이스를
import 하지 않으므로(star 의존) 동일성은 테스트가 단정한다.
"""

import argparse
import json
import math
from pathlib import Path
from urllib.parse import urlsplit

import numpy as np
import pandas as pd

from millie_rec.contracts import (
    DIR_PROCESSED,
    FALLBACK_GLOBAL_POP,
    MODEL_VERSION_FALLBACK,
    ROOT,
)

N_ITEMS = 40
RECOMMENDATION_ID = "rec_static"  # 정적 파일 표시(서버는 rec_<6hex>)
TRENDING_ROW_ID = "trending"
TRENDING_TITLE = "지금 많이 읽는 책"
TRENDING_PURPOSE = "fallback"
SOURCE_POPULARITY = "popularity"
ZERO_WEIGHTS = {"alpha": 0.0, "beta": 0.0, "gamma": 0.0}
COVER_HOST_SUFFIX = ".millie.co.kr"
ADULT_COVER_MARK = "adult-cover"  # data/catalog_kr.py is_eligible 와 같은 규칙(D-14) 중복
MISSING_RANK = 10**9  # pop_rank 결측을 맨 뒤로
DEFAULT_OUT = ROOT / "demo" / "fallback" / "popular.json"


def _clean(value: object) -> object:
    """pandas NA·NaN → None, numpy 스칼라·배열 → 기본형 (export_millie_serving._clean 복사)."""
    if isinstance(value, list | tuple | np.ndarray):
        return [_clean(v) for v in value]
    if value is None or value is pd.NA:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    if hasattr(value, "item"):
        return value.item()
    return value


def is_eligible(row: dict) -> bool:
    """D-14 노출 자격: title 있음 ∧ 표지 호스트가 *.millie.co.kr ∧ 성인 표지 플레이스홀더 아님."""
    url = row.get("image_url") or ""
    url = url if isinstance(url, str) else ""
    host = urlsplit(url).hostname or ""
    return (
        bool(row.get("title")) and host.endswith(COVER_HOST_SUFFIX) and ADULT_COVER_MARK not in url
    )


def _item(row: dict, position: int, n: int) -> dict:
    """ItemOut 12필드 화이트리스트만 조립한다(description·curator_note 누출 차단)."""
    return {
        "book_id": int(row["book_id"]),
        "score": float(n - position),  # serving/fallback.py GlobalPopularFallback 점수 관례
        "source": SOURCE_POPULARITY,
        "reason": None,
        "title": _clean(row.get("title")),
        "authors": _clean(row.get("authors")),
        "image_url": _clean(row.get("image_url")),
        "position": position,
        "source_channels": [SOURCE_POPULARITY],
        "badge": None,
        "book_format": _clean(row.get("book_format")),
        "difficulty": _clean(row.get("difficulty")),
    }


def payload(books: pd.DataFrame, n: int = N_ITEMS) -> dict:
    """서버 level 3 응답(compose.build_response + fallback.trending_row)과 같은 형태.

    level 3 은 items 평탄화가 없으므로 최상위 items 는 빈 목록이다.
    """
    frame = books.assign(
        _rank=pd.to_numeric(books["pop_rank"], errors="coerce").fillna(MISSING_RANK)
    ).sort_values("_rank")
    rows = [r for r in frame.to_dict("records") if is_eligible(r)][:n]
    items = [_item(r, i, len(rows)) for i, r in enumerate(rows)]
    return {
        "recommendation_id": RECOMMENDATION_ID,
        "model_version": MODEL_VERSION_FALLBACK,
        "preference_snapshot_id": None,
        "user_key": None,
        "cell": None,
        "forced": False,
        "fallback_level": FALLBACK_GLOBAL_POP,
        "context": None,
        "latency_ms": 0.0,
        "latency_breakdown": {"total": 0.0},
        "user_state_weights": dict(ZERO_WEIGHTS),
        "dedup_removed": 0,
        "nearline_lag_s": None,
        "items": [],
        "rows": [
            {
                "row_id": TRENDING_ROW_ID,
                "title": TRENDING_TITLE,
                "purpose": TRENDING_PURPOSE,
                "items": items,
                "subtitle": None,
                "channel_mix": {SOURCE_POPULARITY: len(items)} if items else {},
            }
        ],
    }


def export_fallback(books_path: Path, out_path: Path) -> int:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(payload(pd.read_parquet(books_path)), ensure_ascii=False, indent=1),
        encoding="utf-8",
    )
    return out_path.stat().st_size


def main() -> None:
    parser = argparse.ArgumentParser(description="정적 fallback(level 3) popular.json export")
    parser.add_argument("--books", type=Path, default=DIR_PROCESSED / "books_kr.parquet")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    size = export_fallback(args.books, args.out)
    print(
        f"{args.out.name} {size / 1024:.1f}KB level={FALLBACK_GLOBAL_POP} {MODEL_VERSION_FALLBACK}"
    )


if __name__ == "__main__":
    main()
