---
phase: 07-deploy
plan: 04
wave: 4
status: complete
subsystem: infra
tags: [railway, uptimerobot, sentry, playwright, codex, qr]
requires:
  - phase: 07-03 본배포
    provides: 배포 URL(본배포 9fb53ab) · 표식 probe-main-20260906 · walk.py 완주 셀렉터
provides:
  - PDF 5장 재료 — 배포 URL·QR·캡처 6장(report/figures/, repo 밖) · draft §3-3·§5-3
  - Codex 배포 전체 리뷰 2회차 마감(5건 3분류 · C3·C4 반영)
  - 기록 4곳(PROGRESS 3행+미결 5 해소 · 개발일지 D85 · STATE · 아키텍처 01 §2-1) · 운영 인계
  - 사용자 지시 데모 버그 수정 — 쇼케이스 '신규 유저로 체험하기' startFresh
affects: [08-pdf, 운영 인계]
tech-stack:
  added: []          # qrcode 는 uv run --with 일회성 — pyproject·uv.lock 무변경
  patterns: [D8 깨끗한 시작의 정본 = presets.resetAll 1곳, 철회 유저 쓰기 거부 기준 = events_gate.consent_off_keys]
key-files:
  created: [report/figures/p5_01_onboarding.png ~ p5_06_home_after.png, report/figures/p5_qr.png, .planning/phases/07-deploy/07-04-SUMMARY.md]
  modified: [report/draft.md, .planning/STATE.md, demo/js/presets.js, demo/js/actions.js, demo/js/screens/d8_showcase.js, src/millie_rec/app/server.py, src/millie_rec/serving/ratings_api.py, tests/app/test_sentry.py, tests/serving/test_ratings.py, ../PROGRESS.md, ../.assets/개발일지/2026-09-06_Day2_Phase4_파이프라인과_freeze.md, ../.assets/설계서/…/01_시스템_아키텍처_기술스택_배포.md]
key-decisions:
  - "Codex 2회차: C3(철회 후 별점 재저장)·C4(Sentry 요청 본문) 반영, C1(익명 candidate_sets 무제한) 인계, C2(/health 200) 무시 유지 + UptimeRobot 키워드 db_ok 권고, C5(전역 p95) 문구 정정 인계"
  - "push 결정 = push ok(사용자 '승인합니다') — 재배포 1회 감수"
  - "개발일지 번호 D85(D81~84 는 다른 세션 선점) · DEPLOY-03 검사에 demo/assets/brand/ 예외"
requirements-completed: [DEPLOY-01, DEPLOY-02, DEPLOY-03]
duration: ~2h 10m
completed: 2026-09-06
---

# 07-04 마감 — 실행 요약

Phase 7 '배포'(`.planning/ROADMAP.md` "### Phase 7: 배포") wave 4. 배포는 07-03 에서 끝났고 여기서는
게이트 재확인 · Codex 2회차 · 캡처 6장+QR · 기록 4곳 · 운영 인계를 남겼다. 플랜은 "코드 0" 이었지만
**사용자 지시(16:1x) 데모 버그 1건**과 **Codex 필수 fix 2건**으로 코드 커밋 2개가 추가됐다(아래 이탈).

## Task 1 — 최종 게이트 12행 (전부 통과, 16:05~16:10 KST)

