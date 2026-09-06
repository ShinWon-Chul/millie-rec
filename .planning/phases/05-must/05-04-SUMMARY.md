---
phase: 05-must
plan: 04
subsystem: Serving (persona · onboarding_api · demo_api)
tags: [serving, onboarding, events, persona, sqlite, fastapi, tdd]
requires:
  - src/millie_rec/contracts.py (Catalog · Persona · EVENT_TYPES · BADGE_TYPES)
  - src/millie_rec/serving/schemas.py (freeze — 필드 추가 없음)
  - src/millie_rec/serving/db.py (Database.connect)
  - src/millie_rec/serving/schema.sql (users · preference_snapshots · events · candidate_sets)
provides:
  - "serving.persona: PERSONAS · CATEGORY_TO_PERSONA · assign_persona · persona_index · _josa"
  - "serving.onboarding_api.build_router → GET /api/meta/onboarding · GET /api/candidates/onboarding"
  - "serving.demo_api.build_router → POST /api/preferences(201) · POST /api/events(202)"
  - "serving/onboarding_meta.json (D-14 1벌)"
affects:
  - Plan 05-06 (create_app 배선 — 두 build_router 를 include_router)
  - Plan 05-07 (bench.py — POST /api/preferences 로 user_key 50개 생성)
  - Phase 6 '데모 재구성'(.planning/ROADMAP.md) — /contract-sync 텍스트 동일성 검사
tech-stack:
  added: []
  patterns:
    - "APIRouter 팩토리(의존을 클로저로) — create_app 은 주입만"
    - "sqlite3 이름 바인딩(:field) + EventIn.model_dump() 로 15컬럼 INSERT"
    - "star 의존 회피 = 같은 슬라이스 내부 import(onboarding_api._iso·_j 재사용)"
key-files:
  created:
    - src/millie_rec/serving/persona.py
    - src/millie_rec/serving/onboarding_meta.json
    - src/millie_rec/serving/onboarding_api.py
    - src/millie_rec/serving/demo_api.py
    - tests/serving/test_persona.py
    - tests/serving/test_onboarding_api.py
    - tests/serving/test_demo_api.py
  modified: []
decisions:
  - "demo_api 를 150줄에 맞추기 위해 schemas 를 모듈 단위로 import(`from millie_rec.serving import schemas`)"
  - "seeds 자동 library_add 는 전용 9컬럼 SQL(SQL_LIB_ADD)로 분리 — EventIn 조립 10줄 제거"
  - "events INSERT 는 이름 바인딩(:field)으로 바꿔 15개 위치 인자 나열 제거"
metrics:
  tasks: 3
  tests_added: 26
  duration: "~1h"
  completed: 2026-09-06
commits: 0   # no_commit — 작업 트리에 남긴다(사용자 지시 2026-09-05, Advisor 확정 10)
---

# Phase 5 Plan 04: 취향 설정·이벤트 API 요약

온보딩 메타·후보·취향 설정·이벤트 적재 4개 엔드포인트를 두 개의 `APIRouter` 팩토리로 만들고, 페르소나 4종 매핑과 받침 판정 조사를 순수 함수로 분리했다. 상태 갱신은 전혀 하지 않고 이벤트 INSERT + 주입된 `wake()` 호출까지만 한다(SERV-09 경계).

## 변경 파일 (7개, 전부 신규 · 커밋 0)

| 경로 | 줄 수 | 내용 |
|---|---|---|
| `src/millie_rec/serving/persona.py` | 80 | `PERSONAS` 4종 · `CATEGORY_TO_PERSONA` 11종 · `_josa` · `persona_index` · `assign_persona` |
| `src/millie_rec/serving/onboarding_meta.json` | 22 | `survey_variant v1` · `reading_times` 5 · `criteria` 5 · `subcategories`(IT·소설·철학) |
| `src/millie_rec/serving/onboarding_api.py` | 141 | `GET /api/meta/onboarding` · `GET /api/candidates/onboarding` |
| `src/millie_rec/serving/demo_api.py` | 150 | `POST /api/preferences`(201) · `POST /api/events`(202) |
| `tests/serving/test_persona.py` | 6건 | 매핑·sha256·조사·문장·항상 존재 |
| `tests/serving/test_onboarding_api.py` | 7건 | meta 스키마·supported·캐시 · 후보 라운드로빈·상한·catalog None |
| `tests/serving/test_demo_api.py` | 13건 | 스냅샷 append·cell·library_add·consent=false · dedup·품질 게이트·422·주입 |

