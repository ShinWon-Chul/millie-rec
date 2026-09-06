# Phase 8: PDF 제출물 - Context

**Gathered:** 2026-09-06
**Status:** Ready for planning

<domain>
## Phase Boundary

`millie-rec/report/draft.md`(현재 248줄·16,197자)를 **처음 보는 IT 면접관이 5장 안에서 읽어 내는 제출 원고**로 완성하고, Notion에 붙여 PDF 5장으로 내보낸다. 과제 필수 4항목·선택 6항목·★고유 설계 3개·필수 문장 7개·mermaid 그림 4개·캡처 6장·데모 URL·QR·가동 감시 URL이 들어간다. 코드 변경은 PDF 숫자를 깨는 버그 수정만(Day 5 규칙). 새 모델·새 실측·새 데모 기능은 범위 밖.

**사용자 지시(2026-09-06, 이 논의):** 코드베이스와 main 설계서·브레인스토밍_구체화를 전수 조사해 draft.md를 개선한다 · 과제 목표(추천 목표·활용 데이터·추천 구조·성능 평가 + 필수 4·선택 6)를 잘 나타내고 **실력 있는 개발자답게, 잘 읽히게** · 데모 실제 URL `https://millie-rec-production.up.railway.app/#/`와 UptimeRobot 상태 페이지 `https://stats.uptimerobot.com/20M6QwPo7z`를 포함 · Notion → PDF 5장 · **Sentry 정상 동작 확인**도 제출 전 점검에 포함.

</domain>

<decisions>
## Implementation Decisions

### 분량·압축 전략 (16,197자 → 5장)
- **D-01:** 4장 실측 비교표는 **8행 유지**(4 variant × n=0/n≥20 — "가중치가 변해야 한다"의 직접 증거). 대신 표 아래 해석 문단 3개(2,442자)를 **5문장으로 압축**하고, freeze 상수 8개 나열은 각주 1줄로 내린다.
- **D-02:** 3장 §3-3 대응표 아래 실측 불릿 2개(카탈로그 1,061자·배포 535자)는 **각주 2줄로 압축**. 카탈로그: "밀리 공개 도서 9,447권 · 수치·메타·표지 URL만 · 완독지수 82.5%". 배포: "같은 이미지가 로컬 docker와 Railway에서 동일(`model_version` 일치) · 재배포 중에도 SQLite 볼륨 유지". 수집일·파일명 4개·5초 폴링 다운타임 로그는 삭제.
- **D-03:** 5장 ★고유 설계는 **Notion callout 박스 3개**(★앵커 · ★난이도 · ★시간 가변 가중치, 각 3~4문장) + **난이도 4층 피처 소형 표 1개**(원시 완독지수 / 분야·길이 잔차 / 사용자 수준 gap / 신규 가드). 시간 가변 가중치 박스는 2장 수식·표를 유지한 채 5장에 1줄 참조만. 현재 §5-1(1,368자)·§5-2(1,686자) 문단 벽의 나머지 문장은 삭제.
- **D-04:** 2·3장 "구현 현황" 문단 2개는 **각 1문장**으로: "파이프라인 4단계가 코드 폴더와 1:1이고 경계는 아키텍처 테스트가 강제한다" / "파이프라인이 예외를 던져도 200 + 인기 행을 반환하는 것이 테스트로 존재한다". 파일 경로·Phase 번호·`make serve` 삭제.
- **D-05:** 감축 목표치 — 3·4장에서 ≈2,500자, 5장에서 ≈1,500자. 장별 본문 한글 ≈1,000~1,100자(`../.claude/rules/report.md`) 를 상한 지표로 쓰되 표·mermaid·캡처 면적을 함께 본다(D-16 검증).