| # | 검사 | 기대 | 실측 |
|---|---|---|---|
| 1 | `git ls-files \| grep -icE "pdf\|png\|assets"` | 0 | **1** = `demo/assets/brand/millie-mark.png`(Phase 6.1 승인 자산, 07-03 예외) → 예외 후 **0** |
| 2 | `git check-ignore report/figures/p5_qr.png` | FIGURES_IGNORED | ✅ |
| 3 | `git status --short -- src tests demo artifacts results Dockerfile railway.json Makefile pyproject.toml` | 0 | `src/·demo/·Dockerfile·railway.json·pyproject` **0**. `Makefile`·`results/millie_edges_gate.json`·미추적 12건은 **다른 세션의 밀리 리뷰 작업**(미커밋) — 건드리지 않음, push 에 안 섞임 |
| 4 | `git diff --stat origin/main -- src tests demo` | 빈 출력 | ✅ |
| 5 | `/health` `db_ok and api_version=="v2" and model_version!=null` | 종료 0 | ✅ `hybrid_div_v1` · `artifacts_loaded_at 05:54:14Z`(14:54 재기동 — 07-03 Active 14:48 뒤 1회 더) |
| 6 | 25초 간격 5회 | 200 ×5 | **`200 200 200 200 200`** |
| 7 | 상태 페이지 `stats.uptimerobot.com/20M6QwPo7z` | 200 | ✅ 200 |
| 8 | `/metrics` | 404 | ✅ 404(결정 'Grafana 폐기'(`07-CONTEXT.md` D-05)) |
| 9 | ruff format --check · check | 클린 | 145 files already formatted · All checks passed! |
| 10 | `uv run pytest --no-header` | failed 0 | **`573 passed, 2 warnings in 5.29s`** |
| 11 | `make smoke` | PASS | `smoke: PASS` |
| 12 | `db_row_count.users` | ≥ 7(07-03) | **8**(events 1,223 · snapshots 9) |
| + | 표식 `probe-main-20260906` `/api/users/…/state` | 200 | **✅ 200** — 14:54 재기동 후에도 유지 |

## Task 2 — Codex 필수 리뷰 2회차 (adversarial-review, 범위 `20d5fa3` 이후 배포 전체, 11분 56초)

`review` 는 focus 텍스트 불가·07-03 에서 20분 정지 → `adversarial-review --base 20d5fa3 --scope branch` 로
실행(job `review-mtph1mo1-04bvk8`, 세션 `01a0758d-…`). 범위 차이: 07-01 = 작업 트리(Sentry 4파일),
07-03 1-d = 미완. 이번이 Phase 6 데모 + Phase 7 + Dockerfile `+3`(`COPY results/latency.json`) 전체.
Verdict `needs-attention`, 5건:

| # | 지적 | 분류 | 소유 | 처리 |
|---|---|---|---|---|
| C1 [high] `GET /api/candidates/onboarding` 익명 호출이 `user_key=NULL` `candidate_sets` 행을 무제한 저장 → 1GB 볼륨 고갈 가능 | 토론 → **인계** | serving(Phase 5) | 데모는 항상 user_key 전송, 고의 공격 전제·심사 2주. `PROGRESS.md` 미결에 1줄 |
| C2 [high] DB·모델 고장에도 `/health` 200 | **무시 유지**(07-01 F2 = walking skeleton 결정) | 운영 | 코드 0 조치 권고: UptimeRobot 키워드 `"status":"ok"` → `"db_ok":true`(사용자 대시보드) |
| C3 [medium] 철회(consent=0) 뒤 `POST /api/ratings` 가 ratings·events 재생성 | **필수 fix → 반영** | serving | `events_gate.consent_off_keys` 재사용, 403 · 저장·웨이크 없음. 익명 키(users 행 없음)는 201 유지(T2). 테스트 1개(`test_rating_after_consent_withdrawal_403_stores_nothing_no_wake`) |
| C4 [medium] `send_default_pii=False` 여도 요청 본문·query_string 이 Sentry 로 | **필수 fix → 반영** | app(Phase 7) | `sentry_sdk.init(... max_request_body_size="never")` 1줄 + 테스트 단정 1줄 |
| C5 [medium] `latency.json` 전역 p95 79.5 가 pop·cf 행에도 표시, `git_sha 8e5172b` ≠ 배포 HEAD | 토론 → **문구 정정 인계** | report | 코드 주석이 이미 "셀 혼합 전역 p95"(D-11). Phase 8 draft 에 "variant 공통 전역 p95" 1구절, 화면 열 라벨은 인계 |

사용자 회신: **"승인합니다"**(권고안 = fix C3 C4 / push ok). UptimeRobot 가동률·간격 수치는 회신에 없어
상태 페이지 200(게이트 7)으로 갈음 — 대시보드 "Up · 5분" 육안 확인은 사용자 몫으로 남긴다.
반영 후 재게이트: ruff 클린 · **`574 passed`** · `smoke: PASS`. 파일 줄수 `ratings_api.py` 84 · `server.py` 62(≤65 가드).

## Task 3 — 캡처 6장 + QR → draft 2곳

