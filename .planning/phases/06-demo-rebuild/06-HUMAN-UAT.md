---
status: resolved
phase: 06-demo-rebuild
source: [06-VERIFICATION.md, 06-VERIFICATION-NOTES.md]
started: 2026-09-06
updated: 2026-09-06
---

## Current Test

[완료 — 3건 모두 응답 수령(2026-09-06). 상세 결과는 06-UAT.md]

## Tests

### 1. 캡처 12장 육안 확인

expected: `<scratchpad>/pw_demo06/shots/` 12장이 화면 구성 v2 §7 캡처 계획 6항목과 대응하고,
PDF에 넣을 만한 상태다. Advisor가 3장(`p3_home_badges_anchor` · `p4_showcase` · `p4_dashboard`)을
직접 열어 확인했고 나머지 9장은 완주 로그로만 확인했다.
특히 볼 것 — `p4_showcase.png`에 비교표 4행·`split_mode: holdout`·본인 5권→추천 10권,
`p3_home_badges_anchor.png`에 배지와 『…』을 좋아하셨다면 앵커 행, `p4_dashboard.png`에
QRS 100%(n=2)·첫 완독 100%(n=1)·fallback 0%.
result: **passed** — 사용자 "승인합니다".

### 2. `LibraryBook`·`ShowcaseBook`에 `authors` optional 추가 여부

expected: 계약 Day 3 freeze의 예외를 열지 말지 결정한다.
현상 — 내 서재(#/library) 담은 책 5권과 쇼케이스 본인 5권에 저자가 "저자 미상"으로 뜬다.
두 스키마에 저자 필드가 없고, 시드 5권은 dedup `exclude`로 추천 행에 실리지 않아 조회할 곳이 없다.
동작에는 문제가 없다 — 라우팅·dedup은 `book_id`로 하고, 동명 도서('도슨트북' 2권)도 구분된다.
영향은 PDF 캡처 품질뿐이다.
반영할 경우 — `serving/schemas.py` `LibraryBook` + `schemas_should.py` `ShowcaseBook`에
`authors: str | None = None` 추가(기본값 있는 optional만 허용, `.claude/rules/architecture.md`),
그 뒤 `make_mock.py` `card()` · `mock.js` · `d5_library.js` · `d8_showcase.js` 각 1줄.
`src/**`는 Phase 5 세션 소유라 이 세션이 직접 고치지 않았다. `PROGRESS.md` 미결 13번.
result: **issue → resolved** — 사용자 "저자가 나올 수 있도록 해야합니다. /src 수정을 승인". `06-08-PLAN.md` 로 종결(06-UAT.md Gap 1).

### 3. 배지 "6종 중 5종" PDF 문구 승인

expected: `light`("가볍게") 배지는 범위 4분류 Should(`light_start`)라 생성기가 만들지 않는다.
CSS는 `home.css`에 준비돼 있어 서버가 내려주면 즉시 그려진다. 숨은 결함이 아니라 의도된 미구현이다.
06-06이 S3 기준별로 완주해 실측한 렌더 건수 — `author` 7 · `publisher` 8 · `bestseller` 43 ·
`buzz` 34 · `review`(3단 폴백 포함) 39.
PDF에 "배지 6종" 대신 "6종 설계 · 5종 실측"으로 쓰는 문구를 승인한다.
result: **passed** — 사용자 "승인합니다".

## Summary

total: 3
passed: 3
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

(자동 검증에서 발견된 차단 갭 없음 — `06-VERIFICATION.md` 9/9 musts verified,
`06-VERIFICATION-NOTES.md` §8 재위임 0건)
