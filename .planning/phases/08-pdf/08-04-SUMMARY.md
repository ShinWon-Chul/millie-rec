---
phase: 08-pdf
plan: 04
subsystem: report
tags: [pdf, 제출전점검, 체크포인트, sentry, freeze_book_stats]
requires:
  - "report/draft.md 최종 원고(08-03 humanize·/pdf-check 통과, 286줄)"
  - "report/notion_guide.md (사용자 조판 절차)"
provides:
  - "제출 전 자동 점검 10행 실측 기록"
  - "사용자 회신 5건 기록: 5장 이하 · FREEZE 미설정 유지 · 키워드 유지 · Sentry 미확인(probe 미실행) · repo 링크 안 넣음"
  - "5장 이내 확정 원고 report/draft.md(무변경)"
affects:
  - ".planning/phases/08-pdf/08-05-PLAN.md (기록·커밋 — 회신 값 인용, 저작권 게이트 grep 패턴 정정 반영)"
tech-stack:
  added: []
  patterns: []
key-files:
  created:
    - ".planning/phases/08-pdf/08-04-SUMMARY.md"
  modified: []
decisions:
  - "저작권 게이트 `git ls-files | grep -iE 'pdf|png|assets'`가 Phase 8 디렉터리명 `08-pdf`를 매치하는 오탐 발견 → 패턴을 확장자·경로 기준 `\\.(pdf|png|jpe?g)$|(^|/)\\.?assets(/|$)`로 정정(08-05 acceptance·CLAUDE.md 문구 동일 정정 대상)"
  - "커밋 없음 — 08-05에서 사용자 승인 후 일괄"
metrics:
  duration: "Task 1 약 3분(Advisor 직접 실행) · Task 2 사용자 회신 약 10분 · Task 3 약 2분"
  completed: 2026-09-06
---

# Phase 8 Plan 04: 제출 전 점검 · 사용자 확인 Summary