- `shoot.py`(스크래치패드 `…/845b6bda-…/scratchpad/shoot.py`, repo 밖) — `walk.py` 셀렉터 계승,
  `?source=api&capture=1`, `device_scale_factor=2`, **`.phone` 요소(390×844+베젤) 스크린샷**.
  결과: 6장 451~587KB · `console_errors []` · `page_errors []` · `api_non2xx []`.
  홈 rows `anchor_1004·persona_shelf·trending·fresh_picks` → 완독 후 `after_completion` 선두 →
  재설정 후 상위 5권 변경(`titles_changed true`).
- QR: `uv run --with "qrcode[pil]"` → `p5_qr.png` 896B. `git status -- pyproject.toml uv.lock` 빈 출력.
- repo 밖 확인: `git status --short -- report/figures` 0 · ls-files grep(예외 후) 0.
- `report/draft.md`: §5-3 `[Phase 7]` → URL·QR·그림 6장 파일명(0/1 유지 — L3 범례) · §3-3 배포 실측 1줄
  (다운 5~15초·볼륨 부착 30~40초·SQLite 유지). `git diff --stat` = `3 ++-`(2곳).

## Task 4 — 기록 4곳 + 커밋·push

- `../PROGRESS.md`: 결정 로그 **3행**(배포 완료·URL·다운타임 / DEPLOY-04 폐기 확정 / 데모 버그 수정) + 미결 5(계정) 취소선·해소.
- 개발일지 `### D85.`(6요소, 12줄) — 플랜의 D81 은 06-08 이, D82~84 는 리뷰 세션이 선점.
- `.planning/STATE.md`: frontmatter·Current focus·Status 갱신(Day 게이트 2·4 는 07-02·07-03 에서 ✅).
- 아키텍처 01 §2-1 L74: "수십 초 다운" → "약 5~15초 다운 · 볼륨 최초 부착 시 30~40초 — 2026-09-06 실측" (grep 0).
- 커밋 3(`769d69e` fix(demo) · `2f0bb50` fix(serving,app) · `8455408` docs(07-04)) → **push 16:33:37 KST**
  `ad8cd4a..8455408`. 다른 세션 미커밋(Makefile·results·scripts·tests/data 리뷰 작업)은 동반되지 않음.

### push 후 검증
| 검사 | 실측 |
|---|---|
| push → Active | push **16:33:37** → `/health` 5초 폴링: 16:34:07 `200 uptime 821` → 16:34:13 **`000`**(1표본) → 16:34:23 `200 uptime 6` = **Active 16:34:23**(46초, 레이어 캐시·src 변경만). 다운 1표본 ≈5~10초 — 07-02 실측(5~15초)과 동일 |
| `/health` | `hybrid_div_v1` · `db_ok true` · `artifacts_loaded_at 07:34:16Z` · users **9** |
| **표식 `probe-main-20260906` `/state`** | **200** — push 재배포 뒤 이름 기준 유지 → DEPLOY-01 후반(볼륨 영구성) 완결 |
| `/metrics` | 404 |
| 배포본 `d8_showcase.js` | `data-act="startFresh"` 1건 — 새 코드 반영 |
| `fresh_check.py`(배포 URL, api) | **PASS** — 키 변경 · S0 · 새 홈 `after_completion` 없음 · 이전 키 `/state` 200 · 콘솔 에러 0 |
| C3 실측(`probe-c3-20260906`) | `POST /api/preferences` 201 → `DELETE …/personalization` 200(`consent false`) → **`POST /api/ratings` 403 `consent withdrawn`** · `/state.consent false` |
| C4 | 코드 반영(`max_request_body_size="never"`) — Sentry 이벤트 0 이라 실측 불가, 테스트 단정으로 갈음 |


## 이탈 (플랜과 달랐던 점)

1. **코드 0 → 코드 커밋 2.** ① 사용자 지시(16:1x, "신규 유저로 체험하기" 이전 데이터 잔존) — `d8_showcase.js` 버튼이
   `nav` 로 이동만 해 `localStorage millie_user_key`·메모리 상태가 유지되던 것. 프리셋의 `resetAll` 을 재사용하는
   `startFresh` 로 교체(3파일 +10/−3). ralph 루프로 처리: PRD 3 스토리 → Playwright api·mock PASS → architect
   APPROVE(7항목) → deslop(중복 주석·도달불가 분기 삭제) → 회귀 재검증 PASS. ② Codex C3·C4(위 표).
   `must_not_touch`(`src/**`·`demo/**`) 위반이지만 둘 다 사용자 명시 승인.
