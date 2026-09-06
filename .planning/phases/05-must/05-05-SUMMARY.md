---
phase: 05-must
plan: 05
subsystem: serving
tags: [serving, privacy, 열람권, 삭제권, 동의철회, tdd, SERV-07]
requires:
  - contracts.UserState
  - contracts.Catalog
  - millie_rec.serving.db.Database (connect)
  - millie_rec.serving.schemas (UserStateOut · UserDataOut · PersonalizationDeleted)
provides:
  - "millie_rec.serving.privacy_api.build_router (APIRouter — GET state · GET data · DELETE personalization)"
  - "millie_rec.serving.privacy_api.USER_KEY_RE (경로 파라미터 형식 게이트)"
  - "millie_rec.serving.privacy_api.DELETE_TABLES · DELETED_KEYS (삭제 대상 4테이블 ↔ 응답 키)"
  - "millie_rec.serving.privacy_api.HISTORY_EVENT_TYPES (D-05 읽기 이벤트 3종, state.py 와 중복 정의)"
affects: [src/millie_rec/serving/api.py (05-06 include_router), src/millie_rec/app/server.py (05-06 배선)]
tech-stack:
  added: []
  patterns:
    - "APIRouter 팩토리 — 의존을 클로저로 주입(create_app 관례 유지)"
    - "커서 단위 sqlite3.Row — 공유 thread-local 연결의 row_factory 를 바꾸지 않는다"
    - "duck-typed state·invalidate 콜백(형제 플랜 import 없음)"
key-files:
  created:
    - src/millie_rec/serving/privacy_api.py
    - tests/serving/test_privacy_api.py
  modified: []
decisions: [D-05, D-08, D-17, "05-CONTEXT Claude's Discretion — UserStateOut.library 3분류"]
metrics:
  duration: "약 30분"
  completed: 2026-09-06
  tasks: 3
  files: 2
commits: 0   # no_commit
---

# Phase 5 Plan 05: 열람·삭제·철회 API (privacy_api) Summary

**한 줄:** `GET /api/users/{user_key}/state`(library 3분류·스냅샷 active·주입된 weights) · `GET …/data`(4테이블 전 행 + JSON 컬럼 디코드) · `DELETE …/personalization`(4테이블 삭제 + `users.consent=0` + `state.forget`·`invalidate` 콜백, 멱등)을 `USER_KEY_RE` 형식 게이트와 전량 `?` 바인딩 위에서 TDD 한 사이클로 만들었다. `tests/serving/test_privacy_api.py` 12건 + 아키텍처 3건 = **15 passed**, 파일 150줄, 커밋 0.

커밋하지 않는다 — 작업 트리에 남기고 이 SUMMARY 에 변경 파일 목록을 적는다(`no_commit: true`, 사용자 지시 2026-09-05).

## 변경 파일

| 파일 | 상태 | 줄 수 |
|---|---|---|
| `src/millie_rec/serving/privacy_api.py` | 신규 | 150 (한도 150 준수) |
| `tests/serving/test_privacy_api.py` | 신규 | 388 (테스트 12건) |

`must_not_touch` 는 하나도 건드리지 않았다 — `contracts.py` · `serving/schemas.py` · `serving/db.py` · `serving/api.py` · `serving/__init__.py` · `tests/test_architecture.py` 무변경.

## 라우트 3개

| 메서드 · 경로 | 응답 모델 | 동작 | 정본 |
|---|---|---|---|
| `GET /api/users/{user_key}/state` | `UserStateOut` | `consent`·`cell`·`is_new` + `library` 3분류(added/reading/completed, 메타 조인) + `snapshots`(created_at 내림차순, 첫 항목만 `active`) + `user_state_weights`(주입된 `weights`) + `nearline_lag_s=None` | 백엔드 서빙 01 §8 |
| `GET /api/users/{user_key}/data` | `UserDataOut` | `users` 행 + `preference_snapshots`·`events`·`ratings`·`recommendations` 전 행(JSON 컬럼은 `json.loads` 로 풀어서) + `exported_at` + 고정 `note` | 백엔드 서빙 01 §9 (열람권) |
| `DELETE /api/users/{user_key}/personalization` | `PersonalizationDeleted` | 4테이블 DELETE(한 트랜잭션) + `users.consent=0`(행 유지) + `state.forget(user_key)` + `invalidate(user_key)`, 멱등 | 백엔드 서빙 01 §10 (삭제·철회권), 05-CONTEXT D-08 |

세 라우트 공통: 형식 위반 `422`, 미존재 `404 {"detail": "user_key not found"}`, 핸들러는 전부 동기 `def`.

