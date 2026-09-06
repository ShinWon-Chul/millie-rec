---
phase: 05-must
plan: 06
subsystem: serving
tags: [cascade, fallback, recommendation-log, nearline, lifespan, ab-cell]
requires: ["05-01", "05-02", "05-03", "05-04", "05-05"]
provides:
  - "serving/cascade.py — Cascade · variant_for · CELL_VARIANT · PIPE_K_MIN (+ resolve·levels 재-export)"
  - "serving/resolve.py — Resolved · resolve_user · NOT_FOUND_SNAPSHOT · 스냅샷 SQL"
  - "serving/levels.py — cold_start · nonpersonal (seeds cold-start · level 2·3)"
  - "serving/rec_log.py — SQL_REC_INS · abbreviate_rows · merge_breakdown · log_recommendation"
  - "serving/api.py — create_app 이 라우터 4개 include · lifespan(replay·Nearline·close) · /health 채움"
  - "app.state.cascade · app.state.nearline · app.state.store · app.state.cache 노출"
affects: ["05-08", "05-09", "05-10", "05-12"]
tech-stack:
  added: []
  patterns: ["fastapi lifespan + asyncio.create_task", "APIRouter 팩토리 주입", "duck-typed last_breakdown"]
key-files:
  created:
    - src/millie_rec/serving/cascade.py
    - src/millie_rec/serving/resolve.py
    - src/millie_rec/serving/levels.py
    - src/millie_rec/serving/rec_log.py
    - tests/serving/test_cascade.py
  modified:
    - src/millie_rec/serving/api.py
decisions:
  - "등록되지 않은 model= 은 셀 배정 variant 로 되돌아가고 forced 만 남긴다(D-01 우선순위 model>셀>기본)"
  - "level 2 가 빈 items 를 내면 level 3 으로 한 번 더 내려간다 — catalog=None 조립에서도 200 유지"
  - "cascade.py 를 resolve.py(해석)·levels.py(비개인화 단계)로 3분할해 전 파일 ≤150줄(Advisor 승인 2026-09-06). cascade.py 가 Resolved·resolve_user·cold_start·nonpersonal 을 __all__ 로 재-export 해 import 경로 무변경"
metrics:
  duration: "약 1.5h"
  tasks: 3
  files: 6
  tests_added: 25
  completed: 2026-09-06
commits: 0   # no_commit — 커밋하지 않는다(사용자 지시 2026-09-05, plan frontmatter no_commit: true)
---

# Phase 5 Plan 06: api 통합 · cascade · 추천 로그 Summary

`GET /api/recommend` 가 `user_key` 를 해석해 Must 5행 level 0 을 내고, 예산 초과·예외에서 1(캐시)→2(세그먼트 인기)→3(전역 인기)으로 내려가며, 모든 응답을 `recommendations` 에 1행 남긴다. `create_app` 은 온보딩·데모·프라이버시·쇼케이스 라우터 4개를 붙이고 lifespan 에서 24h 리플레이 + Nearline 태스크를 돌린 뒤 종료 시 `db.close()` 한다.

## 변경 파일

| 파일 | 상태 | 줄수 |
|---|---|---|
| `src/millie_rec/serving/api.py` | 수정(로직 이관 후 재구성) | 148 |
| `src/millie_rec/serving/cascade.py` | 신설 — 오케스트레이션 | 150 |
| `src/millie_rec/serving/resolve.py` | 신설 — user_key 해석(2차 분할) | 63 |
| `src/millie_rec/serving/levels.py` | 신설 — 비개인화 단계(2차 분할) | 59 |
| `src/millie_rec/serving/rec_log.py` | 신설 — 추천 로그 | 78 |
| `tests/serving/test_cascade.py` | 신설(25건) | 556 |

`src/` 5파일 전부 **≤150줄**(`.claude/rules/simplicity.md`). `git status --short` 는 위 6개만 `??`(레포 전체가 아직 미커밋). **커밋하지 않는다** — `commits: 0`.

### 2차 분할 (Advisor 승인 2026-09-06, 최초 235줄 → 3파일)

