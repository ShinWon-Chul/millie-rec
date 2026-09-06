"""compose Must 5행 — 계약(순서·row_id·앵커 content) · 정확성(dedup·배지·메타) · 안전성.

Phase 5 '서빙 Must 완성'(.planning/ROADMAP.md).
결정 D-01~D-04(.planning/phases/05-must/05-CONTEXT.md).
가짜 Catalog·Neighbors 주입 — data·app 을 import 하지 않는다.
가짜는 파일마다 복제한다(테스트 간 import 금지).
"""

from dataclasses import asdict, replace
from time import perf_counter

from millie_rec.contracts import BADGE_TYPES, Badge, ScoredItem
from millie_rec.serving.badges import badge_for
from millie_rec.serving.compose import (
    ZERO_WEIGHTS,
    build_response,
    catalog_categories,
    compose_rows,
    normalize_title,
    with_meta,
)
from millie_rec.serving.schemas import RowOut

CATS = ("소설", "에세이", "경제경영", "인문")
N_CAT = 40
ITEMS5 = [14, 15, 16, 17, 18, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 7]
ANCHOR_REASON = "『밀리 표본 도서 1』을 좋아하셨다면"


def _meta(b: int) -> dict:
    """b 1..40, 카테고리 순환. 17 은 7 과 같은 제목(정규화 제목 dedup 케이스, D-04)."""
    title = "밀리 표본 도서 7" if b == 17 else f"밀리 표본 도서 {b}"
    return {
        "book_id": b,
        "title": title,
        "authors": f"저자 {b % 3}",
        "image_url": f"https://img.millie.co.kr/{b}.jpg",
        "book_format": "전자책",
        "difficulty": 0.4,
        "categories": [CATS[(b - 1) % 4]],
        "publisher": "출판사 A" if b % 2 else "출판사 B",
        "pop_rank": b,
        "average_rating": 4.2 if b != 5 else None,
        "review_count": b * 3,
        "millie_label": "밀리 픽" if b == 9 else None,
    }


class _Cat:
    """contracts.Catalog 가짜 — 40권(카테고리 4종 순환)."""

    def meta(self, ids):
        return [_meta(int(b)) for b in ids if 1 <= int(b) <= N_CAT]

    def popular(self, categories=(), n=50):
        ids = [
            b
            for b in range(1, N_CAT + 1)
            if not categories or set(categories) & set(_meta(b)["categories"])
        ]
        return ids[:n]

    def eligible(self, ids):
        return [int(b) for b in ids if 1 <= int(b) <= N_CAT]


class _Nbrs:
    """시드 1 의 이웃 = 2..21, 가중 내림차순."""

    def neighbors(self, book_id, n=20):
        return [(book_id + i, round(0.95 - 0.02 * i, 3)) for i in range(1, n + 1)]


class _NbrsIneligible:
    """41..60 — 전부 자격 없음."""

    def neighbors(self, book_id, n=20):
        return [(40 + i, 0.5) for i in range(1, n + 1)]


def _items(ids, source="content"):
    return [
        ScoredItem(
            book_id=b,
            score=float(60 - i),
            source=source,
            position=i,
            source_channels=(source,),
        )
        for i, b in enumerate(ids)
    ]


def _rows5(**kw):
    """5행 표준 호출 → (rows, dedup_removed)."""
    args = dict(
        items=_items(ITEMS5),
        catalog=_Cat(),
        neighbors=_Nbrs(),
        level=0,
        seeds=(1,),
        categories=("소설",),
        criterion="bestseller",
        persona_name="오디세우스",
        continue_ids=(19,),
        all_categories=CATS,
    )
    args.update(kw)
    return compose_rows(**args)


