# Phase 2: Track A 정량 평가 기반 - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-09-05
**Phase:** 2-Track A 정량 평가 기반
**Areas discussed:** 평가 표본·분할 파라미터, n=0 vs n≥k 표 형태, pop 서버 주입 형태, ILD 벡터 시점

---

## 평가 표본·분할 파라미터

| Option | Description | Selected |
|--------|-------------|----------|
| 테스트 유저 2,000명(고정 seed) | 4 variant×2상태도 수 분 내, 표준오차 ≈±0.01, 재실행 부담 작음 | ✓ |
| 5,000명 | 오차 더 작음, Day 3 튜닝 루프에 10분 안팎 부담 | |
| 전체(필터 통과 유저 전부) | 표본 논란 없음, Day 3 모델은 수십 분 | |
| 유저별 20% test | 통상 설정, test 정답 0 유저 제외·수 기록 | ✓ |
| 유저별 30% test | 정답 많아지나 train 이력 감소 | |
| 유저별 고정 개수 test | 깊이 공정, 적은 유저는 train 소진 | |
| seeds = train 긍정(rating≥4) 중 무작위 5권 | 온보딩 "좋았던 책" 시뮬레이션 부합, 재현 가능 | ✓ |
| seeds = 평점 최고 5권 | 낙관적, 동점 처리 | |
| seeds = train 임의 5권 | 저평점 책이 시드 | |
| n≥k: history = seeds 제외 train 전체, k=20 | 실제 이력 유지, 모집단 차이는 n_users 기록 | ✓ |
| n≥k: 무작위 정확히 k개 | 증거 수 통제, 실제 이력 버림 | |
| 동일 유저 집합(둘 다 train≥25) | 순수 비교, 메인 표 N 감소 | |
| 학습·seen = train 전체 상호작용, 정답만 긍정 | 라벨(만족)과 소비(읽음) 구분 | ✓ |
| 긍정만 학습·seen·정답 | 단순하나 저평점 읽은 책 재추천 가능, 데이터 절반 버림 | |

**User's choice:** 전부 권장안.
**Notes:** 사용자 질문 2건에 답변 — "밀리 데이터로 유저 평가 가능?" → 불가(유저 로그 없음, 2트랙 원칙) / "데모 페이지에서 2,000명 평가?" → 오프라인 `make eval`이고 데모는 `eval_table.json`을 표시만.

---

## n=0 vs n≥k 표 형태

| Option | Description | Selected |
|--------|-------------|----------|
| latest.csv = n=0 4행 + 별도 latest_states.csv | 수용 기준 4행·/eval-run 불변, main §6-1 정의와 일치 | ✓ |
| latest.csv에 state 열, 8행 | 문서 3곳 갱신 필요 | |
| n≥k는 json에만 | "숫자는 csv에서만" 규칙과 어긋남 | |
| 상태 표 대상 = 전 variant 자동 | pop이 대조군 | ✓ |
| hybrid·hybrid_div만 | Phase 2엔 0행, 이름 분기 생김 | |
| eval_table.json = n=0 4행 + 측정 조건 meta | 쇼케이스는 온보딩 시뮬레이션 표 하나 | ✓ |
| 두 표 모두 | 쇼케이스 단가 추가(Phase 6 작업량↑) | |

**User's choice:** 전부 권장안.
**Notes:** 없음.

---

## pop 서버 주입 형태

| Option | Description | Selected |
|--------|-------------|----------|
| 아티팩트 있으면 로드, 없으면 level 3 | make smoke가 level 0 실증, 아티팩트 없이 기동 유지, Goodbooks id는 Phase 3 교체 명시 | ✓ |
| 테스트에서만 주입, server.py 불변 | 사람이 보는 증거 없음 | |
| 기동 시 parquet fit | 6M행 pandas 로드 — 아키 리스크 메모에 정반대 | |
| 기본 variant = 등록된 것 중 VARIANTS 마지막 | Phase 4에 hybrid_div, 셀 B 기본과 이어짐 | ✓ |
| 기본 variant = 첫 것 | 항상 pop | |
| level 0 = trending 1행 + items 평탄화 | Phase 1 D-02 행 뼈대 재사용, 행 순서 정본은 compose.py | ✓ |
| rows 비움, items만 | 구 데모 화면이 빈 화면 | |
| 다른 행 이름 | 의미 어긋남 | |
| seeds 있을 때만 level 0, 익명은 level 3 | 백엔드 01 §5 규약 | ✓ |
| 파이프라인 있으면 항상 level 0 | fallback_level 의미 훼손 | |

**User's choice:** 전부 권장안.
**Notes:** 없음.

---

## ILD 벡터 시점

| Option | Description | Selected |
|--------|-------------|----------|
| Phase 2에서 벡터 부분만 먼저 | pop 1행 3지표 Day 1 실측, Phase 4 부담 감소 | ✓ |
| Phase 2는 ILD 빈칸, Phase 4에서 | 최소 작업, NaN 열 | |
| tags = 상위 20 태그, 잡음 태그 제외 상수 | to-read 등 공통 태그로 ILD 눌림 방지, categories 빈 리스트 | ✓ |
| 상위 20 그대로 | IDF에 의존, 실측 후 판단 | |
| 상위 1~3을 categories로 | Track A에서 쓸 곳 없음 | |

**User's choice:** 전부 권장안.
**Notes:** 없음.

---

## Claude's Discretion

다운로드 구현·`event` 값·파일 분할·Pipeline 어댑터 위치·CLI 형태·`/health` 필드 채우기 시점·git sha 취득·아티팩트 이름·N·Worker wave 분할.

## Deferred Ideas

서버 Goodbooks pop 배선 교체(Phase 3/4) · UCSD Poetry temporal(Should) · 후보 생성·랭킹·재순위화(Phase 4) · user_key·셀·compose(Phase 5) · 쇼케이스 n≥k 표(불채택) · EvalResult 필드 추가(불채택) · EVAL-07 그래프(Should 꼬리) · to_read 신호(불채택) · 매 실행 재표본(불채택).
