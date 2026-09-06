---
phase: 08-pdf
plan: 01
subsystem: report
tags: [pdf, draft, 압축, 4축태그, 그림번호]
requires:
  - "report/draft.md (HEAD aa5cc91 기준 248줄)"
  - "results/latest_states.csv · results/latest.csv · results/latency.json · results/millie_coverage.csv · results/millie_edges_gate.json (숫자 정본, 재측정 없음)"
  - "report/figures/eval_bar.png (라벨 육안 대조, 재생성 없음)"
provides:
  - "report/draft.md 1~4장 제출 원고 형태(개발 과정 표기 0 · 축 태그 12 · 그림 1~5 일관 · 비교 막대 자리 표시)"
affects:
  - ".planning/phases/08-pdf/08-02-PLAN.md (5장 재구성 — 5장 무변경으로 입력 보존)"
  - ".planning/phases/08-pdf/08-03-PLAN.md (분량 계측·차순 삭제 — 3·4장 D-05 목표 초과분 인계)"
tech-stack:
  added: []
  patterns: ["Python 정확 문자열 치환 + assert 카운트(줄 번호 비의존 편집)"]
key-files:
  created:
    - ".planning/phases/08-pdf/08-01-SUMMARY.md"
  modified:
    - "report/draft.md (+54 / −50, 248줄 → 252줄)"
decisions:
  - "D-01 · D-02 · D-04 · D-07(1장 URL) · D-08 · D-10 · D-13 · D-14(회사 수치) · D-15를 grep 증명 가능한 형태로 구현(.planning/phases/08-pdf/08-CONTEXT.md)"
  - "커밋 없음 — 08-05에서 사용자 승인 후 일괄(프로젝트 규칙 CLAUDE.md)"
metrics:
  duration: "약 25분"
  completed: 2026-09-06
---

# Phase 8 Plan 01: draft.md 1~4장 압축·정리 Summary

`report/draft.md` 1~4장에서 개발 과정 표기(Phase·Day·freeze·`make serve`·마커)를 0건으로 만들고, 필수 문장 6개를 본문 줄로 승격하고, 4장 해석 3문단(2,442바이트)을 5문장 + 각주 2줄로 줄이고, 그림 번호를 1~5로 재정렬하면서 1~4장 H2 12개 전부에 4축 태그를 붙였다. 5장은 바이트 동일하다.

## 무엇을 했나 — 태스크별 바뀐 절

### Task 1 — 1·2장

| 항목 | 바뀐 절 | 내용 |
|---|---|---|
| 1-a 조판 지시 삭제 | 문서 제목 아래 | blockquote 2줄(`> 조판:` · `> 분량 배분`) 삭제, `---`는 유지 |
| 1-b 데모 URL | `# 1.` 바로 아래(3번째 줄) | `데모: https://millie-rec-production.up.railway.app/#/ (… 가동 감시 https://stats.uptimerobot.com/20M6QwPo7z)` 1줄 |
| 1-c 축 태그 | §1-1 `[①]` · §1-2 `[①]` · §1-3 `[①]` · §2-2 `[②③]` | H2 끝에 태그만 추가 |
| 1-d 4축 표 | §1-1 blockquote 아래 | 리드 1문장 + 4행 표(① 추천 목표 / ② 활용 데이터 / ③ 추천 구조 / ④ 성능 평가). QRS 첫 등장이 이 표로 이동 → §1-3 표는 `**QRS**`로 축약 |
| 1-e 그림 번호 | §1-4 `(그림 1) [②]` · §2-1 `(그림 2) [③]` | 1장 신호 그림이 그림 1, 2장 파이프라인이 그림 2 |
| 1-f mermaid 축약 | §1-4 | `flowchart LR` 20줄(subgraph 3개) → `flowchart TD` 12줄(펜스 포함), 3단 높이 |
| 1-g 필수 문장 승격 | §1-4 표 아래 문단 | 첫 문장을 `취향 설정 화면은 … **미선택 책은 negative가 아니다** — 노출 위치 때문에 못 본 것일 뿐이다.`로 교체(문단 3문장 유지) |
| 1-h 구현 1문장 | §2-2 마지막 문단 | `**구현 현황.** …` 4문장 → `**구현.** 파이프라인 4단계가 코드 폴더와 1:1이고 경계는 아키텍처 테스트가 강제한다.` |

### Task 2 — 3장

