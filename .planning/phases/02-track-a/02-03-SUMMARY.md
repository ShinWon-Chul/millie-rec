---
phase: 02-track-a
plan: 03
subsystem: evaluation
tags: [evaluation, metrics, harness, report, tdd, track-a]
requires:
  - src/millie_rec/contracts.py (K_RECALL·K_RANK·SEED·VARIANTS·MODEL_VERSION_SUFFIX·DIR_RESULTS·ROOT·UserState·ScoredItem·EvalResult·ItemVectors·Pipeline)
  - tests/conftest.py::item_vectors
provides:
  - "millie_rec.evaluation.recall_at_k / ndcg_at_k / ild_at_k — 3지표 순수 함수(evaluation.md 정의 그대로)"
  - "millie_rec.evaluation.evaluate(pipeline, users, vectors, *, k_recall, k_rank) -> EvalResult — 누수 단언 2개 포함"
  - "millie_rec.evaluation.EvalUser = tuple[UserState, frozenset[int]]"
  - "millie_rec.evaluation.RunMeta / write_results / git_sha / LATEST_FILE / STATES_FILE / LATEST_COLUMNS / STATES_COLUMNS"
affects:
  - "Plan 05 app/cli.py — from millie_rec.evaluation import RunMeta, evaluate, git_sha, write_results"
  - "Plan 06 evaluation/figures.py — 같은 __init__ 에 plot_eval_bar 추가"
  - "/eval-run 스킬 — results/latest.csv 헤더(D-06)를 읽는다"
tech-stack:
  added: []
  patterns:
    - "순수 함수 + numpy 벡터 연산(파이썬 루프는 k≤20 리스트와 유저 루프만)"
    - "pandas.to_csv(float_format=FLOAT_FORMAT) 로 소수 3자리 고정"
    - "frozen slots dataclass DTO(RunMeta) + dataclasses.asdict 로 json 직렬화"
key-files:
  created:
    - src/millie_rec/evaluation/metrics.py
    - src/millie_rec/evaluation/harness.py
    - src/millie_rec/evaluation/report.py
    - tests/evaluation/test_metrics.py
    - tests/evaluation/test_harness.py
    - tests/evaluation/test_report.py
  modified:
    - src/millie_rec/evaluation/__init__.py
decisions:
  - "D-08 유지: EvalResult 계약 무변경 — state·split_mode 는 RunMeta(실행 메타)로만 기록"
  - "D-09 유지: artifacts/serving/eval_table.json 은 evaluation 이 쓰지 않는다(app 소유, Plan 05)"
  - "harness 의 미사용 logging 로거를 넣지 않았다 — 예외를 숨기지 않는 설계라 로깅 지점이 없다"
metrics:
  duration: "약 25분"
  completed: 2026-09-05
---

# Phase 2 Plan 03: evaluation 슬라이스(3지표 · 하네스 · results writer) Summary

`evaluation` 슬라이스를 TDD 한 사이클로 완성했다 — `../.claude/rules/evaluation.md` 지표 정의를 손계산 테스트로 고정한 순수 함수 3개, `contracts.Pipeline` 하나를 평가하며 test 라벨 누수를 `ValueError` 로 차단하는 하네스, D-06~D-08 형식을 문자 단위로 지키는 `results/` writer.

**커밋하지 않는다 — 작업 트리에 남기고 SUMMARY 에 변경 파일 목록을 적는다** (결정 'D-18 커밋 없음'(.planning/phases/02-track-a/02-CONTEXT.md `<decisions>` "검증·완료 형태")).

## 변경 파일 목록 (`git status --short -- src/millie_rec/evaluation tests/evaluation`)

```
 M src/millie_rec/evaluation/__init__.py
?? src/millie_rec/evaluation/harness.py
?? src/millie_rec/evaluation/metrics.py
?? src/millie_rec/evaluation/report.py
?? tests/evaluation/            (test_metrics.py · test_harness.py · test_report.py)
```