| 파일 | 담는 것 |
|---|---|
| `resolve.py` | `Resolved` · `resolve_user` · `_j` · `NOT_FOUND_SNAPSHOT` · 스냅샷 SQL 5개 |
| `levels.py` | `cold_start(cs, seeds, name, k, t0, context, bd)` · `nonpersonal(cs, user, level, categories, k, t0, context, bd, criterion)` — 첫 인자 `cs` 는 `Cascade`(역참조 import 회피로 타입 미표기) |
| `cascade.py` | `Cascade` · `variant_for` · `CELL_VARIANT` · `PIPE_K_MIN` · `KEY_ERR` + 위 이름들의 `__all__` 재-export |

`cascade.py` 가 `__all__ = ["CELL_VARIANT", "NOT_FOUND_SNAPSHOT", "PIPE_K_MIN", "Cascade", "Resolved", "cold_start", "nonpersonal", "resolve_user", "variant_for"]` 로 다시 내보내므로 **`from millie_rec.serving.cascade import Resolved, resolve_user` 등 기존 경로가 그대로 동작**한다(05-08·05-10·`tests/serving/test_cascade.py` 무변경 — 실측 `Resolved is resolve.Resolved` → `True`). 공개 시그니처·동작·반환값 불변, `criteria_labels` 인자 유지.

## cascade 흐름 (텍스트 6줄)

```
respond(user_key, snapshot_id, model, k, context, seeds)
  ├ user_key 형식 불일치 → 422 (privacy_api.USER_KEY_RE 재사용, user_key="" 는 익명)
  ├ user_key 없음 → levels.cold_start: seeds+variant 있으면 level 0 1행(k 그대로) · 없으면 nonpersonal(3)
  └ user_key 있음 → resolve.resolve_user(users + 최신/지정 스냅샷, 남의 snapshot_id 는 404)
       ├ found ∧ consent ∧ snapshot → _personal: 상태 로드(feature) → pipe.recommend(max(k,24))(pipeline)
       │     → 예산 초과 ∨ 예외면 _degrade(캐시 hit → 1 · miss → levels.nonpersonal(2) → 비면 3)
       │     → 정상이면 merge_breakdown → compose_rows 5행 → cache.put → build_response(compose)
       └ 아니면 levels.nonpersonal(3): trending + fresh_picks 2행, 가중치 0
  → 마지막에 항상 _logged → rec_log.log_recommendation(응답 직전 1 INSERT, 실패해도 응답 유지)
```

## TDD 증거

### RED (Task 1 — 스텁 + 25건)

```
$ uv run pytest tests/serving/test_cascade.py --no-header
21 failed, 4 passed, 2 warnings in 0.68s
```

전부 `AssertionError` — `ImportError`·`AttributeError`·`TypeError`·`sqlite3.OperationalError` 0건. 발췌 3건:

```
E       AssertionError: assert ['trending'] == ['trending', 'fresh_picks']
E         Right contains one more item: 'fresh_picks'

E       AssertionError: assert [None, None] == ['u-a-1', None]
E         At index 0 diff: None != 'u-a-1'

E       AssertionError: assert [5] == [5, 24]
E         Right contains one more item: 24
```

같은 시점 기존 회귀 4파일:

```
$ uv run pytest tests/serving/test_recommend_level0.py tests/serving/test_api_weights.py \
    tests/serving/test_schemas.py tests/test_architecture.py --no-header
16 passed, 2 warnings in 0.28s
```

### GREEN (Task 2 — Cascade.respond 완성 + rec_log)

```
$ uv run pytest tests/serving --ignore=tests/serving/test_smoke.py \
    --ignore=tests/serving/test_dashboard_api.py --ignore=tests/serving/test_bench.py \
    tests/test_architecture.py --no-header
135 passed, 2 warnings in 1.03s
```

기존 단정 무수정 증거(C10 실측 7 + 4):

```
$ uv run pytest tests/serving/test_recommend_level0.py tests/serving/test_api_weights.py --no-header
11 passed, 2 warnings in 0.31s
```

`tests/serving/test_smoke.py` 는 05-09 게이트 이관이지만 `app.server` 를 부르지 않는 10건만 따로 돌려 자기 회귀를 확인했다(`-k "not server_module"` → `10 passed, 2 deselected`).

### REFACTOR (Task 3)

```
$ uv run ruff format --check <4파일> && uv run ruff check <4파일>
4 files already formatted
All checks passed!
```

### 2차 분할 후 재검증 (Advisor 수정 브리프 2026-09-06)

분할 전과 **테스트 수·단정 모두 동일**하고 passed 수도 같다.

