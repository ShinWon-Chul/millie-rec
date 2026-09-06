---
phase: 05-must
plan: 02
subsystem: Serving / Page Composition
tags: [compose, rows, dedup, badges, anchor, fresh_picks, SERV-01, SERV-02, SERV-08]
requires:
  - "contracts.Row · ScoredItem · Badge · Catalog · Neighbors · ROW_ANCHOR_PREFIX · BADGE_TYPES · FALLBACK_*"
  - "serving/fallback.py: trending_row · TRENDING_* · SOURCE_POPULARITY (Plan 05-03 이 이름·시그니처를 바꾸지 않는다)"
provides:
  - "compose_rows(...) -> (rows, dedup_removed) — Must 5행 / 비개인화 2행"
  - "build_response(..., rows=, dedup_removed=, latency_breakdown=, user_state_weights=) 확장"
  - "with_meta · normalize_title · catalog_categories · dedup_rows"
  - "serving/rows.py: neighbor_row(앵커·after_completion 공용) · fresh_row · personal_rows · mix · title_of"
  - "serving/badges.py: badge_for · attach_badges · REVIEW_MIN_COUNT · REVIEW_MIN_COUNT_NO_RATING"
affects:
  - "Plan 05-06 (cascade·배선) — compose_rows·build_response 를 verbatim 소비"
  - "Plan 05-10 (after_completion, wave 4) — _neighbor_row 호출만 추가"
tech-stack:
  added: []
  patterns:
    - "05-PATTERNS.md §10 Analog A(Row 조립) · B(meta replace) · C(_norm 정규화) · D(Neighbors Protocol)"
key-files:
  created:
    - src/millie_rec/serving/badges.py
    - src/millie_rec/serving/rows.py
    - tests/serving/test_compose.py
  modified:
    - src/millie_rec/serving/compose.py
decisions:
  - "행 간 channel_mix 단정은 '합계 == len(items)' 대신 '집계 결과와 정확히 일치'로 단정(플랜 내부 모순 해소)"
  - "personal_rows(...) 헬퍼 신설 — compose_rows 를 12줄 수준으로 유지"
  - "compose.py / rows.py 2파일 분할(Advisor 승인 2026-09-06) — 각 144줄로 150줄 규칙 충족"
metrics:
  tasks: 3
  tests_added: 16
  duration: ~1h
  completed: 2026-09-06
commits: 0   # no_commit — 작업 트리에 남긴다(사용자 지시 2026-09-05, Advisor 확정 10)
---

# Phase 5 Plan 02: Page Composition (Must 5행·dedup·배지) Summary

`serving/compose.py` 에 Must 5행(`continue_reading → anchor_<seed₁> → persona_shelf → trending → fresh_picks`)·행 간 dedup(book_id + 정규화 제목)·`catalog.meta` 5필드 조인·비개인화 2행을 넣고, 배지 6종 규칙은 신설 `serving/badges.py` 로 분리했다. 배선(cascade)은 Plan 05-06 몫이라 이 플랜은 순수 함수만 만든다.

## 변경 파일 (커밋하지 않는다 — 작업 트리에 남긴다)

| 파일 | 상태 | 줄 수 |
|---|---|---|
| `src/millie_rec/serving/compose.py` | 수정 (60 → 144) | 144 |
| `src/millie_rec/serving/rows.py` | 신설 (Advisor 승인 분할) | 144 |
| `src/millie_rec/serving/badges.py` | 신설 | 70 |
| `tests/serving/test_compose.py` | 신설 (테스트 16건) | 382 |

`must_not_touch` 목록의 파일은 하나도 건드리지 않았다. `serving/__init__.py` 무수정. `tests/serving/test_compose.py` 는 분할 이후에도 **한 줄도 고치지 않았다**(import 경로 포함). git 조작 0회 (`git add`·`git commit`·`git stash` 없음).

## TDD 증거

### RED — `uv run pytest tests/serving/test_compose.py --no-header`

요약 줄 (스텁 상태):

```
15 failed, 1 passed in 0.22s
```

`ImportError`·`AttributeError`·`TypeError`·`SyntaxError`·collection error **0건** (grep 확인). 실패 사유 발췌 3건 (RED 시점 줄 번호 — 이후 docstring 정리로 +2 이동):

```
E       AssertionError: assert 'anchor_1' in []
tests/serving/test_compose.py:129: AssertionError
--
E       AssertionError: assert 'persona_shelf' in {}
tests/serving/test_compose.py:149: AssertionError
--
E       assert 0 == 1
tests/serving/test_compose.py:224: AssertionError
```

