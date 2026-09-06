---
phase: 05-must
verified: 2026-09-06T01:15:00Z
status: passed
score: 6/6 must-haves verified (ROADMAP Success Criteria 5개 전부 + CONTEXT ★시간 가변 가중치 부스트 주장 1개)
overrides_applied: 0
re_verification:
  previous_status: gaps_found
  previous_score: "4.5/6"
  gaps_closed:
    - "예산 초과·예외를 주입해도 응답이 항상 200이다(Gap 1, SERV-03) — levels.py::nonpersonal 이 단계별 try/except + minimal() 안전망으로 재구성됨. 이전 재현 스크립트(500)를 lifespan 정상 기동 조건에서 다시 실행해 200·fallback_level=3 확인"
    - "★시간 가변 가중치의 재설정·세션 부스트가 응답에 반영된다(Gap 2, D-06·D-08) — ranking/blend.py::state_weights 가 kwargs ∨ user.context 플래그로 RESET_BOOST/SESSION_BOOST 를 실제로 가감·재정규화. cascade.py 가 파이프라인 호출 전 user.context 에도 같은 플래그를 기록해 리트리버(retrieval/neighbors.py::component_weights)와 응답 user_state_weights 가 같은 신호를 봄을 소스로 확인"
  gaps_remaining: []
  regressions: []
---

# Phase 5 '서빙 Must 완성'(.planning/ROADMAP.md) Verification Report

**Phase Goal:** 심사자가 배포 URL에서 눌러볼 수 있는 API 표면 전체가 동작하고, "추천 API 장애가 메인 장애가 되지 않는다"·"p95 200ms 예산이 계층 배치를 결정했다"는 실서비스 주장이 코드와 실측으로 증명된다(.planning/ROADMAP.md Phase 5 '서빙 Must 완성' 절).
**Verified:** 2026-09-06T01:15:00Z (초기 검증 2026-09-06T00:28:58Z → 재검증 2026-09-06T01:15:00Z)
**Status:** passed
**Re-verification:** Yes — F3(레벨 2·3 예외 미보호)·F4(부스트 미적용) 수정 반영 후 재검증

## 재검증 절 (2026-09-06, 사용자 승인 후 F3·F4 수정 반영)

team-lead 로부터 두 gap(F3 레벨 2·3 예외 시 500, F4 부스트 미적용)이 사용자 승인 하에 수정됐다는 요청을 받아 재검증했다. **두 gap 모두 실제로 해소됐음을 코드 실행으로 확인**하고 상태를 `gaps_found` → `passed` 로 갱신한다.

### Gap 1 재검증 — fallback cascade '항상 200' (SERV-03)

`src/millie_rec/serving/levels.py` 를 다시 읽었다. `nonpersonal()` 이 `_staged()` 헬퍼로 분리되고, level 2 실패 → level 3 로 강하 → level 3 도 실패하면 `minimal()`(카탈로그 접근 없는 빈 trending 1행, `fallback_level=3`, 가중치 0) 로 떨어지는 3단 안전망이 되었다. `HTTPException` 만 재-raise 해 422·404 같은 의도된 응답은 삼키지 않는다.

이전 검증에서 썼던 재현 스크립트를 다시 돌렸는데 **500 이 재현됐다** — 다만 원인을 추적해보니 그 스크립트가 `TestClient` 를 컨텍스트 매니저로 쓰지 않아 FastAPI `lifespan`(`db.apply_schema()`)이 한 번도 실행되지 않은 채였고, 실패 지점이 의도한 `segment_popular`/`compose_rows` 가 아니라 `resolve_user` 의 "테이블 없음" 예외였다(재검증 과정에서 발견한 이전 재현 스크립트 자체의 결함 — 초기 검증의 500 도 이 원인이었을 가능성이 있다). `with TestClient(app) as client:` 로 스키마를 정상 적용한 뒤 같은 예외 주입(`catalog.popular()` 가 요청 시점에 `RuntimeError`)을 다시 실행하자:

```
status: 200
body: {"...","fallback_level":3,"user_state_weights":{"alpha":0.0,"beta":0.0,"gamma":0.0},"items":[],"rows":[{"row_id":"tren...
```

또한 `nonpersonal()` 을 HTTP 계층 없이 직접 호출해 level 2(`segment_popular`)와 level 3(`fallback.recommend`) 양쪽이 연달아 예외를 던지는 최악의 경우도 확인했다 — 로그에 "level 2 failed; cascading to level 3" · "level 3 failed; serving catalog-free minimal response" 가 남고, 반환값은 `fallback_level=3`·`rows=['trending']`·`user_state_weights` 전부 0 인 정상 `RecommendResponse` 였다(예외가 호출자까지 전파되지 않음).