**커밋하지 않는다** — 플랜 frontmatter `no_commit: true`. 작업 트리에 그대로 남겼다.

## 라우트 4개

| 파일 | 메서드 | 경로 | status | response_model |
|---|---|---|---|---|
| `onboarding_api.py` | GET | `/api/meta/onboarding` | 200 | `OnboardingMeta` |
| `onboarding_api.py` | GET | `/api/candidates/onboarding` | 200 | `CandidateSet` |
| `demo_api.py` | POST | `/api/preferences` | **201** | `PreferencesResponse` |
| `demo_api.py` | POST | `/api/events` | **202** | `EventsAccepted` |

`POST /api/ratings`(Should)는 wave 4 Plan 05-11 의 별도 파일 `ratings_api.py`(B5) 몫이다 — `demo_api.py` 는 이 플랜 이후 변경 없음.

## 인계 시그니처 (Plan 05-06 · 05-07 이 verbatim 소비)

```python
# src/millie_rec/serving/onboarding_api.py
META_PATH = Path(__file__).parent / "onboarding_meta.json"
SURVEY_VARIANT = "v1"
N_DEFAULT, N_MAX = 30, 60
SUPPORTED_MIN = 20
CATEGORIES_MAX = 3
ALL_BOOKS_N = 10**6

def new_id(prefix: str) -> str
def load_meta(path: Path = META_PATH) -> dict
def catalog_categories_meta(catalog, subcategories) -> list[CategoryMeta]
def build_router(
    *,
    db: Database,
    catalog: Catalog | None = None,
    meta_path: Path = META_PATH,
    now: Callable[[], datetime] | None = None,
) -> APIRouter

# src/millie_rec/serving/demo_api.py
USER_KEY_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
USER_KEY_MSG = "user_key must match ^[A-Za-z0-9_-]{1,64}$"
FUTURE_SKEW_S, BACKDATED_S = 300, 3600
FLAG_TS_FUTURE, FLAG_TS_BACKDATED = "ts_future", "ts_backdated"
FLAG_BOOK_INELIGIBLE = "book_ineligible"
SURFACE_ONBOARDING, EVENT_LIBRARY_ADD = "onboarding", "library_add"

def assign_cell(user_key: str) -> str
def _quality_flag(con, e, now_dt, catalog, *, parsed_ts=None) -> str | None
def build_router(
    *,
    db: Database,
    catalog: Catalog | None = None,
    wake: Callable[[], None] | None = None,
    invalidate: Callable[[str], object] | None = None,
    meta_path: Path = META_PATH,
    now: Callable[[], datetime] | None = None,
) -> APIRouter

# src/millie_rec/serving/persona.py
PERSONAS: tuple[Persona, ...]                # 4종, description="" (템플릿 전)
CATEGORY_TO_PERSONA: dict[str, int]
DESCRIPTION = "회원님은 {cats}{eul} 즐기고, {criterion}{ro} 책을 고르는 독서가입니다."
CATS_NONE, CRITERION_NONE = "다양한 분야", "취향"
CATS_SHOWN_MAX = 2

def _josa(word: str, with_final: str, without_final: str) -> str
def persona_index(categories: Sequence[str]) -> int
def assign_persona(categories: Sequence[str], criterion_label: str | None) -> Persona
```