자동 점검 10행을 실측 원문으로 기록했다(전부 기대값 일치, 단 #7은 게이트 패턴 오탐으로 판정·정정). Task 2 체크포인트에서 사용자에게 5건을 한글로 묻고 회신을 기다린다. Task 1은 명령 실행·기록만이라 Advisor(orchestrator)가 직접 수행했다(CLAUDE.md 위임 규칙 "단일 명령은 직접").

## Task 1 — 자동 점검 10행 (2026-09-06 20:30 KST, `millie-rec/`)

| # | 검사 | 기대 | 실측 |
|---|---|---|---|
| 1 | `uv run pytest --no-header -q` | `failed` 없음 | exit 0 · **590 passed**(진행 표시 점 8×72+14). ⚠ `pyproject.toml` `addopts = "-q"`에 `-q`가 겹쳐 `-qq`가 되어 요약 줄이 출력되지 않음 → 요약 줄이 필요하면 `uv run pytest --no-header`로 실행(플랜 verify의 `tail -1 \| grep passed`는 경고 푸터를 잡음 — 플랜 명령 결함, 코드 무변경) |
| 2 | `make smoke \| tail -1` | `smoke: PASS` | `smoke: PASS` |
| 3 | `curl … /health` 코드 | `200` | `200` |
| 4 | `/health` 본문 `status db_ok model_version` | `ok True hybrid_div_v1` | `ok True hybrid_div_v1` |
| 5 | `curl … stats.uptimerobot.com/20M6QwPo7z` | `200` | `200` |
| 6 | 개발 과정 마커 grep (`[재확인]`·`[Phase`·`Phase N`·`Day N`·`freeze`·`구현 완료`·`make serve`) | `0` | `0` |
| 7 | `git ls-files \| grep -iE "pdf\|png\|assets" \| grep -v millie-mark` | 빈 출력 | **오탐 7건** — 전부 `.planning/phases/08-pdf/*.md`(플랜·CONTEXT·DISCUSSION-LOG, 이미 커밋된 GSD 문서). 디렉터리명 `08-pdf`가 `pdf`에 걸린 것. 정정 패턴 `git ls-files \| grep -iE '\.(pdf\|png\|jpe?g)$\|(^\|/)\.?assets(/\|$)' \| grep -v '^demo/assets/brand/millie-mark.png$'` → **빈 출력 ✅**(저작권 게이트 실질 통과) |
| 8 | URL 집계 `grep -oE 'https?://[^ )*]+' \| sort -u` | 2개 | `https://millie-rec-production.up.railway.app/#/` · `https://stats.uptimerobot.com/20M6QwPo7z` — 2개 |
| 9 | H1 · mermaid · `> ★` | `5` · `4` · `3` | `5` · `4` · `3` |
| 10 | `git status --short -- results report/figures src tests demo Makefile pyproject.toml` | 다른 세션 파일만 | ` M results/millie_edges_gate.json` · `?? results/review_coverage.csv` · `?? results/review_tuples_report.json` · `?? tests/data/test_millie_review_parse.py` · `?? tests/data/test_millie_reviews_build.py` · `?? tests/fixtures/millie_reviews/` — 전부 다른 세션 리뷰 작업, 이 플랜 변화 0 |

- `/pdf-check` 판정은 08-03-SUMMARY "3-d" 표 인용: **제출 가능**(자수 외 ❌ 0, 경고 1 = §2-1 표 셀 `NDCG@K`·`ILD@K` 라벨). 원고는 08-03 종료 후 무변경(humanize 산출 `final.md` 본문과 `report/draft.md` diff 0줄).
- README 데이터 출처 문구 확인(Task 2 질문 5용): L16 Goodbooks-10k(CC BY-SA 4.0, github.com/zygmuntz/goodbooks-10k) · L17 밀리 공개 도서 페이지 수집 범위 — 두 트랙 귀속 문구 있음.

## Task 2 — 사용자 확인 5건 (체크포인트, AskUserQuestion 한글 회신 · 2026-09-06 20:43 KST)

| # | 항목 | 회신 원문 | 시각 |
|---|---|---|---|
| 1 | Notion → PDF 장 수(결정 D-16 '분량 검증', .planning/phases/08-pdf/08-CONTEXT.md) | **"5장 이하"** | 2026-09-06 20:43 KST |
| 2 | Railway `FREEZE_BOOK_STATS=1`(결정 D-18) | **"FREEZE 미설정 유지"** | 2026-09-06 20:43 KST |
| 3 | UptimeRobot 키워드(Codex 2회차 C2, .planning/phases/07-deploy/07-04-SUMMARY.md) | **"키워드 유지"** (`"status":"ok"` 그대로) | 2026-09-06 20:43 KST |
| 4 | Sentry 이벤트(결정 D-17) | **"없습니다"** → probe 명령 제시 → **"실행 안 함 — 미확인으로 기록"** | 2026-09-06 20:43 KST |
| 5 | 공개 repo 링크(08-CONTEXT Deferred) | **"repo 링크 안 넣음"** | 2026-09-06 20:43 KST |

회신 전 Task 3 미착수(이 표 작성 시각 = Task 3 시작 시각).

## Task 3 — 회신 반영

**3-a 장 수(결정 D-16).** Notion PDF **5장 이하(사용자 회신 2026-09-06 20:43 KST)** → `report/draft.md` **확정**. 초과분 삭제 루프 0회, `report/draft.pre-humanize.md` 무변경(줄 수 차 0, 윤문 9줄 차이만).

**3-b Sentry(결정 D-17).** 대시보드 이벤트 0건 · probe 명령(사용자 터미널 인라인 DSN 1회, `capture_message('millie-rec probe')`)을 한글 안내와 함께 제시했으나 사용자가 **실행하지 않음** → **"Sentry: 미확인 — 배포본 이벤트 0건 · 사용자 probe 미실행(사용자 선택, 2026-09-06 20:43 KST)"**. Claude가 DSN을 받거나 실행한 경로 없음(DSN 호스트 문자열 grep 빈 출력). 08-05 PROGRESS 미결 1행 문구: `- [ ] Sentry 이벤트 수신 미확인 — 배포본 예외 0건·probe 미실행(08-04-SUMMARY Task 3-b). 확인 방법: 사용자 터미널에서 DSN 인라인 probe 1회 → Issues에 'millie-rec probe' 표시`.

**3-c 나머지 회신·분기.**
- **FREEZE 분기(ROADMAP Phase 8 성공 기준 4):** "미설정 유지" → ① 화면 `book_stats` 숫자가 이벤트로 변할 수 있음 — PDF 숫자(`results/`)는 무관 ② 08-05 PROGRESS 미결 1행 문구: `- [ ] Railway Variables FREEZE_BOOK_STATS=1 미설정 — 화면 book_stats가 이벤트로 변할 수 있음(ROADMAP Phase 8 성공 기준 4, 08-04-SUMMARY)` ③ STATE Day 5 게이트는 08-05에서 `✅`가 아닌 **`⚠ FREEZE 미설정(PROGRESS 미결)`** 표기.
- **키워드:** `"status":"ok"` 유지 — 사용자 결정. 07-04-SUMMARY 운영 인계에 1줄(08-05).
- **repo 링크:** 안 넣음 → 원고 무변경, URL 집계 기대치 2 유지.

**최종 grep 재확인 (2026-09-06 20:43 KST).** 마커 0 · DSN 호스트 문자열 grep 빈 출력 · `> ★` 3 · mermaid 4 · 비교표 8행 · 5권 표 5행 · URL 2 · `^코드: https://github.com/` 0 · `git diff --stat -- src` 빈 출력 · draft.md ↔ pre-humanize 줄 수 차 0 · 필수 문장 7 본문 줄 각 1(08-03 3-c 표와 동일 원고).

## 저작권 게이트 패턴 정정 (08-05·CLAUDE.md 인계)

Task 1 #7의 오탐 원인은 Phase 8 디렉터리명 `08-pdf`. 정정 패턴(실질 검사 결과 빈 출력):
```
git ls-files | grep -iE '\.(pdf|png|jpe?g)$|(^|/)\.?assets(/|$)' | grep -v '^demo/assets/brand/millie-mark.png$'
```
08-05 Task 3 acceptance와 `millie-rec/CLAUDE.md` Constraints "Copyright" 줄은 이 패턴으로 읽는다(플랜 결함 — 코드 무변경).

## 커밋

없음 — 08-05에서 사용자 승인 후 일괄(프로젝트 규칙 CLAUDE.md).
## Self-Check: PASSED

- `report/draft.md` — 존재(286줄), 08-03 종료 상태와 동일(확정)
- `.planning/phases/08-pdf/08-04-SUMMARY.md` — 존재, 점검표 10행·회신 표 5행·Sentry 결과 1줄·FREEZE 분기 지시
- Sentry DSN 호스트 문자열 재귀 grep(.planning/phases/08-pdf · report · ../PROGRESS.md · ../.assets/개발일지) — SUMMARY·report·PROGRESS·개발일지 빈 출력. 08-04-PLAN·08-05-PLAN 2파일만 매치되는데 그 줄은 플랜 자신의 grep 명령 문자열(자기 참조)이고 DSN 값이 아님 · DSN 값·환경변수 설정 명령 기록 없음(사용자 안내문의 `<붙여넣기>` 자리만)
- 커밋 해시 — 해당 없음(설계상 커밋 0, 08-05 일괄)
