---
phase: 01-local-serving-skeleton
plan: 02
subsystem: app(조립) + 로컬 기동 검증
tags: [uvicorn, staticfiles, walking-skeleton, smoke, composition-root]
requires:
  - "millie_rec.serving.create_app · Database · resolve_db_path · GlobalPopularFallback (Plan 01)"
  - "millie_rec.contracts.ROOT (기존)"
provides:
  - "millie_rec.app.server:app — uvicorn 진입점(Makefile serve·smoke, Dockerfile CMD 가 가리키는 이름)"
  - "GET / → demo/ 정적 데모 같은 origin 서빙(StaticFiles html=True, 마지막 마운트)"
  - "make smoke 3점 PASS — 이후 모든 페이즈의 공통 완료 기준 성립"
  - "data/local/millie.db 실기동 생성(7테이블·WAL·gitignore)"
affects:
  - "Phase 2 'Track A 정량 평가 기반' — server.py 의 pipelines={} 자리에 pipelines[\"pop\"] 주입"
  - "Phase 3 '밀리 카탈로그 빌드' — catalog=catalog_kr 주입 시 빈 trending 행이 채워진다"
  - "Phase 6 '데모 재구성' — demo/api.js 가 같은 origin 을 가리키게 되면 fallback 배너 소멸"
  - "Phase 7 '배포' — Dockerfile 이 editable 설치를 유지해야 contracts.ROOT/'demo' 가 유효(CONTEXT deferred 아키텍트 리뷰 I-2)"
tech-stack:
  added: []   # 의존성 추가 0
  patterns:
    - "composition root 1파일 — create_app 호출 + StaticFiles 마운트만, 비즈니스 규칙 0"
    - "StaticFiles 마운트를 라우트 등록 뒤 마지막에 두어 /health·/docs·/api 를 가리지 않음"
    - "테스트에서 monkeypatch.setenv(DATA_DIR, tmp_path) + sys.modules.pop 후 importlib 로 모듈 재import"
key-files:
  created:
    - src/millie_rec/app/server.py
  modified:
    - tests/serving/test_smoke.py
decisions:
  - "D-11 CORS 미들웨어 없음 — 같은 origin 단일 컨테이너가 설계 자체(아키텍처 01 §9-3)"
  - "D-13 실제 data/local/millie.db 는 테스트가 건드리지 않는다 — DATA_DIR 를 tmp_path 로 돌린 뒤 import"
  - "아키텍트 리뷰 W-3 — /docs 200 단정을 테스트에 포함(PDF P2 캡처 대상이 StaticFiles 에 가리면 안 됨)"
metrics:
  tasks: 2
  files-created: 1
  files-modified: 1
  tests-added: 1
  suite: "104 passed, 2 skipped"
  completed: 2026-09-05
---

# Phase 1 '로컬 서빙 스켈레톤' Plan 02: 조립(app/server.py) · make smoke 3점 · Phase 종료 감사 Summary

**한 줄:** `uvicorn millie_rec.app.server:app` 이 아티팩트·DB·네트워크 없이 실제 프로세스로 떠서 `/health` 200(`model_version:null`·`db_ok:true`)·`/`(demo 정적)·`/api/recommend` 200(level 3 `trending` 1행)을 같은 origin 에서 내고, `make smoke` 가 그 3점을 확인해 `smoke: PASS` 를 출력한다 — 12줄짜리 조립 파일 하나로.

## Task 1 — `app/server.py` 조립 + 테스트 1건

`src/millie_rec/app/server.py` **12줄** (플랜 1-a 원문 그대로, 예산 ≤30):

```python
"""uvicorn 진입점: create_app 주입 + demo/ StaticFiles(마지막). CORS 없음(아키텍처 01 §9-3)."""

from fastapi.staticfiles import StaticFiles

from millie_rec.contracts import ROOT
from millie_rec.serving import Database, GlobalPopularFallback, create_app, resolve_db_path

# Phase 2 → pipelines["pop"], Phase 3 → catalog, Phase 5 → neighbors·book_stats·state.
# 이 호출의 인자만 채운다 — 시그니처 불변(CONTEXT D-09).
app = create_app(pipelines={}, fallback=GlobalPopularFallback(None), db=Database(resolve_db_path()))
# 반드시 마지막 — 앞에 두면 /health·/api/* 가 StaticFiles 에 가려진다
app.mount("/", StaticFiles(directory=ROOT / "demo", html=True), name="demo")
```