## 인계 시그니처 (plan 05-06 이 verbatim 소비)

```python
USER_KEY_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
DELETE_TABLES = ("preference_snapshots", "events", "ratings", "recommendations")
DELETED_KEYS = ("snapshots", "events", "ratings", "recommendations")   # 응답 deleted 의 키
HISTORY_EVENT_TYPES = ("reader_open", "qualified_read", "completion")

def build_router(*, db: Database, catalog: Catalog | None = None, state: object | None = None,
                 weights: Callable[[UserState], dict[str, float]] | None = None,
                 invalidate: Callable[[str], object] | None = None,
                 now: Callable[[], datetime] | None = None) -> APIRouter
```

**콜백 계약 (05-06 배선용)**

| 주입 | 타입 | 호출 시점 | 없을 때 |
|---|---|---|---|
| `catalog` | `contracts.Catalog`(`meta` 만 사용) | `GET …/state` 의 library 메타 조인 | `title`·`image_url` 이 `null`, 200 유지 |
| `weights` | `Callable[[UserState], dict[str, float]]` (= `ranking.state_weights`) | `GET …/state` | `user_state_weights = {"alpha": 0.0, "beta": 0.0, "gamma": 0.0}` |
| `state` | duck-typed. `user_state(user_key, *, seeds, categories) -> UserState` 와 `forget(user_key)` 를 가진 객체 | `user_state` 는 `GET …/state`(SQL 보다 **우선**), `forget` 은 DELETE 직후 | `state=None` 이면 SQL 로 `UserState(None, 최신 스냅샷 seeds, 읽기 history 최근순)` 조립, DELETE 시 `forget` 생략 |
| `invalidate` | `Callable[[str], object]` (level 1 캐시 무효화) | DELETE 직후, `forget` 다음 | 생략(200 유지) |
| `now` | `Callable[[], datetime]` | `GET …/data` 의 `exported_at` | `datetime.now(UTC)` |

라우터 prefix 는 `/api/users` — `create_app` 은 `app.include_router(build_router(...))` 만 하면 된다(경로 중복 금지).

- **DELETE 이후 `/api/recommend` 가 항상 level 3** 이라는 끝단 단정은 이 플랜이 아니라 **plan 05-06 의 `tests/serving/test_cascade.py`** 가 한다. 이 플랜은 `users.consent=0` · 4테이블 행 0 · 콜백 2개 호출까지를 단정한다.
- **Codex 필수 리뷰 대상(plan 05-09):** `privacy_api.py` — `/codex:review --scope working-tree` + `/codex:adversarial-review`(`../.claude/rules/codex-review.md` "언제" 표, 동의 철회·개인정보 표면).

## TDD 증거

**RED — `uv run pytest tests/serving/test_privacy_api.py --no-header` (스텁 라우터, 12건 전부 실패)**

```
E       AssertionError: assert 'A' == 'B'
E       AssertionError: assert {} == {'alpha': 0.0... 'gamma': 0.0}
E       AssertionError: assert {'preference_...endations': 2} == {'preference_...endations': 0}
E           assert 200 == 404
E           assert 200 == 422
E       assert 0 >= 8
E        +  where 0 = <built-in method count of str object at 0x137b49400>('WHERE user_key = ?')
E       assert 'u-1' in '{"user":{},"snapshots":[],"events":[],"ratings":[],"recommendations":[],"exported_at":"","note":"가명 user_key 외 개인정보 없음"}'
12 failed, 2 warnings in 0.33s
```

실패 사유는 **전부 `AssertionError`** 다 — `ImportError`·`SyntaxError`·`TypeError`·`AttributeError`·`sqlite3.OperationalError`·`IntegrityError` 0건(`grep -cE` 로 확인). 같은 시점 `uv run pytest tests/test_architecture.py --no-header` → `3 passed`.

**GREEN — `uv run pytest tests/serving/test_privacy_api.py tests/test_architecture.py --no-header`**

```
15 passed, 2 warnings in 0.28s
```

**REFACTOR** — `uv run ruff format --check` → `2 files already formatted`, `uv run ruff check` → `All checks passed!`. 정리 범위는 이 브리프의 2개 파일뿐(최소 변경). 인터프리터는 `uv run python --version` → `Python 3.11.6` 로 먼저 확인했다(`../.claude/rules/python-tdd.md` 인터프리터 함정).

### 테스트 12건 (3종 구분)

