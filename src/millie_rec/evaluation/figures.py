"""EVAL-07 비교 막대그래프 — results/latest.csv → report/figures/eval_bar.png. PDF 그림 ③."""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # 헤드리스 — 서버·CI 에 디스플레이가 없다. pyplot import 보다 먼저
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from millie_rec.contracts import DIR_FIGURES, DIR_RESULTS  # noqa: E402
from millie_rec.evaluation.report import (  # noqa: E402
    COL_ILD,
    COL_NDCG,
    COL_RECALL,
    LATEST_FILE,
)

FIGURE_NAME = "eval_bar.png"
METRICS = (COL_RECALL, COL_NDCG, COL_ILD)
FIGSIZE = (7.0, 3.2)  # PDF 한 단 폭
DPI = 200


def plot_eval_bar(
    latest_csv: Path = DIR_RESULTS / LATEST_FILE, out: Path = DIR_FIGURES / FIGURE_NAME
) -> Path:
    """variant 별 3지표 묶음 막대. 숫자는 latest.csv 그대로(재계산 없음)."""
    df = pd.read_csv(latest_csv)
    fig, ax = plt.subplots(figsize=FIGSIZE)
    df.set_index("variant")[list(METRICS)].plot.bar(ax=ax, rot=0, width=0.8)
    ax.set_ylim(0, 1)
    ax.set_ylabel("score")
    ax.set_title(
        f"Track A (Goodbooks-10k, {df['split_mode'].iloc[0]}, n_users={int(df['n_users'].iloc[0])})"
    )
    ax.legend(loc="upper right", frameon=False)
    for c in ax.containers:
        ax.bar_label(c, fmt="%.3f", fontsize=7)
    fig.tight_layout()
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=DPI)
    plt.close(fig)
    return out
