"""세그먼트별 인기 순위 — 폴백 2단계 재료(연령 6 × 성별 2 + all, 98,055행).

artifacts/serving/popularity_kr.json 1벌을 기동 시 읽어 세그먼트별 rank 순서로 굳힌다.
서빙 경로이므로 pandas 를 import 하지 않는다(.claude/rules/serving.md 메모리 예산).
"""

import json
import logging
from collections.abc import Sequence
from pathlib import Path

POPULARITY_KR_JSON = "popularity_kr.json"
COL_BOOK_ID, COL_SEGMENT, COL_RANK = "book_id", "segment", "rank"

log = logging.getLogger(__name__)


class SegmentPopularity:
    """세그먼트별 인기 순위. 정렬은 __init__ 1회 — 요청마다 재계산하지 않는다."""

    def __init__(self, rows: Sequence[dict]) -> None:
        buckets: dict[str, list[tuple[int, int]]] = {}
        for row in rows:
            buckets.setdefault(str(row[COL_SEGMENT]), []).append(
                (int(row[COL_RANK]), int(row[COL_BOOK_ID]))
            )
        self._by_segment: dict[str, list[int]] = {
            seg: [b for _rank, b in sorted(pairs)] for seg, pairs in sorted(buckets.items())
        }

    @classmethod
    def load(cls, serving_dir: Path) -> "SegmentPopularity | None":
        """파일 부재·JSON 손상·필드 결측은 None — 아티팩트 없이도 서버가 뜬다(로컬 기동 보장)."""
        path = Path(serving_dir) / POPULARITY_KR_JSON
        try:
            return cls(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, ValueError, TypeError, KeyError) as exc:
            log.warning("segment popularity unavailable (%s): %s", path, exc)
            return None

    def ranked(self, segment: str, n: int) -> list[int]:
        """그 세그먼트 rank 오름차순 상위 n 개 book_id. 없는 세그먼트는 []."""
        return self._by_segment.get(segment, [])[:n]

    def segments(self) -> tuple[str, ...]:
        """가진 세그먼트 이름들 — 진단·테스트용."""
        return tuple(self._by_segment)