| 구분 | 테스트 |
|---|---|
| 계약 | `…library_three_buckets_with_meta` · `…snapshots_desc_with_active_latest_and_weights_from_latest_seeds_history` · `…without_weights_or_catalog_degrades_gracefully` · `…data_export_returns_all_tables_with_json_columns_decoded_and_note` |
| 정확성 | `…delete_removes_four_tables_keeps_user_consent_false_calls_forget_invalidate` · `…delete_is_idempotent_and_state_after_delete_is_empty` · `…delete_does_not_touch_other_users` · `…delete_without_state_or_cache_callbacks_still_200` |
| 안전성 | `…unknown_user_key_is_404_on_all_three_routes` · `…user_key_format_422_and_uuid4_passes_format` · `…sql_is_parameter_bound_source_grep` · `…responses_leak_no_traceback_or_pii` |

이벤트 `ts` 를 `FIXED_NOW − N분` 으로 못박아 `reading == [8, 2]`·`history == (8, 3, 2)` 가 결정적이다. SQLite 는 `tmp_path`, 시간은 `now` 주입, 네트워크 0.

## 보안 자기 점검표 (Codex 리뷰 선행)

| 항목 | 상태 | 근거 |
|---|---|---|
| 경로 파라미터 형식 검증 | ✓ | `USER_KEY_RE = ^[A-Za-z0-9_-]{1,64}$` 미일치는 `422` — 공백·`a';b`·65자 테스트 (T-05-05-01) |
| 미존재 user_key | ✓ | 세 라우트 모두 `404 {"detail": "user_key not found"}` |
| DELETE 멱등 | ✓ | 두 번째 호출도 `200`, `deleted` 전부 0, `consent` 계속 false |
| 응답에 가명 user_key 외 개인정보 없음 | ✓ | `users` 5컬럼 + `schema.sql` 정의 컬럼만(이메일·IP·이름 컬럼 자체가 없다), `note` 고정 문장, `"@"` 부재 테스트 (T-05-05-02) |
| f-string 값 보간 SQL | ✓ 0건 | `grep -c "execute(f"` → 0. `SQL_DELETE` 의 f-string 은 **상수 튜플 `DELETE_TABLES` 의 테이블 이름만**(사용자 입력 아님, `db.row_counts` 관례) |
| `?` 바인딩 | ✓ 8곳 | `grep -o "WHERE user_key = ?" \| wc -l` → 8 (SELECT 6 · DELETE 1(4테이블 공용) · UPDATE 1) |
| 예외 문자열 미노출 | ✓ | `weights` 예외는 `log.exception` 후 0 셋 반환(500 없음), 손상 JSON 은 원문 유지 — 응답에 `Traceback` 부재 테스트 (T-05-05-06) |

## 계획과의 차이 (전부 동작 동일, 150줄 한도 안에서의 구현 선택)

1. **`con.row_factory` → 커서 단위 `cur.row_factory`** (Rule 2 안전). 계획은 연결에 `sqlite3.Row` 를 설정하라고 했으나, `Database.connect()` 는 **thread-local 공유 연결**이라 같은 웨이브의 05-01·05-03 코드(`db.row_counts()` 등)의 행 형태를 바꿀 수 있다. 커서 단위로 설정해 부작용을 없앴다.
2. **`SQL_LIB` 에서 `GROUP BY book_id, event_type` 제거** — `SELECT book_id, event_type, ts … ORDER BY ts DESC` 로 두고 `_ids()` 의 `dict.fromkeys`(첫 등장 = 최신)가 같은 결과를 만든다. 결과 동일, 상수 4줄 → 1줄.
3. **`DELETED_KEYS` 를 dict 가 아니라 `DELETE_TABLES` 와 평행한 튜플**로 두고 `zip(..., strict=True)` 로 합친다(응답 키 `snapshots events ratings recommendations` 는 §10 그대로).
4. **`_snap()` 은 `active` 를 받지 않고** 호출부가 `_snap(s) | {"active": i == 0}` 으로 합친다. `LibraryBook`·`SnapshotSummary` 는 dict 로 넘겨 pydantic 이 검증한다(`schemas.py` 무변경, import 2개 감소).
5. **`_Spy` 하나가 `forget`·`invalidate`·`user_state` 를 모두 갖는다** — 계획의 "둘 다 가진 하나의 가짜로 충분" 그대로. 단정은 `spy.calls == [("forget", "u-1"), ("invalidate", "u-1")]`.
6. **`build_router` 시그니처는 `# fmt: skip` 로 4줄** 유지(파일 150줄 한도). 파라미터 이름·순서·기본값은 계획의 인계 계약과 **완전히 동일**하다.

