---
phase: 05-must
plan: 10
subsystem: Serving (Should 꼬리 — after_completion 행)
tags: [SERV-11, D-13, D-10, after_completion, nearline, compose, cascade, tdd]
requires: [serving.StateStore, serving.NearlineLoop, serving.compose_rows, serving.rows.neighbor_row, serving.Level1Cache, contracts.Neighbors]
provides: [serving.after_completion.precompute, serving.after_completion.stored, serving.after_completion.prepend_after, serving.after_completion.fresh_cache, StateStore.after_completion, compose_rows(after_completion=), levels.variant_for, levels.CELL_VARIANT, levels.PIPE_K_MIN]
affects: [Phase 6 '데모 재구성'(.planning/ROADMAP.md) DEMO-07 뷰어 완독 → 메인 변화, wave 4 Advisor 게이트(pytest·smoke·bench)]
tech-stack:
  added: []
  patterns: [신설 파일로 150줄 한도 회피, dict 한 칸 교체(단일 writer), 함수 이동 + __all__ 재-export, 캐시 정합 판정 함수화]
key-files:
  created:
    - src/millie_rec/serving/after_completion.py
    - tests/serving/test_after_completion.py
  modified:
    - src/millie_rec/serving/state.py
    - src/millie_rec/serving/nearline.py
    - src/millie_rec/serving/compose.py
    - src/millie_rec/serving/cascade.py
    - src/millie_rec/serving/levels.py
decisions: [D-13, D-10 (.planning/phases/05-must/05-CONTEXT.md), Advisor 확정 2026-09-06 1~6 (신설 파일·state 2줄·nearline 훅·compose 인자·variant_for 이동·캐시 무효화)]
metrics:
  tasks: 3
  files: 7
  tests_added: 9
  completed: 2026-09-06
commits: 0   # no_commit
---

# Phase 5 Plan 10: after_completion — 완독 직후 최상단 행 Summary

Nearline 이 `completion` 이벤트를 처리할 때 `Neighbors.neighbors(book, 20)` 을 미리 계산해 `StateStore.after_completion` 에 저장하고, 다음 `GET /api/recommend` 의 rows **최상단**에 "『X』을 완독하셨네요, 다음은"(`source=content`) 행을 붙인다. 새 완독이 이전 것을 덮어쓰고, 완독 뒤 그 행이 없는 level 1 캐시는 무효화돼 다시 나오지 않는다.

## 커밋

**커밋하지 않는다 — 작업 트리에 남기고 이 SUMMARY 에 변경 파일 목록을 적는다**(사용자 지시 2026-09-05, 플랜 frontmatter `no_commit: true`). `commits: 0`. `git log --oneline -1` → `8e5172b chore: project scaffold …`(플랜 시작 시점과 동일, 변화 없음). `git add`·`git commit`·`git clean` 등 git 쓰기 명령을 한 번도 실행하지 않았다.

## 변경 파일 (줄 수, 150 한도)

| 파일 | 줄 | 성격 |
|---|---|---|
| `src/millie_rec/serving/after_completion.py` | 50 | **신설** — 사전 계산·읽기·행 붙이기·캐시 정합 |
| `src/millie_rec/serving/state.py` | 150 | +2줄 (`after_completion` dict 속성 · `forget` 정리) |
| `src/millie_rec/serving/nearline.py` | 122 | +3줄 (completion 훅 · import) |
| `src/millie_rec/serving/compose.py` | 148 | +4줄 (`ROW_ORDER` 맨 앞 · `after_completion=` 인자 · `prepend_after` 호출) |
| `src/millie_rec/serving/cascade.py` | 146 | 배선 +3줄, `variant_for`·상수 2개는 `levels.py` 로 이동 |
| `src/millie_rec/serving/levels.py` | 74 | `CELL_VARIANT`·`PIPE_K_MIN`·`variant_for` 수용 |
| `tests/serving/test_after_completion.py` | 309 | **신설** — 9건 |

`src/` 7파일 전부 ≤150. 공개 import 경로 무변경: `from millie_rec.serving.cascade import CELL_VARIANT, PIPE_K_MIN`(기존 `tests/serving/test_cascade.py:31`)은 `cascade.__all__` 재-export 로 그대로 동작한다.

## TDD 증거

### RED — 신규 9건 중 6건 실패, 전부 `AssertionError`

명령: `uv run pytest tests/serving/test_after_completion.py --no-header`