통과한 1건은 `test_build_response_default_path_is_unchanged_phase2_shape` — 스텁에서도 통과하는 것이 정상이다(하위 호환 회귀 검사이므로 RED 가 아니어야 한다, Advisor 확정 7).

같은 시점 기존 회귀 4파일:

```
uv run pytest tests/serving/test_recommend_level0.py tests/serving/test_smoke.py tests/serving/test_schemas.py tests/test_architecture.py --no-header
24 passed, 2 warnings in 0.30s
```

### GREEN

```
uv run pytest tests/serving/test_compose.py --no-header
16 passed in 0.14s
```

```
uv run pytest tests/serving/test_compose.py tests/serving/test_recommend_level0.py tests/serving/test_smoke.py tests/serving/test_schemas.py tests/test_architecture.py --no-header
40 passed, 2 warnings in 0.34s
```

기존 테스트 단정은 한 줄도 고치지 않았다.

### REFACTOR

```
uv run ruff format --check src/millie_rec/serving/compose.py src/millie_rec/serving/badges.py tests/serving/test_compose.py
3 files already formatted

uv run ruff check src/millie_rec/serving/compose.py src/millie_rec/serving/badges.py tests/serving/test_compose.py
All checks passed!
```

정리 내용: 모듈 docstring 갱신, `ScoredItem`·`Row` 조립부를 위치 인자로 압축(`CH_CONTENT`·`CH_POP` 상수 도입), docstring 4건 E501 해소, 주석에서 `itemknn` 문자열 제거(`data.md` 표기 규칙). 로직·시그니처 변경 없음, 재실행 후 40 passed 유지.

## TDD Gate Compliance

`no_commit: true` 이므로 `test(...)`·`feat(...)` 커밋 게이트는 존재하지 않는다. 플랜 frontmatter 의 `tdd_gate_evidence: pytest-output` 대로 게이트는 위 pytest 출력으로 증명한다 — RED(15 failed, 전부 `AssertionError`) → GREEN(16 passed) → REFACTOR(ruff 클린 + 40 passed) 순서가 지켜졌다. RED 단계에서 예상 밖으로 통과한 테스트 1건은 하위 호환 검사라 설계상 통과가 맞다.

## 구현 요지

**행 5개 (각각 함수 하나).**

| 행 | 출처 | 비고 |
|---|---|---|
| `continue_reading` | `continue_ids` 인자 | `source=None`·`channel_mix={}`. 비면 빈 행 유지(프론트가 숨김) |
| `anchor_<seed₁>` | `rows.neighbor_row` — `Neighbors.neighbors(seed₁, 20)` → `Catalog.eligible` − exclude − seed → 가중 상위 12 | `source="content"`·`source_channels=("content",)`·`channel_mix={"content": n}`, `reason` = 행 제목 |
| `persona_shelf` | 파이프라인 `items` 중 exclude 밖 앞 12권(D-01, `rows.personal_rows`) | 제목 `"{name}의 서가"`, 이름 없으면 `"회원님의 서가"` |
| `trending` | `catalog.popular()` − exclude 상위 12 | `fallback.trending_row` 재사용 |
| `fresh_picks` | leftover 중 선택 카테고리 밖 → 부족분은 미선택 카테고리 인기 라운드로빈(D-02, `rows.fresh_row`) | 카테고리별 풀을 **exclude 로 먼저 거른 뒤** `zip_longest` 순회 |

**상수(`rows.py` 소유):** `ROW_SIZE = 12` · `ANCHOR_NEIGHBORS = 20` · `FRESH_POOL_N = 30` · `ROW_ORDER`(렌더 순서 정본) · `SOURCE_CONTENT = "content"` · `REASON_ANCHOR = "『{title}』을 좋아하셨다면"` · `SUBTITLE_ANCHOR = "결이 비슷한 책"`.

**dedup(D-04, `compose.dedup_rows`):** 렌더 순서 앞 행 우선, `book_id` **와** `normalize_title`(`[^\w]` 제거 + casefold) 두 기준. 제거 후 `position` 재부여 + `channel_mix` 재계산, 제거 수는 `dedup_removed` 로 반환.

**배지(`badges.py`):** `bestseller` = `pop_rank` → "인기 N위" / `review` 3단 폴백(별점+리뷰≥3 → "★4.2 · 리뷰 21", 별점 결측·리뷰≥10 → "리뷰 15", 그 외 → `bestseller`) / `author`·`publisher` 는 시드 meta 와 일치할 때만 / `buzz` = `millie_label` / `light` 는 Should 라 항상 `None`. `criterion=None` 이면 배지를 붙이지 않는다. `shelf_count` 는 review 텍스트에 넣지 않았다.

