# Phase 7 '배포' — Discussion Log

**일시:** 2026-09-06 · **모드:** `/gsd-discuss-phase 7 --auto`(ADVISOR_MODE 없음) + 사용자 직접 결정 4건
**목적:** 감사 추적용. 다운스트림 에이전트는 `07-CONTEXT.md` 만 읽는다.

## 사전 상태
- `init phase-op 7` → `phase_found: true`, `phase_dir: null`(디렉터리 없음 → 생성), `has_context/has_plans: false`
- `todo match-phase 7` → 0건
- Phase 5 '서빙 Must 완성' 검증 passed, Phase 6 '데모 재구성' 다른 세션 진행 중

## 식별한 그레이 영역 4개
1. 배포 시점·순서 (스켈레톤 지금 vs 한 번에 vs 계획만)
2. 관측 범위 (Sentry·Grafana·UptimeRobot)
3. repo 위생·저작권 (`report/figures/*.png` 공개 여부)
4. 커밋·push 범위 (Phase 6 세션 커밋 동반 공개)

## 문답
| # | 질문 | 사용자 답 | 반영 |
|---|---|---|---|
| 1 | 스켈레톤 배포 시점 | **지금 스켈레톤** | D-01·D-02 |
| 2 | 미커밋 158개 처리 | **Phase 1~5 지금 커밋·push** | D-03 (실행 완료 `20d5fa3`) |
| 3 | `report/figures/*.png` repo 포함 | **제외** | D-07·D-08 (`.gitignore` 수정 완료) |
| 4 | Sentry·Grafana | 1차 "둘 다 폐기" → **정정: Sentry 유지, Grafana만 폐기** | D-04·D-05 |
| 5 | push 범위(Phase 6 커밋 21개 동반) | **main 전체 push** | D-03 (`8e5172b..20d5fa3`) |

## 문서에서 이미 확정돼 재질문하지 않은 것
`../.assets/설계서/시스템 아키텍처, 기술 스택 및 배포(프론트, 백엔드 서빙)/02_배포_절차_및_설정.md` 가 실행 정본이라 아래는 그대로 채택했다 — 볼륨 `/data` 1GB(§3-1) · `DATA_DIR` 환경변수(§1-4) · Dockerfile 3조건(§2-1) · 검증 절차(§3-2·§4-4) · 롤백(§6) · 장애 대응표(§7) · 대체 경로(§9) · 사용자 체크리스트 A/B(§1-0).

## 범위 이탈로 밀어낸 것
커스텀 도메인 · Railway CLI · 오토스케일링 · 다중 리전 — `07-CONTEXT.md` `<deferred>` 에 기록.

## 남은 사용자 몫
Railway 결제·프로젝트 생성·볼륨·변수·도메인 생성(§1-0 B 묶음, 10분) · UptimeRobot 모니터 · Sentry DSN.
