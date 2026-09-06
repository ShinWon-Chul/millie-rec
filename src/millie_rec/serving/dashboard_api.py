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
# 읽는 사람이 처음 보는 다섯 문장이다. 줄표·가운뎃점 없이 문장으로 쓴다(사용자 결정 2026-09-06).
# 라우트는 상태 없이 바로 열리는 화면만 쓴다 — 예전 "#/reader/:id" 는 :id 가 그대로 실려 깨졌다.
# demo/scripts/make_mock.py 의 사본과 같은 내용이어야 한다(mock/서버 표류 방지).
MEMORABLE_5 = (
    (
        "취향 설정은 시작점이고 언제든 다시 씁니다. 다시 설정해도 읽은 기록은 지우지 않습니다",
        "취향을 다시 설정하면 앵커 행의 기준 책이 바뀌고 스냅샷이 두 개로 늘어납니다",
        "#/refresh",
    ),
    (
        "설문 7단계를 한 덩어리로 보지 않습니다. "
        "카테고리, 고르는 기준, 고른 5권이 각각 다른 일을 합니다",
        "취향 설정 3단계에서 고르는 기준을 바꾸면 카드에 붙는 배지 종류가 달라집니다",
        "#/onboarding",
    ),
    (
        "목표는 클릭이 아니라 실제로 읽기 시작하는 것입니다. 읽은 시간과 완독이 상태를 바꿉니다",
        "뷰어에서 가상 15분에 닿으면 유효 독서로 기록되고 대시보드 첫 카드에 반영됩니다",
        "#/dashboard",
    ),
    (
        "추천은 상위 목록을 뽑고 끝나지 않습니다. "
        "어떤 행을 어떤 순서로 놓는지까지가 메인 추천입니다",
        "메인에 다섯 행이 뜨고 행 사이 중복을 걸러낸 권수가 함께 표시됩니다",
        "#/home",
    ),
    (
        "정확도와 실서비스 제약을 같은 무게로 다룹니다. "
        "지연과 개인정보는 나중에 붙이는 항목이 아닙니다",
        "서재에서 맞춤 추천 동의를 철회하면 즉시 비개인화 목록으로 내려갑니다",
        "#/library",
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
DATA_NOTICE = "평가는 Goodbooks-10k(CC BY-SA 4.0)을 씁니다. 데모 카탈로그는 밀리 공개 도서 페이지의 수치, 메타, 표지 URL만 쓰고 텍스트는 노출하지 않으며 요청 시 삭제합니다. 데모 이웃은 콘텐츠 유사도입니다. 개인정보는 수집하지 않고 서버 latency는 참고값입니다"  # noqa: E501 — ../.claude/rules/serving.md 2트랙 고지 문장 verbatim(줄을 나누면 글자 대조가 불가능하다)


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
