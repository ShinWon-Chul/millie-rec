"""app/cli.py — 합성 parquet e2e(make eval 의 파일 계약) · data 서브커맨드 호출 순서 ·
미등록 variant 종료. 네트워크·실데이터 0.
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from millie_rec.app.cli import main
from millie_rec.contracts import (
    COL_EVENT,
    COL_ITEM,
    COL_RATING,
    COL_TS,
    COL_USER,
    SEED,
    VARIANTS,
)
from millie_rec.data import BOOKS_FILE, INTERACTIONS_FILE
from millie_rec.evaluation import LATEST_COLUMNS, LATEST_FILE, STATES_FILE

N_USERS, N_ITEMS, N_PER_USER = 30, 40, 15
TAGS = ("fantasy magic", "history war", "romance drama", "science space")


def _write_processed(proc: Path) -> None:
    """유저 30 × 아이템 40 중 15권, 전부 긍정(rating>=4), ts 없음 → holdout."""
    proc.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(SEED)
    users, items = [], []
    for user in range(1, N_USERS + 1):
        chosen = rng.choice(N_ITEMS, size=N_PER_USER, replace=False) + 1
        users += [user] * N_PER_USER
        items += [int(i) for i in chosen]
    n = len(users)
    pd.DataFrame(
        {
            COL_USER: users,
            COL_ITEM: items,
            COL_TS: pd.Series([None] * n, dtype="object"),
            COL_EVENT: "rating",
            COL_RATING: rng.choice([4.0, 5.0], size=n),
        }
    ).to_parquet(proc / INTERACTIONS_FILE, index=False)
    pd.DataFrame(
        {
            COL_ITEM: list(range(1, N_ITEMS + 1)),
            "title": [f"B{i}" for i in range(1, N_ITEMS + 1)],
            "authors": "A",
            "image_url": "",
            "average_rating": 4.0,
            "ratings_count": 10,
            "original_publication_year": 2000,
            "categories": [[] for _ in range(N_ITEMS)],
            "subcategories": [[] for _ in range(N_ITEMS)],
            "tags": [TAGS[i % len(TAGS)] for i in range(N_ITEMS)],
        }
    ).to_parquet(proc / BOOKS_FILE, index=False)


def test_eval_end_to_end_on_synthetic_parquet(tmp_path):
    proc, out, art = tmp_path / "processed", tmp_path / "results", tmp_path / "artifacts"
    _write_processed(proc)
    main(
        ["eval", "--variant", "all", "--processed", str(proc), "--out", str(out)]
        + ["--artifacts", str(art)]
    )
    assert (out / LATEST_FILE).exists()
    lines = (out / LATEST_FILE).read_text(encoding="utf-8").splitlines()
    assert lines[0] == ",".join(LATEST_COLUMNS)
    assert lines[1].startswith("pop,") and lines[1].endswith(",30,holdout,pop_v1")
    assert 0.0 < float(lines[1].split(",")[1]) <= 1.0
    assert len(lines) == 5 and [ln.split(",")[0] for ln in lines[1:]] == list(VARIANTS)
    assert lines[3].startswith("hybrid,") and lines[3].endswith(",30,holdout,hybrid_v1")

    states = (out / STATES_FILE).read_text(encoding="utf-8").splitlines()
    assert len(states) == 9  # 헤더 + 4 variant × 2 상태
    assert states[1].startswith("pop,n0,") and states[1].endswith(",30")
    assert states[2] == "pop,n20,0.000,0.000,0.000,0"
    assert [s.split(",")[0] for s in states[1:]] == [
        "pop", "pop", "cf", "cf", "hybrid", "hybrid", "hybrid_div", "hybrid_div",
    ]  # fmt: skip

    jsons = sorted(out.glob("eval_*.json"))
    assert len(jsons) == 1
    d = json.loads(jsons[0].read_text(encoding="utf-8"))
    assert d["split_mode"] == "holdout" and d["n_users"] == {"n0": 30, "n20": 0}
    assert d["n_excluded"] == 0 and d["k_history"] == 20 and d["test_frac"] == 0.2
    assert d["min_user_interactions"] == 5 and "git_sha" in d

    table = json.loads((art / "serving" / "eval_table.json").read_text(encoding="utf-8"))
    assert table["rows"][0]["variant"] == "pop"
    assert table["meta"]["n_users"] == 30 and table["meta"]["split_mode"] == "holdout"
    assert set(table["meta"]) >= {"dataset", "split_mode", "n_users", "k_recall"}
    assert set(table["meta"]) >= {"k_rank", "seed", "git_sha", "created_at"}
    assert "states" not in table

    pop = json.loads((art / "popularity.json").read_text(encoding="utf-8"))
    assert pop["name"] == "pop" and pop["items"]
    assert (art / "item_neighbors.npz").exists()  # knn 캐시가 --artifacts 아래에 생긴다


def test_eval_unknown_variant_name_is_rejected_by_argparse(tmp_path):
    proc, out, art = tmp_path / "processed", tmp_path / "results", tmp_path / "artifacts"
    _write_processed(proc)
    with pytest.raises(SystemExit):
        main(
            ["eval", "--variant", "nope", "--processed", str(proc), "--out", str(out)]
            + ["--artifacts", str(art)]
        )


def test_data_calls_download_then_build(monkeypatch, tmp_path):
    calls: list[str] = []
    raw, proc = tmp_path / "raw", tmp_path / "p"

    def _download(raw_dir):
        calls.append("download")
        assert raw_dir == raw
        return [raw / "ratings.csv"]

    def _build(raw_dir, out_dir):
        calls.append("build")
        assert raw_dir == raw and out_dir == proc
        return proc / INTERACTIONS_FILE, proc / BOOKS_FILE

    monkeypatch.setattr("millie_rec.app.cli.download_goodbooks", _download)
    monkeypatch.setattr("millie_rec.app.cli.build_goodbooks", _build)
    main(["data", "--raw", str(raw), "--processed", str(proc)])
    assert calls == ["download", "build"]
