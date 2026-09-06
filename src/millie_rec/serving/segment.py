"""시드 대표 독자층(연령×성별) 추정 — 폴백 2단계가 어느 세그먼트 인기를 쓸지 정한다.

ranking/prefs.estimate_segment 와 중복 정의(중복 < 결합) — serving 은 ranking 을 import 못 한다.
"""

from collections import Counter
from collections.abc import Sequence

KEY_TOP_SEGMENT = "top_segment"  # catalog.meta() 컬럼 (9,447권 중 7,384권 = 78.2%)


def estimate(seed_meta: Sequence[dict]) -> str | None:
    """시드 top_segment 다수결. 결측 무시, 동률은 사전순 최소(결정성), 전부 결측이면 None."""
    counts = Counter(s for m in seed_meta if (s := m.get(KEY_TOP_SEGMENT)))
    if not counts:
        return None
    return min(counts, key=lambda s: (-counts[s], s))
