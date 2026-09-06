---
phase: 05-must
plan: 07
subsystem: Serving (dashboard_api showcase · bench)
tags: [serving, showcase, eval-table, bench, latency, urllib, tdd]
requires:
  - src/millie_rec/contracts.py (SEED · DIR_RESULTS · DIR_ARTIFACTS · FALLBACK_GLOBAL_POP · ROOT)
  - src/millie_rec/serving/schemas_should.py (freeze — EvalRow · EvalTable · MetricMapping · Memorable · ShowcaseOut)
  - src/millie_rec/serving/db.py (Database — 타입만, 05-03 인계)
  - "Plan 05-04 POST /api/preferences(201) · GET /api/meta/onboarding · GET /api/candidates/onboarding (bench 가 HTTP 로 호출)"
  - artifacts/serving/eval_table.json (🧊 freeze, 읽기만)
provides:
  - "serving.dashboard_api.build_router(*, db, eval_table_path=EVAL_TABLE_PATH, latency_path=LATENCY_PATH) → APIRouter(GET /api/showcase)"
  - "serving.dashboard_api.load_eval_table(path, latency_path) → EvalTable (문자열 → float, split_mode ← meta)"
  - "serving.dashboard_api 상수 PHILOSOPHY · METRIC_MAPPING · MEMORABLE_5 · ROADMAP · DATA_NOTICE · EVAL_KEY_MAP · EVAL_SOURCE"
  - "serving.bench percentile · summarize · make_users · run · build_parser · main · git_sha (python -m millie_rec.serving.bench)"
affects:
  - "Plan 05-06 (api.py L128-133 이 dashboard_router(db=db) 로 이미 선택 import — 시그니처 일치 확인함)"
  - "Plan 05-09 (Advisor 실측 make serve → make bench → results/latency.json p95 < 200)"
  - "Plan 05-12 (같은 파일에 GET /api/dashboard 최소형 추가 — build_router 의 db 인자를 쓴다)"
  - "Phase 6 '데모 재구성'(.planning/ROADMAP.md) 쇼케이스(#/) 비교표"
tech-stack:
  added: []
  patterns:
    - "star 의존 회피 = git_sha 를 evaluation/report.py 에서 복사한 중복 정의(중복 < 결합)"
    - "HTTP 클라이언트는 표준 urllib.request 1개 함수(_req)로 GET·POST 겸용 — httpx 는 dev 전용이라 쓰지 않는다"
    - "파일 I/O 응답은 요청마다 읽고 예외는 log 후 빈 표 200 (500·Traceback 없음)"
    - "페이로드 조립을 부분 dict 4개 + 언팩으로 — ruff format 이 한 줄 한 키로 펼치는 것을 피해 150줄 한도 안에 든다"
key-files:
  created:
    - src/millie_rec/serving/dashboard_api.py
    - src/millie_rec/serving/bench.py
    - tests/serving/test_dashboard_api.py
    - tests/serving/test_bench.py
  modified: []
decisions:
  - "p95_ms 는 results/latency.json 의 전체 p95 를 4행에 같은 값으로 병기 — bench 가 셀 배정 혼합이라 variant 별 p95 가 없다(D-11). 출처 분리는 source.p95"
  - "eval_table.json 부재·손상·행 키 누락 전부 200 — split_mode 는 unknown, 손상 행만 건너뛴다"
  - "urllib.error.URLError 는 OSError 하위라 except OSError 하나로 서버 미기동을 잡는다(import 1줄 절약)"
  - "run() 은 _measure 헬퍼 없이 루프 안에서 직접 측정 — bench.py 150줄 한도"
requirements-completed: [SERV-13, SERV-10]
metrics:
  tasks: 3
  tests_added: 15
  duration: "~50min"
  completed: 2026-09-06
commits: 0   # no_commit
---

# Phase 5 Plan 07: 쇼케이스 비교표(GET /api/showcase) · 로컬 bench 요약

