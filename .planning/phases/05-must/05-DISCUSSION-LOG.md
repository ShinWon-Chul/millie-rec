# Phase 5: 서빙 Must 완성 - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-09-06
**Phase:** 5-서빙 Must 완성
**Areas discussed:** Must 5행 채우기 규칙 (compose), user_key 상태 모델 (state·nearline), fallback cascade·latency_breakdown·bench, Should 꼬리 범위·온보딩 메타 원천

---

## Must 5행 채우기 규칙 (compose)

| Option | Description | Selected |
|--------|-------------|----------|
| 개인화 파이프라인 결과 | 셀 배정 variant recommend() 상위 결과 그대로, channel_mix = source_channels 집계 | ✓ |
| 스냅샷 카테고리 인기(pop_rank) | 선택 카테고리 ∩ 카탈로그 pop_rank 순 | |
| 파이프라인 결과 중 스냅샷 카테고리 책만 | recommend() 결과를 선택 카테고리로 필터 | |

**User's choice:** persona_shelf = 개인화 파이프라인 결과 (권장)

| Option | Description | Selected |
|--------|-------------|----------|
| 파이프라인 결과 중 선택 카테고리 밖 책 | 앞 행에 안 쓰인 것 중 스냅샷 카테고리 밖, 부족 시 미선택 카테고리 인기 라운드로빈 | ✓ |
| 미선택 카테고리 인기 라운드로빈 | 비개인화 explore | |
| 파이프라인 뒤쪽 순위 | 남은 결과 순서대로 | |

**User's choice:** fresh_picks = 파이프라인 결과 중 선택 카테고리 밖 책 (권장)

| Option | Description | Selected |
|--------|-------------|----------|
| 선택 순서 첫 책 · 행 12권 | 최신 스냅샷 seeds[0], 이웃 20 → eligible·dedup → 12 | ✓ |
| 이웃 가중치 합 최대 책 · 행 12권 | 이웃이 가장 풍부한 seed | |
| 선택 순서 첫 책 · 행 8권 | 짧은 행 | |

**User's choice:** 선택 순서 첫 책 · 행 12권 (권장)

| Option | Description | Selected |
|--------|-------------|----------|
| 앞 행 우선 + book_id·정규화 제목 dedup | 렌더 순서 앞 행 우선, 정규화 제목 동일도 제거 | ✓ |
| 앞 행 우선 + book_id만 | 최소 구현 | |
| 앵커 행 우선 | 앵커 먼저 채우고 나머지 dedup | |

**User's choice:** 앞 행 우선 + book_id·정규화 제목 dedup (권장)
**Notes:** 후속 질문 없이 다음 영역으로. 배지 규칙·continue_reading·메타 조인은 설계서 그대로 + Claude 재량.

---

## user_key 상태 모델 (state·nearline)

| Option | Description | Selected |
|--------|-------------|----------|
| 읽기 행동만: reader_open·qualified_read·completion | Track A history='읽은 책'과 같은 의미 | ✓ |
| 읽기 행동 + library_add | 서재 담기도 장기 신호 | |
| completion만 | 완독만 | |

**User's choice:** 읽기 행동만 (권장)

| Option | Description | Selected |
|--------|-------------|----------|
| 최근 30분 내 reader_open·detail_click, 있으면 session_active | SESSION_WINDOW_S=1800 | ✓ |
| 마지막 추천 요청 이후 이벤트 | 시간 창 없음 | |
| 세션 성분 사용 안 함 | γ 항상 0 | |

**User's choice:** 최근 30분 창 (권장)

| Option | Description | Selected |
|--------|-------------|----------|
| 완독 수 = completion distinct · 레벨 = 완독 책 difficulty 평균, 0권이면 스냅샷 카테고리 평균 | 04-CONTEXT D-06 그대로 | ✓ |
| 완독 평균, 0권이면 None | 신규는 gap 0 | |

**User's choice:** 카테고리 prior 채택 (권장)

| Option | Description | Selected |
|--------|-------------|----------|
| 메모리 dict + Nearline 갱신 + 24h 리플레이 · 부스트 = 최신 스냅샷 2번째 이상 ∧ 24h 이내 | 아키 §3-5 그대로 | ✓ |
| 메모리 dict + Nearline + 전체 리플레이 | 완전 복구 | |
| 요청마다 events 직접 조회 | 메모리 상태 없음 | |

**User's choice:** 메모리 dict + Nearline + 24h 리플레이 (권장)
**Notes:** 후속 질문 없이 다음 영역으로.

