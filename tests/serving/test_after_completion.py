"""after_completion — 완독 직후 최상단 행(D-13 · SERV-11) · 옛 캐시 폐기(D-10).

Phase 5 '서빙 Must 완성'(.planning/ROADMAP.md).
결정 D-13·D-10(.planning/phases/05-must/05-CONTEXT.md).
state 저장·덮어쓰기 → Nearline 사전 계산 → compose 최상단 → HTTP 끝단(SERV-09 경계).
가짜는 파일마다 복제한다(테스트 간 import 금지 관례).
"""

import asyncio
import time
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from millie_rec.contracts import DB_FILENAME, ScoredItem, UserState
from millie_rec.data.catalog_kr import CatalogKR
from millie_rec.serving.after_completion import ROW_ID_AFTER, precompute, stored
from millie_rec.serving.api import create_app
from millie_rec.serving.compose import compose_rows
from millie_rec.serving.db import Database
from millie_rec.serving.fallback import GlobalPopularFallback
from millie_rec.serving.nearline import NearlineLoop
from millie_rec.serving.state import StateStore

T0 = 1_800_000_000.0
CATS = ("소설", "에세이", "경제경영", "인문")
N_CAT = 40
ITEMS5 = [14, 15, 16, 17, 18, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 7]
ROWS5 = ["continue_reading", "anchor_1", "persona_shelf", "trending", "fresh_picks"]
SEEDS = [1, 2, 3, 4, 5]
UK = "u-after-1"
SQL_INSERT = "INSERT INTO events(event_id, user_key, book_id, event_type, ts) VALUES(?, ?, ?, ?, ?)"