계획 대비 누락은 없다. 형제 플랜 파일 import 0(`state.py`·`fallback.py`·`compose.py`·`demo_api.py` 어느 것도 참조하지 않음, `HISTORY_EVENT_TYPES` 는 중복 정의).

## Advisor 보고

- **`serving/__init__.py` 의 `__all__` 미갱신** — `must_not_touch` 라 건드리지 않았다. 새 공개 이름(`build_router` 또는 라우터 팩토리)을 공개 표면에 올릴지는 plan 05-06 배선 시 Advisor 판단. `app/` 은 공개 표면만 import 하므로(`tests/test_architecture.py`) **`create_app` 안에서 `from millie_rec.serving.privacy_api import build_router` 로 배선하면 `__init__` 변경 없이 규칙을 만족**한다.
- **`db.py` 쓰기 헬퍼 미의존** — 05-03 이 같은 시각에 만드는 중이라 `db.connect()` + `with con:` 만 썼다. 05-03 헬퍼가 확정되면 교체는 선택 사항(동작 동일).
- **인덱스** — `events(user_key, ts)` 인덱스(05-03 의 `schema.sql` 증분)가 들어오면 `SQL_LIB`·`SQL_EVENTS` 가 그대로 이득을 본다. 이 플랜은 DDL 을 건드리지 않았다.
- **전역 스위트·`make smoke` 미실행** — 병렬 웨이브 지시대로 자기 대상만 돌렸다. Advisor 가 웨이브 종료 후 1회 실행.

## TDD Gate Compliance

RED(`AssertionError` 12건) → GREEN(`15 passed`) → REFACTOR(ruff 클린 · 150줄) 순서를 지켰다. **`no_commit: true` 라 `test(...)`·`feat(...)` 게이트 커밋은 만들지 않았다** — 게이트 증거는 위 "TDD 증거" 절의 pytest 출력이다(`tdd_gate_evidence: pytest-output`).

## Self-Check

- `src/millie_rec/serving/privacy_api.py` — FOUND (150줄)
- `tests/serving/test_privacy_api.py` — FOUND (388줄, `def test_` 12건)
- `uv run pytest tests/serving/test_privacy_api.py tests/test_architecture.py --no-header` → `15 passed`
- `uv run ruff format --check` · `uv run ruff check`(자기 경로) → 클린
- 커밋 0 · `.planning/STATE.md`·`.planning/ROADMAP.md` 무변경

## Self-Check: PASSED

## Codex 수정 반영 (2026-09-06, 브리프 A)

Codex 리뷰 지적 F2(적대 high) · T3 · T4 를 `privacy_api.py` 한 파일 안에서 처리했다. **`privacy_sql.py` 는 만들지 않았다** — 아래 3번 구조 정리로 150줄 한도를 지켰고, 기존 테스트 `test_sql_is_parameter_bound_source_grep` 이 `privacy_api.py` 본문에서 `WHERE user_key = ?` 를 8회 이상 세므로 SQL 상수를 다른 파일로 옮기면 그 테스트가 깨진다(옮기려면 테스트 본문을 고쳐야 해서 옮기지 않는 쪽을 택했다).

### 무엇을 고쳤나

1. **F2 — `DELETE /api/users/{user_key}/personalization` 이 `candidate_sets` 를 남기던 문제.** `DELETE_TABLES` 에 `"candidate_sets"` 를 추가해 기존 4테이블과 **같은 `with con:` 트랜잭션**에서 지우고, `DELETED_KEYS` 에도 같은 이름을 넣어 응답 `deleted` dict 에 집계된다. `deleted` 는 `dict[str, int]` 라 `schemas.py` 변경 없음. 온보딩이 `book_ids` 를 담아 넣는 행이라 개인정보 삭제 누락이었다.
2. **T3 — 열람권 응답에 `candidate_sets` 누락.** `SQL_EXPORT` 에 `SELECT * FROM candidate_sets WHERE user_key = ? ORDER BY ts` 를 넣고 `UserDataOut.candidate_sets`(Advisor 가 미리 추가한 optional 필드)로 내보낸다. `JSON_COLS` 에 `book_ids` 를 더해 다른 테이블의 JSON 컬럼과 똑같이 풀린 값으로 나간다.
   - **스키마 실측 반영**: 브리프는 `ORDER BY created_at` 이었으나 `schema.sql` 의 `candidate_sets` 컬럼은 `candidate_set_id · user_key · ts · book_ids · survey_variant` 로 `created_at` 이 없다. `ORDER BY ts` 로 두었다(다른 이벤트성 테이블과 동일).
