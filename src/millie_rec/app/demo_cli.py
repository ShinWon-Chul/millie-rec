"""cli demo — 본인 5권 앵커 케이스(REC-07, D-12·D-13). stdout 마크다운만 쓴다."""

import argparse
from pathlib import Path

import numpy as np

from millie_rec.app.pipeline import load_catalog
from millie_rec.app.pipeline_kr import build_pipelines_kr, load_vectors_kr
from millie_rec.contracts import K_RANK, VARIANTS, UserState
from millie_rec.data import DIR_SERVING, CatalogKR
from millie_rec.ranking import state_weights
from millie_rec.reranking import GUARD_MIN_COMPLETED, GUARD_RESID_Z

HYBRID_DIV, N_NEIGHBORS, FIND_LIMIT = VARIANTS[3], 5, 30  # D-13 seed 별 이웃 top-5
HEADER = "| # | 책 | 저자 | 분야 | 난이도 | 근거 |"  # D-13 헤더
RULE = "|---|---|---|---|---|---|"
NEIGHBOR_NOTE = "이웃은 콘텍츠 유사도(제목·소개 TF-IDF)"
FIXED_SENTENCE = (  # .claude/rules/data.md 고정 문장 — 글자 그대로
    "데모 카탈로그의 앵커 이웃은 콘텍츠 유사도다. 협업 필터링(Item-KNN)의 Recall·NDCG는 "
    "유저 단위 로그가 있는 Goodbooks(Track A)에서만 측정하며 두 트랙의 숫자를 섞지 않는다."
)
MILLIE_INDEX = "millie_index"


def _norm(s: object) -> str:
    return "".join(str(s or "").split()).casefold()  # 대소문자·공백 무시 매칭 키


def _parse_seeds(raw: str) -> tuple[int, ...]:
    """'1,2,3' → (1, 2, 3). serving/api.py 와 같은 로직의 중복 정의(serving 내부 import 불가)."""
    try:
        seeds = tuple(int(s) for s in raw.split(",") if s.strip())
    except ValueError as e:
        raise SystemExit("--seeds 는 정수 콤마 목록") from e
    if not seeds:
        raise SystemExit("--seeds 는 정수 콤마 목록")
    return seeds


def _all_meta(catalog: CatalogKR) -> list[dict]:
    return catalog.meta(catalog.popular(n=10**6))  # eligible 전량, pop_rank 순


def _tertiles(metas: list[dict]) -> tuple[float, float]:
    d = [m["difficulty"] for m in metas if m.get("difficulty") is not None]
    return tuple(float(x) for x in np.quantile(d, [1 / 3, 2 / 3])) if d else (1 / 3, 2 / 3)


def _dots(d: float | None, t: tuple[float, float]) -> str:
    """난이도 3분위 ●○○ — 숫자는 노출하지 않는다(main §5-6 낙인)."""
    if d is None:
        return "—"
    return "●○○" if d < t[0] else ("●●○" if d < t[1] else "●●●")


def _cell(v: object) -> str:
    """셀 안 '|' 는 전각으로 — 저자 문자열의 '|' 가 표 열을 깨뜨렸다(09-06 실측)."""
    return str(v).replace("|", "｜")


def _row(n: int, m: dict, dots: str, why: str) -> str:
    cats = _cell("·".join(m.get("categories") or []) or "—")
    title, authors = _cell(m.get("title") or "(제목 없음)"), _cell(m.get("authors") or "—")
    return f"| {n} | {title} | {authors} | {cats} | {dots} | {why} |"


def cmd_find(catalog: CatalogKR, query: str) -> None:
    q = _norm(query)
    hits = [
        m for m in _all_meta(catalog) if q in _norm(m.get("title")) or q in _norm(m.get("authors"))
    ][:FIND_LIMIT]
    print("| book_id | 제목 | 저자 | 분야 |")
    print("|---|---|---|---|")
    for m in hits:
        cats = "·".join(m.get("categories") or []) or "—"
        cells = (m["book_id"], m.get("title"), m.get("authors") or "—", cats)
        print("| " + " | ".join(_cell(x) for x in cells) + " |")
    if not hits:
        print("(일치 없음)")


def cmd_seeds(catalog: CatalogKR, vectors, seeds: tuple[int, ...], k: int) -> None:
    pipes = build_pipelines_kr(catalog, weights=state_weights, vectors=vectors)
    if HYBRID_DIV not in pipes:
        raise SystemExit(
            "content_vectors_kr.npz 없음 — hybrid_div 불가(make millie 는 freeze 전 1회)"
        )
    t = _tertiles(_all_meta(catalog))
    nbr = {s: catalog.neighbors(s, N_NEIGHBORS) for s in seeds}
    ids = list(seeds) + [n for s in seeds for n, _ in nbr[s]]
    by_id = {int(m["book_id"]): m for m in catalog.meta(ids)}
    for s in seeds:
        m = by_id.get(s)
        if m is None:
            print(f"### seed {s} — 카탈로그에 없음\n")
            continue
        print(f"### 『{m['title']}』을 좋아하셨다면 — {NEIGHBOR_NOTE}")
        print(HEADER)
        print(RULE)
        for n, (nb, w) in enumerate(nbr[s], 1):
            nm = by_id.get(nb, {"book_id": nb})
            print(_row(n, nm, _dots(nm.get("difficulty"), t), f"content {w:.2f}"))
        print()
    user = UserState(None, explicit_seeds=seeds)
    w = state_weights(user)
    items = pipes[HYBRID_DIV].recommend(user, k)
    stats = catalog.stats([i.book_id for i in items])
    bad = sum(
        1
        for st in stats
        if st.source == MILLIE_INDEX and st.resid_z is not None and st.resid_z < GUARD_RESID_Z
    )
    cats = {
        int(m["book_id"]): m.get("categories") for m in catalog.meta([i.book_id for i in items])
    }
    print(
        f"### hybrid_div 상위 {k} — alpha={w['alpha']} beta={w['beta']} gamma={w['gamma']} · "
        f"가드 활성(n_completed={len(user.history)}<{GUARD_MIN_COMPLETED}) · "
        f"상위 {k} 중 resid_z<−1(millie_index) {bad}권"
    )
    print(HEADER)
    print(RULE)
    for n, i in enumerate(items, 1):
        m = {"title": i.title, "authors": i.authors, "categories": cats.get(i.book_id)}
        print(_row(n, m, _dots(i.difficulty, t), "+".join(i.source_channels)))
    print()
    print(FIXED_SENTENCE)


def cmd_demo(args: argparse.Namespace) -> None:
    catalog = load_catalog(args.serving)
    if catalog is None:
        raise SystemExit(f"카탈로그 없음 @ {args.serving} — make millie 후(freeze 전 최종 1회)")
    if args.find:
        cmd_find(catalog, args.find)
    elif args.seeds:
        cmd_seeds(catalog, load_vectors_kr(args.serving), _parse_seeds(args.seeds), args.k)
    else:
        raise SystemExit("--find 또는 --seeds 중 하나")


def add_demo_parser(sub) -> None:
    m = sub.add_parser("demo", help="본인 5권 앵커 케이스(stdout 마크다운) · --find 제목/저자 검색")
    m.add_argument("--seeds", type=str, default=None)
    m.add_argument("--find", type=str, default=None)
    m.add_argument("--serving", type=Path, default=DIR_SERVING)
    m.add_argument("--k", type=int, default=K_RANK)
    m.set_defaults(func=cmd_demo)