**비개인화(SERV-08):** `level >= 2` 는 `trending` + `fresh_picks` 2행만. `rows[0]` 은 항상 `trending`, `items` 는 호출자가 넘긴 인기 결과.

## Plan 05-06 인계 시그니처 (verbatim)

```python
# src/millie_rec/serving/compose.py — 순서·dedup·배지 부착·응답 DTO
ZERO_WEIGHTS = {"alpha": 0.0, "beta": 0.0, "gamma": 0.0}
ROW_ORDER = ("continue_reading", ROW_ANCHOR_PREFIX, "persona_shelf", "trending", "fresh_picks")
ROW_SIZE = 12   # rows.py 에서 import — `compose.ROW_SIZE` 로도 그대로 읽힌다


def normalize_title(s: object) -> str: ...


def with_meta(items, catalog): ...   # 정의는 rows.py — compose 에서도 import 가능


def catalog_categories(catalog: Catalog) -> list[str]: ...


def dedup_rows(rows: Sequence[Row]) -> tuple[tuple[Row, ...], int]: ...


def compose_rows(
    *,
    items: Sequence[ScoredItem],
    catalog: Catalog,
    neighbors: Neighbors | None,
    level: int,
    seeds: Sequence[int] = (),
    categories: Sequence[str] = (),
    criterion: str | None = None,
    persona_name: str | None = None,
    continue_ids: Sequence[int] = (),
    all_categories: Sequence[str] = (),
    k: int = ROW_SIZE,
) -> tuple[tuple[Row, ...], int]: ...


def build_response(
    items: Sequence[ScoredItem],
    *,
    model_version: str,
    level: int,
    k: int,
    t0: float,
    context: str | None,
    rows: Sequence[Row] | None = None,
    dedup_removed: int = 0,
    latency_breakdown: dict[str, float] | None = None,
    user_state_weights: dict[str, float] | None = None,
) -> RecommendResponse: ...


def default_variant(pipelines: dict[str, Pipeline]) -> str | None: ...


def new_rec_id() -> str: ...


# src/millie_rec/serving/rows.py — 행 하나를 만드는 일(행 상수·메타 조인 포함)
ROW_SIZE, ANCHOR_NEIGHBORS, FRESH_POOL_N = 12, 20, 30
SOURCE_CONTENT = "content"
CH_CONTENT, CH_POP = ("content",), ("popularity",)
META_KEYS = ("title", "authors", "image_url", "book_format")
TITLE_CONTINUE, TITLE_FRESH = "이어 읽기", "새로운 발견"
TITLE_PERSONA, TITLE_PERSONA_DEFAULT = "{name}의 서가", "회원님의 서가"
SUBTITLE_ANCHOR = "결이 비슷한 책"
REASON_ANCHOR = "『{title}』을 좋아하셨다면"
Items = Sequence[ScoredItem]
Cats = Sequence[str]


def with_meta(items: Items, catalog: Catalog | None) -> tuple[ScoredItem, ...]: ...


def mix(items: Items) -> dict[str, int]: ...


def title_of(catalog: Catalog, book_id: int) -> str: ...


def neighbor_row(
    row_id: str,
    title: str,
    subtitle: str | None,
    seed: int,
    nbrs: Sequence[tuple[int, float]],
    catalog: Catalog,
    exclude: set[int],
) -> Row | None: ...


def fresh_row(
    catalog: Catalog, leftover: Items, categories: Cats, all_categories: Cats, exclude: set[int]
) -> Row: ...


def personal_rows(
    items: Items,
    catalog: Catalog,
    neighbors: Neighbors | None,
    seeds: Sequence[int],
    categories: Cats,
    persona_name: str | None,
    continue_ids: Sequence[int],
    all_categories: Cats,
) -> tuple[Row, ...]: ...


# src/millie_rec/serving/badges.py
REVIEW_MIN_COUNT = 3
REVIEW_MIN_COUNT_NO_RATING = 10


def badge_for(
    meta: dict,
    *,
    criterion: str | None,
    seed_authors: frozenset[str] = frozenset(),
    seed_publishers: frozenset[str] = frozenset(),
) -> Badge | None: ...


def attach_badges(
    rows: Sequence[Row], catalog: Catalog, criterion: str | None, seeds: Sequence[int]
) -> tuple[Row, ...]: ...
```

호출 규약 3가지 (05-06 이 지켜야 한다):