| 항목 | 바뀐 절 | 내용 |
|---|---|---|
| 2-a 축 태그·그림 번호 | §3-1 → `## 3-1. 운영 3계층 (그림 3) [③]` · §3-2 `[③]` · §3-3 `실서비스 ↔ 데모 대응 [③]` | H2의 "요청마다 …" 문장은 본문으로 내려감, "5일" 제거 |
| 2-b 필수 문장 승격 | §3-1 계층 표 아래 | `**요청마다 무거운 계산을 다시 하지 않는다** — 계층 배치의 기준은 지연 예산이다. …` 3문장. `추천 API 장애가 …`는 이 문단에서 분리 |
| 2-c 구현 1문장 | §3-1 마지막 문단 | `**추천 API 장애가 메인 장애가 되어선 안 된다.** 파이프라인이 예외를 던져도 200 + 인기 행을 반환하는 것이 테스트로 존재한다(\`tests/serving/test_smoke.py\`의 fallback 200 테스트).` — `make serve` 삭제, 테스트 이름 1개 유지 |
| 2-d 미채택 이유 분리 | §3-2 표 아래 문단 | LLM · Two-Tower · ALS 각 1문장으로 분리(`**의도적으로 넣지 않은 것.**` 한 문단) |
| 2-e 실측 불릿 → 각주 | §3-3 대응표 아래 | `- (Day 1 실측 …)` · `- (Day 2·Day 4 실측 …)` 2불릿(1,596바이트) 삭제 → `각주 — ` 2줄. 수집일·파일명·`books_kr.json`·SVD 128·5초 폴링·다운타임 초 전부 삭제, 9,447권·82.5%·0.356 + 출처 2개는 보존 |
| 2-f 표 열 제목 | §3-2 표 머리 | `5일 MVP (구현)` → `MVP (구현)` |

### Task 3 — 4장

| 항목 | 바뀐 절 | 내용 |
|---|---|---|
| 3-a 축 태그·그림 번호 | §4-1 `(그림 4) [④]` · §4-2 `[④]` · §4-3 `실서비스 제약 → 설계 결정 [③④]` | 부제 `(제약이 아키텍처를 결정했다)` 삭제 |
| 3-b 회사 수치 제거 | §4-1 mermaid 아래 문단 | `24만 권 카탈로그` → `수십만 권 카탈로그`(위협 T-08-05) |
| 3-c 표 머리말·오타 | §4-1 실측 표 | `**실측 (Phase 4 완료, …)**` → `**실측 (\`results/latest_states.csv\` · Goodbooks-10k · holdout · seed 42)**`, `콘텍츠` → `콘텐츠` 2곳. **비교표 8행 유지** |
| 3-d 비교 막대 자리 표시 | 비교표 마지막 행 아래 | `(그림 5 · 비교 막대 — \`report/figures/eval_bar.png\`, Notion 삽입 · 폭 1/2)` + `그림 5. 온보딩 직후(n=0) 상태의 4 variant × …` 캡션 |
| 3-e 해석 5문장 | 비교표 아래 3문단 | 해석·측정 설계·각주 3문단 삭제 → 2문단(5문장) + `각주 — Goodbooks-10k…` + `각주 — 고정 상수: …` |
| 3-f §4-3 표 정리 | 응답 지연 · 데이터 품질 · 모니터링 행 | `Phase 1 테스트` → `fallback 200 테스트` + `variant 공통 전역 p95 — 셀 혼합 bench` 구절(Codex 2회차 C5, `.planning/phases/07-deploy/07-04-SUMMARY.md` "Task 2 — Codex" 표) · `Phase 2 dedupe` → `멱등 dedupe 테스트` · 모니터링 행에서 `/metrics`·`prometheus-client`·`GET /api/dashboard` 삭제 |

## eval_bar.png 라벨 대조 (재생성 없음)

**일치 ✅** — `report/figures/eval_bar.png`의 막대 위 수치 라벨 12개(pop 0.063/0.054/0.764 · cf 0.117/0.107/0.643 · hybrid 0.118/0.110/0.606 · hybrid_div 0.116/0.107/0.684)가 `results/latest.csv` 4행과 전부 같고 제목도 `Track A (Goodbooks-10k, holdout, n_users=2000)`로 캡션과 일치한다. 다만 hybrid_div의 ild@10 라벨 `0.684`가 범례 `ild@10` 텍스트와 시각적으로 겹친다 — 숫자는 맞으므로 재생성하지 않았고, Notion 삽입 시 폭 1/2로 줄이면 더 겹칠 수 있으니 조판 단계(08-04) 육안 확인 항목으로 남긴다.

