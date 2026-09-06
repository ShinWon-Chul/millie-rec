"""/api/recommend 통합 — user_key 5행 · 셀 배정 · cascade 0→1→2→3 · 추천 로그 · Nearline 경계.

Phase 5 '서빙 Must 완성'(.planning/ROADMAP.md). 결정 D-01·D-09~D-12(05-CONTEXT.md).
가짜 Pipeline + 합성 카탈로그(conftest millie_serving_sample) 조립 — 모델 슬라이스는 부르지 않는다.
가짜는 파일마다 복제한다(테스트 간 import 금지 관례).
"""

import asyncio
import hashlib
import json
import sqlite3
import time
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from millie_rec.contracts import (
    DB_FILENAME,
    MODEL_VERSION_FALLBACK,
    MODEL_VERSION_SUFFIX,
    ROW_IDS,
    ScoredItem,
    UserState,
)
from millie_rec.data.catalog_kr import CatalogKR
from millie_rec.serving import cascade as cascade_mod
from millie_rec.serving import rec_log
from millie_rec.serving.api import create_app
from millie_rec.serving.cascade import CELL_VARIANT, PIPE_K_MIN, resolve_user
from millie_rec.serving.db import Database
from millie_rec.serving.fallback import GlobalPopularFallback, Level1Cache
from millie_rec.serving.nearline import NearlineLoop
from millie_rec.serving.schemas import RecommendOut
from millie_rec.serving.state import StateStore

ZERO = {"alpha": 0.0, "beta": 0.0, "gamma": 0.0}
CATS = ["소설", "IT"]  # IT 는 표본에 없다 — 교집합만 남는지 확인용
SEEDS = [1, 2, 3, 4, 5]
ROWS5 = ["continue_reading", "anchor_1", "persona_shelf", "trending", "fresh_picks"]
ANCHOR_REASON = "『밀리 표본 도서 1』을 좋아하셨다면"
SQL_LOG = (
    "SELECT recommendation_id, user_key, snapshot_id, model_version, cell, forced, "
    "fallback_level, latency_total_ms, latency_breakdown, weights, rows FROM recommendations"
)
clock = {"t": time.time()}


class _Fake:
    """seen 을 뺀 1..17 상위 k. reverse 로 두 variant 의 순서를 다르게 만든다."""

    def __init__(self, name: str = "hybrid", reverse: bool = False) -> None:
        self.name = name
        self.reverse = reverse
        self.calls: list[int] = []

    def recommend(self, user: UserState, k: int) -> list[ScoredItem]:
        self.calls.append(k)
        ids = [b for b in range(1, 18) if b not in user.seen]
        if self.reverse:
            ids = list(reversed(ids))
        return [
            ScoredItem(b, float(100 - n), "content", position=n, source_channels=("content",))
            for n, b in enumerate(ids[:k])
        ]


class _Slow(_Fake):
    """D-10 예산 초과용 — 10ms 를 쓴다. BUDGET_MS monkeypatch 와 함께 쓴다."""

    def recommend(self, user: UserState, k: int) -> list[ScoredItem]:
        time.sleep(0.01)
        return super().recommend(user, k)


class _Boom:
    """recommend 가 항상 예외 — '추천 API 장애 ≠ 메인 장애' 증거용 가짜 Pipeline."""

    def __init__(self, name: str = "hybrid") -> None:
        self.name = name

    def recommend(self, user: UserState, k: int) -> list[ScoredItem]:
        raise RuntimeError("boom")


def _cell(user_key: str) -> str:
    """백엔드 01 §5 — CPython hash() 금지, sha256 앞 8hex 의 짝/홀."""
    return "A" if int(hashlib.sha256(user_key.encode()).hexdigest()[:8], 16) % 2 == 0 else "B"


UK_A = next(f"u-a-{i}" for i in range(99) if _cell(f"u-a-{i}") == "A")
UK_B = next(f"u-b-{i}" for i in range(99) if _cell(f"u-b-{i}") == "B")


