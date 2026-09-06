"""CLI 진입점 — argparse 하나(simplicity.md).

data: Goodbooks 다운로드 → parquet · eval: 등록 variant × 두 상태 → results/ +
eval_table.json (아키텍처 01 §3-6) · demo: 본인 5권 앵커(stdout, demo_cli).
"""

import argparse
import logging
from pathlib import Path
from time import perf_counter

from millie_rec.app.demo_cli import add_demo_parser
from millie_rec.app.export import SERVING_SUBDIR, write_eval_table
from millie_rec.app.pipeline import fit_pipelines
from millie_rec.contracts import (
    DIR_ARTIFACTS,
    DIR_PROCESSED,
    DIR_RAW,
    DIR_RESULTS,
    K_RANK,
    K_RECALL,
    N_ONBOARD_SEEDS,
    VARIANTS,
)
from millie_rec.data import (
    BOOKS_FILE,
    INTERACTIONS_FILE,
    K_HISTORY,
    MIN_ITEM_INTERACTIONS,
    MIN_USER_INTERACTIONS,
    RAW_SUBDIR,
    STATE_N0,
    STATE_NK,
    TEST_FRAC,
    build_goodbooks,
    download_goodbooks,
    filter_min_interactions,
    load_books,
    load_interactions,
    mask_onboarding,
    relevant_sets,
    select_test_users,
    split,
)
from millie_rec.evaluation import RunMeta, evaluate, git_sha, write_results
from millie_rec.ranking import state_weights
from millie_rec.retrieval import KNN_ARTIFACT, POP_ARTIFACT, ContentVectors

log = logging.getLogger(__name__)
ALL = "all"


def cmd_data(args: argparse.Namespace) -> None:
    """유일한 네트워크 진입점(make data). 멱등."""
    raw = download_goodbooks(args.raw)
    ip, bp = build_goodbooks(args.raw, args.processed)
    print(f"raw={len(raw)} files @ {args.raw} → {ip.name} · {bp.name} @ {args.processed}")


def cmd_eval(args: argparse.Namespace) -> None:
    """load → filter → split → 표본 → 두 상태 → 등록 variant 평가 → results/ → 아티팩트."""
    t0 = perf_counter()
    inter = filter_min_interactions(load_interactions(args.processed / INTERACTIONS_FILE))
    books = load_books(args.processed / BOOKS_FILE)
    sp = split(inter)
    users, n_excluded = select_test_users(sp.train, sp.test)
    states = mask_onboarding(sp.train, users)
    rel = relevant_sets(sp.test)
    n0 = [(u, rel[u.user_id]) for u in states.n0]
    nk = [(u, rel[u.user_id]) for u in states.n_k]
    vectors = ContentVectors(
        books, weights=state_weights
    )  # content 채널 성분 가중 + ILD 벡터(같은 객체)
    pipes = fit_pipelines(
        sp.train, vectors, knn_artifact=args.artifacts / KNN_ARTIFACT.name, weights=state_weights
    )
    wanted = list(pipes) if args.variant == ALL else [args.variant]
    missing = [v for v in wanted if v not in pipes]
    if missing:
        raise SystemExit(f"variant {missing} 미등록 — 등록: {list(pipes)}")
    rows, state_rows = [], []
    for name in VARIANTS:
        if name not in wanted:
            continue
        r0 = evaluate(pipes[name], n0, vectors)
        rk = evaluate(pipes[name], nk, vectors)
        rows.append(r0)
        state_rows += [(STATE_N0, r0), (STATE_NK, rk)]
        print(
            f"{name}: recall@{K_RECALL}={r0.recall:.3f} ndcg@{K_RANK}={r0.ndcg:.3f} "
            f"ild@{K_RANK}={r0.ild:.3f} n_users={r0.n_users} | "
            f"{STATE_NK}: n_users={rk.n_users} recall={rk.recall:.3f}"
        )
    meta = RunMeta(
        split_mode=sp.split_mode,
        test_frac=TEST_FRAC,
        n_excluded=n_excluded,
        n_onboard_seeds=N_ONBOARD_SEEDS,
        k_history=K_HISTORY,
        min_user_interactions=MIN_USER_INTERACTIONS,
        min_item_interactions=MIN_ITEM_INTERACTIONS,
        elapsed_s=round(perf_counter() - t0, 1),
        git_sha=git_sha(),
    )
    jp = write_results(rows, state_rows, meta, out_dir=args.out)
    tp = write_eval_table(args.out, meta, len(n0), serving_dir=args.artifacts / SERVING_SUBDIR)
    pop = pipes.get(VARIANTS[0])
    ap = pop.retriever.save(args.artifacts / POP_ARTIFACT.name) if pop is not None else None
    print(f"split_mode={sp.split_mode} n_users={len(n0)}/{len(nk)} n_excluded={n_excluded}")
    print(f"→ {jp.name} · {tp} · {ap}")


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(
        prog="millie_rec.app.cli", description="Track A 데이터·평가 진입점(make data · make eval)"
    )
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("data", help="Goodbooks-10k 멱등 다운로드 + parquet 캐시")
    d.add_argument("--raw", type=Path, default=DIR_RAW / RAW_SUBDIR)
    d.add_argument("--processed", type=Path, default=DIR_PROCESSED)
    d.set_defaults(func=cmd_data)
    e = sub.add_parser("eval", help="등록 variant × 두 상태 평가 → results/")
    e.add_argument("--variant", choices=[ALL, *VARIANTS], default=ALL)
    e.add_argument("--processed", type=Path, default=DIR_PROCESSED)
    e.add_argument("--out", type=Path, default=DIR_RESULTS)
    e.add_argument("--artifacts", type=Path, default=DIR_ARTIFACTS)
    e.set_defaults(func=cmd_eval)
    add_demo_parser(sub)
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    args.func(args)


if __name__ == "__main__":
    main()