두 라우터 모두 `APIRouter(prefix="/api")` 를 반환한다. `create_app` 은 `app.include_router(...)` 만 하면 된다(Plan 05-06). `demo_api` 는 `onboarding_api` 의 `META_PATH`·`_iso`·`_j`·`load_meta`·`new_id` 를 같은 슬라이스 내부 import 로 재사용한다.

## persona 매핑 표에 쓴 실제 밀리 분류명

`artifacts/serving/books_kr.json`(9,447권, 카테고리 29종) 실측 이름만 사용했다(읽기만 함, 🧊 freeze 유지).

| 페르소나(인덱스) | 작품 · 인용 | 매핑한 실제 분류명(권수) |
|---|---|---|
| 오디세우스 (0) | 《오디세이아》 "지혜로 승리하리라!" | 경제경영(511) · 자기계발(587) · IT(105) |
| 셜록 홈즈 (1) | 《주홍색 연구》 "사소한 것이 가장 중요하다." | 소설(1719) · 과학(198) · 철학(202) |
| 돈키호테 (2) | 《돈키호테》 "이룰 수 없는 꿈을 꾸리라!" | 인문(632) · 역사(245) · 사회(171) |
| 제인 에어 (3) | 《제인 에어》 "나는 나 자신의 주인입니다." | 에세이/시(714) · 라이프스타일(383) |

나머지 18종(오디오북·어린이·챗북·청소년·웹툰/웹소설·밀리 오리지널·부모·여행·외국어·종교·매거진·디즈니·세계문학전집·도슨트북·빨간펜 동화·만화·미분류·오브제북)은 `int(sha256(name)[:8], 16) % 4` 로 결정적 선택 — 페르소나는 항상 존재한다(D-16). 테스트는 `오디오북`(→ 1)·`미분류`로 손계산 확인.

## 상수 값

| 상수 | 값 | 근거 |
|---|---|---|
| `N_DEFAULT` / `N_MAX` | 30 / 60 | 백엔드 서빙 01 §3 기본 30 · §0 "n ≤ 60" |
| `SUPPORTED_MIN` | 20 | 05-CONTEXT D-14 supported = eligible ≥ 20 |
| `CATEGORIES_MAX` | 3 | 후보 쿼리 카테고리 상한 |
| `FUTURE_SKEW_S` | 300 | 백엔드 서빙 01 §6 미래 +5분 |
| `BACKDATED_S` | 3600 | 백엔드 서빙 01 §6 1h 이상 과거 |
| `SURVEY_VARIANT` | `"v1"` | 백엔드 서빙 01 §2 |

sha256 손계산에 쓴 B 셀 `user_key` = **`"u-1"`** (`int(sha256(b"u-1").hexdigest()[:8], 16) % 2 == 1` → `"B"`). A 셀 대조군은 `"u-2"`. 테스트가 같은 식을 다시 계산해 단정한다(`_expected_cell`).

## TDD 증거

### RED (Task 1 — 스텁 + 테스트 26건)

```
20 failed, 6 passed, 2 warnings in 0.37s
```

전부 `AssertionError`(35건), `ImportError`·`AttributeError`·`TypeError`·`sqlite3.OperationalError` 0건. 발췌:

```
_________ test_persona_index_mapping_table_and_dominant_first_category _________

    def test_persona_index_mapping_table_and_dominant_first_category():
>       assert persona_index(["경제경영"]) == persona_index(["자기계발"]) == persona_index(["IT"]) == 0
E       AssertionError: assert 3 == 0
E        +  where 3 = persona_index(['IT'])

tests/serving/test_persona.py:36: AssertionError
```

```
_______ test_candidates_round_robin_pop_rank_and_persists_candidate_set ________

>       assert out.survey_variant == "v1" and out.created_at == _iso(FIXED_NOW)
E       AssertionError: assert ('v0' == 'v1'
E
E         - v1
E         + v0)

tests/serving/test_onboarding_api.py:132: AssertionError
```

