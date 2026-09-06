---
phase: 02-track-a
plan: 05
subsystem: app (조립 레인)
tags: [cli, pipeline, export, server-wiring, eval-harness-entrypoint]
requires: ["02-01 (data 공개 표면)", "02-02 (retrieval 공개 표면)", "02-03 (evaluation 공개 표면)"]
provides:
  - "millie_rec.app.pipeline: PopPipeline · fit_pipelines(train) · build_pipelines(artifact)"
  - "millie_rec.app.cli: main() — 서브커맨드 data · eval --variant all|pop|cf|hybrid|hybrid_div"
  - "millie_rec.app.export: write_eval_table() → artifacts/serving/eval_table.json (D-09 형태)"
  - "app/server.py: pipelines=build_pipelines() 주입 (ROADMAP Success Criterion 5 배선)"
affects:
  - "Phase 4 '추천 파이프라인과 모델 freeze': fit_pipelines/build_pipelines dict 에 cf·hybrid·hybrid_div 추가 지점"
  - "Phase 5 '서빙 Must 완성': GET /api/showcase 가 eval_table.json 을 읽는다"
tech-stack:
  added: []
  patterns: ["argparse 서브커맨드 1개(app/cli.py)", "variant dict 조립(아키텍처 01 §3-3)", "monkeypatch 로 머신 상태 비의존 테스트"]
key-files:
  created:
    - src/millie_rec/app/pipeline.py
    - src/millie_rec/app/cli.py
    - src/millie_rec/app/export.py
    - tests/app/test_pipeline.py
    - tests/app/test_cli.py
    - tests/app/test_export.py
  modified:
    - src/millie_rec/app/server.py
    - tests/serving/test_smoke.py
decisions:
  - "Pipeline 어댑터(Candidate→ScoredItem)는 app/pipeline.py — 비즈니스 규칙 0, retrieval 이 Pipeline 의미를 모르게"
  - "eval_table.json writer 는 app/export.py 로 분리(B5) — cli.py 150줄 유지 + artifacts/serving/ 소유 = app export"
  - "tests/serving/test_smoke.py 의 서버 조립 테스트는 build_pipelines 를 monkeypatch 로 대체(B4) — 아티팩트 유무 비의존"
metrics:
  duration: "약 40분"
  completed: 2026-09-05
  tasks: 3
  tests_added: 9
---

# Phase 2 Plan 05: app 조립 (cli · pipeline · export · server 주입) Summary

**한 줄:** `make data`·`make eval` 의 실행 진입점(`app/cli.py`)과 `pop` variant dict·서버용 아티팩트 로더(`app/pipeline.py`), `artifacts/serving/eval_table.json` writer(`app/export.py`)를 만들고 `app/server.py` 에 `pipelines=build_pipelines()` 를 배선했다 — 합성 parquet e2e 로 `make eval` 의 파일 계약 5종을 네트워크 없이 고정.

## 커밋

**(no commit — 사용자 승인 대기.)** 결정 'D-18 커밋 없음'(`.planning/phases/02-track-a/02-CONTEXT.md` §검증·완료 형태) 및 결정 'Phase 1 실행 방식'(`../.assets/개발일지/2026-09-05_Day1_GSD_초기화와_계약_freeze.md` 항목 D55)에 따라 `git add`·`git commit` 을 실행하지 않았다. 변경은 작업 트리에 남아 있다. `git log --oneline | head -1` = `8e5172b` (플랜 시작 전과 동일).

## 변경 파일 (git status --short — 전부 untracked, 삭제 0)

```
?? src/millie_rec/app/cli.py        (128줄, 신규)
?? src/millie_rec/app/export.py     (41줄,  신규)
?? src/millie_rec/app/pipeline.py   (55줄,  신규)
?? src/millie_rec/app/server.py     (18줄,  수정 — Phase 1 산출물이 아직 미커밋이라 ?? 로 표시)
?? tests/app/                       (test_pipeline.py 49 · test_cli.py 126 · test_export.py 55, 신규)
?? tests/serving/test_smoke.py      (198줄, +32줄 삽입 · 삭제 0)
```

`git diff --numstat tests/serving/test_smoke.py` 는 **출력 없음** — 이 파일은 아직 커밋되지 않은 untracked 파일이라 diff 대상이 아니다. 대신 편집 전 사본(스크래치패드)과 `diff` 해 **삭제 줄 수 0 / 추가 줄 수 32** 를 실측했다(기존 11건 단정 무변경, 새 테스트 1건 + `_FakePop` + monkeypatch 2줄 + import 2줄).