---

## fallback cascade·latency_breakdown·bench

| Option | Description | Selected |
|--------|-------------|----------|
| 서빙 4키(feature·pipeline·compose·total) + 파이프라인 제공 시 세분 병합 | StagedPipeline 옵션 속성 last_breakdown을 getattr | ✓ |
| 서빙 4키만 | 단계 세분 없음 | |
| contracts.Pipeline에 breakdown() 추가 | Protocol 변경 | |

**User's choice:** 서빙 4키 + 세분 병합 (권장)

| Option | Description | Selected |
|--------|-------------|----------|
| 파이프라인 완료 후 누적 판정 · 캐시 = 직전 level 0 rows, 키 user_key+snapshot_id+variant | 스레드 중단 없음, fallback 경로에서만 캐시 읽기 | ✓ |
| 단계별 중간 판정 | StagedPipeline 내부 예산 검사 | |
| 타임아웃 스레드 강제 중단 | concurrent.futures wait | |

**User's choice:** 완료 후 누적 판정 (권장)

| Option | Description | Selected |
|--------|-------------|----------|
| user_key 50개 사전 생성 → 라운드로빈 500요청, model 미지정, k=40 | 실제 경로 측정 | ✓ |
| seeds 쿼리 cold-start 500회, model=hybrid_div | 최단 경로 | |
| 둘 다 기록 | 두 모집단 분리 | |

**User's choice:** user_key 경로 (권장)

| Option | Description | Selected |
|--------|-------------|----------|
| 모든 응답(level 0~3, seeds 포함) · rows는 row_id·book_id·position 축약 | 노출 로그 단일 소스 | ✓ |
| user_key 있는 응답만 | DB 가벼움 | |
| 모든 응답 · rows 전체 | 응답 재구성 가능 | |

**User's choice:** 모든 응답 · rows 축약 (권장)
**Notes:** 후속 질문 없이 다음 영역으로.

---

## Should 꼬리 범위·온보딩 메타 원천

| Option | Description | Selected |
|--------|-------------|----------|
| after_completion + ratings + dashboard 최소형 포함, /metrics·book_stats 설계만 | prometheus-client 미추가 | ✓ |
| after_completion + ratings만 | dashboard도 설계만 | |
| 4건 전부(prometheus-client 추가) | Should 버림 없이 계획 | |
| Must만 | Should 전부 설계만 | |

**User's choice:** 세 건 포함, metrics 설계만 (권장)

| Option | Description | Selected |
|--------|-------------|----------|
| serving/onboarding_meta.json 1벌 + categories 카탈로그 계산, /contract-sync 검사 | 아키 §9-3 파일 | ✓ |
| 모듈 상단 상수 | json 없이 | |
| 서버가 demo/config 직접 읽기 | 소유권 규칙 예외 | |

**User's choice:** serving/onboarding_meta.json (권장)

| Option | Description | Selected |
|--------|-------------|----------|
| 카테고리 라운드로빈 | 각 카테고리 pop_rank 상위 1권씩 | ✓ |
| 전체 pop_rank 순 | 합집합 그대로 | |

**User's choice:** 라운드로빈 (권장)

| Option | Description | Selected |
|--------|-------------|----------|
| persona.py 매핑 표 + 미매핑은 sha256 결정적 선택 | 항상 페르소나 존재 | ✓ |
| 매핑 표 + 미매핑 null | 스키마 optional | |

**User's choice:** 매핑 표 + sha256 결정적 선택 (권장)
**Notes:** "컨텍스트 문서 작성" 선택 — 추가 회색 지대 탐색 없음.

---

## Claude's Discretion

api.py 150줄 유지 방법(오케스트레이션 분리 파일) · n_completed 대리값 교체 방식(UserState.context 분기 검토) · /health 채우기 · seeds+user_key 동시 요청 우선순위 · 세션 만료·history 상한·리플레이 배치·Nearline 예외 처리·impression selected 채우기 · library 3분류 · showcase 상수 문장·personal_case · db.py 쓰기 헬퍼·close()·인덱스 · Worker 분할

## Deferred Ideas

/metrics·book_stats 24h 집계·FREEZE_BOOK_STATS(설계만) · admin/export(안 함) · similar_readers·anchor_seed₂·light_start·light 배지 · personal_case(시간 있으면) · ab_table 층화·MDE · 세그먼트 인기 level 2 · Pipeline.breakdown() · 타임아웃 스레드 · history에 library_add · demo/config 직접 읽기 · 전체 리플레이
