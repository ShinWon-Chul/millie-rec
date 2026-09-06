---
phase: 07-deploy
reviewed: 2026-09-06T07:43:05Z
depth: standard
files_reviewed: 9
files_reviewed_list:
  - src/millie_rec/app/server.py
  - src/millie_rec/serving/ratings_api.py
  - tests/app/test_sentry.py
  - tests/serving/test_ratings.py
  - demo/js/presets.js
  - demo/js/actions.js
  - demo/js/screens/d8_showcase.js
  - Dockerfile
  - .dockerignore
findings:
  critical: 0
  warning: 1
  info: 6
  total: 7
status: issues_found
---

# Phase 7 '배포'(.planning/ROADMAP.md): Code Review Report

**Reviewed:** 2026-09-06T07:43:05Z
**Depth:** standard
**Files Reviewed:** 9
**Status:** issues_found

## Summary

Phase 7 '배포'의 변경 4묶음 — Sentry fail-open 초기화(`app/server.py`), 철회 유저 별점 403(`serving/ratings_api.py`), 쇼케이스 "신규 유저로 체험하기" 초기화(`demo/js/presets.js`·`actions.js`·`d8_showcase.js`), `results/latency.json` 이미지 포함(`Dockerfile`·`.dockerignore`) — 을 diff(`20d5fa3..HEAD`) 기준으로 읽고 교차 확인했다.

확인한 사실:
- `uv run ruff check`·`ruff format --check` 통과, `tests/app/test_sentry.py` + `tests/serving/test_ratings.py` + `tests/test_architecture.py` 16 passed.
- 파일 길이: `server.py` 62줄(테스트 상한 65) · `ratings_api.py` 84줄 · demo JS 3개 모두 ≤250줄.
- star 의존: `ratings_api.py`의 신규 import는 `millie_rec.serving.events_gate`(같은 슬라이스) — 위반 없음.
- `results/latency.json`은 git 추적 중(`git ls-files` 확인), `.dockerignore`의 `results/*` + `!results/latency.json` 부정 패턴은 유효. Railway 빌드(`railway.json` DOCKERFILE 빌더)에서 COPY가 실패할 조건은 없다.
- `demo/assets/brand/millie-mark.png` 존재·추적 중. 해시 라우팅이라 상대 경로 `assets/brand/...`는 항상 `/`에서 해석된다.
- Sentry: `sentry-sdk 2.68.1`(lock) — `is_initialized()`·`max_request_body_size="never"` 모두 유효한 API. spy가 `sentry_sdk.init`을 교체하므로 테스트에서 실제 초기화·네트워크 없음.
- 403은 `with con:` 블록 안에서 raise되어 sqlite3 컨텍스트 매니저가 롤백하며, 그 시점에 INSERT는 없으므로 부작용 0. `inserted`는 예외 경로에서 참조되지 않는다.

Critical 없음. Warning 1건은 서버의 신규 403 응답을 데모 클라이언트가 소비하지 않아 철회 유저에게 성공 토스트가 뜨는 흐름이다. 나머지는 주석·이름 정확성과 선택적 견고성 제안이다.

의도적 사항(재지적 안 함): Dockerfile `USER` 미지정(Railway 볼륨 root 소유), `python:3.11-slim`·`uv:latest` 가변 태그(07-01 F3 수용), `/health`가 `db_ok=false`에도 200(walking skeleton 결정), `Makefile`·`results/`·`scripts/`·`tests/data/` 미커밋 변경(다른 세션).

## Warnings

### WR-01: 별점 403이 데모에서 성공으로 표시된다