### 그림·캡처 배치
- **D-06:** 캡처 6장(`report/figures/p5_01_onboarding.png` ~ `p5_06_home_after.png`, 폰 프레임 2x)은 **5장에 3×2 그리드**, 한 줄 3장으로 작게(약 1/3 페이지). 캡션은 D-11 시나리오 6단계와 **1:1**. 그림 파일은 repo 밖(07-CONTEXT D-07) — draft에는 자리 표시와 캡션만, 삽입은 Notion 조판에서.
- **D-07:** **데모 URL·QR·상태 페이지 박스**를 5장 데모 절 상단에 둔다: 왼쪽 "데모 https://millie-rec-production.up.railway.app/#/" + 오른쪽 QR(`report/figures/p5_qr.png`) + 아래 1줄 "심사 기간 가동 감시(5분 간격 헬스체크): https://stats.uptimerobot.com/20M6QwPo7z". **1장 제목 아래에도 데모 URL 1줄을 재기재**(문서 첫 화면에서 바로 누르게). URL은 `/#/` 해시 포함 그대로.
- **D-08:** mermaid 그림 **4개 전부 유지**(1장 7단계 신호 · 2장 4단계 파이프라인 · 3장 3계층+fallback · 4장 3지표↔3단계). 1장 신호 그림은 노드 텍스트를 줄여 높이 약 1/3로. ASCII 그림 금지, Notion 코드 블록 언어 = Mermaid.
- **D-09:** 본인 5권 앵커 사례는 **소형 표 1개**(시드 5권 → 앵커 행 대표 이웃 2권씩, 5행×3열, 출처 `report/demo_5books.md`) + "데모 카탈로그의 이웃은 콘텐츠 유사도(제목·소개 TF-IDF), 실서비스는 Item-KNN 이웃" 1줄. 현재 L234 "『○○』을 좋아하셨다면 행(Item-KNN 이웃 그대로)"는 **과대 표기 → 수정**.

### 독자 언어·근거 표기 · 시나리오
- **D-10:** 개발 과정 표기는 **전부 삭제**: "Phase N", "Day N", "freeze", "구현 완료", 재배포 폴링 로그, `make serve`, 스크래치패드·repo 언급, L3~4 조판 지시 블록, `[Phase N]`·`[재확인]` 마커. **산출물 근거만 각주로 유지**: 숫자 옆 출처(`results/latest.csv` · `results/latest_states.csv` · `results/latency.json` · `results/millie_coverage.csv` · `results/millie_difficulty.json`)와 테스트 이름 **1~2개**(fallback 200 테스트 · 철회 후 level 3 테스트). 재현 가능성이 개발자 신뢰의 근거이므로 출처 자체는 남긴다.
- **D-11:** 선택 ⑥ 사용자 시나리오·화면 흐름 = **5장 데모 절 도입 서사 3문장 + 캡처 캡션 1:1**. 서사: "자기계발 독자가 취향 설정에서 5권을 고르면 메인 첫 행이 『○○』을 좋아하셨다면 앵커 행이 된다 → 한 권을 완독하고 별점을 한 번 누르면 메인 최상단에 '완독하셨네요, 다음은' 행이 생긴다 → 취향을 SF로 재설정하면 기존 기록은 남고 앵커·페르소나 행만 즉시 바뀐다". 캡처 6장 = ①취향 설정(5권) ②메인(앵커 행) ③책 상세 ④뷰어 완독·별점 ⑤취향 재설정 ⑥메인 변화.
- **D-12:** 설계서에 있으나 draft에 없는 항목 중 **완독 직후 행 + 1탭 별점만 보충**(D-11 서사 안에 자연스럽게). 별점은 만족 라벨 수집이며 **모델 입력은 설계만**이라고 명시. 이벤트 스키마 소형 표·노출 근거 개인화(배지·리뷰 스니펫)·라이트 리더 처방은 **보충하지 않음**(분량) — Deferred.
- **D-13:** 필수 문장 7개 중 소제목·표 셀에만 있는 2개를 **본문 문장으로 승격**: "요청마다 무거운 계산을 다시 하지 않는다"(현재 H2 제목) · "미선택 책은 negative가 아니다"(현재 표 셀). Two-Tower·LLM 미채택 이유는 한 문단에 뭉쳐 있으므로 **각 1문장씩 분리**.
- **D-14:** 문체 규칙 유지(`../.claude/rules/report.md`): 한 문단 3문장 이내 · 영어 용어 첫 등장 `용어(풀네임: 설명)` · 출처 각주 없음 · Netflix/YouTube 인용은 1문장 · 데이터 2트랙 불혼합 · 회사 수치 `[재확인]` 제거.