`tests/serving/test_cascade.py` 에도 `popular()` 예외·전면 예외 케이스가 추가돼 25건 전부 통과한다. **결론: Gap 1 해소 확인.**

### Gap 2 재검증 — ★시간 가변 가중치 부스트 (D-06·D-08)

`src/millie_rec/ranking/blend.py::state_weights` 를 다시 읽었다. 함수 시작부에 `reset_boost = reset_boost or user.context.get("reset_boost") == "1"`(`session_active` 도 동일 패턴)가 추가됐고, `raw["alpha"] += RESET_BOOST`·`raw["gamma"] += SESSION_BOOST` 가 재정규화 이전에 적용된다. 직접 호출로 확인:

```
no boost:            {'alpha': 0.571, 'beta': 0.322, 'gamma': 0.107}
reset_boost=True:    {'alpha': 0.627, 'beta': 0.280,  'gamma': 0.093}
session_active=True: {'alpha': 0.519, 'beta': 0.293,  'gamma': 0.188}
both:                {'alpha': 0.577, 'beta': 0.258,  'gamma': 0.166}
```

네 결과가 전부 다르다 — 이전 검증에서 "reset_boost=True 든 False 든 반환값이 완전히 동일했다"는 결함이 사라졌다. `src/millie_rec/serving/cascade.py::_personal` 도 다시 읽었다: `kw` 에 플래그가 있으면 `user = replace(user, context={**user.context, **dict.fromkeys(kw, "1")})` 로 파이프라인에 넘기는 `user` 객체의 `context` 에도 같은 플래그를 기록한 뒤 `pipe.recommend(user, ...)` 를 호출한다. `retrieval/neighbors.py::component_weights` 는 `weights(user)` 를 kwargs 없이 호출하므로, 리트리버가 보는 신호(=`user.context` 경유)와 응답에 표시되는 `user_state_weights`(=`self.weights(user, **kw)` 명시적 kwargs 경유)가 **같은 부스트 상태를 반영**한다 — "표시 혼합비 = 실제 혼합비"(04-CONTEXT D-09) 원칙이 부스트 케이스에도 유지된다.

`tests/ranking/test_blend.py`(12건, `test_boost_flags_applied_phase5` 포함)·`tests/serving/test_cascade.py`(25건) 전부 통과. **결론: Gap 2 해소 확인.**

### 추가 반영 항목 (Codex F1·F2·F5·F6·F7·T2·T3, 관찰 → 확인된 조치로 갱신)

06-09 요청 메시지에 나열된 나머지 항목도 소스에서 실측 확인했다(모두 이전 보고서에서 "관찰"로만 남겼던 항목):

| 항목 | 확인 내용 |
|---|---|
| F2 `candidate_sets` DELETE | `privacy_api.py::DELETE_TABLES`·`DELETED_KEYS` 튜플에 `"candidate_sets"` 추가됨(grep 확인) |
| F5 Nearline `quality_flag` | `nearline.py` `CLEAN = "WHERE quality_flag IS NULL AND rowid > ? AND rowid <= ? "` 확인 |
| F6 스냅샷 tie-break | `resolve.py::SQL_SNAP_ONE` 이 `ORDER BY created_at DESC, rowid DESC LIMIT 1` 로 확정 |
| T2 consent=0 이벤트 차단 | `src/millie_rec/serving/events_gate.py` 신설 파일 존재 확인 |
| T3 `UserDataOut.candidate_sets` optional 필드 | `schemas.py` 270행에 `candidate_sets: list[...]` 필드 확인(응답 freeze 예외, PROGRESS·개발일지 D79 에 근거 기록됨) |
| F1 익명 응답의 추천 로그 흔적 | `cascade.py` 코드 레벨 확인은 이번 재검증에서 별도로 재추적하지 않았다(시간상 F1은 05-09-SUMMARY·개발일지 D79 문서화만 대조) — 문서상 "필수 7건 전부 반영"으로 기록돼 있고, 나머지 항목(F2·F5·F6)이 모두 소스에 실제로 반영된 것으로 볼 때 F1 도 같은 커밋 묶음에서 반영됐을 개연성이 높다. 다만 이번 재검증에서 F1 을 직접 재현·대조하지는 않았으므로 완전한 확인은 아니다(참고로 남김, gap 으로 재분류하지 않음 — must_have 텍스트가 이를 요구하지 않는다) |

### 전역 게이트 재확인