경계 확인(실측):
- `grep -c "millie_rec\.serving\." src/millie_rec/app/server.py` = **0** (3단 경로 없음 — `app` 은 공개 표면 2단만, `tests/test_architecture.py` L41-42)
- `grep -c "CORSMiddleware\|os\.environ\|@app\." src/millie_rec/app/server.py` = **0** (미들웨어·환경변수 해석·라우트 추가 0 — 경로 해석은 `serving/db.py` 의 `resolve_db_path()` 만)
- `app = create_app(...)`(L10) 이 `app.mount("/", …)`(L12) 보다 **앞** — 마운트가 마지막

`tests/serving/test_smoke.py` 에 1건 추가(기존 10건·fixture·import 불변, stdlib 그룹에 `import importlib`·`import sys` 추가):

```python
def test_server_module_serves_demo_index_and_keeps_api_routes(tmp_path: Path, monkeypatch):
    """app.server:app — StaticFiles 마운트가 마지막: / 는 demo, /health·/docs·/api 는 유지."""
    monkeypatch.setenv(ENV_DATA_DIR, str(tmp_path))   # 실제 data/local/millie.db 미접촉(D-13)
    sys.modules.pop("millie_rec.app.server", None)
    server = importlib.import_module("millie_rec.app.server")
    with TestClient(server.app) as c:
        root = c.get("/"); assert root.status_code == 200 and "<html" in root.text.lower()
        assert c.get("/health").status_code == 200
        assert c.get("/docs").status_code == 200      # PDF P2 캡처 대상(W-3)
        rec = c.get("/api/recommend", params={"seeds": "1,2,3", "k": 5})
    assert rec.status_code == 200 and rec.json()["fallback_level"] == FALLBACK_GLOBAL_POP
    assert (tmp_path / DB_FILENAME).exists()
```

결과: `uv run pytest tests/serving/test_smoke.py --no-header` → **11 passed**, `uv run pytest tests/test_architecture.py --no-header` → **3 passed**, `uv run ruff check src tests` → `All checks passed!`. 테스트 실행만으로는 `data/local/` 이 생성되지 않음(확인: 이 시점에 `data/local 없음`).

### TDD 표기

플랜 frontmatter 는 `type: execute`, Task 1 은 `tdd="true"` 지만 `../.claude/rules/python-tdd.md` "적용 범위" 표가 **`app/` 조립은 "Advisor 직접. 아키텍처 테스트 + 계약 테스트로 대체"** 로 규정한다. `app/server.py` 가 없는 상태에서 새 테스트를 먼저 돌리면 `ModuleNotFoundError` 이고 그것은 같은 규칙이 **"Red 가 아니다"** 로 명시한 오류라, Plan 01 처럼 스텁을 세우는 것은 12줄 조립 파일에 대해 최소 변경 원칙을 넘는다. 따라서 플랜 action 순서(1-a 코드 → 1-b 테스트)를 그대로 따랐고, 마운트 순서의 회귀 방어는 추가된 단정(`/health`·`/docs`·`/api/recommend` 200)이 담당한다.

## Task 2 — 실측·감사

### `make smoke` (8010 포트, exit 0)

포트 선점 없음 확인 후 1회 실행, 재시도 없음:

```
smoke: /health 200
smoke: / (demo static) 200
smoke: /api/recommend 200
smoke: PASS
```

종료 후 `lsof -iTCP:8010 -sTCP:LISTEN` 빈 출력, `.uvicorn.pid` 없음.

### 전체 스위트

```
104 passed, 2 skipped, 2 warnings in 1.31s
```

기준선 93(HEAD `8e5172b`) + Plan 01 의 10 + Plan 02 의 1 = 104. failed 0. `uv run ruff format --check src tests` → `22 files already formatted`, `uv run ruff check src tests` → `All checks passed!`.

### 실응답 (포트 8011, 축약 — PDF 숫자 아님)

`DATA_DIR` unset → 기본 경로 `data/local/millie.db`.

`GET /health`:
```json
{"status":"ok","api_version":"v2","model_version":null,"artifacts_loaded_at":null,"db_ok":true,
 "db_row_count":{"book_stats":0,"candidate_sets":0,"events":0,"preference_snapshots":0,"ratings":0,"recommendations":0,"users":0},
 "nearline_last_run":null,"uptime_s":3.754…}
```

