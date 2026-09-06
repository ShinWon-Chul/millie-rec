# Phase 1: 로컬 서빙 스켈레톤 - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-09-05
**Phase:** 1-로컬 서빙 스켈레톤
**Areas discussed:** fallback 응답 형태, SQLite 스켈레톤 범위, create_app 주입 표면, 검증·완료 형태

---

## fallback 응답 형태

| Option | Description | Selected |
|--------|-------------|----------|
| contracts 상수 신설 | `MODEL_VERSION_FALLBACK="fallback_v1"` 추가(Advisor). 모델 이름과 분리 | ✓ |
| 서빙하려던 variant 이름 유지 | `hybrid_div_v1` + `fallback_level=3`으로 degraded 표시 | |
| `pop_v1` 재사용 | level 3 = 전역 인기이므로 pop 이름 | |

| Option | Description | Selected |
|--------|-------------|----------|
| 빈 trending 1행 | `rows=[trending(purpose fallback, items [])]`, `items=[]` | ✓ |
| Must 5행 뼈대 전부 | 빈 items로 5행 모두 | |
| rows·items 모두 빈 배열 | 최소 | |

| Option | Description | Selected |
|--------|-------------|----------|
| 매 응답 `rec_<6hex>` 발급 | 백엔드 §0 ID 규약, DB 기록은 Phase 5 | ✓ |
| null 유지 | 저장 않는 응답엔 id 없음 | |

**User's choice:** 세 질문 모두 권장안. 다음 영역으로 이동.
**Notes:** latency 실측·가중치 0·seeds 검증은 문서 확정 사항이라 Claude 재량.

---

## SQLite 스켈레톤 범위

| Option | Description | Selected |
|--------|-------------|----------|
| Must 4 + Should 3 전부 | 아키텍처 01 §3-4 DDL 그대로, 검증은 Must 4만 | ✓ |
| Must 4만 | SKEL-04 글자 그대로 | |

| Option | Description | Selected |
|--------|-------------|----------|
| 생성만, 쓰기 없음 | 스키마·PRAGMA·연결만 | ✓ |
| 매 recommend마다 recommendations 1행 | 노출 로그 Day 1부터 | |

| Option | Description | Selected |
|--------|-------------|----------|
| 존재 테이블 전부, 0건 포함 | `/health.db_row_count`가 테이블 존재 증거 | ✓ |
| events·preference_snapshots만 | 백엔드 §1 예시 2키 | |
| 빈 dict | Phase 5에서 채움 | |

**User's choice:** 세 질문 모두 권장안. 다음 영역으로 이동.

---

## create_app 주입 표면

| Option | Description | Selected |
|--------|-------------|----------|
| 시그니처 유지 + None 기본값 | serving.md 인자 이름·순서 유지, 미사용 인자 `\| None = None` | ✓ |
| app/이 빈 스텁 주입 | EmptyCatalog 등 | |
| Phase 1 최소 시그니처 | `create_app(db, fallback)` | |

| Option | Description | Selected |
|--------|-------------|----------|
| serving/fallback.py의 Pipeline 구현 | `GlobalPopularFallback(catalog\|None)` | ✓ |
| fallback.py에 함수만 | `fallback_response()` 순수 함수 | |

| Option | Description | Selected |
|--------|-------------|----------|
| 넣지 않음 | 같은 origin 설계 | ✓ |
| localhost:8080만 허용 | demo-serve 교차 확인 | |

**User's choice:** 세 질문 모두 권장안. 다음 영역으로 이동.

---

## 검증·완료 형태

| Option | Description | Selected |
|--------|-------------|----------|
| pytest 단정 + /health 키, smoke 3점 유지 | Makefile·REQUIREMENTS 불변 | ✓ |
| smoke에 4번째 점 추가 | python -c로 db_row_count 확인 | |

| Option | Description | Selected |
|--------|-------------|----------|
| create_app 직접 조립 + server.app 1건 | tmp_path DB, serving 단독 + StaticFiles 1건 | ✓ |
| server.app만 import | 실제 data/local DB 사용 | |

| Option | Description | Selected |
|--------|-------------|----------|
| 로컬 커밋 1개, push 없음 | 저작권 grep 후, 실행 시 재승인 | ✓ |
| 원격 결정까지 보류 | | |
| 코드·.planning 2개 커밋 | | |

**User's choice:** 세 질문 모두 권장안. 마무리 선택.
**Notes:** 토론 중 확인된 사실 — 09-05 오전 다른 세션이 원격 레포 생성·스캐폴드 push·`.gitignore` `data/local/` 추가를 이미 완료. 커밋 방침(push 없음)은 그대로 유효.

---

## Claude's Discretion

seeds 파싱·422, `k` 기본/상한, `db_ok`·`uptime_s` 방식, lifespan 범위, FastAPI 메타, `schema.sql` 로딩·패키지 포함 확인, 인덱스 시점, 행 제목 상수 위치, 브리프 분할(권장 Worker 1 + Advisor).

## Deferred Ideas

SQLite 쓰기(Phase 5) · fallback level 1·2(Phase 5) · CORS(Phase 6) · Should 3 테이블 사용(Phase 4·5) · smoke 4번째 점(채택 안 함) · origin push(사용자 승인) · PROGRESS 미결 8 optional 필드(Phase 4).