3. **T4 — 열람 응답이 일관 스냅샷이 되도록 한 트랜잭션.** `con.execute("BEGIN")` 후 `with con:` 안에서 `_user_or_404` 검증 + 5테이블 SELECT 를 모두 수행한다. `with con:` 이 정상 종료 시 COMMIT, 404·예외 시 ROLLBACK 하므로 어느 경로에서도 트랜잭션이 열린 채 남지 않는다(try/finally 를 별도로 쓰지 않고 같은 보장을 얻는 쪽 — 150줄 한도). deferred BEGIN 이라 첫 SELECT 시점의 스냅샷을 끝까지 읽는다.
   - 이 과정에서 `SQL_SNAPS`·`SQL_EVENTS`·`SQL_RATINGS`·`SQL_RECS` 4개 상수를 `SQL_EXPORT` dict(키 = `UserDataOut` 필드명) 하나로 합치고 핸들러를 dict comprehension 으로 줄였다. `GET /state` 는 `SQL_EXPORT["snapshots"]` 를 쓴다. 동작 동일, 파라미터 바인딩·f-string 금지 규칙 그대로(`ruff` 클린, grep 테스트 통과 — 이제 `WHERE user_key = ?` 9회).

### 기존 테스트 중 고친 것 (불가피)

`deleted` 응답 키가 4개 → 5개가 되므로 정확 일치 단정 3곳이 그대로면 깨진다. 단정 **문장**은 유지하고 기대값만 상수로 뺐다: `SEEDED_DELETED = dict(zip(DELETED_5, (2, 7, 1, 2, 0), strict=True))` · `EMPTY_DELETED = dict.fromkeys(DELETED_5, 0)`. (`_seed_user` 는 `candidate_sets` 를 넣지 않으므로 기존 테스트의 기대값은 `candidate_sets: 0`.) 다른 단정은 손대지 않았다.

### 추가한 테스트 4개

| 테스트 | 무엇을 못박나 |
|---|---|
| `test_delete_removes_candidate_sets_and_counts_them_without_touching_others` | F2 — `deleted["candidate_sets"] == 1`, `u-1` 행 0개, `u-2` 행은 그대로 |
| `test_data_export_includes_candidate_sets_with_book_ids_decoded` | T3 — 키 존재 + `book_ids` 가 리스트로 풀림 + 다른 사용자 행 미포함 |
| `test_data_export_runs_in_one_read_transaction_and_leaves_none_open` | T4 — `set_trace_callback` 기록이 `BEGIN → SELECT×6 → COMMIT`, `con.in_transaction is False` |
| `test_data_export_404_does_not_leave_a_transaction_open` | T4 안전성 — 404 경로에서도 열린 트랜잭션 0 |

`_DbTrace` 는 `Database` 를 감싸 핸들러가 실제로 쓴 연결(스레드풀 연결)과 실행 SQL 을 기록하는 가짜다. 테스트 스레드의 연결과 다르기 때문에 이 래퍼 없이는 트랜잭션 종료를 단정할 수 없다.

### RED / GREEN

```
# RED — 구현 전
uv run pytest tests/serving/test_privacy_api.py --no-header
6 failed, 10 passed, 2 warnings in 0.36s
E       AssertionError: assert {'snapshots':...endations': 2} == {'snapshots':...ions': 2, ...}
E       AssertionError: assert {'snapshots':...endations': 0} == {'snapshots':...ions': 0, ...}
E       AssertionError: assert {'snapshots':...endations': 2} == {'snapshots':...ions': 2, ...}
E       AssertionError: assert None == 1            # deleted["candidate_sets"] 없음 (F2)
E       AssertionError: assert 0 == 1               # 열람 응답에 candidate_sets 없음 (T3)
E       AssertionError: assert ['SELECT', ...] == ['BEGIN', ...]   # 트랜잭션 없음 (T4)

# GREEN — 구현 후
uv run pytest tests/serving/test_privacy_api.py --no-header
16 passed, 2 warnings in 0.29s

uv run pytest tests/serving/test_privacy_api.py tests/serving/test_schemas.py tests/test_architecture.py --no-header
21 passed, 2 warnings in 0.26s

uv run ruff format ... && uv run ruff check ...
2 files left unchanged
All checks passed!
```

### 파일

- `src/millie_rec/serving/privacy_api.py` — 150줄(한도 그대로, 신설 파일 없음)
- `tests/serving/test_privacy_api.py` — 483줄, `def test_` 16건

전역 스위트·`make smoke` 는 병렬 웨이브 지시대로 돌리지 않았다(Advisor 게이트).
