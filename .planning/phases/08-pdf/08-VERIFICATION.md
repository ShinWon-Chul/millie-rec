---
phase: 08-pdf
verified: 2026-09-06T21:30:00+09:00
status: passed
score: 4/4 must-haves verified (1 with recorded override)
overrides_applied: 1
overrides:
  - must_have: "제출 전 uv run pytest -q와 make smoke가 PASS 상태이고, FREEZE_BOOK_STATS=1이 설정되어 화면·PDF 숫자가 어긋나지 않는다 (ROADMAP Phase 8 성공 기준 4)"
    reason: "사용자가 Railway Variables FREEZE_BOOK_STATS=1을 설정하지 않고 유지하기로 명시적으로 결정함(2026-09-06 20:43 KST 회신 'FREEZE 미설정 유지'). PDF 숫자는 results/*.csv·json에서만 인용되므로(재측정 0회, 본 검증에서 24개 값 전수 대조 확인) 화면 book_stats 변동과 무관하다. 결정은 PROGRESS.md 미결 1행과 STATE.md Day 5 게이트 '⚠ FREEZE 미설정(PROGRESS 미결)' 표기로 기록되어 있어 유실되지 않았다."
    accepted_by: "user (밀리의서재 사전과제 담당자, 2026-09-06 20:43 KST 회신)"
    accepted_at: "2026-09-06T20:43:00+09:00"
---

# Phase 8: PDF 제출물 Verification Report

**Phase Goal:** 설계서의 주장과 앞 페이즈의 실측 숫자가 5페이지 안에 들어가고, 데모·서버가 죽어도 제출물이 완결된다. (`.planning/ROADMAP.md` "### Phase 8: PDF 제출물")
**Verified:** 2026-09-06T21:30:00+09:00
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|---|---|---|
| 1 | `report/draft.md`가 main 설계서 §2 페이지 매핑대로 P1~P5를 채우고, 모든 숫자가 `results/latest.csv`·`results/latency.json` 등에서만 인용되며 데이터 2트랙 각주가 붙어 있다 (**PDF-01**) | ✓ VERIFIED | 08-03-SUMMARY의 P1~P5 대조표 확인 + 직접 재실행한 숫자 대조: 비교표 8행(`results/latest_states.csv`) 전부 글자 단위 일치, 난이도 잔차 분야 평균 0.488(어린이)~0.505(에세이/시)·완독 확률 40.3%(오디오북)~79.0%(어린이)·7,796권·8분야가 `results/millie_difficulty.json`과 정확히 일치, 카탈로그 9,447권·82.5%가 `results/millie_coverage.csv`와 일치, p95 79.5ms가 `results/latency.json`과 일치. 2트랙 각주(L166 밀리 표본 vs 4장 Goodbooks-10k 각주) 확인 |
| 2 | ★3개(앵커·난이도·시간 가변 가중치)가 각각 박스로 존재하고, 필수 문장 7개·그림 4종(아키텍처·단계↔지표·비교 막대·데모 캡처)이 들어 있다 (**PDF-02**) | ✓ VERIFIED | `grep -c '^> ★ \*\*'` = 3 (앵커·난이도·시간 가변 가중치) · 필수 문장 7개 전부 본문 줄(표/제목 아님)에 각 1회 이상 존재(직접 grep 재확인: CTR 2·재설정≠초기화 1·요청마다 재계산 1·장애 격리 1·Two-Tower 2·LLM 1·미선택≠negative 1) · mermaid 펜스 4개(그림 1~4) + 그림 5(비교 막대 자리 표시, `eval_bar.png`) + 그림 6(데모 캡처 3×2, `p5_01~06.png`) — 그림 파일 7장 전부 `report/figures/`에 실존 확인 |
| 3 | `/pdf-check` 전 항목이 통과하고 5페이지 이내이며 `[재확인]` 마커가 0건이다 (**PDF-03**) | ✓ VERIFIED | 개발 과정·마커 grep(`Phase [0-9]\|Day [0-9]\|freeze\|구현 완료\|make serve\|\[Phase\|\[재확인\]`) = 0(직접 재확인) · 08-03 `/pdf-check` 판정 "제출 가능"(자수 항목 외 ❌ 0, 경고 1 = 표 셀 지표 라벨, 원고 결함 아님) · 사용자 Notion 내보내기 회신 "5장 이하"(08-04-SUMMARY, 2026-09-06 20:43 KST) — 규칙(`report.md`)의 최종 게이트 |
| 4 | 제출 전 `uv run pytest`와 `make smoke`가 PASS 상태이고, `FREEZE_BOOK_STATS=1`이 설정되어 화면·PDF 숫자가 어긋나지 않는다 (ROADMAP 성공 기준 4) | ✓ VERIFIED (override) | `uv run pytest --no-header` 재실행 → **590 passed**, 0 failed · `make smoke` 재실행 → **PASS**(3/3: `/health` 200 · `/` 200 · `/api/recommend` 200) · 배포본 `/health`·`https://stats.uptimerobot.com/20M6QwPo7z` 재확인 200. `FREEZE_BOOK_STATS=1` 미설정은 사용자 결정 — 위 overrides 참조 |

