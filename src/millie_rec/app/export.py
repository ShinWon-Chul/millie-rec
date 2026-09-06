"""artifacts/serving/ export — app 소유(architecture.md 산출물 표).

Phase 2 는 eval_table.json 만(D-09).
"""

import csv
import json
from datetime import UTC, datetime
from pathlib import Path

from millie_rec.contracts import DIR_ARTIFACTS, K_RANK, K_RECALL
from millie_rec.evaluation import LATEST_FILE, RunMeta

EVAL_TABLE = "eval_table.json"  # Phase 5 GET /api/showcase 입력(D-09)
SERVING_SUBDIR = "serving"
DIR_SERVING = DIR_ARTIFACTS / SERVING_SUBDIR  # Dockerfile COPY 대상, 커밋 대상


def write_eval_table(
    results_dir: Path, meta: RunMeta, n_users: int, serving_dir: Path = DIR_SERVING
) -> Path:
    """latest.csv 행을 그대로 복사(재계산 없음). n>=k 표는 넣지 않는다 — PDF P3 전용(D-09)."""
    with (results_dir / LATEST_FILE).open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    payload = {
        "rows": rows,
        "meta": {
            "dataset": meta.dataset,
            "split_mode": meta.split_mode,
            "n_users": n_users,
            "k_recall": K_RECALL,
            "k_rank": K_RANK,
            "seed": meta.seed,
            "git_sha": meta.git_sha,
            "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
        },
    }
    serving_dir.mkdir(parents=True, exist_ok=True)
    out = serving_dir / EVAL_TABLE
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return out