`results/` · `artifacts/` · `data/` 미접촉(`git status --short -- results artifacts data` 출력 없음, `ls -a artifacts/serving/` = `.gitkeep` 만). 테스트는 전부 `tmp_path`.

## 태스크별 RED / GREEN

### Task 1 — app/pipeline.py (+ tests/app/test_pipeline.py 4건)
- **RED:** 스텁(`build_pipelines` → `{"stub": None}`) 상태에서 `uv run pytest tests/app/test_pipeline.py --no-header` → `4 failed`, 전부 `AssertionError`. 발췌: `E AssertionError: assert set() == {'pop'}` / `Extra items in the right set: 'pop'`.
- **GREEN:** `PopPipeline`(Pipeline 구현 glue) · `fit_pipelines(train)` · `build_pipelines(artifact)` 작성 → `4 passed`. 아키텍처 테스트 `3 passed`.
- 안전성: 아티팩트 부재 → `log.info` + `{}`, 손상(`"not json"`·`items` 키 없음) → `log.exception` + `{}` — 어느 경우에도 기동을 막지 않는다(위협 T-02-24 mitigate 이행).

### Task 2 — app/export.py · app/cli.py (+ test_export.py 1건 · test_cli.py 3건)
- **RED:** export 스텁(파일을 쓰지 않고 경로만 반환) → `1 failed`, `E AssertionError: assert False +  where False = exists()`. cli 스텁(파싱만) → `3 failed`: e2e 는 `assert (out / LATEST_FILE).exists()` AssertionError, 미등록 variant 는 `Failed: DID NOT RAISE <class 'SystemExit'>`, data 는 `E AssertionError: assert [] == ['download', 'build']`.
- **GREEN:** `write_eval_table`(csv.DictReader 복사) → `1 passed`; `cmd_data`·`cmd_eval`·`main` → `3 passed`. `tests/app` 합계 **8 passed** (e2e 0.82s — 30초 예산 안).
- e2e 가 고정한 파일 계약: `latest.csv`(헤더 + `pop,…,30,holdout,pop_v1`, recall ∈ (0,1]) · `latest_states.csv` 3줄(`pop,n0,…,30` / `pop,n20,0.000,0.000,0.000,0`) · `eval_<ts>.json`(`split_mode=holdout`, `n_users={"n0":30,"n20":0}`, `n_excluded=0`, `k_history=20`, `test_frac=0.2`, `git_sha` 키) · `eval_table.json`(rows[0].variant=pop, meta 8키, `"states"` 없음 = D-09) · `popularity.json`(`name="pop"`).

### Task 3 — app/server.py 주입 + test_smoke 결정론화
- `server.py`: import 1행 추가 + `pipelines={}` → `pipelines=build_pipelines()`, 주석 1줄 갱신. 18줄(≤30), StaticFiles 마운트가 여전히 마지막(L18), `create_app` 시그니처 무변경, CORS·`os.environ`·라우트 추가 0.
- `test_smoke.py`: 기존 조립 테스트에 `monkeypatch.setattr("millie_rec.app.pipeline.build_pipelines", lambda: {})` 1줄(기존 `FALLBACK_GLOBAL_POP` 단정 무변경) + 새 테스트 `test_server_module_injects_pop_pipeline_when_build_pipelines_returns_pop`.
- **결과: `uv run pytest tests/serving/test_smoke.py --no-header` → `12 passed`.** 02-04(`serving/api.py` level 0 분기)가 이미 착지해 있어(확인: `api.py` L13 `FALLBACK_PERSONALIZED`, L77 `_personalized_response(..., level=FALLBACK_PERSONALIZED, ...)`, L130 `pipelines[name]`) 새 테스트가 **대기 없이 즉시 통과**했다. 플랜이 예상한 "02-04 미완료 시 1 failed" 상황은 발생하지 않았다.
- 기동 무부작용: `uv run python -c "import sys, millie_rec.app.server; print('pandas' in sys.modules, 'sklearn' in sys.modules)"` → **`False False`**.

## 검증 증거 (자기 경로 스코프 — 전역 게이트는 wave 2 종료 후 Advisor)