**Score:** 4/4 truths verified (1 with recorded override)

### Required Artifacts

| Artifact | Expected | Status | Details |
|---|---|---|---|
| `report/draft.md` | P1~P5 채운 제출 원고, H1 5·mermaid 4·★박스 3 | ✓ VERIFIED | 286줄. 직접 재계측 장별 한글 자수(전체/산문): 1장 1,127/591 · 2장 1,010/400 · 3장 1,091/406 · 4장 1,141/520 · 5장 1,588/1,059 — SUMMARY 08-03 claim(1,127/1,010/1,091/1,141/산문 1,059)과 사실상 일치, D-05 정정 상한(3장≤1,100·4장≤1,150·5장 산문≤1,100) 전부 충족 |
| `report/draft.pre-humanize.md` | humanize 직전 백업 | ✓ VERIFIED | 존재(286줄), draft.md와 구조·숫자·mermaid 동일(08-03 diff 근거 재확인 불필요 — 숫자 대조가 이미 draft.md 자체를 검증) |
| `report/notion_guide.md` | Notion 조판 안내 8절 | ✓ VERIFIED | 존재(38줄, H2 8개), 붙여넣기 순서·Mermaid 언어 전환·callout 3곳·그림 삽입·PDF 내보내기·장 수 회신 절차 전부 확인 |
| `report/demo_guide.md` §6 | 완독 후 추천 보는 법 (D-19) | ✓ VERIFIED | `## 6. 완독 후 추천 보는 법`(L188) 존재, append-only(190줄) |
| `report/figures/p5_01~06.png · p5_qr.png · eval_bar.png` | 캡처 6장 + QR + 비교 막대 | ✓ VERIFIED | 전부 실존(`ls` 확인), repo 밖(`.gitignore`) 유지 |
| `.planning/phases/07-deploy/07-04-SUMMARY.md` 운영 인계 | Sentry·UptimeRobot 결과 1줄씩 | ✓ VERIFIED | Sentry 확인(미확인, 사유 명시)·UptimeRobot 키워드 유지·Codex C5 반영 완료 문구 확인 |
| `../PROGRESS.md` | 결정 로그 1행 + 미결 2행 | ✓ VERIFIED | "PDF 원고 확정" 결정 행 + `FREEZE_BOOK_STATS=1 미설정`·`Sentry 이벤트 수신 미확인` 미결 2행 존재 |
| `../.assets/개발일지/2026-09-06_...D89` | 6요소 개발일지 항목 | ✓ VERIFIED | `### D89.` 존재, 기존 최댓값(88)+1과 일치, 신규 번호 중복 0(기존 D3·D63 중복은 phase 8 이전부터 존재하는 선행 결함, 본 phase 책임 아님) |
| `.planning/STATE.md` / `.planning/ROADMAP.md` | Day 5 게이트·Phase 8 Complete 기록 | ✓ VERIFIED | STATE Day 5 행 `⚠ FREEZE 미설정(PROGRESS 미결)` · ROADMAP Progress 표 `8. PDF 제출물 \| 4~5 \| 5/5 \| Complete` · 플랜 체크박스 5개 `[x]` 전부 확인 |