```
    def test_user_key_format_422_on_preferences_and_events_uuid4_passes(tmp_path: Path):
        _, client = _build(tmp_path)
>       assert client.post("/api/preferences", json={"user_key": "a';b"}).status_code == 422
E       assert 201 == 422
E        +  where 201 = <Response [201 Created]>.status_code
```

RED 에서 통과한 6건은 스텁이 이미 만족하는 것들이다 — 페르소나 4종 텍스트(상수라 스텁에도 실제 값), pydantic `extra="forbid"`·상한 422, 소스 grep 2건(`apply_event`·`execute(f` 부재), `catalog=None` 빈 items, 예외 문자열 미노출. 플랜의 "≥23건 RED" 기준에는 3건 못 미치지만, 나머지 20건은 전부 값 단정이 깨지는 정상 RED다.

### GREEN (Task 2 + Task 3)

```
29 passed, 2 warnings in 0.33s
```

(`test_persona.py` 6 + `test_onboarding_api.py` 7 + `test_demo_api.py` 13 + `tests/test_architecture.py` 3)

ruff:

```
6 files already formatted
All checks passed!
```

## TDD Gate Compliance

`no_commit: true` 플랜이라 RED/GREEN/REFACTOR 게이트를 커밋으로 남기지 않았다. 게이트는 위 pytest 출력으로 증명한다 — RED(스텁 + 테스트 26건 → 20 failed, 전부 AssertionError) → GREEN(구현 → 29 passed) → REFACTOR(150줄 압축 후 재실행 → 29 passed, ruff 클린). 커밋 0건이므로 `test(...)`·`feat(...)` 커밋은 존재하지 않는다.

## 구현 결정 (플랜 대비 조정)

1. **`demo_api.py` 150줄 맞추기.** 플랜의 코드 스케치 그대로 쓰면 196줄이었다. 로직·공개 시그니처를 바꾸지 않고 세 가지를 줄였다.
   - `from millie_rec.serving.schemas import (7개 이름)`(ruff isort 가 9줄로 전개) → `from millie_rec.serving import schemas` 1줄, 본문은 `schemas.PreferencesResponse` 처럼 참조. **플랜 key_links 의 `from millie_rec.serving.schemas import` 패턴 grep 은 이 파일에서 더는 맞지 않는다**(`onboarding_api.py` 에는 그대로 있다).
   - `events` INSERT 를 위치 인자 15개 → **이름 바인딩(`:event_id` …)** 으로 바꾸고 `e.model_dump()` 에 `ts`·`selected`·`payload`·`quality_flag` 만 덮어쓴다. 컬럼 이름은 `EventIn` 필드명과 1:1이라 순서 실수가 구조적으로 불가능해졌다.
   - seeds 자동 `library_add` 는 15컬럼 SQL 재사용 대신 **9컬럼 전용 `SQL_LIB_ADD`**(`INSERT OR IGNORE`, `payload='{}'`)로 넣는다. 그래서 `grep -c "INSERT OR IGNORE INTO events"` 는 플랜의 1이 아니라 **2**다.
2. **`_iso`·`_j` 중복 정의 제거.** 플랜은 두 파일에 각각 두라고 했지만 같은 슬라이스 안이라 `demo_api` 가 `onboarding_api._iso`·`_j` 를 import 한다(줄 수 + 표기 일관성). `_422` 는 `loc` 이 `["query", …]` / `["body", …]` 로 달라 각 파일에 그대로 중복 정의했다. `USER_KEY_RE` 도 `privacy_api.py` 와 중복 정의 유지(revision C5).
3. **`_iso` 가 `astimezone(UTC)` 를 흡수.** `onboarding_api._iso` 가 `dt.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")` 다 — revision C3 의 Z 정규화가 한 곳에서 끝난다.
4. **`_check_key` 함수 제거, 호출부 2곳에 인라인.** `USER_KEY_MSG` 상수는 남겨 두 곳이 같은 문구를 쓴다.
5. **`FLAG_*` 3개를 한 줄에 두지 못했다.** `FLAG_TS_FUTURE, FLAG_TS_BACKDATED, FLAG_BOOK_INELIGIBLE = "ts_future", "ts_backdated", "book_ineligible"` 은 104자로 ruff `line-length = 100` 위반이라 두 줄로 나눴다. 플랜 acceptance 의 `grep -n '"ts_future", "ts_backdated", "book_ineligible"'` 1행은 성립하지 않는다.
6. **`grep -c "hash(" demo_api.py` 가 1**로 나오지만 `assign_cell` docstring 의 `CPython hash() 금지` 문구다. 실제 호출은 `hashlib.sha256` 1건뿐이다.

