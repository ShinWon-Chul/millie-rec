---
phase: 07-deploy
plan: 01
wave: 1
status: complete
executed: 2026-09-06
executor: Advisor 직접(조립 레인 — `pyproject.toml`·`src/millie_rec/app/server.py` 는 Advisor 전용 파일, `.claude/rules/architecture.md`)
head_at_start: a8f0b70
head_at_verify: 95ed776   # Phase 6 세션의 06-08 5커밋이 실행 중 착지 — 아래 "세션 간 충돌" 절
commit: 68cef80(코드 4파일) · 이 문서(docs 커밋)
push: 0
---

# 07-01 코드 준비 — 실행 요약

Phase 7 '배포'(`.planning/ROADMAP.md` "### Phase 7: 배포") wave 1. 이 페이즈에서 코드가 바뀌는
유일한 플랜이다. 결과: `sentry-sdk[fastapi]` 1개 + `app/server.py` `init_sentry()` + 테스트 1파일,
로컬 게이트 20행 전부 통과, Codex 필수 리뷰 2회 → 필수 fix 1건 반영, 커밋 2 · **push 0**.

## Task 1 — Sentry 초기화 (TDD)

### Red (verbatim)

```
==================================== ERRORS ====================================
__________________ ERROR collecting tests/app/test_sentry.py ___________________
ImportError while importing test module '.../millie-rec/tests/app/test_sentry.py'.
Traceback:
tests/app/test_sentry.py:10: in <module>
    import sentry_sdk
E   ModuleNotFoundError: No module named 'sentry_sdk'
=========================== short test summary imports ============================
ERROR tests/app/test_sentry.py
!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
1 error in 0.07s
```

### Green

- `uv run pytest tests/app/test_sentry.py --no-header` → **3 passed in 0.37s**
- `uv run pytest tests/app --no-header` → **33 passed**
- `env -u SENTRY_DSN uv run python -c "import millie_rec.app.server, sentry_sdk; assert not sentry_sdk.is_initialized()"` → `SENTRY_OFF_WITHOUT_DSN` (실 아티팩트로 기동해도 Sentry 비활성)

### 변경 내용

| 파일 | 변경 |
|---|---|
| `pyproject.toml` | `dependencies` 끝에 `"sentry-sdk[fastapi]>=2.0",` 1줄. `grep -c prometheus` == 0 유지(결정 'Grafana 폐기'(`.planning/phases/07-deploy/07-CONTEXT.md` D-05)) |
| `uv.lock` | `sentry-sdk 2.68.1` + 전이 의존 `urllib3 2.7.0`. Dockerfile `uv sync --frozen` 이 이 lock 을 읽는다 |
| `src/millie_rec/app/server.py` | `import logging`·`import os` + `init_sentry()` 정의 + 호출 1줄. **38 → 61줄**(Codex F1 fail-open 포함) |
| `tests/app/test_sentry.py` | 신설 **4 테스트**(DSN 없음 · DSN 있음 · 줄 수 가드 · F1 예외 주입). `_server` 헬퍼는 `tests/app/test_server_catalog.py` 에서 복제(2곳째 — `_shared` 는 3곳부터, `.claude/rules/simplicity.md`) |
| `../PROGRESS.md` | 결정 로그 1행(의존성 추가) + 세션 간 알림 회신 1행 |

`init_sentry()` 최종형(`src/millie_rec/app/server.py` L21~L36 — Codex F1 반영 후):

```python
def init_sentry() -> bool:
    """SENTRY_DSN 있을 때만 Sentry 초기화 — 없으면 SDK import 도 안 한다(07-CONTEXT D-04)."""
    dsn = os.environ.get("SENTRY_DSN")
    if not dsn:
        return False
    import sentry_sdk  # 지연 import — 로컬·테스트 기동 경로는 SDK 를 건드리지 않는다(네트워크 0)

    # traces 0 = 예외만(성능 추적 없음) · PII off = 가명 user_key 외 미전송(백엔드 §3-8)
    env = os.environ.get("RAILWAY_ENVIRONMENT_NAME", "local")
    try:  # fail-open(Codex F1) — 관측 기능이 기동을 막지 않는다. DSN 은 로그에 안 남긴다
        sentry_sdk.init(dsn=dsn, traces_sample_rate=0, send_default_pii=False, environment=env)
    except Exception:
        logging.getLogger(__name__).warning("SENTRY_DSN 이 잘못돼 Sentry 를 끕니다")
        return False
    return True
```

