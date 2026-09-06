# Phase 8: PDF 제출물 - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-09-06
**Phase:** 08-pdf
**Areas discussed:** 분량·압축 전략, 그림·캡처 배치, 독자 언어·근거 표기 + 시나리오 (미선택: 제출 전 점검·운영 문구 → Advisor 재량 D-15~D-18)

**사용자 지시(논의 시작 시):** 코드베이스·main 설계서·브레인스토밍_구체화 전수 조사 후 draft.md 개선 · 과제 필수 4/선택 6 반영 · 실력 있는 개발자답게·잘 읽히게 · 데모 URL `…/#/`·UptimeRobot 상태 페이지 URL 포함 · Notion → PDF 5장 · Sentry 정상 동작 확인.

**전수 조사(탐색 에이전트) 요약:** 필수 4·선택 ⑤⑦⑨⑩ 강 / ⑥ 시나리오 약 / ⑧ 데모 중 · ★3 박스 없음 · 3·4장 각 7,100자 과부하, 5장 표·그림 0 · 개발 흔적 잔존 10곳 · 과대 표기 L234(Item-KNN).

---

## 분량·압축 전략

| Option | Description | Selected |
|---|---|---|
| 8행 유지 | 해석 문단 5문장 압축, freeze 상수 각주 1줄 | ✓ |
| 4행만(n≥20) | 표 절반, 시간 가변 가중치 증거 약화 | |
| 6행(pop n≥20만) | 기준선 1행 | |

| Option | Description | Selected |
|---|---|---|
| 각주 2줄로 압축 | 카탈로그·배포 실측 불릿 → 각주, 수집일·파일·폴링 로그 삭제 | ✓ |
| 불릿 삭제, 표만 | 카탈로그 수치는 5장으로 | |
| 유지 | | |

| Option | Description | Selected |
|---|---|---|
| Notion callout 3 + 표 1 | ★앵커·★난이도·★시간 가변 각 3~4문장 + 난이도 4층 피처 표 | ✓ |
| 소제목 유지, 문단 절반 | | |
| 박스 2개만 | 시간 가변은 2장에만 | |

| Option | Description | Selected |
|---|---|---|
| 1문장으로 압축 | 구현 현황 2문단 → 각 1문장, 경로·Phase 삭제 | ✓ |
| 전부 삭제 | | |
| 유지 | | |

**User's choice:** 전부 권장안.

---

## 그림·캡처 배치

| Option | Description | Selected |
|---|---|---|
| 5장 3×2 그리드 | 시나리오 6단계 1:1 캡션, 약 1/3 페이지 | ✓ |
| 1·2·5장 분산 | | |
| 5장 4장만 | | |

| Option | Description | Selected |
|---|---|---|
| 5장 데모 절 상단 박스(+1장 URL 재기재) | 데모 URL + QR + 상태 페이지 1줄 | ✓ |
| 1장 제목 아래에만 | | |
| 5장에만 | | |

| Option | Description | Selected |
|---|---|---|
| mermaid 4개 유지 | 1장 그림 노드 축약 | ✓ |
| 3개(1장→표) | | |
| 2·3장 합치기 | | |

| Option | Description | Selected |
|---|---|---|
| 소형 표 1개 | 5권 → 대표 이웃 2권, 콘텐츠 유사도 명시(L234 과대 표기 수정) | ✓ |
| 문장 2개 | | |
| 캡처에 맡김 | | |

**User's choice:** 전부 권장안.

---

## 독자 언어·근거 표기 + 시나리오

| Option | Description | Selected |
|---|---|---|
| 프로세스 용어 삭제, 산출물 근거만 각주 | Phase·Day·freeze 삭제, results/·테스트 이름 1~2개 유지 | ✓ |
| 전부 삭제 | | |
| 파일 경로·테스트 이름 유지 | | |

| Option | Description | Selected |
|---|---|---|
| 서사 3문장 + 캡션 1:1 | 자기계발 5권 → 앵커 → 완독·별점 → '다음은' → SF 재설정 → 메인 변화 | ✓ |
| 단계 표 | | |
| 서사 문단만 | | |

| Option | Description | Selected |
|---|---|---|
| 완독 직후 행 + 1탭 별점 | 시나리오 안에 자연 삽입, 별점 모델 입력은 설계만 | ✓ |
| 이벤트 스키마 소형 표 | | |
| 노출 근거 개인화 1문장 | | |
| 라이트 리더 처방 1문장 | | |

| Option | Description | Selected |
|---|---|---|
| Advisor 계측 + 사용자 Notion 확인 | 자수·표·그림 계측 + make pdf, 사용자 장 수 회신 | ✓ |
| 사용자 확인만 | | |

**User's choice:** 전부 권장안. 마무리 질문 → "CONTEXT 작성으로".

---

## Claude's Discretion
- 미선택 영역(제출 전 점검·운영 문구): D-15 관측 문단·전역 p95 문구 · D-16 분량 검증 · D-17 Sentry 확인 순서(대시보드 → 로컬 probe, 디버그 엔드포인트 금지) · D-18 제출 전 점검 목록.
- 5장 내부 순서, callout 형식, 축 태그 형식, 1장 mermaid 축약 문구, 4장 해석 5문장 선택, 감축 우선순위.

## Deferred Ideas
- 이벤트 스키마 소형 표 · 노출 근거 개인화 · 라이트 리더 처방 · 지연 예산 표·MDE 수치 · 별점 403 토스트(WR-01)·Codex C1 인계 · 공개 repo 링크 표기 여부.
