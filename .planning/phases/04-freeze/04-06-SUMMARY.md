---
phase: 04-freeze
plan: 06
status: complete
executed_by: Advisor + 사용자 게이트(최종 make millie 승인 · 본인 5권 제공, 2026-09-06 00:2x~00:5x)
executed_at: 2026-09-06
commits: 0   # no_commit — Phase 1~4 산출물 일괄, 사용자 승인 후
requirements: [REC-07, REC-08]
key-files:
  created:
    - report/demo_5books.md
  modified:
    - report/draft.md
    - .planning/STATE.md
    - .planning/REQUIREMENTS.md
    - .planning/phases/03-millie-catalog/03-06-SUMMARY.md
    - ../.assets/개발일지/2026-09-06_Day2_Phase4_파이프라인과_freeze.md
    - ../.assets/개발일지/2026-09-05_Day1_GSD_초기화와_계약_freeze.md
    - ../.claude/rules/serving.md
    - ../.assets/설계서/시스템 아키텍처, 기술 스택 및 배포(프론트, 백엔드 서빙)/01_시스템_아키텍처_기술스택_배포.md
    - ../.assets/설계서/데이터 소스/03_밀리_데이터_적재_트래킹.md
    - src/millie_rec/app/demo_cli.py      # 예외: 04-05 렌더링 버그 1줄(_cell) — 아래 Deviation
    - tests/app/test_demo_cli.py           # 예외: 위 버그 재현 테스트 1건
---

# Plan 04-06 SUMMARY — 5권 실측 · 최종 카탈로그 4 variant 판정 · 🧊 freeze 4종 선언

## Task 1 (사용자 게이트) — 통과
- **최종 스냅샷(Phase 3 03-06 Task 4, 사용자 승인 09-06 00:2x):** 진입 조건 `pgrep -f collect_millie` 빈 출력 · 재수집 로그 2개 SUMMARY(453+443=896, 실패 0). `cp data/id_map.csv <scratch>/id_map.final_before.csv` → `time make millie` **37s** → `_n_records 9447 · _n_badge_title 0 · titleless 4 · empty 129` · 이웃 게이트 통과(350,080 엣지·동일 카테고리 0.3564) · 벡터 9,447 = 책 수(이전 8,708≠9,450 해소) · id_map 접두 diff 빈 출력(9,453행·삭제 0) · 미수집 프론티어 0 · `uv run pytest --no-header` **326 passed, 0 failed**(`test_coverage_gate` 통과) · `make smoke` PASS. 03-06 SUMMARY `status: complete` + Task 4 절, 트래킹 03 §2 최종 행, 개발일지 D66 결과 줄, draft P3 수치(8,708→9,447 · 완독지수 82.5% · 동일 카테고리 0.356) 갱신·마커 제거.
- **5권 확정(`cli demo --find`, 사용자 확인 2회):** 『정의란 무엇인가』(마이클 샌델)·『채식주의자』(한강)는 카탈로그 미수집 → 사용자가 『죽음의 수용소에서』로 교체. 판본은 인기순 1위 전자책.

| book_id | 제목 | 저자 |
|---|---|---|
| 1012 | 싯다르타 | 헤르만 헤세 / 박병덕 옮김 |
| 2765 | 데미안 | 헤르만 헤세 / 전영애 옮김 |
| 1446 | 위버멘쉬 | 프리드리히 니체 / 어나니머스 옮김 |
| 1222 | 쇼펜하우어 인생수업: 한 번뿐인 삶 이렇게 살아라 | 쇼펜하우어 |
| 2292 | 빅터 프랭클의 죽음의 수용소에서 | 빅터프랭클, 이시형 옮김 |

**SEEDS=1012,2765,1446,1222,2292**

## Task 2 — `make demo` + 서버 4 variant 판정
- `make demo SEEDS=1012,2765,1446,1222,2292` → `report/demo_5books.md`(60줄). **실행 2회** — 1회차에서 『쇼펜하우어의 인생 수업』 저자 문자열 `지은이 | 아르투어 쇼펜하우어`의 `|`가 마크다운 열을 8→7로 깨뜨림(Plan 04-05 렌더링 버그). 재현 테스트 `test_row_escapes_pipe_inside_cells` RED(`10 == 7`) → `demo_cli._cell`(셀 안 `|`→`｜`) GREEN → 2회차. 2회차 stdout == 저장 파일 diff 0.
- grep: 좋아하셨다면 5 · HEADER 6 · `hybrid_div 상위 10` 1 · `alpha=1.0 beta=0.0 gamma=0.0` 1 · 병기 5 · 고정 문장 1 · 카탈로그에 없음/description/curator_note/배지 제목 0 · `resid_z`(플랜이 요구한 헤더 문구 `resid_z<−1(millie_index) 0권` 제외) 0 · 열 수 불일치 행 0. **플랜 acceptance 자기모순 1건:** `resid_z == 0` 패턴이 플랜 자신의 필수 헤더 문구에 걸림 → 헤더 제외로 판정(코드·플랜 수정 없음, 기록만).
- **최종 카탈로그 서버 4 variant(port 8011, seeds 5권, k=10):**