### 운영 문구·제출 전 점검 (사용자 미선택 영역 — Advisor 재량으로 확정)
- **D-15:** 4장 §4-3 모니터링 행은 "Sentry(예외) 연결 · 가동 감시 5분 · 지표 수집기(Prometheus→Grafana)는 설계만"으로 정리(요구사항 'Sentry·Grafana Cloud scrape 연결'(`.planning/REQUIREMENTS.md` DEPLOY-04) 폐기 반영). 배포 p95 79.5ms는 **"variant 공통 전역 p95(셀 혼합 bench)"** 1구절을 붙인다(Codex 2회차 C5, `07-04-SUMMARY.md`).
- **D-16:** 분량 검증 = **Advisor 계측 + 사용자 Notion 확인**. Advisor는 장별 한글 자수·표 행·mermaid·캡처 면적을 계측하고 `make pdf`(pandoc HTML)로 미리 보며 5장 안으로 맞춘 뒤, 사용자가 Notion에 붙여 PDF 내보내기 후 **장 수를 한 줄 회신** → 초과분은 문장 차순 삭제(폰트·여백 축소 금지).
- **D-17:** **Sentry 정상 동작 확인(사용자 지시)** — 배포본에서 코드 없이 예외를 유발할 안전한 경로가 없다(ERROR 로그 10곳 모두 내부 장애 시에만). 순서: ① 사용자가 Sentry 프로젝트 대시보드에서 SDK 연결·최근 이벤트 여부 확인(회신) → ② 없으면 사용자가 보관한 DSN으로 로컬 1회 `sentry_sdk.capture_message("millie-rec probe")` 를 보내 대시보드에서 수신 확인(DSN은 파일·기록에 남기지 않음) → **디버그 엔드포인트·의도적 500은 만들지 않는다**(Day 5 코드 규칙). 결과는 07-04-SUMMARY 운영 인계 또는 PROGRESS 미결에 1줄.
- **D-18:** 제출 전 점검 목록(플랜 마지막 태스크): `uv run pytest --no-header` failed 0 · `make smoke` PASS · Railway Variables `FREEZE_BOOK_STATS=1`(화면·PDF 숫자 고정) · UptimeRobot 키워드 `"status":"ok"` → `"db_ok":true` 권고(사용자 대시보드) · `/pdf-check` 전 항목 통과 · `[재확인]`·`[Phase N]` 0 · 상단 체크리스트 표 삭제 · 데모 URL·상태 페이지 URL 실제 200 재확인.

### 완독 후 추천 유저 플로우 (사용자 지시 2026-09-06, 플랜 착수 중 추가)
- **D-19:** 데모 방문자가 완독 후 추천 행('『○○』을 완독하셨네요, 다음은')까지 거의 가지 않는다 — 프리셋 3개(신규 유저 A·건너뛰기·재설정) 중 완독을 만드는 것이 없고, 손으로는 4클릭 깊이다. 문서에 **완독 후 추천 결과를 보는 유저 플로우를 명시**한다. ① `report/draft.md` 5장 데모 절: D-11 서사 아래에 **클릭 경로 1줄** — "완독 후 추천 보기: 메인 책 카드 → 책 상세 「바로 읽기」 → 뷰어 「완독」 → 별점 ★ 1탭(「나중에」도 가능) → 메인 최상단 『○○』을 완독하셨네요, 다음은 행". 화면 문구는 데모 라벨 그대로(`demo/js/screens/d3_detail.js` 「바로 읽기」 · `d4_reader.js` 「완독」·「10분 읽기」·별점 모달 「어떠셨나요?」 · 행 제목 `src/millie_rec/serving/after_completion.py` `TITLE_AFTER`). 완독 또는 「나중에」 뒤 화면은 자동으로 `#/home`으로 돌아온다(`demo/js/actions.js` `rate`·`rateLater`). 캡처 캡션 ④(뷰어 완독·별점)·⑥(메인 변화)이 이 경로의 앞·뒤이므로 캡션에 경로 단계 번호를 붙여 연결한다. ② `report/demo_guide.md`에 "완독 후 추천 보는 법" 1절 추가 — 같은 경로 + "「10분 읽기」는 유효 독서(T=15분, 데모 상수) 기록용이고 행을 만드는 것은 「완독」이다" 2문장. 코드·프리셋 변경은 하지 않는다(Day 5 규칙). '완독 유저' 프리셋 추가는 사용자가 따로 승인할 때 demo 레인 후속으로만.