```
E       assert [] == [(3, 20)]
E         Right contains one more item: (3, 20)
E       assert [] == [(3, 20)]
E         Right contains one more item: (3, 20)
E       AssertionError: assert 'continue_reading' == 'after_completion'
E         - after_completion
E         + continue_reading
E       assert [19] == [2]
E         At index 0 diff: 19 != 2
E       AssertionError: assert (0 == 0 and 5 == 6)
E       assert 1 == 2
=========================== short test summary info ============================
FAILED tests/serving/test_after_completion.py::test_state_set_get_overwrite_forget
FAILED tests/serving/test_after_completion.py::test_nearline_completion_precomputes_neighbors_only
FAILED tests/serving/test_after_completion.py::test_compose_after_completion_row_first_content_channel
FAILED tests/serving/test_after_completion.py::test_compose_after_completion_dedup_wins_over_anchor
FAILED tests/serving/test_after_completion.py::test_http_completion_event_then_run_once_prepends_row
FAILED tests/serving/test_after_completion.py::test_http_stale_cache_not_served_after_completion
6 failed, 3 passed, 2 warnings in 0.29s
```

RED 시점 스텁: `after_completion.py` 4함수가 각각 `None`·`tuple(rows)`·`hit` 을 그대로 돌려주고, `compose_rows(after_completion=…)` 인자는 받되 무시. 통과한 3건은 기존 동작을 지키는 회귀 단정(`…default_none_keeps_five_rows` · `…without_neighbors_keeps_none` · `…nonpersonal_ignores_after_completion`)이라 RED 에서도 통과하는 것이 정상이다. 같은 시점 기존 테스트 회귀 `uv run pytest tests/serving/test_compose.py tests/serving/test_cascade.py tests/serving/test_state.py tests/serving/test_nearline.py tests/test_architecture.py --no-header` → `62 passed`.

### GREEN — 9 passed

```
9 passed, 2 warnings in 0.24s
```

### 회귀 포함 최종

명령: `uv run pytest tests/serving/test_after_completion.py tests/serving/test_compose.py tests/serving/test_cascade.py tests/serving/test_state.py tests/serving/test_nearline.py tests/test_architecture.py --no-header`

```
71 passed, 2 warnings in 0.78s
```

기존 테스트 파일의 단정은 한 줄도 고치지 않았다(추가도 없음 — 신규 단정은 전부 `tests/serving/test_after_completion.py`).

### REFACTOR / lint

`uv run ruff format` + `uv run ruff check` 를 이 플랜의 7파일에만 실행 → `7 files left unchanged` · `All checks passed!`. 디렉터리 전체 포맷은 wave 4 형제(05-11 `ratings_api.py` · 05-12 `dashboard_agg.py`)와 같은 작업 트리를 쓰므로 실행하지 않았다.

## TDD Gate Compliance

`type: tdd` 플랜이지만 `no_commit: true` 라 RED/GREEN 게이트 커밋(`test(...)` → `feat(...)`)이 존재하지 않는다. 게이트 증거는 위 pytest 출력으로 대체한다(플랜 frontmatter `tdd_gate_evidence: pytest-output`). RED 는 구현 전 실행해 6건 `AssertionError` 를 확인했고, 통과하지 말아야 할 테스트가 먼저 통과한 사례는 없다.

## 구현 요지

- **`after_completion.py`(신설)** — 아키 §9-3 파일 목록 밖의 신설이다(Advisor 승인 2026-09-06, PROGRESS 1줄은 Advisor 몫). 4개 함수뿐이다.
  - `precompute(store, user_key, book_id, neighbors)`: `neighbors.neighbors(book_id, AFTER_COMPLETION_N=20)` → `store.after_completion[user_key] = (book_id, ((b, w), …))`. 같은 키 재대입이라 새 완독이 덮어쓴다.
  - `stored(store, user_key)`: 요청 경로 읽기, `store` 가 없으면(스켈레톤 기동) `None`.
  - `prepend_after(rows, pair, catalog, seeds)`: `rows.neighbor_row` 를 그대로 써서 `row_id="after_completion"` · `purpose="discover"` · items `source="content"` · `source_channels=("content",)` · `channel_mix={"content": n}` · `reason` = 행 제목. 자격 있는 이웃이 없으면 기존 행을 그대로 돌려준다.
  - `fresh_cache(hit, store, cache, user_key)`: 완독 기록이 있는데 캐시된 rows 에 `after_completion` 행이 없으면 `Level1Cache.invalidate(user_key)` 후 `None`(미스).