def _iso(epoch: float) -> str:
    return datetime.fromtimestamp(epoch, UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


# ── compose 가짜(test_compose.py 복제) ───────────────────────────────────
def _meta(b: int) -> dict:
    return {
        "book_id": b,
        "title": f"밀리 표본 도서 {b}",
        "authors": f"저자 {b % 3}",
        "image_url": f"https://img.millie.co.kr/{b}.jpg",
        "book_format": "전자책",
        "difficulty": 0.4,
        "categories": [CATS[(b - 1) % 4]],
        "publisher": "출판사 A",
        "pop_rank": b,
        "average_rating": 4.2,
        "review_count": b * 3,
        "millie_label": None,
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
    """시드의 이웃 = seed+1 .. seed+n, 가중 내림차순. 호출을 기록한다."""

    def __init__(self) -> None:
        self.calls: list[tuple[int, int]] = []

    def neighbors(self, book_id, n=20):
        self.calls.append((int(book_id), int(n)))
        return [(int(book_id) + i, round(0.95 - 0.02 * i, 3)) for i in range(1, n + 1)]


def _items(ids, source="content"):
    return [
        ScoredItem(b, float(60 - i), source, position=i, source_channels=(source,))
        for i, b in enumerate(ids)
    ]


def _rows5(**kw):
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


# ── HTTP 조립(test_cascade.py 복제) ──────────────────────────────────────
class _Fake:
    """seen 을 뺀 1..17 상위 k."""

    def __init__(self, name: str = "hybrid", reverse: bool = False) -> None:
        self.name, self.reverse = name, reverse

    def recommend(self, user: UserState, k: int) -> list[ScoredItem]:
        ids = [b for b in range(1, 18) if b not in user.seen]
        if self.reverse:
            ids = list(reversed(ids))
        return [
            ScoredItem(b, float(100 - n), "content", position=n, source_channels=("content",))
            for n, b in enumerate(ids[:k])
        ]


class _Slow(_Fake):
    """D-10 예산 초과용 — 10ms 를 쓴다. BUDGET_MS monkeypatch 와 함께."""

    def recommend(self, user: UserState, k: int) -> list[ScoredItem]:
        time.sleep(0.01)
        return super().recommend(user, k)


async def _idle(self: NearlineLoop) -> None:
    """살아 있는 루프가 이벤트를 먼저 먹는 경쟁을 끈다(C7). run_once 는 테스트가 부른다."""
    await asyncio.Event().wait()


@pytest.fixture(autouse=True)
def _no_nearline_loop(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(NearlineLoop, "run", _idle)


@pytest.fixture
def catalog(millie_serving_sample: Path) -> CatalogKR:
    return CatalogKR.load(millie_serving_sample)


def _full(tmp_path: Path, catalog, pipelines=None):
    pipes = pipelines or {"hybrid": _Fake("hybrid"), "hybrid_div": _Fake("hybrid_div", True)}
    return create_app(
        pipelines=pipes,
        fallback=GlobalPopularFallback(catalog),
        catalog=catalog,
        db=Database(tmp_path / DB_FILENAME),
        neighbors=catalog,
        state=StateStore(),
    )


def _onboard(c: TestClient) -> None:
    body = {"user_key": UK, "categories": ["소설"], "criterion": "bestseller", "seeds": SEEDS}
    assert c.post("/api/preferences", json=body).status_code == 201


def _complete(c: TestClient, app, event_id: str, book_id: int) -> None:
    ev = {
        "event_id": event_id,
        "user_key": UK,
        "book_id": book_id,
        "event_type": "completion",
        "ts": _iso(time.time()),
    }
    assert c.post("/api/events", json=ev).status_code == 202
    app.state.nearline.run_once()


def _row_ids(d: dict) -> list[str]:
    return [r["row_id"] for r in d["rows"]]


# ── 계약 ────────────────────────────────────────────────────────────────
def test_state_set_get_overwrite_forget():
    store, nbrs = StateStore(), _Nbrs()
    assert stored(store, "u") is None
    precompute(store, "u", 3, nbrs)
    assert nbrs.calls == [(3, 20)]
    assert stored(store, "u") == (3, tuple(nbrs.neighbors(3, 20)))
    precompute(store, "u", 7, nbrs)
    assert stored(store, "u")[0] == 7  # 새 완독이 덮어쓴다(D-13)
    store.forget("u")
    assert stored(store, "u") is None


def test_compose_default_none_keeps_five_rows():
    rows, _ = _rows5()
    assert [r.row_id for r in rows] == ROWS5


# ── 정확성 ──────────────────────────────────────────────────────────────
def test_nearline_completion_precomputes_neighbors_only(tmp_path: Path):
    db, store, nbrs = Database(tmp_path / "t.db"), StateStore(), _Nbrs()
    db.apply_schema()
    loop = NearlineLoop(db, store, neighbors=nbrs, now=lambda: T0)
    con = db.connect()
    with con:
        con.execute(SQL_INSERT, ("e1", "u", 5, "reader_open", _iso(T0)))
    loop.run_once()
    assert nbrs.calls == []  # reader_open 은 이웃을 부르지 않는다
    with con:
        con.execute(SQL_INSERT, ("e2", "u", 3, "completion", _iso(T0)))
    loop.run_once()
    assert nbrs.calls == [(3, 20)]
    got = stored(store, "u")
    assert got is not None and got[0] == 3
    assert got[1] == tuple(_Nbrs().neighbors(3, 20))


def test_nearline_without_neighbors_keeps_none(tmp_path: Path):
    db, store = Database(tmp_path / "t.db"), StateStore()
    db.apply_schema()
    loop = NearlineLoop(db, store, neighbors=None, now=lambda: T0)
    con = db.connect()
    with con:
        con.execute(SQL_INSERT, ("e1", "u", 3, "completion", _iso(T0)))
    assert loop.run_once() == 1
    assert stored(store, "u") is None
    assert store.n_completed("u") == 1  # apply_event 는 그대로 돈다


def test_compose_after_completion_row_first_content_channel():
    rows, _ = _rows5(after_completion=(3, [(4, 0.9), (5, 0.8), (6, 0.7)]))
    first = rows[0]
    assert first.row_id == ROW_ID_AFTER
    assert first.title == "『밀리 표본 도서 3』을 완독하셨네요, 다음은"
    assert first.purpose == "discover"
    assert [i.book_id for i in first.items] == [4, 5, 6]
    assert all(i.source == "content" and i.source_channels == ("content",) for i in first.items)
    assert all(i.reason == first.title for i in first.items)
    assert first.channel_mix == {"content": 3}
    assert [r.row_id for r in rows[1:]] == ROWS5


def test_compose_after_completion_dedup_wins_over_anchor():
    base_rows, base_removed = _rows5()
    anchor_first = next(r for r in base_rows if r.row_id == "anchor_1").items[0].book_id
    rows, removed = _rows5(after_completion=(3, [(anchor_first, 0.9)]))
    anchor = next(r for r in rows if r.row_id == "anchor_1")
    assert [i.book_id for i in rows[0].items] == [anchor_first]
    assert anchor_first not in [i.book_id for i in anchor.items]
    assert removed == base_removed + 1


def test_compose_nonpersonal_ignores_after_completion():
    for level in (2, 3):
        rows, _ = _rows5(level=level, after_completion=(3, [(4, 0.9), (5, 0.8)]))
        assert [r.row_id for r in rows] == ["trending", "fresh_picks"]


# ── 안전성 · HTTP 끝단 ───────────────────────────────────────────────────
def test_http_completion_event_then_run_once_prepends_row(tmp_path: Path, catalog):
    app = _full(tmp_path, catalog)
    with TestClient(app) as c:
        _onboard(c)
        assert _row_ids(c.get("/api/recommend", params={"user_key": UK}).json()) == ROWS5
        ev = {
            "event_id": "e1",
            "user_key": UK,
            "book_id": 9,
            "event_type": "completion",
            "ts": _iso(time.time()),
        }
        assert c.post("/api/events", json=ev).status_code == 202
        mid = c.get("/api/recommend", params={"user_key": UK}).json()
        assert _row_ids(mid) == ROWS5  # SERV-09: Nearline 전에는 바뀌지 않는다
        app.state.nearline.run_once()
        after = c.get("/api/recommend", params={"user_key": UK}).json()
        anon = c.get("/api/recommend").json()
        _complete(c, app, "e2", 13)
        again = c.get("/api/recommend", params={"user_key": UK}).json()
        assert c.delete(f"/api/users/{UK}/personalization").status_code == 200
        gone = c.get("/api/recommend", params={"user_key": UK}).json()
    assert after["fallback_level"] == 0 and len(after["rows"]) == 6
    assert _row_ids(after) == [ROW_ID_AFTER, *ROWS5]
    assert "밀리 표본 도서 9" in after["rows"][0]["title"]
    assert "완독하셨네요" in after["rows"][0]["title"]
    assert after["rows"][0]["items"]
    personal = [r for r in after["rows"] if r["row_id"] in (ROW_ID_AFTER, "persona_shelf")]
    assert 9 not in {i["book_id"] for r in personal for i in r["items"]}  # 완독 책은 빠진다
    assert ROW_ID_AFTER not in _row_ids(anon)  # 익명 level 3 은 개인화 행이 없다
    assert "밀리 표본 도서 13" in again["rows"][0]["title"]  # 새 완독이 덮어쓴다
    assert ROW_ID_AFTER not in _row_ids(gone)


def test_http_stale_cache_not_served_after_completion(tmp_path: Path, catalog, monkeypatch):
    slow = {"hybrid": _Slow("hybrid"), "hybrid_div": _Slow("hybrid_div", True)}
    app = _full(tmp_path, catalog, slow)
    with TestClient(app) as c:
        _onboard(c)
        first = c.get("/api/recommend", params={"user_key": UK}).json()
        _complete(c, app, "e1", 9)
        monkeypatch.setattr("millie_rec.serving.fallback.BUDGET_MS", 1)
        stale = c.get("/api/recommend", params={"user_key": UK}).json()
    assert first["fallback_level"] == 0 and ROW_ID_AFTER not in _row_ids(first)
    assert stale["fallback_level"] == 2  # 옛 캐시(완독 전 rows)를 내지 않는다(D-10 · T-05-10-03)
    assert _row_ids(stale) == ["trending", "fresh_picks"]