`GET /api/recommend?seeds=1,2,3&k=5`:
```json
{"recommendation_id":"rec_6a9447","model_version":"fallback_v1","preference_snapshot_id":null,"user_key":null,"cell":null,
 "forced":false,"fallback_level":3,"context":null,"latency_ms":0.0078…,"latency_breakdown":{"total":0.0078…},
 "user_state_weights":{"alpha":0.0,"beta":0.0,"gamma":0.0},"dedup_removed":0,"nearline_lag_s":null,
 "items":[],"rows":[{"row_id":"trending","title":"지금 많이 읽는 책","purpose":"fallback","items":[],"subtitle":null,"channel_mix":{}}]}
```

CONTEXT `<specifics>` 기대 예시와 필드 집합 일치(`latency_ms`·`uptime_s`·`recommendation_id` 값만 다름 — 참고값). 서버 종료 후 8010·8011 모두 빈 출력, `pgrep -fl "uvicorn millie_rec"` 없음.

### SKEL-04 실기동 증거 — `data/local/millie.db`

```
data/local/millie.db          4096 B
data/local/millie.db-shm     32768 B
data/local/millie.db-wal     82432 B
```
- 테이블 7개: `book_stats candidate_sets events preference_snapshots ratings recommendations users` (Must 4 + Should 3, D-05)
- `PRAGMA journal_mode` → `('wal',)`
- `git check-ignore data/local/millie.db` → `data/local/millie.db` (커밋 대상 아님, `.gitignore` L31-32)
- `git status --short | grep -c "data/local"` → **0**

### 사이드이펙트 감사 (사용자 제약 1~5, Phase 1 전체)

`git status --short -- src tests data` — 코드 변경 정확히 8경로:
```
 M src/millie_rec/contracts.py
 M src/millie_rec/serving/__init__.py
?? src/millie_rec/app/server.py
?? src/millie_rec/serving/api.py
?? src/millie_rec/serving/db.py
?? src/millie_rec/serving/fallback.py
?? src/millie_rec/serving/schema.sql
?? tests/serving/test_smoke.py
```

| 감사 항목 | 명령 | 결과 |
|---|---|---|
| 변경 금지 파일 | `git diff --stat -- demo serving/schemas*.py tests/test_architecture.py tests/serving/test_schemas.py Makefile pyproject.toml Dockerfile uv.lock` | **빈 출력** ✅ |
| contracts 최소 변경 | `git diff --numstat src/millie_rec/contracts.py` | `1	0` ✅ |
| 계층 폴더 | `find src/millie_rec -type d \( -name domain -o … -o -name helpers \)` | **빈 출력** ✅ |
| 저작권 (D-14 점검만) | `git ls-files \| grep -iE "pdf\|png\|assets"` | `none` ✅ |
| 커밋 0 | `git log -1 --format=%h` | `8e5172b` (플랜 시작 시점과 동일) ✅ |

`.planning/**`·`.gitignore`·`CLAUDE.md`·`.planning/config.json` 의 변경은 Advisor 세션이 소유하는 문서·설정이라 이 감사의 대상이 아니다(플랜 수용 기준 명시).

### 줄 수 (`wc -l`)

| 파일 | 줄 | 상한 |
|---|---|---|
| `src/millie_rec/app/server.py` | **12** | ≤30 (플랜 예산) ✅ |
| `src/millie_rec/serving/db.py` | 60 | ≤150 ✅ |
| `src/millie_rec/serving/fallback.py` | 45 | ≤150 ✅ |
| `src/millie_rec/serving/api.py` | 128 | ≤150 ✅ |
| `src/millie_rec/serving/schema.sql` | 35 | — |
| `src/millie_rec/serving/__init__.py` | 16 | — |
| `tests/serving/test_smoke.py` | 166 | — |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] 신규 테스트 docstring 이 ruff E501(113 > 100) 위반**
- **Found during:** Task 1-c (`uv run ruff check src tests`)
- **Issue:** 플랜 1-b 원문 docstring `"""millie_rec.app.server:app — StaticFiles 가 마지막에 마운트되어 / 는 demo, /health·/docs·/api 는 그대로."""` 은 ASCII 기준으로는 98자지만 ruff 는 한글을 **폭 2**로 계산해 113 → `line-length = 100`(pyproject `[tool.ruff]`) 위반. 완료 기준 `uv run ruff check src tests` 가 통과할 수 없다. Plan 01 의 `contracts.py` 재포맷 편차와 같은 원인(한글 폭).
- **Fix:** 같은 뜻을 유지한 채 95폭으로 축약 — `"""app.server:app — StaticFiles 마운트가 마지막: / 는 demo, /health·/docs·/api 는 유지."""`. 함수 이름·본문·단정은 플랜 원문 그대로(수용 기준 grep 3종 모두 충족).
- **Files modified:** `tests/serving/test_smoke.py`
- **Commit:** 없음(커밋 금지 플랜)

