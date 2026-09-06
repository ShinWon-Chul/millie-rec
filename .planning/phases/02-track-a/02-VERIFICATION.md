---
phase: 02-track-a
verified: 2026-09-05T06:37:12Z
status: passed
score: 5/5 roadmap success criteria verified (+ EVAL-07 Should complete)
overrides_applied: 0
---

# Phase 2 'Track A 정량 평가 기반'(.planning/ROADMAP.md) Verification Report

**Phase Goal:** PDF 비교표의 유일한 숫자 출처인 `results/`가 생기고, 3지표·온보딩 시뮬레이션·누수 방지가 테스트로 고정되어 이후 variant가 추가될 때마다 행만 늘면 된다.
**Verified:** 2026-09-05T06:37:12Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria 1–5)

| # | Truth | Status | Evidence |
|---|---|---|---|
| 1 | `make data && make eval` → `results/latest.csv`에 `pop` 행, `eval_<ts>.json`에 `split_mode`·`n_users`·`seed`·`sha` | ✓ VERIFIED | `results/latest.csv` = `pop,0.063,0.054,0.764,2000,holdout,pop_v1`; `results/eval_20260905_0626.json`에 `split_mode="holdout"`·`n_users={"n0":2000,"n20":1990}`·`seed=42`·`git_sha="8e5172b"` 전부 존재(직접 `cat` 확인) |
| 2 | Recall@20·NDCG@10·ILD@10 손계산 테스트 + "학습에 본 아이템 제외" 테스트 통과 | ✓ VERIFIED | `src/millie_rec/evaluation/metrics.py` 읽음 — Recall 분모 `len(relevant)`(min(K,·) 아님), NDCG IDCG=`min(len(relevant),k)`, ILD 상삼각 cosine 평균, 0벡터→거리1. `harness.py`가 `user.seen & relevant`·`returned_seen`에서 `ValueError`. `uv run pytest tests/evaluation --no-header` = 20 passed(경계 2건 포함) |
| 3 | 온보딩 시뮬레이션이 유저별 5권만 `explicit_seeds`로 노출, 미선택 책은 negative 아님 | ✓ VERIFIED | `data/onboarding.py::mask_onboarding` 읽음 — `UserState`에 negative 필드 없음(`__dataclass_fields__` 5개 고정), seeds ⊂ `is_positive(train)`. `tests/data/test_onboarding.py` 6건 통과(`UserState.__dataclass_fields__` 단정 포함) |
| 4 | n=0(온보딩 5권)과 n≥k(행동 축적) 지표가 별도 표로 출력 | ✓ VERIFIED | `results/latest_states.csv` = `pop,n0,0.063,0.054,0.764,2000` / `pop,n20,0.080,0.087,0.746,1990` — 상태별 `n_users` 분리(2000 vs 1990) 실측 확인 |
| 5 | `uv run pytest -q`·`make smoke` PASS, `pop` 주입 후 `/api/recommend`가 `fallback_level=0` | ✓ VERIFIED | 전체 스위트 `uv run pytest --no-header` → **171 passed, 2 skipped, 0 failed**(직접 재실행 확인). 서버를 포트 8021에 직접 기동해 `curl "/api/recommend?seeds=1,2,3&k=5"` → `fallback_level=0`·`model_version=pop_v1`·`items` 5개(`book_id ∈ {4,17,5,20,18}`, seeds `{1,2,3}` 제외 확인)·`rows[0].row_id="trending"`; `seeds` 없는 요청 → `fallback_level=3`·`model_version=fallback_v1`(Phase 1 회귀 없음) |

**Score:** 5/5 truths verified

### Should 꼬리 — EVAL-07

| 항목 | 상태 | 근거 |
|---|---|---|
| `report/figures/eval_bar.png` | ✓ 존재 | 38,767 바이트(직접 `ls` 확인), `tests/evaluation/test_figures.py` 2건이 `evaluation` 20건 안에 포함, `evaluation/__init__.py`의 `plot_eval_bar` 공개 |

### Required Artifacts

| Artifact | Expected | Status | Details |
|---|---|---|---|
| `src/millie_rec/data/{goodbooks,load,split,onboarding,labels}.py` | Track A 데이터 준비 | ✓ VERIFIED | 존재·≤150줄(117/42/61/72/25)·star 의존 위반 0 |
| `src/millie_rec/retrieval/{popularity,content}.py` | pop 후보 생성 + ILD 벡터 | ✓ VERIFIED | 존재, 58/42줄, `content.py`에 `retrieve()` 없음(D-14 준수, Phase 4 몫) |
| `src/millie_rec/evaluation/{metrics,harness,report,figures}.py` | 3지표·하네스·writer·그림 | ✓ VERIFIED | 존재, 38/67/119/44줄, 코드 읽어 지표 정의·누수 검사 로직 확인 |
| `src/millie_rec/serving/compose.py` + `api.py` level 0 분기 | level 0 응답 조립 | ✓ VERIFIED | 존재(60/135줄), 라이브 curl로 level 0/level 3 응답 형태 확인 |
| `src/millie_rec/app/{pipeline,cli,export}.py` + `server.py` 주입 | 실행 진입점 + 서버 배선 | ✓ VERIFIED | 존재(55/128/41/18줄), 라이브 서버가 `pipelines=build_pipelines()`로 pop 로드 확인 |
| `results/latest.csv`·`latest_states.csv`·`eval_20260905_0626.json` | PDF 숫자 출처 | ✓ VERIFIED | 파일 존재, 내용 직접 `cat` 확인(위 표) |
| `artifacts/serving/eval_table.json`·`artifacts/popularity.json` | 쇼케이스·서버 입력 | ✓ VERIFIED | 존재(447바이트/15KB), 서버가 실제로 이 아티팩트를 로드해 level 0을 낸다(라이브 확인) |
| `report/figures/eval_bar.png` | EVAL-07 그림 | ✓ VERIFIED | 존재, 38,767바이트 |