| 명령 | 결과 |
|---|---|
| `uv run pytest tests/app --no-header --durations=3` | `8 passed in 0.86s` |
| `uv run pytest tests/serving/test_smoke.py --no-header` | `12 passed` |
| `uv run pytest tests/test_architecture.py --no-header` | `3 passed` |
| `uv run pytest tests/app tests/serving/test_smoke.py tests/test_architecture.py --no-header` | **`23 passed`, failed 0** |
| `uv run ruff format --check src/millie_rec/app tests/app tests/serving/test_smoke.py` | `9 files already formatted` |
| `uv run ruff check src/millie_rec/app tests/app tests/serving/test_smoke.py` | `All checks passed!` |
| `wc -l` | pipeline 55 · cli 128 · export 41 · server 18 — 전부 상한 이내 |
| `grep -c "millie_rec\.(data\|retrieval\|evaluation\|serving)\." cli.py` / `export.py` / `pipeline.py` | 0 / 0 / 0 (3단 경로 없음 = star 의존 준수) |
| `grep -c "import argparse" src/millie_rec/app/*.py` | cli.py 만 1 |
| `grep -c "def test_" tests/serving/test_smoke.py` / `grep -c "POP_ARTIFACT.exists()"` | 12 / 0 (머신 상태 의존 0) |
| `uv run python -c "… sys.modules …"` | `False False` |

전역 `uv run pytest --no-header` · `ruff check .` · `make smoke` 는 **의도적으로 실행하지 않았다** — 02-04 와 같은 wave 2 에서 병렬 실행 중이라 이 시점의 전역 결과는 신뢰할 수 없다(플랜 3-d, 오케스트레이터 지시).

## planner 결정 3개와 근거

1. **Pipeline 어댑터 위치 = `app/pipeline.py`.** `Candidate → ScoredItem` 변환은 "retriever 단독 variant 를 Pipeline 으로 보이게 하는" 조립 glue 이고 비즈니스 규칙이 없다. retrieval 에 두면 retrieval 이 `Pipeline` 의미(ScoredItem·position)를 알게 된다. Phase 4 가 `cf`·`hybrid`·`hybrid_div` 를 추가하는 자리도 같은 dict(아키텍처 01 §3-3 "variant dict")다.
2. **`eval_table.json` writer = `app/export.py`(checker B5).** `artifacts/serving/` 소유가 app export(`../.claude/rules/architecture.md` 산출물 소유권 표)이고, cli 에 남기면 155줄로 150줄 상한을 넘긴다. 분리 후 cli 128 · export 41 로 둘 다 여유.
3. **`tests/serving/test_smoke.py` 서버 조립 테스트의 `build_pipelines` monkeypatch(checker B4).** `server.py` 가 import 시점에 `build_pipelines()` 를 호출하므로, 아티팩트가 있는 머신에서는 기존 level 3 단정이 깨진다. `sys.modules.pop` **앞**에서 대체해 level 3 경로를, 새 테스트에서 `{"pop": _FakePop()}` 로 level 0 경로를 각각 결정론적으로 단정한다. `artifacts/popularity.json` 유무와 무관하게 12건 전부 통과.

## `--raw` 기본값 처리 방식

`src/millie_rec/data/__init__.py` 가 `RAW_SUBDIR`("goodbooks")를 실제로 공개하고 있어 **플랜의 1안**을 택했다: `d.add_argument("--raw", type=Path, default=DIR_RAW / RAW_SUBDIR)`. `"goodbooks"` 리터럴을 cli 에 다시 쓰지 않는다(이름의 정본 = data 슬라이스 공개 상수). 대안(`None` → 기본 인자에 위임)은 불필요.

## `eval_table.json.rows` 값 타입 주의

`rows` 값은 `csv.DictReader` 결과 그대로 **csv 문자열**이다(예: `"recall@20": "0.100"`). 재계산 없이 `latest.csv` 를 복사한다는 D-09·위협 T-02-27(Repudiation mitigate)의 요구가 이 형태를 강제한다. Phase 5 '서빙 Must 완성'(.planning/ROADMAP.md)의 `GET /api/showcase` 스키마가 float 을 기대하면 **그때 serving 쪽에서 변환**한다.

## Deviations from Plan

