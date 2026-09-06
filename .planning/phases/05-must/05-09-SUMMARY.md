---
phase: 05-must
plan: 09
subsystem: serving
tags: [gate, bench, latency, codex-review, docs]
status: complete
requires: [05-06, 05-07, 05-08]
provides:
  - "results/latency.json p95 79.5ms (PDF 유일 지연 숫자)"
  - "report/draft.md §4-3 3행·§5-2·§5-3 갱신([Phase 5] 마커 0)"
  - "report/figures/p2_docs.png (/docs 엔드포인트 10개)"
  - "PROGRESS 결정 로그 4행 + 결과 스냅샷 · 개발일지 D78"
  - "Codex 리뷰 2건(일반·적대) 3분류 보고 — 사용자 승인 대기"
key-files:
  created: [results/latency.json, report/figures/p2_docs.png]
  modified: [report/draft.md, ../PROGRESS.md, ../.assets/개발일지/2026-09-06_Day2_Phase4_파이프라인과_freeze.md]
commits: 0   # no_commit — 사용자 승인 후 Phase 1~5 일괄
---

# Plan 05-09: wave 2 게이트 + Advisor 실측 + 문서 + Codex 리뷰 — SUMMARY

**한 줄:** wave 2 게이트 9행 통과(468 passed) → `make serve`(8000) + `bench --n-books 9447` → **p95 79.5ms**(p50 52.5·p99 113.7, level 0 500/500, hybrid_v1·hybrid_div_v1 250/250) → `/docs` 캡처 → draft 5곳·PROGRESS·개발일지 D78 → Codex 일반+적대 리뷰 17건을 필수 fix 7 / 토론 4 / 무시 4로 분류. 코드 변경 0, 커밋 0. 사용자 체크포인트 "approved"(Swagger 화면 공유로 확인, 2026-09-06).

## Task 1 — wave 2 게이트 (Advisor 1회, cascade.py 분할 후 재실행)
| 명령 | 결과 |
|---|---|
| `ls 05-0{6,7,8}-SUMMARY.md` | 3파일 |
| `codegraph sync .` | 갱신 |
| `ruff format --check . && ruff check .` | 125 files already formatted · All checks passed! |
| `uv run pytest --no-header` | **468 passed in 10.26s** (기준선 327 + wave 1 94 + wave 2 47) |
| `pytest tests/serving/test_smoke.py tests/app` | 42 passed |
| `make smoke` | smoke: PASS |
| `wc -l serving/*.py app/*.py` | 최대 150(`privacy_api.py`·`state.py`), `schemas.py` 277 예외 |
| `import dashboard_api, cascade` | ok |
| `grep prometheus\|sentry src/ pyproject.toml` | 출력 없음 |
| freeze(`contracts.py`·`schemas*.py`) | Phase 5 변경 0(`contracts.py`의 M 1줄 `MODEL_VERSION_FALLBACK`은 Phase 2 산출) |

1차 게이트에서 `cascade.py` 235줄 실패 → 05-06에 수정 브리프(`resolve.py`·`levels.py` 분할, 재-export) → 150/63/59줄로 재통과. wave 1 게이트에서도 `compose.py` 304줄 → `rows.py` 분할(144/144).

## Task 2 — 실측 (사용자 확인 완료)
- `results/latency.json`: p50 52.54 / **p95 79.52** / p99 113.73 ms · n 500 · users 50 · warmup 50 · k 40 · seed 42 · `fallback_levels {"0": 500}` · `variants {hybrid_v1: 250, hybrid_div_v1: 250}` · `catalog.n_books 9447` · git_sha 8e5172b · base_url http://localhost:8000. 1회 실행으로 게이트 통과(재실행 불필요).
- `curl /api/recommend?user_key=<bench 키>` → rows `continue_reading → anchor_4019 → persona_shelf → trending → fresh_picks` · level 0 · cell B · `hybrid_div_v1` · `latency_breakdown {feature 0.2, retrieval 8.4, ranking 11.4, rerank 2.2, pipeline 23.0, compose 49.0, total 73.3}`.
- `curl /api/showcase` → `split_mode holdout`, rows[0] pop 0.063/0.054/0.764 + `p95_ms 79.5`, `data_notice` 2트랙 문장. `/health` → `nearline_last_run` 채워짐, db_row_count users 50·snapshots 50·events 250·recommendations 553.
- `report/figures/p2_docs.png`(Playwright, 1280×2760): 엔드포인트 10개(`/health`·`/api/recommend`·meta·candidates·preferences·events·state·data·personalization·showcase).
- 관찰: 한 요청 73ms 중 `compose` 49ms(5행 조립·메타 조인·배지·추천 로그 INSERT)가 파이프라인 23ms보다 크다. 예산 안이라 보류. PDF 문장에 쓰지 않음.

