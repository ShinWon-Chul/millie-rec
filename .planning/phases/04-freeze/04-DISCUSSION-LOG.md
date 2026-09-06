# Phase 4: 추천 파이프라인과 모델 freeze - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-09-05
**Phase:** 04-추천 파이프라인과 모델 freeze
**Areas discussed:** 가중치 α/β/γ 구조와 hybrid 병합, hybrid_div 재순위화와 Should 꼬리, 서버 Track B 4 variant와 user_state_weights 경로, 본인 5권 케이스와 freeze 선언

---

## 가중치 α/β/γ 구조와 hybrid 병합

| Option | Description | Selected |
|--------|-------------|----------|
| 사용자 상태 성분 가중치(2단 구조) | α/β/γ는 seeds·history·session 성분에, 채널 가중치 w_cf·w_content·w_pop은 hybrid.py 상수 | ✓ |
| 채널 가중치(1단) | α→content, β→cf, γ→session, pop 별도 — n=0에서 cf 소멸 | |

| Option | Description | Selected |
|--------|-------------|----------|
| 결합: 아키 초기값·하한 + main 지수 감쇠 | 0.6/0.3/0.1, α_n=max(0.2, α₀e^{−n/20}), β:γ=3:1, 미사용 성분 재정규화, 부스트는 인자만 | ✓ |
| 아키 단계 규칙만 | reader_open n회마다 ±0.05 — main §5-2 번복 필요 | |
| main 지수 감쇠만, α₀=1.0 | 아키 초기값 폐기 | |

| Option | Description | Selected |
|--------|-------------|----------|
| min-max 정규화 + 고정 상수, 튜닝 1회 | 0.5/0.3/0.2 초기, ≤3조합 그리드 1회, 버린 조합은 eval_<ts>.json만 | ✓ |
| 순위 기반 병합(RRF) | 1/(60+r) 합산 — α/β/γ가 순위로 뭉개짐 | |
| 튜닝 없이 초기 상수 그대로 | 수정 기회 없음 | |

| Option | Description | Selected |
|--------|-------------|----------|
| Claude 재량 — 기본안 | 이진 희소 cosine, 이웃 top-50 npz 캐시, content=seeds 평균 벡터, 풀 200 | ✓ |
| 아티팩트 캐시 없이 매번 fit | 실행마다 10k×10k 재계산 | |
| 이웃 수·후보 풀 사용자 지정 | — | |

**User's choice:** 2단 구조 · 결합 스케줄(τ=20) · min-max+상수 튜닝 1회 · 후보 통로 Claude 재량
**Notes:** main §5-2 vs 아키 §3-3 스케줄 충돌은 결합으로 해소, 아키 문구 갱신은 Advisor 후속.

---

## hybrid_div 재순위화와 Should 꼬리

| Option | Description | Selected |
|--------|-------------|----------|
| REC-06 난이도 가드 | millie_index ∧ resid_z<−1 상단 N 제외, Track B 전용 | ✓ |
| REC-04 gap 피처 | gap·gap⁺·n_completed×gap 상수 가중, 결측·None 가중 0 | ✓ |
| ablation A/B/C AUC 표 | Track B 라벨 부재·순환 — 설계만 | |

| Option | Description | Selected |
|--------|-------------|----------|
| λ=0.7 · 풀 top-50 · ILD 상승을 완료 게이트로 | ild↑ ∧ ndcg 하락 ≤20%, 미달 시 λ=0.5 1회 | ✓ |
| λ 그리드(0.5/0.7/0.9)로 ILD 최대 | NDCG 손실 미고려 | |
| λ 사용자 지정 | — | |

| Option | Description | Selected |
|--------|-------------|----------|
| MMR 뒤에 가드 · n_completed=len(history) 대리 | 상단 N 안 위반만 내림, Phase 5가 이벤트 수로 교체 | ✓ |
| 가드 뒤에 MMR | 후보에서 제거 — main §5-6과 어긋남 | |
| UserState.context에 n_completed 전달 | dict 경계 사용 | |