### Key Link Verification

| From | To | Via | Status | Details |
|---|---|---|---|---|
| `draft.md` §4-1 비교표 8행 | `results/latest_states.csv` | 숫자 24개 + n 값 | ✓ WIRED | 8행 × (recall@20, ndcg@10, ild@10, n_users) 전부 소수점까지 일치 확인 |
| `draft.md` §5-2 ★난이도 박스 | `results/millie_difficulty.json` | 분야 평균 범위·완독 확률 범위·모집단 | ✓ WIRED | `by_category` 8개 분야 min/max 직접 계산 → 0.4881~0.5047(반올림 0.488~0.505), 40.2965%~79.0113%(반올림 40.3%~79.0%), n=7,796 — 원고와 정확히 일치 |
| `draft.md` §5-3 본인 5권 표 | `report/demo_5books.md` | 시드·이웃 문자열 | ✓ WIRED | 정본은 제목/저자 열 분리(`싯다르타` / `헤르만 헤세 / 최유경 옮김`), 원고의 결합 표기 `싯다르타(최유경 옮김)`는 동명이서 구분을 위한 정당한 합성이며 원자료 왜곡 아님(구성요소 grep 확인) |
| `draft.md` §5-1 데모 URL·상태 페이지 | 배포된 서비스 | HTTP 200 | ✓ WIRED | 재요청 결과 `https://millie-rec-production.up.railway.app/#/` 200 · `/health` 200(`db_ok:true`) · `https://stats.uptimerobot.com/20M6QwPo7z` 200 |
| `draft.md` §5-1 완독 후 추천 클릭 경로 | 캡션 ②③④⑥ | 경로 단계 번호 | ✓ WIRED | `경로 ①`~`경로 ⑤` 표기가 캡션 표(L249, L251)에 그대로 연결됨 확인 |

### Data-Flow Trace (Level 4)

해당 없음 — 이 페이즈는 정적 문서(`report/*.md`)만 산출하며 런타임 데이터 흐름이 없다. 문서 안 숫자의 출처 추적은 위 Key Link Verification과 숫자 전수 대조로 대체.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|---|---|---|---|
| 전체 테스트 스위트 통과 | `uv run pytest --no-header` | 590 passed, 0 failed | ✓ PASS |
| 로컬 서빙 스모크 | `make smoke` | `/health` 200 · `/` 200 · `/api/recommend` 200 → PASS | ✓ PASS |
| 배포본 데모 URL 응답 | `curl .../#/ ` | 200 | ✓ PASS |
| 배포본 헬스체크 | `curl .../health` | `{"status":"ok",...,"db_ok":true}` | ✓ PASS |
| 가동 감시 상태 페이지 | `curl stats.uptimerobot.com/...` | 200 | ✓ PASS |
| 저작권 게이트(정정 패턴) | `git ls-files \| grep -iE '\.(pdf\|png\|jpe?g)$\|(^\|/)\.?assets(/\|$)' \| grep -v millie-mark.png` | 빈 출력 | ✓ PASS |
| 원고 장/그림/★박스 구조 | `grep -c` H1·mermaid·★ | 5 / 4 / 3 | ✓ PASS |
| 개발 과정 마커 잔존 | `grep -cE 'Phase [0-9]\|Day [0-9]\|freeze\|...'` | 0 | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|---|---|---|---|---|
| PDF-01 | 08-01, 08-03 | `draft.md` P1~P5·숫자는 `results/`만 | ✓ SATISFIED | Truth 1, 08-03 대조표 + 본 검증 숫자 재대조 |
| PDF-02 | 08-01, 08-02 | ★3개 박스·필수 문장 7개·그림 4종 | ✓ SATISFIED | Truth 2 |
| PDF-03 | 08-03, 08-04, 08-05 | `/pdf-check` 통과·5페이지 이내·기한 내 제출 | ✓ SATISFIED (기한 09-08 22:00 KST는 미도래, 원고 자체는 확정·5장 이하 확인 완료) | Truth 3 |

