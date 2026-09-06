"""bench 순수 함수(percentile·summarize)·인자 파서·서버 부재 안내 — 네트워크 호출 없음 (D-11)."""

import json
from pathlib import Path

import pytest

from millie_rec.contracts import DIR_RESULTS
from millie_rec.serving import bench
from millie_rec.serving.bench import SERVE_HINT, build_parser, main, percentile, summarize

RECORDS = [
    (10.0, 0, "hybrid_div_v1"),
    (20.0, 0, "hybrid_v1"),
    (30.0, 1, "hybrid_div_v1"),
    (40.0, 3, "fallback_v1"),
]
SUMMARY_KEYS = {
    "p50",
    "p95",
    "p99",
    "n",
    "warmup",
    "users",
    "k",
    "seed",
    "fallback_levels",
    "variants",
    "catalog",
    "created_at",
    "git_sha",
    "base_url",
}


def _summary(records=RECORDS) -> dict:
    return summarize(
        records,
        n_users=2,
        warmup=0,
        k=40,
        base_url="http://x",
        n_books=20,
        created_at="2026-09-07T00:00:00Z",
        git_sha="abc1234",
    )


# ── 계약 ────────────────────────────────────────────────────────────────────
def test_percentile_index_rule_hand_computed():
    four = [1.0, 2.0, 3.0, 4.0]
    assert percentile(four, 50) == 2.0
    assert percentile(four, 95) == 4.0
    assert percentile(four, 99) == 4.0
    assert percentile([5.0], 50) == 5.0
    ten = [float(x) for x in range(10, 101, 10)]
    assert percentile(ten, 90) == 90.0
    assert percentile([], 95) == 0.0


def test_summarize_keys_distributions_and_percentiles():
    out = _summary()
    assert set(out) == SUMMARY_KEYS
    assert out["n"] == 4 and out["users"] == 2 and out["k"] == 40 and out["warmup"] == 0
    assert out["p50"] == 20.0 and out["p95"] == 40.0 and out["p99"] == 40.0
    assert out["fallback_levels"] == {"0": 2, "1": 1, "2": 0, "3": 1}
    assert out["variants"] == {"hybrid_div_v1": 2, "hybrid_v1": 1, "fallback_v1": 1}
    assert out["catalog"] == {"n_books": 20}
    assert out["seed"] == 42
    assert out["base_url"] == "http://x" and out["git_sha"] == "abc1234"
    assert out["created_at"] == "2026-09-07T00:00:00Z"


def test_summarize_empty_records_is_safe_zero():
    out = _summary(records=[])
    assert set(out) == SUMMARY_KEYS
    assert out["n"] == 0
    assert out["p50"] == out["p95"] == out["p99"] == 0.0
    assert out["fallback_levels"] == {"0": 0, "1": 0, "2": 0, "3": 0}
    assert out["variants"] == {}


# ── 정확성 ──────────────────────────────────────────────────────────────────
def test_summarize_output_has_no_user_key():
    dumped = json.dumps(_summary(), ensure_ascii=False)
    assert "user_key" not in dumped
    assert set(json.loads(dumped)) == SUMMARY_KEYS


def test_parser_defaults_match_d11_and_help_exits_zero(capsys):
    args = build_parser().parse_args([])
    assert args.base == "http://localhost:8000"
    assert (args.users, args.warmup, args.n, args.k) == (50, 50, 500, 40)
    assert args.out == DIR_RESULTS / "latency.json"
    assert args.seed == 42 and args.n_books is None
    assert build_parser().parse_args(["--n-books", "9447"]).n_books == 9447
    with pytest.raises(SystemExit) as help_exit:
        main(["--help"])
    assert help_exit.value.code == 0
    with pytest.raises(SystemExit) as bad_exit:
        main(["--n", "abc"])
    assert bad_exit.value.code == 2


# ── 안전성 ──────────────────────────────────────────────────────────────────
def test_run_exits_1_with_hint_when_server_down(tmp_path: Path, capsys):
    with pytest.raises(SystemExit) as exit_info:
        bench.run(
            "http://127.0.0.1:1",
            n_users=1,
            warmup=0,
            n_requests=1,
            k=1,
            out=tmp_path / "latency.json",
            seed=1,
        )
    assert exit_info.value.code == 1
    assert SERVE_HINT in capsys.readouterr().out
    assert not (tmp_path / "latency.json").exists()


def test_bench_uses_urllib_not_httpx_source_grep():
    src = Path(bench.__file__).read_text(encoding="utf-8")
    assert "import httpx" not in src and "httpx" not in src
    assert "urllib.request" in src
    assert "localhost" in bench.BASE_URL
    assert 'DIR_RESULTS / "latency.json"' in src