```
$ wc -l src/millie_rec/serving/cascade.py src/millie_rec/serving/resolve.py \
        src/millie_rec/serving/levels.py
     150 src/millie_rec/serving/cascade.py
      63 src/millie_rec/serving/resolve.py
      59 src/millie_rec/serving/levels.py

$ uv run ruff format --check <cascade·resolve·levels·test_cascade> && uv run ruff check <같은 경로>
4 files already formatted
All checks passed!

$ uv run pytest tests/serving/test_cascade.py --no-header
25 passed, 2 warnings in 0.83s

$ uv run pytest tests/serving --ignore=tests/serving/test_smoke.py \
    --ignore=tests/serving/test_dashboard_api.py --ignore=tests/serving/test_bench.py \
    tests/test_architecture.py --no-header
135 passed, 2 warnings in 1.31s

$ uv run pytest tests/serving/test_recommend_level0.py tests/serving/test_api_weights.py --no-header
11 passed, 2 warnings in 0.26s

$ uv run pytest tests/serving/test_smoke.py -k "not server_module" --no-header
10 passed, 2 deselected, 2 warnings in 0.23s
```

`tests/serving/test_cascade.py` 는 **한 줄도 고치지 않았다**(재-export 덕분에 import 경로 조정 불필요) — `grep -c "def test_"` → 25, `grep -c "from millie_rec.serving.cascade import"` → 1.

## TDD Gate Compliance

RED(신규 25건 중 21건 `AssertionError`) → GREEN(135 passed) → REFACTOR(ruff 클린 + 재통과) 순서를 지켰다. `pytest.skip` 없음, 기존 테스트 단정 수정 없음. `no_commit: true` 라 `test(...)`/`feat(...)` 커밋은 남기지 않는다 — 게이트 증거는 위 pytest 출력이다.

## 인계 시그니처 (05-08 · 05-09 · 05-10 · 05-12 가 소비, 실제 코드 복사)

`Resolved`·`resolve_user`·`NOT_FOUND_SNAPSHOT` 의 **정의는 `serving/resolve.py`**, `cold_start`·`nonpersonal` 의 정의는 **`serving/levels.py`** 지만, `cascade.py` 가 전부 재-export 하므로 아래 import 경로를 그대로 쓰면 된다.

```python
# src/millie_rec/serving/cascade.py (정의 위치는 resolve.py — 재-export)
CELL_VARIANT = {"A": "hybrid", "B": "hybrid_div"}
PIPE_K_MIN = 2 * ROW_SIZE                      # 24 — _personal 만 사용(cold-start 는 k 그대로)
NOT_FOUND_SNAPSHOT = "snapshot_id not found for user_key"

@dataclass(frozen=True)
class Resolved:
    user_key: str
    found: bool = False
    consent: bool = False
    cell: str | None = None
    snapshot_id: str | None = None
    seeds: tuple[int, ...] = ()
    categories: tuple[str, ...] = ()
    criterion: str | None = None
    persona_name: str | None = None
    snapshots_count: int = 0
    latest_created_at: str | None = None

def resolve_user(db: Database, user_key: str, snapshot_id: str | None) -> Resolved
def variant_for(cell, model, pipelines: dict[str, Pipeline], default: str | None) -> str | None

# src/millie_rec/serving/levels.py (cascade.py 가 재-export). 첫 인자 cs 는 Cascade 인스턴스
def cold_start(cs, seeds, name, k, t0, context, bd) -> RecommendResponse
def nonpersonal(cs, user, level, categories, k, t0, context, bd, criterion) -> RecommendResponse

class Cascade:
    def __init__(self, pipelines, fallback, *, catalog=None, db, neighbors=None, store=None,
                 cache, weights=None, default=None, all_categories=(), criteria_labels=None,
                 now: Callable[[], float] | None = None) -> None
    def respond(self, *, user_key: str | None, snapshot_id: str | None, model: str | None,
                k: int, context: str | None,
                seeds: tuple[int, ...]) -> tuple[RecommendResponse, bool]
```

```python
# src/millie_rec/serving/rec_log.py
SQL_REC_INS = ("INSERT INTO recommendations(recommendation_id, user_key, snapshot_id, "
               "model_version, cell, forced, fallback_level, latency_total_ms, "
               "latency_breakdown, weights, rows, ts) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)")
SUB_KEYS = ("retrieval", "ranking", "rerank")

def abbreviate_rows(rows: Sequence[Row]) -> list[dict]          # row_id·book_id·position 3키만
def merge_breakdown(bd: dict[str, float], sub: object) -> dict[str, float]   # pipeline 키 유지
def log_recommendation(db: Database, resp: RecommendResponse, *, user_key: str | None,
                       snapshot_id: str | None, cell: str | None, forced: bool,
                       now: Callable[[], float] | None = None) -> None
```