## 장별 한글 자수 (D-16 계측)

`re.findall(r'[가-힣]')` 기준. `산문` = 표·mermaid·그림 캡션 줄 제외.

| 장 | 전 전체 | 후 전체 | 증감 | 전 산문 | 후 산문 | 증감 |
|---|---:|---:|---:|---:|---:|---:|
| 1. 추천 목표와 활용 데이터 | 1,054 | 1,120 | +66 | 524 | 584 | +60 |
| 2. 추천 구조 | 1,065 | 1,011 | −54 | 455 | 401 | −54 |
| 3. 기술 스택과 시스템 아키텍처 | 1,471 | 1,320 | −151 | 607 | 475 | −132 |
| 4. 성능 평가 방법 | 1,371 | 1,263 | −108 | 745 | 599 | −146 |
| 5. 도서 도메인 고유 설계 (미변경) | 1,193 | 1,193 | 0 | 1,152 | 1,152 | 0 |

1장 증가분은 4축 표(D-16 계측 대상이지만 `/pdf-check` 판정 기준인 산문에서는 표 제외)와 데모 URL 1줄 때문이다. 3장 1,320·4장 1,263은 결정 D-05의 감축 목표(3장 ≤1,100 · 4장 ≤1,150, `.planning/phases/08-pdf/08-CONTEXT.md`)를 전체 기준으로는 아직 넘는다 — 그 목표는 08-03 Task 1(계측·차순 삭제) 몫이라 이 플랜에서 더 지우지 않았다. 산문 기준으로는 두 장 모두 여유가 있다.

## 검증 결과

### 태스크별 `<verify><automated>`

| 태스크 | 결과 |
|---|---|
| Task 1 | `PASS` |
| Task 2 | `PASS` |
| Task 3 | `PASS` |

### 태스크별 acceptance_criteria

**Task 1** — 조판 0 / 분량 배분 0 · URL 1(H1 이후 3번째 줄, `OK`) · 리드 1 · `| ① 추천 목표 |` 1 · `| ④ 성능 평가 |` 1 · `QRS(Qualified Reading Start: 유효 독서 시작)` 1 · 1·2장 H2 6개 전부 태그(무태그 0) · `## 1-4 … (그림 1) [②]` 1 · `## 2-1 … (그림 2) [③]` 1 · 첫 mermaid 12줄(≤14) · 전체 mermaid 4 · 본문 줄 `미선택 책은 negative가 아니다` 1 · `**구현.** 파이프라인 4단계가…` 1 · 2장 `구현 현황` 0 · 개발 과정 표기 0 · 본문 줄 CTR 1 · 재설정≠초기화 1 · 3~5장 diff 없음.

**Task 2** — 3장 개발 과정 표기·`5일` 0 · `## 3-1. 운영 3계층 (그림 3) [③]` 1 · `## 3-2 … [③]` 1 · `## 3-3. 실서비스 ↔ 데모 대응 [③]` 1 · 본문 줄 `요청마다 무거운 계산을 다시 하지 않는다` 1(정확 문자열 1) · `**추천 API 장애가 …** 파이프라인이 예외를 던져도 200 + 인기 행을…` 1 · `구현 현황` 0 · LLM/Two-Tower/ALS 각 1 · `**의도적으로 넣지 않은 것.**` 1 · `각주 — ` 2 · `- (Day` 0 · 각주 1에 9,447권·82.5%·0.356·`results/millie_coverage.csv`·`results/millie_edges_gate.json` 각 1 · 각주 2에 `model_version`·`SQLite 볼륨` 각 1 · 삭제 대상 문자열(수집일·`books_kr.json`·`SVD 128`·`5초 폴링`·`30~40초`·`5~15초`) 0 · mermaid 4 · 1·2장·4·5장 diff 없음.

