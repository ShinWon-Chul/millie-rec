# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-09-05)

**Core value:** 설계서의 주장(취향 설정은 갱신되는 explicit prior · 4단계 파이프라인 · 3지표 1:1 대응 · 앵커/난이도/시간 가변 가중치)이 로컬에서 실행되는 코드와 실측 숫자로 증명되어 PDF 5페이지 안에 들어간다. 데모·서버가 죽어도 PDF는 완결된다.
**Current focus:** Phase 1 '로컬 서빙 스켈레톤'(.planning/ROADMAP.md) — Day 1, `make serve`로 `/health`·정적 데모·fallback 추천을 띄운다

## Current Position

Phase: 1 of 8 (로컬 서빙 스켈레톤)
Plan: 0 of TBD in current phase
Status: Ready to plan
Last activity: 2026-09-05 — ROADMAP.md 작성, v1 요구사항 58건 전부 페이즈에 매핑

Progress: [░░░░░░░░░░] 0%

## Performance Metrics

**Velocity:**
- Total plans completed: 0
- Average duration: -
- Total execution time: 0.0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| - | - | - | - |

**Recent Trend:**
- Last 5 plans: -
- Trend: -

*Updated after each plan completion*

## Accumulated Context

### Decisions

결정의 정본은 `../.assets/개발일지/`(6요소 형식)이고, 프로젝트 수준 요약은 PROJECT.md Key Decisions 표에 있다. 현재 작업에 영향을 주는 결정:

- 첫 페이즈 = 로컬 서빙 스켈레톤 (walking skeleton) — 결정 '참조 표기 규칙 + 전 과정 로컬 기동'(개발일지 2026-09-04 파일 항목 D49)
- 데이터 2트랙, 데모 이웃 = 콘텐츠 유사도 — 결정 '데모 이웃은 콘텐츠 유사도'(개발일지 2026-09-04 파일 항목 D42)
- Should 버리는 순서 = 아키텍처 01 §8 티어 표 아래부터, 완독 직후 행·별점은 가장 늦게 — 결정 '버리는 순서'(개발일지 2026-09-04 파일 항목 D40)
- 두 계약(`contracts.py`·`serving/schemas.py`) Day 1 freeze 완료, 응답 형태 최종 freeze는 Day 3 — 결정 '두 계약 Day 1 freeze'(개발일지 2026-09-04 파일 항목 D44)

### Day 게이트

| Day | 최소 종료 조건 | 상태 |
|-----|---------------|------|
| 1 | Phase 1 스켈레톤 `make smoke` PASS · `pop` Recall@20 실측 1개 · `millie_pages.jsonl` ≥600 | ⬜ |
| 2 | 커버리지 게이트·이웃 게이트 3 통과 · Recall 3행 · 배포 URL `/health` 200·볼륨 영구 확인 | ⬜ |
| 3 | 비교표 4행 실측 + 본인 5권 케이스 · **모델·API 형태 freeze 선언** | ⬜ |
| 4 | 배포 URL에서 쇼케이스 화면(`#/`) → 관제 대시보드 화면(`#/dashboard`) 완주, variant 전환 시 책이 바뀐다 | ⬜ |
| 5 | `/pdf-check` 통과 · 5페이지 이내 · 제출(09-08 22:00 KST 가정) | ⬜ |

### Pending Todos

없음. (진행 이력·미결의 보조 정본은 `PROGRESS.md`)

### Blockers/Concerns

- **밀리 야간 배치 진행 중** — Phase 3 '밀리 카탈로그 빌드' 착수 전제는 배치 종료 또는 `data/raw/millie_pages.jsonl` ≥ 600행. 진행 수치는 `../.assets/설계서/데이터 소스/03_밀리_데이터_적재_트래킹.md` §2.
- **사용자 몫(코드 밖)** — Railway 가입·카드·Usage Limit $15, UptimeRobot·Sentry 계정(Phase 7 Day 2 스켈레톤 전), 본인 5권 선정(밀리 카탈로그 내 한국 책, Phase 4 전), 제출 기한 확인, PDF 조판.
- **`demo/` 27파일은 v1 산출물** — Phase 6 '데모 재구성' 착수 시 재구성 대상(구 형태 grep 0건이 완료 기준).

## Deferred Items

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| *(none)* | | | |

## Session Continuity

Last session: 2026-09-05
Stopped at: ROADMAP.md·STATE.md 작성 및 REQUIREMENTS.md traceability 갱신 완료
Resume file: None