**`artifacts/serving/eval_table.json`(지표 값이 문자열, 키가 `recall@20`)을 `schemas_should.ShowcaseOut`으로 변환하는 `GET /api/showcase`와, 표준 `urllib`만으로 `POST /api/preferences` 50명 → warmup 50 → 500 요청을 재어 `results/latency.json`을 쓰는 bench CLI를 TDD 한 사이클(RED 12 → GREEN 18)로 만들었다. 실측(`make serve` + `make bench`)은 Plan 05-09 Advisor 몫이라 이 플랜은 `results/`를 건드리지 않았다.**

## 변경 파일 (4개 전부 신규 · 커밋 0)

| 경로 | 상태 | 줄 수 | 내용 |
|---|---|---|---|
| `src/millie_rec/serving/dashboard_api.py` | 신규 | **140** (≤150) | `GET /api/showcase` · `load_eval_table` · 고정 문장 상수 5종 |
| `src/millie_rec/serving/bench.py` | 신규 | **150** (=한도) | `percentile` · `summarize` · `make_users` · `run` · `build_parser` · `main` · `git_sha` |
| `tests/serving/test_dashboard_api.py` | 신규 | 155 (`def test_` 8건) | 계약 3 · 정확성 1 · 안전성 4 |
| `tests/serving/test_bench.py` | 신규 | 127 (`def test_` 7건) | 계약 3 · 정확성 2 · 안전성 2 |

**커밋하지 않는다** — 플랜 frontmatter `no_commit: true`(사용자 지시 2026-09-05). 네 파일 모두 `git status --short` 에 `??` 로 남아 있고, `must_not_touch` 목록은 하나도 건드리지 않았다(`contracts.py` · `schemas*.py` · `api.py` · `serving/__init__.py` · wave 1 파일 · `app/**` · `results/**` · `artifacts/serving/**` · `Makefile` · `tests/test_architecture.py` 포함).

## TDD 증거

### RED (Task 1 — 스텁 2개 + 테스트 15건)

실행: `uv run pytest tests/serving/test_dashboard_api.py tests/serving/test_bench.py --no-header`

```
12 failed, 3 passed, 2 warnings in 0.27s
```

실패 사유는 전부 `AssertionError` 였다. `ImportError`·`AttributeError`·`TypeError`·`KeyError`·`NotImplementedError`·collection error 는 0건(`grep -cE` → `0`). 발췌 3건:

```
    def test_showcase_parses_and_converts_string_metrics_to_float(tmp_path: Path):
        out = _showcase(tmp_path / "a")
        table = out.eval_table
>       assert table.split_mode == "holdout"
E       AssertionError: assert 'x' == 'holdout'
```

```
    def test_percentile_index_rule_hand_computed():
        four = [1.0, 2.0, 3.0, 4.0]
>       assert percentile(four, 50) == 2.0
E       assert 0.0 == 2.0
```

```
E       assert 2 == 1
E        +  where 2 = SystemExit(2).code
E        +    where SystemExit(2) = <ExceptionInfo SystemExit(2) tblen=2>.value
```

RED 에서 통과한 3건은 스텁이 이미 만족하는 것들이다 — 소스 grep 2건(`dashboard_api` 에 `Query(`·`request.` 없음, `bench` 가 `httpx` 대신 `urllib.request`)과 `build_parser()` 기본값(스텁에도 실제 값을 넣으라는 플랜 지시). 같은 시점에 `uv run pytest tests/test_architecture.py --no-header` → `3 passed`.

### GREEN (Task 2)

```
18 passed, 2 warnings in 0.25s
```

(`test_dashboard_api.py` 8 + `test_bench.py` 7 + `tests/test_architecture.py` 3)

### REFACTOR (Task 3)

```
4 files already formatted
All checks passed!
18 passed, 2 warnings in 0.25s
```

`uv run ruff format` + `ruff format --check` + `ruff check` 를 **이 플랜의 4개 파일만 지정**해 실행했다(디렉터리·글롭 미사용 — 05-06·05-08 이 같은 트리에서 편집 중). 리팩터 내용은 E501 7건 해소(모듈·함수 docstring 4개와 `MEMORABLE_5` 문장 1개 축약, 테스트 fixture JSON 1줄 접기)뿐이고 로직 변경은 없다. `DATA_NOTICE` 만 `# noqa: E501` 로 남겼다 — 줄을 나누면 `../.claude/rules/serving.md` 문장과의 글자 대조가 불가능해진다.