`create_app` 시그니처는 **불변**(`pipelines, fallback, *, catalog=None, db, neighbors=None, book_stats=None, state=None, weights=None`). 05-08 의 `create_app(..., state=store, book_stats=stats)` 호출은 그대로 동작한다.

### `app.state` 노출 (테스트·05-08 접근용)

| 이름 | 값 | 비고 |
|---|---|---|
| `app.state.cascade` | `Cascade` | 항상 존재 |
| `app.state.nearline` | `NearlineLoop` 또는 `None` | `state=None` 이면 `None`(루프·리플레이 없음) |
| `app.state.store` | `create_app(state=)` 로 받은 객체 | 그대로 |
| `app.state.cache` | `Level1Cache` | 항상 존재. `invalidate` 는 demo·privacy 라우터에 콜백으로도 주입 |

### 라우터 배선

```python
app.include_router(onboarding_router(db=db, catalog=catalog))
app.include_router(demo_router(db=db, catalog=catalog, wake=wake_fn, invalidate=inv))
app.include_router(privacy_router(db=db, catalog=catalog, state=state, weights=weights, invalidate=inv))
try:  # 05-07 병렬
    from millie_rec.serving.dashboard_api import build_router as dashboard_router
    app.include_router(dashboard_router(db=db))
except ImportError:
    log.info("dashboard_api not present yet (wave 2 parallel)")
```

`wake_fn` 은 `nearline.waker(loop)` 가 만든 `loop.call_soon_threadsafe(wake.set)` 클로저를 감싼다 — 동기 핸들러가 `asyncio.Event.set()` 을 직접 부르지 않는다(Advisor 확정 13).

**dashboard_api 선택 import 실측:** 이 플랜 종료 시점에 05-07 의 `serving/dashboard_api.py` 가 이미 존재해 **선택 import 가 실제로 붙었다**. `create_app(pipelines={}, fallback=GlobalPopularFallback(None), db=…)` 조립에서 `GET /api/showcase` → **200**, `GET /health` → 200 실측(2026-09-06).

## `nearline_lag_s` (revision D4)

`RecommendOut.nearline_lag_s` 는 **채우지 않는다 — 항상 `None`**(선택 필드, 응답 형태 freeze 유지). 값을 넣으려면 `RecommendResponse` 에 필드를 더해야 하는데 `contracts.py` 는 🧊 freeze 대상이다. 대시보드의 `feature_freshness_s`(05-12)가 같은 정보를 `nearline.last_run` 에서 계산한다.

## Deviations from Plan

### 1. [Rule 1 - 계약 해석] 등록되지 않은 `model=` 은 "기본 variant" 가 아니라 셀 variant 로 되돌아간다

- **발견 위치:** Task 2, `test_cell_assignment_picks_variant_and_model_query_forces`
- **문제:** 플랜 `<behavior>` 문장은 "`model=pop`(등록 안 됨) → 기본 variant"라고 적혀 있으나, 같은 플랜의 `variant_for` 구현 명세(Task 2-b)는 `model not in pipelines` → 셀 배정 → 그것도 없으면 default 순서다. `user_key` 가 있어 셀이 배정된 요청에서는 두 문장이 어긋난다.
- **결정:** 구현 명세(D-01 우선순위 `model=` > 셀 > 기본)를 따랐다. 셀 A 사용자의 `model=pop` 은 `hybrid_v1` + `forced=true`. 셀이 없는 `seeds` cold-start 에서는 기존대로 기본 variant(`tests/serving/test_recommend_level0.py::test_registered_only_pop_but_model_cf_uses_default_without_error` 가 계속 통과).
- **반영:** 이 플랜이 새로 쓴 테스트의 단정을 그 규칙으로 적었다(기존 테스트 무수정).

### 2. [Rule 2 - 정확성] level 2 가 빈 items 를 내면 level 3 으로 한 번 더