2. **개발일지 D81 → D85.** 07-03 인계의 D82 도 리뷰 세션이 먼저 썼다.
3. **DEPLOY-03 검사 예외** `demo/assets/brand/millie-mark.png`(07-03 인계 그대로).
4. **UptimeRobot 가동률 수치 미수신** — 사용자 회신이 "승인합니다" 한 줄. 상태 페이지 200 으로 갈음.
5. **표식 이름 확인이 push 전에 먼저 성립** — 다른 세션의 16:19 push(`ad8cd4a`) 재배포 뒤 `probe-main-20260906` state 200.
6. Codex `review` 대신 `adversarial-review`(focus 지원). 07-01 무시 항목 F2 재등장 → 무시 유지.

## 운영 인계 (배포 02 §5~§8 을 현재 사실로)

- **심사 기간 점검(§5):** UptimeRobot 알림(Keyword `"status":"ok"`, 5분) → Railway Deployments 로그 → 아래 장애표.
  Railway Usage 주 1회($15 하드 캡). Day 5 이후 코드 변경 금지. `FREEZE_BOOK_STATS=1` 은 필요 시 Variables 추가.
  권고: 키워드를 `"db_ok":true` 로 바꾸면 Codex C2(DB 고장 시 200)를 코드 없이 감시.
- **백업 사실 정정:** §5 의 `GET /api/admin/export` 는 **미구현**, `METRICS_TOKEN` 도 없다(D-05 폐기).
  백업 수단은 Railway 볼륨(Backups 탭)뿐. 유실 시 데모 상태만 초기화, PDF 숫자(`results/`)는 무관.
- **롤백(§6):** Railway → Deployments → 직전 성공 배포 → **Redeploy**(1클릭). 코드 롤백은 `git revert <sha> && git push`.
- **장애 대응(§7) 상위 4줄:** `ModuleNotFoundError: millie_rec` → 두 번째 `uv sync` · `unable to open database file` → 볼륨/`DATA_DIR` ·
  헬스체크 반복 실패 → `${PORT}` · 표지 안 뜸 → 밀리 CDN 핫링크(플레이스홀더 정상, 다운로드 금지).
- **철거(§8):** 심사 결과 통보 +7일 → Railway 서비스 Delete(볼륨 포함) → Sentry·UptimeRobot 정리 → PROGRESS 종료 기록. 캘린더 알림은 사용자 몫.
- **Codex 인계(C1·C5):** `PROGRESS.md` 미결 참조. C1 은 Phase 8 이후 `onboarding_api.py`(익명 호출 미저장 또는 TTL), C5 는 draft 문구 → Phase 8 'PDF 제출물' 08-01 에서 draft §4-3 에 'variant 공통 전역 p95' 반영 완료.
- **Sentry 확인(Phase 8 'PDF 제출물' 제출 전 점검, `.planning/phases/08-pdf/08-04-SUMMARY.md` · 결정 D-17 'Sentry 정상 동작 확인'(`.planning/phases/08-pdf/08-CONTEXT.md`)):** 미확인 — 배포본 예외 이벤트 0 건, 사용자 터미널 probe 미실행(사용자 선택, 2026-09-06 20:3x KST). 확인이 필요해지면 사용자 터미널에서 DSN 인라인 probe 1 회. DSN 은 기록하지 않는다.
- **UptimeRobot 키워드(Codex C2 권고):** `"status":"ok"` 유지 — 사용자 결정(2026-09-06 20:3x KST), 키워드 변경 없음. `FREEZE_BOOK_STATS`: 미설정 유지(사용자 결정) — 화면 `book_stats` 가 이벤트로 변할 수 있어 `PROGRESS.md` 미결 1 행으로 인계.

## Self-Check: PASSED
- 게이트 12행 · 캡처 7장 · draft 마커 0 · 기록 4곳 grep 확인 · 커밋 3 · push 완료 · 위 "push 후 검증" 절 참조.