# ── 계약 ────────────────────────────────────────────────────────────────
def test_compose_level0_returns_five_rows_in_render_order():
    rows, _ = _rows5()
    assert [r.row_id for r in rows] == [
        "continue_reading",
        "anchor_1",
        "persona_shelf",
        "trending",
        "fresh_picks",
    ]
    assert [r.purpose for r in rows] == ["resume", "discover", "discover", "fallback", "explore"]
    assert all(len(r.items) <= 12 for r in rows)
    for r in rows:
        RowOut.model_validate(asdict(r))


def test_anchor_row_is_content_channel_with_reason_and_meta():
    rows, _ = _rows5()
    row_ids = [r.row_id for r in rows]
    assert "anchor_1" in row_ids
    anchor = rows[row_ids.index("anchor_1")]
    assert anchor.title == ANCHOR_REASON
    assert anchor.subtitle == "결이 비슷한 책"
    ids = [i.book_id for i in anchor.items]
    assert ids == list(range(2, 14))
    assert all(i.source == "content" for i in anchor.items)
    assert all(i.source_channels == ("content",) for i in anchor.items)
    assert all(i.reason == ANCHOR_REASON for i in anchor.items)
    assert anchor.channel_mix == {"content": 12}
    scores = [i.score for i in anchor.items]
    assert scores == sorted(scores, reverse=True)
    assert [i.position for i in anchor.items] == list(range(12))
    assert all(i.title for i in anchor.items)
    assert 1 not in ids and 19 not in ids and 21 not in ids


def test_persona_shelf_excludes_used_keeps_order_and_title():
    rows, _ = _rows5()
    by_id = {r.row_id: r for r in rows}
    assert "persona_shelf" in by_id
    shelf = by_id["persona_shelf"]
    assert shelf.title == "오디세우스의 서가"
    assert [i.book_id for i in shelf.items] == [14, 15, 16, 18, 20, 21, 22, 23, 24, 25, 26]
    assert shelf.channel_mix == {"content": 11}
    assert [i.position for i in shelf.items] == list(range(11))
    rows2, _ = _rows5(persona_name=None)
    assert {r.row_id: r.title for r in rows2}["persona_shelf"] == "회원님의 서가"


def test_continue_reading_row_from_ids_or_empty():
    rows, _ = _rows5()
    assert [r.row_id for r in rows][:1] == ["continue_reading"]
    cont = rows[0]
    assert cont.title == "이어 읽기"
    assert [i.book_id for i in cont.items] == [19]
    assert cont.items[0].title == "밀리 표본 도서 19"
    rows2, _ = _rows5(continue_ids=())
    assert rows2[0].row_id == "continue_reading"
    assert rows2[0].items == ()


def test_trending_row_uses_global_popular_minus_used():
    rows, _ = _rows5()
    by_id = {r.row_id: r for r in rows}
    assert "trending" in by_id
    trend = by_id["trending"]
    assert trend.title == "지금 많이 읽는 책"
    assert [i.book_id for i in trend.items] == list(range(27, 39))
    assert all(i.source == "popularity" for i in trend.items)
    assert trend.channel_mix == {"popularity": 12}


def test_fresh_picks_outside_selected_categories_round_robin():
    rows, _ = _rows5()
    by_id = {r.row_id: r for r in rows}
    assert "fresh_picks" in by_id
    fresh = by_id["fresh_picks"]
    fresh_ids = [i.book_id for i in fresh.items]
    assert fresh_ids == [39, 40]
    assert all("소설" not in _meta(b)["categories"] for b in fresh_ids)
    earlier = {i.book_id for r in rows[:-1] for i in r.items}
    assert not (earlier & set(fresh_ids))
    rows2, removed2 = compose_rows(
        items=(),
        catalog=_Cat(),
        neighbors=None,
        level=0,
        seeds=(),
        categories=("소설",),
        all_categories=CATS,
    )
    by2 = {r.row_id: r for r in rows2}
    assert [i.book_id for i in by2["fresh_picks"].items] == [
        14,
        15,
        16,
        18,
        19,
        20,
        22,
        23,
        24,
        26,
        27,
        28,
    ]
    assert [i.book_id for i in by2["trending"].items] == list(range(1, 13))
    assert by2["persona_shelf"].items == ()
    assert removed2 == 0