부가 확인:

```
uv run python -m millie_rec.serving.bench --help   → 종료 코드 0
ls results/latency.json                            → 없음(이 플랜은 실측하지 않는다)
```

## TDD Gate Compliance

| Gate | 상태 | 근거 |
|---|---|---|
| RED | 통과 | 신규 15건 중 12건이 `AssertionError` 로 실패, 나머지 3건은 상수·소스 grep 이라 스텁에서도 통과 |
| GREEN | 통과 | 구현 후 18 passed, failed 0 |
| REFACTOR | 통과 | ruff format/check 클린, 재실행 18 passed |

`no_commit: true` 라 `test(...)` → `feat(...)` 커밋 게이트는 만들지 않았다. 게이트 증거는 위 pytest 출력으로 대체한다.

## 인계 시그니처 (Plan 05-06 · 05-09 · 05-12 가 소비)

```python
# src/millie_rec/serving/dashboard_api.py
EVAL_TABLE_PATH = DIR_ARTIFACTS / "serving" / "eval_table.json"
LATENCY_PATH = DIR_RESULTS / "latency.json"
SPLIT_MODE_UNKNOWN = "unknown"
EVAL_KEY_MAP = {"recall@20": "recall_at_20", "ndcg@10": "ndcg_at_10", "ild@10": "ild_at_10"}
EVAL_SOURCE = {"metrics": "results/latest.csv", "p95": "results/latency.json"}
PHILOSOPHY: str
METRIC_MAPPING: tuple[tuple[str, str], ...]   # 3개
MEMORABLE_5: tuple[tuple[str, str, str], ...]  # (claim, how_to_verify, route) × 5
ROADMAP: tuple[str, ...]                       # 7개
DATA_NOTICE: str                               # serving.md 2트랙 고지 문장 verbatim


def load_eval_table(path: Path = EVAL_TABLE_PATH, latency_path: Path = LATENCY_PATH) -> EvalTable


def build_router(
    *,
    db: Database,
    eval_table_path: Path = EVAL_TABLE_PATH,
    latency_path: Path = LATENCY_PATH,
) -> APIRouter        # APIRouter(prefix="/api") + GET /showcase
```

**05-06 배선 확인:** `src/millie_rec/serving/api.py` L128-133 이 이미
`from millie_rec.serving.dashboard_api import build_router as dashboard_router` → `app.include_router(dashboard_router(db=db))` 로 부른다. 경로 인자 2개가 기본값이라 **호출 시그니처가 그대로 맞는다**(추가 작업 없음). `try/except ImportError` 는 이제 항상 성공 경로를 탄다.

**05-12 인계:** `GET /api/dashboard` 최소형은 이 파일에 라우트 하나를 더 붙이면 된다. `build_router` 의 `db` 인자는 지금 쓰이지 않고 그 용도로 받아만 둔 것이다. 현재 140줄이라 여유는 10줄뿐 — 집계 로직은 별도 파일(예: `dashboard_stats.py`)로 빼야 한다.

```python
# src/millie_rec/serving/bench.py
BASE_URL = "http://localhost:8000"
N_USERS, WARMUP, N_REQUESTS, K = 50, 50, 500, 40
OUT_PATH = DIR_RESULTS / "latency.json"
TIMEOUT_S, SEEDS_PER_USER, CAND_N, CATS_MAX = 10.0, 5, 60, 3
SERVE_HINT, UA, CRITERION = "make serve 를 먼저 실행하세요", "millie-rec-bench/0.1", "bestseller"


def git_sha() -> str | None
def percentile(sorted_ms: Sequence[float], p: float) -> float
def summarize(
    records: Sequence[tuple[float, int, str]],
    *,
    n_users: int, warmup: int, k: int, base_url: str, n_books: int | None,
    created_at: str, git_sha: str | None, seed: int = SEED,
) -> dict
def make_users(base: str, n: int, rng: random.Random) -> list[str]
def run(
    base: str, *, n_users: int, warmup: int, n_requests: int, k: int,
    out: Path, seed: int, n_books: int | None = None,
) -> dict
def build_parser() -> argparse.ArgumentParser
def main(argv: list[str] | None = None) -> None
```

