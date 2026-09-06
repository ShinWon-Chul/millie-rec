---
phase: 05-must
plan: 03
subsystem: api
tags: [fastapi, sqlite, cache, fallback, tdd]

requires:
  - phase: 01-local-serving-skeleton
    provides: "serving/fallback.py GlobalPopularFallback·trending_row · serving/db.py Database(thread-local·PRAGMA·apply_schema) · schema.sql 7테이블"
  - phase: 04-freeze
    provides: "🧊 freeze — contracts.py(BUDGET_MS 200 · CACHE_TTL_S 600 · FALLBACK_*) 무변경 전제"
provides:
  - "fallback level 1 캐시 Level1Cache((user_key, snapshot_id, variant) 키 · TTL 600s · invalidate(user_key))"
  - "예산 판정 over_budget(elapsed_ms) — 모듈 전역 BUDGET_MS 를 호출 시점에 읽어 monkeypatch 주입 가능"
  - "level 2 재료 segment_popular(catalog, user, categories, k) — 카테고리 인기에서 seen 제외 상위 k"
  - "SQLite DML 헬퍼 Database.execute·executemany·query(sqlite3.Row)·close·backup — 모두 ? 바인딩, 문마다 커밋"
  - "schema.sql 인덱스 2개(idx_events_user_ts · idx_recommendations_user_ts, 멱등 DDL)"
affects: [05-04 state·nearline, 05-05 demo_api·privacy_api, 05-06 cascade·api 통합, 05-09 Advisor 검증·Codex]

tech-stack:
  added: []
  patterns:
    - "TTL 캐시는 dict + threading.Lock 수작업(캐시 데코레이터 금지, ../.claude/rules/simplicity.md)"
    - "DML 은 with con: 컨텍스트로 문마다 커밋 — 다른 연결(Nearline 스레드)에서 보이는 것을 테스트로 단정"
    - "테스트 주입용 상수는 모듈 상단 바인딩(from millie_rec.contracts import BUDGET_MS)"

key-files:
  created:
    - tests/serving/test_fallback_levels.py
    - tests/serving/test_db.py
  modified:
    - src/millie_rec/serving/fallback.py
    - src/millie_rec/serving/db.py
    - src/millie_rec/serving/schema.sql

key-decisions:
  - "GlobalPopularFallback.recommend 는 segment_popular(catalog, user, (), k) 위임으로 축소 — 반환값·시그니처·name 불변(회귀 테스트가 지킴), level 2·3 가 한 구현을 공유"
  - "backup() 의 대상 연결은 with 문 대신 try/finally 로 명시적 close — with sqlite3.connect(dest) 는 커밋만 하고 연결을 닫지 않아 파일 핸들이 남는다"
  - "connect() 에 row_factory = sqlite3.Row 추가 — 기존 fetchone()[0] 인덱스 접근(row_counts·ok)은 그대로 동작"

patterns-established:
  - "Level1Cache: 값 = (만료시각, rows, model_version), 만료는 get 이 조회 시 제거(lazy eviction)"
  - "executemany 는 문별 rowcount 합산 — INSERT OR IGNORE 중복이 0 으로 빠져 duplicates 집계가 된다"

requirements-completed: [SERV-03]

duration: ~20min
completed: 2026-09-06
---

# Phase 5 Plan 03: fallback 재료 · SQLite 쓰기 헬퍼 Summary

**fallback cascade 의 재료 3종(level 1 TTL 캐시 · 예산 판정 · level 2 세그먼트 인기)과 커밋을 보장하는 SQLite DML 헬퍼 5종, 인덱스 2개를 TDD 한 사이클(RED 16 → GREEN 32)로 추가했다. cascade 오케스트레이션은 05-06 몫이라 이 플랜은 재료만 만든다.**

## Performance