- **`state.py`** — `StateStore.after_completion` 을 dict 속성으로 두고(쓰는 스레드는 Nearline 하나, dict 한 칸 교체는 GIL 아래 원자적) `forget` 이 함께 지운다. `DELETE /api/users/{key}/personalization` 은 이미 `state.forget` 을 부르므로(`serving/privacy_api.py:144`) 추가 배선이 없다.
- **`nearline.py`** — `_apply_rows` 의 기존 행 단위 `try` 안에서 `event_type == COMPLETION and book_id is not None and self.neighbors is not None` 일 때만 `precompute`. 이웃 조회가 실패해도 그 행만 로그하고 루프는 계속된다.
- **`compose.py`** — `ROW_ORDER` 맨 앞에 `"after_completion"`, `compose_rows(..., after_completion=None)` 기본값. level 0·1 분기에서만 `prepend_after` 를 호출하므로 level 2·3 은 인자를 줘도 비개인화 2행 그대로다. dedup 은 기존 `dedup_rows` 가 렌더 순서 앞 행 우선이라, 맨 앞에 붙는 것만으로 앵커·서가보다 우선한다.
- **`cascade.py`** — `_personal` 이 `after_completion=stored(store, r.user_key)` 를 넘기고, `_degrade` 가 `fresh_cache(...)` 로 감싼 캐시를 읽는다.

## Advisor 확정 이동 내역 (2026-09-06)

Advisor 확정 5에 따라 `cascade.py` 가 150줄을 넘지 않도록 아래를 `serving/levels.py` 로 **이동**했다. 동작·시그니처 무변경, `cascade.__all__` 재-export 유지.

| 이동 대상 | 이전 | 이후 |
|---|---|---|
| `CELL_VARIANT` | `cascade.py:37` | `levels.py` 상단 상수 |
| `PIPE_K_MIN` | `cascade.py:38` | `levels.py` 상단 상수 |
| `variant_for(cell, model, pipelines, default)` | `cascade.py:42` | `levels.py` |

부수 변화: `cascade.py` 는 `contracts.Pipeline` 과 `serving.rows.ROW_SIZE` 를 더 이상 import 하지 않고, `levels.py` 가 대신 import 한다. `tests/serving/test_cascade.py` 는 계속 `from millie_rec.serving.cascade import CELL_VARIANT, PIPE_K_MIN` 로 import 하며 수정하지 않았다.

## 계획과 달라진 점

1. **[Advisor 확정 1·2] 로직 배치** — 플랜 frontmatter 는 `state.py` 에 `set_after_completion`/`after_completion` 메서드, `nearline.py` 에 `AFTER_COMPLETION_N` 을 두라고 적었으나 두 파일 모두 여유가 2줄뿐이었다. Advisor 확정에 따라 신설 `after_completion.py` 로 옮겼다. 결과적으로 플랜의 `key_links` 패턴 `self.neighbors.neighbors\(` 는 `nearline.py` 가 아니라 `after_completion.py:precompute` 에 있다(`nearline.py` 는 `precompute(self.store, user_key, book_id, self.neighbors)` 1줄). "이웃은 `contracts.Neighbors` Protocol 로만" 이라는 규칙은 그대로 지켜진다 — serving 은 retrieval 을 import 하지 않는다.
2. **[Rule 1 - 계획 단정 오류] "완독 책 9 가 어느 행에도 없다"는 성립하지 않는다** — 플랜 behavior 의 `9 not in` 어느 행 items 단정은 현재 Must 행 구성에서 거짓이다. 실측(20권 표본, 완독 9): `after_completion [10,11,12,13,14]` · `continue_reading []` · `anchor_1 [6]` · `persona_shelf [17,16,15,8,7]` · `trending [9]` · `fresh_picks []`. `trending` 은 `catalog.popular()` 결과라 사용자의 완독 책을 거르지 않는다(wave 1 `rows.personal_rows` 의 기존 동작, 이 플랜 범위 밖). 단정을 "완독 책은 `after_completion`·`persona_shelf` 에 없다"로 좁혔고, 행 구성은 건드리지 않았다. 완독 책을 인기 행에서도 빼려면 `rows.py` 의 Must 행 규칙을 바꿔야 하므로 Advisor 판단 사항으로 넘긴다.
3. **[Advisor 확정 6] 캐시 무효화 방식** — 플랜 objective 는 "`_degrade` 1줄로 캐시 미스 취급"을 제안했고 Advisor 확정 6 은 `Level1Cache.invalidate(user_key)` 를 요구했다. `fresh_cache` 가 둘 다 한다(무효화 후 미스). Nearline 은 캐시 핸들이 없고 `api.py` 는 이 플랜의 쓰기 영역이 아니므로 요청 경로에서 판정한다.
4. **`compose.py` 인자 이름 충돌 없음** — `StateStore.after_completion` 은 dict 속성이라 플랜이 적은 메서드 호출(`store.after_completion(user_key)`)이 아니라 `stored(store, user_key)` 헬퍼로 읽는다.

