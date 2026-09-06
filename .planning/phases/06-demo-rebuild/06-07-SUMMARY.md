---
phase: 06-demo-rebuild
plan: 07
wave: 4
executed_by: Advisor (오케스트레이터 세션)
date: 2026-09-06
commits: 0
code_changed: false
---

# 06-07 실행 요약 — 전역 게이트 · Advisor 실측 · 인계

전체 결과는 `06-VERIFICATION-NOTES.md`(12절)에 있다. 이 문서는 그 요약이다.
**코드 0줄 수정 · 커밋 0건.** 게이트 실패를 소유 플랜에 되돌리는 것이 이 플랜의 유일한 권한인데,
되돌릴 것이 없었다.

## 게이트 결과

| 게이트 | 결과 |
|---|---|
| 구 형태 grep (`demo/` 전체) | **0건** |
| `/contract-sync` 6항 | 전부 ✅ · mock 10 + `fallback/popular.json` = `model_validate` **11/11** |
| `uv run pytest --no-header` | **529 passed**, failed 0 |
| `uv run pytest tests/demo` | 10 passed |
| `uv run ruff check demo/scripts tests/demo` | All checks passed! |
| `make smoke` | PASS (`/health` · `/` · `/api/recommend` 전부 200) |
| `wc -l` 250줄 상한 | 초과 0 (최대 `mock.js` 249 · `router.js` 28) |
| `node --check` demo JS 전 파일 | 실패 0 |
| `innerHTML` in `demo/js/screens` · `href="javascript` | 0 · 0 |
| `codegraph sync .` | Done |
| 색 리터럴 (`tokens.css` 밖) | 16건 잔존 — `base.css` 7 · `onboarding.css` 9 (Should, 수용 판단 기록) |

## Playwright mock 완주 (DEMO-09 판정)

```
17/17 OK · console_error=0 · pageerror=0 · 404=0 · shots=12
```

쇼케이스 `#/` → 취향 설정 → 메인 → 책 상세 → 뷰어(10분 읽기 2회 · 완독 · 별점) → 홈
`after_completion` → 내 서재 → 취향 재설정 → 타임라인 2 → 내 데이터 열람 → 동의 철회 →
비개인화 2행 → 관제 대시보드 → D8 프리셋 3종. `?capture=1` 에서 상단바·인스펙터 숨김,
`?capture=2` 에서 인스펙터 유지를 단정으로 확인했다.

첫 실행의 실패 2건은 앱이 아니라 검증 스크립트의 셀렉터 문제였다 —
`data-act="closeModal"` 이 모달 배경 div 와 닫기 button 양쪽에 붙어 있어 `.first` 가 배경을
잡았다. `demo/` 는 고치지 않고 스크립트를 좁혀 17/17 이 됐다.

## api 모드 관측 (완주 판정 아님)

uvicorn 8022, 읽기 경로만. 요청 61건 중 **비-2xx 0건**, 콘솔 에러 0, pageerror 0.
플랜은 "아직 없는 엔드포인트가 404" 를 전제했으나 Phase 5 '서빙 Must 완성' 이 12개 라우트를
전부 등록한 뒤라 404 목록이 비었다. `?source=api` 완주는 06-CONTEXT D-09 대로
Phase 7 '배포' 사전 게이트로 남는다.

## DEMO-01~09

9개 전부 ✅. 두 건에 단서가 붙는다.
- **DEMO-05** — 배지는 6종 중 5종이 mock 에서 실제로 렌더된다. `light`("가볍게")는 범위 4분류
  Should 라 생성기가 만들지 않고, CSS 는 준비돼 있어 서버가 내려주면 그려진다.
  PDF 문장은 "6종 중 5종 실측" 으로 쓴다.
- **DEMO-09** — mock 완주로 판정한다. api 완주는 Phase 7 로 이관(06-CONTEXT D-09).

## 캡처

스크래치패드 `pw_demo06/shots/` 12장(`device_scale_factor=2`), 화면 02 §7 캡처 계획 6항목을
모두 덮는다. **repo 반입 0** — `git status --short | grep -ci png` = 0.
`report/figures/` 복사와 밀리 표지 공개 판단은 Phase 8 'PDF 제출물' 몫이고,
Phase 5 커밋 `20d5fa3` 가 `.gitignore` 에 `report/figures/` 제외를 이미 넣었다.

## 재위임 · 인계

**재위임 0건.** 06-06 이 올린 관측 6건과 06-05 가 올린 계약 관측 1건은 전부 Advisor 판단으로
종결하거나 `PROGRESS.md` 미결로 이관했다(`06-VERIFICATION-NOTES.md` §8).

`PROGRESS.md` append 3건(기존 줄 무수정):
- 항목 12 — `/contract-sync` 에 `serving/onboarding_meta.json` ↔ `demo/config/onboarding.json`
  텍스트 동일성 검사를 항목 7로 추가하자는 제안
- 항목 13 — `LibraryBook`·`ShowcaseBook` 에 `authors` optional 추가 검토(내 서재·쇼케이스에서
  저자 병기 불가, 현재 "저자 미상")
- Phase 6 검증 결과 1줄 — Phase 5 후속 ⑦(`inspector.js` `static_popular`) 해소 기록 포함

플랜이 지시한 나머지 2건(Makefile `mock` 타깃 · REQUIREMENTS DEMO-09 문구)은 **이미 항목 11b·11
로 존재**해 중복 추가하지 않았다.

## 플랜과 달랐던 점

1. **api 관측 포트 8000 → 8022.** Phase 5 세션이 같은 시간에 서버를 쓰고 있어 충돌을 피했다.
2. **`no_commit: true` frontmatter.** 이 플랜은 지시대로 커밋 0건이지만, Phase 6 전체로 보면
   06-01~06-06 이 원자 커밋 20건을 남겼다. 플래그는 2026-09-05 "사용자 승인 대기" 뜻으로
   붙었고, 승인이 09-06 에 도착했다 — `PROGRESS.md` 결정 로그 D80 "Phase 1~5 249파일
   `20d5fa3` 커밋·push(main 전체, **Phase 6 커밋 21개 동반 공개 승인**)". 플래그가 무효가 된
   것이지 위반이 아니다.
3. **Codex 교차검증 생략.** `../.claude/rules/codex-review.md` 표에서 `demo/`·문서는 생략 행이고,
   이 페이즈의 `src/**` 변경이 0이다(`git status --short src | wc -l` = 0).
4. **`grep -c '[제안·Phase 6 세션]'` == 2 라는 수용 기준.** 파일의 기존 표기는
   `(제안 — Phase 6 세션, 09-06)` 형식이라 그 관례를 따랐다. 현재 4건이 있다(11b·11·12·13).

---

## ▶ Next Up

**Phase 6 '데모 재구성'(.planning/ROADMAP.md "Phase 6: 데모 재구성") 7개 플랜 실행·검증 완료 —
DEMO-01~09 전부 ✅, 재위임 0건.**

`/clear` 후:

`/gsd-verify-work 6` — Phase 6 '데모 재구성' 사람 UAT(캡처 12장 육안 확인 · mock 완주 재현)

**Also available:**
- `/gsd-plan-phase 7` — Phase 7 '배포'(.planning/ROADMAP.md "Phase 7: 배포"), 사전 게이트 =
  `make serve` + `?source=api` 쓰기 경로 포함 완주
- `/gsd-code-review 6` — `demo/` 소스 리뷰(프로젝트 규칙상 선택)
- `/gsd-progress` — 갱신된 로드맵 확인