## bench 실행 절차 (Plan 05-09 Advisor 용)

```bash
# 터미널 1
make serve                      # uvicorn 1 worker, port 8000

# 터미널 2 — 인자 없이 D-11 모집단(user 50 · warmup 50 · 500 요청 · k 40 · model 미지정)
make bench                      # == uv run python -m millie_rec.serving.bench
cat results/latency.json | jq '.p50, .p95, .p99, .fallback_levels, .variants'
```

인자를 바꾸려면 (예: 카탈로그 규모를 페이로드에 남기고 요청 수를 줄여 예행)

```bash
uv run python -m millie_rec.serving.bench --n 100 --warmup 20 --n-books 9447
uv run python -m millie_rec.serving.bench --base http://localhost:8010 --out results/latency.json
```

- 서버가 안 떠 있으면 첫 `GET /health` 에서 `make serve 를 먼저 실행하세요` 를 출력하고 종료 코드 1 — `results/latency.json` 은 만들지 않는다.
- bench 는 실제로 서버 DB(`data/local/millie.db`)에 user_key 50개·스냅샷 50개·추천 로그 550건을 남긴다(플랜 위협 등록부 T-05-07-05 `accept`). **Railway 볼륨에 대고 돌리지 않는다** — 로컬 uvicorn 전용.
- `make bench` 후 서버 재기동 없이 `GET /api/showcase` 의 `eval_table.rows[*].p95_ms` 가 채워진다(요청마다 파일을 읽는다).

## `results/latency.json` 키 목록 (D-11)

| 키 | 형 | 의미 |
|---|---|---|
| `p50` · `p95` · `p99` | float(ms) | 클라이언트 측 **전체 응답** 시간. 게이트는 `p95 < 200` |
| `n` | int | 측정 표본 수(warmup 제외) |
| `warmup` · `users` · `k` · `seed` | int | 재현 조건. `seed` = `contracts.SEED` |
| `fallback_levels` | dict | `{"0": n, "1": n, "2": n, "3": n}` — 없는 단계도 0 으로 채운다 |
| `variants` | dict | `{model_version: n}` (셀 배정 결과 분포) |
| `catalog` | dict | `{"n_books": <--n-books 인자 또는 null>}` |
| `created_at` | str | `2026-09-07T00:00:00Z` (UTC, 초 단위) |
| `git_sha` | str \| null | `git rev-parse --short HEAD` |
| `base_url` | str | 측정 대상 |

user_key 는 어디에도 기록되지 않는다 — 표본 튜플이 `(ms, fallback_level, model_version)` 3원소라 들어갈 자리가 없다(위협 등록부 T-05-07-04, 테스트 `test_summarize_output_has_no_user_key`).

## showcase 변환 규칙

- **문자열 → float:** `EVAL_KEY_MAP` 으로 `recall@20`·`ndcg@10`·`ild@10` 을 `recall_at_20`·`ndcg_at_10`·`ild_at_10` 으로 바꾸고 `float()` 캐스팅한다(`"0.063"` → `0.063`).
- **`split_mode` ← `meta.split_mode`:** 파일 값을 그대로 전달한다. `temporal` 이면 `temporal`, 없으면 `unknown` — 거짓 값을 만들지 않는다.
- **`p95_ms` 병기:** `results/latency.json` 의 전체 `p95` 를 4행 모두에 같은 값으로 넣는다. 파일이 없으면 4행 전부 `None`. 출처는 `source = {"metrics": "results/latest.csv", "p95": "results/latency.json"}` 로 분리해 Track A(Goodbooks) 숫자와 로컬 데모 지연을 섞지 않는다(`../.claude/rules/data.md` 2트랙).
- **안전성:** 파일 부재·손상 JSON·행의 지표 키 누락 전부 200. 손상은 `log.exception` 1건 후 빈 표, 행 키 누락은 `log.warning` 후 그 행만 제외. 응답에 `Traceback` 없음.
- 실제 아티팩트로 확인: `load_eval_table()` 기본 경로 호출 → `split_mode='holdout'`, 4행 `[('pop', 0.063, None), ('cf', 0.117, None), ('hybrid', 0.118, None), ('hybrid_div', 0.116, None)]`(p95 는 05-09 실측 전이라 None).