**File:** `demo/js/actions.js:170-185` (원인 변경: `src/millie_rec/serving/ratings_api.py:73-74`)
**Issue:** `ratings_api.py`가 철회 유저(`consent=0`)에게 403을 새로 반환하지만, 데모의 `rate` 액션은 `api.postRating` 반환값을 보지 않는다. `demo/js/api.js:45`의 `soft()`가 403을 `null`로 삼키므로 (1) `state.ratings[r.bookId] = stars`가 API 호출 전에 이미 기록되고, (2) `log("rating", ...)` 이벤트가 그대로 적재되고, (3) "다음 책을 준비하고 있어요" 토스트가 뜬다. 재현 경로: 내 서재 철회 → 메인(level 3 trending 행은 여전히 보임) → 상세 → 뷰어 → 완독 → 별점. 서버는 옳게 거부했는데 화면은 저장된 것처럼 보여 "삭제 응답이 거짓"이 되는 것을 막으려던 Codex C3의 취지가 UI에서 끊긴다. mock 경로(`demo/js/mock.js:228` `postRating`)도 consent 검사가 없어 api/mock 동작이 갈린다.
**Fix:**
```js
rate: async (el) => {
  const r = state.reading;
  const stars = Number(el.dataset.stars);
  if (!r) return;
  const res = await api.postRating(state.source, { /* 기존 body 그대로 */ });
  if (!res) {                       // 403(철회)·네트워크 실패 — soft() 가 null 로 준다
    state.modal = null;
    toast("별점을 저장하지 못했어요");
    location.hash = "#/home";
    return;
  }
  state.ratings[r.bookId] = stars;  // 성공 뒤에만 로컬 반영
  log("rating", { book_id: r.bookId, payload: { stars: String(stars) } });
  state.modal = null;
  toast("다음 책을 준비하고 있어요");
  location.hash = "#/home";
},
```
가능하면 `mock.postRating`에도 `store`의 consent 상태를 보고 `null`을 돌려주는 분기를 넣어 두 소스의 동작을 맞춘다(하드코딩 문구는 `demo/config/onboarding.json` 정본 규칙에 맞춰 배치).

## Info

### IN-01: `import sentry_sdk`가 fail-open `try` 바깥에 있다

**File:** `src/millie_rec/app/server.py:26`
**Issue:** 함수의 목표는 "관측 기능이 기동을 막지 않는다"(Codex F1)인데, `SENTRY_DSN`이 설정된 환경에서 `sentry_sdk`가 어떤 이유로든 import 불가하면(`ImportError`) `try` 밖이라 모듈 import가 죽는다. `pyproject.toml`에 하드 의존이어서 현재 위험은 낮다.
**Fix:** import를 `try` 안으로 옮기고 `except Exception`이 함께 덮게 한다. 줄 수 변화 없음(65 상한 유지).
```python
try:
    import sentry_sdk
    sentry_sdk.init(dsn=dsn, ...)
except Exception:
    ...
```

### IN-02: `max_request_body_size`는 본문만 막고 `query_string`은 그대로 전송된다

**File:** `tests/app/test_sentry.py:59-60`, `src/millie_rec/app/server.py:28`
**Issue:** 주석은 "PII off 만으로는 요청 본문·query_string 이 오류 이벤트에 실린다"고 문제를 적고 `max_request_body_size="never"`를 답으로 단언하는데, Sentry Starlette/ASGI 통합은 `request.query_string`을 PII 설정과 무관하게 항상 포함한다. `/api/recommend?user_key=...`의 가명 `user_key`가 실리는 것은 07-CONTEXT D-04의 "가명 user_key 외 미전송" 범위 안이라 결정 위반은 아니지만, 주석이 해결 범위를 과장한다.
**Fix:** 주석을 "본문 미수집(query_string 은 가명 키만 담기므로 허용)"으로 고치거나, query_string까지 막으려면 `before_send=lambda ev, hint: (ev.get("request", {}).pop("query_string", None), ev)[1]`를 추가하고 테스트에 단언을 더한다.

### IN-03: 테스트 이름 `under_50_lines`와 상한 상수 65 불일치

