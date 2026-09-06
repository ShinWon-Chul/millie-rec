---
status: diagnosed
phase: 03-millie-catalog
source: [03-01-SUMMARY.md, 03-02-SUMMARY.md, 03-03-SUMMARY.md, 03-04-SUMMARY.md, 03-05-SUMMARY.md, 03-06-SUMMARY.md, 03-07-SUMMARY.md]
started: 2026-09-05T11:48:18Z
updated: 2026-09-05T11:52:43Z
snapshot: "8,708권 (2026-09-05 20:28 make millie, 배치 진행 중) — Task 4 최종 스냅샷 후 재검증 예정"
---

## Current Test
<!-- OVERWRITE each test - shows where we are -->

[testing complete — 2 items blocked(Task 4 · Phase 5), 1 issue diagnosed]

number: 9
name: 서버 주입 level 0 — /api/recommend 가 밀리 책으로 응답 (사람 판단)
expected: |
  GET /api/recommend?seeds=1,2,3&k=5 → fallback_level 0 · model_version pop_v1 · rows[0].row_id trending · items 5개(1·2·3 제외).
  Advisor 실측(콜드 스타트 서버, 포트 8013): items [1004, 2081, 2843, 1060, 4320],
  제목 ['불편한 편의점', '도슨트북', '무료', '도슨트북', '홍학의 자리'] — 전부 한글, 표지 호스트 img./image.millie.co.kr, difficulty 0.25~0.64.
  사람 판단 요청: 이 5권이 "밀리 인기 순 실제 도서"로 보이는가? (관측: 3위 제목이 '무료', '도슨트북' 제목 2권 — eligible 규칙(D-14)엔 걸리지 않는 데이터 품질 항목)
awaiting: user response

## Tests

### 1. Cold Start Smoke Test
expected: 서버 프로세스 종료 → 빈 DATA_DIR 로 처음부터 기동 → 오류 없이 부팅, 스키마 적용, /health 200·db_ok true·Must 4테이블 0행.
result: pass
evidence: "Advisor 자동 검증 — 빈 DATA_DIR(scratch)로 uvicorn 8013 기동 0.82s, /health ok · db_ok True · 7테이블 0행(users·preference_snapshots·events·recommendations + ratings·candidate_sets·book_stats), millie.db+wal 생성, 로그 error 0. /docs 200 · / 200"

### 2. DATA-01 사전순 surrogate book_id · id_map append-only
expected: books_kr.parquet 의 book_id 가 data/id_map.csv 에서 오고, 재빌드 후에도 기존 행 변동 0(HEAD 1,066행 바이트 동일), book_id 1..N 연속·유일.
result: pass
evidence: "id_map 8,710행 · book_id·millie_id unique · 1..8710 연속 · git show HEAD 1,066행과 head -1067 diff 빈 출력 · Plan 01 사본(6,980줄) 이 재빌드 파일의 접두로 동일 · git diff --numstat 삭제 0"

### 3. DATA-02 계약 컬럼 9개 문자 일치 · book_format 3종
expected: books_kr.json 행 키에 book_id title authors image_url average_rating ratings_count original_publication_year categories tags 가 문자 그대로 있고 book_format ∈ {전자책, 오디오북, 챗북}.
result: pass
evidence: "8,708행 · 28키 · 계약 9키 ⊂ 키 집합 True · book_format 전자책 5,627 / 오디오북 2,725 / 챗북 356"

### 4. DATA-03 커버리지 게이트 → results/millie_coverage.csv
expected: title 100% · image_url ≥99% · categories ≥95% · completion_prob ≥70% · formats ≥90% · seg_dist ≥70% · 카테고리 ≥8종 · 20권 이상 ≥6 분야, test_coverage_gate passed, csv 에 _n_skipped_titleless 등 행 존재.
result: pass
evidence: "title 1.0000 · image_url 1.0000 · categories 1.0000 · completion_prob 0.8385 · formats 0.9773 · seg_dist 0.8024 · _category_distinct 74 · _categories_ge_20 25 · _n_records 8708 · _n_success 8740 · titleless 1(0.011% ≤ 0.5%) · 게이트 테스트 passed(전체 233 passed 안)"