def _iso(epoch: float) -> str:
    return datetime.fromtimestamp(epoch, UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _weights(u: UserState, **kw: object) -> dict[str, float]:
    """테스트용 — 인자 도달(배선) 증거만 본다. 실제 혼합비는 ranking.state_weights."""
    out = {
        "alpha": 1.0 if u.explicit_seeds else 0.0,
        "beta": 1.0 if u.history else 0.0,
        "gamma": 0.1 if kw.get("session_active") else 0.0,
    }
    if kw.get("reset_boost"):
        out["reset"] = 1.0
    return out


async def _idle(self: NearlineLoop) -> None:
    """살아 있는 루프가 이벤트를 먼저 먹는 경쟁을 끈다(C7). run_once 는 테스트가 직접 부른다."""
    await asyncio.Event().wait()


@pytest.fixture(autouse=True)
def _no_nearline_loop(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(NearlineLoop, "run", _idle)


@pytest.fixture
def catalog(millie_serving_sample: Path) -> CatalogKR:
    return CatalogKR.load(millie_serving_sample)


def _app(
    tmp_path: Path, pipelines: dict, *, catalog=None, state=None, weights=None, name=DB_FILENAME
):
    return create_app(
        pipelines=pipelines,
        fallback=GlobalPopularFallback(catalog),
        catalog=catalog,
        db=Database(tmp_path / name),
        neighbors=catalog,
        state=state,
        weights=weights,
    )


def _full(tmp_path: Path, catalog, pipelines: dict | None = None, weights=_weights):
    """카탈로그·상태·가중치까지 붙인 완전 조립(기본 파이프라인 2벌)."""
    pipes = (
        pipelines
        if pipelines is not None
        else {
            "hybrid": _Fake("hybrid"),
            "hybrid_div": _Fake("hybrid_div", True),
        }
    )
    return _app(
        tmp_path, pipes, catalog=catalog, state=StateStore(now=lambda: clock["t"]), weights=weights
    )


def _onboard(c: TestClient, user_key: str, **body: object) -> dict:
    payload: dict = {
        "user_key": user_key,
        "categories": CATS,
        "criterion": "bestseller",
        "seeds": SEEDS,
    }
    payload.update(body)
    r = c.post("/api/preferences", json=payload)
    assert r.status_code == 201, r.text
    return r.json()


def _ids(d: dict) -> list[tuple[str, int]]:
    return [(r["row_id"], i["book_id"]) for r in d["rows"] for i in r["items"]]


def _all_books(d: dict) -> set[int]:
    return {i["book_id"] for r in d["rows"] for i in r["items"]}


# ── 계약 ────────────────────────────────────────────────────────────────
def test_user_key_level0_returns_five_rows_anchor_content_and_echo_fields(tmp_path, catalog):
    with TestClient(_full(tmp_path, catalog)) as c:
        snap = _onboard(c, UK_A)
        r = c.get("/api/recommend", params={"user_key": UK_A, "k": 40})
    assert r.status_code == 200, r.text
    out = RecommendOut.model_validate(r.json())
    assert out.fallback_level == 0
    assert [row.row_id for row in out.rows] == ROWS5
    anchor = next(row for row in out.rows if row.row_id == "anchor_1")
    assert anchor.items
    assert all(i.source == "content" and i.source_channels == ["content"] for i in anchor.items)
    assert all(i.reason == ANCHOR_REASON for i in anchor.items)
    assert anchor.channel_mix == {"content": len(anchor.items)}
    assert out.user_key == UK_A and out.cell == _cell(UK_A)
    assert out.preference_snapshot_id == snap["preference_snapshot_id"]
    first = next(row for row in out.rows if row.items)
    assert out.items[0].book_id == first.items[0].book_id
    assert len(out.items) <= 40 and out.dedup_removed >= 0
    assert not ({18, 19, 20} & _all_books(r.json()))
    assert {"feature", "pipeline", "compose", "total"} <= set(out.latency_breakdown)


def test_cell_assignment_picks_variant_and_model_query_forces(tmp_path, catalog):
    with TestClient(_full(tmp_path, catalog)) as c:
        _onboard(c, UK_A)
        _onboard(c, UK_B)
        a = c.get("/api/recommend", params={"user_key": UK_A}).json()
        b = c.get("/api/recommend", params={"user_key": UK_B}).json()
        pop = c.get("/api/recommend", params={"user_key": UK_A, "model": "pop"}).json()
        hy = c.get("/api/recommend", params={"user_key": UK_B, "model": "hybrid"}).json()
    assert a["cell"] == "A" and a["model_version"] == CELL_VARIANT["A"] + MODEL_VERSION_SUFFIX
    assert b["cell"] == "B" and b["model_version"] == CELL_VARIANT["B"] + MODEL_VERSION_SUFFIX
    assert a["forced"] is False and b["forced"] is False
    # 등록되지 않은 model= 은 셀 배정으로 되돌아가되 forced 는 남는다(D-01 우선순위)
    assert pop["model_version"] == CELL_VARIANT["A"] + MODEL_VERSION_SUFFIX
    assert pop["forced"] is True
    # 등록된 model= 은 셀(B→hybrid_div)을 이긴다
    assert hy["model_version"] == "hybrid" + MODEL_VERSION_SUFFIX and hy["forced"] is True


def test_seeds_only_cold_start_keeps_single_trending_row_with_and_without_catalog(
    tmp_path, catalog
):
    with TestClient(_full(tmp_path, catalog)) as c:
        d = c.get("/api/recommend", params={"seeds": "1,2,3", "k": 5}).json()
    assert d["fallback_level"] == 0
    assert len(d["rows"]) == 1 and d["rows"][0]["row_id"] == "trending"
    assert len(d["items"]) == 5
    bare = create_app(
        pipelines={}, fallback=GlobalPopularFallback(None), db=Database(tmp_path / "bare.db")
    )
    with TestClient(bare) as c:
        s = c.get("/api/recommend", params={"seeds": "1,2,3", "k": 5}).json()
    assert len(s["rows"]) == 1 and s["rows"][0]["items"] == []
    assert s["items"] == [] and "total" in s["latency_breakdown"]
    assert s["user_state_weights"] == ZERO and s["model_version"] == MODEL_VERSION_FALLBACK


def test_anonymous_with_catalog_gets_trending_and_fresh_picks_with_titles(tmp_path, catalog):
    with TestClient(_full(tmp_path, catalog)) as c:
        d = c.get("/api/recommend").json()
    assert d["fallback_level"] == 3
    assert [r["row_id"] for r in d["rows"]] == ["trending", "fresh_picks"]
    assert d["rows"][0]["items"][0]["title"].startswith("밀리 표본 도서")
    assert d["items"] == [] and d["user_state_weights"] == ZERO
    bare = _app(tmp_path, {}, name="anon.db")
    with TestClient(bare) as c:
        s = c.get("/api/recommend").json()
    assert len(s["rows"]) == 1


def test_consent_false_is_level3_two_rows_zero_weights(tmp_path, catalog):
    with TestClient(_full(tmp_path, catalog)) as c:
        _onboard(c, "skip-1", consent=False, categories=[], criterion=None, seeds=[])
        d = c.get("/api/recommend", params={"user_key": "skip-1"}).json()
    assert d["fallback_level"] == 3
    assert [r["row_id"] for r in d["rows"]] == ["trending", "fresh_picks"]
    assert d["user_state_weights"] == ZERO
    assert d["user_key"] == "skip-1" and d["cell"] == _cell("skip-1")


def test_user_key_without_snapshot_is_level3_echo_key(tmp_path, catalog):
    with TestClient(_full(tmp_path, catalog)) as c:
        d = c.get("/api/recommend", params={"user_key": "ghost-1"}).json()
    assert d["fallback_level"] == 3
    assert d["user_key"] == "ghost-1" and d["cell"] is None
    assert [r["row_id"] for r in d["rows"]] == ["trending", "fresh_picks"]


# ── 정확성 ──────────────────────────────────────────────────────────────
def test_budget_exceeded_serves_level1_from_cache_with_new_rec_id(tmp_path, catalog, monkeypatch):
    slow = {"hybrid": _Slow("hybrid"), "hybrid_div": _Slow("hybrid_div", True)}
    with TestClient(_full(tmp_path, catalog, slow)) as c:
        _onboard(c, UK_A)
        first = c.get("/api/recommend", params={"user_key": UK_A}).json()
        monkeypatch.setattr("millie_rec.serving.fallback.BUDGET_MS", 1)
        second = c.get("/api/recommend", params={"user_key": UK_A}).json()
    assert first["fallback_level"] == 0
    assert second["fallback_level"] == 1
    assert second["model_version"] == first["model_version"]
    assert _ids(second) == _ids(first)
    assert second["recommendation_id"] != first["recommendation_id"]
    assert second["items"]


def test_budget_exceeded_without_cache_serves_level2_snapshot_categories(
    tmp_path, catalog, monkeypatch
):
    slow = {"hybrid": _Slow("hybrid"), "hybrid_div": _Slow("hybrid_div", True)}
    with TestClient(_full(tmp_path, catalog, slow)) as c:
        _onboard(c, UK_A)
        monkeypatch.setattr("millie_rec.serving.fallback.BUDGET_MS", 1)
        d = c.get("/api/recommend", params={"user_key": UK_A}).json()
    assert d["fallback_level"] == 2
    assert [r["row_id"] for r in d["rows"]] == ["trending", "fresh_picks"]
    assert [i["book_id"] for i in d["rows"][0]["items"]] == [9, 13, 17]
    assert d["model_version"] == MODEL_VERSION_FALLBACK


def test_pipeline_exception_always_200_no_leak(tmp_path, catalog):
    boom = {"hybrid": _Boom("hybrid"), "hybrid_div": _Boom("hybrid_div")}
    with TestClient(_full(tmp_path, catalog, boom)) as c:
        _onboard(c, UK_A)
        r = c.get("/api/recommend", params={"user_key": UK_A})
    assert r.status_code == 200
    assert r.json()["fallback_level"] == 2
    assert "boom" not in r.text and "Traceback" not in r.text
    bare = _app(
        tmp_path,
        {"hybrid_div": _Boom("hybrid_div")},
        state=StateStore(now=lambda: clock["t"]),
        weights=_weights,
        name="boom.db",
    )
    with TestClient(bare) as c:
        _onboard(c, UK_B)
        s = c.get("/api/recommend", params={"user_key": UK_B})
    assert s.status_code == 200
    assert s.json()["fallback_level"] == 3 and len(s.json()["rows"]) == 1


def test_normal_path_never_reads_cache_fallback_path_does(tmp_path, catalog, monkeypatch):
    calls: list[tuple] = []
    orig = Level1Cache.get

    def spy(self, *a):
        calls.append(a)
        return orig(self, *a)

    monkeypatch.setattr("millie_rec.serving.fallback.Level1Cache.get", spy)
    slow = {"hybrid": _Slow("hybrid"), "hybrid_div": _Slow("hybrid_div", True)}
    with TestClient(_full(tmp_path, catalog, slow)) as c:
        _onboard(c, UK_A)
        c.get("/api/recommend", params={"user_key": UK_A})
        assert calls == []
        monkeypatch.setattr("millie_rec.serving.fallback.BUDGET_MS", 1)
        c.get("/api/recommend", params={"user_key": UK_A})
    assert len(calls) == 1


def test_every_response_logged_in_recommendations_with_rows_abbreviated(tmp_path, catalog):
    with TestClient(_full(tmp_path, catalog)) as c:
        _onboard(c, UK_A)
        lvl0 = c.get("/api/recommend", params={"user_key": UK_A}).json()
        c.get("/api/recommend", params={"seeds": "1,2,3"})
        anon = c.get("/api/recommend").json()
    con = sqlite3.connect(tmp_path / DB_FILENAME)
    logged = con.execute(SQL_LOG).fetchall()
    con.close()
    assert len(logged) == 3
    by_id = {r[0]: r for r in logged}
    r0 = by_id[lvl0["recommendation_id"]]
    assert r0[1] == UK_A and r0[2] == lvl0["preference_snapshot_id"] and r0[6] == 0
    rows = json.loads(r0[10])
    assert all(set(x) == {"row_id", "book_id", "position"} for x in rows)
    assert rows[0]["row_id"] in ROW_IDS or rows[0]["row_id"].startswith("anchor_")
    assert json.loads(r0[9]) == lvl0["user_state_weights"]
    assert json.loads(r0[8])["total"] == lvl0["latency_ms"]
    ra = by_id[anon["recommendation_id"]]
    assert ra[1] is None and ra[6] == 3


def test_events_do_not_change_state_until_nearline_run_once(tmp_path, catalog):
    app = _full(tmp_path, catalog)
    with TestClient(app) as c:
        _onboard(c, UK_A)
        before = c.get("/api/recommend", params={"user_key": UK_A}).json()
        assert before["user_state_weights"]["beta"] == 0.0
        ev = {
            "event_id": "e1",
            "user_key": UK_A,
            "book_id": 9,
            "event_type": "reader_open",
            "ts": _iso(time.time()),
        }
        assert c.post("/api/events", json=ev).status_code == 202
        mid = c.get("/api/recommend", params={"user_key": UK_A}).json()
        assert mid["user_state_weights"]["beta"] == 0.0
        app.state.nearline.run_once()
        after = c.get("/api/recommend", params={"user_key": UK_A}).json()
    assert after["user_state_weights"]["beta"] == 1.0
    cont = next(r for r in after["rows"] if r["row_id"] == "continue_reading")
    shelf = next(r for r in after["rows"] if r["row_id"] == "persona_shelf")
    assert 9 in [i["book_id"] for i in cont["items"]]
    assert 9 not in [i["book_id"] for i in shelf["items"]]


def test_session_active_and_reset_boost_kwargs_reach_weights(tmp_path, catalog):
    app = _full(tmp_path, catalog)
    with TestClient(app) as c:
        _onboard(c, UK_A)
        ev = {
            "event_id": "e2",
            "user_key": UK_A,
            "book_id": 9,
            "event_type": "reader_open",
            "ts": _iso(clock["t"]),
        }
        c.post("/api/events", json=ev)
        app.state.nearline.run_once()
        after = c.get("/api/recommend", params={"user_key": UK_A}).json()
        assert after["user_state_weights"]["gamma"] == 0.1
        _onboard(c, UK_A, restart=True)
        again = c.get("/api/recommend", params={"user_key": UK_A}).json()
    assert again["user_state_weights"]["reset"] == 1.0


def test_delete_personalization_then_level3_until_reconsent(tmp_path, catalog):
    with TestClient(_full(tmp_path, catalog)) as c:
        _onboard(c, UK_A)
        assert c.get("/api/recommend", params={"user_key": UK_A}).json()["fallback_level"] == 0
        assert c.delete(f"/api/users/{UK_A}/personalization").status_code == 200
        gone = c.get("/api/recommend", params={"user_key": UK_A}).json()
        _onboard(c, UK_A)
        back = c.get("/api/recommend", params={"user_key": UK_A}).json()
    assert gone["fallback_level"] == 3
    assert [r["row_id"] for r in gone["rows"]] == ["trending", "fresh_picks"]
    assert gone["user_state_weights"] == ZERO
    assert back["fallback_level"] == 0 and len(back["rows"]) == 5


def test_snapshot_id_must_belong_to_user_else_404(tmp_path, catalog):
    with TestClient(_full(tmp_path, catalog)) as c:
        first = _onboard(c, UK_A)["preference_snapshot_id"]
        other = _onboard(c, UK_B)["preference_snapshot_id"]
        missing = c.get("/api/recommend", params={"user_key": UK_A, "snapshot_id": "snap_zzzzzz"})
        stolen = c.get("/api/recommend", params={"user_key": UK_A, "snapshot_id": other})
        _onboard(c, UK_A, seeds=[6, 7, 8, 9, 10])
        pinned = c.get("/api/recommend", params={"user_key": UK_A, "snapshot_id": first}).json()
    assert missing.status_code == 404
    assert missing.json()["detail"] == "snapshot_id not found for user_key"
    assert stolen.status_code == 404
    assert pinned["preference_snapshot_id"] == first
    assert any(r["row_id"] == "anchor_1" for r in pinned["rows"])


def test_health_filled_with_catalog_and_none_without(tmp_path, catalog):
    with TestClient(_full(tmp_path, catalog)) as c:
        h = c.get("/health").json()
    assert h["model_version"] == "hybrid_div" + MODEL_VERSION_SUFFIX
    assert h["artifacts_loaded_at"].endswith("Z")
    assert h["nearline_last_run"] is None or h["nearline_last_run"].endswith("Z")
    bare = create_app(
        pipelines={}, fallback=GlobalPopularFallback(None), db=Database(tmp_path / "h.db")
    )
    with TestClient(bare) as c:
        h2 = c.get("/health").json()
    assert h2["model_version"] is None and h2["artifacts_loaded_at"] is None


# ── 안전성 ──────────────────────────────────────────────────────────────
def test_user_key_format_422_and_empty_is_anonymous(tmp_path, catalog):
    with TestClient(_full(tmp_path, catalog)) as c:
        bad = c.get("/api/recommend", params={"user_key": "x" * 65})
        empty = c.get("/api/recommend", params={"user_key": ""}).json()
    assert bad.status_code == 422
    assert empty["fallback_level"] == 3 and empty["user_key"] is None


def test_lifespan_replays_24h_and_closes_db(tmp_path, catalog, monkeypatch):
    with TestClient(_full(tmp_path, catalog)) as c:
        _onboard(c, UK_A)
    con = sqlite3.connect(tmp_path / DB_FILENAME)  # C7: 테스트 스레드와 분리된 연결
    with con:
        con.execute(
            "INSERT INTO events(event_id, user_key, book_id, event_type, ts) VALUES(?,?,?,?,?)",
            ("replay-1", UK_A, 9, "reader_open", _iso(time.time())),
        )
    con.close()
    closes: list[int] = []
    orig = Database.close

    def spy(self) -> None:
        closes.append(1)
        orig(self)

    monkeypatch.setattr(Database, "close", spy)
    with TestClient(_full(tmp_path, catalog)) as c:
        d = c.get("/api/recommend", params={"user_key": UK_A}).json()
    assert d["user_state_weights"]["beta"] == 1.0
    assert len(closes) == 1


def test_k_upper_bound_and_row_sizes(tmp_path, catalog):
    with TestClient(_full(tmp_path, catalog)) as c:
        _onboard(c, UK_A)
        d = c.get("/api/recommend", params={"user_key": UK_A, "k": 100}).json()
    assert len(d["items"]) <= 100
    assert all(len(r["items"]) <= 12 for r in d["rows"])


def test_weights_exception_degrades_to_fallback_200(tmp_path, catalog):
    with TestClient(_full(tmp_path, catalog, weights=lambda u, **kw: 1 / 0)) as c:
        _onboard(c, UK_A)
        r = c.get("/api/recommend", params={"user_key": UK_A})
    assert r.status_code == 200
    assert r.json()["fallback_level"] in (1, 2, 3)
    assert r.json()["user_state_weights"] == ZERO


def test_forced_flag_only_when_model_query(tmp_path, catalog):
    with TestClient(_full(tmp_path, catalog)) as c:
        _onboard(c, UK_A)
        plain = c.get("/api/recommend", params={"user_key": UK_A}).json()
        forced = c.get("/api/recommend", params={"user_key": UK_A, "model": "hybrid_div"}).json()
        anon = c.get("/api/recommend").json()
    assert plain["forced"] is False and anon["forced"] is False
    assert forced["forced"] is True


def test_recommend_never_returns_ineligible_or_seen(tmp_path, catalog):
    with TestClient(_full(tmp_path, catalog)) as c:
        _onboard(c, UK_A)
        d = c.get("/api/recommend", params={"user_key": UK_A, "k": 100}).json()
    books = _all_books(d)
    assert not (books & {18, 19, 20})
    assert not (books & set(SEEDS))


def test_cold_start_passes_k_unchanged_personal_uses_pipe_k_min(tmp_path, catalog):
    fake = _Fake("hybrid_div", True)
    with TestClient(_full(tmp_path, catalog, {"hybrid_div": fake})) as c:
        c.get("/api/recommend", params={"seeds": "1,2,3", "k": 5})
        assert fake.calls == [5]
        _onboard(c, UK_B)
        c.get("/api/recommend", params={"user_key": UK_B, "k": 5})
    assert fake.calls == [5, PIPE_K_MIN]


def test_last_breakdown_merged_additively_keeps_pipeline_key(tmp_path, catalog):
    staged = _Fake("hybrid_div", True)
    staged.last_breakdown = {"retrieval": 1.0, "ranking": 2.0, "rerank": 0.5}
    with TestClient(_full(tmp_path, catalog, {"hybrid_div": staged})) as c:
        _onboard(c, UK_B)
        d = c.get("/api/recommend", params={"user_key": UK_B}).json()
    keys = set(d["latency_breakdown"])
    assert {"feature", "pipeline", "retrieval", "ranking", "rerank", "compose", "total"} <= keys
    with TestClient(_full(tmp_path, catalog, {"hybrid_div": _Fake("hybrid_div", True)})) as c:
        _onboard(c, UK_B)
        plain = c.get("/api/recommend", params={"user_key": UK_B}).json()
    assert set(plain["latency_breakdown"]) == {"feature", "pipeline", "compose", "total"}


def test_recommendation_log_lives_in_rec_log_module(tmp_path, catalog, monkeypatch):
    seen: list[object] = []
    orig = rec_log.log_recommendation

    def spy(*a, **kw):
        seen.append(kw.get("user_key"))
        return orig(*a, **kw)

    monkeypatch.setattr(rec_log, "log_recommendation", spy)
    with TestClient(_full(tmp_path, catalog)) as c:
        _onboard(c, UK_A)
        c.get("/api/recommend", params={"user_key": UK_A})
        c.get("/api/recommend")
    assert seen == [UK_A, None]
    assert "INSERT INTO recommendations" not in Path(cascade_mod.__file__).read_text("utf-8")
    assert "INSERT INTO recommendations" in Path(rec_log.__file__).read_text("utf-8")


# ── Codex 수정 반영 (2026-09-06, 브리프 B) ──────────────────────────────
class _BadCatalog:
    """안쪽 카탈로그에 위임하되 지정한 단계만 터뜨린다 — level 2·3 을 따로 깨보기 위한 가짜."""

    def __init__(self, inner: CatalogKR) -> None:
        self._inner = inner
        self.fail_segment = False  # 스냅샷 카테고리 조회만 실패 → level 2 만 깨진다
        self.fail_meta = False  # meta 실패 → 두 단계의 compose 가 모두 깨진다

    def __getattr__(self, name: str) -> object:
        return getattr(self._inner, name)

    def popular(self, categories=(), n: int = 50) -> list[int]:
        if self.fail_segment and list(categories) == CATS:  # level 3·fresh_picks 는 살려둔다
            raise RuntimeError("popular boom")
        return self._inner.popular(categories, n)

    def meta(self, book_ids) -> list[dict]:
        if self.fail_meta:
            raise RuntimeError("meta boom")
        return self._inner.meta(book_ids)


def test_revoked_user_recommendation_row_is_anonymous(tmp_path, catalog):
    """F1: consent=false 응답도 기록하되 user_key·snapshot_id·cell 은 비운다(재연결 금지)."""
    with TestClient(_full(tmp_path, catalog)) as c:
        _onboard(c, UK_A)
        c.get("/api/recommend", params={"user_key": UK_A})
        assert c.delete(f"/api/users/{UK_A}/personalization").status_code == 200
        gone = c.get("/api/recommend", params={"user_key": UK_A}).json()
    con = sqlite3.connect(tmp_path / DB_FILENAME)
    linked = con.execute(
        "SELECT COUNT(*) FROM recommendations WHERE user_key = ?", (UK_A,)
    ).fetchone()[0]
    row = con.execute(
        "SELECT user_key, snapshot_id, cell, fallback_level FROM recommendations "
        "WHERE recommendation_id = ?",
        (gone["recommendation_id"],),
    ).fetchone()
    total = con.execute("SELECT COUNT(*) FROM recommendations").fetchone()[0]
    con.close()
    assert gone["fallback_level"] == 3
    assert linked == 0
    assert row == (None, None, None, 3)
    assert total == 1
    assert gone["user_key"] == UK_A and gone["cell"] == _cell(UK_A)  # 응답 에코는 그대로


def test_level2_catalog_failure_falls_through_to_level3(tmp_path, catalog):
    """F3: level 2 단계만 터져도 500 이 아니라 level 3 으로 내려간다."""
    bad = _BadCatalog(catalog)
    boom = {"hybrid": _Boom("hybrid"), "hybrid_div": _Boom("hybrid_div")}
    with TestClient(_full(tmp_path, bad, boom), raise_server_exceptions=False) as c:
        _onboard(c, UK_A)
        bad.fail_segment = True
        r = c.get("/api/recommend", params={"user_key": UK_A})
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["fallback_level"] == 3
    assert [row["row_id"] for row in d["rows"]] == ["trending", "fresh_picks"]
    assert d["rows"][0]["items"]
    assert "boom" not in r.text and "Traceback" not in r.text


def test_compose_failure_at_every_level_serves_minimal_200(tmp_path, catalog):
    """F3: level 2·3 의 compose 가 모두 터져도 카탈로그 없는 최소 200 을 낸다."""
    bad = _BadCatalog(catalog)
    boom = {"hybrid": _Boom("hybrid"), "hybrid_div": _Boom("hybrid_div")}
    with TestClient(_full(tmp_path, bad, boom), raise_server_exceptions=False) as c:
        _onboard(c, UK_A)
        bad.fail_meta = True
        r = c.get("/api/recommend", params={"user_key": UK_A})
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["fallback_level"] == 3
    assert d["model_version"] == MODEL_VERSION_FALLBACK
    assert d["items"] == [] and d["user_state_weights"] == ZERO
    assert all(row["items"] == [] for row in d["rows"])
    assert "boom" not in r.text and "Traceback" not in r.text


def test_snapshot_tie_on_created_at_resolves_to_last_inserted(tmp_path):
    """F6: created_at 이 초 단위라 동률이면 snapshot_id 사전순이 아니라 삽입 순서가 이긴다."""
    db = Database(tmp_path / "tie.db")
    db.apply_schema()
    same = _iso(1_700_000_000)
    db.execute("INSERT INTO users(user_key, consent, cell) VALUES(?,?,?)", ("tie-1", 1, "A"))
    for sid in ("snap_zzzzzz", "snap_aaaaaa"):  # 두 번째가 최신, 사전순으로는 첫 번째가 이긴다
        db.execute(
            "INSERT INTO preference_snapshots(snapshot_id, user_key, created_at) VALUES(?,?,?)",
            (sid, "tie-1", same),
        )
    assert resolve_user(db, "tie-1", None).snapshot_id == "snap_aaaaaa"


def test_feature_breakdown_includes_resolve_user_time(tmp_path, catalog, monkeypatch):
    """F7(D-09): feature = 상태·스냅샷 로드 — resolve_user 시간이 빠지면 안 된다."""
    orig = cascade_mod.resolve_user

    def slow(*a, **kw):
        time.sleep(0.02)
        return orig(*a, **kw)

    monkeypatch.setattr(cascade_mod, "resolve_user", slow)
    with TestClient(_full(tmp_path, catalog)) as c:
        _onboard(c, UK_A)
        d = c.get("/api/recommend", params={"user_key": UK_A}).json()
    assert d["fallback_level"] == 0
    assert d["latency_breakdown"]["feature"] >= 15


def test_boost_flags_reach_pipeline_through_user_context(tmp_path, catalog):
    """F4: 부스트 신호가 표시 가중치뿐 아니라 리트리버(UserState.context)에도 닿는다."""
    seen: list[dict] = []

    class _Ctx(_Fake):
        def recommend(self, user: UserState, k: int) -> list[ScoredItem]:
            seen.append(dict(user.context))
            return super().recommend(user, k)

    pipes = {"hybrid": _Ctx("hybrid"), "hybrid_div": _Ctx("hybrid_div", True)}
    app = _full(tmp_path, catalog, pipes)
    with TestClient(app) as c:
        _onboard(c, UK_A)
        c.get("/api/recommend", params={"user_key": UK_A})
        assert "session_active" not in seen[-1] and "reset_boost" not in seen[-1]
        ev = {
            "event_id": "e3",
            "user_key": UK_A,
            "book_id": 9,
            "event_type": "reader_open",
            "ts": _iso(clock["t"]),
        }
        c.post("/api/events", json=ev)
        app.state.nearline.run_once()
        c.get("/api/recommend", params={"user_key": UK_A})
        assert seen[-1].get("session_active") == "1" and "reset_boost" not in seen[-1]
        _onboard(c, UK_A, restart=True)
        after = c.get("/api/recommend", params={"user_key": UK_A}).json()
    assert seen[-1].get("reset_boost") == "1"
    assert after["user_state_weights"]["reset"] == 1.0  # 표시 가중치와 같은 신호
