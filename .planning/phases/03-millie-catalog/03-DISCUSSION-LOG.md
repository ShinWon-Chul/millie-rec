# Phase 3: 밀리 카탈로그 빌드 - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-09-05
**Phase:** 03-밀리 카탈로그 빌드
**Areas discussed:** 빌드 스냅샷 시점, 커버리지 게이트 미달 조치, content_sim 이웃 게이트, 서빙 주입·popularity_kr 범위

---

## 빌드 스냅샷 시점

| Option | Description | Selected |
|--------|-------------|----------|
| 지금 5,157권으로 빌드 → 배치 종료 후 재빌드 | walking skeleton, id_map append-only라 재빌드 안전 | ✓ |
| 배치 종료를 기다린다 | 단일 스냅샷, 오늘 밤 Phase 3 작업 불가 | |
| 배치 지금 중단·5,157권 확정 | 상한 없음 결정 번복 필요 | |

| Option | Description | Selected |
|--------|-------------|----------|
| 마지막 재빌드 스냅샷 | `results/millie_coverage.csv` 정본, freeze 전 마지막 `make millie` | ✓ |
| 첫 빌드 숫자로 고정 | 문서와 산출물 어긋날 위험 | |

| Option | Description | Selected |
|--------|-------------|----------|
| Day 2 오전에 중단, 그 스냅샷 최종 | 시간 상한 보완, 미발견 프론티어 수 기록 | ✓ |
| 계속 돌리고 Day 3 freeze 직전 재빌드 | Phase 4 실측 재실행 위험 | |

**User's choice:** 세 질문 모두 권장안.
**Notes:** 배치 실측 프론티어 2,482 · ≈6s/권 → 4~7h 잔여.

---

## 커버리지 게이트 미달 조치

| Option | Description | Selected |
|--------|-------------|----------|
| 껍데기 5건을 수집 실패로 분류·분모 제외 | 유효 레코드 정의, `n_skipped_empty` 기록 | ✓ |
| 전부 포함, title 임계 99.5%로 완화 | §7 표 수정 필요, 파서 결함 탐지 약화 | |
| 재수집 후 결정 | 수집기 skip 로직 수정 필요 | |

| Option | Description | Selected |
|--------|-------------|----------|
| 파서 미스 1건 제외·건수 기록, 0.5% 임계 | 최종 스냅샷 초과 시 파서 수정 | ✓ |
| 지금 픽스처 추가·파서 수정·1건 재수집 | 20~30분, 270줄 파서 분리 여부 걸림 | |

| Option | Description | Selected |
|--------|-------------|----------|
| 밀리 분류 그대로 분야로 취급 | 화면 01 §8 폐기 결정과 일관, 코드 0 | ✓ |
| 형식형 상수 목록 분리, 게이트 계산 제외 | 게이트 숫자가 주제 분야만 셈 | |

**User's choice:** 세 질문 모두 권장안.
**Notes:** 실측상 title 외 전 항목 통과. §7 표는 정책으로 유지.

---

## content_sim 이웃 게이트

| Option | Description | Selected |
|--------|-------------|----------|
| 코드대로 tags 기본 제외, 설계 문구 갱신 | 어휘 ~30토큰이 동일 카테고리 이웃을 밀어 ③에 불리 | ✓ |
| 설계대로 저가중 포함 후 ③ 미달 시 제거 | 실행 2번 가능 | |

| Option | Description | Selected |
|--------|-------------|----------|
| 현 구현 유지(category_best + top_up ≥5, 임계 없음) | 게이트 3만 요구 | ✓ |
| content_sim 최소 cosine 임계 + category_best 대체 | 임계 근거 없음 | |

| Option | Description | Selected |
|--------|-------------|----------|
| description 가중 상향만, 그래도 미달이면 보고 | 설계 그대로, 새 코드 없음 | ✓ |
| 상향 + 동일 카테고리 ≤14 후처리 | 설계에 없는 리랭킹 | |

| Option | Description | Selected |
|--------|-------------|----------|
| TF-IDF → TruncatedSVD 128 dense L2 | ≈2.6MB, 이웃은 원본 cosine | ✓ |
| max_features 2000 dense | ≈41MB, 재빌드 시 초과 | |
| 벡터 미탑재, 이웃 그래프만 | DATA-07·Phase 4 MMR 이중 구현 | |

**User's choice:** 네 질문 모두 권장안.
**Notes:** 사용자 질문 "TF-IDF보다 BM25는?" → 대칭성·벡터 공간(MMR·ILD)·길이 균일·기존 의존성 근거로 TF-IDF 유지, BM25·임베딩은 PDF "설계만". 피처 = title+description+curator_note 문자 2~4gram(char_wb), tags 제외.

---

## 서빙 주입·popularity_kr 범위

| Option | Description | Selected |
|--------|-------------|----------|
| `*_kr.json` 있으면 카탈로그 주입 + pop = Track B, Goodbooks pop 서버에서 내림 | 성공 기준 4 직접 충족, 숫자 불혼합 | ✓ |
| Phase 4까지 Goodbooks pop 유지, 카탈로그는 level 3만 | id 체계 불일치가 Day 2 배포에 노출 | |

| Option | Description | Selected |
|--------|-------------|----------|
| title ∧ millie 호스트 표지 ∧ 성인 표지 아님 | 깨진 카드 방지 최소 게이트 | ✓ |
| title만 | 표지 없는 카드 노출 | |
| + completion_prob 실측만 | 결측 13.7% 배제, 설계와 어긋남 | |

| Option | Description | Selected |
|--------|-------------|----------|
| all 세그먼트만 Must, 연령×성별은 Should 증분 | 스키마 고정, level 2 검증은 Phase 5 | ✓ |
| 세그먼트 12개 지금 | 이 페이즈에서 증명 불가 | |
| all만, 세그먼트는 Phase 5로 | 소유권(data) 어긋남 | |

**User's choice:** 세 질문 모두 권장안.

---

## Claude's Discretion

난이도 파생 세부(분위 수·최소 표본) · `catalog_kr.py` 구성·`meta()` 필드 · Track B pop Pipeline 위치 · `demo/fallback/popular.json` 형태 · export 세부·유사도 메모리 · 서버 주입 테스트 fixture · Worker wave 분할. Advisor 판단: 150줄 초과 3파일 분리하지 않음(새 로직은 새 파일), id 부여는 유효 레코드에만.

## Deferred Ideas

세그먼트 인기·level 2 검증(Phase 5) · similar_readers 소스 분리(Phase 5) · coLoan(Day 3 Should) · 쪽수 진단(Day 2 Should) · BM25·임베딩(설계만) · 파서 수정·150줄 분리(미채택) · cosine 임계·카테고리 상한(미채택) · 형식형 분류 목록(Phase 6 화면 기준) · Goodbooks pop 서버 로드(폐기).