1. `build_response(rows=None)` 은 Phase 2 형태(trending 1행)를 **바이트 단위로** 유지한다. 5행을 쓰려면 `rows=` 를 반드시 넘긴다.
2. `catalog_categories(catalog)` 는 전 카탈로그 meta 를 훑는다 — **기동 시 1회**만 부르고 결과를 `all_categories` 로 넘긴다(위협 T-05-02-03).
3. `compose_rows(catalog=...)` 는 `catalog` 가 **None 이 아니라고 가정**한다(아래 Advisor 보고 6번).
4. `with_meta` 의 정의는 `rows.py` 로 옮겼지만 `compose.py` 가 import 해 쓰므로 `from millie_rec.serving.compose import with_meta` 도 그대로 동작한다. 행 상수(`REASON_ANCHOR` 등)는 `millie_rec.serving.rows` 에서 가져온다.

## Deviations from Plan

### Rule 1 (버그) — 플랜 내부 모순 해소: channel_mix 단정

- **발견:** Task 1 `<behavior>` 의 dedup 절이 "모든 행 `sum(channel_mix.values()) == len(items)`" 를 요구하는데, 같은 플랜 Task 2 골격은 `continue_reading` items 를 `source=None`·`source_channels=()` 로 만들라고 지정한다. 두 지시를 동시에 만족할 수 없다(1권짜리 `continue_reading` 은 합계 0, 길이 1).
- **처리:** 테스트를 "각 행의 `channel_mix` == 그 행 items 의 `source_channels` 집계" 로 단정했다. dedup 후 재계산(revision C1)이라는 의도를 그대로 검사하면서 채널 없는 행도 성립하는, 더 강한 단정이다.
- **파일:** `tests/serving/test_compose.py::test_dedup_by_book_id_and_normalized_title_counts_removed`

### Rule 3 (진행 차단 해소) — `personal_rows(...)` 헬퍼 신설

- 플랜 골격은 개인화 5행 조립을 `compose_rows` 본문에 인라인했으나 그러면 함수 하나가 약 50줄이 된다(플랜 자신의 "함수 하나 = 관심사 하나, 각 ≤12줄" 위반). 개인화 분기를 `personal_rows(...)` 로 뺐다(분할 후 `rows.py` 소유). 공개 시그니처·동작은 플랜 그대로다.

### 라인 수 압축 (로직 무변경)

- `CH_CONTENT`·`CH_POP`·`META_KEYS` 모듈 상수를 추가하고 `ScoredItem`·`Row` 조립을 위치 인자로 바꿨다. 플랜 `<interfaces>` 에 없는 이름이지만 상수일 뿐이며 계약 표면이 아니다. 이 압축으로 `compose.py` 333 → 304줄.
- 이후 Advisor 승인 분할(아래)에서 `Items`·`Cats` 타입 별칭과 `build_response` 의 `keep` 플래그로 다시 압축해 두 파일 각 144줄이 됐다. `popular_items` 는 호출처가 하나뿐이라 `personal_rows` 안으로 인라인했다.

## Advisor 보고 (이 Worker 가 바꾸지 않은 것)

1. **✅ 해소: `rows.py` 분할(Advisor 승인 2026-09-06).** 최초 보고 시 `compose.py` 는 304줄로 150줄 규칙을 넘겼다. Advisor 가 제안대로 2파일 분할을 승인해 다음과 같이 나눴다 — **`compose.py` 144줄 · `rows.py` 144줄**로 둘 다 규칙을 충족한다.
   - `serving/rows.py`(신설, 144줄): `with_meta` · `mix` · `title_of` · `neighbor_row` · `fresh_row` · `personal_rows` + 행 상수(`ROW_SIZE`·`ANCHOR_NEIGHBORS`·`FRESH_POOL_N`·`SOURCE_CONTENT`·`CH_CONTENT`·`CH_POP`·`META_KEYS`·`TITLE_*`·`SUBTITLE_ANCHOR`·`REASON_ANCHOR`) + 타입 별칭 `Items`·`Cats`. 옮긴 함수는 `_` 접두를 떼고 공개 이름으로 바꿨다(같은 슬라이스 내부 import 이므로 `__init__` 노출 불필요).
   - `serving/compose.py`(144줄): `ZERO_WEIGHTS` · `ROW_ORDER` · `default_variant` · `new_rec_id` · `normalize_title` · `catalog_categories` · `dedup_rows` · `compose_rows` · `build_response`.
   - **승인안과 다른 두 곳(둘 다 순환 import 회피가 이유):** (i) `with_meta` 는 `rows.py` 로 옮겼다 — `neighbor_row`·`fresh_row`·`personal_rows` 가 모두 부르므로 `compose.py` 에 두면 `compose ↔ rows` 순환이 된다. `compose.py` 가 import 해 쓰므로 `from millie_rec.serving.compose import with_meta` 는 그대로 동작한다(테스트가 그 경로로 import 해 통과). (ii) `dedup_rows` 는 `compose.py` 에 남겼다 — `normalize_title` 을 부르는데 그 함수는 `compose.py` 소유이기 때문이고, 줄 수 균형(144/144)에도 맞았다.
   - `popular_items` 는 별도 함수를 없애고 `personal_rows` 안으로 인라인했다(호출처 1곳).
   - 공개 시그니처·동작·반환값은 전부 불변이다. 테스트 파일은 **한 줄도 고치지 않았고**(import 경로 포함) 개수·단정 그대로 16건이 통과한다.
   - Plan 05-09 가 `PROGRESS.md` 에 1줄 필요: `serving/rows.py` 신설(아키 §9-3 목록 외, Advisor 승인 2026-09-06) — `badges.py` 와 같은 절차.
