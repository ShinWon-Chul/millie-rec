---
phase: 07-deploy
plan: 02
wave: 2
status: complete
commits: 68cef80..79b8e63 push 4회(07-01 17커밋 · 빈 커밋 3개 = 재배포 트리거)
executed: 2026-09-06
executor: Advisor 직접(조립 레인 — push·curl 검증·기록. 코드 0)
task1_started: "2026-09-06 12:52 KST"   # 90분 규칙(07-CONTEXT D-13) 기준 시각 → 14:22 KST 까지 /health 200
push: "20d5fa3..2d7df0a  main -> main"(17 커밋)
---

# 07-02 스켈레톤 배포 — 실행 요약

Phase 7 '배포'(`.planning/ROADMAP.md` "### Phase 7: 배포") wave 2. 결정 '스켈레톤을 지금 한다'
(`.planning/phases/07-deploy/07-CONTEXT.md` D-01) — 빌드·볼륨·도메인 리스크를 Day 4 이전에 드러낸다.

## Task 1 — push 승인 → push → 사용자 B 묶음

### 자동 부분

| 검사 | 결과 |
|---|---|
| 07-01 커밋 로컬 존재 | ✅ `68cef80`(코드) · `ec1a007`(SUMMARY) · `2d7df0a`(STATE·ROADMAP) |
| `uv run pytest tests/app --no-header` | ✅ 34 passed |
| `make smoke` | ✅ PASS |
| 미커밋 코드 변경 | `results/millie_edges_gate.json` 1건 — `generated_at` 타임스탬프만(Phase 6 세션 산출물). 미커밋이라 push 에 안 섞임 |
| GitHub 인증 | ✅ `ShinWon-Chul` |

### 사용자 몫 정리 문서 (사용자 질문 "정리된 문서가 있나요?")

정본 = 배포 절차서 §1-0 "사용자 체크리스트 — 두 묶음"(`../.assets/설계서/시스템 아키텍처, 기술 스택 및 배포(프론트, 백엔드 서빙)/02_배포_절차_및_설정.md`,
결정 '사용자 체크리스트 두 묶음'(개발일지 2026-09-05 파일 항목 D54)) + §3-1(프로젝트 생성 7단계) ·
§3-3(UptimeRobot·Sentry) · §3-4(완료 기준). `07-02-PLAN.md` Task 1 how-to-verify 가 인라인. 이 턴에서
A/B/C 세 묶음으로 사용자에게 전문 제시.

### push (사용자 "push ok — A 묶음 완료", 2026-09-06 12:52 KST)

```
To https://github.com/ShinWon-Chul/millie-rec.git
   20d5fa3..2d7df0a  main -> main
```

범위 17 커밋 = 이 세션 3(07-01) + Phase 6 세션 14(06-06~06-08: feat 4 · test 2 · chore 1 · docs 7).
`authors` optional 계약 변경(`c0dc39a`) 포함 — 사용자에게 고지 후 승인. push 시점에 Railway 프로젝트가
없으므로 이 push 는 GitHub 만 바꿨다. `git rev-list --count origin/main..HEAD` = **0**.

### 사용자 B 묶음 (진행 중)

Hobby 결제 → Usage Limit $15 → New Project(Deploy from GitHub `millie-rec`, Dockerfile 감지) →
Settings(Region · Generate Domain · `/health` · App Sleeping OFF) → Volume `/data` 1GB →
Variables `DATA_DIR=/data` → 첫 빌드 로그.

사용자 캡처로 확인(13:00 KST): 프로젝트 `efficient-ambition` · 서비스 `millie-rec` Online · Dockerfile
Automatically Detected · Region Southeast Asia(Singapore) · 1 Replica · `DATA_DIR=/data` · 첫 빌드
**Deployment successful**(대상 커밋 `2d7df0a` = push 직후 최신 main, healthcheckTimeout 120 안에 통과).

**Q&A 2건(사용자 질문):** ① "왜 8080 포트?" — Railway 가 컨테이너에 `PORT` 를 주입하고 Dockerfile
`CMD … --port ${PORT:-8000}` 이 그 값을 쓴다. 8000 은 로컬 fallback. 도메인 target port = 주입된 PORT(8080)
이어야 하며 8000 으로 바꾸면 502. ② Deploy 절의 Healthcheck Path 공란·재시작 10 회 표시 — `railway.json`
(config-as-code) 가 대시보드 값보다 우선해 폼에 반영되지 않는 것. 손댈 것 없음, Config-as-code 절에서
파일 인식만 확인.

