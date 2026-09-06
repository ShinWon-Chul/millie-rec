"""EVAL-07 비교 막대그래프 — 계약(경로 반환·PNG 시그니처) · 안전성(1행)."""

from pathlib import Path

from millie_rec.evaluation.figures import plot_eval_bar

HEADER = "variant,recall@20,ndcg@10,ild@10,n_users,split_mode,model_version\n"
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def _csv(tmp_path: Path, *rows: str) -> Path:
    path = tmp_path / "latest.csv"
    path.write_text(HEADER + "".join(r + "\n" for r in rows), encoding="utf-8")
    return path


def test_plot_eval_bar_writes_png_from_latest_csv(tmp_path: Path) -> None:
    latest = _csv(
        tmp_path,
        "pop,0.100,0.200,0.300,2,holdout,pop_v1",
        "cf,0.150,0.250,0.350,2,holdout,cf_v1",
    )
    out = tmp_path / "eval_bar.png"

    got = plot_eval_bar(latest, out)

    assert got == out
    assert out.exists()
    assert out.stat().st_size > 1000
    assert out.read_bytes()[:8] == PNG_MAGIC


def test_plot_eval_bar_handles_single_row(tmp_path: Path) -> None:
    latest = _csv(tmp_path, "pop,0.063,0.054,0.764,2000,holdout,pop_v1")
    out = tmp_path / "nested" / "eval_bar.png"

    got = plot_eval_bar(latest, out)

    assert got == out
    assert out.exists()
    assert out.read_bytes()[:8] == PNG_MAGIC
