---
gsd_state_version: 1.0
milestone: v2.1
milestone_name: milestone
status: "07-04 '마감' ✅ — 게이트 12행 · 캡처 6장+QR(`report/figures/`, repo 밖) · draft §3-3·§5-3 · 기록 4곳(PROGRESS 3행 · 개발일지 D85 · 아키텍처 01 §2-1) · Codex 2회차 5건(C3·C4 반영, C1·C5 인계, C2 무시) · 사용자 지시 데모 버그(`startFresh`) 수정 · 커밋 3 push `ad8cd4a..8455408` 16:33:37 → Active 16:34:23(다운 1표본) · **표식 `probe-main-20260906` state 200(이름 기준 볼륨 확인)** · 배포본 fresh_check PASS · C3 실측 403. 운영 인계는 07-04-SUMMARY"
stopped_at: Phase 8 'PDF 제출물' context gathered (08-CONTEXT.md D-01~D-18) — 다음 /gsd-plan-phase 8
last_updated: "2026-09-06T09:15:33.751Z"
last_activity: 2026-09-06
progress:
  total_phases: 8
  completed_phases: 7
  total_plans: 46
  completed_plans: 46
  percent: 100
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-09-05)

**Core value:** 설계서의 주장(취향 설정은 갱신되는 explicit prior · 4단계 파이프라인 · 3지표 1:1 대응 · 앵커/난이도/시간 가변 가중치)이 로컬에서 실행되는 코드와 실측 숫자로 증명되어 PDF 5페이지 안에 들어간다. 데모·서버가 죽어도 PDF는 완결된다.
**Current focus:** Phase 7 '배포' ✅ 완료(07-01~04) — 다음 Phase 8 'PDF 제출물'(`/gsd-verify-work 7` 후 `/gsd-discuss-phase 8`)

## Current Position

Phase: 8
Plan: Not started
Status: 07-04 '마감' ✅ — 게이트 12행 · 캡처 6장+QR(`report/figures/`, repo 밖) · draft §3-3·§5-3 · 기록 4곳(PROGRESS 3행 · 개발일지 D85 · 아키텍처 01 §2-1) · Codex 2회차 5건(C3·C4 반영, C1·C5 인계, C2 무시) · 사용자 지시 데모 버그(`startFresh`) 수정 · 커밋 3 push `ad8cd4a..8455408` 16:33:37 → Active 16:34:23(다운 1표본) · **표식 `probe-main-20260906` state 200(이름 기준 볼륨 확인)** · 배포본 fresh_check PASS · C3 실측 403. 운영 인계는 07-04-SUMMARY
Deploy: BASE=https://millie-rec-production.up.railway.app (Railway project efficient-ambition · region Singapore/sin1 · Dockerfile 자동 감지 · volume /data 1GB **13:53 부착 확정** · DATA_DIR=/data · 스켈레톤 push 09-06 12:52 KST → /health 200 13:07 · SQLite 영구성 ✅ 13:55 재배포 후 users 1 유지 · **본배포 9fb53ab 2026-09-06 14:48**(push 14:34:53 → Active 14:48:19, Dockerfile 변경 빌드 13.5분) · SENTRY_DSN 투입 14:2x · 배포 완주 Playwright 12/12 콘솔 에러 0 · 4 variant distinct 4 · showcase p95 79.5 표시 · 신규 표식 `probe-main-20260906` level 0 · **07-04 push `8455408` 16:34 재배포 후 `/state` 200 — 이름 기준 영구성 확인 ✅**)
Monitor: UptimeRobot **Keyword** 모니터(`"status":"ok"`, GET, 5분 — HEAD 는 FastAPI 404 라 HTTP 타입 불가) · 공개 상태 페이지 https://stats.uptimerobot.com/20M6QwPo7z · Sentry DSN **Railway 투입 완료**(07-03, 배포 로그 sentry 에러 0)
Downtime(D-14, /health 5초 폴링): 코드 push 재배포 **약 5~15초**(실패 1표본 ×3회: 502·502·연결끊김) · 볼륨 최초 부착 재배포 **30~40초**(404 6표본). ⚠️ railway.json 은 Railway 정책(Config as Code 2026-08-28 옵트인 종료)으로 **무효** — healthcheckPath 는 대시보드 수동 입력, 07-04 문서 정정
Last activity: 2026-09-06

Progress: [█████░░░░░] 50% (4/8 phases — Phase 4 검증 통과 · Phase 3 검증(/gsd-verify-work 3)만 남음)

## Performance Metrics

**Velocity:**