**BASE = `https://millie-rec-production.up.railway.app`** (edge `sin1`, `server: railway-hikari`)

## Task 2 — 배포 URL 검증 (배포 02 §3-2) — 전부 기대값 ✅

| 검사 | 기대 | 실측 |
|---|---|---|
| `GET /health` | 200 · `status ok` · `db_ok true` · `model_version` 비-null | **200 (0.43s)** · ok · true · `hybrid_div_v1` · `api_version v2` · `artifacts_loaded_at 2026-09-06T03:53:21Z` · `nearline_last_run 2026-09-06T04:06:51Z`(Nearline 루프 가동 중) |
| `GET /` · `/?source=mock` · `/?source=api` | 200 ×3 | **200 · 200 · 200** |
| `GET /docs` | Swagger HTML | `<!DOCTYPE html>` ✅ |
| `GET /api/recommend?seeds=1,2,3,4,5&k=5` | 200 | **`fallback_level 0` · `hybrid_div_v1` · rows `["trending"]` · 5 items** · `latency_ms 144.4`(참고값 — PDF 미사용, D-12) |
| `GET /api/showcase` | `split_mode holdout` · rows 4 | **holdout · 4** |
| `POST /api/preferences`(표식 행 `probe-volume-20260906`) | 200 · users ≥1 | ✅ `preference_snapshot_id` 발급 · **`users_before_restart = 1`** (`preference_snapshots 1 · events 5 · recommendations 1`) |

D-09(아티팩트를 이미지에 굽는다) 실증 — `model_version` 이 로컬 `/health` 와 같은 `hybrid_div_v1`.
STATE.md: Deploy 줄 1행 추가 · Day 게이트 2행 `/health` 200 ✅ · 볼륨 ⬜(Task 3).

## Task 3 — 볼륨 검증 · UptimeRobot · 다운타임 실측 — 통과 ✅ (우회 2건 · 오판 1건 정정)

### 발견 1 — `railway.json` 이 Railway 에서 무효다 (계획 전제 붕괴)

사용자 캡처(Settings → Config-as-code): *"Config as Code is deprecated … Starting 2026-08-28, services
that have never used Config as Code cannot opt in."* 서비스가 2026-09-06 생성이라 옵트인 불가 →
`healthcheckPath /health` · `restartPolicyMaxRetries 3` · `numReplicas 1` 이 **전부 미적용**. 대시보드 폼이
Healthcheck 공란·재시작 10회로 보인 이유가 "파일 우선"이 아니라 "파일 무효"였다(Advisor 의 첫 설명은
틀렸고 같은 턴에 정정). 조치: 사용자가 Settings → Deploy → Healthcheck Path 에 `/health` 수동 입력 →
Deploy 배너로 적용. 재시작 횟수 10 은 유지(3 보다 많아 무해). **07-04 에서 배포 02 §2-3·07-CONTEXT D-11
정정 + `railway.json` 처분(삭제 또는 "레거시" 주석) 결정 필요.** 첫 배포 "successful" 은 헬스체크 없이
프로세스 기동만 본 결과였다.

### 발견 2 — UptimeRobot 기본 HEAD 요청을 FastAPI `@app.get` 이 404 로 거절

Deploy Logs 의 `"HEAD /health HTTP/1.1" 404 Not Found` 반복 = UptimeRobot. `curl -I` 로 재현(404, GET 은 200).
HTTP method 를 GET 으로 바꾸는 옵션은 유료. **무료 우회 = Monitor type Keyword**(GET 으로 본문 검사,
keyword `"status":"ok"`, alert when not exists, 5분). 구 HTTP 모니터 삭제 → 그 모니터를 담고 있던 상태 페이지
`qogHCGSz4O` 가 비어 Edit 불가 → 삭제 후 재생성 **`https://stats.uptimerobot.com/20M6QwPo7z`**(모니터
`millie-rec` 담김 확인). 대안으로 검토한 `HEAD /`(StaticFiles 는 HEAD 200) 는 프로세스 생존만 보므로 기각.
코드로 HEAD 를 받게 하는 건 `serving/api.py` must_not_touch 라 하지 않았다 — 07-03/04 에서 결정 후보.