## 확인한 계약·규칙

- 세 py 파일 모두 `millie_rec.contracts` · `millie_rec.serving.*` 만 import — `data`·`app`·`retrieval`·`ranking`·`reranking`·`evaluation` grep 0건, `tests/test_architecture.py` 3 passed.
- `schemas.py`·`contracts.py`·`schema.sql`·`artifacts/serving/*` 무변경(🧊 freeze). 의존성 추가 0.
- `must_not_touch` 전부 무변경 — `serving/__init__.py`(05-01 소유)·`serving/api.py`(05-06 배선) 포함. 새 공개 이름을 `__init__.__all__` 에 넣지 않았다.
- 파일 ≤150줄: persona 80 · onboarding_api 141 · demo_api 150.
- SQL 전부 `?` / `:name` 바인딩, `execute(f` 0건. `apply_event`·`StateStore` 0건(SERV-09).
- `onboarding_meta.json` 의 `reading_times`·`criteria` 문구가 `demo/config/onboarding.json` S1·S3 `options` 와 글자 동일(grep 각 1). 서버는 `demo/` 를 읽지 않는다(D-14).
- persona `description` 이 `demo/mock/preferences_response.json` 문장과 동일(revision A1).

## Known Stubs

없음. 네 엔드포인트 모두 실제 DB 쓰기·카탈로그 조회를 한다. `catalog=None`·`wake=None`·`invalidate=None` 경로는 스텁이 아니라 스켈레톤 기동(아티팩트 없는 로컬)을 위한 정상 분기다.

## Advisor 보고

1. **`demo_api.py` 가 정확히 150줄**이다. 여기에 한 줄이라도 더 붙으면 한도를 넘는다. Plan 05-11 의 `POST /api/ratings` 를 `ratings_api.py`(B5)로 분리하기로 한 결정이 그대로 유효하고, 이 파일에는 앞으로 아무것도 추가하지 말아야 한다.
2. **`onboarding_api.py` 신설을 PROGRESS.md 에 1줄 남겨야 한다** — 아키텍처 문서 §9-3 serving 파일 분할 목록에 없는 파일이다(Advisor 확정 17 B2). `catalog_categories_meta` 가 `compose.py` 의 `catalog_categories` 와 기능 중복인 것도 같은 줄에 적을 항목이다(revision C11, `_shared` 는 3곳부터).
3. **`serving/__init__.py` 를 건드리지 않았다.** `build_router` 2개·`assign_persona`·`assign_cell` 을 공개 표면(`__all__`)에 올릴지는 05-01 / 05-06 소유자 판단이다. 현재는 `millie_rec.serving.demo_api` 경로로만 접근 가능하다.
4. **`_quality_flag` 의 `ts_backdated` 기준이 "그 user_key 의 `MAX(ts)`"** 라서, 미래 이벤트(`ts_future`)가 먼저 저장되면 그 뒤 정상 이벤트가 상대적으로 과거가 된다. 같은 user_key 로 +5분 초과 이벤트를 받은 직후 1h 이상 이전 이벤트가 오면 `ts_backdated` 가 붙는다 — 문서 규약대로 구현했고 분석용 플래그일 뿐 저장은 되지만, 대시보드 `flagged_events` 해석 시 알고 있어야 한다.
5. **작업 중 `uv run ruff format tests/serving/*.py` 를 한 번 실행했다**(글롭). 다른 플랜 소유의 `tests/serving/` 파일이 그 시점에 동시 편집 중이었다면 포맷만 정규화됐을 수 있다. 의미 변경은 없고 각 소유자가 자기 파일에 `ruff format` 을 다시 돌리면 동일 결과다. 이후로는 자기 파일만 지정해 실행했다.
6. **wave 1 종료 후 Advisor 1회**: 전역 `uv run pytest --no-header` · `make smoke` · `/contract-sync`(Phase 6 에서 `onboarding_meta.json` ↔ `demo/config/onboarding.json` 항목 추가).