**2. [Rule 1 - Bug] 모듈 docstring 이 거짓이 됨 (`app/ 은 import 하지 않는다`)**
- **Found during:** Task 1-b (테스트 추가 직후)
- **Issue:** `tests/serving/test_smoke.py` L4 는 Plan 01 이 쓴 `app/ 은 import 하지 않는다.` 였는데, 이 플랜이 추가한 테스트가 정확히 `millie_rec.app.server` 를 import 한다. 파일 머리말이 파일 내용과 모순되면 이후 세션이 잘못된 전제로 편집한다(`../.claude/rules/references.md` 의 "확인 가능한 참조" 정신).
- **Fix:** L4 → `app/ 은 마지막 1건(조립 테스트)에서만 import 한다.` 1줄 교체. 테스트·import·fixture 는 불변(플랜 제약 유지). `tests/` 는 무엇이든 import 가능하므로 아키텍처 위반 아님(`tests/test_architecture.py` 는 `src/` 만 검사, L29).
- **Files modified:** `tests/serving/test_smoke.py`
- **Commit:** 없음(커밋 금지 플랜)

그 외 편차 없음 — `server.py` 는 플랜 1-a 원문 그대로다. Makefile 재실행·수정 없음(`make smoke` 1회 성공).

## Requirements

| ID | 상태 | 근거 |
|---|---|---|
| SKEL-01 | 충족 | `uvicorn millie_rec.app.server:app` 실기동(8010·8011) → `/health` 200, `model_version:null`·`artifacts_loaded_at:null`. 아티팩트·네트워크 없음 |
| SKEL-02 | 충족 | `smoke: / (demo static) 200` + `test_server_module_serves_demo_index_and_keeps_api_routes` 의 `"<html" in root.text` |
| SKEL-03 | 재확인 | 실서버 `/api/recommend?seeds=1,2,3&k=5` → `fallback_level:3`, `rows[0].row_id == "trending"` |
| SKEL-04 | 재확인(실기동) | `data/local/millie.db` 7테이블 + WAL + gitignore |
| SKEL-05 | 충족 | `make smoke` 4줄 · exit 0 · pid 정리 |

## Known Stubs

없음. `server.py` 의 `pipelines={}`·`GlobalPopularFallback(None)` 은 스텁이 아니라 **주입되지 않은 상태의 정의된 동작**(level 3 fallback, CONTEXT D-09·D-10). Phase 2·3·5 가 같은 시그니처의 인자만 채운다.

## Threat Flags

없음 — 이 플랜이 추가한 표면은 `StaticFiles(directory=ROOT/"demo")` 하나이며 플랜 `<threat_model>` T-01-07(경로 traversal, Starlette 정규화에 의존·accept)·T-01-08(라우트 가림, mitigate → `/health`·`/docs`·`/api/recommend` 200 단정으로 고정)에 이미 등록돼 있다. `demo/` 에 비밀·DB 없음(`data/local/` 은 별도 경로 + gitignore).

## 커밋

**커밋 없음.** `git log -1 --format=%h` = `8e5172b` (플랜 시작 시점과 동일). `.planning/STATE.md`·`.planning/ROADMAP.md` 미변경(오케스트레이터 소유).

다음(Advisor): `/codex:review --scope working-tree` → 사용자 승인 → 로컬 커밋 1개, push 없음(CONTEXT D-14); 브라우저 확인 `make serve` → `http://localhost:8000/?source=api`(구 데모 + fallback 배너 = 정상)

## Self-Check: PASSED

- `src/millie_rec/app/server.py` 존재 확인(`wc -l` = 12, `cat -n` 출력)
- `tests/serving/test_smoke.py` 수정 확인(`grep -c "def test_"` = 11, `git status --short` 에 `??` — Plan 01 신규 파일이라 미추적 상태 유지)
- `data/local/millie.db` 존재 확인(`ls -la`, 7테이블 조회 성공)
- 커밋 해시 검증 대상 없음 — 이 플랜은 의도적으로 커밋 0건(`no_commit: true`). `git log -1 --format=%h` = `8e5172b` 불변으로 대체 확인
- 남은 uvicorn 프로세스 0(`pgrep -fl "uvicorn millie_rec"` 빈 출력), 8010·8011 리스너 0