## Task 3 — 문서
- `report/draft.md`: §4-3 응답 지연 행 → `로컬 bench p95 **79.5ms**(user_key 50·warmup 50·500요청·k 40, results/latency.json)` · 개인정보 행 → `GET/DELETE /api/users/{key}/*` + 테스트명 · 모니터링 행 → "설계만 — 관측(…)" · §5-2 완독 수 문장 → "데모 서버는 완독 이벤트 수(`n_completed`)…" · §5-3 "p95 실측 79.5ms(results/latency.json)". `grep -c "\[Phase 5\]"` → 0.
- `../PROGRESS.md` 결정 로그 4행(cascade.py 신설 · D-04 seeds 예외 · §9-3 목록 외 신설 6개 · catalog_categories 중복 허용) + 결과 스냅샷 p95 1줄. wave 4 신설 3개(ratings_api·dashboard_agg·after_completion)와 미결은 phase 종료 시 추가.
- 개발일지 **D78**(D77은 Phase 6 세션이 사용) — 6요소, `2026-09-06_Day2_Phase4_파이프라인과_freeze.md`.

## Codex 리뷰 3분류 (코드 변경 0 — 사용자 승인분만 반영)
**필수 fix 후보 7** — F1 consent=false·미존재 사용자 응답도 `recommendations`에 user_key·cell 기록(DELETE 무효화, 적대 high) → 익명 NULL 기록 · F2 `candidate_sets` DELETE 누락(적대 high) → `DELETE_TABLES` 추가 · F3 `levels.py` level 2·3의 `segment_popular`/`compose_rows`/`build_response`가 try 밖(적대 high) → 2 예외→3, 3 예외→빈 trending 200 · **F4 부스트(재설정 +0.15·세션 +0.1) 미적용**(일반 P1, 검증 확인: `state_weights`가 kwargs 무시 + 파이프라인 1인자 호출 → 랭킹·표시 모두 0; test_cascade는 가짜 weights로 통과) → `state_weights`가 kwargs ∨ `user.context` 플래그로 부스트 적용·재정규화, cascade가 플래그를 context에도 기록(Model 레인 상수 추가 `BOOST_*`, freeze 상수 무변경) · F5 Nearline이 `quality_flag` 이벤트도 상태 적용(일반 P1) → `WHERE quality_flag IS NULL` · F6 최신 스냅샷 tie(초 단위 created_at, 일반 P2) → `ORDER BY created_at DESC, rowid DESC` · F7 `resolve_user`가 feature 타이머 밖(D-09 위배, 일반 P2) → 타이머 시작점 이동.
**토론 4** — T1 consent=false `/preferences`가 categories·persona 저장(D-08 문서 확정 그대로, 유지 권장) · T2 `/events`가 consent=0 사용자 이벤트 저장·웨이크(차단 시 demo_api 150 초과 → 별도 파일) · T3 export에 `candidate_sets` 포함(UserDataOut 필드 추가 = 응답 freeze 위반, 보류 권장) · T4 export 단일 읽기 트랜잭션(1 worker, 보류).
**무시 4** — I1 IDOR/무인증(과제 범위 '안 함: 인증', 가명 키 데모; PDF 개인정보 행에 "실서비스: 세션 주체↔user_key 바인딩" 1문장) · I2 DELETE↔Nearline 선형화·상태 복사 락·이벤트 시간 순서(단일 worker·단일 Nearline 스레드, 설계만) · I3 BUDGET_MS 측정 시점(D-10 명시 결정 "타임아웃 없음 — 단순") · I4 `collect_millie` 샤딩·`itemknn` 캐시 키(Phase 2·3 산출물 freeze).

### 반영 결과 (사용자 승인 2026-09-06: 필수 7건 전부 + T2·T3·T4)
브리프 A(privacy: F2·T3·T4) · B(cascade: F1·F3·F6·F7·F4 serving) · C(blend: F4 Model) · D(nearline·events: F5·T2) 병렬 반영. 신설 `serving/events_gate.py`(50줄), `UserDataOut.candidate_sets` optional 필드(Advisor 직접, freeze 예외 — PROGRESS·개발일지 D79). `tests/ranking/test_blend.py::test_boost_flags_accepted_but_not_applied_in_phase4` → `test_boost_flags_applied_phase5` 교체 1건. 게이트 재실행: ruff 클린 · **513 passed** · `make smoke` PASS · 전 파일 ≤150. gsd-verifier 1차 `gaps_found`(F3·F4 재현) → 수정 후 재검증.

## wave 4 착수 판단
착수함(사용자 지시 "→ wave 4 Should"). 05-10·11·12 완료, 게이트 495 passed·smoke PASS·전 파일 ≤150. bench p95 재측정은 하지 않음(PDF 숫자 = 05-09 값 유지, 플랜 지침).

## 커밋
없음 — `git log --oneline -1` = `8e5172b`(불변). 사용자 승인 후 Phase 1~5 일괄.