- Total plans completed: 30
- Average duration: -
- Total execution time: 0.0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01 | 2 | - | - |
| 02 | 6 | - | - |
| 2 | 6 | - | - |
| 04 | 6 | - | - |
| 05 | 12 | - | - |
| 07 | 4 | - | - |

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
| 1 | Phase 1 스켈레톤 `make smoke` PASS ✅(09-05) · `pop` Recall@20 실측 1개 ✅(09-05, `results/latest.csv` pop 0.063) · `millie_pages.jsonl` ≥600 ✅(09-05, 8,810줄) | ✅ |
| 2 | 커버리지 게이트·이웃 게이트 3 통과 ✅(09-05 20:28, 8,708권 스냅샷 — 최종 재빌드 대기) · Recall 3행 ✅(09-06 비교표 4행) · 배포 URL `/health` 200 ✅(09-06 13:07, `millie-rec-production.up.railway.app`) · 볼륨 영구 확인 ✅(09-06 13:55 재배포 후 표식 행 유지) | ✅ |
| 3 | 비교표 4행 실측 ✅(09-06, `results/latest.csv`·D-07 게이트 통과) · 본인 5권 케이스 ✅(`report/demo_5books.md`, SEEDS=1012,2765,1446,1222,2292) · **모델·API 형태 freeze 선언 ✅ 🧊**(09-06 00:5x, D-14 4종 — STATE·개발일지 D72·draft §4-1 각주·§5-1) | ✅ |
| 4 | 배포 URL에서 쇼케이스 화면(`#/`) → 관제 대시보드 화면(`#/dashboard`) 완주 ✅(09-06 14:5x, Playwright 12/12·콘솔 에러 0 + 사용자 approved) · variant 전환 시 책이 바뀐다 ✅(4 variant 제목 목록 4종) | ✅ |
| 5 | `/pdf-check` 통과 · 5페이지 이내 · 제출(09-08 22:00 KST 가정) | ⬜ |

### Pending Todos

없음. (진행 이력·미결의 보조 정본은 `PROGRESS.md`)

### Blockers/Concerns

- **UAT Test 9 이슈(major):** 카탈로그 title 728/8,708권(8.4%)이 밀리 기능 배지 라벨(도슨트북·읽던 지점 그대로 이어듣기·무료·오브제북·웹소설·웹툰·오디오웹소설 + `종료 D-N` 9건). 원인 `millie_parse._header` 선행 노이즈 집합 누락. 수정 = 03-08-PLAN(파서 TDD·게이트 `_n_badge_title`·`--recollect`·재수집 ≈815건 → 최종 재빌드). 재수집·최종 스냅샷은 배치 종료 후 한 번에(03-06 Task 4 흡수).
- ~~**재수집 진행 중(03-08 Task 3-c):**~~ → **해소(09-06 00:3x):** 재수집 896건 완료·최종 `make millie` 1회 → 9,447권·`_n_badge_title 0`·id_map 접두 불변(9,453행)·`test_coverage_gate` 통과. **이후 `make millie*` 재실행 금지(freeze ③).** 원문: 완료 판정 = `pgrep -f collect_millie` 빈 출력 + 두 로그 `SUMMARY` 줄. 그 뒤 순서: JSONL 접두 md5 불변 확인(scratch `jsonl.md5.before`, 9,586줄) → 사전 점검(`badge_title_remaining`) → `cp data/id_map.csv <scratch>/id_map.final_before.csv` → `time make millie` → 게이트(`_n_badge_title,0`)·233+ 테스트·smoke·level 0(배지 0) → draft 마커 제거·트래킹 03 §2 최종 스냅샷 행·개발일지 D67 → 이후 `make millie` 금지. 재수집 중 병행 가능: Phase 4 discuss/plan, `/gsd-code-review 3`. 금지: `make millie*`, `scripts/millie_parse.py`·`collect_millie.py`·`data/raw/**` 편집, `make mock`.
- **(참고) 21:37 다른 세션의 카탈로그 재빌드 감지** — parquet 9,450권·id_map 9,452행(append-only 유지, HEAD·20:28 접두 동일). 최종 재빌드가 덮어쓴다.
- ~~**밀리 배치(2샤드) 진행 중 — 03-08 Task 3 = 03-06 Task 4 사람 게이트:**~~ → 배치 자연 종료(21:28) 확인, 사용자 알림 수신. 배치 자연 종료 또는 Day 2(09-06) 오전 사용자 승인 후 `pkill -f collect_millie`(D-03) → `make millie` 최종 재빌드 1회 → `report/draft.md` `[숫자는 … 교체]` 마커·트래킹 03 §2·D66 결과 줄 갱신 → 이후 `make millie` 금지(Day 3 freeze). 20:31 현재 jsonl 8,810줄 · discovered 8,681줄. 절차는 `.planning/phases/03-millie-catalog/03-06-SUMMARY.md` CHECKPOINT 절.
- **Phase 3 후속 인계(03-06 SUMMARY 관측):** 익명 level 3 items `title` None(Phase 5 fallback meta 조인) · 제목 중복('도슨트북' 2권)·'무료' 제목 도서(Phase 5 dedup·Phase 6 화면) · `inspector.js` `static_popular` 라벨·`make mock` 금지(Phase 6) · 이웃 빌드 RSS 1.24GB@6,977권(9천 권 초과 시 float32).
- **사용자 몫(코드 밖)** — Railway 가입·카드·Usage Limit $15, UptimeRobot·Sentry 계정(Phase 7 Day 2 스켈레톤 전), 본인 5권 선정(밀리 카탈로그 내 한국 책, Phase 4 전), 제출 기한 확인, PDF 조판.
- **`demo/` 27파일은 v1 산출물** — Phase 6 '데모 재구성' 착수 시 재구성 대상(구 형태 grep 0건이 완료 기준).

## Deferred Items

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| *(none)* | | | |

## Session Continuity

Last session: 2026-09-06T09:15:33.749Z
Stopped at: Phase 8 'PDF 제출물' context gathered (08-CONTEXT.md D-01~D-18) — 다음 /gsd-plan-phase 8
Resume file: .planning/phases/08-pdf/08-CONTEXT.md
