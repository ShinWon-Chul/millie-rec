"""app/export.py — artifacts/serving/eval_table.json 이 latest.csv 행을 그대로 복사한다(D-09)."""

import json

from millie_rec.app.export import write_eval_table
from millie_rec.evaluation import LATEST_COLUMNS, LATEST_FILE, RunMeta

META_KEYS = {
    "dataset",
    "split_mode",
    "n_users",
    "k_recall",
    "k_rank",
    "seed",
    "git_sha",
    "created_at",
}


def test_write_eval_table_copies_latest_rows_and_meta_without_states(tmp_path):
    results_dir = tmp_path / "results"
    results_dir.mkdir()
    (results_dir / LATEST_FILE).write_text(
        ",".join(LATEST_COLUMNS) + "\npop,0.100,0.200,0.300,2,holdout,pop_v1\n",
        encoding="utf-8",
    )
    meta = RunMeta(
        split_mode="holdout",
        test_frac=0.2,
        n_excluded=0,
        n_onboard_seeds=5,
        k_history=20,
        min_user_interactions=5,
        min_item_interactions=5,
        elapsed_s=0.0,
        git_sha="abc1234",
    )
    out = write_eval_table(results_dir, meta, 2, serving_dir=tmp_path / "serving")
    assert out.exists()
    d = json.loads(out.read_text(encoding="utf-8"))
    assert set(d) == {"rows", "meta"}
    assert d["rows"] == [
        {
            "variant": "pop",
            "recall@20": "0.100",
            "ndcg@10": "0.200",
            "ild@10": "0.300",
            "n_users": "2",
            "split_mode": "holdout",
            "model_version": "pop_v1",
        }
    ]
    assert set(d["meta"]) == META_KEYS
    assert d["meta"]["n_users"] == 2
    assert d["meta"]["split_mode"] == "holdout" and d["meta"]["git_sha"] == "abc1234"
