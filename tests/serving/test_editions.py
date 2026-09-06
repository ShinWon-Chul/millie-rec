"""판본 dedup — 계약(same_work 집합·가드) · 정확성(행 12권 유지) · 안전성(이어 읽기 예외·항등).

사용자 보고 2026-09-06: 앵커 행 '결이 비슷한 책' 1번 칸에 방금 읽은 책의 오디오북 판본이 왔다.
가짜는 파일마다 복제한다(tests/serving/test_compose.py 관례).
"""

from millie_rec.contracts import FALLBACK_PERSONALIZED, ScoredItem
from millie_rec.serving.compose import compose_rows
from millie_rec.serving.compose import normalize_title as normalize_title_compose
from millie_rec.serving.editions import (
    KEEP_ROWS,
    drop_same_work,
    normalize_title,
    same_work,
)
from millie_rec.serving.rows import ROW_SIZE, neighbor_row

CATS = ("소설", "에세이", "경제경영", "인문")
N_CAT = 40
SEED = 1
EDITION = 2  # 시드 1 의 다른 판본(오디오북) — 정규화 제목이 같다
BLANK = (30, 31)  # 제목이 빈 두 권 — 서로 묶이면 안 된다
ITEMS = [14, 15, 16, 18, 20, 21, 22, 23, 24, 25, 26, 27, 28]
READ = 1  # 시드가 아닌데 읽은 책 — EDITION 이 이 책의 다른 판본이다
SEEDS_NO_READ = (5,)  # READ 를 시드에 넣지 않는다(이번 결함의 조건)


def _title(b: int) -> str:
    if b == EDITION:
        return "밀리 표본 도서 1"
    return "" if b in BLANK else f"밀리 표본 도서 {b}"


def _meta(b: int, title: str | None = None) -> dict:
    return {
        "book_id": b,
        "title": _title(b) if title is None else title,
        "authors": f"저자 {b % 3}",
        "image_url": f"https://img.millie.co.kr/{b}.jpg",
        "book_format": "오디오북" if b == EDITION else "전자책",
        "difficulty": 0.4,
        "categories": [CATS[(b - 1) % 4]],
        "publisher": "출판사 A",
        "pop_rank": b,
        "average_rating": 4.2,
        "review_count": b * 3,
        "millie_label": None,
    }


class _Cat:
    """contracts.Catalog 가짜 — 40권. book_id 2 는 book_id 1 의 다른 판본."""

    def __init__(self, unique: bool = False) -> None:
        self.unique = unique  # True 면 중복 제목 없음(회귀 항등 확인용)
        self.meta_calls = 0

    def _row(self, b: int) -> dict:
        return _meta(b, f"밀리 표본 도서 {b}" if self.unique else None)

    def meta(self, ids):
        self.meta_calls += 1
        return [self._row(int(b)) for b in ids if 1 <= int(b) <= N_CAT]

    def popular(self, categories=(), n=50):
        ids = [
            b
            for b in range(1, N_CAT + 1)
            if not categories or set(categories) & set(self._row(b)["categories"])
        ]
        return ids[:n]

    def eligible(self, ids):
        return [int(b) for b in ids if 1 <= int(b) <= N_CAT]


class _Nbrs:
    """시드 1 의 이웃 20권 = 2..21. 1위가 판본 중복(가중치 1.0) — 실측 재현."""

    def neighbors(self, book_id, n=20):
        return [
            (book_id + i, 1.0 if i == 1 else round(0.95 - 0.02 * i, 3)) for i in range(1, n + 1)
        ]


def _items(ids):
    return [
        ScoredItem(b, float(60 - i), "content", position=i, source_channels=("content",))
        for i, b in enumerate(ids)
    ]


def _rows(**kw):
    args = dict(
        items=_items(ITEMS),
        catalog=_Cat(),
        neighbors=_Nbrs(),
        level=FALLBACK_PERSONALIZED,
        seeds=(SEED,),
        categories=("소설",),
        criterion="bestseller",
        persona_name="오디세우스",
        continue_ids=(19,),
        all_categories=CATS,
    )
    args.update(kw)
    return compose_rows(**args)