### 1. [Rule 3 - Blocking] `server.py` 의 `create_app(...)` 호출이 ruff format 에 의해 여러 줄로 감쌈
- **발견 시점:** Task 3
- **문제:** 플랜 acceptance 는 `^app = create_app(pipelines=build_pipelines(), fallback=GlobalPopularFallback(None), db=Database(resolve_db_path()))` 한 줄 grep 을 요구하지만, 그 줄은 **115자**로 `line-length = 100`(pyproject `[tool.ruff]`)을 위반한다. 같은 플랜의 완료 기준(`ruff format --check` + `ruff check` 클린)과 직접 충돌한다.
- **조치:** ruff format 이 만든 4줄 형태를 채택했다(L12-16). 의미·인자·순서는 동일하고 `pipelines=build_pipelines()` 는 그대로 존재한다.
- **영향 파일:** `src/millie_rec/app/server.py`

### 2. [Rule 1 - 검증 도구 오탐] `awk 'length > 100'` 은 이 환경에서 **바이트**를 센다
- **발견 시점:** Task 1
- **문제:** 플랜의 E501 확인 명령 `awk 'length > 100' … | wc -l == 0` 이 한글 주석 4줄에서 0이 아닌 값을 냈다. macOS awk 가 UTF-8 한글을 3바이트로 세기 때문(문자 길이 아님).
- **조치:** 문자 기준 실측(`len(line)` 파이썬)으로 **모든 파일 100자 초과 0줄**을 확인했고, 정본 판정은 ruff E501(문자 기준)로 대체했다 — `All checks passed!`. 코드는 바꾸지 않았다.
- **영향 파일:** 없음(검증 방법만)

### 3. [플랜 허용 범위] `test_smoke.py` 주석 1줄을 2줄로 줄바꿈
- 삽입한 monkeypatch 설명 주석이 101자여서 ruff E501 이 떴다. 플랜의 `<project_rules_inline>` 이 명시적으로 허용한 "docstring·주석·문자열은 의미 변경 없이 100자 이내로 줄바꿈" 을 적용했다. 삭제 0 유지.

### 4. [사실 갱신] 새 level 0 조립 테스트가 대기 없이 통과
- 플랜은 "02-04 미완료 시 `11 passed, 1 failed`" 를 예상했으나, 실행 시점에 02-04 의 `serving/api.py` level 0 분기가 이미 착지해 **12 passed**. SUMMARY 에 "02-04 대기" 항목은 없다.

### 범위 밖 관찰 (수정하지 않음)
- `git diff --stat -- src/millie_rec/contracts.py Makefile pyproject.toml src/millie_rec/{data,retrieval,evaluation}` 는 빈 출력이 아니다 — 그러나 이는 **wave 1(02-01~02-03)의 `__init__.py` 공개 표면 추가 + 오케스트레이터의 pyproject `.planning` ruff 제외**이고 이 플랜이 만든 변경이 아니다. 이 플랜은 `files_modified` 8개 파일 밖을 쓰지 않았다.

## 사용자 지시와의 긴장

- "no side effects / 최소 변경": `server.py` 는 import 1행 + 호출 인자 1개 + 주석 1줄만 바뀌었고(ruff format 로 인한 줄바꿈 포함), StaticFiles 마지막 마운트·`create_app` 시그니처는 불변. `test_smoke.py` 는 삽입 전용(삭제 0).
- "modular": `pipeline.py`(glue) · `cli.py`(argparse 오케스트레이션) · `export.py`(파일 writer) 로 관심사를 1파일 1개로 분리했고 각 ≤150줄.
- 긴장 없음 — 플랜의 구체 지시와 사용자 지시가 같은 방향이었다.

## Known Stubs

없음. RED 단계에서 만든 스텁 3개(`pipeline.py`·`export.py`·`cli.py`)는 GREEN 에서 전문 교체됐고, 남아 있는 `STUB` 문자열은 0이다.

## Threat Flags

없음 — 플랜 `<threat_model>` 밖의 새 네트워크·인증·스키마 표면을 만들지 않았다. `build_pipelines` 는 `json.loads` 만 하고 값은 `int()`/`float()` 로 강제된다(T-02-25 accept 유지).

## Self-Check: PASSED

- 생성 파일 6개 + 수정 파일 2개 존재 확인(`wc -l` 실측: 55 / 128 / 41 / 18 / 49 / 126 / 55 / 198)
- 커밋 0 — `git log --oneline | head -1` = `8e5172b` (플랜 시작 전과 동일). 커밋 해시 대신 변경 파일 목록을 위에 기록
- 스코프 테스트 23 passed / failed 0, ruff 클린, 기동 무부작용 `False False` 재확인
