---
phase: 05-must
plan: 11
subsystem: Serving (ratings_api — POST /api/ratings, Should)
tags: [serving, ratings, events, sqlite, fastapi, tdd, should]
requires:
  - src/millie_rec/serving/schemas.py (RatingIn · RatingOut — freeze, 무변경)
  - src/millie_rec/serving/db.py (Database.connect · query)
  - src/millie_rec/serving/schema.sql (ratings · events)
  - src/millie_rec/serving/api.py (create_app — wake_fn · inv 클로저, Plan 05-06)
provides:
  - "serving.ratings_api.build_router(*, db, wake=None, invalidate=None, now=None) → APIRouter(POST /api/ratings 201)"
  - "serving.ratings_api: SURFACE_READER · EVENT_RATING · USER_KEY_RE · SQL_RATING_INS · SQL_EVENT_INS"
  - "api.py: POST /api/ratings 마운트(include_router 1줄)"
affects:
  - Phase 6 '데모 재구성'(.planning/ROADMAP.md) DEMO-07 — 뷰어 시뮬레이션 화면(#/reader/:id, ../.assets/설계서/화면 구성 및 디자인/02_화면구성_v2_8페이지.md §2) 1탭 별점 모달이 부르는 엔드포인트
  - PROGRESS.md 결정 로그 — 아키 §9-3 파일 목록 외 신설 1줄(Advisor 몫)
tech-stack:
  added: []
  patterns:
    - "APIRouter 팩토리(의존을 클로저로) — demo_api.build_router 관례 그대로"
    - "INSERT OR IGNORE + rowcount 로 멱등 판정 → 이벤트·wake·invalidate 를 rowcount 로 게이팅"
    - "demo_api 의 SQL_EVENT_INS·USER_KEY_RE·_parse 는 import 하지 않고 중복 정의(파일 독립, demo_api 무변경)"
key-files:
  created:
    - src/millie_rec/serving/ratings_api.py
    - tests/serving/test_ratings.py
  modified:
    - src/millie_rec/serving/api.py
decisions:
  - "이벤트 INSERT 는 15컬럼 위치 바인딩(?) — demo_api 의 이름 바인딩과 달리 EventIn 모델을 만들지 않고 값 튜플 1개로 끝낸다(파일 80줄)"
  - "payload 는 json.dumps({'stars': str(stars)}) 인라인 — onboarding_api._j 를 import 하지 않아 파일 독립 유지"
  - "invalidate 는 삽입에 성공했을 때만 호출(중복 재전송은 캐시를 건드리지 않는다)"
  - "now 파라미터는 시그니처 호환용으로만 받는다 — ratings 는 서버 시각을 쓰지 않고 body.ts 만 정규화한다"
metrics:
  tasks: 3
  tests_added: 8
  duration: "~35m"
  completed: 2026-09-06
commits: 0   # no_commit — 작업 트리에 남긴다(플랜 frontmatter no_commit: true, 사용자 지시 2026-09-05)
---

# Phase 5 Plan 11: POST /api/ratings 요약

별점 1탭 저장 경로를 신규 파일 `serving/ratings_api.py` 하나로 만들었다. `ratings` INSERT 와 `rating` 이벤트 자동 기록이 같은 트랜잭션에서 일어나고, 삽입에 성공했을 때만 Nearline 웨이크와 캐시 무효화를 부른다. 별점은 모델 라벨로 쓰지 않는다(05-CONTEXT D-13 · 결정 '1탭 별점 UI를 "설계만" → "데모 축소판"'(../.assets/개발일지/ 2026-09-04 파일 항목 D22)) — 소스 grep 테스트가 이를 단정한다.

## 변경 파일 (3개 · 커밋 0)

| 경로 | 줄 수 | 상태 | 내용 |
|---|---|---|---|
| `src/millie_rec/serving/ratings_api.py` | 80 | 신규 | 상수 5개 · `_422` · `_parse` · `_iso` · `build_router` → `POST /api/ratings`(201) |
| `src/millie_rec/serving/api.py` | 150 | 수정 (+2줄) | import 1줄 + `include_router` 1줄 |
| `tests/serving/test_ratings.py` | 149 | 신규 | 8건(계약 1 · 정확성 3 · 안전성 3 · 통합 1) |

**커밋하지 않는다** — 플랜 frontmatter `no_commit: true`. 작업 트리에 그대로 남겼다. (`git status` 상 이 저장소는 아직 대부분 미추적이라 `api.py` 도 untracked 로 보인다 — `git diff` 대신 아래 인용으로 2줄을 확인한다.)

## `api.py` 에 늘어난 2줄 (전부)

```python
# L35 (import 블록, privacy_api 와 schemas 사이 — isort 순서 그대로)
from millie_rec.serving.ratings_api import build_router as ratings_router

# L116 (privacy include 바로 아래)
app.include_router(ratings_router(db=db, wake=wake_fn, invalidate=inv))
```

`invalidate` 인자에는 `create_app` 이 이미 쓰고 있는 지역 변수 `inv`(= `cache.invalidate`)를 그대로 넘겼다. 다른 라인은 손대지 않았고 `demo_api.py`(150줄)는 무변경이다(`git diff --stat -- src/millie_rec/serving/demo_api.py` 출력 없음, `grep -c "def ratings" demo_api.py` → 0).

## 인계 시그니처 (Phase 6 데모가 verbatim 소비)

```python
# src/millie_rec/serving/ratings_api.py
SURFACE_READER = "reader"          # events.surface
EVENT_RATING = "rating"            # contracts.EVENT_TYPES 안
USER_KEY_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")   # demo_api.py 와 중복 정의(C5)
SQL_RATING_INS = "INSERT OR IGNORE INTO ratings(rating_id, user_key, book_id, stars, ts, recommendation_id) VALUES(?,?,?,?,?,?)"
SQL_EVENT_INS  = "INSERT OR IGNORE INTO events(... 15 컬럼 ...) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"

def build_router(*, db: Database,
                 wake: Callable[[], None] | None = None,
                 invalidate: Callable[[str], object] | None = None,
                 now: Callable[[], datetime] | None = None) -> APIRouter
```

## 라우트 1행

| 파일 | 메서드 | 경로 | status | request | response_model |
|---|---|---|---|---|---|
| `ratings_api.py` | POST | `/api/ratings` | **201** | `RatingIn` | `RatingOut` |

### Phase 6 DEMO-07 이 부르는 요청 JSON

```http
POST /api/ratings
Content-Type: application/json

{ "rating_id": "rat_1c9d00", "user_key": "u-1", "book_id": 3, "stars": 5,
  "ts": "2026-09-07T12:00:00+00:00", "recommendation_id": "rec_8f3a2c" }
```

응답 `201 {"ok": true, "rating_id": "rat_1c9d00"}` (백엔드 서빙 01 §7 `POST /api/ratings` 정본과 동일). `rating_id` 는 클라이언트 발급 `rat_<6hex>` 이고 멱등 키다 — 같은 값으로 재전송하면 201·`ok: true` 를 그대로 주지만 `ratings`·`events` 행은 늘지 않고 `wake()`·`invalidate()` 도 다시 부르지 않는다. `recommendation_id` 는 생략 가능(NULL 저장). `ts` 는 파싱 후 `...Z` 로 정규화해 저장하고, 파싱 실패·`user_key` 형식 위반·`stars` 범위 밖·정의되지 않은 필드는 전부 422다.

부수 효과로 `events` 에 `event_type="rating"`, `surface="reader"`, `payload={"stars": "5"}`, `recommendation_id` 동일, `ts` 동일 정규화, `event_id` = `uuid4().hex`(32자) 행이 1건 생긴다. 이 이벤트는 Nearline 리플레이·대시보드 집계의 입력이지 모델 라벨이 아니다.

## TDD 증거

### RED (Task 1 — 스텁: 201 만 반환, DB 쓰기·검증 없음)

```
E       assert 0 == 1
E        +  where 0 = len([])
tests/serving/test_ratings.py:66: AssertionError
E       AssertionError: assert (0 == 1)
E        +  where 0 = _count(<millie_rec.serving.db.Database object at 0x117a9d490>, 'ratings')
tests/serving/test_ratings.py:86: AssertionError
E       assert (0 == 1)
E        +  where 0 = len([])
E        +    where [] = <test_ratings._Spy object at 0x117c81510>.calls
tests/serving/test_ratings.py:94: AssertionError
E       AssertionError: assert (0 == 1)
E        +  where 0 = _count(<millie_rec.serving.db.Database object at 0x117c81f10>, 'ratings')
tests/serving/test_ratings.py:103: AssertionError
E           AssertionError: ({'user_key': "a';b"}, 201, '{"ok":true,"rating_id":"rat_1c9d00"}')
E           assert 201 == 422
E            +  where 201 = <Response [201 Created]>.status_code
tests/serving/test_ratings.py:121: AssertionError
FAILED tests/serving/test_ratings.py::test_rating_201_persists_and_records_rating_event_with_payload_and_z_ts
FAILED tests/serving/test_ratings.py::test_rating_idempotent_on_duplicate_rating_id
FAILED tests/serving/test_ratings.py::test_rating_calls_wake_and_invalidate_once_only_when_inserted
FAILED tests/serving/test_ratings.py::test_rating_without_recommendation_id_is_null
FAILED tests/serving/test_ratings.py::test_rating_stars_out_of_range_extra_field_user_key_bad_ts_422
5 failed, 3 passed, 2 warnings in 0.29s
```

실패 5건이 전부 `AssertionError` 다(`ImportError`·collection error 아님 — ../.claude/rules/python-tdd.md). 스텁 단계에서 통과한 3건은 예정된 것이다: pydantic 이 이미 처리하는 422 일부가 아니라, 소스 grep 1건(`test_rating_source_has_no_model_label_usage_and_no_fstring_sql`) · `test_no_traceback` · `create_app` 마운트 확인 1건(`api.py` include 2줄은 Task 1 에서 이미 넣었으므로 스텁이라도 201 을 준다).

같은 시점 회귀 3파일도 확인했다 — `uv run pytest tests/serving/test_recommend_level0.py tests/serving/test_api_weights.py tests/test_architecture.py --no-header` → `14 passed, 2 warnings in 0.38s`.

### GREEN (Task 2 — 검증 → INSERT OR IGNORE → 이벤트 → wake·invalidate)

```
......................                                                   [100%]
22 passed, 2 warnings in 0.42s
```

(`tests/serving/test_ratings.py` 8 + `test_recommend_level0.py` 7 + `test_api_weights.py` 4 + `tests/test_architecture.py` 3 = 22 — 플랜 acceptance 와 동일.)

### REFACTOR (Task 3 — ruff · 스모크 포함 최종)

```
3 files left unchanged
All checks passed!
```

`uv run ruff format` 이 세 파일을 그대로 두었고 `uv run ruff check` 도 클린이다(다른 wave 4 파일은 포맷하지 않았다). 최종 실행:

```
32 passed, 2 deselected, 2 warnings in 0.44s
```

= 위 4개 대상 + `tests/serving/test_smoke.py -k "not server_module"`(포트를 여는 2건 deselect).

## TDD Gate Compliance

| Gate | 상태 | 증거 |
|---|---|---|
| RED | 통과 | 스텁 상태에서 5 failed(전부 `AssertionError`) · 3 passed |
| GREEN | 통과 | 구현 후 `22 passed` |
| REFACTOR | 통과(코드 변경 없음) | `ruff format` → `3 files left unchanged`, `ruff check` → `All checks passed!` |

`no_commit: true` 라 `test(...)`/`feat(...)` 커밋은 만들지 않았다. 게이트 증거는 커밋 로그가 아니라 위 pytest 출력이다(플랜 frontmatter `tdd_gate_evidence: pytest-output`).

## 줄 수·경계 확인

| 항목 | 값 | 기준 |
|---|---|---|
| `ratings_api.py` | 80줄 | ≤150 |
| `api.py` | 150줄 | ≤150 (변경 전 148 + 2) |
| `test_ratings.py` | 149줄 | min 50 |
| `grep -c "ratings_router" api.py` | 2 | import + include |
| `grep -c "execute(f" ratings_api.py` | 0 | f-string SQL 없음 |
| `grep -c "INSERT OR IGNORE INTO ratings" ratings_api.py` | 1 | — |
| `git diff --stat -- demo_api.py` | 출력 없음 | demo_api 무변경 |

star 의존: `ratings_api.py` 는 `millie_rec.serving.db` · `millie_rec.serving.schemas` 만 import 한다(같은 슬라이스). 다른 슬라이스 import 0, `contracts` 도 직접 쓰지 않는다 — `tests/test_architecture.py` 3건 통과.

## 위협 모델 처리 (플랜 `<threat_model>`)

| Threat ID | 처리 | 증거 |
|---|---|---|
| T-05-11-01 Tampering(SQL 인젝션) | mitigate | 두 INSERT 모두 `?` 바인딩, `USER_KEY_RE` 불일치 422 — `test_rating_stars_out_of_range_extra_field_user_key_bad_ts_422` 가 `"a';b"` 를 단정, `execute(f` 0건 |
| T-05-11-02 Tampering(별점으로 모델 오염) | mitigate | 소스에 `blend`·`state_weights`·`score` 없음 — `test_rating_source_has_no_model_label_usage_and_no_fstring_sql` |
| T-05-11-03 DoS(재전송 폭주) | mitigate | `INSERT OR IGNORE` + `rowcount` 게이팅 — 중복은 이벤트·wake·invalidate 전부 없음 |
| T-05-11-04 Info Disclosure(예외 문자열) | accept | 예외 경로는 pydantic 422 와 `_422` 뿐 — `test_no_traceback` 이 4개 요청 응답에서 `Traceback` 부재 단정 |

## 계획 대비 편차

### 자동 수정(Rule 1~3) 없음

플랜대로 실행했다. 아래 2건은 플랜 본문 표기와 다르게 구현한 판단이며, 계약·동작·acceptance 에는 영향이 없다.

**1. [판단] `invalidate` 를 `rc` 게이팅에 포함**
- 플랜 Task 2 action 은 `if rc: (wake and wake()); (invalidate and invalidate(...))` 로 이미 두 호출 모두 `rc` 안이다. behavior 절의 "중복 시 wake·invalidate 추가 호출 없음" 과 일치하므로 그대로 따랐다. 별도 편차 아님 — 명시만 해 둔다.

**2. [판단] `_j` 대신 `json.dumps` 인라인**
- 플랜 action 은 `_j({"stars": ...})` 를 썼다. `_j` 는 `onboarding_api` 소유 헬퍼이고, 이 파일은 "demo_api 무변경 + 파일 독립"(Advisor 확정 17 B5) 취지로 상수·헬퍼를 중복 정의하는 방침이라 `json.dumps` 를 직접 썼다. 저장 결과는 동일(`{"stars": "5"}`).

### Advisor 결정 필요 없음 (Rule 4 해당 없음)

## Known Stubs

없음. `now` 파라미터만 현재 미사용이다 — `build_router` 시그니처를 다른 라우터 팩토리와 맞추기 위해 받되, `ratings` 는 서버 시각을 쓰지 않고 클라이언트 `ts` 만 정규화한다(품질 게이트 `ts_future`·`ts_backdated` 판정은 `POST /api/events` 소관, 백엔드 서빙 01 §6).

## Threat Flags

| Flag | File | Description |
|---|---|---|
| threat_flag: new_endpoint | `src/millie_rec/serving/ratings_api.py` | 비인증 쓰기 엔드포인트 1개 추가(`POST /api/ratings`) — 플랜 `<threat_model>` 이 이미 다루는 표면과 동일, 새 surface 아님 |

## Advisor 보고 (요청 사항)

1. **PROGRESS.md 1줄 후보(Advisor 몫)** — "`serving/ratings_api.py` 신설: 아키 §9-3 파일 목록 외. 이유 = `demo_api.py` 가 이미 150줄이라 `POST /api/ratings`(Should, 백엔드 서빙 01 §7)를 넣을 수 없음. 영향 슬라이스 = serving 만, `api.py` include 1줄."
2. **`api.py` 가 정확히 150줄이 됐다** — 상한에 닿았다. 다음에 `api.py` 에 무언가를 더 붙이려면 `create_app` 의 일부를 슬라이스 파일로 빼야 한다.
3. **wave 4 병렬** — 05-10(`state`·`nearline`·`compose`·`cascade`·`rows`·`levels`·`after_completion`)·05-12(`dashboard_*`) 와 파일이 겹치지 않았고, 실행 중 ImportError 재시도도 없었다. `make smoke`·전체 스위트는 지시대로 돌리지 않았다 — wave 4 종료 후 Advisor 몫.
4. **Codex 리뷰 권장** — `serving/` 쓰기 표면 신설이라 ../.claude/rules/codex-review.md 기준 "선택" 이 아닌 "필수" 에 가깝다(비인증 INSERT 2문). `/codex:review --scope working-tree` 를 wave 4 종료 후 한 번 돌리기를 권한다.

## Self-Check: PASSED

- `src/millie_rec/serving/ratings_api.py` FOUND (80줄)
- `src/millie_rec/serving/api.py` FOUND (150줄, `ratings_router` 2회)
- `tests/serving/test_ratings.py` FOUND (149줄, `def test_` 8개)
- 커밋 해시 없음 — `no_commit: true` 이므로 정상
- `.planning/STATE.md` · `.planning/ROADMAP.md` 미변경(오케스트레이터 소유)
</content>
</invoke>