## 확인한 계약·규칙

- 두 파일 모두 `millie_rec.contracts` · `millie_rec.serving.*` 만 import — `data`·`app`·`retrieval`·`ranking`·`reranking`·`evaluation` grep 0건, `tests/test_architecture.py` 3 passed.
- 의존성 추가 0. `httpx` 는 소스에 문자열조차 없다(`grep -c httpx` → 0). HTTP 는 `urllib.request` 만.
- `DATA_NOTICE` 가 `../.claude/rules/serving.md` 문장과 글자 동일(`grep -c` 로 두 파일 각 1). `ROADMAP` 7개가 `../.assets/설계서/백엔드 서빙/01_백엔드_서버_구성.md` §13 `"roadmap"` 배열과 순서·문자열 동일.
- 경로는 모듈 상수 2개(`EVAL_TABLE_PATH`·`LATENCY_PATH`) 또는 팩토리 주입만 — 라우터 소스에 `Query(`·`request.` 0건(테스트가 grep 으로 단정).
- 파일 ≤150줄: `dashboard_api.py` 140 · `bench.py` 150.
- `results/` · `artifacts/serving/` 미변경. `results/latency.json` 미생성.

## Advisor 보고 (재량 판단·경계 밖 항목)

1. **`bench.py` 가 정확히 150줄**이다. 한 줄도 더 못 붙인다. 플랜 코드 스케치를 그대로 쓰면 ~215줄이라 다음 4가지로 줄였다 — 전부 동작·공개 시그니처 무변경이다.
   - `_measure` 헬퍼를 없애고 `run()` 루프 안에서 직접 측정(플랜 스케치의 `_measure` 는 존재하지 않는다).
   - `_get`·`_post` 를 `_req(url, body=None)` 하나로 합쳤다(`body` 가 있으면 POST). GET 에도 `Content-Type` 헤더가 붙지만 무해하다.
   - `summarize` 의 반환 dict 를 `pcts`·`counts`·`dist`·`origin` 4개 부분 dict + 언팩으로 조립했다. 한 줄 한 키로 쓰면 ruff format 이 16줄로 펼친다.
   - `import math` 를 빼고 `-(-int(p * n) // 100)` 정수 올림을 썼다(`percentile` 결과는 플랜의 손계산 값과 동일 — 테스트 6건이 단정).
