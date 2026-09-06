# Phase 7: 배포 - Context

**Gathered:** 2026-09-06
**Status:** Ready for planning

<domain>
## Phase Boundary

심사 기간 내내 살아 있는 **URL 하나**에서 프론트(정적 8페이지)·API·SQLite가 같은 origin으로 서빙된다. 컨테이너 1개(Railway Hobby), 볼륨 1개(`/data`), 감시 1개(UptimeRobot), 예외 수집 1개(Sentry). 배포는 **두 번** 한다 — ① 스켈레톤(지금, 리스크 노출) ② 본배포(Phase 6 '데모 재구성' 완료 후).

**이 페이즈가 만들지 않는 것:** 새 엔드포인트·모델·화면(전부 Phase 5·6에서 끝났다), 오토스케일링·K8s·CDN(설계만), 커스텀 도메인.

**쓰기 영역:** `Dockerfile` · `railway.json` · `.dockerignore` · `app/server.py`(Sentry 초기화 3줄) · `pyproject.toml`(의존성 1개) · `.planning/` · 문서. 전부 **Advisor 전용** 파일이다(`../.claude/rules/architecture.md`). `demo/`는 Phase 6 레인이라 건드리지 않는다.

**PDF 기여(4축 태그):** 축③ 추천 구조 — "컨테이너 1개가 프론트·API·SQLite·Nearline을 한 주소에서" · 축④/실서비스 — 배포 URL·QR·완주 스크린샷이 5장의 데모 절을 채운다. 배포가 실패해도 PDF는 완결된다(§9 대체 경로).

</domain>

<decisions>
## Implementation Decisions

### 배포 시점과 순서 (사용자 결정 2026-09-06)
- **D-01 (스켈레톤을 지금 한다):** Phase 6이 진행 중이어도 지금 배포한다. 목적은 데모 완성이 아니라 **빌드·볼륨·도메인 리스크를 Day 4 이전에 드러내는 것**이다. 배포되는 것은 Phase 5까지의 서버(Must API 12개 전부 동작) + 데모 v1 화면이다. 선택지 '한 번에 배포'는 빌드 실패가 Day 4에 처음 드러나 90분 규칙을 위협해 버렸다.
- **D-02 (본배포는 재배포다):** Phase 6 완료 후 같은 서비스에 push 한 번으로 갱신한다. 새 프로젝트를 만들지 않는다 — 도메인·볼륨·환경변수가 유지되어야 UptimeRobot 모니터와 PDF에 적을 URL이 바뀌지 않는다.
- **D-03 (커밋·push 완료):** Phase 1~5 산출물 249파일을 `20d5fa3` 으로 커밋하고 `origin/main` 에 push했다(2026-09-06). Phase 6 세션의 커밋 21개가 같은 브랜치에 있어 함께 공개됐다(사용자 승인). 이후 push = Railway 자동 재배포이므로 **push 전 로컬 게이트 통과가 의무**다(`../.claude/rules/local-run.md`).

### 관측 범위 (사용자 결정 2026-09-06 — 결정 'Should 꼬리…'(개발일지 2026-09-06 파일 항목 D76) 부분 번복)
- **D-04 (Sentry 유지):** `sentry-sdk[fastapi]` 의존성을 추가하고 `app/server.py` 에서 `SENTRY_DSN` 환경변수가 있을 때만 초기화한다(없으면 완전 비활성 — 로컬·테스트는 네트워크를 타지 않는다). D76이 "미추가"로 적었던 것을 이 결정이 번복한다. `traces_sample_rate=0`(예외만, 성능 추적 없음), `send_default_pii=False`(가명 `user_key` 외 개인정보 없음 — 백엔드 §3-8).
- **D-05 (Grafana 폐기):** `GET /metrics`·prometheus-client·Grafana Cloud scrape를 하지 않는다. D76의 판단(가장 무거운데 PDF 기여는 문장 하나) 그대로다. PDF에는 "설계만 — 관측" 1줄로 남고 draft §4-3 모니터링 행에 이미 반영돼 있다. ROADMAP의 **DEPLOY-04는 이 결정으로 폐기**한다.
- **D-06 (UptimeRobot 유지):** 5분 간격 `/health` 감시 1개. 무료·카드 불필요·5분 작업이고 DEPLOY-03의 수용 기준이다.

### repo 위생·저작권 (사용자 결정 2026-09-06)
- **D-07 (그림은 repo 밖):** `.gitignore` 에서 `!report/figures/*.png` 예외를 제거하고 `report/figures/` 를 무시한다. 이유는 Day 4 데모 캡처 6장에 **밀리 표지 이미지**가 들어가는데 repo가 public이기 때문이다(`../.claude/rules/data.md` 표지 이미지 금지). 그림은 로컬에 남아 Notion 조판에만 쓴다.
- **D-08 (게이트는 그대로):** DEPLOY-03의 `git ls-files | grep -iE "pdf|png|assets"` 빈 결과 판정을 완화하지 않는다. 2026-09-06 커밋 후 실측 빈 결과 확인.