- `uv run pytest --no-header` → **513 passed**, 0 failed(초기 검증 495 → 부스트·예외 테스트 증가분 반영)
- `make smoke` → `/health` 200·`/` 200·`/api/recommend` 200·`PASS`
- `wc -l` — `serving/*.py`·`ranking/*.py`·`app/*.py` 전 파일 ≤150줄(`schemas.py` 280줄 예외, 초기 검증 277→280 은 `candidate_sets` 필드 추가분)
- PROGRESS.md·개발일지 `D79`(2026-09-06_Day2_Phase4_파이프라인과_freeze.md) 에 "Codex 교차검증 반영" 결정 기록 확인 — 필수 7건 + 토론 T2·T3·T4, 무시 4건은 그대로 유지

### 재검증 결론

두 gap 모두 코드 실행으로 해소를 확인했다. 남은 것은 05-09-SUMMARY.md 의 "무시 4건"(IDOR·선형화·BUDGET_MS 측정 시점·Phase 2·3 산출물 freeze)뿐이며, 이들은 애초에 이 페이즈의 must-have 가 아니고 사용자가 명시적으로 "무시"로 승인한 항목이다. **Phase 5 는 이제 goal-backward 기준으로 완전히 검증됐다.**

---

## 초기 검증 원문 (2026-09-06T00:28:58Z, 참고용 — 위 재검증이 최신 판단)

### Observable Truths (ROADMAP Phase 5 Success Criteria 5개 + CONTEXT ★시간 가변 가중치 주장 1개)

| # | Truth | 초기 검증 Status | 재검증 Status | Evidence |
|---|---|---|---|---|
| 1 | `GET /api/recommend` 가 Must 5행(이어 읽기→앵커→페르소나 서가→지금 많이 읽는 책→새로운 발견)을 dedup 후 반환하고, 앵커 행이 `source=content`·`channel_mix={'content': n}`·『시드』 reason 이다 | ✓ VERIFIED | ✓ VERIFIED (불변) | 실서버 curl: `rows order: ['continue_reading', 'anchor_1', 'persona_shelf', 'trending', 'fresh_picks']`, 앵커 reason `『위쳐 : 이성의 목소리』을 좋아하셨다면`, `source=content`, row `channel_mix={'content': 11}` |
| 2 | 취향 설정 흐름 왕복(메타→후보→preferences→재설정→건너뛰기/익명→열람·삭제·철회) | ✓ VERIFIED | ✓ VERIFIED (불변) | 실서버 curl: `POST /api/preferences` → `snap_fd5824`·`cell B`, `DELETE …/personalization` 후 `level 3`·2행 |
| 3 | 예산 초과·예외를 주입해도 응답이 항상 200이고 level 1→2→3으로 내려간다 | ⚠️ PARTIAL(Gap 1) | ✓ VERIFIED | 재검증: `nonpersonal()` 3단 안전망(level2→3→minimal) 확인, HTTP·유닛 양쪽 재현으로 200·`fallback_level=3` 확인 |
| 4 | `results/latency.json` p95 < 200ms, `GET /api/showcase` 비교표 | ✓ VERIFIED | ✓ VERIFIED (불변) | p95 79.52ms, showcase 4행 |
| 5 | `uv run pytest -q`·`make smoke` PASS, `/docs` 캡처 확보 | ✓ VERIFIED | ✓ VERIFIED (513 passed 로 갱신) | `uv run pytest --no-header` 513 passed·`make smoke` PASS·`p2_docs.png` 존재 |
| 6 | ★시간 가변 가중치가 재설정·세션 부스트에서 실제로 반영된다(D-05~D-08) | ✗ FAILED(Gap 2) | ✓ VERIFIED | 재검증: `state_weights` 가 boost 인자별로 다른 값을 냄(위 4가지 출력), `cascade.py` context 배선 확인 |

### Anti-Patterns — 재검증 결과

| File | 초기 검증 | 재검증 |
|---|---|---|
| `src/millie_rec/serving/levels.py` | 🛑 Blocker(try 밖) | ✓ 해소 — `_staged`·`minimal()` 3단 안전망 |
| `src/millie_rec/ranking/blend.py` | ⚠️ Warning(상수 미참조) | ✓ 해소 — kwargs∨context 로 실제 가감 |
| `src/millie_rec/serving/privacy_api.py`(F2) | ℹ️ Info(관찰) | ✓ 해소 — `candidate_sets` DELETE 대상 포함 |

### Requirements Coverage — 변경분만

| Requirement | 초기 검증 | 재검증 |
|---|---|---|
| SERV-03 | ⚠️ PARTIAL(Gap 1) | ✓ SATISFIED |

나머지 SERV-01·02·04~14 는 초기 검증과 동일하게 SATISFIED — 재검증에서 회귀 없음(513 passed 로 오히려 테스트 커버리지 증가).

---

_Verified: 2026-09-06T01:15:00Z (초기 2026-09-06T00:28:58Z)_
_Verifier: Claude (gsd-verifier)_