# ── 계약 ────────────────────────────────────────────────────────────────
def test_same_work_returns_only_same_normalized_title():
    cat = _Cat()
    assert same_work(cat, [EDITION, 3, 4], [SEED]) == {EDITION}
    assert same_work(cat, list(range(2, 21)), [SEED]) == {EDITION}


def test_same_work_ignores_blank_titles():
    """제목 없는 책끼리 묶이면 카탈로그의 결측이 추천을 지운다."""
    assert same_work(_Cat(), [BLANK[1]], [BLANK[0]]) == set()


def test_same_work_guards_return_empty_set():
    cat = _Cat()
    assert same_work(None, [EDITION], [SEED]) == set()
    assert same_work(cat, [EDITION], []) == set()
    assert same_work(cat, [], [SEED]) == set()


def test_same_work_calls_meta_twice():
    cat = _Cat()
    same_work(cat, list(range(2, 21)), [SEED])
    assert cat.meta_calls == 2


def test_normalize_title_unchanged_after_move():
    assert normalize_title("데미안 (세계문학전집 44)") == "데미안세계문학전집44"
    assert normalize_title(None) == ""
    assert normalize_title_compose is normalize_title  # compose 경유 import 유지(기존 테스트)


# ── 정확성 ──────────────────────────────────────────────────────────────
def test_neighbor_row_drops_seed_edition_and_still_fills_row_size():
    cat = _Cat()
    row = neighbor_row("anchor_1", "머리말", None, SEED, _Nbrs().neighbors(SEED, 20), cat, set())
    ids = [i.book_id for i in row.items]
    assert EDITION not in ids
    assert len(ids) == ROW_SIZE
    assert ids == list(range(3, 3 + ROW_SIZE))


def test_compose_rows_sweeps_seed_edition_from_every_row():
    rows, _ = _rows(items=_items([EDITION, *ITEMS]))
    for row in rows:
        assert EDITION not in [i.book_id for i in row.items], row.row_id


# ── 안전성 ──────────────────────────────────────────────────────────────
def test_continue_reading_keeps_seed_edition():
    """이어 읽기는 '지금 읽는 중'이라 시드와 같은 작품이어도 남는다(데모 동선)."""
    assert KEEP_ROWS == ("continue_reading",)
    rows, _ = _rows(continue_ids=(EDITION,))
    cont = next(r for r in rows if r.row_id == "continue_reading")
    assert [i.book_id for i in cont.items] == [EDITION]


def test_no_duplicate_titles_means_no_change():
    cat = _Cat(unique=True)
    rows, removed = _rows(catalog=cat)
    assert [r.row_id for r in rows] == [
        "continue_reading",
        "anchor_1",
        "persona_shelf",
        "trending",
        "fresh_picks",
    ]
    anchor = next(r for r in rows if r.row_id == "anchor_1")
    assert [i.book_id for i in anchor.items] == list(range(2, 2 + ROW_SIZE))
    assert removed == 0
    assert drop_same_work(rows, cat, (SEED,)) == tuple(rows)


# ── 읽기 이력·완독 경로(후속 브리프) ───────────────────────────────────────
def test_read_history_edition_is_swept_from_every_row():
    """시드가 아닌 책을 읽어도 그 판본이 남으면 안 된다(사용자 원문의 경로)."""
    kw = dict(items=_items([EDITION, *ITEMS]), seeds=SEEDS_NO_READ)
    before, _ = _rows(**kw)
    assert EDITION in [i.book_id for r in before for i in r.items]  # read_ids 없으면 남는다
    rows, _ = _rows(**kw, read_ids=(READ,))
    for row in rows:
        assert EDITION not in [i.book_id for i in row.items], row.row_id


def test_completed_book_edition_is_swept_without_read_ids():
    """완독 책은 after_completion[0] 이 refs 라 read_ids 없이도 잡힌다."""
    after = (READ, ((EDITION, 1.0), (3, 0.9), (4, 0.8)))
    rows, _ = _rows(items=_items([EDITION, *ITEMS]), seeds=SEEDS_NO_READ, after_completion=after)
    assert rows[0].row_id == "after_completion"
    for row in rows:
        assert EDITION not in [i.book_id for i in row.items], row.row_id