## Self-Check: PASSED

- 파일 7개 전부 존재 확인(`persona.py` 80 · `onboarding_meta.json` · `onboarding_api.py` 141 · `demo_api.py` 150 · 테스트 3개 6/7/13건)
- 커밋 0건 — `no_commit: true` 이므로 커밋 해시 검증 대상 없음
- `.planning/STATE.md`·`.planning/ROADMAP.md` 무변경(오케스트레이터 소유)

## Codex 수정 반영 (2026-09-06, 브리프 D)

**T2 (적대 리뷰 high, 사용자 승인) — 동의 철회 후 이벤트 재유입.** `POST /api/events` 가 `users.consent` 를 보지 않아, `DELETE /api/users/{key}/personalization` 으로 `consent=0` 이 된 뒤에도 클라이언트가 계속 이벤트를 보내면 그대로 적재되고 Nearline 웨이크까지 걸려 상태가 다시 채워졌다.

- `events_gate.consent_off_keys(con, user_keys)` 를 신설했다. 배치의 **distinct user_key 마다 1회** `SELECT 1 FROM users WHERE user_key = ? AND consent = 0`(파라미터 바인딩)으로 조회한다. 해당 유저의 이벤트는 INSERT 하지 않고 `accepted` 에서 빼며, 웨이크는 `accepted > 0` 조건 그대로라 자동으로 걸리지 않는다.
- **`consent_off` 표기 선택:** `schemas.FlaggedEvent.quality_flag` 가 `Literal` 이 아닌 `str` 이라 응답 스키마를 바꾸지 않고 값만 추가할 수 있었다. 그래서 차단된 이벤트를 기존 `flagged` 리스트에 `{"event_id": …, "quality_flag": "consent_off"}` 로 담는다. `duplicates` 의미(= `event_id` 중복)는 건드리지 않았다. 응답 형태 🧊 freeze 유지 — 필드 추가 없음.
- `users` 행이 없는 익명·미온보딩 키는 **기존 동작 그대로 수락**한다(동의 철회 이력이 없는 유저).
- **파일 분할:** `demo_api.py` 가 정확히 150줄이라 `_quality_flag` · `_parse` 와 게이트 상수(`FUTURE_SKEW_S` · `BACKDATED_S` · `FLAG_TS_FUTURE` · `FLAG_TS_BACKDATED` · `FLAG_BOOK_INELIGIBLE` · `SQL_LAST_TS`)를 새 파일 `src/millie_rec/serving/events_gate.py`(50줄, 아키 §9-3 목록 외 신설 — 05-04-SUMMARY 항목 1·2 와 같은 사유, `ratings_api.py` 선례)로 옮기고 `parse_ts` · `quality_flag` 공개 이름으로 노출했다. `demo_api.py` 는 136줄로 줄었다.
- 테스트 2건 추가(`tests/serving/test_demo_api.py`): `test_events_from_consent_off_user_not_stored_and_no_wake`(202 · `accepted == 0` · `flagged == [consent_off]` · events 0행 · wake 0회), `test_events_consent_on_and_unknown_user_key_still_accepted`(consent=1 · 익명 수락 · 혼합 배치는 clean 만 저장하고 wake 1회).
- **남은 표면:** `POST /api/ratings`(`ratings_api.py`)도 `rating` 이벤트를 자동 기록하지만 이 브리프의 편집 범위 밖이라 손대지 않았다. 같은 동의 게이트가 필요한지는 Advisor 판단.