### 발견 3 — "Restart 후 데이터 유지" 는 볼륨 증거가 아니었다 (Advisor 오판 정정)

Restart 직후 `users 1` 유지를 보고 "볼륨 영구성 ✅" 라 판정했으나, 이후 **재배포에서 `users 0` 으로 초기화**.
Railway Restart 는 같은 컨테이너 파일시스템을 유지하고 프로세스만 재기동하므로 임시 파일도 살아남는다.
실제로는 **볼륨이 붙어 있지 않았다**(캔버스 첫 캡처에 볼륨 블록 없음 · Variables 에 `RAILWAY_VOLUME_*` 없음 ·
사용자가 "5. 완료"로 보낸 캡처는 Variables 화면). 사용자가 캔버스에서 Volume 생성 → `millie-rec` 에 `/data`
로 부착 → Deploy 배너 적용(13:53). 이후 `Backups` 탭이 생김(볼륨 서비스 표식).
**교훈(배포 02 §3-2 정정 대상): 볼륨 검증은 Restart 가 아니라 재배포(push) 로 한다.**

### 실측 — 재배포 다운타임(D-14) · 영구성

| # | 시각 | 트리거 | 볼륨 | 폴링 결과(5초 간격) | 다운 추정 | 재배포 후 `users` |
|---|---|---|---|---|---|---|
| 1 | 13:44 | 빈 커밋 push `18450fd` | ✗ | 502 ×1 | **5~11초** | 1 → **0**(휘발) |
| 2 | 13:49 | 빈 커밋 push `5cb8f94` | ✗(설정만) | 502 ×1 | 5~11초 | 1 → **0**(휘발) |
| 3 | 13:53 | 볼륨 부착 Deploy | 부착 중 | **404 ×6** | **30~40초** | — |
| 4 | 13:55 | 빈 커밋 push `79b8e63` | ✅ | 연결끊김 ×1 | **5~15초** | **1 → 1 · snapshots 1 · events 5 유지 ✅** |

PDF 3장 문장 후보: "단일 컨테이너 재배포 다운타임은 5초 폴링에서 1표본 실패(≈10초 내외), 볼륨을 처음 붙이는
재배포만 30~40초." 빌드는 레이어 캐시로 40초 내 완료(빈 커밋 기준). 원자료 `poll_health_run1.csv`·
`poll_health.csv`(스크래치패드, repo 밖).

### 완료 기준(배포 02 §3-4) 대조

| 기준 | 결과 |
|---|---|
| `/health` 200 · `db_ok true` | ✅ |
| `/`·`/?source=mock` 200 | ✅ (콘솔 에러 0 은 07-03 Playwright 게이트) |
| Restart 후 볼륨 데이터 유지 | ✅ — **재배포 후** 유지로 상향 검증(#4) |
| 재배포 다운타임 실측 기록 | ✅ 위 표 · STATE Downtime 줄 |
| UptimeRobot 모니터 활성 | ✅ Keyword · 상태 페이지 `20M6QwPo7z` |
| URL·리전·볼륨·다운타임 기록 | ✅ STATE.md Deploy/Monitor/Downtime 3줄 (PROGRESS·개발일지는 07-04) |

### 07-03 인계

- `SENTRY_DSN` 은 사용자가 보관 중(값은 어떤 파일에도 쓰지 않음 · `ingest.us.sentry.io` 리전). 07-03 Task 2 에서 Variables 투입 + push 1회.
- `.planning/**` 문서 커밋은 **로컬에만** 둔다 — push 하면 재배포(≈10초 다운) 가 한 번 더 일어난다. 07-03 push 에 동반.
- 새 배포의 Details → Configuration → Deploy 에 `Healthcheck path /health` 표시 여부는 사용자 확인 미수신 — 07-03 Task 1 체크리스트에 포함.
- 07-03 freeze 무변경 검사(`authors` optional 예외) · 07-04 D81→D82 정정은 07-01-SUMMARY 기록 그대로.