기존 흐름은 무변경이다 — `git diff src/millie_rec/app/server.py` 는 추가만 있고
`catalog = load_catalog()` · `create_app(...)` · `app.mount(...)` 줄은 손대지 않았다.
Claude's Discretion 2건 결정: 초기화 위치 = `create_app` 앞 모듈 상단, `environment` =
Railway 가 주입하는 `RAILWAY_ENVIRONMENT_NAME` 이 있으면 그 값, 없으면 `"local"`.

### 계획 이탈 1건 — `max_lines: 50` → 61 (사용자 승인 2026-09-06)

07-01-PLAN.md 는 `src/millie_rec/app/server.py` `max_lines: 50` 을 걸었으나 **계획이 지정한
형태로는 산술적으로 불가능**하다. 기존 38줄은 "무변경" 이 요구사항이고, 계획이 본문에 직접 적어 준
`init_sentry()` 를 넣으면:

| 항목 | 줄 |
|---|---|
| 기존 파일 | 38 |
| `import logging`·`import os` + 그룹 구분 빈 줄(ruff I) | +3 |
| `def init_sentry()` 본문(docstring 1 · 분기 3 · 지연 import 1 · 빈 줄 1(ruff format 강제) · 주석 1 · 본문 2 · return 1) | +11 |
| Codex F1 fail-open `try/except` 4줄 | +4 |
| 함수 앞뒤 빈 줄 2+2(ruff format 강제) · `init_sentry()` 호출 1 · 기존 주석 블록 앞 빈 줄 1 | +5 |
| **합계** | **61** |

빈 줄 2개를 지웠더니 `ruff format --check` 가 되돌렸다(지연 import 뒤 빈 줄은 포매터 강제).
조치: 테스트 상수를 `MAX_SERVER_LINES = 65` 로 두고 근거 주석 3줄을 달았다. 65 는 "얇은 진입점
유지" 가드이며 `.claude/rules/simplicity.md` 의 실제 상한은 150 이다. Task 3 체크포인트에서
사용자 승인을 받았다(2026-09-06).

계획의 다른 지시 1건도 이탈했다: 모듈 docstring 을 `"""uvicorn 진입점: Sentry(DSN 있을 때만) + …"""`
로 바꾸라 했으나 그러면 106자가 되어 ruff `E501`(line-length 100) 에 걸린다. 원문 docstring 을 그대로
두고 Sentry 설명은 `init_sentry()` 자신의 docstring 이 진다(최소 변경 원칙, `CLAUDE.md` §3-7).

## Task 2 — push 선행 게이트 20행

| # | 검사 | 기대 | 실측 |
|---|---|---|---|
| 1 | `grep -c 'uv sync --frozen --no-dev' Dockerfile` | 2 | **2** ✅ |
| 2 | `grep -c '^USER ' Dockerfile` | 0 | **0** ✅ |
| 3 | `grep -c 'PORT:-8000' Dockerfile` | 1 | **1** ✅ |
| 4 | `railway.json` healthcheck `/health` · replica 1 · builder DOCKERFILE | 종료 0 | **OK** ✅ |
| 5 | `!artifacts/serving` (dockerignore·gitignore) + `.gitkeep` | 각 1 · 존재 | **1 / 1 / yes** ✅ |
| 6 | `git ls-files \| grep -icE "pdf\|png\|assets"` | 0 | **0** ✅ (DEPLOY-03) |
| 7 | `git check-ignore report/figures/x.png` | 무시됨 | **FIGURES_IGNORED** ✅ |
| 8 | `find artifacts/serving -size +50M` · `du -sh` | 0 · ≈30M | **0 · 30M** ✅ |
| 9 | `git ls-files uv.lock` | 추적 중 | **uv.lock** ✅ |
| 10 | `ruff format --check .` · `ruff check .` | 클린 | **135 files already formatted · All checks passed** ✅ |
| 11 | `uv run pytest --no-header` | failed 0 | **534 passed**(HEAD `95ed776`) → F1 반영 후 **535 passed** ✅ |
| 12 | `make smoke` | PASS | **smoke: PASS** ✅ |
| 13 | `make docker-up PORT=8001` | smoke PASS | **smoke: PASS · `/health` `status=ok db_ok=True model_version=hybrid_div_v1`** ✅ |
| 14 | `/health` jq | db_ok true · model_version 비-null | **true · `hybrid_div_v1` · `artifacts_loaded_at 2026-09-06T02:27:28Z`** ✅ (아티팩트가 이미지에 실림 — D-09) |
| 15 | `POST /api/preferences` → `db_row_count.users` | N1 ≥ 1 | **201 · N1 = 1** ✅ |
| 16 | `docker restart` 후 users | == N1 | **1 == 1 → VOLUME_PERSISTED** ✅ (named volume `millie-rec-data`) |
| 17 | `/api/recommend?model=hybrid_div&seeds=1,2,3,4,5` | 200 | **`fallback_level 0` · `hybrid_div_v1` · rows `["trending"]`** ✅ |
| 18 | `GET /?source=api` | 200 | **200** ✅ (화면 완주는 07-03 게이트 — `06-CONTEXT.md` D-09) |
| 19 | 이미지 크기 | 기록 | **749 MB** (아래 주의) |
| 20 | `make docker-down` | 컨테이너 정리 | **removed container millie-rec-local · 잔존 0**(볼륨·이미지 유지) ✅ |