커밋 해시 자리: **(no commit — 사용자 승인 대기)**. `git log --oneline | head -1` 은 플랜 전후 모두 `8e5172b`.

계획 밖 파일은 하나도 건드리지 않았다. `git diff --stat -- src/millie_rec/contracts.py src/millie_rec/serving results` 가 보여주는 `contracts.py`(`MODEL_VERSION_FALLBACK` 1줄)·`serving/__init__.py` 변경은 **Phase 1 '로컬 서빙 스켈레톤' 산출물**로, mtime 이 이 세션 시작(15:00) 이전인 11:12 다 — 이 플랜의 변경이 아니다. `results/` 는 `.gitkeep` 만으로 불변(모든 writer 테스트는 `tmp_path`).

## TDD Gate Compliance

커밋 게이트(`test(...)` → `feat(...)` 커밋)는 **D-18(커밋 없음)** 때문에 생략했다. 대체 증거는 아래 pytest 요약 줄 3개다.

### RED — `uv run pytest tests/evaluation --no-header`

```
FFFFFFFFFFFFFFFFFF                                                       [100%]
...
18 failed in 0.09s
```

전 18건이 단정 실패(`AssertionError` 16건 · `Failed: DID NOT RAISE ValueError` 2건). `ImportError`·`ModuleNotFoundError`·`SyntaxError`·`NameError`·`KeyError` 는 0건(`grep -cE` 확인). 스텁은 계획대로 시그니처·상수·`RunMeta` 필드를 완성형으로 두고 본문만 틀린 값(`-1.0` · 호출 없는 `EvalResult` · `"stub"` 파일)을 반환했다.

AssertionError 발췌 3건(지표·하네스·report 각 1건):

```
tests/evaluation/test_metrics.py::test_recall_hand_cases
>       assert recall_at_k([1, 2, 3], {2, 9}, 3) == 0.5
E       assert -1.0 == 0.5
E        +  where -1.0 = recall_at_k([1, 2, 3], {2, 9}, 3)

tests/evaluation/test_harness.py::test_evaluate_returns_eval_result_with_hand_computed_means
>       assert res.recall == pytest.approx(0.75)
E       assert -1.0 == 0.75 ± 7.5e-07

tests/evaluation/test_report.py::test_json_has_run_meta_keys_and_state_n_users
>       assert set(d) >= META_KEYS
E       AssertionError: assert set() >= {'created_at'...'k_rank', ...}
```

누수 게이트 2건은 `Failed: DID NOT RAISE ValueError`(스텁이 파이프라인을 호출조차 하지 않으므로 검사 자체가 없음):

```
tests/evaluation/test_harness.py::test_evaluate_raises_when_seen_overlaps_relevant
tests/evaluation/test_harness.py::test_evaluate_raises_when_pipeline_returns_seen_item
E       Failed: DID NOT RAISE ValueError
```

RED 시점 `uv run pytest tests/test_architecture.py --no-header` → `3 passed`.

### GREEN — `uv run pytest tests/evaluation --no-header`

```
..................                                                       [100%]
18 passed in 0.03s
```

첫 실행에 18/18 통과(손계산 값 수정 0건 — `0.6934264 = (0.3868528 + 1.0) / 2` 재검산 결과 계획값이 맞았다).

### REFACTOR — `uv run pytest tests/evaluation tests/test_architecture.py --no-header`

```
.....................                                                    [100%]
21 passed in 0.05s
```

`uv run ruff format --check src/millie_rec/evaluation tests/evaluation` → `7 files already formatted` · `uv run ruff check …` → `All checks passed!`

## Task별 결과

### Task 1 (RED) — 스텁 3 + 테스트 3