### Key Link Verification

| From | To | Via | Status | Details |
|---|---|---|---|---|
| `data/onboarding.py` | `data/labels.py` | `is_positive(train)`로 seeds 후보 제한 | ✓ WIRED | 코드에 `from millie_rec.data.labels import is_positive` + `pos_by_user` 사용 확인 |
| `data/split.py` | `contracts.py` | `default_rng(SEED)`·`COL_USER`·`COL_TS` | ✓ WIRED | 코드 확인, `_holdout`이 `np.random.default_rng(seed)` 사용 |
| `retrieval/popularity.py` | `contracts.py` | `Candidate`·`UserState.seen` 제외 | ✓ WIRED | `retrieve()`의 `if b in user.seen: continue` 확인, `tests/retrieval` 11건 통과 |
| `evaluation/harness.py` | `retrieval.ContentVectors`(Protocol 경유) | `vectors.vectors(ranked[:k_rank])`로 ILD 계산 | ✓ WIRED | `harness.py` L55 확인 |
| `serving/api.py` | `serving/compose.py` | `build_response`·`default_variant` import | ✓ WIRED | `api.py` L24 import, 라이브 응답으로 최종 확인 |
| `app/server.py` | `app/pipeline.py` | `pipelines=build_pipelines()` | ✓ WIRED | 라이브 서버 `/api/recommend?seeds=…` → `model_version=pop_v1`(build_pipelines가 `artifacts/popularity.json`을 실제로 로드) |
| `app/cli.py` | `evaluation.write_results`·`app/export.py` | `make eval` → `results/`+`artifacts/serving/eval_table.json` | ✓ WIRED | 파일 산출물 존재 + 내용 정합 확인(위 표) |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|---|---|---|---|---|
| `results/latest.csv` | `pop` 행 지표 | `evaluation.evaluate(PopPipeline, users, ContentVectors)` ← `PopularityRetriever.fit(train)` ← `data.split(load_interactions())` ← Goodbooks 실 CSV(5,976,479행 다운로드 확인) | Yes | ✓ FLOWING |
| `/api/recommend?seeds=…` items | `PopPipeline.recommend` | `PopularityRetriever.load(artifacts/popularity.json)`(실제 파일, 1,000항목) | Yes | ✓ FLOWING |
| `artifacts/serving/eval_table.json` | `rows`/`meta` | `app/export.py`가 `results/latest.csv`를 csv.DictReader로 그대로 복사(재계산 없음, D-09 의도적) | Yes(원본이 실측이므로) | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|---|---|---|---|
| level 0 응답(seeds 있음) | `curl "localhost:8021/api/recommend?seeds=1,2,3&k=5"` | `fallback_level=0`·`model_version=pop_v1`·items 5개(seeds 제외)·`rows[0].row_id=trending` | ✓ PASS |
| 익명 요청(level 3 회귀 없음) | `curl "localhost:8021/api/recommend?k=3"` | `fallback_level=3`·`model_version=fallback_v1`·`items=[]` | ✓ PASS |
| `/health` | `curl "localhost:8021/health"` | `status=ok`·`db_ok=true`·`model_version=null`(Phase 5로 의도적 연기, 계약 optional) | ✓ PASS |
| 전체 테스트 스위트 | `uv run pytest --no-header` | `171 passed, 2 skipped, 0 failed` | ✓ PASS |
| lint | `uv run ruff format --check . && uv run ruff check .` | `60 files already formatted` / `All checks passed!` | ✓ PASS |
| star 의존 위반 검사 | `grep -rn "millie_rec\.(다른 슬라이스)" src/millie_rec/{data,retrieval,evaluation,serving}/` | 4개 슬라이스 전부 출력 없음 | ✓ PASS |

### Requirements Coverage