| variant | model_version | level | 상위 10 book_id | user_state_weights |
|---|---|---|---|---|
| pop | pop_v1 | 0 | 1004, 2081, 2843, 1060, 4320, 2204, 108, 621, 1355, 1467 | {1.0, 0.0, 0.0} |
| cf | cf_v1 | 0 | 3778, 2293, 1335, 2075, 966, 1007, 4070, 6157, 2076, 6989 | {1.0, 0.0, 0.0} |
| hybrid | hybrid_v1 | 0 | 3778, 2075, 1335, 2293, 6157, 1274, 4070, 5585, 966, 1050 | {1.0, 0.0, 0.0} |
| hybrid_div | hybrid_div_v1 | 0 | 3778, 2293, 1335, 5585, 6157, 1274, 966, 1144, 2081, 4070 | {1.0, 0.0, 0.0} |

교집합: pop∩cf 0 · pop∩hybrid 0 · pop∩hybrid_div 1 · cf∩hybrid 7 · cf∩hybrid_div 6 · hybrid∩hybrid_div 8 → **pairwise 동일 리스트 없음**. 기본(`model` 없음) = `hybrid_div_v1`. 4 리스트 title 전체에 배지 제목 0(『도슨트북』『읽던 지점 그대로 이어듣기』『무료』 없음).
- **관찰(코드 변경 없음, Phase 5 인계):** cf·hybrid 상위 10이 seed 책의 다른 판본·오디오북(『데미안』 ×4·『싯다르타』 ×3)으로 채워진다 — 콘텍츠 유사도 이웃의 구조적 한계. hybrid_div(MMR)가 일부 완화(『데미안』 2·『싯다르타』 3). 판본 dedup(동일 제목·저자 묶기)은 서빙 compose(Phase 5) 몫. draft §5-1에 사실대로 적었다.

## Task 3 — 🧊 freeze 4종 선언(3곳) + 문서
- **① 상수** `retrieval`: KNN_TOP 50 · POOL 200 · N_NEIGHBORS 20 / `ranking`: ALPHA0/BETA0/GAMMA0 0.6/0.3/0.1 · TAU 20 · ALPHA_FLOOR 0.2 · W_CF/W_CONTENT/W_POP 0.5/0.3/0.2 · W_GAP/W_GAP_POS/W_NCOMP_GAP −0.10/−0.20/−0.01 / `reranking`: LAMBDA_MMR 0.7 · MMR_POOL 50 · GUARD_RESID_Z −1.0 · GUARD_MIN_COMPLETED 3 · GUARD_TOP_N 10 · **②** `contracts.VARIANTS` (pop, cf, hybrid, hybrid_div) · **③** `artifacts/serving/*` 09-06 00:31~32 스냅샷(`make millie*` 재실행 금지) · **④** `serving/schemas*.py` 응답 형태(Day 1 D44 재확인).
- 기록: `.planning/STATE.md` Day 3 게이트 ✅ 🧊 + Current focus FREEZE 문구 + Blockers 재수집 해소 · 개발일지 D72(6요소) · `report/draft.md` §4-1 각주(상수 1구, 04-05) + §5-1 5권 실측·freeze 문장.
- `.planning/REQUIREMENTS.md` REC-01~08 `[x]` · 추적표 8행 Complete · `../.claude/rules/serving.md` `create_app(... weights=)` · 아키텍처 01 §3-3 `ranking/blend.py` 단계 규칙 → D-02 결합안.

## 전역 게이트(코드 변경 = `_cell` 1건만)
`uv run ruff format . && uv run ruff check .` 클린 · `uv run pytest --no-header` **327 passed, 0 failed** · `make smoke` PASS · `demo_cli.py` 149줄.

## Deviation
- 코드 변경 0 원칙의 예외 1건: 04-05 렌더링 버그(`|` 이스케이프) — 플랜 2-a "grep 실패 = 04-05 버그 → 고친 뒤 `make demo` 1회 다시" 규칙 적용. 모델·상수·응답 형태 무변경.
- GSD `code_review_gate`(`gsd-code-review` 스킬)는 REVIEW.md 커밋을 동반하므로 **생략**(사용자 지시: 커밋은 승인 후). 대안 = `/codex:review --scope working-tree`(선택, Model 레인).

커밋하지 않는다 — 작업 트리에 남기고 SUMMARY 에 변경 파일 목록을 적는다. 커밋은 Phase 1~4 산출물 일괄로 사용자 승인 후.