### 5. DATA-04 완독지수 파생 난이도
expected: resid_z·len_z·difficulty 3컬럼, difficulty = 1/(1+exp(resid_z)) (= σ(−resid_z)), 결측은 difficulty_source=category_prior · resid_z 0 · difficulty None(json null).
result: pass
evidence: "books_kr.json: difficulty null 1,406 == category_prior 1,406 · prior 행 resid_z 전부 0.0 · measured 7,302행 시그모이드 항등 True(1e-6) · 손계산 6건(test_millie_difficulty) 통과 · 어댑터 stats(1) source millie_index difficulty 0.857"

### 6. DATA-05 content_sim 이웃 · 이웃 게이트 3
expected: item_edges_kr 이 title+description+curator_note 문자 2~4gram TF-IDF top-20(+category_best) 이고 self-edge 0 · 전 도서 이웃 ≥5 · 동일 카테고리 비율 ≤0.70, results/millie_edges_gate.json 존재.
result: pass
evidence: "n_books 8708 · n_edges 323,223(content_sim 158,546 · category_best 164,677) · self_edges 0 · min_degree 21 · n_orphans 0 · same_category_share 0.3662 · D-10 조치 미발동(스크립트 무변경) · 첫 책 이웃 = 같은 시리즈(위쳐)"

### 7. DATA-06 catalog_kr 어댑터 · 밀리 텍스트 미노출
expected: CatalogKR 이 Catalog·Neighbors·BookStatsSource 를 만족, meta() 에 description·curator_note·seg_dist 없음, data 슬라이스가 contracts 만 import(아키텍처 테스트 통과), pandas 미사용.
result: pass
evidence: "CatalogKR.load() 실 아티팩트: meta 28키·제외 키 ∅ · popular(n=10) 전부 eligible · neighbors(1,n=3) [(159,0.602),(1121,0.2),(1122,0.2)] · test_architecture 3 passed · test_catalog_kr 12 + test_vectors_kr 4 passed · pandas import 0"

### 8. DATA-07 make millie-export 산출물 4+1
expected: artifacts/serving/{books_kr,item_edges_kr,popularity_kr}.json + content_vectors_kr.npz + demo/fallback/popular.json 이 파일당 <50MB, description 0건, popular.json 이 RecommendOut 으로 파싱된다.
result: pass
evidence: "7.6MB · 10.2MB · 7.3MB · 4.5MB · 18.7KB, >50MB 0 · description/curator_note/seg_dist/millie_id 0건 · itemknn 0건 · npz (8708,128) float32 행 L2 1.0 · ids == books · popular.json RecommendOut OK(level 3 · fallback_v1 · trending 40권, 1위 불편한 편의점)"

### 9. 서버 주입 level 0 — /api/recommend 가 밀리 책으로 응답 (사람 판단)
expected: GET /api/recommend?seeds=1,2,3&k=5 → fallback_level 0 · pop_v1 · trending 5개(1·2·3 제외), 제목이 한글 밀리 도서. 사람 판단: 5권이 "밀리 인기 실제 도서"로 보이는가('무료' 제목·'도슨트북' 중복 관측).
result: issue
reported: "Advisor 직접 검증(사용자 위임 '직접 검증 진행'): '도슨트북'은 책 제목이 아니라 밀리 기능 배지 라벨. 파서가 헤더 첫 줄(배지)을 title 로, 배지 설명을 subtitle 로 잡았다. 카탈로그 8,708권 중 728권(8.4%)의 title 이 배지 라벨('읽던 지점 그대로 이어듣기' 444 · '도슨트북' 116 · '무료' 64 · '오브제북' 30 · '웹소설' 29 · '웹툰' 27 · '오디오웹소설' 18). 그중 pop_rank ≤40 이 10권 → level 0 상위 5 에 2권 노출. API 형태·순서는 정상."
severity: major

### 10. 익명 요청 level 3 — trending 이 카탈로그 인기로 채워짐
expected: GET /api/recommend(익명) → fallback_level 3 · fallback_v1 · items [] · rows[0].items 40권(pop_rank 순, 비자격 제외) · user_state_weights 전부 0.
result: pass
evidence: "level 3 fallback_v1 · items 0 · trending 40 · 앞 5 [1004,2081,2843,1060,4320] · weights {alpha 0, beta 0, gamma 0} · model=pop 강제 시 forced True level 0"

### 11. DATA-08 popularity_kr 세그먼트 인기 (Should)
expected: popularity_kr 에 all + 연령×성별 12세그먼트 행, 라벨 밀리 표기('40대 여성'), 세그먼트별 rank 연속; fallback level 2 응답이 전역 인기와 다르다.
result: blocked
blocked_by: other
reason: "데이터 전제는 통과(13종 · all 8,708 + 12×6,987 · 세그먼트 1위가 all 1위와 7/12 상이, distinct top-1 = 5). 'level 2 응답이 다름' 은 Phase 5 state.py·fallback level 2 이후 검증(결정 D-15 — Phase 3 완료 기준 아님)"