| 파일 | 테스트 수 | 3종 |
|---|---|---|
| `tests/evaluation/test_metrics.py` | 7 | 정확성 4 · 안전성(경계) 2 · 계약 1 |
| `tests/evaluation/test_harness.py` | 6 | 계약·정확성 1 · 안전성(누수) 5 |
| `tests/evaluation/test_report.py` | 5 | 계약 1 · 정확성 3 · 안전성 1 |

가짜 객체는 `tests/serving/test_smoke.py::_Boom` 패턴을 따랐다 — `_FakePipeline`(받은 `user` 를 `seen_users` 에 기록) · `_OneHot`(dim 100 직교 one-hot). `data`·`retrieval` 을 import 하지 않으므로 형제 플랜 01·02 와 완전히 독립이다.

### Task 2 (GREEN) — 구현

**지표 정의 문장 ↔ 코드 대응 3줄** (`../.claude/rules/evaluation.md` "지표 정의"):

| 규칙 문장 | 코드 |
|---|---|
| "Recall@K = \|L_u ∩ R_u\| / \|R_u\|. 분모를 min(\|R_u\|,K)로 바꾸지 않는다" | `metrics.py` `return hits / len(relevant)` — 전용 테스트 `test_recall_denominator_is_relevant_size_not_min_k` 가 `recall_at_k([1,2,3,4], {1,…,6}, 4) == 4/6` 로 고정 |
| "NDCG@K = DCG/IDCG. 이진 gain, 할인 1/log2(i+1), IDCG 는 min(\|R_u\|,K)개 기준" | `metrics.py` `dcg = sum(1.0 / math.log2(i + 2) …)` + `idcg = sum(… for i in range(min(len(relevant), k)))` |
| "ILD@K = 모든 쌍 (1 − cosine(v_i, v_j))의 평균" | `metrics.py` `unit @ unit.T` 상삼각(`np.triu_indices(n, k=1)`) 평균. 0 벡터는 `np.where(norms == 0, 1.0, norms)` 로 cosine 0 → 거리 1 |

**누수 차단(T-02-12)**: `harness.evaluate` 는 정답 `relevant` 를 로컬 변수로만 두고 `pipeline.recommend(user, k_recall)` 에 `UserState` 만 넘긴다. `raise ValueError` 2곳 — ① `user.seen & relevant` ≠ ∅(데이터 준비 누수) ② 파이프라인이 `seen` 아이템 반환(EVAL-04 "학습에 본 아이템 제외" 위반). 예외를 삼키지 않는다(숫자 출처).

**출력 정본(D-06~D-08)**: `latest.csv` 헤더 `variant,recall@20,ndcg@10,ild@10,n_users,split_mode,model_version` · `latest_states.csv` 헤더 `variant,state,recall@20,ndcg@10,ild@10,n_users` · `eval_<YYYYMMDD_HHMM>.json` 17키. 컬럼 이름은 `K_RECALL`·`K_RANK` 에서 f-string 으로 파생(상수와 헤더가 어긋날 수 없다). 정렬은 `VARIANTS` 순, 미지 variant 는 `ValueError`. `git_sha()` 는 argv 리스트 고정 + `shell=False`(기본) + `check=False` + `timeout=5` + `cwd=ROOT`, 실패·부재 시 `None`(T-02-14).

`grep -c "eval_table\|artifacts" src/millie_rec/evaluation/report.py` → `0` (D-09: `artifacts/serving/eval_table.json` 은 app 몫).

### Task 3 (REFACTOR) — 공개 표면 · ruff

`src/millie_rec/evaluation/__init__.py` 공개 이름 **12개**(`uv run python -c "import millie_rec.evaluation as e; print(len(e.__all__))"` → `12`): `LATEST_COLUMNS LATEST_FILE STATES_COLUMNS STATES_FILE EvalUser RunMeta evaluate git_sha ild_at_k ndcg_at_k recall_at_k write_results`. Plan 05 `app/cli.py` 와 Plan 06 `figures.py` 가 여기서만 가져간다.