### Claude's Discretion
- 5장 안에서 ★박스·시나리오·캡처 그리드·5권 표·URL 박스의 **순서**와 callout 색·아이콘.
- 각 장 H2에 축 태그([①]~[④]) 표기 형식(`/pdf-check` 8-②가 검사).
- 1장 mermaid 노드 축약 문구, 4장 해석 5문장의 선택, 각주 문장 형태.
- 감축 시 어느 문장을 먼저 지울지(단, 필수 문장 7·★3·숫자 출처는 보존).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 원고·규칙·점검
- `millie-rec/report/draft.md` — 현재 원고 248줄(개선 대상). L3~4 조판 지시 블록은 제출 전 삭제.
- `../.claude/rules/report.md` — 장 구성(H1 5개)·분량·필수 문장 7·mermaid 3 필수·영어 용어 형식·2트랙 각주·캡처 6장·저작권.
- `../.claude/skills/pdf-check/SKILL.md` — 제출 전 체크리스트(필수 4·선택 7·필수 문장·숫자 출처·4축 가시성·★3 박스).
- `../.claude/rules/references.md` — 원고 밖 문서(플랜·SUMMARY)의 참조 표기.

### 설계 정본(주장의 출처)
- `../.assets/설계서/main 설계서/과제대응전략_최종본(main 설계서).md` — §1 중심 철학·§1-1 4축 · §2 페이지 매핑 P1~P5 · §4 QRS·난이도 미스매치 · §5-2 시간 가변 가중치 · §5-3 재설정 시나리오(자기계발→SF) · §5-6 난이도 4층 피처 · §5-7 앵커 · §6 평가 · §7 제약 · §8 범위 4분류·이벤트 스키마 · §9 기억할 5가지.
- `../.assets/설계서/브레인스토밍_구체화.md` — §1 상태 열(A~F 중 구현/설계만/폐기 구분 — 과대 표기 방지).
- `../.assets/PRD/PRD_메인_추천_시스템.md` — §9 수용 기준 표 말미 제출물 기준.
- `../.assets/설계서/화면 구성 및 디자인/02_*.md` §7 PDF 캡처 계획(2x · `?capture=1`) · `01_*.md` 디자인 토큰.

### 숫자 정본(PDF 숫자는 여기서만)
- `millie-rec/results/latest.csv` · `results/latest_states.csv` — 비교표 8행(Goodbooks-10k · holdout · seed 42 · n=2,000/1,990).
- `millie-rec/results/latency.json` — p95 79.5ms(로컬 bench, 셀 혼합 전역, `git_sha 8e5172b`).
- `millie-rec/results/millie_coverage.csv` · `results/millie_difficulty.json` · `results/millie_edges_gate.json` — 카탈로그 9,447권·완독지수 82.5%·잔차 분야 평균 0.502~0.505·동일 카테고리 비율 0.356.
- `millie-rec/report/demo_5books.md` — 본인 5권 앵커 행·hybrid_div 상위 10(D-09 표의 출처).

### 데모·배포 사실
- `millie-rec/.planning/phases/07-deploy/07-04-SUMMARY.md` — 배포 URL·상태 페이지·다운타임 실측·Codex C5(전역 p95)·운영 인계·캡처 스크립트 위치.
- `millie-rec/report/figures/p5_01_onboarding.png` ~ `p5_06_home_after.png` · `p5_qr.png` — repo 밖(`.gitignore`), Notion 삽입용.
- `millie-rec/.planning/phases/07-deploy/07-CONTEXT.md` D-05(Grafana 폐기)·D-07(그림 repo 밖)·D-14(다운타임 실측).
- `millie-rec/.planning/phases/04-freeze/04-CONTEXT.md` D-14(freeze 4종)·D-05(ablation 설계만) — "구현 vs 설계만" 경계.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `report/draft.md` 5장 골격·mermaid 4개·표 11개·필수 문장 7개 전부 존재(2개는 제목·표 셀) — **재작성이 아니라 압축·재배치**.
- `report/demo_5books.md` — 5권 앵커 표의 원자료. `report/figures/` 캡처 7장 완료(07-04).
- `make pdf` — pandoc HTML 미리보기(`report/mermaid.html` 헤더) → 장 수 추정용.
- `/pdf-check` 스킬 — 최종 점검 자동화. `/eval-run` — 비교표 숫자 재확인(재측정 금지, 읽기만).

