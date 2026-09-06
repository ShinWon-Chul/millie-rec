# Phase 6: 데모 재구성 - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-09-06
**Phase:** 6-데모 재구성
**Areas discussed:** mock 모드의 상태 시뮬레이션 깊이, 재구성 vs 재작성 경계, D8 쇼케이스의 정적 데이터 원천, Phase 5 대기 지점과 완료 판정

---

## mock 모드의 상태 시뮬레이션 깊이

| Option | Description | Selected |
|--------|-------------|----------|
| 밀리 카탈로그 위 브라우저 내 경량 시뮬레이션 | 스냅샷·완독 상태 변경, 재설정 시 새 시드 이웃으로 앵커 행 교체, after_completion 추가. 스코어링 없음 | ✓ |
| 시나리오 고정 스냅샷 (mock JSON N개) | 재설정 전/후·완독 전/후 응답을 미리 생성. 클릭 순서 고정 | |
| mock은 D1→D2 최소만, 나머지 api 전용 | D4~D7은 서버 필요 안내. DEMO-09와 충돌 | |

| Option | Description | Selected |
|--------|-------------|----------|
| make_mock.py가 축약본을 demo/mock/에 생성 | catalog_kr.json(카드 필드만 ≈2MB) + neighbors_kr.json(top-20). 설명문·리뷰 자동 제외 | ✓ |
| 같은 origin의 artifacts/serving/를 fetch | 생성 단계 없으나 서버 없으면 mock 불가, 27MB 로드, 설명문 노출 | |

| Option | Description | Selected |
|--------|-------------|----------|
| 이 보드가 직접 맞은 이벤트에서 집계 | sessionStorage 이벤트 → D7 집계. '데모 표본, 검정 안 함' 고지 | ✓ |
| 고정 예시 숫자 (부종 표기) | 그럴싸한 예시 JSON. '숫자는 results/만' 규칙과 긴장 | |
| mock에서는 D7 비활성 | 서버 연결 시 표시 안내만 | |

**User's choice:** 경량 시뮬레이션 · 축약본 생성 · 세션 이벤트 집계
**Notes:** "심사자가 mock으로 눌러봐도 가짜가 티나지 않아야 한다"는 방향. 스코어링은 이중 구현 금지로 배제, 이웃 테이블 조회만.

---

## 재구성 vs 재작성 경계

| Option | Description | Selected |
|--------|-------------|----------|
| app.js 새로 쓴다 — state+setState+render 구조만 계승 | S0~S8 선형 머신은 8페이지 라우터와 안 맞음. 패턴·유틸만 가져가고 router.js 추가 | ✓ |
| 증분 수정 — 기존 함수 유지, 라우터만 얹는다 | v2 §8 문구 그대로. 250줄 초과·구 형태 잔존 위험 | |

| Option | Description | Selected |
|--------|-------------|----------|
| mock.js 폐기 후 새로 | 상태 시뮬레이션 구조와 불일치. 배지 6종은 표시 규칙으로 JS에 둠 | ✓ |
| 배지 로직만 유지, 나머지 삭제 | 현재 배지 타입이 구 형태(rating)라 수정 필요 | |

| Option | Description | Selected |
|--------|-------------|----------|
| 구 mock 7개 + fallback/popular.json 전부 삭제, 밀리 기반 재생성 | DEMO-02·데이터 2트랙 규칙. Goodbooks 영문 제목 잔존 경로 0 | ✓ |
| fallback/popular.json만 유지 | 최후 보루 유지하나 Goodbooks 책이 한국 데모에 나올 수 있음 | |

**User's choice:** 전부 새로 (패턴만 계승) · 구 데이터 전부 삭제
**Notes:** 완료 기준에 구 형태 grep 0건(hf.space · "/recommend" · timestamp · "format" · "rating" · goodbooks).

---

## D8 쇼케이스의 정적 데이터 원천

| Option | Description | Selected |
|--------|-------------|----------|
| make_mock.py가 eval_table.json → demo/mock/showcase.json 복사 + api 모드 /api/showcase | 본인 5권 출력도 함께. Phase 5 전에도 실측 숫자로 뜸. 원천은 results/ 1곳 | ✓ |
| /api/showcase만, mock에서는 문구만 | Phase 5 전 스크린샷 불가 | |

**User's choice:** 복사 + api 모드 병행
**Notes:** 숫자 복사를 손으로 하지 않고 `make mock`이 한다.

---

## Phase 5 대기 지점과 완료 판정

| Option | Description | Selected |
|--------|-------------|----------|
| Phase 6 = mock 완주로 verify, api 완주는 Phase 7 사전 게이트로 이관 | 두 세션 독립 완료. DEMO-09 문구 1줄 수정을 Phase 5 세션에 제안 | ✓ |
| Phase 6 완료는 Phase 5 뒤로 | 요구사항 수정 없음. 병렬 이점 일부 상실 | |

**User's choice:** mock 완주 verify, api 완주 이관
**Notes:** REQUIREMENTS.md는 Phase 5 세션(Advisor) 소유 — 이 세션은 편집하지 않고 PROGRESS.md 미결에 제안.

---

## Claude's Discretion

router.js 구조·해시 매칭, D7·D8 PC 레이아웃 세부, 인스펙터 CSS, D4 "10분 읽기" 연출(T=15분 상수 표기 유지), `?capture` 구현, sessionStorage 키, mock 지연 상수, Worker wave 분할.

## Deferred Ideas

- REQUIREMENTS.md DEMO-09 분리 문구 → Phase 5 세션 제안
- `?source=api` 완주 게이트 → Phase 7 배포 전
- onboarding_meta.json ↔ config/onboarding.json 동일성 → Phase 5 후 `/contract-sync`
- 본인 5권 book_id 선정 → 사용자