## Known Stubs

없음. `after_completion.py` 의 4함수 모두 실제 동작하며, 하드코딩된 빈 값·placeholder 문자열이 남아 있지 않다.

## Threat Flags

플랜 `<threat_model>` 밖의 새 보안 표면 없음. 새 엔드포인트·인증 경로·파일 접근·스키마 변경이 없다. 등록된 처분은 그대로 이행:

| Threat ID | 처분 | 구현 |
|---|---|---|
| T-05-10-01 (completion 폭주) | accept | 이웃 조회는 메모리 dict 20건, Nearline 스레드에서만 |
| T-05-10-02 (자격 없는 seed) | mitigate | `rows.neighbor_row` 가 `catalog.eligible` 로 이웃을 거르고 seed 를 뺀다. 제목은 `title_of` 가 meta 없으면 book_id 문자열 |
| T-05-10-03 (옛 캐시 노출) | mitigate | `fresh_cache` + 테스트 `test_http_stale_cache_not_served_after_completion` |

## PROGRESS 1줄 후보 (Advisor 기록용)

- `serving/after_completion.py` 신설 — 아키 §9-3 파일 목록 외. `state.py` 150줄·`nearline.py`·`compose.py`·`cascade.py` 한도 유지를 위해 완독 행 로직(사전 계산·행 생성·캐시 정합)을 한 파일로 모았다(Advisor 승인 2026-09-06, 플랜 05-10). 같은 이유로 `variant_for`·`CELL_VARIANT`·`PIPE_K_MIN` 을 `cascade.py` → `levels.py` 로 이동(재-export 유지).

## PDF 문장 후보 (report/draft.md)

- 축③ 추천 구조 — "완독 이벤트는 요청 경로에서 처리되지 않는다. `POST /api/events` 는 적재만 하고, Nearline 루프가 그 책의 이웃 20건을 미리 계산해 두었다가 다음 응답의 첫 줄을 『X』을 완독하셨네요, 다음은 으로 바꾼다. Offline/Nearline/Online 경계가 문장이 아니라 코드로 존재한다는 증거." — 수용 기준 '완독 → 완독하셨네요 row(Should)'(../.assets/PRD/PRD_메인_추천_시스템.md §9 수용 기준 표) 충족.

## Advisor 보고

- **완료** — SERV-11 구현·테스트 9건·회귀 71 passed·ruff 클린. `src/` 7파일 전부 ≤150.
- **판단 필요 1** — 위 "계획과 달라진 점" 2번: 완독 책이 `trending` 행에 남는다. Must 행 규칙 변경이라 이번 플랜에서 손대지 않았다. Phase 6 '데모 재구성'(.planning/ROADMAP.md) 의 뷰어 완독 시연에서 "방금 완독한 책이 인기 행에 그대로 보인다"가 어색하면 별도 결정이 필요하다.
- **판단 필요 2** — PROGRESS 1줄(위 후보)과 개발일지 항목은 Advisor 몫이다. `after_completion.py` 신설 + `variant_for` 이동 2건.
- **미실행(지시대로)** — `make smoke` · `make serve` · `make bench` · 전역 `uv run pytest` · `ruff format .`. wave 4 종료 후 Advisor 게이트에서 1회 실행한다. `after_completion` 행이 level 0 응답에 1행(이웃 조회 1회 + `catalog.meta` 조인 1회)을 더하므로 bench p95 재측정 시 소폭 증가가 예상된다 — PDF 숫자는 05-09 게이트 값 유지가 플랜 지침.
- **형제 플랜 간섭 없음** — `serving/ratings_api.py`(05-11) · `serving/dashboard_agg.py`(05-12) 파일이 작업 중 생성됐으나 이 플랜의 테스트 실행은 한 번도 ImportError 로 실패하지 않았다.

## Self-Check: PASSED

- 파일 존재: `src/millie_rec/serving/after_completion.py` FOUND · `tests/serving/test_after_completion.py` FOUND · 수정 5파일 FOUND
- 커밋: 없음(의도) — `git log --oneline -1` 이 플랜 시작 시점 `8e5172b` 그대로
- 테스트: 71 passed · ruff `All checks passed!` · `wc -l` src 전부 ≤150