### Established Patterns
- 숫자 정본 3종(`results/`만) · 이름 정본 `contracts.py`(`VARIANTS`·`ROW_IDS` 표기 그대로: pop/cf/hybrid/hybrid_div · anchor_·after_completion·persona_shelf·trending·fresh_picks).
- 데이터 2트랙: 비교표 = Goodbooks(Track A), 데모·난이도·5권 = 밀리 표본(Track B). 한 표에 섞지 않는다.
- 저작권: 과제 PDF 문구 인용 금지 · 표지 이미지 금지 · 밀리 리뷰·설명문 미노출 · 그림은 repo 밖.

### Integration Points
- 이 페이즈는 코드를 만들지 않는다. 산출물 = `report/draft.md` 최종본(커밋) + Notion 페이지(사용자) + PDF(사용자 내보내기) + 제출 전 점검 기록(PROGRESS·07-04-SUMMARY 인계 갱신).
- 전수 조사 결과(이 논의에서 확보): 필수 4항목·선택 ⑤⑦⑨⑩ = 강, **⑥ 시나리오 = 약(D-11로 보강)**, ⑧ 데모 = 중(D-07·D-09·D-11로 보강). ★3개 박스 없음(D-03). 장별 자수 — 1장 4,449 · 2장 4,817 · 3장 7,132 · 4장 7,152 · 5장 5,064(표·그림 포함).

</code_context>

<specifics>
## Specific Ideas

- "실력 있는 개발자답게" = 주장마다 **실측 숫자와 출처**, 안 쓴 것의 이유(Two-Tower·LLM·ALS), 제약 → 설계 인과문. 개발 과정 서술(Phase·Day·freeze)은 개발자 티가 아니라 소음이므로 지운다.
- 메시지는 "Netflix/YouTube 모델을 만들었다"가 아니라 **"공식 설계 원칙을 밀리의 UI·데이터·규모에 맞게 번역했다"**(main 설계서 §9) — 기억할 5가지는 마지막 문단 유지.
- 5장은 **그림 장**: URL·QR 박스 → 시나리오 3문장 → 캡처 3×2 → ★박스 3 → 5권 표 → 로드맵 1줄 → 기억할 5가지.
- 데모 URL은 `/#/`(쇼케이스 해시)까지 그대로 적는다. 상태 페이지 문구는 "심사 기간 가동 감시(5분 간격 헬스체크)".

</specifics>

<deferred>
## Deferred Ideas

- 이벤트 스키마 소형 표(`recommendation_id`·`model_version`·`row_id`·`position`·`candidate_set_id`) — main 설계서 §8 지시였으나 분량으로 미수록. 1장 L60 산문 1줄 유지.
- 노출 근거 개인화 1문장(리뷰 기준 사용자 → 리뷰 배지) · 라이트 리더 처방 1문장 — 미수록(면접 구두 설명 후보, `report/interview_story.md`).
- 지연 예산 컴포넌트 표(30/50/60/20ms)·MDE 예시 수치 — 3장 mermaid 노드·4장 불릿으로 갈음.
- 데모 화면의 별점 403(철회 유저) 성공 토스트 표시(코드 리뷰 WR-01) · Codex C1(익명 `candidate_sets`) — Phase 8 이후 인계(PROGRESS 미결).
- 공개 repo 링크를 PDF에 넣을지 — 논의하지 않음. 플랜에서 "`README.md` 데이터 출처 문구 확인 후 사용자 1회 확인" 항목으로만.

</deferred>

---

*Phase: 08-pdf*
*Context gathered: 2026-09-06*