`git diff --stat -- Dockerfile railway.json .dockerignore` = **빈 출력**(D-11 3조건 무변경).

### 07-02 로 넘기는 관측 2건

- **이미지 749MB.** `artifacts/serving` 30MB 는 일부일 뿐이고 대부분은 `python:3.11-slim` +
  numpy/scipy/pandas/pyarrow/scikit-learn/matplotlib 이다. Railway 빌드 시간·배포 시간이
  로컬보다 길 수 있으니 `railway.json` 의 `healthcheckTimeout 120` 이 충분한지 07-02 §3-2 에서
  실측한다(초과 시 healthcheck 실패로 나타난다).
- **`make smoke` 의 좀비 uvicorn.** `Makefile` `smoke:` 는 `kill $(cat .uvicorn.pid)` 로
  `uv run` 래퍼만 죽이고 그 자식 python 이 8010 을 계속 잡는다. 출력을 파이프로 받으면 파이프가
  닫히지 않아 명령이 끝나지 않는다(이번에 재현 — 파일 리다이렉트로 우회). **게이트 판정에는 영향
  없지만**(`smoke: PASS` 는 정상 출력) `Makefile` 은 Advisor 전용이고 이 플랜의 `must_not_touch`
  라 고치지 않았다. 07-04 나 별도 결정으로 다룬다.

## 세션 간 충돌 점검 (사용자 지시 — Phase 6 동시 진행)

Phase 6 '데모 재구성' 세션이 `/gsd-verify-work 6` Gap 1(서재·쇼케이스 저자 미표시)을 이 세션과
**같은 시간에** 06-08 로 닫았다. 실행 중 착지한 커밋 5개: `7ad056e`(Red) · `c0dc39a`(계약) ·
`ccef4e3`(생성기) · `88910ca`(화면) · `fee6b19`·`95ed776`(문서).

**파일 충돌 0.** 06-08 이 만진 `serving/schemas.py`·`schemas_should.py`·`privacy_api.py`·`demo/**`
는 이 플랜의 `must_not_touch` 이고, 이 플랜이 만진 `pyproject.toml`·`app/server.py`·`uv.lock`·
`tests/app/test_sentry.py` 는 06-08 의 `must_not_touch` 다(`06-08-PLAN.md` frontmatter 에
"특히 Dockerfile·railway·server.py 는 Phase 7 세션" 으로 명시돼 있다). `PROGRESS.md` 는 양쪽이
append 하므로 편집 직전 재읽기로 처리했다(`CLAUDE.md` §6).

게이트 11·12 는 06-08 착지 **후** HEAD `95ed776` 에서 재실행해 `534 passed` · `smoke: PASS` 를
다시 확인했다(첫 실행은 `a8f0b70` 기준, 같은 534).

### 다음 wave 가 떠안는 선행 조정 2건 — **wave 1 에서 고치지 않았다**

1. **`07-03-PLAN.md` 의 freeze 무변경 검사가 이미 깨져 있다.** must_have
   `"git diff 20d5fa3 -- … serving/schemas.py serving/schemas_should.py … 이 빈 출력"` 은 06-08
   `c0dc39a` 로 각 `+1` 줄(`authors: str | None = None`)이 되어 **거짓 실패**한다. wave 3 착수 시
   "`authors` optional 추가분(계약 freeze 예외, 사용자 승인 2026-09-06)만 예외" 로 검사를 고쳐야
   한다. 근거 = `.claude/rules/architecture.md` "필드 추가는 기본값 있는 optional 로만".