- **발견 위치:** Task 2, `test_pipeline_exception_always_200_no_leak` 의 `catalog=None` 조립
- **문제:** `segment_popular(catalog=None, …)` 는 `[]` 를 돌려주므로 level 2 응답이 빈 trending 1행이 된다.
- **수정:** `_degrade` 가 `seg.rows[0].items` 가 비면 `_nonpersonal(..., FALLBACK_GLOBAL_POP, ...)` 를 한 번 더 부른다(플랜 Task 2-c 에 명시된 동작).

### 3. [Rule 3 - 블로킹] `from millie_rec.serving import rec_log` (모듈 참조 import)

- **이유:** `rec_log.log_recommendation` 을 monkeypatch 로 감쌀 수 있어야 B3 acceptance(“spy 호출 수 == 응답 수”)가 성립한다. `from … import log_recommendation` 이면 cascade 네임스페이스에 바인딩돼 spy 가 걸리지 않는다.
- **위험 확인:** `serving/__init__.py` → `api` → `cascade` → `serving` 부분 초기화 경로에서 `_handle_fromlist` 가 서브모듈을 정상 로드한다. 135 tests + 공개 표면 import 로 실측 확인.

## Advisor 보고 (범위 밖 · 미결)

1. ~~🔴 `cascade.py` 235줄 — 150줄 규칙 위반~~ → **해소: 2파일 분할(Advisor 승인 2026-09-06).** 제안 ①+② 를 그대로 실행해 `resolve.py`(63) · `levels.py`(59) 를 신설하고 `cascade.py` 를 150줄로 줄였다. `__all__` 재-export 로 05-08·05-10·테스트의 import 경로는 무변경이며, 테스트 수·단정·passed 수 전부 분할 전과 같다(위 "2차 분할 후 재검증"). `api.py`(148) · `rec_log.py`(78) 포함 **serving 신규·수정 5파일 전부 ≤150**.
2. `grep -c "from millie_rec.serving.onboarding_api import" api.py` 는 **1 이 아니라 2** 다(플랜 acceptance 기대값 1). ruff isort 가 `build_router as onboarding_router` 와 `load_meta` 를 별도 줄로 나눈 결과이고 의미는 같다. 게이트에서 오탐으로 처리해 달라. 같은 이유로 `grep -c "PIPE_K_MIN" cascade.py` 는 **2 가 아니라 3** 이다(정의 1 + `__all__` 1 + `_personal` 사용 1 — 분할로 늘어난 재-export 목록 때문).
3. `Cascade.criteria_labels`(= `onboarding_meta.json` 의 criterion id→라벨)는 **주입만 받고 아직 쓰지 않는다.** `compose`/`badges` 는 라벨이 아니라 criterion **id** 를 쓴다. 플랜 must_haves 가 시그니처에 명시해 유지했다. 쓸 곳이 없다면 05-09 에서 인자와 `api.py` 의 `load_meta()` 호출을 함께 걷어내는 편이 낫다.
4. **`make smoke` · `tests/serving/test_smoke.py` 전체 · `tests/app/**` 은 돌리지 않았다** — 05-08 이 `app/` 을 같은 시각에 고치는 중이라 플랜 revision A5 가 05-09 wave 2 게이트로 이관했다. `test_smoke.py` 중 `app.server` 를 부르지 않는 10건은 통과 확인.
5. `Database.close()` 는 **lifespan 이 도는 스레드의 연결만** 닫는다(`threading.local`). 요청 스레드풀의 연결은 프로세스 종료 시 정리된다. 단일 워커 데모에서는 문제없으나 05-09 Codex 리뷰 항목으로 남긴다.
6. 추천 로그 INSERT 실패는 `log.exception` 후 삼킨다(T-05-06-07) — 추천이 로그 장애의 인질이 되지 않는 대신 로그가 유실될 수 있다. 의도한 트레이드오프.

## PROGRESS 1줄 후보 (05-09 Advisor 가 기록)

1. `serving/cascade.py` 신설 — 아키 §9-3 파일 목록 외, `api.py` 150줄 유지용(Advisor 확정 3). 150줄.
2. `serving/rec_log.py` 신설 — 아키 §9-3 목록 외, 추천 로그 D-12(Advisor 확정 17 B3).
3. `serving/resolve.py` 신설 — 아키 §9-3 목록 외, `cascade.py` 150줄 유지용 user_key 해석 분리(Advisor 승인 2026-09-06).
4. `serving/levels.py` 신설 — 아키 §9-3 목록 외, 같은 이유로 cold-start·비개인화 단계 분리(Advisor 승인 2026-09-06). `cascade.py` 가 3·4 의 이름을 `__all__` 로 재-export 해 import 경로는 바뀌지 않는다.
5. D-04(level 3 = trending + fresh_picks)의 **예외: `seeds` 쿼리 cold-start 경로는 1행 trending 유지**(Advisor 확정 7 조건부 호환) — CLI·bench·`make smoke` 의 `?seeds=` 계약을 깨지 않기 위해서.

