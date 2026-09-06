"""hybrid 가중합 랭커 — 채널 min-max + 고정 상수 가중합(D-03) + ★난이도 gap 3항(D-06)."""

from collections.abc import Sequence

from millie_rec.contracts import BookStatsSource, Candidate, Catalog, ScoredItem, UserState
from millie_rec.ranking import prefs

CH_CF, CH_CONTENT, CH_POP = "cf", "content", "pop"  # 채널 슬롯. Candidate.source 와 다른 층
W_CF, W_CONTENT, W_POP = 0.5, 0.3, 0.2  # D-03 초기값. Day 3 ≤3조합 그리드 1회 후 freeze(D-14 ①)
CHANNEL_WEIGHTS = {CH_CF: W_CF, CH_CONTENT: W_CONTENT, CH_POP: W_POP}
SLOT_ORDER = (CH_CF, CH_CONTENT, CH_POP)  # source_channels 순서·동률 우선순위
# Track A source → 슬롯. Track B 는 app 이 슬롯 dict 를 직접 만든다(cf 슬롯도 source="content")
SOURCE_ITEMKNN, SOURCE_CONTENT = "itemknn", "content"  # retrieval 과 중복 정의(중복 < 결합)
SOURCE_POPULARITY = "popularity"
SLOT_OF_SOURCE = {SOURCE_ITEMKNN: CH_CF, SOURCE_CONTENT: CH_CONTENT, SOURCE_POPULARITY: CH_POP}
# D-06 ★난이도 gap 3항 — 음수(어려운 쪽 감점). 결측·level None 은 가중 0. freeze(D-14 ①)
W_GAP, W_GAP_POS, W_NCOMP_GAP = -0.10, -0.20, -0.01


def _slot_rank(slot: str) -> int:
    """동률 시 앞 슬롯(cf → content → pop) 우선."""
    return SLOT_ORDER.index(slot) if slot in SLOT_ORDER else len(SLOT_ORDER)


def _minmax(cands: Sequence[Candidate]) -> dict[int, float]:
    """채널 안 0~1. 후보 1개·분산 0 이면 1.0. 같은 책이 두 번 오면 큰 점수만 남긴다."""
    by_id: dict[int, float] = {}
    for c in cands:
        b = int(c.book_id)
        if b not in by_id or c.score > by_id[b]:
            by_id[b] = float(c.score)
    if not by_id:
        return {}
    lo, hi = min(by_id.values()), max(by_id.values())
    span = hi - lo
    return {b: (s - lo) / span if span > 0 else 1.0 for b, s in by_id.items()}


def _gap_bonus(
    user: UserState, book_ids: Sequence[int], book_stats: BookStatsSource | None
) -> tuple[dict[int, float], dict[int, float | None]]:
    """(gap 보정, 난이도). book_stats None · user_level() None · difficulty None 은 가중 0(D-06)."""
    if book_stats is None:
        return {}, {}
    stats = {int(s.book_id): s for s in book_stats.stats(list(book_ids))}
    difficulty = {int(b): (stats[b].difficulty if b in stats else None) for b in book_ids}
    level = book_stats.user_level(user)
    if level is None:
        return {}, difficulty  # 신규 유저 — 난이도 표시는 하고 점수는 건드리지 않는다
    # D-07: 서빙은 context(완독 수), Track A 는 len(user.history) 대리값
    n_completed = int(user.context.get("n_completed", len(user.history)))
    bonus: dict[int, float] = {}
    for b, d in difficulty.items():
        if d is None:
            continue
        gap = d - level
        bonus[b] = W_GAP * gap + W_GAP_POS * max(gap, 0.0) + W_NCOMP_GAP * n_completed * gap
    return bonus, difficulty


def blend_channels(
    user: UserState,
    channels: dict[str, list[Candidate]],
    weights: dict[str, float] | None = None,
    *,
    book_stats: BookStatsSource | None = None,
    catalog: Catalog | None = None,
) -> list[ScoredItem]:
    """슬롯별 min-max → Σ w_slot·norm(없으면 0) + gap 3항 + 취향 가점(분류·작가·독자층) → 정렬.

    seen 은 넣지 않는다. 가중치가 없는 슬롯은 후보에서도 빠진다(cf variant = {"cf": 1.0}).
    """
    w = dict(CHANNEL_WEIGHTS if weights is None else weights)
    slots = [s for s in SLOT_ORDER if s in channels and s in w]
    slots += [s for s in channels if s in w and s not in SLOT_ORDER]
    norm = {s: _minmax(channels[s]) for s in slots}
    src = {s: {int(c.book_id): c.source for c in channels[s]} for s in slots}
    books = sorted({b for s in slots for b in norm[s] if b not in user.seen})
    if not books:
        return []
    bonus, difficulty = _gap_bonus(user, books, book_stats)
    pref = prefs.bonus(user, books, catalog)
    scored: list[tuple[float, int, str, tuple[str, ...], float | None]] = []
    for b in books:
        contrib = {s: w[s] * norm[s][b] for s in slots if b in norm[s]}
        total = sum(contrib.values()) + bonus.get(b, 0.0) + pref.get(b, 0.0)
        best = max(contrib.items(), key=lambda kv: (kv[1], -_slot_rank(kv[0])))[0]
        chans = tuple(
            dict.fromkeys(src[s][b] for s in slots if b in norm[s])
        )  # 순서 유지 중복 제거
        scored.append((total, b, src[best][b], chans, difficulty.get(b)))
    scored.sort(key=lambda t: (-t[0], t[1]))
    return [
        ScoredItem(
            book_id=b, score=float(t), source=s, position=i, source_channels=ch, difficulty=d
        )
        for i, (t, b, s, ch, d) in enumerate(scored)
    ]


class HybridRanker:
    """contracts.Ranker — flat Candidate 를 source → 슬롯으로 묶어 blend_channels 를 부르는 래퍼."""

    def __init__(
        self,
        weights: dict[str, float] | None = None,
        *,
        book_stats: BookStatsSource | None = None,
        slot_of: dict[str, str] | None = None,
    ) -> None:
        self._weights = weights
        self._book_stats = book_stats
        self._slot_of = slot_of or SLOT_OF_SOURCE

    def rank(self, user: UserState, candidates: list[Candidate]) -> list[ScoredItem]:
        channels: dict[str, list[Candidate]] = {}
        for c in candidates:
            slot = self._slot_of.get(c.source)
            if slot is None:
                continue  # 매핑에 없는 source(explicit 등)는 랭킹 채널이 아니다
            channels.setdefault(slot, []).append(c)
        return blend_channels(user, channels, self._weights, book_stats=self._book_stats)