2. **개발일지 `### D81` 을 06-08 이 선점했다.** `07-04-PLAN.md` 는 본문(L346)에서 "다른 세션이
   D81 을 먼저 쓸 수 있다 — 그러면 다음 번호로" 라고 이미 대비했지만, artifacts 의
   `contains: "### D81."`(L56)과 자동 검증 `grep -q "### D81\."`(L373)은 번호를 하드코딩했다.
   wave 4 착수 시 **D82** 로 함께 정정한다.

## Task 3 — Codex 필수 리뷰

`.claude/rules/codex-review.md` "언제" 표의 **필수** 2행(`Dockerfile`·`railway.json` / 배포 직전)에
해당해 2회 실행했다. `Dockerfile`·`railway.json` 은 `20d5fa3` 이후 무변경이라 working-tree diff 에
잡히지 않으므로, 적대적 리뷰에 "diff 밖의 배포 파일도 반드시 읽으라" 는 초점을 명시해 덮었다.

| 회차 | 명령 | 결과 |
|---|---|---|
| 1 | `codex-companion.mjs review --wait --scope working-tree` | **지적 0.** "Sentry initialization is correctly gated by SENTRY_DSN, and the dependency and lockfile changes are consistent. No functional regression was identified." (테스트 실행은 샌드박스의 uv 캐시 접근 제한으로 차단됨 — Advisor 가 별도로 534 passed 확인) |
| 2 | `codex-companion.mjs adversarial-review --wait --scope working-tree <배포 초점>` | **needs-attention 3건**(high 2 · medium 1) |

### 3분류

| # | 지적 | 분류 | 판단 |
|---|---|---|---|
| F1 | **[high] 잘못된 `SENTRY_DSN` 이 서버 기동을 막는다**(`app/server.py:29`) — 비어 있지 않은 DSN 이면 예외 경계 없이 `sentry_sdk.init()` 호출, `BadDsn` 이 모듈 import 를 깨고 `restartPolicyMaxRetries 3` 을 소진 | **필수 fix** | Advisor 가 독립 재현: `SENTRY_DSN='not-a-dsn'` → `sentry_sdk.utils.BadDsn: Unsupported scheme ''`. 07-03 에서 Railway Variables 에 DSN 을 넣는 순간 드러나는, D-11 이 막으려던 "배포 시점에만 드러나는 결함" 그 자체다. `.claude/rules/local-run.md` "외부 연동은 환경변수가 없으면 비활성" 의 정신 = 관측 부가기능이 서비스를 죽이면 안 된다. 수정 4줄 + 테스트 1개 |
| F2 | **[high] 고장 난 DB·모델도 헬스체크를 통과한다**(`serving/api.py:124`) — `status="ok"` 하드코딩, `db_ok=false`·`model_version=null` 이어도 HTTP 200 | **토론 → 무시 권고** | 사실은 맞다(Advisor 직접 확인). 그러나 이건 결함이 아니라 **결정**이다 — `.claude/rules/local-run.md` "아티팩트·DB·네트워크 없이 기동한다 … 비어 있으면 빈 `trending` 행 + level 3" 가 walking skeleton 의 전제이고, 이게 없었으면 Day 1~2 스켈레톤 배포 자체가 불가능했다. 게다가 `serving/**` 는 이 플랜의 `must_not_touch`(Phase 5 검증 완료) 이고 `HealthOut` 은 🧊 freeze 다. **대신 07-02 검증을 강화한다**: `/health` 200 만 보지 말고 `db_ok true` + `model_version` 비-null 을 함께 단정(07-02 must_have 에 이미 그렇게 적혀 있다). readiness/liveness 분리는 PDF "설계만" 항목으로 |
| F3 | **[medium] `python:3.11-slim`·`uv:latest` 가 가변 태그**(`Dockerfile:1`) — 같은 커밋의 재빌드가 OS·패치·uv 버전을 바꿀 수 있다 | **무시** | 결정 'Dockerfile 3조건 불변'(`.planning/phases/07-deploy/07-CONTEXT.md` D-11)이 이 파일을 잠갔고, 심사 기간은 3일이라 드리프트 위험 < 배포 직전 Dockerfile 변경 위험이다. digest 고정은 Docker 재빌드 게이트 20행 재실행을 요구해 90분 규칙(D-13)을 위협한다. PDF 3장 "설계만" 에 한 줄로 남긴다 |

### F1 반영 결과 (사용자 승인 2026-09-06 — "반영한다")