- **Duration:** 약 20분
- **Tasks:** 3/3 (RED · GREEN · REFACTOR)
- **Files modified:** 5 (신규 2 · 수정 3)
- **Commits:** `commits: 0   # no_commit` — 커밋하지 않는다(사용자 지시 2026-09-05, plan frontmatter `no_commit: true`). 변경은 작업 트리에 남겨 두었다.

## 변경 파일

| 파일 | 상태 | 내용 | 줄 수 |
|---|---|---|---|
| `src/millie_rec/serving/fallback.py` | 수정 | `Level1Cache` · `over_budget` · `segment_popular` · `CacheKey` 추가, `BUDGET_MS`/`CACHE_TTL_S` 모듈 바인딩 | 45 → **119** (≤150) |
| `src/millie_rec/serving/db.py` | 수정 | `execute` · `executemany` · `query` · `close` · `backup` 추가, `connect()` 에 `row_factory=sqlite3.Row` | 60 → **95** (≤150) |
| `src/millie_rec/serving/schema.sql` | 수정 | `CREATE INDEX IF NOT EXISTS` 2개 + L1 머리 주석 갱신 | +4줄 |
| `tests/serving/test_fallback_levels.py` | 신규 | 9건(계약 2 · 정확성 4 · 안전성 3) | 149 |
| `tests/serving/test_db.py` | 신규 | 8건(계약 2 · 정확성 4 · 안전성 2) | 116 |

`must_not_touch` 목록은 하나도 건드리지 않았다(`contracts.py` · `schemas*.py` · `api.py` · `compose.py` · `state.py` · `serving/__init__.py` · `app/**` · `tests/test_architecture.py` · `tests/serving/test_smoke.py` 포함).

## TDD 증거

### RED (Task 1 — 스텁 상태, 실행 `uv run pytest tests/serving/test_fallback_levels.py tests/serving/test_db.py --no-header`)

```
16 failed, 1 passed in 0.24s
```

실패 사유는 전부 `AssertionError` 였고 `ImportError`·`AttributeError`·`TypeError`·`sqlite3.OperationalError`·collection error 는 0건이다(`grep -cE "ImportError|AttributeError|TypeError|OperationalError|SyntaxError"` → `0`). 발췌:

```
>       assert names == ["idx_events_user_ts", "idx_recommendations_user_ts"]
E       AssertionError: assert [] == ['idx_events_...ions_user_ts']
E
E         Right contains 2 more items, first extra item: 'idx_events_user_ts'
tests/serving/test_db.py:99: AssertionError
```

```
>       assert db.execute("INSERT INTO users(user_key) VALUES(?)", (evil,)) == 1
E       assert -1 == 1
E        +  where -1 = execute('INSERT INTO users(user_key) VALUES(?)', ("x'; DROP TABLE users; --",))
E        +    where execute = <millie_rec.serving.db.Database object at 0x119392710>.execute
tests/serving/test_db.py:107: AssertionError
```

```
E       AssertionError: assert None == ((Row(row_id='trending', title='지금 많이 읽는 책', purpose='fallback', items=(ScoredItem(book_id=1, score=1.0, ...))), 'hybrid_v1')
E        +  where None = get('u', 'snap_1', 'hybrid')
```

```
E       AssertionError: assert False
E        +  where False = over_budget(200.1)
```

RED 시점의 기존 테스트는 그대로 통과했다 — `uv run pytest tests/serving/test_smoke.py tests/test_architecture.py --no-header` → `15 passed, 2 warnings in 0.25s`.

### GREEN (Task 2)

```
32 passed, 2 warnings in 0.29s
```
(신규 17 + `tests/serving/test_smoke.py` 12 + `tests/test_architecture.py` 3)

### REFACTOR (Task 3)

```
4 files already formatted
All checks passed!
32 passed, 2 warnings in 0.30s
```

