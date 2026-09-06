"""results writer — 계약(파일 이름·헤더 문자 단위) · 정확성(3자리·VARIANTS 정렬·json 키).

안전성: git_sha None 경로.
"""

import json
import re
import subprocess

import pytest

from millie_rec.contracts import EvalResult
from millie_rec.evaluation.report import RunMeta, git_sha, write_results

JSON_NAME = re.compile(r"^eval_\d{8}_\d{4}\.json$")
LATEST_HEADER = "variant,recall@20,ndcg@10,ild@10,n_users,split_mode,model_version"
STATES_HEADER = "variant,state,recall@20,ndcg@10,ild@10,n_users"
META_KEYS = {
    "dataset",
    "split_mode",
    "test_frac",
    "seed",
    "n_users",
    "n_excluded",
    "k_recall",
    "k_rank",
    "n_onboard_seeds",
    "k_history",
    "min_user_interactions",
    "min_item_interactions",
    "git_sha",
    "elapsed_s",
    "created_at",
    "rows",
    "states",
}


def _r(variant: str = "pop", n_users: int = 2) -> EvalResult:
    return EvalResult(
        variant, 0.1, 0.2, 0.3, n_users, 20, 10, 42, f"{variant}_v1", "2026-01-01T00:00:00+00:00"
    )


def _meta() -> RunMeta:
    return RunMeta(
        split_mode="holdout",
        test_frac=0.2,
        n_excluded=7,
        n_onboard_seeds=5,
        k_history=20,
        min_user_interactions=5,
        min_item_interactions=5,
        elapsed_s=1.5,
        git_sha="abc1234",
    )


# ── 계약 ──
def test_write_results_file_names_and_headers(tmp_path) -> None:
    r = _r()
    path = write_results([r], [("n0", r), ("n20", _r(n_users=1))], _meta(), out_dir=tmp_path)
    assert JSON_NAME.match(path.name) is not None, path.name
    assert path.parent == tmp_path
    latest = (tmp_path / "latest.csv").read_text(encoding="utf-8").splitlines()
    states = (tmp_path / "latest_states.csv").read_text(encoding="utf-8").splitlines()
    assert latest[:1] == [LATEST_HEADER]
    assert states[:1] == [STATES_HEADER]


# ── 정확성 ──
def test_latest_csv_rows_three_decimals_and_states_rows(tmp_path) -> None:
    r = _r()
    write_results([r], [("n0", r), ("n20", _r(n_users=1))], _meta(), out_dir=tmp_path)
    assert (tmp_path / "latest.csv").read_text(encoding="utf-8").splitlines() == [
        LATEST_HEADER,
        "pop,0.100,0.200,0.300,2,holdout,pop_v1",
    ]
    assert (tmp_path / "latest_states.csv").read_text(encoding="utf-8").splitlines() == [
        STATES_HEADER,
        "pop,n0,0.100,0.200,0.300,2",
        "pop,n20,0.100,0.200,0.300,1",
    ]


def test_json_has_run_meta_keys_and_state_n_users(tmp_path) -> None:
    r = _r()
    path = write_results([r], [("n0", r), ("n20", _r(n_users=1))], _meta(), out_dir=tmp_path)
    d = json.loads(path.read_text(encoding="utf-8"))
    assert set(d) >= META_KEYS
    assert d["dataset"] == "goodbooks-10k"
    assert d["split_mode"] == "holdout"
    assert d["seed"] == 42
    assert d["n_users"] == {"n0": 2, "n20": 1}
    assert d["k_recall"] == 20
    assert d["k_rank"] == 10
    assert d["git_sha"] == "abc1234"
    assert len(d["rows"]) == 1
    assert d["rows"][0]["variant"] == "pop"
    assert d["rows"][0]["split_mode"] == "holdout"
    assert len(d["states"]) == 2
    assert d["states"][1]["state"] == "n20"


def test_rows_sorted_by_variants_order_and_unknown_variant_rejected(tmp_path) -> None:
    rows = [_r("cf"), _r("pop")]
    write_results(rows, [("n0", rows[1])], _meta(), out_dir=tmp_path)
    lines = (tmp_path / "latest.csv").read_text(encoding="utf-8").splitlines()
    assert [line.split(",")[0] for line in lines[1:]] == ["pop", "cf"]
    with pytest.raises(ValueError):
        write_results([_r("zzz")], [], _meta(), out_dir=tmp_path)


# ── 안전성 ──
def test_git_sha_returns_none_on_failure(monkeypatch) -> None:
    def boom(*args, **kwargs):
        raise FileNotFoundError("git not found")

    monkeypatch.setattr(subprocess, "run", boom)
    assert git_sha() is None
    monkeypatch.setattr(
        subprocess, "run", lambda *a, **k: subprocess.CompletedProcess([], 1, "", "")
    )
    assert git_sha() is None
    monkeypatch.setattr(
        subprocess, "run", lambda *a, **k: subprocess.CompletedProcess([], 0, "abc1234\n", "")
    )
    assert git_sha() == "abc1234"