```python
    import sentry_sdk  # 지연 import — 로컬·테스트 기동 경로는 SDK 를 건드리지 않는다(네트워크 0)

    # traces 0 = 예외만(성능 추적 없음) · PII off = 가명 user_key 외 미전송(백엔드 §3-8)
    env = os.environ.get("RAILWAY_ENVIRONMENT_NAME", "local")
    try:  # fail-open: 관측 부가기능이 서버 기동을 막지 않는다(DSN 은 로그에 남기지 않는다)
        sentry_sdk.init(dsn=dsn, traces_sample_rate=0, send_default_pii=False, environment=env)
    except Exception:
        logging.getLogger(__name__).warning("SENTRY_DSN 이 잘못돼 Sentry 를 끕니다", exc_info=False)
        return False
    return True
```

실제 반영본은 주석을 100자에 맞춰 한 줄 줄였다(`ruff E501`). 동반 테스트
`test_bad_dsn_does_not_break_server_import` 추가 — `sentry_sdk.init` 이 `BadDsn` 을 던지게 한 뒤
`_server(...)` import 가 성공하고 `server.app` 이 살아 있으며 `init_sentry()` 가 `False` 를 돌려주는지
단정한다. `server.py` 56 → **61줄**, `MAX_SERVER_LINES` 60 → **65**.

spy 없이 실제로도 재확인:

```
$ SENTRY_DSN='not-a-dsn' uv run python -c "import millie_rec.app.server as s, sentry_sdk; ..."
SENTRY_DSN 이 잘못돼 Sentry 를 끕니다
import OK · app: FastAPI · sentry on: False
```

**F1 반영 후 게이트 10~12 재실행:** `ruff format --check` 135 files already formatted ·
`ruff check` All checks passed · `uv run pytest --no-header` **535 passed, 2 warnings** ·
`make smoke` **PASS**.

**F2·F3 는 사용자 승인으로 무시**(2026-09-06 — "둘 다 무시 권고 수용"). 코드 변경 0.
F2 는 07-02 검증에서 `/health` 200 + `db_ok true` + `model_version` 비-null 동시 단정으로 갈음하고,
F3 는 PDF 3장 "설계만" 한 줄로 남긴다.

## 수용 기준 대조

| 기준 | 결과 |
|---|---|
| Red 출력 verbatim 기록 | ✅ 위 |
| `test_sentry.py` 3 passed | ✅ **4 passed**(F1 예외 주입 테스트 1개 추가) |
| `server.py` ≤ 50줄 | ❌ **61줄 — 계획 수치 이탈**(위 근거, 사용자 승인 2026-09-06). 가드는 `MAX_SERVER_LINES = 65` |
| 기존 `create_app(`·`app.mount(` 무변경 | ✅ 추가만 |
| `grep -c 'sentry-sdk[fastapi]' pyproject.toml` == 1 | ✅ |
| `grep -c prometheus pyproject.toml` == 0 | ✅ |
| `uv.lock` 에 sentry-sdk | ✅ 2.68.1 |
| DSN 없이 `is_initialized()` False | ✅ |
| `PROGRESS.md` 결정 로그 sentry-sdk 1행 | ✅ |
| 게이트 20행 | ✅ 20/20 |
| Codex 3분류 + 사용자 승인 + 커밋 1 · push 0 | ✅ F1 반영 · F2·F3 무시 · 커밋 2(`68cef80` 코드 · `21b5dc0` 문서) · **push 0** |

## 07-02 착수 조건

- 코드·게이트 측 전제는 충족(로컬 pytest·smoke·docker 스모크 3종 PASS = ROADMAP Success Criteria 4).
- Codex 3분류·커밋 완료. **push 0.**
- ⚠️ **07-02 Task 1 의 push 는 커밋 16개를 한 번에 올린다**(`git rev-list --count origin/main..HEAD` = 16).
  이 플랜의 2개 외 14개는 Phase 6 '데모 재구성' 세션(06-06~06-08)의 것이다. 결정 '커밋·push 완료'
  (`.planning/phases/07-deploy/07-CONTEXT.md` D-03)가 "Phase 6 세션의 커밋이 같은 브랜치에 있어 함께
  공개됐다(사용자 승인)" 로 이미 다룬 사안이지만, push 승인 시 **범위를 다시 고지**한다.
- 작업 트리에 `results/millie_edges_gate.json` 1건이 남아 있다(이 세션 소유 아님 · `results/**` 는
  `must_not_touch`). 07-02 push 전 소유 세션 확인이 필요하다.
- 사용자 몫 35분(Railway Hobby 결제 · New Project · Volume `/data` 1GB · `DATA_DIR=/data` ·
  Generate Domain)은 07-02 에서 안내한다.