**User's choice:** 가드+gap 구현, ablation 설계만 · λ=0.7/풀 50/ILD 게이트 · MMR→가드, len(history) 대리
**Notes:** 버리는 순서는 gap 피처 → 가드(아키 §8 난이도 계통).

---

## 서버 Track B 4 variant와 user_state_weights 경로

| Option | Description | Selected |
|--------|-------------|----------|
| create_app에 keyword-only `weights` 인자 추가 | app이 ranking 공개 함수 주입, contracts 무변경 | ✓ |
| Pipeline Protocol에 `weights(user)` 메서드 | 계약 변경·fake 6개 영향 | |
| serving이 가중치 규칙 별도 구현 | 이중 구현 금지 위반 | |

| Option | Description | Selected |
|--------|-------------|----------|
| cf=Neighbors 엣지 · content=VectorsKR cosine · 같은 랭커 코드 | 어댑터만 다름, 둘 다 source=content | ✓ |
| 서버 cf·hybrid 이웃 재료 하나로(엣지만) | 차이가 pop 혼입만 | |
| 서버는 pop·hybrid_div만 등록, cf·hybrid 422 | ROADMAP 성공 기준 1 위반 | |

**User's choice:** create_app `weights` 인자 · cf=엣지/content=SVD/같은 코드
**Notes:** 재빌드 전 스냅샷 실측 cf∩content 1/10, cf∩pop 1/10, content∩pop 0/10.

---

## 본인 5권 케이스와 freeze 선언

| Option | Description | Selected |
|--------|-------------|----------|
| 아직 — 제목 검색 도우미를 넣고 Day 3 실측 전에 준다 | `cli demo --find`, Worker는 임의 5권으로 검증 | ✓ |
| 이미 정했다 — 제목을 적어 넘김 | — | |
| Advisor가 임시 5권으로 진행, 나중에 교체 | freeze 후 재실행 위험 | |

| Option | Description | Selected |
|--------|-------------|----------|
| 앵커 5행 + hybrid_div top-10 마크다운, stdout → Makefile이 report/에 리다이렉트 | `report/demo_5books.md`, cli는 report/를 열지 않음 | ✓ |
| 앵커 1행(seed₁) + hybrid_div top-10만 | 최소 형태 | |
| RecommendOut JSON 그대로 | PDF 변환은 사람 몫 | |

| Option | Description | Selected |
|--------|-------------|----------|
| 모델 상수·VARIANTS·카탈로그 스냅샷·응답 스키마 4종 freeze, 3곳 기록 | STATE·개발일지 D 항목·draft §4-1 | ✓ |
| 수치만 freeze, 상수 튜닝은 Day 4 오전까지 | draft 표 재작성 위험 | |
| 선언 문구만(STATE.md 1줄) | 범위 불명 | |

**User's choice:** `--find` 도우미 + Day 3 전 제공 · 앵커 5행+hybrid_div 10 마크다운 → report/demo_5books.md · freeze 4종 3곳 기록
**Notes:** 마무리 질문에 사용자가 "이 설계가 밀리 데이터에서 성립하나? 맞다면 개발일지·draft.md에 의사결정 과정을 남겨라"로 답함 → 아티팩트 실측(difficulty 82.5%, 가드 모집단 1,173권, 4 variant 상이) 후 개발일지 D68·draft.md §2-2·§4-1·§5-2·§5-3 반영.

## Claude's Discretion

Item-KNN 세부(정규화·chunk·npz 포맷)·성분별 점수 계산 방식·`state_weights` 시그니처·guard 패스스루 구현·조립 코드 위치·`fit_pipelines` 시그니처·`cli demo` 3분위 경계·`--find` 매칭·npz 캐시 무효화·Worker 분할.

## Deferred Ideas

ablation AUC 표(설계만) · user_level·n_completed·부스트 적용(Phase 5 state.py) · compose 5행·앵커 reason(Phase 5) · 아키 §3-3·serving.md 문구 갱신(Advisor 후속) · overlap@20 참고 수치·coLoan(Day 3 Should) · SOURCE_* 승격 · Pipeline weights 메서드·RRF·λ 그리드·가드→MMR·임시 5권·Track B ILD 참고 수치(채택 안 함).