# ── 정확성 ──────────────────────────────────────────────────────────────
def test_dedup_by_book_id_and_normalized_title_counts_removed():
    rows, removed = _rows5()
    assert removed == 1
    all_ids = [i.book_id for r in rows for i in r.items]
    assert len(all_ids) == len(set(all_ids))
    titles = [normalize_title(i.title) for r in rows for i in r.items]
    assert len(titles) == len(set(titles))
    for r in rows:
        expected: dict[str, int] = {}
        for i in r.items:
            for ch in i.source_channels:
                expected[ch] = expected.get(ch, 0) + 1
        assert r.channel_mix == expected


def test_normalize_title_strips_space_symbols_and_casefolds():
    assert normalize_title("데미안 (세계문학전집 44)") == "데미안세계문학전집44"
    assert normalize_title("데미안(세계문학전집44)") == "데미안세계문학전집44"
    assert normalize_title(None) == ""
    assert normalize_title(" Demian ") == "demian"


def test_badge_for_six_types_and_review_three_step_fallback():
    m1, m5, m7, m9 = _meta(1), _meta(5), _meta(7), _meta(9)
    assert badge_for(m7, criterion="bestseller") == Badge("bestseller", "인기 7위")
    assert badge_for(m7, criterion="review") == Badge("review", "★4.2 · 리뷰 21")
    assert badge_for(m5, criterion="review") == Badge("review", "리뷰 15")
    low = badge_for({**m5, "review_count": 6}, criterion="review")
    assert low == Badge("bestseller", "인기 5위")
    hit_a = badge_for(m1, criterion="author", seed_authors=frozenset({"저자 1"}))
    assert hit_a == Badge("author", "저자 1 작가")
    assert badge_for(m1, criterion="author", seed_authors=frozenset({"저자 2"})) is None
    hit_p = badge_for(m1, criterion="publisher", seed_publishers=frozenset({"출판사 A"}))
    assert hit_p == Badge("publisher", "출판사 A 출판")
    assert badge_for(m1, criterion="publisher", seed_publishers=frozenset({"출판사 B"})) is None
    assert badge_for(m9, criterion="buzz") == Badge("buzz", "밀리 픽")
    assert badge_for(m1, criterion="buzz") is None
    assert badge_for(m7, criterion="light") is None
    assert badge_for(m7, criterion=None) is None
    for c in ("bestseller", "review", "author", "publisher", "buzz", "light"):
        b = badge_for(
            m9,
            criterion=c,
            seed_authors=frozenset({"저자 0"}),
            seed_publishers=frozenset({"출판사 A"}),
        )
        assert b is None or b.type in BADGE_TYPES


def test_badges_attached_to_all_rows_when_criterion_else_none():
    rows, _ = _rows5()
    assert len(rows) == 5
    items = [i for r in rows for i in r.items]
    assert items and all(i.badge is not None for i in items)
    assert all(i.badge.type == "bestseller" for i in items)
    rows2, _ = _rows5(criterion=None)
    assert all(i.badge is None for r in rows2 for i in r.items)


def test_nonpersonal_level3_gives_trending_and_fresh_only():
    rows, removed = compose_rows(
        items=_items([1, 2, 3, 4, 5], source="popularity"),
        catalog=_Cat(),
        neighbors=None,
        level=3,
        all_categories=CATS,
    )
    assert [r.row_id for r in rows] == ["trending", "fresh_picks"]
    assert [i.book_id for i in rows[0].items] == [1, 2, 3, 4, 5]
    assert [i.book_id for i in rows[1].items] == [9, 6, 7, 8, 13, 10, 11, 12, 14, 15, 16]
    assert removed == 1
    rows2, _ = compose_rows(
        items=_items([1, 2], source="popularity"),
        catalog=_Cat(),
        neighbors=None,
        level=2,
        all_categories=CATS,
    )
    assert [r.row_id for r in rows2] == ["trending", "fresh_picks"]


