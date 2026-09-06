"""results/ writer — latest.csv(n=0 비교표) · latest_states.csv(n0|n20) · eval_<ts>.json.

PDF 숫자는 여기서만.
"""

import json
import subprocess
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from millie_rec.contracts import DIR_RESULTS, K_RANK, K_RECALL, ROOT, SEED, VARIANTS, EvalResult

DATASET = "goodbooks-10k"  # evaluation.md 트랙 분리 — 결과 json 에 데이터셋 이름 기록
LATEST_FILE = "latest.csv"
STATES_FILE = "latest_states.csv"
COL_RECALL = f"recall@{K_RECALL}"  # → "recall@20"
COL_NDCG = f"ndcg@{K_RANK}"  # → "ndcg@10"
COL_ILD = f"ild@{K_RANK}"  # → "ild@10"
LATEST_COLUMNS = (
    "variant",
    COL_RECALL,
    COL_NDCG,
    COL_ILD,
    "n_users",
    "split_mode",
    "model_version",
)  # D-06
STATES_COLUMNS = ("variant", "state", COL_RECALL, COL_NDCG, COL_ILD, "n_users")  # D-07
FLOAT_FORMAT = "%.3f"  # evaluation.md 소수 3자리


@dataclass(frozen=True, slots=True)
class RunMeta:
    """실행 수준 메타(D-08). EvalResult 에 없는 것만 — 계약은 바꾸지 않는다."""

    split_mode: str
    test_frac: float
    n_excluded: int
    n_onboard_seeds: int
    k_history: int
    min_user_interactions: int
    min_item_interactions: int
    elapsed_s: float
    dataset: str = DATASET
    seed: int = SEED
    git_sha: str | None = None


def git_sha() -> str | None:
    """짧은 sha. git 이 없거나 실패하면 None — 절대 예외를 내지 않는다."""
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
            cwd=ROOT,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout.strip() or None if out.returncode == 0 else None


def _row(r: EvalResult, split_mode: str) -> dict:
    return {
        "variant": r.variant,
        COL_RECALL: r.recall,
        COL_NDCG: r.ndcg,
        COL_ILD: r.ild,
        "n_users": r.n_users,
        "split_mode": split_mode,
        "model_version": r.model_version,
    }


def _order(variant: str) -> int:
    if variant not in VARIANTS:
        raise ValueError(f"unknown variant {variant!r}; allowed {VARIANTS}")
    return VARIANTS.index(variant)


def write_results(
    rows: Sequence[EvalResult],
    states: Sequence[tuple[str, EvalResult]],
    meta: RunMeta,
    out_dir: Path = DIR_RESULTS,
) -> Path:
    """세 파일을 쓰고 json 경로를 돌려준다. 손으로 편집하지 않는다(evaluation.md)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = sorted(rows, key=lambda r: _order(r.variant))
    states = sorted(states, key=lambda s: (_order(s[1].variant), s[0]))
    pd.DataFrame([_row(r, meta.split_mode) for r in rows], columns=list(LATEST_COLUMNS)).to_csv(
        out_dir / LATEST_FILE, index=False, float_format=FLOAT_FORMAT
    )
    pd.DataFrame(
        [{**_row(r, meta.split_mode), "state": s} for s, r in states],
        columns=list(STATES_COLUMNS),
    ).to_csv(out_dir / STATES_FILE, index=False, float_format=FLOAT_FORMAT)
    now = datetime.now(UTC)
    n_users: dict[str, int] = {}
    for s, r in states:
        n_users.setdefault(s, r.n_users)
    payload = {
        **asdict(meta),
        "n_users": n_users,
        "k_recall": K_RECALL,
        "k_rank": K_RANK,
        "created_at": now.isoformat(timespec="seconds"),
        "rows": [{**asdict(r), "split_mode": meta.split_mode} for r in rows],
        "states": [{"state": s, **asdict(r)} for s, r in states],
    }
    path = out_dir / f"eval_{now.strftime('%Y%m%d_%H%M')}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
