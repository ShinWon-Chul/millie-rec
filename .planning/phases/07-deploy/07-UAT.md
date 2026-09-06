---
status: complete
phase: 07-deploy
source: [07-01-SUMMARY.md, 07-02-SUMMARY.md, 07-03-SUMMARY.md, 07-04-SUMMARY.md]
started: 2026-09-06T07:55:00Z
updated: 2026-09-06T08:25:00Z
---

## Current Test

[testing complete]

## Tests

### 1. 콜드 스타트 스모크(로컬)
expected: millie-rec/ 에서 실행 중인 서버를 모두 끄고 `make smoke` → `smoke: PASS`(3개 200) 후 서버 자동 종료. `uv run pytest --no-header` failed 0(574 passed).
result: pass

### 2. 배포 URL 헬스체크
expected: 브라우저에서 https://millie-rec-production.up.railway.app/health 를 열면 JSON 에 `"status":"ok"`, `"db_ok":true`, `"model_version":"hybrid_div_v1"`, `"api_version":"v2"` 가 보인다. https://millie-rec-production.up.railway.app/metrics 는 404.
result: pass

### 3. 배포 데모 완주(api 모드)
expected: https://millie-rec-production.up.railway.app/?source=api 에서 쇼케이스(비교표 4행·split_mode 표기) → "신규 유저로 체험하기" → 취향 설정 7단계(5권 선택) → 메인(앵커 행 "『○○』을 좋아하셨다면" + 배지·reason) → 카드 → 책 상세 → 바로 읽기 → 뷰어(10분×2·완독·별점) → 메인에 "다음은" 행 → 내 서재 → 관제 대시보드 까지 이동되고, 개발자도구 콘솔에 빨간 에러가 0건이다. 상단 표시 model_version 은 hybrid_div_v1.
result: pass

### 4. "신규 유저로 체험하기" — 이전 데이터가 남지 않는다
expected: 3번을 끝낸 브라우저에서 쇼케이스(#/)로 돌아가 "신규 유저로 체험하기" 를 다시 누르면 취향 설정 첫 화면(S0 시작)이 뜨고, 새로 완주한 메인에는 직전 사용자의 "다음은"(after_completion)·이어 읽기 행이 없다. 인스펙터의 user_key 도 새 값이다.
result: pass

### 5. 철회 뒤 별점은 저장되지 않는다(Codex C3)
expected: 내 서재 → 맞춤 추천 동의 철회 → 확인 후 메인에 "비개인화 인기 도서" 배너가 뜬다. 그 상태에서 카드 → 뷰어 → 완독 → 별점을 눌러도 화면은 정상 진행되고(토스트 "다음 책을 준비하고 있어요"), 콘솔에는 빨간 에러가 아닌 `[api] HTTP 403` 경고 1줄만 남는다. 별점 모달이 다시 떠도 저장된 별점은 없다.
result: pass

### 6. UptimeRobot 감시
expected: UptimeRobot 대시보드에서 모니터 `millie-rec` 이 Up, Monitoring Interval 5 minutes, 마지막 체크가 5분 이내다. 공개 상태 페이지 https://stats.uptimerobot.com/20M6QwPo7z 가 열리고 모니터가 Up 으로 표시된다. (권고: 키워드를 `"status":"ok"` → `"db_ok":true` 로 바꾸면 DB 고장도 잡힌다.)
result: pass

### 7. 캡처 6장 + QR
expected: millie-rec/report/figures/ 에 p5_01_onboarding.png ~ p5_06_home_after.png 6장이 폰 프레임·2x 로 또렷하고 순서가 취향 설정(5권 선택) → 메인(앵커 행) → 책 상세 → 뷰어 완독 → 취향 재설정 → 메인 변화다. p5_qr.png 를 폰 카메라로 찍으면 배포 URL 로 열린다.
result: pass

### 8. 저작권 게이트 — repo 에 PDF·캡처·assets 없음
expected: millie-rec/ 에서 `git ls-files | grep -iE "pdf|png|assets"` 의 결과가 `demo/assets/brand/millie-mark.png` 1줄뿐이고(Phase 6.1 승인 자산), `git status --short -- report/figures` 가 빈 출력이다. GitHub `ShinWon-Chul/millie-rec` 에도 report/figures 가 없다.
result: pass

### 9. 볼륨 영구성 — 표식 이름 확인
expected: https://millie-rec-production.up.railway.app/api/users/probe-main-20260906/state 가 200 JSON(스냅샷·서재 정보)으로 열린다. 이 표식은 07-03(14:51)에 만든 것으로 이후 재배포 3회(14:54·16:20·16:34)를 거쳤다.
result: pass

## Summary

total: 9
passed: 9
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

[none yet]
