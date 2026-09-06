---
phase: 05-must
plan: 01
subsystem: Serving (state·nearline·book_stats)
tags: [SERV-09, SERV-04, state, nearline, book_stats, tdd]
requires: [contracts.UserState, contracts.Catalog, contracts.Neighbors, serving.db.Database]
provides: [StateStore, NearlineLoop, ServingBookStats, reset_boost, parse_ts, SESSION_WINDOW_S]
affects: [05-06 api.py 통합, 05-08 app/ 주입, wave 4 after_completion]
tech-stack:
  added: []
  patterns: [메모리 dict aggregate, rowid 커서, asyncio.Event 웨이크, asyncio.to_thread, 시간 주입]
key-files:
  created:
    - src/millie_rec/serving/state.py
    - src/millie_rec/serving/nearline.py
    - src/millie_rec/serving/book_stats.py
    - tests/serving/test_state.py
    - tests/serving/test_nearline.py
    - tests/serving/test_book_stats.py
  modified:
    - src/millie_rec/serving/__init__.py
decisions: [D-05, D-06, D-07, D-08 (.planning/phases/05-must/05-CONTEXT.md)]
metrics:
  tasks: 3
  files: 7
  tests_added: 23
  completed: 2026-09-06
commits: 0   # no_commit
---

# Phase 5 Plan 01: user_key 상태 모델 Summary

`StateStore`(메모리 dict aggregate) · `NearlineLoop`(rowid 커서 · 24h 리플레이 · 웨이크 루프) · `ServingBookStats`(완독 평균 / 카테고리 prior `user_level`) 세 클래스를 TDD 한 사이클로 만들어, 상태 쓰기 경로가 Nearline 하나뿐이라는 SERV-09 경계를 코드와 테스트로 고정했다.

## 커밋

**커밋하지 않는다 — 작업 트리에 남기고 이 SUMMARY 에 변경 파일 목록을 적는다**(사용자 지시 2026-09-05, 플랜 frontmatter `no_commit: true`). `commits: 0`.

## 변경 파일 (`git status --short`)

```
 M src/millie_rec/serving/__init__.py
?? src/millie_rec/serving/book_stats.py
?? src/millie_rec/serving/nearline.py
?? src/millie_rec/serving/state.py
?? tests/serving/test_book_stats.py
?? tests/serving/test_nearline.py
?? tests/serving/test_state.py
```

`must_not_touch` 파일 중 `src/millie_rec/contracts.py` · `Makefile` · `pyproject.toml` 이 `M` 으로 보이지만 **이 플랜이 만든 변경이 아니다**(앞 페이즈·Advisor 레인의 미커밋 변경). `git diff src/millie_rec/contracts.py` 에 이 플랜의 이름(`StateStore` `NearlineLoop` `ServingBookStats` `SESSION_WINDOW_S`)은 0건.

## TDD 증거

### RED (Task 1 — 시그니처만 있는 스텁 + 신규 테스트 23건)

명령: `uv run pytest tests/serving/test_state.py tests/serving/test_nearline.py tests/serving/test_book_stats.py --no-header`

요약 줄:

```
21 failed, 2 passed in 0.23s
```

`ImportError` · `ModuleNotFoundError` · `AttributeError` · `TypeError` · `SyntaxError` 0건(grep 확인), `AssertionError`/`E  assert` 42줄. 발췌:

```
_______________ test_parse_ts_accepts_z_offset_and_naive_as_utc ________________
>       assert parse_ts("2026-09-07T12:00:27Z") == expected
E       AssertionError: assert 0.0 == 1788782427.0
E        +  where 0.0 = parse_ts('2026-09-07T12:00:27Z')

____ test_handler_side_insert_does_not_change_state_until_run_once ____
>       assert nearline.run_once() == 2
E       assert -1 == 2

_______ test_waker_is_thread_safe _______
E       assert False is True

__ test_user_level_is_mean_difficulty_of_completed_books_excluding_missing __
>       assert adapter.user_level(store.user_state("u")) == pytest.approx(0.4)
E       assert None == 0.4 ± 4.0e-07
```

같은 시각 `uv run pytest tests/test_architecture.py --no-header` → `3 passed`.

### GREEN (Task 2)

```
..........................                                               [100%]
26 passed in 0.21s
```

(신규 23 + `tests/test_architecture.py` 3)

### REFACTOR (Task 3)

- `uv run ruff format --check <자기 경로 7개>` → `7 files already formatted`
- `uv run ruff check <자기 경로 7개>` → `All checks passed!`
- `wc -l` → `state.py 148` · `nearline.py 119` · `book_stats.py 47` (전부 ≤150)
- `uv run python -c "import sys; from millie_rec.serving import StateStore, NearlineLoop, ServingBookStats; print('pandas' in sys.modules)"` → `False`(공개 표면 import 가 pandas·scipy 를 끌지 않는다)
- 재실행 `26 passed`

