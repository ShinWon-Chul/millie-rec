---
phase: 07-deploy
plan: 03
wave: 3
status: complete
commits: 0 코드 · push 1회(`79b8e63..9fb53ab`, 3 커밋 — 이 세션 문서 1 + 다른 세션 2)
executed: 2026-09-06
executor: Advisor 직접(조립 레인 — 게이트·Playwright 완주·push·검증. 코드 0)
push_at: "2026-09-06 14:34:53 KST"
active_at: "2026-09-06 14:48:19 KST"     # 90분 규칙(07-CONTEXT D-13) 시계 14:34 → 사용자 approved 14:5x, 마감 16:04 안
approved_at: "2026-09-06 14:5x KST"
requirements_touched: [DEPLOY-02, DEPLOY-01]
---

# 07-03 본배포 — 실행 요약

Phase 7 '배포'(`.planning/ROADMAP.md` "### Phase 7: 배포") wave 3. 결정 '본배포는 재배포다'
(`.planning/phases/07-deploy/07-CONTEXT.md` D-02) — 같은 서비스·같은 도메인·같은 볼륨에 push 1회.
**코드 0줄 수정.** 이 플랜의 `?source=api` 완주 게이트 통과가 Phase 6 '데모 재구성' D-09 이관분
(`.planning/phases/06-demo-rebuild/06-CONTEXT.md`)의 완료 판정을 겸한다.

## Task 1 — push 선행 게이트 (전부 통과)

### 1-a 전제 8행

| 검사 | 기대 | 실측 |
|---|---|---|
| `06-07-SUMMARY.md` 존재 | 존재 | ✅ |
| `git status --short -- demo/ src/ tests/` | 0 | demo·src **0** · tests/ 미추적 3건은 **다른 세션의 밀리 리뷰 작업**(`tests/data/test_millie_review_parse.py`·`test_millie_reviews_build.py`·`tests/fixtures/millie_reviews/`, Makefile `millie-reviews` 타깃 미커밋 포함) — 미커밋이라 push 에 안 섞임. Phase 6 산출물은 전부 커밋됨 |
| `git rev-list --count origin/main..HEAD` | 기록 | 1(`2674d43` 07-02 SUMMARY) — push 직전 다른 세션 커밋 2개 추가돼 **3** |
| freeze 무변경 `git diff 20d5fa3 -- contracts.py schemas.py schemas_should.py artifacts/serving` | 빈 출력 | `schemas.py`·`schemas_should.py` 각 **`+    authors: str \| None = None` 1줄만**(06-08 `c0dc39a`, 사용자 승인 2026-09-06) — **`authors` optional 예외 반영**(07-01-SUMMARY 인계). 그 외 변경 줄 **0**(`grep -v authors` 후 0) · `artifacts/serving` 0 |
| 배포 파일 diff vs origin/main(Dockerfile·railway.json·.dockerignore·pyproject·server.py) | 빈 출력 | ✅ 빈 출력(검사 시점 14:0x — **push 직전 다른 세션이 Dockerfile 을 바꿨다**, 아래 이탈 1) |
| `grep -c 'API_BASE = ""' demo/js/api.js` | 1 | ✅ 1 |
| `find artifacts/serving -size +50M` · `"description"` | 0 · 0 | ✅ 0 · 0 |
| `git ls-files \| grep -icE 'pdf\|png\|assets'` | 0 | **1** — `demo/assets/brand/millie-mark.png`. Phase 6.1 '데모 브랜드 마감' 결정 D-05 마크 배치(`.planning/phases/06.1-demo-brand/06.1-CONTEXT.md`, `.gitignore` `!demo/**/*.png` 허용)로 승인된 자산이며 이미 배포됨. 과제 PDF·캡처·`.assets/` 유출은 0 → DEPLOY-03 충족. **07-04 의 같은 검사도 `grep -v '^demo/assets/brand/'` 예외를 둔다** |

### 1-b 로컬 게이트 3종(D-12)

| 게이트 | 결과 |
|---|---|
| `uv run ruff format --check . && uv run ruff check .` | 143 files already formatted · All checks passed! |
| `uv run pytest --no-header` | **`573 passed in 14.52s`**(`pyproject` `addopts=-q` 라 요약 줄은 `-o addopts=""` 로 확보) — failed 0 |
| `make smoke` | PASS(`/health`·`/`·`/api/recommend` 200) |
| `make docker-up PORT=8001`(`WAIT_S=120`) | `smoke: PASS` · `/health` `db_ok True` · **`LOCAL_MV = hybrid_div_v1`** · `make docker-down` 후 컨테이너 0 |

### 1-c `?source=api` 완주 게이트 — docker 8001 (Phase 6 D-09 이관분)

