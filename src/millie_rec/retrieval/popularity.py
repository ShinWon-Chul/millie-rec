"""pop 기준선 — contracts.CandidateGenerator 구현.

train 전체 행 카운트(평점 무관, CONTEXT D-05) · seen 제외 · 작은 json 아티팩트(D-10).
"""

import json
from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING

from millie_rec.contracts import COL_ITEM, DIR_ARTIFACTS, Candidate, UserState

if TYPE_CHECKING:
    import pandas as pd

SOURCE_POPULARITY = "popularity"  # serving/fallback.py 와 같은 값 — serving import 불가라 중복 정의
ARTIFACT_NAME = "popularity.json"
POP_ARTIFACT = DIR_ARTIFACTS / ARTIFACT_NAME  # app/pipeline.py 가 존재 검사만 한다(D-10)
TOP_N = 1000  # D-10: K_MAX(100) + seen 여유. 서빙은 이 상위 N 만 안다


class PopularityRetriever:
    """전역 인기 상위 k. fit 은 train 만 받는다(Protocol docstring 그대로)."""

    name = "pop"

    def __init__(self, ranked: Sequence[tuple[int, float]] = ()) -> None:
        self._ranked: list[tuple[int, float]] = [(int(b), float(s)) for b, s in ranked]

    def fit(self, train: "pd.DataFrame") -> "PopularityRetriever":
        counts = train[COL_ITEM].value_counts()  # 평점 무관 — "평점이 있다 = 읽었다"(D-05)
        table = counts.rename_axis(COL_ITEM).reset_index(name="n")
        table = table.sort_values(["n", COL_ITEM], ascending=[False, True], kind="stable")
        self._ranked = [
            (int(b), float(n)) for b, n in zip(table[COL_ITEM], table["n"], strict=True)
        ]
        return self

    def retrieve(self, user: UserState, k: int) -> list[Candidate]:
        out: list[Candidate] = []
        for b, s in self._ranked:  # 상위부터 k 개에서 멈춘다 — 전 카탈로그 순회 아님
            if b in user.seen:
                continue
            out.append(Candidate(book_id=b, source=SOURCE_POPULARITY, score=s))
            if len(out) == k:
                break
        return out

    def save(self, path: Path = POP_ARTIFACT, *, top_n: int = TOP_N) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"name": self.name, "items": [[b, s] for b, s in self._ranked[:top_n]]}
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        return path

    @classmethod
    def load(cls, path: Path = POP_ARTIFACT) -> "PopularityRetriever":
        payload = json.loads(path.read_text(encoding="utf-8"))
        return cls((int(b), float(s)) for b, s in payload["items"])