`uv run ruff format --check` + `uv run ruff check` 를 이 플랜의 4개 파일에만 실행했다(다른 serving 파일은 병렬 Worker 소유라 포맷하지 않았다). 회귀 확인으로 `tests/serving/test_recommend_level0.py tests/serving/test_api_weights.py` 도 읽기 전용으로 1회 실행 → `11 passed`(`GlobalPopularFallback` 내부를 위임 형태로 바꾼 것이 기존 level 0·가중치 경로에 영향이 없음을 확인).

## TDD Gate Compliance

| Gate | 상태 | 근거 |
|---|---|---|
| RED | 통과 | 신규 17건 중 16건이 `AssertionError` 로 실패, 1건(`test_global_popular_fallback_regression_unchanged`)은 기존 동작 회귀라 설계상 통과 |
| GREEN | 통과 | 구현 후 32 passed, failed 0 |
| REFACTOR | 통과 | docstring 정리 + ruff format/check 클린, 재실행 32 passed |

커밋 게이트(`test(...)` → `feat(...)`)는 **없다** — plan frontmatter `no_commit: true` 라 커밋을 만들지 않았다. 게이트 증거는 위 pytest 출력으로 대체한다.

## 인계 시그니처 (05-04 · 05-05 · 05-06 이 그대로 소비)

```python
# src/millie_rec/serving/fallback.py
from millie_rec.contracts import BUDGET_MS, CACHE_TTL_S, Catalog, Row, ScoredItem, UserState

TRENDING_ROW_ID = "trending"
TRENDING_TITLE = "지금 많이 읽는 책"
TRENDING_PURPOSE = "fallback"
SOURCE_POPULARITY = "popularity"
CacheKey = tuple[str, str, str]  # (user_key, snapshot_id, variant)


class GlobalPopularFallback:            # 불변: name = "fallback"
    def __init__(self, catalog: Catalog | None) -> None
    def recommend(self, user: UserState, k: int) -> list[ScoredItem]


def trending_row(items: Sequence[ScoredItem]) -> Row


def segment_popular(
    catalog: Catalog | None, user: UserState, categories: Sequence[str], k: int
) -> list[ScoredItem]


def over_budget(elapsed_ms: float) -> bool


class Level1Cache:
    def __init__(
        self, *, ttl_s: float = CACHE_TTL_S, now: Callable[[], float] | None = None
    ) -> None
    def put(
        self,
        user_key: str,
        snapshot_id: str,
        variant: str,
        rows: Sequence[Row],
        model_version: str,
    ) -> None
    def get(
        self, user_key: str, snapshot_id: str, variant: str
    ) -> tuple[tuple[Row, ...], str] | None
    def invalidate(self, user_key: str) -> int
    def __len__(self) -> int
```

```python
# src/millie_rec/serving/db.py (기존 connect·apply_schema·table_names·row_counts·ok·resolve_db_path 불변)
class Database:
    def execute(self, sql: str, params: Sequence[object] = ()) -> int
    def executemany(self, sql: str, rows: Sequence[Sequence[object]]) -> int
    def query(self, sql: str, params: Sequence[object] = ()) -> list[sqlite3.Row]
    def close(self) -> None
    def backup(self, dest: Path) -> Path
```

호출 쪽이 알아야 할 의미:

- `execute` 는 **DML 1문 + 커밋**이고 반환은 `rowcount` 다. `INSERT OR IGNORE` 중복은 `0`, `DELETE` 는 삭제된 행 수. 값은 반드시 `?` 바인딩으로 넘긴다(f-string 금지).
- `executemany` 는 문별 `rowcount` 합계다(드라이버의 `executemany` 를 쓰지 않는다). 중복 3건 중 2건 삽입 → `2`.
- `query` 는 `sqlite3.Row` 목록이라 `r["col"]` · `dict(r)` 가 된다.
- `Level1Cache.get` 은 만료 시 항목을 지우고 `None` 을 준다. `put` 은 매 level 0 성공마다, `get` 은 fallback 경로에서만 호출한다(읽기 정책의 정본은 05-06 cascade).
- `over_budget` 은 **초과만** True(`200.0` 은 False). 테스트에서 `monkeypatch.setattr("millie_rec.serving.fallback.BUDGET_MS", 1)` 로 주입할 수 있다.
- `segment_popular(catalog, user, (), k)` 는 전역 인기(level 3 재료), `categories` 를 주면 level 2 재료다. `catalog=None` 이면 `[]`.