## Known Stubs

없음. `nearline_lag_s` 는 스텁이 아니라 **의도적 미채움**(위 §`nearline_lag_s`).

## Threat Flags

없음 — 이 플랜이 만든 표면은 전부 `<threat_model>` T-05-06-01~08 안에 있다. `GET /api/recommend` 의 `user_key`·`snapshot_id` 는 각각 `USER_KEY_RE` 422 와 소유 검사 404 로 막았고 SQL 은 전부 `?` 바인딩이다(`grep -c "execute(f"` → 3파일 모두 0).

## Self-Check: PASSED

- `src/millie_rec/serving/cascade.py` FOUND · `resolve.py` FOUND · `levels.py` FOUND · `rec_log.py` FOUND · `src/millie_rec/serving/api.py` FOUND · `tests/serving/test_cascade.py` FOUND
- 커밋 해시 없음 — `no_commit: true`(의도)
- `grep -c "def test_" tests/serving/test_cascade.py` → 25 (분할 전후 동일)
- `wc -l` — cascade 150 · resolve 63 · levels 59 · api 148 · rec_log 78 → 전부 ≤150
- acceptance grep 실측: `over_budget(` 1 · `cache.put(` 1 · `cache.get(` 1 · `getattr(pipe, "last_breakdown", None)` 1 · `PIPE_K_MIN` 3(재-export 포함) · `INSERT INTO recommendations` cascade·resolve·levels 0 / rec_log 1 · `execute(f` 0 · `include_router(` 4 · `create_task(` 1 · `db.close()` 1 · star 의존 위반 0(신규 2파일 포함)
- 재-export 실측: `from millie_rec.serving.cascade import Resolved, resolve_user` → `Resolved is resolve.Resolved` `True`, `resolve_user is resolve.resolve_user` `True`

## Codex 수정 반영 (2026-09-06, 브리프 B)

Advisor 승인 Codex 리뷰 지적 5건(F1·F3·F6·F7·F4 serving 절반)을 cascade 계열 4파일에 반영했다. 계약(`contracts.py`·`schemas*.py`)·`api.py`·`compose.py`·`state.py` 는 건드리지 않았다.

### F1 (적대 high) — 철회·미등록 응답의 추천 로그를 익명으로
`Cascade.respond` 가 `personal = r.found and r.consent` 를 계산해, 개인화가 아닌 응답은 `recommendations` 행에 `user_key`·`snapshot_id`·`cell` 을 전부 `NULL` 로 넣는다. 응답 자체는 D-12 대로 계속 1행 기록하고, 응답 본문의 `user_key`·`cell` 에코는 그대로다. `DELETE …/personalization` 이 4테이블을 지운 뒤 다음 요청이 같은 `user_key` 로 행을 되살리던 경로가 사라졌다.

### F3 (적대 high) — 강등 단계마다 독립 가드
`levels.py` 의 `nonpersonal` 을 세 조각으로 나눴다. `_staged` 가 한 단계(재료 → `compose_rows` → `build_response`)를 그대로 수행하고, `nonpersonal` 이 단계마다 `try` 로 감싼다. level 2(`segment_popular`·compose·build) 실패 → `log.exception` 후 level 3 재시도(카테고리는 전역으로 비운다), level 3 실패 → `minimal()` 이 카탈로그를 건드리지 않는 200 을 낸다(`model_version=MODEL_VERSION_FALLBACK`, `fallback_level=3`, 빈 trending 1행, 가중치 0). `HTTPException`(404·422)은 두 자리 모두 `raise` 로 통과시킨다. 예외 문구는 응답에 실리지 않는다.
`variant_for` 가 `None` 을 돌려주는 경로가 level 3 에 스냅샷 카테고리를 넘기던 기존 동작은 유지했다(강등으로 내려온 경우에만 `categories = ()`).