`wc -l src/millie_rec/evaluation/*.py`:

```
      28 __init__.py
      67 harness.py
      38 metrics.py
     119 report.py
     252 total
```

전부 150줄 예산 안. ruff format 이 `__init__.py` 1파일만 재포맷(`__all__` 정렬), 나머지 6파일 무변경 — 행동 변경 0.

## Deviations from Plan

### Auto-fixed / 판단 항목

**1. [Rule 2 - 최소 변경] `harness.py` 에서 미사용 `logging` 로거 생략**
- **Found during:** Task 2
- **Issue:** 계획 코드 골격에 `import logging` + `log = logging.getLogger(__name__)` 가 있으나, 같은 골격의 docstring 이 "예외는 숨기지 않는다"이고 실제로 `log` 를 쓰는 지점이 없다.
- **Fix:** 두 줄을 넣지 않았다. 사용자 지시 ④("요청하지 않은 추가 금지")와 `../.claude/rules/simplicity.md`("추상화는 두 번째 사용에서")를 따랐다. 두 번째 사용이 생기면(예: Plan 05 cli 가 진행 로그를 원할 때) 그때 추가한다.
- **Files:** `src/millie_rec/evaluation/harness.py`
- **Commit:** (no commit — 사용자 승인 대기)

**2. [문서화] Task 2 수용 기준 `awk 'length > 100' … | wc -l` == 0 은 바이트 기준이라 한글 주석에서 오탐**
- **Found during:** Task 2 검증
- **Issue:** macOS `awk` 의 `length` 는 C 로케일에서 **바이트** 수를 세어 한글 docstring·주석이 있는 줄을 100 초과로 잡는다(실측 9줄). 실제 게이트인 ruff `E501` 은 **문자** 수 기준이다.
- **Fix:** 문자 기준 검사로 대체 — `uv run python` 으로 `len(line) > 100` 인 줄을 세어 **0줄** 확인, 그리고 정본 게이트 `uv run ruff check src/millie_rec/evaluation tests/evaluation` → `All checks passed!`(E501 포함). 코드 수정 없음.
- **Files:** 없음(검증 방법만 교체)
- **Commit:** (no commit)

**3. [표기] 플랜 `key_links` 의 `pattern: float_format="%.3f"` 은 상수 경유로 충족**
- **Found during:** Task 2
- **Issue:** `key_links` 정규식은 리터럴 `float_format="%.3f"` 을 기대하지만, 같은 플랜의 Task 2 코드 골격과 acceptance 기준(`grep -n 'FLOAT_FORMAT = "%.3f"'` 1행)은 모듈 상단 상수 `FLOAT_FORMAT` 을 쓰라고 지시한다.
- **Fix:** acceptance 기준(구체적 action)을 따랐다 — `FLOAT_FORMAT = "%.3f"` 상수 1곳 + `to_csv(..., float_format=FLOAT_FORMAT)` 2곳. `../.claude/rules/simplicity.md`("설정은 모듈 상단 대문자 상수")와도 일치.
- **Files:** `src/millie_rec/evaluation/report.py`
- **Commit:** (no commit)

### 손계산 수정

없음 — 계획의 모든 기대값(`0.5`, `0.3868528`, `2/3`, `0.75`, `0.6934264`)이 구현과 첫 실행에 일치했다. 테스트 단정을 고친 곳은 0곳.

### 사용자 지시와의 긴장

없음. ①(계획 밖 파일 무변경) ②(파일 하나 = 관심사 하나, 전부 ≤150줄, `__all__` 공개 표면) ③(함수 우선 · 상수 모듈 상단 · docstring 1줄 · 예외 계층 없이 `ValueError`) ④(추가 금지 — 위 Deviation 1)를 모두 지켰다.

## Authentication Gates

없음.

## Known Stubs