2. **`serving/__init__.py` 미수정.** `badges.py` 의 공개 이름(`badge_for`·`attach_badges`)을 `__all__` 에 넣지 않았다 — 그 파일은 Plan 05-01 소유이고 `compose` 내부 이름은 노출하지 않는 기존 관례(`compose.py` 머리 주석)와도 맞는다. `app/` 이 배지를 직접 쓸 일이 생기면 그때 Advisor 가 판단한다.
3. **`app/pipeline_kr.py::WithMeta` 와 `compose.with_meta` 중복.** star 의존상 serving 은 app 을 import 할 수 없어 의도적 중복이다(`architecture.md` "중복 < 결합"). 두 곳의 조인 필드 5개가 어긋나지 않게 유지해야 한다.
4. **`k` 인자는 받되 쓰지 않는다.** 행 크기는 `ROW_SIZE` 고정이고 평탄화 `k` 는 `build_response` 가 처리한다(플랜 지시 그대로). 05-06 이 `compose_rows(k=...)` 로 행 크기를 바꿀 수 있다고 오해하지 않도록 docstring 에 명시했다.
5. **`level == 1`(캐시) 경로.** `compose_rows` 는 `level < 2` 를 전부 개인화 5행으로 처리한다. 실제 level 1 은 캐시된 rows 를 재사용하는 경로라 `compose_rows` 를 다시 부르지 않을 가능성이 크다 — 배선은 Plan 05-06 판단.
6. **`catalog=None` 은 지원하지 않는다.** `with_meta` 만 `None` 을 견디고 `_title_of`·`_popular_items`·`_fresh`·`attach_badges` 는 `catalog` 메서드를 직접 부른다. 아티팩트 없는 로컬 기동(`local-run.md`)에서는 `catalog` 가 `None` 일 수 있으므로 **05-06 의 cascade 가 `catalog is None` 이면 `compose_rows` 를 부르지 않고 level 3 로 가야 한다**. 지금 방어 코드를 넣으면 플랜 시그니처(`catalog: Catalog`)와 어긋나므로 넣지 않았다.

## Known Stubs

| 위치 | 내용 | 사유 |
|---|---|---|
| `src/millie_rec/serving/badges.py::badge_for` | `criterion == "light"` 이면 항상 `None` | `light` 배지는 Should — 이 페이즈 범위 밖(05-CONTEXT "배지 6종 규칙" 절 · `serving.md`). 배지 없이 카드가 정상 렌더되므로 목표를 막지 않는다 |

## Threat Flags

없음. 플랜 `<threat_model>` 밖의 새 보안 표면(네트워크 엔드포인트·인증 경로·파일 접근·스키마)을 만들지 않았다. T-05-02-01(밀리 저작 텍스트 노출)은 `grep -c description src/millie_rec/serving/compose.py` = 0 으로 확인했다 — `with_meta` 는 `META_KEYS` 4필드 + `difficulty` 만 조인한다.

## Self-Check: PASSED

- `src/millie_rec/serving/compose.py` FOUND (144줄)
- `src/millie_rec/serving/rows.py` FOUND (144줄)
- `src/millie_rec/serving/badges.py` FOUND (70줄)
- `tests/serving/test_compose.py` FOUND (382줄, `grep -c "def test_"` = 16)
- 커밋 0건 (`no_commit: true`) — 해시 검증 대상 없음
- `uv run pytest tests/serving/test_compose.py tests/serving/test_recommend_level0.py tests/serving/test_smoke.py tests/serving/test_schemas.py tests/test_architecture.py --no-header` → **40 passed**
- `uv run ruff format --check` · `uv run ruff check` (자기 3파일) → 클린
- `wc -l` 150줄 규칙: `compose.py` 144 · `rows.py` 144 · `badges.py` 70 — **전부 충족**(Advisor 승인 분할로 해소)