### F6 (일반 P2) — 스냅샷 동률 정렬
`resolve.py` `SQL_SNAP_ONE` 의 `ORDER BY created_at DESC, snapshot_id DESC` 를 `created_at DESC, rowid DESC` 로 바꿨다. `created_at` 이 초 단위라 같은 초에 두 벌이 들어오면 `snapshot_id` 사전순(사실상 난수)이 이기던 문제. 이제 나중에 삽입된 스냅샷이 최신이다.

### F7 (일반 P2 / D-09) — feature 구간에 `resolve_user` 포함
`tf = perf_counter()` 를 `respond` 안 `resolve_user` **앞**으로 옮기고 `_personal(..., tf)` 로 넘긴다. D-09 정의(`feature` = state·스냅샷 로드)와 실제 계측이 일치한다.

### F4 serving 절반 (일반 P1) — 부스트 신호를 `UserState.context` 로
`_personal` 이 `reset_boost`·`session_active` 를 판정한 뒤 `pipe.recommend` **전에** `dataclasses.replace` 로 `user.context` 에 넣는다(`context["reset_boost"] = "1"` · `context["session_active"] = "1"`, 거짓이면 키 없음, 값은 계약대로 `str`). 주입된 1-인자 `weights(user)` 를 부르는 리트리버도 같은 신호를 본다. 표시용 `self.weights(user, **kw)` 는 그대로라 기존 `test_session_active_and_reset_boost_kwargs_reach_weights` 는 무변경 통과. ranking 쪽 절반(`state_weights` 가 kwargs 또는 이 context 키를 존중)은 Worker C 담당.

### 변경 파일 · 줄 수

| 파일 | 줄 | 비고 |
|---|---|---|
| `src/millie_rec/serving/cascade.py` | 150 | F1·F4·F7 (상한 150 유지) |
| `src/millie_rec/serving/levels.py` | 97 | F3 — `_staged`·`minimal` 신설 |
| `src/millie_rec/serving/resolve.py` | 64 | F6 — SQL 1줄 + 주석 1줄 |
| `src/millie_rec/serving/rec_log.py` | 78 | 변경 없음(F1 은 호출 쪽에서 해결) |
| `tests/serving/test_cascade.py` | 699 | 테스트 6개 추가(25 → 31), 기존 단정 무변경 |

옮긴 이름 없음 — `cascade.py` 가 150줄에 들어가 `__all__` 재-export 목록은 그대로다. `levels.py` 신규 `_staged`·`minimal` 은 모듈 내부용이라 재-export 하지 않았다.

### Red / Green

```
# Red — 구현 전 (tests/serving/test_cascade.py)
6 failed, 25 passed, 2 warnings in 0.87s
# Green — 구현 후
31 passed, 2 warnings in 0.73s
```

Red 6건 전부 `AssertionError` 로 확인했다(`KeyError` 로 떨어지던 F4 테스트는 `dict.get` 으로 바꿔 단정 실패로 만들었고, F3 두 건은 `raise_server_exceptions=False` 로 500 을 응답으로 받아 `assert 500 == 200` 단정 실패가 되게 했다). F3 두 테스트는 가짜 카탈로그의 실패 범위를 좁힌 뒤 `levels.py` 를 수정 전 형태로 임시 되돌려 Red 를 재확인했다.

회귀 게이트:
```
uv run pytest tests/serving/test_cascade.py tests/serving/test_after_completion.py \
  tests/serving/test_recommend_level0.py tests/serving/test_api_weights.py \
  tests/serving/test_fallback_levels.py tests/test_architecture.py --no-header
63 passed, 2 warnings in 0.97s
```
`uv run ruff format --check` · `uv run ruff check` 대상 5파일 전부 통과.

### 남긴 것

- 브리프 범위대로 `make smoke`·전체 스위트·서버 기동은 돌리지 않았다(다른 Worker 가 `privacy_api.py`·`ranking/blend.py`·`nearline.py`·`demo_api.py` 를 동시에 편집 중).
- F4 는 serving 절반만이다. `ranking.state_weights` 가 context 키를 읽도록 바뀌기 전까지는 리트리버가 신호를 "볼 수 있는" 상태이고 실제 반영은 Worker C 의 변경에 달려 있다.
- 비개인화 경로(level 2·3 단독 응답)의 `latency_breakdown` 에는 여전히 `feature` 키가 없다. D-09 는 level 0 기준이라 그대로 뒀다.