## TDD Gate Compliance

커밋 게이트(`test(...)` → `feat(...)`)를 **생략**했다. 사유: 이 프로젝트의 커밋 정책상 Phase 1~5 산출물은 사용자 승인 후 일괄 커밋한다(사용자 지시 2026-09-05, 플랜 `no_commit: true`). 대체 증거 = 위 pytest 요약 줄 2개(RED `21 failed, 2 passed` / GREEN `26 passed`)와 RED 발췌.

## 구현 요지

**`src/millie_rec/serving/state.py`** (148줄) — 상수 `SESSION_WINDOW_S=1800`(D-06) · `REPLAY_WINDOW_S=86400` · `RESET_BOOST_WINDOW_S=86400`(D-08) · `HISTORY_MAX=200` · `HISTORY_EVENT_TYPES=("reader_open","qualified_read","completion")`(D-05) · `SESSION_EVENT_TYPES=("reader_open","detail_click")`(D-06). `_Record`(history·session·completed·reading·last_event_ts)를 `user_key` 별로 들고, `apply_event` 만 쓰기다. `_push_front` 로 최근순 distinct + 상한, `_session_ids` 는 `now − 1800 ≤ t ≤ now + 1800` 창(미래 ts 가 세션을 영구 활성화하지 못하게 상한도 건다 — 위협 T-05-01-01). 모든 접근은 `threading.Lock`.

**`src/millie_rec/serving/nearline.py`** (119줄) — `SQL_NEW`(`WHERE rowid > ?`) · `SQL_REPLAY`(`WHERE ts >= ? AND rowid > ?`) · `SQL_MAX_ROWID` · `SQL_MARK_SELECTED` 전부 `?` 바인딩(`execute(f` 0건). `_apply_rows(con, rows)` 는 행 단위 `try/except` + `log.exception` 후 커서 전진(한 행의 실패가 루프를 멈추지 않는다 — T-05-01-03). `run_once` 는 `BATCH_ROWS=1000` 씩 커서 뒤 전부, `replay` 는 24h 창만 적용하고 커서를 `MAX(rowid)` 로 올린다. `_tick` = `wait_for(wake.wait(), interval_s)` → `clear()` → `asyncio.to_thread(run_once)` → `last_run` ISO. `waker(loop)` 는 `loop.call_soon_threadsafe(self.wake.set)`(동기 핸들러가 `Event.set()` 을 직접 부르지 않는다). `neighbors` 는 보관만 — wave 4 `after_completion` 이 쓴다.

**`src/millie_rec/serving/book_stats.py`** (47줄) — `PRIOR_POPULAR_N=200`. `stats` 는 카탈로그 1:1 위임, `user_level` 은 완독 책 `difficulty` 평균(결측 제외) → 없으면 `context["categories"]` 의 `popular(cats, n=200)` 평균, 그것도 없으면 `None`. prior 는 `tuple(categories)` 키 dict 캐시(두 번째 호출에서 `popular` 재조회 없음).

**`src/millie_rec/serving/__init__.py`** — `NearlineLoop` · `ServingBookStats` · `StateStore` 3이름 추가(기존 7이름 유지, `__all__` 문자 코드 순).

## 05-06 · 05-08 인계용 공개 시그니처 (실제 코드 복사)

```python
# millie_rec/serving/state.py
SESSION_WINDOW_S = 1800
REPLAY_WINDOW_S = 86400
RESET_BOOST_WINDOW_S = 86400
HISTORY_MAX = 200
HISTORY_EVENT_TYPES = ("reader_open", "qualified_read", "completion")
SESSION_EVENT_TYPES = ("reader_open", "detail_click")
COMPLETION = "completion"

def parse_ts(ts: str) -> float
def reset_boost(snapshots_count: int, latest_created_at: str | None, *, now: float) -> bool

class StateStore:
    def __init__(self, *, now: Callable[[], float] | None = None) -> None
    def apply_event(self, user_key: str, event_type: str, book_id: int | None, ts: str) -> None
    def user_state(
        self,
        user_key: str,
        *,
        seeds: Sequence[int] = (),
        categories: Sequence[str] = (),
        context: str | None = None,
    ) -> UserState
    def session_active(self, user_key: str) -> bool
    def n_completed(self, user_key: str) -> int
    def completed_books(self, user_key: str) -> tuple[int, ...]
    def continue_reading(self, user_key: str) -> tuple[int, ...]
    def last_event_ts(self, user_key: str) -> float | None
    def forget(self, user_key: str) -> None
    def __len__(self) -> int

# millie_rec/serving/nearline.py
BATCH_ROWS = 1000
SELECTED_EVENT = "preference_book_selected"

class NearlineLoop:
    def __init__(
        self,
        db: Database,
        store: StateStore,
        *,
        neighbors: Neighbors | None = None,
        interval_s: float = NEARLINE_INTERVAL_S,
        now: Callable[[], float] | None = None,
    ) -> None
    wake: asyncio.Event
    last_run: str | None      # ISO seconds 'Z' — /health.nearline_last_run
    last_rowid: int
    def run_once(self) -> int
    def replay(self) -> int
    async def run(self) -> None          # while True: await self._tick()
    def waker(self, loop: asyncio.AbstractEventLoop) -> Callable[[], None]

# millie_rec/serving/book_stats.py
PRIOR_POPULAR_N = 200

class ServingBookStats:
    def __init__(self, catalog: Catalog, store: StateStore) -> None
    def stats(self, book_ids: Sequence[int]) -> list[BookStats]
    def user_level(self, user: UserState) -> float | None
```