REQUIREMENTS.md 트래커 상 세 항목의 `Status` 열이 여전히 "Pending"으로 남아 있다(코드 근거는 충족되었으나 트래커 문서 자체가 08-05에서 갱신 대상에 포함되지 않았음) — 산출물 결함이 아니라 트래킹 문서 갱신 누락이며 후속 세션에서 1줄 정정하면 된다. 이 페이즈의 must_haves 어디에도 REQUIREMENTS.md 갱신이 명시되지 않았으므로 gap으로 分류하지 않는다.

**Orphaned requirements:** 없음 — REQUIREMENTS.md가 Phase 8에 매핑한 PDF-01·02·03 전부가 08-01~08-05 plans의 `requirements` 프런트매터에 나타난다.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|---|---|---|---|---|
| `report/draft.md` | L83 (측정 조건 각주) | `**...temporal split(시간순 분할)**로` — 굵게 닫는 `**` 뒤 조사가 바로 붙어 Notion 렌더에서 굵게가 풀릴 가능성 | ℹ️ Info | 08-01·08-03에서 이미 인지되어 08-04 조판 확인 항목으로 인계됨. 텍스트 내용은 정확, 시각적 렌더링만의 문제로 제출 전 Notion에서 육안 확인 필요 |
| `report/figures/eval_bar.png` | — | hybrid_div의 ild@10 라벨 `0.684`가 범례 텍스트와 시각적으로 겹침(08-01-SUMMARY 기록) | ℹ️ Info | 숫자 자체는 정확(`results/latest.csv`와 일치 확인), 이미지 재생성 없이 Notion 삽입 폭 조정으로 해결 가능한 조판 이슈 |

두 항목 모두 텍스트/숫자 정확성에는 영향이 없는 조판(레이아웃) 수준의 관찰이며, 이미 이전 SUMMARY에서 인지되어 사용자의 Notion 조판 단계로 인계된 상태다. 코드/문서 결함(blocker)은 발견되지 않았다.

### Human Verification Required

없음. 사용자는 이미 Notion → PDF 내보내기를 수행하고 장 수("5장 이하")·FREEZE_BOOK_STATS·UptimeRobot 키워드·Sentry·repo 링크 5건을 회신했다(08-04-SUMMARY, 2026-09-06 20:43 KST). 남은 것은 09-08 22:00 KST 제출 기한 전 실제 제출 행위뿐이며, 이는 미래 시점의 절차적 작업이지 이 페이즈의 산출물 검증 대상이 아니다.

### Gaps Summary

갭 없음. `report/draft.md`가 5개 플랜을 거쳐 완성되었고, 4개의 관찰된 진실(observable truths) 모두 코드베이스·배포본·정본 숫자 파일에 대한 독립 재검증으로 확인되었다. 유일한 미충족 항목(`FREEZE_BOOK_STATS=1` 미설정)은 사용자가 명시적으로 결정하고 `PROGRESS.md`·`STATE.md`에 정확히 기록한 의도된 편차이므로 override로 처리했다 — PDF 숫자는 `results/`에서만 인용되어(재측정 0회, 전수 대조 통과) 이 미설정과 무관하다.

---

*Verified: 2026-09-06T21:30:00+09:00*
*Verifier: Claude (gsd-verifier)*
