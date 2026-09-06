"""GET /api/showcase(Must, 백엔드 서빙 01 §13) — eval_table.json → ShowcaseOut."""

import json
import logging
from pathlib import Path

from fastapi import APIRouter

from millie_rec.contracts import DIR_ARTIFACTS, DIR_RESULTS
from millie_rec.serving.dashboard_agg import build_dashboard
from millie_rec.serving.db import Database
from millie_rec.serving.schemas_should import (
    DashboardOut,
    EvalRow,
    EvalTable,
    Memorable,
    MetricMapping,
    ShowcaseOut,
)

log = logging.getLogger(__name__)

# 고정 경로 2개 — 요청에서 경로를 만들지 않는다(T-05-07-01)
EVAL_TABLE_PATH = DIR_ARTIFACTS / "serving" / "eval_table.json"
LATENCY_PATH = DIR_RESULTS / "latency.json"

SPLIT_MODE_UNKNOWN = "unknown"  # 파일 부재·손상 시 거짓 split_mode 를 만들지 않는다
# artifacts/serving/eval_table.json 키 → schemas_should.EvalRow 필드 (값은 문자열이라 float 캐스팅)
EVAL_KEY_MAP = {"recall@20": "recall_at_20", "ndcg@10": "ndcg_at_10", "ild@10": "ild_at_10"}
EVAL_SOURCE = {"metrics": "results/latest.csv", "p95": "results/latency.json"}

PHILOSOPHY = (
    "사용자가 취향 설정에서 직접 알려준 선호를 cold-start의 강한 prior로 사용하되, "
    "읽기 행동이 쌓일수록 그 비중을 줄여 가는 시간 가변 가중치로 "
    "4단계 파이프라인(후보 → 순위 → 재순위 → 페이지 구성)을 조립한다. "
    "목표는 클릭이 아니라 유효 독서 시작(QRS)이다."
)
# Offline 3지표 ↔ 파이프라인 3단계 1:1 (백엔드 서빙 01 §13)
METRIC_MAPPING = (
    ("Candidate Retrieval", "Recall@20"),
    ("Ranking", "NDCG@10"),
    ("Re-ranking", "ILD@10"),
)
MEMORABLE_5 = (
    (
        "취향 설정은 시작점이자 갱신되는 상태다 — 재설정하면 새 앵커 행이 뜨고 이전 기록은 남는다",
        "취향 재설정 후 anchor_ 행 seed 가 바뀌고 GET /api/users/{key}/state 의 snapshots 가 2개",
        "#/refresh",
    ),
    (
        "설문 7단계는 전부 다른 종류의 신호다 — 카테고리·기준·시드가 각각 행·배지·앵커를 만든다",
        "취향 설정 3단계의 기준을 바꾸면 카드 배지 종류가 바뀐다",
        "#/onboarding",
    ),
    (
        "클릭이 아니라 유효 독서 시작(QRS)이 목표다 — 이어 읽기·완독 이벤트가 상태를 바꾼다",
        "뷰어에서 읽기 후 user_state_weights 의 beta 가 0 에서 올라간다",
        "#/reader/:id",
    ),
    (
        "Top-K 가 아니라 페이지 구성까지가 메인 추천이다 — 5행 dedup·fresh_picks 는 내 카테고리 밖",
        "GET /api/recommend 의 rows 5개와 dedup_removed",
        "#/home",
    ),
    (
        "정확도와 실서비스 제약을 같은 수준에서 — 예산 초과·예외는 fallback 0→3, 항상 200",
        "인스펙터 fallback_level 과 results/latency.json p95",
        "#/dashboard",
    ),
)
ROADMAP = (
    "Reviewer-affinity",
    "Interleaving",
    "선호 교정 루프",
    "텍스트 난이도",
    "Two-Tower/ANN",
    "Kafka/K8s",
    "피크 autoscaling",
)
DATA_NOTICE = "평가 = Goodbooks-10k(CC BY-SA 4.0) · 데모 카탈로그 = 밀리 공개 도서 페이지(수치·메타·표지 URL만, 텍스트 미노출, 요청 시 삭제) · 데모 이웃 = 콘텐츠 유사도 · 개인정보 무수집 · 서버 latency는 참고값"  # noqa: E501 — ../.claude/rules/serving.md 2트랙 고지 문장 verbatim(줄을 나누면 글자 대조가 불가능하다)


def _read_p95(path: Path) -> float | None:
    """results/latency.json 의 전체 p95. bench 는 셀 배정 혼합이라 variant 별 p95 가 없다(D-11)."""
    if not path.exists():
        return None
    try:
        return float(json.loads(path.read_text(encoding="utf-8"))["p95"])
    except (OSError, ValueError, TypeError, KeyError):
        log.exception("latency.json unreadable at %s", path)
        return None


def _rows(raw: dict, p95: float | None) -> list[EvalRow]:
    """행마다 키 변환 + float 캐스팅("0.063" → 0.063). 키 누락·형 불일치는 그 행만 건너뛴다."""
    out: list[EvalRow] = []
    for row in raw.get("rows", []):
        try:
            values = {dst: float(row[src]) for src, dst in EVAL_KEY_MAP.items()}
            out.append(EvalRow(variant=row["variant"], p95_ms=p95, **values))
        except (KeyError, TypeError, ValueError):
            log.warning("eval_table row skipped: %r", row)
    return out


def load_eval_table(path: Path = EVAL_TABLE_PATH, latency_path: Path = LATENCY_PATH) -> EvalTable:
    """eval_table.json(02-CONTEXT D-09 형태) → EvalTable. 부재·손상은 빈 rows + unknown."""
    p95 = _read_p95(latency_path)
    raw: dict = {}
    if path.exists():
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
            raw = loaded if isinstance(loaded, dict) else {}
        except (OSError, ValueError):
            log.exception("eval_table unreadable at %s", path)
    split_mode = (raw.get("meta") or {}).get("split_mode") or SPLIT_MODE_UNKNOWN
    return EvalTable(split_mode=split_mode, source=dict(EVAL_SOURCE), rows=_rows(raw, p95))


def build_router(
    *,
    db: Database,
    eval_table_path: Path = EVAL_TABLE_PATH,
    latency_path: Path = LATENCY_PATH,
) -> APIRouter:
    """GET /api/showcase(파일 2개) + GET /api/dashboard(db 집계, 05-12)."""
    router = APIRouter(prefix="/api")

    @router.get("/dashboard", response_model=DashboardOut)
    def dashboard() -> DashboardOut:
        """§11 최소형 — 집계는 전부 dashboard_agg(Advisor 확정 17 B6). 여기는 배선만."""
        return build_dashboard(db)

    @router.get("/showcase", response_model=ShowcaseOut)
    def showcase() -> ShowcaseOut:
        # 파일은 호출마다 읽는다 — make bench 후 재기동 없이 p95 가 반영된다(KB 단위 json)
        return ShowcaseOut(
            philosophy=PHILOSOPHY,
            eval_table=load_eval_table(eval_table_path, latency_path),
            metric_mapping=[MetricMapping(stage=s, metric=m) for s, m in METRIC_MAPPING],
            personal_case=None,
            memorable_5=[Memorable(claim=c, how_to_verify=h, route=r) for c, h, r in MEMORABLE_5],
            roadmap=list(ROADMAP),
            data_notice=DATA_NOTICE,
        )

    return router