스크립트: 스크래치패드 `walk.py`(`/private/tmp/claude-501/-Users-shinwonchul-Documents----------/9dcbb889-1193-46b3-b9ea-ea02cbf045cc/scratchpad/walk.py`, repo 밖).
Phase 6 mock 완주 스크립트(`pw_demo06/run.py`, 17/17)의 셀렉터를 계승해 온보딩 7단계를 실제 클릭한다.
순서: `#/` → `#/onboarding`(S0 시작 → S1~S5 → 5권) → `#/home` → 앵커 타일 → `#/book/:id` → 바로 읽기
→ `#/reader/:id`(10분×2 · 완독 · 별점 4) → `#/home`(after_completion) → `#/library` → 철회 →
`#/home`(level 3 배너) → `#/refresh` → `#/home`(앵커 복귀) → `#/dashboard` → `#/home` 모델 라디오 4회.

```json
{"steps_ok":"12/12","console_errors":[],"page_errors":[],"api_non2xx":[],
 "variants_seen":["pop","cf","hybrid","hybrid_div"],"distinct_title_lists":4,
 "cards":{"pop":45,"cf":41,"hybrid":23,"hybrid_div":45},"forced_label":true}
```

행 관측: 온보딩 직후 `['anchor_1004','persona_shelf','trending','fresh_picks']` → 완독 후
`after_completion` 선두 → 철회 후 `['trending','fresh_picks']` + 비개인화 배너 → 재설정 후 앵커 복귀.
제목 상위 3개는 네 variant 모두 `불편한 편의점 · 불편한 편의점 2 · 나의 돈키호테`(선두 행 =
완독 직후/이어읽기 개인 행이라 공유) — 상이함은 전체 카드 목록(23~45장) 기준 4/4.

### 1-d Codex 배포 직전 리뷰

`codex-companion.mjs review --background --base 20d5fa3 --scope branch` 실행(job `review-mtpcr7p2-2vp02y`).
**20분간 `investigating` 에서 진행 없음**(로그 마지막 = `codegraph_context failed` ×2) → 취소.
직전 `adversarial-review --help` 가 `--help` 를 focus 텍스트로 받아 작업 트리 리뷰를 잘못 시작한 건도 취소.
판정: 배포 파일 4개(Dockerfile·railway.json·pyproject·server.py)는 검사 시점 기준 07-01 Codex 리뷰 2회
(F1 fail-open 반영 · F2·F3 무시) 이후 무변경 → **"배포 파일 무변경 — 07-01 리뷰 유효"**. 단 push 직전
다른 세션의 Dockerfile 변경이 들어와(이탈 1) **07-04 Task 2 의 배포 전체 Codex 리뷰가 이를 반드시 포함**한다.
demo/ 인계 목록: 없음(리뷰 미완).

## Task 2 — SENTRY_DSN → push → Active

- 사용자 "dsn set"(Variables 투입, 재배포 Active — 배포 로그: 볼륨 마운트 · uvicorn 8080 · `/health` 200,
  sentry 에러 0). DSN 문자열은 어디에도 적지 않았다(T-07-03-02).
- push 전 `/health`(14:10): `hybrid_div_v1` · users **1** · snapshots 1 · events 5(07-02 표식 그대로).
  DSN 재배포 후(14:34, uptime 235s): users **4**.
- `git push origin main` **14:34:53 KST** → `79b8e63..9fb53ab main -> main`. `origin/main..HEAD` = 0.
- Active **14:48:19 KST**(`/health` 5초 폴링: 14:48:13 http=000 1표본 → 14:48:19 uptime 11s).
  소요 13.5분 — Dockerfile 변경으로 `uv sync` 레이어 재빌드. 다운 자체는 07-02 실측(5~15초)과 같은 1표본.
  다운타임 재측정은 D-14 1회 원칙대로 하지 않았다(07-02 값이 정본).

## Task 3 — 배포 URL 검증 (`https://millie-rec-production.up.railway.app`)

