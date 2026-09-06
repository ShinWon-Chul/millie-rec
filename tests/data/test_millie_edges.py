"""US-005 이웃 빌더 단위 테스트 + 적재 계획 §6 이웃 품질 게이트 3개.

게이트: ① self-edge 0 ② 전 도서 이웃 ≥5 ③ top-20 동일 카테고리 비율 ≤70%.
③ 미달이면 TF-IDF 에서 tags 를 빼고 description 가중을 올린다.
실측 수치는 results/millie_edges_gate.json 에 남긴다(숫자 정본).
"""

import importlib.util
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "tests" / "fixtures" / "millie" / "sample_records.jsonl"
REAL_BOOKS = ROOT / "data" / "processed" / "books_kr.parquet"
REAL_EDGES = ROOT / "data" / "processed" / "item_edges_kr.parquet"
GATE_JSON = ROOT / "results" / "millie_edges_gate.json"

MIN_NEIGHBOURS = 5
TOP_N = 20
MAX_SAME_CATEGORY_SHARE = 0.70
CATEGORY_BEST_WEIGHT = 0.2

FIRST_BOOK, CHATBOOK, DREAM_STORE, ALMOND = 1, 2, 11, 12  # 사전순 surrogate (픽스처)


def _load(name: str):
    """scripts/ 는 패키지가 아니므로 경로로 직접 로드한다."""
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def edges_mod():
    return _load("build_millie_edges")


@pytest.fixture(scope="module")
def books(tmp_path_factory) -> pd.DataFrame:
    out = tmp_path_factory.mktemp("processed")
    _load("build_millie_catalog").build(FIXTURE, out, raw_dir=out)
    return pd.read_parquet(out / "books_kr.parquet")


@pytest.fixture(scope="module")
def edges(edges_mod, books) -> pd.DataFrame:
    return edges_mod.build(books, edges_mod.read_best_links(FIXTURE))


def _degree(edges: pd.DataFrame) -> pd.Series:
    return edges.groupby("src_book_id").size()


def _same_category_share(edges: pd.DataFrame, books: pd.DataFrame) -> float:
    """content_sim top-20 안에서 src 와 같은 카테고리인 이웃 비율의 평균."""
    category = {
        int(b): (list(c)[0] if len(c) else None)
        for b, c in zip(books["book_id"], books["categories"], strict=True)
    }
    content = edges[edges["source"] == "content_sim"]
    shares = []
    for src, group in content.groupby("src_book_id"):
        top = group.nlargest(TOP_N, "weight")
        if top.empty or category[int(src)] is None:
            continue
        same = sum(category.get(int(d)) == category[int(src)] for d in top["dst_book_id"])
        shares.append(same / len(top))
    return sum(shares) / len(shares) if shares else 0.0


def test_edge_columns_and_sources(edges):
    assert list(edges.columns) == ["src_book_id", "dst_book_id", "weight", "source"]
    assert set(edges["source"]) <= {"content_sim", "category_best"}


def test_no_self_edge(edges):
    """게이트 ①."""
    assert (edges["src_book_id"] == edges["dst_book_id"]).sum() == 0


def test_every_book_has_at_least_five_neighbours(edges, books):
    """게이트 ②."""
    degree = _degree(edges)
    missing = sorted(set(books["book_id"].astype(int)) - set(degree.index.astype(int)))
    assert not missing, f"이웃 0인 도서: {missing}"
    thin = degree[degree < MIN_NEIGHBOURS]
    assert thin.empty, f"이웃 {MIN_NEIGHBOURS} 미만: {thin.to_dict()}"


def test_edges_reference_existing_book_ids(edges, books):
    known = set(books["book_id"].astype(int))
    assert set(edges["src_book_id"].astype(int)) <= known
    assert set(edges["dst_book_id"].astype(int)) <= known


def test_content_sim_weights_are_cosine_scores(edges):
    content = edges[edges["source"] == "content_sim"]["weight"]
    assert not content.empty
    assert content.min() >= 0.0
    assert content.max() <= 1.0


def test_category_best_uses_best_links_and_drops_unknown_targets(edges):
    """분야 BEST 1홉은 저가중 0.2, 카탈로그 밖 링크(ffff…)는 버린다."""
    pairs = {
        (int(r["src_book_id"]), int(r["dst_book_id"])): float(r["weight"])
        for r in edges[edges["source"] == "category_best"].to_dict("records")
    }
    assert pairs[(FIRST_BOOK, DREAM_STORE)] == pytest.approx(CATEGORY_BEST_WEIGHT)
    assert pairs[(FIRST_BOOK, ALMOND)] == pytest.approx(CATEGORY_BEST_WEIGHT)
    # 아몬드의 best_links 는 2개지만 하나가 카탈로그 밖(ffff…)이라 엣지는 1개다
    assert [dst for src, dst in pairs if src == ALMOND] == [FIRST_BOOK]