`UserState.context` 키 = `user_key` · `n_completed`(str) · `categories`(쉼표 결합) · `reading_time`(인자 `context` 가 있을 때만). 값은 전부 `str`.

## Deviations from Plan

### 1. [Rule 3 - 블로킹] `db.py` 의 `row_factory = sqlite3.Row` 를 테스트가 흡수

- **발견 시점:** Task 2 GREEN 첫 실행
- **문제:** 형제 플랜 05-03 이 같은 시각에 `serving/db.py` `connect()` 에 `con.row_factory = sqlite3.Row` 를 추가했다. `test_preference_book_selected_fills_impression_selected` 의 `fetchall() == [(7, 1), (8, None)]` 비교가 `sqlite3.Row` 객체와 튜플을 비교해 실패했다.
- **조치:** 단정을 약화하지 않고 `[tuple(r) for r in rows] == [(7, 1), (8, None)]` 로 정규화(row_factory 유무와 무관하게 같은 값을 검사). `db.py` 는 건드리지 않았다. 구현 쪽 `_apply_rows` 는 `sqlite3.Row` 언패킹이 그대로 동작한다.
- **파일:** `tests/serving/test_nearline.py`

### 2. [Rule 3 - 블로킹] 모듈 docstring 길이 (ruff E501)

- **문제:** ruff 는 한글(동아시아 전각)을 폭 2로 세어 플랜에 적힌 1줄 docstring 3개가 100자를 넘겼다.
- **조치:** 뜻을 유지한 채 짧게 줄였다(정본 참조 표기는 유지). 로직·상수·시그니처 무변경.
- **파일:** `state.py` · `nearline.py` · `book_stats.py` · 테스트 3파일의 머리 docstring

### 3. [플랜 재량] `state.py` 150줄 맞추기 위한 `_snapshot` 헬퍼

- **문제:** 플랜의 pseudocode 그대로 쓰면 158줄(한도 초과).
- **조치:** 락 안에서 레코드를 얻는 비공개 `_snapshot(user_key) -> _Record` 하나를 두고 읽기 메서드 5개를 1줄로 줄였다(148줄). 공개 시그니처·반환값 무변경.

### 4. [플랜 재량] `nearline.py` SQL 중복 상수화

- `SELECT rowid, user_key, book_id, event_type, ts, candidate_set_id FROM events ` 를 `COLUMNS` 상수로 뽑아 `SQL_NEW` · `SQL_REPLAY` 가 공유한다(Task 3 정리 범위 "중복 SQL 문자열 상수화"). `WHERE rowid > ?` 문자열은 `SQL_NEW` 에 그대로 남아 acceptance grep 을 만족한다.

## 인증 게이트

없음.

## Known Stubs

없음. 세 파일 모두 실제 로직으로 구현했고, `NearlineLoop.neighbors` 만 미사용 보관 인자다(wave 4 `after_completion` 이 소비 — 결정 D-13(.planning/phases/05-must/05-CONTEXT.md)에 명시된 의도적 미구현).

## Advisor 보고 (범위 밖 필요 변경 · 미결)

