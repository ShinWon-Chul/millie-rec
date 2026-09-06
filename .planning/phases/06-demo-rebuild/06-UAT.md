---
status: resolved
phase: 06-demo-rebuild
source: [06-VERIFICATION.md, 06-VERIFICATION-NOTES.md, 06-HUMAN-UAT.md]
started: 2026-09-06
updated: 2026-09-06
---

## Current Test

[완료 — 3건 응답, Gap 1 수정·검증 종결. Phase 6 닫힘]

## Tests

### 1. 캡처 12장 육안 확인
expected: `<scratchpad>/pw_demo06/shots/` 12장이 화면 구성 02 §7 캡처 계획 6항목과 대응하고
PDF에 넣을 만한 상태다.
result: **passed** — 사용자 "승인합니다"(2026-09-06).

Advisor 확인 사항 1건을 함께 기록한다. `p4_dashboard.png` 는 최초 완주에서 동의 철회 **뒤에**
찍혀 세션 집계가 전부 0·fallback 100%·모델 분포 `fallback_v1` 하나인 빈 화면이었다. 세션 집계
대시보드로서는 정직하지만 PDF 그림으로는 아무것도 보여주지 못해, 철회 **전** 상태(온보딩 완주 +
2권 완독 + 별점 2건)에서 재캡처했다. 코드는 고치지 않고 캡처 시점만 옮겼다.
재캡처 KPI — QRS 100.0%(n=2) · 첫 완독 도달률 100.0%(n=1) · fallback 0.0%(n=3) · 이벤트 210건.
**Phase 8 주의: 대시보드 캡처는 반드시 철회 전에 찍는다.**

### 2. `LibraryBook`·`ShowcaseBook` 에 `authors` optional 추가 여부
expected: 계약 Day 3 freeze 의 예외를 열지 결정한다. 현상 — 내 서재(#/library) 담은 책 5권과
쇼케이스 본인 5권에 저자가 "저자 미상" 으로 뜬다.
result: **issue** — 사용자 "저자가 나올 수 있도록 해야합니다. UI 완성도에 영향을 줄 수 있을
것 같습니다. `/src` 수정을 승인하며, 다른 세션에서도 알 수 있도록 개발일지에 기록합니다."
(2026-09-06). → Gap 1 로 진단, `06-08-PLAN.md` 로 수정 위임.

### 3. 배지 "6종 설계 · 5종 실측" PDF 문구 승인
expected: `light`("가볍게") 는 범위 4분류 Should(`light_start`) 라 생성기가 만들지 않는다.
숨은 결함이 아니라 의도된 미구현이며, PDF 문구를 "6종 설계 · 5종 실측" 으로 쓴다.
result: **passed** — 사용자 "승인합니다"(2026-09-06).
실측 렌더 건수(06-06 S3 기준별 완주) — `author` 7 · `publisher` 8 · `bestseller` 43 ·
`buzz` 34 · `review`(3단 폴백 포함) 39.

## Summary

total: 3
passed: 3
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

### Gap 1 — 서재·쇼케이스에서 저자가 표시되지 않는다
status: resolved
plan: 06-08-PLAN.md

**증상.** `#/library` 담은 책 5권과 `#/` 쇼케이스 본인 5권의 저자 자리가 전부 "저자 미상"이다.
같은 카탈로그를 쓰는 메인(`d2_home.js`)·상세(`d3_detail.js`)·뷰어(`d4_reader.js`)는 저자가
정상 표시된다 — 이 셋은 `ItemOut.authors` 를 직접 읽는다.

**근본 원인.** 두 응답 모델에 저자 필드가 없다.
- `src/millie_rec/serving/schemas.py:239` `LibraryBook` = `book_id` · `title` · `image_url`
- `src/millie_rec/serving/schemas_should.py:75` `ShowcaseBook` = `book_id` · `title` ·
  `image_url` · `reason` · `badge`

두 모델 모두 `_Strict` 기반이라 여분 키를 넣을 수 없다. 그래서 화면이 우회했고, 그 우회가
시드 5권에서만 실패한다 — `d5_library.js:26` `authorOf()` 는 `state.recommend.rows` 에서
같은 `book_id` 를 찾는데, 시드 5권은 dedup `exclude` 대상이라 추천 행에 실리지 않는다.
`d8_showcase.js:52` 는 아예 저자를 포기하고 `book_id N` 을 병기했다.

**데이터는 이미 있다.** `artifacts/serving/books_kr.json` 원소에 `authors` 가 있고
(`['book_id','title','authors','image_url', …]` 28키), `CatalogKR.meta()`
(`src/millie_rec/data/catalog_kr.py:73`) 는 그 dict 를 통째로 돌려준다. 서버 쪽 손실 지점은
`privacy_api.py:25` 의 `BOOK_KEYS = ("title", "image_url")` 한 줄뿐이다.
`demo/mock/catalog_kr.json` 도 16키 중 세 번째가 `authors` 다.

**계약 freeze 판단.** `.claude/rules/architecture.md` "필드 추가는 기본값 있는 optional 로만"
을 지키는 `authors: str | None = None` 추가라 freeze 규칙 안에 있다. 사용자 승인 2026-09-06,
개발일지 D81 기록.

**영향 범위 (7파일).** 계약 2 · 서버 1 · demo 4 + 테스트.
`src/**` 는 평소 Phase 5·7 세션 소유라 이번에만 사용자 승인으로 이 세션이 편집한다.

**해소 (2026-09-06, `06-08-PLAN.md` · 커밋 `aa73286`~`fee6b19` 6건).**
계약 2줄(`LibraryBook`·`ShowcaseBook` 각 `authors: str | None = None`) · `privacy_api.py`
`BOOK_KEYS` 에 단어 1개 · demo 4곳(`make_mock.py` 2곳 · `mock.js` · `d5_library.js` ·
`d8_showcase.js`). `src/` 변경은 승인받은 3파일 밖으로 새지 않았다.

Advisor 검증 실측 — `uv run pytest` 529 → **534 passed, failed 0** · ruff clean ·
`/contract-sync` **11/11** 유지(여분 키 0) · `make smoke` PASS · 생성기 재실행 시
`showcase.json`·`state.json`·`catalog_kr.json` md5 불변(결정성 유지) · 구 형태 grep 0 ·
250줄 상한 초과 0.

화면 실측(Playwright, `<scratchpad>/pw_demo06/authors_result.json`) —
쇼케이스 `.case__author` 15칸 전부 실제 저자(예: `헤르만 헤세 / 박병덕 옮김`,
`빅터 프랭클 / 이시형, 김혜림 옮김`), 서재 `.tile__author` 5칸 전부 실제 저자
(`채사장` · `이미예` · `비욘 나티코 린데블라드 …` · `김호연` · `김호연`).
**"저자 미상" 0건 · `book_id` 폴백 0건 · 콘솔 에러 0 · pageerror 0.**
`p4_showcase.png` · `p3_library_timeline.png` 재캡처 완료.

개발일지 D81 기록(`../../../../.assets/개발일지/2026-09-06_Day2_Phase4_파이프라인과_freeze.md`).