### 이미지·볼륨·환경변수 (배포 02 문서 확정, 재확인)
- **D-09 (아티팩트는 이미지에 굽는다):** `artifacts/serving/` 31MB(최대 파일 11MB)를 Dockerfile `COPY` 로 이미지에 넣는다. 볼륨에 두지 않는다 — 볼륨은 쓰기 상태(SQLite) 전용이고, 아티팩트가 이미지에 있어야 롤백 시 코드와 데이터가 함께 되돌아간다. 파일당 50MB 한도 안.
- **D-10 (볼륨은 `/data` 하나):** 1GB, `DATA_DIR=/data`. `serving/db.py` 가 `contracts.ENV_DATA_DIR` 로 해석한다. 검증 = Restart 후 `/health.db_row_count` 가 0으로 리셋되지 않는 것(배포 02 §3-2).
- **D-11 (Dockerfile 3조건 불변):** ① `uv sync` 두 번(두 번째가 src-layout 패키지 설치) ② `USER` 지시어 없음(Railway 볼륨은 root 소유) ③ `${PORT:-8000}`. 이 셋 중 하나라도 빠지면 배포 시점에만 드러나는 결함이다. 계획은 이 세 줄을 grep으로 검사한다.

### 검증·실패 처리
- **D-12 (배포 전 로컬 게이트):** `uv run pytest --no-header` failed 0 · `make smoke` PASS · 로컬 docker 스모크(배포 02 §4-2)가 push 선행 조건이다. Railway 에서 `make bench` 를 돌리지 않는다 — PDF p95는 로컬 실측 `results/latency.json`(79.5ms)만 쓴다(`../.claude/rules/serving.md` 숫자 규칙).
- **D-13 (90분 규칙 · 대체 경로):** 배포가 90분 안에 풀리지 않으면 로컬 `uvicorn` 으로 같은 화면을 띄워 캡처하고 PDF 5장의 URL 자리를 "로컬 데모, 면접 시 시연"으로 대체한다(배포 02 §9). 배포 실패가 PDF 제출을 막지 않는다.
- **D-14 (다운타임 실측 기록):** 재배포 시 정지→시작 사이 다운타임을 한 번 측정해 기록한다. PDF 3장 "컨테이너 1개" 주장의 운영 현실을 보여주는 숫자다.

### Claude's Discretion
- Sentry 초기화 위치(`app/server.py` 최상단 vs `create_app` 앞)와 `environment` 태그 값.
- 로컬 docker 스모크 스크립트를 `Makefile` 타깃(`docker-smoke`)으로 만들지, 문서의 명령 나열로 둘지.
- UptimeRobot 모니터 이름·알림 채널.
- 배포 검증 curl 묶음을 `/deploy-demo` 스킬의 `check` 단계로 흡수할지.

### 사용자 몫 (코드 밖 — 계획은 여기서 멈춘다)
- Railway Hobby 결제(카드) + Usage Limit $15/월 + 알림 이메일
- New Project → Deploy from GitHub `ShinWon-Chul/millie-rec` → Dockerfile 자동 감지 확인
- Volumes → `/data` 1GB · Variables → `DATA_DIR=/data`(+ Day 4에 `SENTRY_DSN`)
- Settings → Networking → Generate Domain → URL 기록
- UptimeRobot 모니터 추가(URL 생성 후) · Sentry 프로젝트 생성 → DSN 보관

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 배포 절차 (실행 정본)
- `../.assets/설계서/시스템 아키텍처, 기술 스택 및 배포(프론트, 백엔드 서빙)/02_배포_절차_및_설정.md` — §1-0 사용자 체크리스트 A/B 묶음 · §1-4 시크릿 · §2 배포 파일 3종 · §3 스켈레톤 배포(§3-1 프로젝트 생성 · §3-2 검증 · §3-3 UptimeRobot·Sentry · §3-4 완료 기준) · §4 본배포(§4-1 코드 전제 · §4-2 로컬 docker 스모크 · §4-3 배포 · §4-4 검증 체크리스트) · §5 운영 · §6 롤백 · §7 장애 대응표 · §9 실패 시 대체 경로
- `../.assets/설계서/시스템 아키텍처, 기술 스택 및 배포(프론트, 백엔드 서빙)/01_시스템_아키텍처_기술스택_배포.md` — §5 배포 · §6 비용 · §7 런북 · §9-3 serving 파일 분할(2026-09-06 실측 갱신)