**Task 3** — 4장 개발 과정 표기·`24만` 0 · variant 행 8 · `0.240` 2 · `pop 0.087 대 hybrid 0.240` 1 · `0.087→0.240` 0 · `cf 0.237과 hybrid의 차이는 0.003` 1 · `0.780` 1 · `콘텍츠` 0 · `report/figures/eval_bar.png` 1 · 그림 5 캡션 1 · `results/latest.csv` 1 · **해석 종결어미 `다.` 5개(정확히 5문장)** · `각주 — Goodbooks-10k(CC BY-SA 4.0)` 1 · 고정 상수 각주 정확 문자열 1 · `측정 설계` 0 · `temporal split(시간순 분할)` 1 · `두 숫자를 한 표에 섞지 않는다` 1 · 모니터링 행 1 · `지표 수집기(Prometheus→Grafana)는 설계만` 1 · `prometheus-client|/metrics|/api/dashboard` 0 · `variant 공통 전역 p95` 1 · `79.5ms` 1 · `fallback 200 테스트` 1 · `test_delete_personalization_then_level3_until_reconsent` 1 · §4-1~§4-3 태그 각 1 · mermaid 4 · `그림 1`~`그림 5` 전부 존재 · 1~3장·5장 diff 없음.

### 플랜 `<verification>` 5항목

| # | 항목 | 결과 |
|---|---|---|
| 1 | `grep -c "^# [1-5]\."` = 5 · `grep -c '^```mermaid'` = 4 | ✅ 5 / 4 |
| 2 | 1~4장에 `Phase [0-9]\|Day [0-9]\|freeze\|구현 완료\|make serve\|[Phase\|[재확인]\|24만\|5일` = 0 | ✅ 0 |
| 3 | 필수 문장 7개가 본문 줄(제목·표 셀 아님)에 존재 | ✅ 7개 전부 각 1회 (5장 몫 포함 7개 모두 1~4장 본문에 존재) |
| 4 | 1~4장 H2 12개 전부 `[①~④]`로 끝남 | ✅ H2 12 / 무태그 0 |
| 5 | 5장이 `aa5cc91`과 diff 없음 | ✅ 빈 출력 |

추가(위협 등록부): `grep -c '\.assets' report/draft.md` = 0 (T-08-01 · T-08-03).

## 커밋

**커밋 없음(08-05에서 일괄, 사용자 승인 후).** `git add`·`git commit`·`gsd-tools commit`을 한 번도 실행하지 않았다. `.planning/STATE.md`·`.planning/ROADMAP.md`·`.planning/REQUIREMENTS.md`도 건드리지 않았다(08-05 소유).

작업 트리 상태:

```
 M .planning/STATE.md                 ← 이 플랜 착수 전부터 변경돼 있던 것(미수정)
 M report/draft.md                    ← 이 플랜의 산출물
 M results/millie_edges_gate.json     ← 다른 세션(미수정)
?? .planning/phases/08-pdf/08-01-SUMMARY.md  ← 이 플랜의 산출물
?? artifacts/serving/review_agg_kr.json · report/plan_surfaces_search_feed.md
?? results/review_coverage.csv · results/review_tuples_report.json
?? scripts/{build,collect,export}_millie_reviews.py · scripts/millie_review_{js,parse}.py
?? tests/data/test_millie_review{_parse,s_build}.py · tests/fixtures/millie_reviews/
                                      ← 전부 다른 세션(미수정)
```

## Deviations from Plan

없음 — 플랜에 적힌 문자열·순서 그대로 실행했다. 재측정(`make eval`·`make bench`·`make millie*`)·그림 재생성은 하지 않았고 `results/`는 읽기만 했다.

기록해 둘 관찰 2건(수정하지 않음, 08-03·08-04 인계):

1. 4장 첫 각주의 `**실서비스 평가는 반드시 temporal split(시간순 분할)**로` — 플랜 지정 문자열 그대로 넣었다. 굵게 닫는 `**` 뒤에 공백 없이 조사 `로`가 붙어 있어 Notion 렌더에서 굵게가 풀릴 가능성이 있다. 조판 미리보기(08-04) 확인 항목.
2. 위 "장별 한글 자수" 절의 3·4장 D-05 목표 초과분.

## Known Stubs

없음. 이 플랜은 코드를 만들지 않는다.

## Self-Check: PASSED

- `report/draft.md` — 존재 (252줄, `+54/−50`)
- `.planning/phases/08-pdf/08-01-SUMMARY.md` — 존재
- 커밋 해시 — 해당 없음(설계상 커밋 0, `<commit_override>`)
- 5장 vs `aa5cc91` — diff 빈 출력
</content>
</invoke>
