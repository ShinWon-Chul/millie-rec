---
phase: 06-demo-rebuild
plan: 08
wave: 5
gap_closure: true
source: 06-UAT.md Gap 1
subsystem: serving-contract + demo
tags: [pydantic, fastapi, vanilla-js, mock-generator, tdd]

requires:
  - phase: 06-demo-rebuild
    provides: 재구축된 demo 8화면 · make_mock 생성기 · 계약 mock 10종
provides:
  - LibraryBook·ShowcaseBook 의 authors optional 필드
  - privacy_api 가 카탈로그 저자를 서재 카드에 실어 보낸다
  - 서재(#/library)·쇼케이스(#/) 화면의 실제 저자 표시
affects: [07-deploy, 08-pdf]

tech-stack:
  added: []
  patterns:
    - "계약 freeze 예외 = 기본값 있는 optional 추가 1개씩, 기존 필드 무변경"
    - "저자 정본은 응답 필드, 화면 조회는 폴백일 뿐"

key-files:
  created: []
  modified:
    - src/millie_rec/serving/schemas.py
    - src/millie_rec/serving/schemas_should.py
    - src/millie_rec/serving/privacy_api.py
    - demo/scripts/make_mock.py
    - demo/js/mock.js
    - demo/js/screens/d5_library.js
    - demo/js/screens/d8_showcase.js
    - demo/mock/showcase.json
    - demo/mock/state.json
    - tests/serving/test_privacy_api.py
    - tests/demo/test_make_mock.py

key-decisions:
  - "쇼케이스 `.case__author` 는 저자를 보이고 authors 가 null 일 때만 `book_id N` 으로 떨어진다 — 동명 도서 구분(06-CONTEXT.md 결정 D-07b ③)의 원래 의도가 저자 병기였다"
  - "서재 타일은 응답의 `LibraryBook.authors` 를 먼저 쓰고, 없을 때만 기존 추천행 조회로 떨어진다 — 시드 5권은 dedup exclude 라 추천행에 없다"
  - "라우팅·dedup 은 계속 `book_id` 로만 한다 — 저자·제목으로 동일성 판단하지 않는다"

requirements-completed: [DEMO-07, DEMO-06]

duration: ~25min
completed: 2026-09-06
---

# Phase 6 '데모 재구축' Plan 08: 서재·쇼케이스 저자 표시 Summary

**`LibraryBook`·`ShowcaseBook` 에 `authors` optional 을 1개씩 더하고 `privacy_api.BOOK_KEYS`
한 단어를 늘려, 서재 담은 책 5권과 쇼케이스 본인 5권에서 "저자 미상"·"book_id N" 을 지웠다.**

## Performance

- **Duration:** 약 25분
- **Completed:** 2026-09-06
- **Tasks:** 3/3 (TDD 2건 — RED/GREEN 커밋 각 1쌍)
- **Files modified:** 11 (계약 2 · 서버 1 · 생성기 1 · 화면 3 · mock 산출물 2 + manifest · 테스트 2)

## 무엇을 했나

### Task 1 — 계약 2줄 + 서버 1단어 (TDD)

RED `aa73286`: `tests/serving/test_privacy_api.py` 의 가짜 카탈로그 `_Cat.meta` 에
`"authors": f"저자{b}"` 를 더하고, `GET /api/users/{key}/state` 의 `library.added` 가 그 저자를
그대로 싣는다는 테스트를 추가했다. 카탈로그 미주입 시 `authors is None` 도 같은 테스트 안에서
단정한다. Red 는 의도한 `AssertionError`:

```
E       AssertionError: assert [None, None, None] == ['저자3', '저자2', '저자1']
```

GREEN `c0dc39a`: `schemas.LibraryBook`·`schemas_should.ShowcaseBook` 에
`authors: str | None = None` 을 `title` 다음 줄에 각 1개, `privacy_api.py` 의
`BOOK_KEYS = ("title", "image_url")` → `("title", "authors", "image_url")`. 서버 로직은
한 줄도 바꾸지 않았다 — 80행 `cards` 가 `m.get(b, {}).get(k)` 로 키를 훑고,
`CatalogKR.meta()` 가 `books_kr.json` 원소를 통째로 돌려주므로 저자가 이미 그 안에 있었다.

### Task 2 — 생성기 + mock 재생성 (TDD)

RED `7ad056e`: `showcase.json` 의 `personal_case.seeds`·`recommendations` 와 `state.json` 의
library 전 버킷이 비어 있지 않은 `authors` 를 갖는다는 테스트. Red 는 `AssertionError: 1 / assert None`.

GREEN `ccef4e3`: `make_mock.py` 의 `personal_case()` 두 dict 와 `user_state()` 의 library 카드에
`authors` 를 채우고 `uv run python demo/scripts/make_mock.py` 로 재생성했다
(`make mock`·`make millie` 는 실행하지 않았다 — 카탈로그 Day 3 freeze).
변경된 산출물은 `showcase.json`·`state.json` 둘뿐이고 나머지 11개 파일은 바이트 동일하다.

### Task 3 — 화면 2개 + mock 어댑터 `88910ca`

- `mock.js` `getUserState()` 의 `card()` 에 `authors: byId(b)?.authors ?? null`.
- `d5_library.js` `authorOf(state, book)` — 인자를 `bookId` 에서 카드 객체로 바꾸고
  `book.authors` 를 먼저 본다. 없으면 기존 `state.recommend.rows` 조회, 그다음 `"저자 미상"`.
- `d8_showcase.js` `.case__author` — `${b.authors ? esc(b.authors) : \`book_id ${esc(b.book_id)}\`}`.

## 검증

| 항목 | 결과 |
|---|---|
| `uv run pytest --no-header` | **534 passed**, failed 0 (직전 529 + 새 테스트 2, 나머지는 Phase 7 세션 추가분) |
| `uv run ruff check demo/scripts tests/demo src/millie_rec/serving tests/serving` | All checks passed! |
| mock 10 + `fallback/popular.json` `model_validate` | **11/11** 통과, 여분 키 0 |
| 생성기 결정성 재실행 | `_manifest.json` 외 전 파일 sha 동일 |
| 로컬 스모크 (`/health` · `/` · `/api/recommend`) | **PASS** 3줄 |
| 실서버 확인 (`POST /api/preferences` → `GET /api/users/{key}/state`) | `library.added` 에 `"authors": "헤르만 헤세 / 전영애 옮김"` 등 실제 저자 |
| 화면 렌더 확인 (Node 로 `d5_library.render`·`d8_showcase.render` 직접 호출) | 서재 5칸·쇼케이스 15칸 전부 실제 저자, `저자 미상` 0 · `book_id N` 0 |
| 폴백 3분기 | authors 없음+추천행 있음 → 추천행 저자 / 추천행 없음 → `저자 미상` / 쇼케이스 → `book_id 77` |
| 구 형태 grep (`demo/` 전체) | 0건 |
| 줄 수 상한 | demo JS/CSS 250 초과 0 (`mock.js` 250) · `privacy_api.py` 150 · `schemas_should.py` 102 |
| `node --check` 3파일 | 통과 |

**클릭 완주는 하지 않았다.** `.claude/rules/demo.md` 가 Worker 의 브라우저 자동화를 금지하므로
`make demo-serve` → `?source=mock` 육안 확인은 Advisor 몫으로 남는다. 대신 그 화면을 만드는
`render()` 를 재생성된 실제 mock 으로 Node 에서 직접 호출해 출력 HTML 을 단정했다(위 표).

## 계약 변경 diff (전체)

```
+    authors: str | None = None      # schemas.LibraryBook
+    authors: str | None = None      # schemas_should.ShowcaseBook
-SNAP_KEYS, BOOK_KEYS = (...), ("title", "image_url")
+SNAP_KEYS, BOOK_KEYS = (...), ("title", "authors", "image_url")
```

기존 필드의 이름·순서·타입 변경 0, 삭제 0. `.claude/rules/architecture.md` "필드 추가는 기본값
있는 optional 로만" 을 지킨다. 승인 근거는 `06-UAT.md` 테스트 2번 사용자 응답(2026-09-06).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] RED 테스트 안의 비교 대상 오타**
- **Found during:** Task 1 GREEN 직후
- **Issue:** 모델 단정 줄이 dict 리스트 `added` 를 돌면서 `.book_id` 속성에 접근해
  `AttributeError` 가 났다. RED 에서는 앞 단정이 먼저 실패해 가려져 있었다.
- **Fix:** `lib = out.library["added"]` 로 받아 같은 리스트를 양쪽에 쓴다.
- **Files modified:** `tests/serving/test_privacy_api.py`
- **Commit:** `c0dc39a`

계획 대비 그 외 이탈 없음. 계획이 예고한 `state.json` library 카드 보강도 예고대로 필요했다.

## 동시 세션 주의

Phase 7 '배포' 세션이 같은 워킹 트리에서 `pyproject.toml`·`uv.lock`·`src/millie_rec/app/server.py`·
`tests/app/test_sentry.py` 를 동시에 고치고 있었다. 이 플랜의 커밋 5건은 pathspec 을 못박아
그 파일들을 한 번도 스테이징하지 않았다. `make smoke` 는 8010 포트를 그 세션이 점유하고 있어
8031 로 따로 띄워 확인했고, 그 세션의 프로세스는 건드리지 않았다.

로컬 개발 DB(`data/local/millie.db`, 미추적)에 실서버 확인용으로 만든 사용자
`uat-authors-65560` 는 확인 뒤 5테이블에서 삭제했다.

## Advisor 제안

- `demo/js/mock.js` 가 정확히 **250줄**이 됐다(`.claude/rules/demo.md` 상한과 동일).
  다음에 이 파일에 한 줄이라도 더 들어가면 상한을 넘는다. 분할 대상 후보는
  `getUserState`·`getUserData`·`deletePersonalization` 세 얇은 위임 함수다.
  이번 플랜의 최소 변경 범위 밖이라 손대지 않았다.
- `d5_library.js` 의 추천행 폴백은 이제 죽은 경로에 가깝다(응답이 저자를 항상 싣는다).
  다만 API 모드에서 카탈로그가 없을 때를 위해 남겨 뒀다. 정리하려면 별도 결정이 필요하다.

## Known Stubs

없음.

## Threat Flags

없음. 새 네트워크 표면·인증 경로·파일 접근·스키마 경계 변경 없음. 추가한 `authors` 는 밀리 공개
페이지의 저자 표기로, 이미 메인·상세·뷰어 화면이 `ItemOut.authors` 로 노출하던 값과 같다
(리뷰 텍스트·필명 등 미저장 대상 아님).

## Commits

| # | Hash | Message |
|---|---|---|
| 1 | `aa73286` | test(06-08): LibraryBook.authors 실패 테스트 — 카탈로그 저자 전달·미주입 시 None |
| 2 | `c0dc39a` | feat(06-08): LibraryBook·ShowcaseBook 에 authors optional 추가 |
| 3 | `7ad056e` | test(06-08): 쇼케이스 본인 5권·서재 카드에 authors 가 실린다는 실패 테스트 |
| 4 | `ccef4e3` | feat(06-08): 생성기가 쇼케이스·서재 카드에 authors 를 싣는다 |
| 5 | `88910ca` | feat(06-08): 서재·쇼케이스 화면이 응답의 authors 를 보여준다 |

## TDD Gate Compliance

Task 1 · Task 2 모두 `test(...)` → `feat(...)` 순서로 커밋됐고 두 RED 모두 `AssertionError`
(collection error·ImportError 아님)로 확인했다. REFACTOR 커밋은 없다 — 정리할 것이 없었다.

## Self-Check: PASSED

11개 수정 파일 + SUMMARY 전부 존재, 커밋 5건 전부 `git log` 에서 확인.