def test_catalog_categories_sorted_by_count_unique():
    cats = catalog_categories(_Cat())
    assert cats == ["소설", "에세이", "경제경영", "인문"]
    assert len(cats) == len(set(cats))


def test_with_meta_joins_five_fields_and_none_catalog_passthrough():
    out = with_meta(_items([1, 2]), _Cat())
    assert [i.title for i in out] == ["밀리 표본 도서 1", "밀리 표본 도서 2"]
    assert [i.authors for i in out] == ["저자 1", "저자 2"]
    assert all(i.image_url and i.book_format == "전자책" for i in out)
    assert all(i.difficulty == 0.4 for i in out)
    raw = _items([1, 2])
    assert with_meta(raw, None) == tuple(raw)
    kept = with_meta([replace(_items([1])[0], difficulty=0.9)], _Cat())
    assert kept[0].difficulty == 0.9


# ── 안전성 ──────────────────────────────────────────────────────────────
def test_anchor_row_omitted_without_neighbors_seeds_or_eligible():
    expected = ["continue_reading", "persona_shelf", "trending", "fresh_picks"]
    for kw in ({"neighbors": None}, {"seeds": ()}, {"neighbors": _NbrsIneligible()}):
        rows, _ = _rows5(**kw)
        row_ids = [r.row_id for r in rows]
        assert row_ids == expected
        assert "anchor_" not in "".join(row_ids)


def test_build_response_default_path_is_unchanged_phase2_shape():
    items = _items([4, 5, 6, 7, 8], "popularity")
    resp = build_response(
        items, model_version="pop_v1", level=0, k=5, t0=perf_counter(), context=None
    )
    assert len(resp.rows) == 1
    assert resp.rows[0].row_id == "trending"
    assert resp.rows[0].channel_mix == {"popularity": 5}
    assert [i.book_id for i in resp.items] == [4, 5, 6, 7, 8]
    assert set(resp.latency_breakdown) == {"total"}
    assert resp.user_state_weights == ZERO_WEIGHTS
    assert resp.dedup_removed == 0
    resp3 = build_response(
        items, model_version="fallback_v1", level=3, k=5, t0=perf_counter(), context=None
    )
    assert resp3.items == ()


def test_build_response_with_rows_flattens_top_k_and_merges_breakdown_weights():
    rows5, removed = _rows5()
    bd = {"feature": 1.0, "pipeline": 2.0, "compose": 0.5}
    weights = {"alpha": 1.0, "beta": 0.0, "gamma": 0.0}
    resp = build_response(
        [],
        model_version="hybrid_v1",
        level=0,
        k=3,
        t0=perf_counter(),
        context=None,
        rows=rows5,
        dedup_removed=removed,
        latency_breakdown=bd,
        user_state_weights=weights,
    )
    assert resp.rows == tuple(rows5)
    assert [i.book_id for i in resp.items] == [19, 2, 3]
    assert resp.items[1].title == "밀리 표본 도서 2"
    assert resp.items[1].reason == ANCHOR_REASON
    assert set(resp.latency_breakdown) == {"feature", "pipeline", "compose", "total"}
    assert resp.latency_breakdown["total"] == resp.latency_ms
    assert resp.user_state_weights == weights
    assert resp.dedup_removed == 1
    r1 = build_response(
        [], model_version="hybrid_v1", level=1, k=2, t0=perf_counter(), context=None, rows=rows5
    )
    assert [i.book_id for i in r1.items] == [19, 2]
    r2 = build_response(
        [], model_version="hybrid_v1", level=2, k=2, t0=perf_counter(), context=None, rows=rows5
    )
    assert r2.items == ()