2. **`urllib.error` 를 import 하지 않았다.** `URLError` 는 `OSError` 하위라 `except OSError` 하나로 닫힌 포트·미기동·타임아웃을 전부 잡는다. 플랜은 `(urllib.error.URLError, OSError)` 를 적었지만 동작이 같고 import 1줄을 아낀다.
3. **`bench.py` 는 `../.assets/설계서/…` 아키텍처 문서 §9-3 serving 파일 분할 목록에 있는 이름**이라 `PROGRESS.md` 신설 기록은 필요 없다. `dashboard_api.py` 도 목록에 있다.
4. **`serving/__init__.py` 를 건드리지 않았다**(05-01 소유, `must_not_touch`). `build_router`·`load_eval_table`·`percentile`·`summarize` 를 `__all__` 에 올릴지는 05-01/05-06 소유자 판단이다. 05-06 은 이미 `millie_rec.serving.dashboard_api` 경로로 직접 import 하고 있어 노출은 필요 없다.
5. **`make_users` 의 카테고리 선택 규칙:** `GET /api/meta/onboarding` 의 `supported=true` 카테고리 상위 3개를 쓰고, 하나도 없으면 전체 상위 3개로 떨어진다. `criterion` 은 `"bestseller"` 고정(`serving/onboarding_meta.json` 의 criteria id). 카탈로그가 없는 서버(level 3 스켈레톤)에서는 후보가 비어 `seeds=[]` 로 스냅샷이 만들어지고 bench 는 계속 돈다 — 다만 그 숫자는 개인화 경로가 아니므로 **PDF 에 쓰지 않는다**. 05-09 실측 전 `GET /health` 의 `artifacts_loaded_at`·카탈로그 적재 여부를 먼저 확인해 달라.
6. **`--n-books` 는 사람이 넣는 값이다.** bench 는 카탈로그 파일을 읽지 않는다(serving 슬라이스가 `data` 를 import 할 수 없고, 클라이언트라 파일 접근도 부적절하다). 05-09 에서 `--n-books 9447` 처럼 실제 카탈로그 규모를 넘겨 주면 `catalog.n_books` 가 채워지고, 생략하면 `null` 이다.
7. **전역 검증은 하지 않았다** — 병렬 3인 규칙대로 `uv run pytest` 전체·`make smoke`·`make serve`·`make bench` 는 실행하지 않았다. wave 2 종료 후 Advisor 1회가 남아 있다.
8. **Codex 리뷰 대상 여부:** 이 플랜은 `contracts.py`·`schemas*.py` 를 바꾸지 않았고 개인정보 표면(`privacy_api.py`·`db.py`)도 아니다. `../.claude/rules/codex-review.md` 표 기준 **선택**이다. 다만 `GET /api/showcase` 가 파일을 읽는 비인증 엔드포인트라 `/codex:review --scope working-tree` 를 05-09 에서 한 번 돌릴 값은 있다.

## Known Stubs

없음. RED 단계의 스텁 4종(`load_eval_table`·`build_router` 빈 값, `percentile` 0.0, `summarize` `{}`)은 Task 2 에서 전부 실제 구현으로 교체됐다. `personal_case=None` 은 스텁이 아니라 **Should 미구현**이다 — 플랜 범위 밖(05-CONTEXT Deferred "`personal_case`(showcase 5권) → Should, wave 4에 시간 남으면"). `catalog.n_books` 가 인자 없이는 `null` 인 것도 설계된 동작이다(위 Advisor 보고 6).

## Threat Flags

| Flag | File | Description |
|---|---|---|
| threat_flag: new-endpoint | `src/millie_rec/serving/dashboard_api.py` | `GET /api/showcase` — 비인증 읽기 표면이 1개 늘었다. 쿼리 파라미터 없음, 읽는 파일은 모듈 상수 2개뿐, 예외는 전부 200 으로 흡수. 플랜 `<threat_model>` T-05-07-01~03 의 `mitigate` 를 테스트 4건(소스 grep · 부재 · 손상 · 키 누락)으로 이행했다 |

`bench.py` 는 서버 표면을 늘리지 않는다(클라이언트 CLI). T-05-07-05(로컬 DB 오염)·T-05-07-06(`--base` 외부 URL)은 플랜대로 `accept` 이고, 위 "bench 실행 절차" 에 로컬 전용이라는 운영 주의를 적었다.

## Self-Check: PASSED

- `src/millie_rec/serving/dashboard_api.py` FOUND (140줄) · `src/millie_rec/serving/bench.py` FOUND (150줄)
- `tests/serving/test_dashboard_api.py` FOUND (`def test_` 8건) · `tests/serving/test_bench.py` FOUND (`def test_` 7건)
- `uv run pytest tests/serving/test_dashboard_api.py tests/serving/test_bench.py tests/test_architecture.py --no-header` → `18 passed`
- `uv run ruff format --check` + `uv run ruff check` (위 4개 파일) → `4 files already formatted` · `All checks passed!`
- `uv run python -m millie_rec.serving.bench --help` → 종료 코드 0
- 커밋 0건 — `no_commit: true` 이므로 검증할 커밋 해시가 없다. `git status --short` 상 네 파일이 `??` 로 남아 있다
- `.planning/STATE.md` · `.planning/ROADMAP.md` 미수정(오케스트레이터 소유)
