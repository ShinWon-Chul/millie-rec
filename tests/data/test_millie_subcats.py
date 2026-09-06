"""3depth 세부 카테고리 파서·빌더·패치 — 합성 데이터만(네트워크·실데이터 없음)."""

import json
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import build_millie_subcats as bld  # noqa: E402
from millie_subcat_parse import (  # noqa: E402
    CATEGORY_SEQ2,
    UA,
    extract_book_ids,
    parse_depth3_links,
)

A = "a" * 16
B = "b" * 16
C = "c" * 16
Z = "f" * 16  # 카탈로그에 없는 id


def test_parse_depth3_links_skips_op_and_foreign_parent_and_dedups():
    anchors = [
        ("/v3/search/3depth/?parentSeq=1223&op=total&nav_hidden=y", "소설 전체보기"),
        ("/v3/search/3depth/?parentSeq=1223&op=best&nav_hidden=y", "소설 인기 도서"),
        ("/v3/search/3depth/1225/?parentSeq=1223&nav_hidden=y", "추리/스릴러"),
        ("/v3/search/3depth/1226/?parentSeq=1223&nav_hidden=y", " SF "),
        ("/v3/search/3depth/1225/?parentSeq=1223&nav_hidden=y", "추리/스릴러"),
        ("/v3/search/3depth/9999/?parentSeq=1240&nav_hidden=y", "인문 것"),
        ("/v3/search/2depth/1223?nav_hidden=y", "소설"),
        ("", "빈 링크"),
    ]
    assert parse_depth3_links(anchors, "1223") == [("1225", "추리/스릴러"), ("1226", "SF")]


def test_extract_book_ids_ordered_dedupe():
    hrefs = [f"/v4/book/{A}", "/v4/library/12", f"/v4/book/{B}?x=1", f"/v4/book/{A}", "bad"]
    assert extract_book_ids(hrefs) == [A, B]


def test_constants():
    assert len(CATEGORY_SEQ2) == 29 and CATEGORY_SEQ2["소설"] == "1223"
    assert UA.startswith("millie-rec-demo-assignment/")


@pytest.fixture
def env(tmp_path: Path) -> dict:
    rows = [
        {"category": "소설", "depth2_seq": "1223", "depth3_seq": "1225",
         "subcategory": "추리/스릴러", "millie_ids": [A, B, Z], "n": 3, "status": "ok"},
        {"category": "소설", "depth2_seq": "1223", "depth3_seq": "1226", "subcategory": "SF",
         "millie_ids": [B], "n": 1, "status": "ok"},
        {"category": "IT", "depth2_seq": "2068", "depth3_seq": "3000", "subcategory": "실패건",
         "millie_ids": [], "n": 0, "status": "fail"},
    ]  # fmt: skip
    jsonl = tmp_path / "s.jsonl"
    jsonl.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
    idmap = tmp_path / "id_map.csv"
    idmap.write_text(f"millie_id,book_id,first_seen_at\n{A},1,t\n{B},2,t\n{C},3,t\n")
    books = pd.DataFrame(
        {"book_id": [1, 2, 3], "millie_id": [A, B, C], "title": ["a", "b", "c"],
         "categories": [["소설"], ["소설"], ["IT"]], "subcategories": [[], [], []]}
    )  # fmt: skip
    pq = tmp_path / "books_kr.parquet"
    books.to_parquet(pq, index=False)
    serving = tmp_path / "serving"
    serving.mkdir()
    payload = [{"book_id": i, "title": t, "subcategories": [], "x": {"k": [i]}} for i, t in
               ((1, "a"), (2, "b"), (3, "c"))]  # fmt: skip
    (serving / "books_kr.json").write_text(json.dumps(payload, ensure_ascii=False))
    return {"jsonl": jsonl, "idmap": idmap, "pq": pq, "serving": serving, "tmp": tmp_path}


def test_build_and_patch(env):
    rep = bld.run(env["jsonl"], env["idmap"], env["pq"], env["tmp"] / "out", env["tmp"] / "res",
                  env["serving"], dry_run=False)  # fmt: skip
    assert rep["n_subcats"] == 2 and rep["n_dropped_unknown"] == 1
    t = pd.read_parquet(env["tmp"] / "out" / "subcategories_kr.parquet")
    assert list(t.columns) == bld.COLS and len(t) == 3
    assert t.loc[t.book_id == 1, "rank"].tolist() == [1]
    meta = json.loads((env["tmp"] / "res" / "subcat_meta.json").read_text())
    assert meta == {"IT": [], "소설": ["추리/스릴러", "SF"]}
    cov = pd.read_csv(env["tmp"] / "res" / "subcat_coverage.csv")
    assert list(cov.columns) == bld.COV_COLS and cov.iloc[-1]["category"] == "ALL"
    assert cov.set_index("category").loc["소설", "share_books_with_subcat"] == 1.0
    assert cov.set_index("category").loc["IT", "n_catalog_books"] == 1
    pq = pd.read_parquet(env["pq"])
    assert [list(v) for v in pq["subcategories"]] == [["추리/스릴러"], ["SF", "추리/스릴러"], []]
    js = json.loads((env["serving"] / "books_kr.json").read_text())
    assert [r["subcategories"] for r in js] == [["추리/스릴러"], ["SF", "추리/스릴러"], []]
    assert [r["x"] for r in js] == [{"k": [1]}, {"k": [2]}, {"k": [3]}]  # 다른 키 무변경
    assert rep["patched_parquet"] == 2 and rep["patched_json"] == 2


def test_dry_run_leaves_targets_untouched(env):
    before = (env["serving"] / "books_kr.json").read_bytes()
    rep = bld.run(env["jsonl"], env["idmap"], env["pq"], env["tmp"] / "out", env["tmp"] / "res",
                  env["serving"], dry_run=True)  # fmt: skip
    assert rep["patched_json"] is None and (env["serving"] / "books_kr.json").read_bytes() == before
    assert [list(v) for v in pd.read_parquet(env["pq"])["subcategories"]] == [[], [], []]


def test_patch_is_idempotent(env):
    args = (env["jsonl"], env["idmap"], env["pq"], env["tmp"] / "out", env["tmp"] / "res",
            env["serving"])  # fmt: skip
    bld.run(*args, dry_run=False)
    once = (env["serving"] / "books_kr.json").read_bytes()
    bld.run(*args, dry_run=False)
    assert (env["serving"] / "books_kr.json").read_bytes() == once