### 규칙
- `../.claude/rules/local-run.md` — 배포는 로컬 통과 후에만 · `make smoke` 선행
- `../.claude/rules/serving.md` — Dockerfile 3조건 · 환경변수 · 숫자 규칙(p95는 로컬 bench만)
- `../.claude/rules/data.md` — 표지 이미지·밀리 텍스트 공개 금지(D-07의 근거)
- `../.claude/rules/codex-review.md` — `Dockerfile`·`railway.json`·배포 직전은 Codex **필수** 리뷰
- `../.claude/rules/references.md` — 이름 + 경로 병기

### 앞 페이즈 결정
- `.planning/phases/05-must/05-CONTEXT.md` — D-13(Should 범위·`/metrics` 설계만) · D-18(완료 형태)
- `.planning/phases/05-must/05-VERIFICATION.md` — Phase 5 goal 검증 passed(배포 대상 서버의 상태)
- `.planning/phases/06-demo-rebuild/06-CONTEXT.md` — D-09(api 완주는 Phase 7 게이트) — **본배포 검증이 Phase 6 완료 판정을 겸한다**
- 개발일지 `../.assets/개발일지/` — 결정 '배포 = Railway Hobby 유료'(2026-09-03 파일 항목 D3) · 결정 '사용자 체크리스트 두 묶음'(2026-09-05 파일 항목 D54) · 결정 'Should 꼬리…'(2026-09-06 파일 항목 D76, D-04가 부분 번복) · 결정 'Codex 교차검증 반영'(2026-09-06 파일 항목 D79)

### 수용 기준
- `.planning/ROADMAP.md` "### Phase 7: 배포" — Success Criteria 4개 · DEPLOY-01~04
- `.planning/REQUIREMENTS.md` — DEPLOY-01·02·03(Must) · DEPLOY-04(Should, **D-05로 폐기**)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `Dockerfile`(13줄): v2.1 사양과 **일치**. `uv sync` 두 번 · `USER` 없음 · `ENV DATA_DIR=/data` · `CMD … --port ${PORT:-8000} --workers 1`. 재구성 대상 없음.
- `railway.json`: healthcheck `/health`(timeout 120) · `restartPolicyType ON_FAILURE`(3회) · `numReplicas 1`. 그대로 사용.
- `.dockerignore`: `.venv`·`.git`·`data/raw|processed|local`·`artifacts/*` 제외 + `!artifacts/serving` 예외. 이미지에 들어갈 것만 남는다.
- `app/server.py`(38줄): 주입 + StaticFiles. Sentry 초기화 3줄이 들어갈 유일한 자리(Advisor 전용).
- `Makefile`: `serve`·`smoke`·`bench` 존재. docker 스모크 타깃은 없다.
- `/health` 응답: `status·api_version·model_version·artifacts_loaded_at·db_ok·db_row_count·nearline_last_run·uptime_s` — 볼륨 영구성 확인(`db_row_count`)과 UptimeRobot 감시가 같은 엔드포인트로 된다.

### Established Patterns
- 외부 연동은 환경변수가 없으면 비활성(`../.claude/rules/local-run.md`). Sentry도 이 패턴을 따른다.
- 의존성 추가는 Advisor 승인 + `PROGRESS.md` 기록(`../.claude/rules/simplicity.md`). `sentry-sdk` 가 이 페이즈의 유일한 추가다.
- 커밋은 사용자 승인 후. push = 자동 배포이므로 push는 별도 승인.

### Integration Points
- `origin/main` push → Railway 빌드 → healthcheck `/health` → 도메인. 현재 `main` = `20d5fa3`, 원격과 동기.
- `artifacts/serving/` 5파일 31MB가 이미지에 포함된다 — 빌드 시간·이미지 크기의 주 요인.
- Phase 6이 `demo/` 를 갱신하면 같은 이미지에 실려 본배포에서 화면이 바뀐다.

</code_context>

<deferred>
## Deferred Ideas

- **`GET /metrics`·Grafana Cloud scrape** → 폐기(D-05). DEPLOY-04 종료.
- **커스텀 도메인** → 안 함(DNS 전파가 일정 리스크, 배포 02 §1-0 "하지 말 것").
- **Railway CLI 설치** → 안 함(대시보드로 충분).
- **오토스케일링·피크 용량·K8s** → 설계만(main 설계서 §7, PDF 3장 문장).
- **`GET /api/admin/export`(Could)** → 안 함(05-CONTEXT Deferred 유지).
- **다중 리전·CDN** → 범위 밖.

### Reviewed Todos (not folded)
없음 — `todo match-phase 7` 결과 0건.

</deferred>

---

*Phase: 07-deploy*
*Context gathered: 2026-09-06*