| Requirement | 제목 | Source Plan | Status | Evidence |
|---|---|---|---|---|
| **EVAL-01** | Goodbooks-10k 멱등 다운로드 | 02-01, 02-06 | ✓ SATISFIED | `data/goodbooks.py::download_goodbooks`(`exists() and st_size>0` 건너뜀) + 실측: 1회차 15.2s 다운로드, 2회차 2.3s `downloaded` 로그 0줄(02-06-SUMMARY) |
| **EVAL-02** | `ts` 없으면 random holdout·`split_mode` 기록 | 02-01 | ✓ SATISFIED | `split.py` 코드 확인(위), `results/latest.csv`·`eval_*.json` 모두 `split_mode=holdout`, `grep -c "temporal split" report/draft.md` = 0(거짓 표기 금지 준수, 02-06-SUMMARY) |
| **EVAL-03** | 온보딩 5권 마스킹·미선택 ≠ 부정 신호 | 02-01 | ✓ SATISFIED | `onboarding.py` 코드 확인 — `UserState`에 negative 구조 없음, `tests/data/test_onboarding.py::test_user_state_has_no_negative_structure` 존재·통과 |
| **EVAL-04** | 3지표 순수 함수·손계산 테스트·누수 방지 | 02-02, 02-03 | ✓ SATISFIED | `metrics.py`·`harness.py` 코드 확인(위), `tests/evaluation` 20 passed, `tests/retrieval` 11 passed(`retrieve`가 `user.seen` 제외) |
| **EVAL-05** | `make eval` 4행 + `split_mode` 기록 | 02-03, 02-05, 02-06 | ✓ SATISFIED(Phase 2 몫) | `latest.csv`에 `pop` 1행 + 4행 구조(`write_results`가 `VARIANTS` 순 정렬, 미지 variant `ValueError`) + `eval_*.json`에 `split_mode`·`n_users`·`seed`·`git_sha` 전부 존재. 4행 완성은 ROADMAP상 Phase 4 몫(계획대로) |
| **EVAL-06** | n=0 vs n≥k 지표 분리 출력 | 02-03, 02-06 | ✓ SATISFIED | `latest_states.csv` 2행(n0/n20), 상태별 `n_users` 분리(2000/1990) 실측 |
| **EVAL-07** | 비교 막대그래프 `eval_bar.png` | 02-06 | ✓ SATISFIED (Should) | `report/figures/eval_bar.png` 38,767바이트, `plot_eval_bar` 공개, 테스트 2건 |

**ORPHANED 검사:** `.planning/REQUIREMENTS.md`의 Phase 2 매핑(EVAL-01~07) 전부 위 표에 대응됨 — orphaned 없음.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|---|---|---|---|---|
| (없음) | — | TODO/FIXME/placeholder/스텁 잔존 0건(`grep -rn "TODO\|FIXME\|PLACEHOLDER\|스텁" src/millie_rec/{data,retrieval,evaluation,serving,app}` 결과 없음, SUMMARY의 "Known Stubs: 없음" 6건과 일치) | — | — |

### TDD Gate Compliance (Plan 01–04)

| Plan | RED 증거 | GREEN 증거 | 판정 |
|---|---|---|---|
| 02-01 (data) | `19 failed, 1 passed`, 실패 전부 `AssertionError`/`Failed: DID NOT RAISE`, `ImportError` 등 0건 | `20 passed` | ✓ 정직한 RED→GREEN |
| 02-02 (retrieval) | `11 failed`, `AssertionError` 12회, 금지 오류 0건 | `11 passed` | ✓ 정직한 RED→GREEN |
| 02-03 (evaluation) | `18 failed`(`AssertionError` 16 + `DID NOT RAISE` 2), 금지 오류 0건 | `18 passed` | ✓ 정직한 RED→GREEN |
| 02-04 (serving level0) | `4 failed, 3 passed`(3건은 Phase 1 회귀 방지용 의도된 사전 통과), 실패 전부 `AssertionError` | `7 passed` | ✓ 정직한 RED→GREEN |

커밋 게이트는 D-18(커밋 없음, 사용자 승인 대기)에 따라 전 플랜에서 생략 — 프로젝트 정책과 일치하며 gap 아님(project_facts 확인).

### Human Verification Required

없음. 모든 Success Criteria·Requirements가 코드 읽기 + 라이브 서버 curl + 전체 테스트 재실행으로 프로그램적으로 확인되었다. `report/figures/eval_bar.png`의 시각적 품질은 PDF 조판 단계(Phase 8 'PDF 제출물')에서 사람이 보는 것으로 충분하며, 파일 존재·크기·PNG 시그니처는 이미 자동 확인됨(Should 항목, 비차단).

### Gaps Summary

없음. Phase 2 'Track A 정량 평가 기반'의 ROADMAP Success Criteria 5개 전부와 EVAL-01~07(Must 6 + Should 1) 전부가 코드·라이브 서버·테스트 재실행으로 검증되었다. `contracts.py`·`serving/schemas.py` freeze는 유지됨(diff가 Phase 1 산출물 1줄 추가로만 확인, Phase 2 플랜의 변경 아님). star 의존 위반 0, 파일당 150줄 상한 준수, 의존성 추가 0, 전체 테스트 171 passed/2 skipped/0 failed, ruff 클린.

---

_Verified: 2026-09-05T06:37:12Z_
_Verifier: Claude (gsd-verifier)_