없음. Task 1 의 스텁 3파일은 Task 2 에서 전부 실제 구현으로 대체됐다(`grep` 으로 `"stub"` 잔존 0건 확인 — `git status` 의 3파일이 최종 구현본).

## Threat Flags

없음 — 이 플랜은 네트워크 엔드포인트·인증 경로·스키마를 만들지 않는다. 유일한 외부 프로세스 호출 `git_sha()` 는 플랜 `<threat_model>` T-02-14 에 이미 등록돼 있고 argv 고정·`shell=False`·`timeout=5`·실패 시 `None` 으로 완화했다.

## 검증 명령과 결과

| 명령 | 결과 |
|---|---|
| `uv run pytest tests/evaluation --no-header` | `18 passed` |
| `uv run pytest tests/evaluation tests/test_architecture.py --no-header` | `21 passed`, failed 0 |
| `uv run ruff format --check src/millie_rec/evaluation tests/evaluation` | `7 files already formatted` |
| `uv run ruff check src/millie_rec/evaluation tests/evaluation` | `All checks passed!` |
| `uv run python -c "import millie_rec.evaluation as e; print(len(e.__all__))"` | `12` |
| `wc -l src/millie_rec/evaluation/*.py` | 28 / 67 / 38 / 119 — 전부 ≤150 |
| `grep -rn "millie_rec\.(data\|retrieval\|serving\|app)" src/millie_rec/evaluation/` | 출력 없음(star 의존 준수) |
| `ls -a results/` | `.gitkeep` 만 |
| `git log --oneline \| head -1` | `8e5172b` (플랜 전과 동일 — 커밋 0) |

**전역 게이트는 이 플랜에서 돌리지 않았다**(checker B3 · 02-06-PLAN.md `<wave_gate>`): 전체 트리 `uv run pytest --no-header`(기준선 104 passed / 2 skipped 위) · `uv run ruff check .` · `make smoke` 는 wave 1 의 세 플랜(01·02·03)이 모두 끝난 뒤 Advisor 가 1회 실행한다. 이 플랜은 서버를 접촉하지 않았다.

## 요구사항 대응

- **EVAL-04** — 3지표 순수 함수 + 손계산 테스트 7건 통과. 하네스가 `seen` 반환을 `ValueError` 로 막아 "학습에 본 아이템은 추천에서 제외"를 평가 단계에서도 강제.
- **EVAL-05** — `write_results` 가 `latest.csv`(D-06 컬럼, `VARIANTS` 순 정렬, 소수 3자리)·`eval_<ts>.json`(`split_mode`·`n_users`·`seed`·`git_sha`)을 쓴다. 수용 기준 '평가 4행 + split_mode 출력'(../.assets/PRD/PRD_메인_추천_시스템.md §9 수용 기준 표)의 전제 완성(4행 채우기는 Phase 4 '추천 파이프라인과 모델 freeze'(.planning/ROADMAP.md)).
- **EVAL-06** — `latest_states.csv`(D-07)가 `state`(n0|n20)별 행과 별도 `n_users` 를, json 이 `n_users{state: n}` 를 기록. 수용 기준 'n=0 vs n≥k 지표 분리'(PRD §9 수용 기준 표). 하네스 테스트 `test_evaluate_two_states_report_separate_n_users` 가 상태별 `n_users` 분리를 고정.

## Self-Check: PASSED

- `src/millie_rec/evaluation/metrics.py` FOUND
- `src/millie_rec/evaluation/harness.py` FOUND
- `src/millie_rec/evaluation/report.py` FOUND
- `src/millie_rec/evaluation/__init__.py` FOUND (modified)
- `tests/evaluation/test_metrics.py` FOUND
- `tests/evaluation/test_harness.py` FOUND
- `tests/evaluation/test_report.py` FOUND
- 커밋 해시: 해당 없음 — D-18 에 따라 커밋 0. `git log --oneline | head -1` = `8e5172b`(플랜 전과 동일)로 확인.