**File:** `tests/app/test_sentry.py:20`, `tests/app/test_sentry.py:64`
**Issue:** `MAX_SERVER_LINES = 65`로 바꾼 이유는 주석에 잘 남겼지만 함수 이름은 여전히 `test_server_module_stays_under_50_lines`다. 실패 메시지가 이름을 보여 주므로 나중에 읽는 사람이 다른 숫자를 본다.
**Fix:** `test_server_module_stays_thin_under_max_lines`처럼 숫자를 이름에서 빼거나 `_under_65_lines`로 맞춘다.

### IN-04: 파일 헤더 "고지 하드코딩 0"이 더 이상 참이 아니다

**File:** `demo/js/screens/d8_showcase.js:2`, `demo/js/screens/d8_showcase.js:47-49`, `demo/js/screens/d8_showcase.js:107`
**Issue:** 2행 주석은 "숫자·문장은 전부 state.showcase에서만 온다. 이 파일에 지표 값·철학·고지 하드코딩 0"이라고 선언하는데, 이번 변경으로 n=0 캡션 3문장(47-49행)과 로고 상표 고지(107행)가 JS 안에 리터럴로 들어갔다. 화면 텍스트 정본은 `demo/config/onboarding.json` 또는 `ShowcaseOut.data_notice`(서버)라는 프로젝트 규칙과도 어긋난다.
**Fix:** (a) 상표 고지는 `dashboard_api.py`의 `data_notice`(ShowcaseOut) 문장 끝에 붙여 서버가 내려 주게 하고, n=0 캡션은 `eval_table`에 `notice` 같은 optional 필드(기본값 있는 추가 = 계약 규칙 허용)로 내려 준다. 또는 (b) 최소 조치로 2행 주석을 "고지·캡션 2곳은 예외(정적 문구)"로 고친다.

### IN-05: `COPY results/latency.json`이 빌드를 하드 실패시킨다

**File:** `Dockerfile:11`
**Issue:** `serving/dashboard_api.py:84-90`은 파일이 없거나 손상이면 `log.exception` 후 p95를 `None`으로 우아하게 비우는데, Dockerfile은 파일 부재를 빌드 실패로 바꾼다. 현재 파일은 커밋되어 있어 문제 없지만, `make bench` 재실행 뒤 파일을 지우고 커밋하거나 `results/`를 정리하면 배포가 깨진다(런타임 폴백이 있는 파일에는 과한 강제).
**Fix:** 선택적 COPY 패턴으로 바꾸면 없을 때 빈 디렉터리만 만든다.
```dockerfile
COPY results/latency.jso[n] ./results/
```
(글로브가 0개 매치여도 COPY는 실패하지 않는다. 의도적으로 하드 실패를 원한다면 현행 유지하고 주석에 "없으면 빌드 실패 = 의도"를 한 줄 적는다.)

### IN-06: `startFresh`가 진행 중인 프리셋 비동기 흐름과 겹칠 수 있다

**File:** `demo/js/presets.js:26-29`, `demo/js/presets.js:107-117`
**Issue:** `presets.run`은 `await` 여러 개를 거치는데(`runOnboarding` → `requestRecommend`), 그 사이에 "신규 유저로 체험하기"를 누르면 `resetAll`이 같은 `state` 객체를 비운 뒤 진행 중이던 프리셋이 새 `userKey`로 스냅샷을 push하고 `#/home`으로 이동시킨다. 기존 프리셋 버튼 간 더블클릭에도 있던 패턴이라 신규 결함은 아니고, 심사자 데모에서 드물다.
**Fix:** 모듈 변수 `let running = false;`로 `run`·`startFresh` 진입을 막거나(`if (running) return;`), `resetAll`에서 세대 번호(`state.gen++`)를 올리고 `runOnboarding`이 `await` 뒤마다 세대가 바뀌었으면 중단한다. 5일 범위에서는 전자(3줄)로 충분하다.

---

_Reviewed: 2026-09-06T07:43:05Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