1. **`app/server.py` 배선이 남아 있다.** `create_app(..., state=<StateStore>)` 주입, lifespan 의 `replay()` → `asyncio.create_task(nearline.run())` → shutdown 취소, `ServingBookStats(catalog, store)` 를 `book_stats=` 로 주입, `POST /api/events` 핸들러가 `nearline.waker(loop)()` 를 부르는 것 — 전부 Plan 05-06 · 05-08(Advisor) 몫이다. 이 플랜은 명시 인자를 받는 클래스만 만들었다.
2. **`n_completed` 대리값 교체(D-07 Claude's Discretion (c) 안)는 하지 않았다.** `UserState.context["n_completed"]` 를 서버가 채우는 데까지가 이 플랜 범위이고, `reranking/guard.py` · `ranking/hybrid.py` 가 그 키를 읽는 1줄 분기는 Model 레인 파일이라 Advisor 승인 + 개발일지 항목이 필요하다. 미적용 상태에서는 guard·hybrid 가 여전히 `len(user.history)` 를 본다.
3. **`db.py` 의 `row_factory = sqlite3.Row`(05-03)** 가 기존 `fetchall()` 튜플 비교에 의존하는 다른 테스트를 깨뜨릴 수 있다. wave 1 종료 후 Advisor 전체 스위트에서 확인 필요.
4. **`events(user_key, ts)` 인덱스 없음.** `SQL_REPLAY` 는 `ts >= ?` 문자열 비교라 데모 규모에서는 full scan 으로 충분하지만, `schema.sql` 에 `CREATE INDEX IF NOT EXISTS` 를 넣을지는 `schema.sql` 소유자(05-03)·Advisor 판단이다.
5. **`git status` 에 보이는 `Makefile` · `pyproject.toml` · `contracts.py` · `.planning/STATE.md` · `.planning/ROADMAP.md` 의 `M`** 은 이 플랜과 무관하다(앞 페이즈·Advisor·오케스트레이터 레인). 이 Worker 는 그중 어느 파일도 열거나 쓰지 않았다. 일괄 커밋 시 분리 확인 필요.
6. **커밋 0 확인:** `git log --oneline -1` → `8e5172b chore: project scaffold — contracts freeze, serving schemas, demo mock, GSD planning docs`(플랜 시작 시점과 동일).

## Self-Check: PASSED

- `src/millie_rec/serving/state.py` · `nearline.py` · `book_stats.py` · `tests/serving/test_state.py` · `test_nearline.py` · `test_book_stats.py` 6파일 존재, `src/millie_rec/serving/__init__.py` 3이름 추가 확인
- 커밋 해시 없음 — `no_commit: true` 이므로 커밋 검증 대상 없음(`commits: 0`)
- `uv run pytest tests/serving/test_state.py tests/serving/test_nearline.py tests/serving/test_book_stats.py tests/test_architecture.py --no-header` → `26 passed`
- `grep -rn "apply_event(" src/millie_rec/serving/` → 정의 1곳(`state.py:78`) + 호출 1곳(`nearline.py:63`) = SERV-09 경계 코드 증거
- `grep -rn "millie_rec.(data|app|retrieval|ranking|reranking|evaluation)" <신규 3파일>` → 0건 (star 의존 유지)

## Codex 수정 반영 (2026-09-06, 브리프 D)

**F5 (Codex P1) — Nearline 이 품질 플래그 행까지 상태에 반영하던 문제.** `SQL_NEW` · `SQL_REPLAY` 가 `events` 전 행을 골라 `_apply_rows` 가 `StateStore.apply_event` 로 넘기고 있었다. `quality_flag` 가 붙은 행(`ts_future` · `ts_backdated` · `book_ineligible`)도 그대로 통과해, 부적격 도서가 history · continue_reading 에 들어가고 미래·과거 타임스탬프가 30분 세션 창을 왜곡할 수 있었다.

- 두 쿼리 공통 조건을 `CLEAN = "WHERE quality_flag IS NULL AND rowid > ? AND rowid <= ?"` 로 묶었다. 플래그 행은 저장·대시보드 집계용으로 남고 온라인 상태만 만들지 않는다(백엔드 01 §6 "플래그가 붙어도 저장한다"는 유지).
- 커서 정체 방지: `run_once` · `replay` 가 스캔 전에 `hi = MAX(rowid)` 로 상한을 고정하고, 스캔이 끝나면 `last_rowid = max(last_rowid, hi)` 로 올린다. 건너뛴 플래그 행에서 커서가 멈추지 않고, 스캔 도중 들어온 새 행(rowid > hi)은 다음 회차가 가져가므로 유실도 없다. `replay` 가 쓰던 사후 `MAX(rowid)` 대입은 이 상한으로 대체했다.
- 테스트 2건 추가(`tests/serving/test_nearline.py`): `test_run_once_skips_quality_flagged_rows_and_advances_cursor`(clean 1 + flagged 1 → 적용 1건 · history 에 clean 만 · `last_rowid == 2` · 재실행 0건), `test_replay_skips_quality_flagged_rows`.
- 파일: `src/millie_rec/serving/nearline.py` 129줄(기존 122). 기존 단정은 고치지 않았다.