**Codex 필수 리뷰 대상: `src/millie_rec/serving/db.py` 쓰기 헬퍼**(`../.claude/rules/codex-review.md` 표) — 실행은 wave 3 Advisor(plan 05-09).

## Advisor 보고 (재량 판단·경계 밖 항목)

1. **`GlobalPopularFallback.recommend` 를 `segment_popular` 위임으로 축소**(plan Task 2-a 가 허용한 선택지). 이름·시그니처·`name`·반환값 불변이고 `tests/serving/test_smoke.py` 의 회귀 단정과 신규 회귀 테스트가 모두 통과한다. 부수 효과 하나: 내부에서 `catalog.popular([], n=...)` 처럼 **categories 를 위치 인자로** 넘긴다. 저장소의 모든 `popular` 구현(`data/catalog_kr.py` · 테스트 가짜 4개)이 `popular(self, categories=(), n=50)` 시그니처이고 `if not categories` 분기라 `[]` 와 `()` 가 동치임을 확인했다.
2. **`backup()` 은 `with sqlite3.connect(dest)` 대신 `try/finally` + `close()`** 로 구현했다. `with` 는 트랜잭션만 닫고 연결을 닫지 않아 백업 파일 핸들이 남는다(파일 핸들 누수 = Rule 2 성격의 보정).
3. **`serving/__init__.py` 는 건드리지 않았다**(05-01 소유). 새 공개 이름 `Level1Cache` · `segment_popular` · `over_budget` 을 `__all__` 에 노출할지는 Advisor/05-01 판단이다. 05-06 cascade 는 같은 슬라이스 내부 import(`from millie_rec.serving.fallback import Level1Cache`)로 쓰면 되므로 노출은 필수가 아니다.
4. **전역 검증은 하지 않았다** — 병렬 Worker 규칙에 따라 `uv run pytest` 전체·`make smoke` 는 실행하지 않았다. wave 1 종료 후 Advisor 1회가 남아 있다(기준선 327 passed + 이 플랜 17건).
5. **인덱스 2개는 `schema.sql` 끝에 append** 했고 컬럼 변경은 없다. `apply_schema()` 를 두 번 호출해도 인덱스 수가 같음을 테스트로 단정했다.

## Known Stubs

없음 — RED 단계의 스텁 5종은 Task 2 에서 전부 실제 구현으로 교체되었고, 남은 `return -1`·`return []` 형태의 자리표시자는 없다.

## Threat Flags

없음 — 이 플랜이 새로 만든 표면은 HTTP 엔드포인트가 아니라 내부 헬퍼다. plan `<threat_model>` 의 `mitigate` 6건(SQL 인젝션 · 캐시 메모리 · 캐시 교차 노출 · 커밋 누락 · WAL 백업 손상)은 각각 `?` 바인딩 테스트 · TTL 만료 제거 · 키의 `user_key` 포함 · 별도 연결 가시성 테스트 · `con.backup()` 사용으로 이행했다.

## Self-Check: PASSED

- `src/millie_rec/serving/fallback.py` FOUND (119줄) · `src/millie_rec/serving/db.py` FOUND (95줄) · `src/millie_rec/serving/schema.sql` FOUND (`CREATE INDEX IF NOT EXISTS` 2건)
- `tests/serving/test_fallback_levels.py` FOUND (`def test_` 9건) · `tests/serving/test_db.py` FOUND (`def test_` 8건)
- 커밋: 0건(의도적 — `no_commit: true`). `git status --short` 상 위 5개 파일은 작업 트리에 남아 있다.
- `.planning/STATE.md` · `.planning/ROADMAP.md` 미수정(orchestrator 소유)