### 12. 최종 스냅샷 수치 일치 (03-06 Task 4)
expected: 배치 종료 후 make millie 1회 → results/ 최종 값 == report/draft.md P3 문장·트래킹 03 §2·개발일지 D66 수치, draft 의 '[숫자는 … 교체]' 마커 0건, 이후 make millie 재실행 금지 기록.
result: blocked
blocked_by: other
reason: "밀리 수집 배치 2샤드 진행 중(사용자: 종료 시 알림). 현재 draft 는 8,708권 + 교체 마커 유지"

## Summary

total: 12
passed: 9
issues: 1
pending: 0
skipped: 0
blocked: 2

## Gaps

- truth: "GET /api/recommend 상위 항목과 카탈로그 title 이 실제 밀리 도서 제목이다(DATA-02 계약 컬럼 title 의 의미 정합)"
  status: failed
  reason: "Advisor 검증: 728/8,708권(8.4%) title 이 밀리 기능 배지 라벨(읽던 지점 그대로 이어듣기·도슨트북·무료·오브제북·웹소설·웹툰·오디오웹소설). 커버리지 게이트는 존재율(title 100%)만 봐서 통과했다"
  severity: major
  test: 9
  evidence_lines: "실페이지 헤더(09-05 20:5x, 1회 렌더): book 213 = [로그인, 전자책, 오디오북, 챗북, 도슨트북, 종이책에서 읽던 지점 바로 이어읽기, '12가지 인생의 법칙 (40만 부 기념 스페셜 에디션)', '혼돈의 해독제', '조던B.피터슨 지음, 강주헌 옮김', 4.1, 메이븐, 인문, 2023.02.10, 이 책이 담긴 서재 11만+] · book 1550 = [로그인, 무료, 챗북, '따박따박 경제상식 [ETF 첫걸음]', '3화. 재테크 초보도 할 수 있는 ETF 투자 첫걸음', 밀리의서재 편집부, 4.8, 밀리의 서재, 챗북, 2025.04.14, 이 책이 담긴 서재 2.2만+] — 스크래치 page_213.json·page_1550.json"
  root_cause: "scripts/millie_parse.py::_header — '로그인' 뒤 선행 노이즈 스킵 집합 _NAV_NOISE(전자책|오디오북|챗북|종이책|종이책에서 읽던 지점 바로 이어읽기|미서비스|pdf)에 기능 배지 라벨 7종이 없어 배지 줄이 block[0]=title, 그 설명 줄이 block[1]=subtitle 로 들어간다. 원문 라인은 저장하지 않으므로(raw HTML 미보관 규칙) 진짜 제목은 재수집으로만 복구된다"
  artifacts:
    - path: "scripts/millie_parse.py"
      issue: "_NAV_NOISE 에 배지 라벨 부재 · 헤더 첫 줄을 무조건 title 로 채택"
    - path: "tests/data/test_millie_catalog.py"
      issue: "커버리지 게이트가 title 존재율만 검사 — 배지 라벨 title 을 잡는 단언 없음"
    - path: "scripts/collect_millie.py"
      issue: "멱등(기존 millie_id skip)이라 영향 728건을 다시 렌더할 옵션이 없다(--recollect <ids 파일> 필요)"
    - path: "tests/fixtures/millie/"
      issue: "배지 라벨이 헤더에 있는 픽스처가 없어 결함이 테스트에서 드러나지 않았다"
  missing:
    - "millie_parse._NAV_NOISE 에 배지 라벨 7종(+설명 줄) 추가 — 배지 픽스처 1~2건으로 RED→GREEN(TDD)"
    - "커버리지 게이트에 'title ∉ 배지 라벨 집합' 단언 + results/millie_coverage.csv 에 _n_badge_title 행"
    - "collect_millie.py --recollect <ids.txt> 옵션(대상 id 만 재렌더·기존 줄 대체 또는 append 후 read_records 가 마지막 줄 우선 — 현 dedup 규칙 활용)"
    - "영향 728 id 목록(title ∈ 배지 집합) 추출 → 배치 종료 후 재수집(≈728×7.5s/2샤드 ≈ 45분) → make millie(Task 4 최종 스냅샷과 통합)"
  debug_session: ""