| 검사 | 기대 | 실측 |
|---|---|---|
| `/health.model_version` | == `LOCAL_MV` | ✅ **`hybrid_div_v1`**(문자열 동일) · `db_ok true` · `artifacts_loaded_at 05:48:07Z` |
| `db_row_count.users` | ≥ N_AFTER(1) | ✅ 4(Active 직후) → 7(표식 생성 후). snapshots 8 · events 953 |
| 표식 `probe-volume-20260906` `/api/recommend` | level 0 | ❌ **level 3 · `fallback_v1`** — `/api/users/…/state` 404(행 없음). 이탈 2 |
| 신규 표식 `probe-main-20260906`(14:51 POST) | — | ✅ `snap_7bde89` · cell A · `/api/recommend` **level 0 · `hybrid_div_v1` · rows `continue_reading·anchor_1·persona_shelf·trending·fresh_picks`** |
| `/api/showcase` | holdout · 4행 | ✅ holdout · 4 · **`p95_ms 79.5` ×4행**(출처 `results/latency.json`) |
| `/api/dashboard` | 200 | ✅ 11키(`kpi`·`ab_table`·`latency`·`mde_note`…) · `p95_latency_ms 354`(참고용, PDF 금지) · `error_rate 0` |
| `/metrics` | 404 | ✅ 404(D-05 Grafana 폐기) |
| `/?source=api&api=http://127.0.0.1:1` | 200 | ✅ 200 |
| walk.py(배포 URL) | 콘솔 에러 0 · 4 variant · distinct ≥2 | ✅ **12/12 OK · console_errors [] · page_errors [] · api_non2xx [] · variants 4 · distinct 4**(pop 45 · cf 41 · hybrid 42 · hybrid_div 45, 모두 `forced`) |
| 사용자 브라우저 확인 | approved | ✅ **"approved"**(완주·variant 전환·클라이언트 fallback·Sentry 이벤트 0). Redeploy 신호 없음 → 이름 기준 볼륨 확인은 07-04 |

STATE.md: Day 게이트 4 ✅ · Deploy 줄 `본배포 9fb53ab 2026-09-06 14:48` · Monitor 줄 DSN 투입 · Current Position wave 3 완료.

## 플랜과 달랐던 점 (이탈 3건 + 가정 불일치 2건)

1. **push 범위에 다른 세션 커밋 2개 동반.** `3097d78 feat(report)`(d8_showcase 헤더 "온보딩 직후 n=0" 칩·캡션,
   **Dockerfile `COPY results/latency.json` +3줄**, `report/interview_story.md`) · `9fb53ab fix(demo)`(별점 모달
   누적 채움 CSS + 방향 라벨). 1-a 5번 검사(빈 diff)는 그 커밋 전이었다. Dockerfile 변경은 이 플랜의
   `must_not_touch` 이자 D-11 "Dockerfile 3조건 불변" 대상이지만, 내용은 07-03 Task 1 에서 관측한 "showcase p95 null"
   을 정확히 고치는 1줄(`.dockerignore` 에 `!results/latency.json` 이미 있어 로컬 `docker build` 성공 확인)이다.
   push 는 사용자 "push ok" 승인 범위(origin/main..HEAD 전부) 안. **Codex 리뷰는 07-04 로 이월(필수).**
2. **07-02 표식 `probe-volume-20260906` 이 배포 DB 에 없다.** 14:10 까지 users 1·snapshots 1·events 5 로 표식
   수치 그대로였고 DSN 재배포 후 users 4. (가) 볼륨이 DSN 재배포에서 초기화됐다 (나) 14:10 의 1행이 표식이 아니었다
   — 수치만으론 구분 불가. 대응: 신규 표식 `probe-main-20260906` 생성(level 0 확인). **07-04 push 뒤
   `/api/users/probe-main-20260906/state` 200 을 이름으로 확인**해 DEPLOY-01 후반을 닫는다. 실패면 Railway Volume
   mount path ↔ `DATA_DIR` 재점검(배포 02 §7).
3. **Codex 리뷰 미완**(위 1-d) — 07-04 로 이월.
4. (가정 불일치) 플랜은 `/api/showcase.eval_table.p95_ms 79.5` 를 기대했으나 Task 1 시점 배포본·mock 모두 `null`
   ("p95 출처 로컬 bench — 아직 없음"). 이탈 1 의 Dockerfile 변경으로 Task 3 시점엔 79.5 표시. PDF 숫자
   `results/latency.json p95 79.5` 는 처음부터 무사.
5. (가정 불일치) 대시보드 api 모드에 "MDE" 문구 없음(`mde_note` 키는 있으나 화면 문구는 mock 전용). 게이트 항목 아님.

## 07-04 인계

- 표식 `probe-main-20260906` 이름 확인(push 후) · 배포 전체 Codex 리뷰(Dockerfile +3 포함) · DEPLOY-03 검사에
  `demo/assets/brand/` 예외 · REQUIREMENTS DEMO-09 api 절반 ✅ · DEPLOY-01/02 ✅ 갱신 · PROGRESS·개발일지 **D82**
  (D81 은 06-08 선점) · draft §3-3 배포 실측(다운 1표본 ≈5~10초, Dockerfile 변경 빌드 13.5분) · `railway.json` 처분.
- 다른 세션 미커밋 작업(Makefile `millie-reviews` · `scripts/*_millie_review*` · `tests/data/test_millie_review*`)은
  건드리지 않았다. 07-04 push 전 `git status` 로 동반 여부를 다시 본다.
- 캡처 원본 후보: 스크래치패드 `shots_prod/`(배포 URL 완주 12장, 1480×1000) — 07-04 캡처 6장은 플랜대로 재촬영.