def test_merge_keeps_max_weight_and_its_source(edges_mod):
    stronger = edges_mod._merge({(1, 2): 0.5}, {(1, 2): CATEGORY_BEST_WEIGHT})
    assert stronger[(1, 2)] == (0.5, "content_sim")
    weaker = edges_mod._merge({(1, 2): 0.05}, {(1, 2): CATEGORY_BEST_WEIGHT})
    assert weaker[(1, 2)] == (CATEGORY_BEST_WEIGHT, "category_best")


def test_top_up_holds_the_minimum_when_top_n_is_tiny(edges_mod, books, monkeypatch):
    """top-20 이 좁아도 이웃 ≥5 는 top-20 밖 content_sim 으로 채워 유지된다."""
    monkeypatch.setattr(edges_mod, "TOP_N", 2)
    tight = edges_mod.build(books, edges_mod.read_best_links(FIXTURE))
    assert _degree(tight).min() >= MIN_NEIGHBOURS
    assert (tight["src_book_id"] == tight["dst_book_id"]).sum() == 0


def test_with_tags_variant_stays_valid(edges_mod, books):
    tagged = edges_mod.build(books, edges_mod.read_best_links(FIXTURE), with_tags=True)
    assert (tagged["src_book_id"] == tagged["dst_book_id"]).sum() == 0
    assert _degree(tagged).min() >= MIN_NEIGHBOURS


def test_synthetic_same_category_share_is_reported(edges, books):
    share = _same_category_share(edges, books)
    print(f"\n[합성 12권] top-20 동일 카테고리 비율 {share:.3f}")
    assert 0.0 <= share <= 1.0


# ── 게이트 (실제 수집 산출물) ────────────────────────────────────────────────
def test_neighbour_quality_gate():
    """계획 §6 이웃 품질 게이트 3개를 실제 카탈로그에 적용한다."""
    if not REAL_BOOKS.exists() or not REAL_EDGES.exists():
        pytest.skip(
            "실제 수집 산출물이 없다 — 게이트는 야간 배치 + build_millie_edges.py 후에만 돈다 "
            f"(필요: {REAL_BOOKS.relative_to(ROOT)}, {REAL_EDGES.relative_to(ROOT)})"
        )
    real_books = pd.read_parquet(REAL_BOOKS)
    real_edges = pd.read_parquet(REAL_EDGES)
    known = set(real_books["book_id"].astype(int))
    degree = _degree(real_edges)
    share = _same_category_share(real_edges, real_books)
    print(f"\ntop-20 동일 카테고리 비율 평균 {share:.3f} (기준 ≤{MAX_SAME_CATEGORY_SHARE})")
    orphans = sorted(known - set(degree.index.astype(int)))

    # 단언보다 먼저 기록한다 — 게이트 미달이어도 수치가 남아야 D-10 보고가 가능하다
    GATE_JSON.parent.mkdir(parents=True, exist_ok=True)
    GATE_JSON.write_text(
        json.dumps(
            {
                "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
                "n_books": len(known),
                "n_edges": int(len(real_edges)),
                "sources": {
                    k: int(v) for k, v in real_edges["source"].value_counts().to_dict().items()
                },
                "self_edges": int((real_edges["src_book_id"] == real_edges["dst_book_id"]).sum()),
                "min_degree": int(degree.min()) if len(degree) else 0,
                "n_orphans": len(orphans),
                "same_category_share": round(float(share), 4),
                "max_same_category_share": MAX_SAME_CATEGORY_SHARE,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    assert (real_edges["src_book_id"] == real_edges["dst_book_id"]).sum() == 0
    assert set(real_edges["dst_book_id"].astype(int)) <= known
    assert set(real_edges["src_book_id"].astype(int)) <= known
    assert not orphans, f"이웃 0인 도서 {len(orphans)}권: {orphans[:10]}"
    thin = degree[degree < MIN_NEIGHBOURS]
    assert thin.empty, f"이웃 {MIN_NEIGHBOURS} 미만 {len(thin)}권: {thin.head(10).to_dict()}"
    assert share <= MAX_SAME_CATEGORY_SHARE, (
        f"동일 카테고리 {share:.3f} — TF-IDF 에서 tags 제거·description 가중 상향 필요"
    )
