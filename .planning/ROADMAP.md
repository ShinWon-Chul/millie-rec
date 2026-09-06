# Roadmap: millie-rec — 밀리의서재 메인 추천 시스템 (5일 데모 + PDF)

**Created:** 2026-09-05
**Granularity:** standard (5~8 페이즈)
**Milestone:** v1 사전과제 제출물 (2026-09-03 ~ 09-08, 사람 시간 12~15h)

## Overview

제출물은 PDF 1~5페이지다. 코드는 그 PDF에 들어갈 **실측 비교표(Track A, Goodbooks-10k) · 밀리 카탈로그 위의 데모(Track B) · 본인 5권 정성 케이스 · 배포 URL**을 만들기 위해서만 존재한다. 그래서 이 로드맵은 "설계를 구현하는 순서"가 아니라 **"설계의 주장이 실행되는 코드와 실측 숫자로 바뀌는 순서"**다.

먼저 아티팩트 없이도 뜨는 서버를 띄우고(Phase 1: 로컬 서빙 스켈레톤), 그 서버에 두 트랙의 데이터 기반을 병렬로 붙인다(Phase 2: Track A 정량 평가 기반 ‖ Phase 3: 밀리 카탈로그 빌드). 그 위에 4단계 파이프라인을 얹어 비교표 4행과 모델 freeze를 만들고(Phase 4: 추천 파이프라인과 모델 freeze), 같은 서버에 Must 서빙과 데모 8페이지를 병렬로 완성한다(Phase 5: 서빙 Must 완성 ‖ Phase 6: 데모 재구성). 마지막으로 배포 URL을 붙이고(Phase 7: 배포) 숫자를 PDF로 옮긴다(Phase 8: PDF 제출물).

**전 과정 로컬 기동 원칙**(`../.claude/rules/local-run.md`): Phase 1 종료부터 서버가 떠 있고, **모든 페이즈의 성공 기준에 `uv run pytest -q`와 `make smoke` PASS가 들어간다.** 배포는 로컬 통과 후에만 한다.

**데이터 2트랙, 숫자 불혼합**(`CLAUDE.md` §2-8): 비교표 숫자는 Track A(Goodbooks-10k)에서만 나오고, 데모 화면·앵커·배지·난이도·본인 5권은 Track B(밀리 공개 도서 페이지)에서만 나온다. 데모 이웃은 콘텐츠 유사도이며 응답에 `source_channels=content`로 표기한다(결정 '데모 이웃은 콘텐츠 유사도'(개발일지 2026-09-04 파일 항목 D42)).

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): 계획된 마일스톤 작업
- Decimal phases (2.1, 2.2): 계획 후 삽입된 긴급 작업 (INSERTED 표기)

- [ ] **Phase 1: 로컬 서빙 스켈레톤** - 아티팩트·DB·네트워크 없이 `make serve`로 서버·정적 데모·fallback 추천이 뜬다 (Day 1)
- [x] **Phase 2: Track A 정량 평가 기반** - Goodbooks-10k holdout에서 3지표와 `pop` 실측 1행이 `results/`에 남는다 (Day 1, Phase 3과 병렬) (completed 2026-09-05)
- [ ] **Phase 3: 밀리 카탈로그 빌드** - 밀리 공개 도서 전량 → `books_kr`·content_sim 이웃·완독지수 난이도가 게이트를 통과해 서빙 아티팩트가 된다 (Day 1 밤~Day 2, Phase 2와 병렬)
- [x] **Phase 4: 추천 파이프라인과 모델 freeze** - 후보 3통로 → 가중합 랭킹 → MMR·가드로 비교표 4행과 본인 5권 케이스가 나오고 Day 3에 모델이 얼어붙는다 (Day 2~3) (completed 2026-09-06 — 🧊 freeze 선언, verification passed 5/5)
- [x] **Phase 5: 서빙 Must 완성** - Must 엔드포인트 9개·SQLite 4테이블·Nearline·fallback cascade·p95 < 200ms가 떠 있는 서버 위에 붙는다 (Day 2 골격 → Day 3~4, Phase 6과 병렬) (completed 2026-09-06 — 12 plans · bench p95 79.5ms · verification passed 6/6, Codex 필수 fix 7 + 토론 3 반영(결정 D79))
- [ ] **Phase 6: 데모 재구성** - v1 데모 27파일을 8페이지 해시 라우팅·새 스키마·밀리 카탈로그로 재구성해 로컬 API에 붙인다 (Day 2~4, Phase 5와 병렬)
- [ ] **Phase 7: 배포** - Day 2 Railway 스켈레톤으로 배포 리스크를 먼저 노출하고 Day 4에 본배포한다 (Day 2 · Day 4)
- [ ] **Phase 8: PDF 제출물** - `results/`의 숫자만으로 P1~P5를 채우고 5페이지 이내로 조판·제출한다 (Day 4 문장 → Day 5 조판)

**병렬 관계:** Phase 2 ‖ Phase 3 (Day 1, 레인이 Model / Data-B로 분리) · Phase 4 ‖ Phase 5 ‖ Phase 6 (Day 3, Model / Serving / Demo 레인) · Phase 5 ‖ Phase 6 (Day 2~4). `config.json`의 `parallelization: true`와 아키텍처 경계(`../.claude/rules/architecture.md` 레인 표)가 이 병렬의 근거다.

**Day 3 종료 = 모델·API 응답 형태 freeze.** Phase 4 종료 시점에 선언하고, 이후 페이즈는 새 모델·후보 통로·응답 필드를 추가하지 않는다(`CLAUDE.md` §2-4).

## Phase Details

### Phase 1: 로컬 서빙 스켈레톤
**Goal**: 개발자가 아티팩트·DB·네트워크·클라우드 없이 서버를 띄울 수 있고, 이후 모든 슬라이스를 "떠 있는 서버에 붙여" 검증할 수 있다.
**Day**: Day 1 (가장 먼저)
**Depends on**: 없음 (첫 페이즈. 두 계약 `contracts.py`·`serving/schemas.py`는 이미 freeze 완료)
**병렬**: 없음 — 이 페이즈가 끝나야 나머지가 서버에 붙는다
**Requirements**: SKEL-01, SKEL-02, SKEL-03, SKEL-04, SKEL-05 (전부 Must)

**착수 전** (`../.assets/설계서/구현 마일스톤/01_마일스톤_착수_프롬프트.md` §0 4단계):
1. 설계서 전수 조사 — 아키텍처 01 §3-2 API 계층·§3-4 데이터 저장·§3-11 fallback·§9-3 serving 파일 분할, 백엔드 서빙 01 §1 `/health`·§5 `/api/recommend`. 참고 입력 5개는 제외.
2. 기존 구현 인벤토리 — `serving/`은 `schemas.py`·`schemas_should.py`만 존재(일치·freeze), 나머지 미구현. `Dockerfile`·`railway.json`은 v2.1 일치.
3. 정합 판정과 재구성 — `demo/`는 이 페이즈에서 건드리지 않는다(구 `api.js`가 `hf.space`를 가리키므로 `?source=api`에서 fallback 배너가 뜨는 것이 정상).
4. 로컬 기동 확인 — 착수 전 `make test` 통과 확인, 완료 기준에 `make test`·`make smoke` 둘 다 포함.

**Success Criteria** (what must be TRUE):
  1. 개발자가 `make serve` 후 브라우저에서 `http://localhost:8000/`을 열면 `demo/` 정적 데모가 같은 origin에서 뜨고, `GET /health`가 200과 `HealthOut`(`model_version` null 허용)을 반환한다 — **SKEL-01** `make serve` 기동·`/health` 200 · **SKEL-02** 정적 데모 같은 origin 서빙
  2. 파이프라인이 주입되지 않은 상태에서도 `GET /api/recommend?seeds=1,2,3`이 `fallback_level=3`으로 200을 반환한다 — **SKEL-03** 파이프라인 없을 때 fallback 200, 수용 기준 '파이프라인 예외 → 인기 row 200'(PRD §9 수용 기준 표)의 최소 형태
  3. `contracts.DIR_DATA_LOCAL/millie.db`가 자동 생성되고 `schema.sql`의 Must 4테이블(`users`·`preference_snapshots`·`events`·`recommendations`)이 만들어진다 — **SKEL-04** SQLite 자동 생성·Must 4테이블
  4. `uv run pytest -q`와 `make smoke` PASS — **SKEL-05** `make smoke` 3점 확인, 이후 모든 페이즈의 공통 완료 기준(`../.claude/rules/local-run.md`)

**Should 꼬리**: 없음 (전 항목 Must).
**Plans:** 2 plans

Plans:
- [x] 01-01-PLAN.md — [TDD·wave 1·Serving 레인] `serving/schema.sql`·`db.py`·`fallback.py`·`api.py` + `contracts.MODEL_VERSION_FALLBACK` + `tests/serving/test_smoke.py`(10건): `/health`·level 3 `/api/recommend`·SQLite 7테이블 (SKEL-01·03·04)
- [x] 01-02-PLAN.md — [execute·wave 2·Advisor 조립] `app/server.py`(create_app + demo StaticFiles 마지막 마운트) + server 테스트 1건 + `make smoke` PASS·전체 스위트·사이드이펙트 감사 (SKEL-01·02·05)

### Phase 2: Track A 정량 평가 기반
**Goal**: PDF 비교표의 유일한 숫자 출처인 `results/`가 생기고, 3지표·온보딩 시뮬레이션·누수 방지가 테스트로 고정되어 이후 variant가 추가될 때마다 행만 늘면 된다.
**Day**: Day 1
**Depends on**: Phase 1 (`pop` 파이프라인을 떠 있는 서버에 주입해 검증)
**병렬**: Phase 3 (밀리 카탈로그 빌드)과 동시 실행 — 쓰기 영역이 Model 레인(`src/millie_rec/{data,retrieval,evaluation}/`)과 Data-B 레인(`scripts/`·`data/`)으로 분리된다
**Requirements**: EVAL-01, EVAL-02, EVAL-03, EVAL-04, EVAL-05, EVAL-06 (Must) · EVAL-07 (Should)

**착수 전**:
1. 설계서 전수 조사 — main 설계서 §6-1 Offline 3지표, PRD §6-1, 데이터 소스 01 §4-1 Track A 확정, `../.claude/rules/evaluation.md`.
2. 기존 구현 인벤토리 — `tests/conftest.py`의 Track A 합성 fixture는 유지. `data/`·`retrieval/`·`evaluation/` 슬라이스는 `__init__.py`만 있는 껍데기.
3. 정합 판정과 재구성 — Track B 파일(`scripts/`·`data/id_map.csv`)은 불변. 재구성 대상 없음.
4. 로컬 기동 확인 — 착수 전 `make smoke` PASS 상태에서 시작하고, 완료 시 `pop` 주입 후 다시 PASS.

**Success Criteria** (what must be TRUE):
  1. 개발자가 `make data && make eval`을 실행하면 `results/latest.csv`에 `pop` 행이, `results/eval_<ts>.json`에 `split_mode`·`n_users`·`seed`·`sha`가 기록된다 — **EVAL-01** Goodbooks 멱등 다운로드 · **EVAL-02** `ts` 없으면 holdout·`split_mode` 기록 · **EVAL-05** 4행 기록 구조, 수용 기준 '평가 4행 + split_mode 출력'(PRD §9 수용 기준 표)의 전제(4행 완성은 Phase 4)
  2. Recall@20·NDCG@10·ILD@10 손계산 케이스 테스트와 "학습에 본 아이템은 추천에서 제외" 테스트가 통과한다 — **EVAL-04** 3지표 순수 함수·누수 방지
  3. 온보딩 시뮬레이션이 테스트 유저의 첫 5권만 `explicit_seeds`로 노출하고, 미선택 책을 부정 신호로 학습하지 않음이 단위 테스트로 증명된다 — **EVAL-03** 온보딩 마스킹, 수용 기준 '미선택 책 ≠ 부정 신호'(PRD §9 수용 기준 표)
  4. n=0(온보딩 5권만)과 n≥k(행동 축적) 상태의 지표가 별도 표로 출력된다 — **EVAL-06** n=0 vs n≥k 분리, 수용 기준 'n=0 vs n≥k 지표 분리'(PRD §9 수용 기준 표) · ★시간 가변 가중치의 증거
  5. `uv run pytest -q`와 `make smoke` PASS — `pop` 파이프라인 주입 후 `/api/recommend`가 `fallback_level=0`으로 응답한다

**Should 꼬리**: **EVAL-07** 비교 막대그래프 `report/figures/eval_bar.png` 생성. 시간 부족 시 아키텍처 01 §8 티어 표 아래부터 버린다(완독 직후 행·별점은 가장 늦게 — 결정 '버리는 순서'(개발일지 2026-09-04 파일 항목 D40)). 그림이 없으면 PDF는 표만 싣는다.
**Plans:** 6/6 plans complete

Plans:
- [x] 02-01-PLAN.md — [TDD·wave 1·Model 레인 data] `data/goodbooks.py`(멱등 HTTPS 다운로드·parquet)·`load.py`(필터 유저≥5·아이템≥5)·`split.py`(holdout|temporal, `split_mode`)·`onboarding.py`(seeds 5권·n0/n20 두 상태·2,000명 표본)·`labels.py`(rating≥4) + `tests/data/` Track A 19건 (EVAL-01·02·03)
- [x] 02-02-PLAN.md — [TDD·wave 1·Model 레인 retrieval] `retrieval/popularity.py`(`PopularityRetriever` train만 fit·seen 제외·`artifacts/popularity.json` save/load)·`content.py`(`ContentVectors` tags TF-IDF, 벡터 부분만) + `tests/retrieval/` 11건 (EVAL-04)
- [x] 02-03-PLAN.md — [TDD·wave 1·Model 레인 evaluation] `evaluation/metrics.py`(3지표 손계산)·`harness.py`(Pipeline 평가·`seen ∩ R_u == ∅` 단언)·`report.py`(`latest.csv`·`latest_states.csv`·`eval_<ts>.json`·`git_sha`) + `tests/evaluation/` 18건 (EVAL-04·05·06)
- [x] 02-04-PLAN.md — [TDD·wave 2·Serving 레인] `serving/compose.py`(`build_response` 신설) + `serving/api.py` level 0 분기(D-11 기본 variant·D-12 trending 1행+items·D-13 익명 level 3·예외→level 3) + `tests/serving/test_recommend_level0.py` 7건 (Success Criterion 5)
- [x] 02-05-PLAN.md — [execute·wave 2·조립] `app/pipeline.py`(`PopPipeline`·`fit_pipelines`·`build_pipelines`)·`app/cli.py`(`data`·`eval --variant`)·`app/server.py`(`pipelines=build_pipelines()`) + `tests/app/` 7건(합성 parquet e2e) + smoke 서버 단정 아티팩트 조건부 (EVAL-01·05·06)
- [x] 02-06-PLAN.md — [execute·wave 3·실측] `make data`(유일한 네트워크) → `make eval` → `results/` 3파일·`artifacts/serving/eval_table.json`·`artifacts/popularity.json` → `make smoke` level 0 실측 → `report/draft.md` P4 1줄 → (Should) `evaluation/figures.py` → `report/figures/eval_bar.png` (EVAL-01·02·05·06·07)

### Phase 3: 밀리 카탈로그 빌드
**Goal**: 밀리 공개 도서 전량이 커버리지·이웃 게이트를 통과한 서빙 아티팩트가 되어, 데모·앵커·배지·난이도·본인 5권이 전부 한국 책 위에서 동작한다.
**Day**: Day 1 밤 ~ Day 2
**Depends on**: Phase 1 (카탈로그를 주입해 `/api/recommend`가 밀리 책으로 응답하는지 확인) · 야간 배치 종료 또는 `data/raw/millie_pages.jsonl` ≥ 600행
**병렬**: Phase 2 (Track A 정량 평가 기반)와 동시 실행
**Requirements**: DATA-01, DATA-02, DATA-03, DATA-04, DATA-05, DATA-06, DATA-07 (Must) · DATA-08 (Should)

**착수 전** — ②단계가 핵심:
1. 설계서 전수 조사 — 적재 계획 02 §3 스키마·§4 난이도·§5 별점 결측·§6 이웃·§7 게이트·§12 검증 절차, 데이터 소스 03 트래킹 §1 표, 확보 방안 01 §3-2 완화 규칙 6개.
2. 기존 구현 인벤토리 — `scripts/` 5개(`millie_parse`·`collect_millie`·`build_millie_catalog`·`build_millie_edges`·`export_millie_serving`)·`tests/data/` 3개·픽스처 8건·`data/id_map.csv` 1,066행이 **이미 설계 기준으로 작성돼 있다.** 적재 계획 02와 대조한 일치/불일치 표를 먼저 만든다.
3. 정합 판정과 재구성 — 150줄 초과 파일(`millie_parse`·`build_millie_catalog`·`collect_millie`) 분리 여부는 Advisor 판단. 불일치 파일은 파일명으로 명시.
4. 로컬 기동 확인 — 착수 전·후 `make smoke` PASS.

**Success Criteria** (what must be TRUE):
  1. 커버리지 게이트 테스트가 통과하고 `results/millie_coverage.csv`가 생긴다: title 100% · image_url ≥99% · categories ≥95% · completion_prob ≥70% · formats ≥90% · seg_dist ≥70% · 카테고리 종수 ≥8 · 20권 이상 분야 ≥6 — **DATA-01** 사전순 surrogate `book_id` · **DATA-02** 계약 컬럼 9개 문자 일치 · **DATA-03** 커버리지 게이트
  2. `item_edges_kr.parquet`가 이웃 게이트 3(self-edge 0 · 전 도서 이웃 ≥5 · 동일 카테고리 ≤70%)을 통과하고, `data/id_map.csv`를 이전 버전과 diff했을 때 기존 행 변동이 0이다 — **DATA-05** content_sim TF-IDF 이웃·게이트 3
  3. `data/catalog_kr.py`가 `Catalog`·`Neighbors`·`BookStatsSource`를 구현하고 `description`·`curator_note`를 노출하지 않으며, 난이도가 `σ(−resid_z)`·결측은 `difficulty=None`(가드 모집단 제외)이다 — **DATA-04** 완독지수 파생 난이도 · **DATA-06** 어댑터 텍스트 미노출
  4. `make millie-export` 후 `artifacts/serving/`에 4개 파일 + `demo/fallback/popular.json`이 파일당 <50MB·`description` 0건으로 생기고, 서버에 주입하면 `/api/recommend`가 밀리 책으로 응답한다 — **DATA-07** export 산출물
  5. `uv run pytest -q`와 `make smoke` PASS · `/contract-sync` 카탈로그 항목 통과

**Should 꼬리**: **DATA-08** `popularity_kr` 세그먼트(연령×성별) 인기 → fallback level 2 응답이 전역 인기와 다름. 시간 부족 시 아키텍처 01 §8 티어 표 아래부터 버린다(완독 직후 행·별점은 가장 늦게). 데이터 레인 자체의 버리는 순서는 적재 계획 02 §8(쪽수 진단 → coLoan → overlap@20 → BEST 확장 → `similar_readers` 소스 분리 → `popularity_kr`).
**Plans**: 7 plans · 4 waves (2026-09-05 planned)
- [x] 03-01-PLAN.md — 난이도 파생(`scripts/millie_difficulty.py`) + 카탈로그 빌더 유효 레코드·카운터·3컬럼 + 첫 실빌드·커버리지 게이트 (wave 1, Data-B, tdd) — DATA-01·02·03·04
- [x] 03-02-PLAN.md — `data/catalog_kr.py`·`data/vectors_kr.py` 어댑터 + conftest 20권 서빙 fixture (wave 1, Model, tdd) — DATA-04·06
- [x] 03-03-PLAN.md — content_sim 이웃 실측·게이트 3 → `results/millie_edges_gate.json` (wave 2, Data-B, execute) — DATA-05
- [x] 03-04-PLAN.md — `build_millie_popularity.py`(all) + export json 3파일·BOOK_FIELDS 28 (wave 2, Data-B, tdd) — DATA-07
- [x] 03-05-PLAN.md — `export_millie_vectors.py`(SVD 128 npz) + `export_millie_fallback.py`(RecommendOut popular.json) (wave 2, Data-B, tdd) — DATA-07
- [x] 03-06-PLAN.md — Advisor 조립: `app/` 카탈로그 주입·Track B pop, Makefile 게이트 순서, `make millie` 실측·전역 게이트·contract-sync·draft P3·트래킹·개발일지, 최종 스냅샷 재빌드 체크포인트 (wave 3, 조립, execute) — DATA-01~07
- [x] 03-07-PLAN.md — `popularity_kr` 연령×성별 12세그먼트 (wave 4, Data-B, tdd, Should — 시간 부족 시 이 플랜만 버림) — DATA-08

### Phase 4: 추천 파이프라인과 모델 freeze
**Goal**: 설계서의 4단계 파이프라인이 실제 코드로 존재하고, 그 결과가 비교표 4행과 본인 5권 앵커 1장이라는 PDF 증거가 된 뒤 모델이 얼어붙는다.
**Day**: Day 2 (후보 통로) → Day 3 (랭킹·재순위화·freeze)
**Depends on**: Phase 2 (평가 하네스·`pop` 기준선) · Phase 3 (밀리 카탈로그·이웃·난이도)
**병렬**: Day 3에 Phase 5 (서빙 Must 완성) · Phase 6 (데모 재구성)과 동시 실행 — Model 레인 단독 쓰기
**Requirements**: REC-01, REC-02, REC-03, REC-05, REC-07, REC-08 (Must) · REC-04, REC-06 (Should)

**착수 전**:
1. 설계서 전수 조사 — main 설계서 §5-1 4단계 파이프라인·§5-2 시간 가변 가중치·§5-6 난이도 4층·§5-7 앵커, 아키텍처 01 §3-3 추천 파이프라인, 브레인스토밍 구체화 A·C·F.
2. 기존 구현 인벤토리 — `retrieval/`·`ranking/`·`reranking/` 슬라이스는 껍데기. `contracts.py`의 `CandidateGenerator`·`Ranker`·`Reranker`·`ItemVectors`·`BookStatsSource` Protocol이 인터페이스 정본.
3. 정합 판정과 재구성 — 절댓값 피처 `|difficulty − user_level|`은 폐기된 설계다(부호 유지 gap으로 대체). 재구성 대상 코드는 없으나 옛 표기를 코드에 넣지 않는다.
4. 로컬 기동 확인 — 매 variant 조립 후 `make smoke`, `/api/recommend?model=` 쿼리로 4 variant 응답 확인.

**Success Criteria** (what must be TRUE):
  1. `make eval` 결과 `results/latest.csv`에 `pop`·`cf`·`hybrid`·`hybrid_div` 4행이 `split_mode`와 함께 남고, 서버에서 `model=` 쿼리로 4 variant가 서로 다른 책을 반환한다 — **REC-01** 후보 3통로 · **REC-02** `VARIANTS` 4종 dict 조립, 수용 기준 '평가 4행 + split_mode 출력'(PRD §9 수용 기준 표)
  2. `hybrid_div`의 ILD@10이 `hybrid`보다 높고, NDCG 하락 대비 다양성 이득을 해석한 문단이 `report/draft.md`에 남는다 — **REC-05** MMR 다양성 재순위화
  3. `user_state_weights`가 사용 가능한 성분으로 재정규화되어 신규 유저는 β=0으로 표시되고, 이벤트가 쌓이면 α가 감쇠한다 — **REC-03** α/β/γ 재정규화·갱신 · ★시간 가변 가중치
  4. `app/cli.py demo --seeds <밀리 카탈로그 내 본인 5권>`이 앵커 추천 1장을 출력하고, 그 이웃이 콘텐츠 유사도임을 출력에 병기한다 — **REC-07** 본인 5권 앵커 케이스(Track B 전용, 비교표 숫자와 섞지 않음)
  5. Day 3 종료에 모델·API 응답 형태 freeze가 `.planning/STATE.md`와 개발일지에 선언되고, `uv run pytest -q`와 `make smoke` PASS — **REC-08** Day 3 freeze 선언

**Should 꼬리**: **REC-04** 난이도 부호 gap·`gap⁺`·`n_completed×gap` 피처(결측은 가중 0) → 수용 기준 '난이도 4층 피처·ablation'(PRD §9 수용 기준 표) · **REC-06** 난이도 가드(완독 <3 유저에게 `source=millie_index ∧ resid_z<−1` 책 상단 제외) → 수용 기준 '난이도 가드(Should)'(PRD §9 수용 기준 표). 시간 부족 시 아키텍처 01 §8 티어 표 아래부터 버린다 — 난이도 계통은 Grafana scrape 바로 위라 **일찍 버리는 축**이고, 완독 직후 행·별점은 가장 늦게 버린다(결정 '버리는 순서'(개발일지 2026-09-04 파일 항목 D40)). 버릴 경우 PDF에 "설계만" 표기로 대체한다.
**Plans**: TBD

### Phase 5: 서빙 Must 완성
**Goal**: 심사자가 배포 URL에서 눌러볼 수 있는 API 표면 전체가 동작하고, "추천 API 장애가 메인 장애가 되지 않는다"·"p95 200ms 예산이 계층 배치를 결정했다"는 실서비스 주장이 코드와 실측으로 증명된다.
**Day**: Day 2 골격(가짜 Pipeline) → Day 3~4 구현
**Depends on**: Phase 1 (스켈레톤 위에 증분) · Phase 3 (카탈로그·이웃) · Phase 4 (파이프라인 주입, 단 골격은 가짜 Pipeline으로 먼저 시작)
**병렬**: Phase 6 (데모 재구성)과 동시 실행 — Serving 레인(`src/millie_rec/serving/`)과 Demo 레인(`demo/`)은 쓰기 영역이 겹치지 않고 HTTP 계약으로만 만난다
**Requirements**: SERV-01, SERV-02, SERV-03, SERV-04, SERV-05, SERV-06, SERV-07, SERV-08, SERV-09, SERV-10, SERV-13 (Must) · SERV-11, SERV-12, SERV-14 (Should)

**착수 전**:
1. 설계서 전수 조사 — 아키텍처 01 §3-2 API 계층·§3-4 SQLite·§3-5 Nearline·§3-8 개인정보·§3-9 품질 게이트·§3-10 A/B 배정·§3-11 fallback·§9-3 파일 분할, 백엔드 서빙 01 전부, 화면 구성 02 §5 이벤트 매핑.
2. 기존 구현 인벤토리 — Phase 1의 스켈레톤(`api.py`·`db.py`·`fallback.py`·`schema.sql`)과 freeze된 `schemas.py`·`schemas_should.py` 위에 증분한다.
3. 정합 판정과 재구성 — `schemas*.py`는 변경 금지(optional 추가만, Advisor). 파일당 ≤150줄, `serving`은 `contracts`만 import.
4. 로컬 기동 확인 — **매 브리프 후 `make smoke`**. Railway·외부 계정 없이 검증을 끝낸다.

**Success Criteria** (what must be TRUE):
  1. `GET /api/recommend`가 Must 5행(이어 읽기 → 앵커 행 → 페르소나 서가 → 지금 많이 읽는 책 → 새로운 발견)을 행 간 dedup 후 반환하고, 앵커 행 items의 `source`·`source_channels`·`channel_mix`가 `content`이며 `reason`이 "『시드』… 좋아하셨다면"이다 — **SERV-01** Page Composition Must 5행 · **SERV-02** 앵커 행 content 채널, 수용 기준 '온보딩 5권 → 앵커 row'(PRD §9 수용 기준 표)
  2. 취향 설정 흐름이 왕복한다: `GET /api/meta/onboarding`·`GET /api/candidates/onboarding` → `POST /api/preferences`(스냅샷 append·`cell` sha256·`library_add` 자동 기록) → 재설정 시 새 앵커가 나오고 이전 기록이 남는다. 건너뛰기·익명은 개인화 행 없이 인기·신간만, `DELETE …/personalization` 이후는 항상 level 3이다 — **SERV-04** 스냅샷 append · **SERV-05** 온보딩 메타·후보 · **SERV-07** 열람·삭제·철회 · **SERV-08** 비개인화 행, 수용 기준 '재설정 → 새 앵커·기록 보존'·'건너뛰기 → 비개인화 row만'·'동의 철회 → 비개인화 fallback'(PRD §9 수용 기준 표)
  3. 예산 초과·예외를 주입해도 응답이 항상 200이고 `fallback_level`이 1→2→3으로 내려가며, `POST /api/events`가 품질 게이트를 통과한 이벤트를 저장하고 모든 노출 로그에 `recommendation_id`·`model_version`·`row_id`·`position`이 있다 — **SERV-03** fallback cascade · **SERV-06** 품질 게이트·노출 로그 · **SERV-09** Nearline 루프(요청 핸들러는 이벤트만 적재), 수용 기준 '파이프라인 예외 → 인기 row 200'·'노출 로그 4필드'(PRD §9 수용 기준 표)
  4. `results/latency.json`에 p50/p95/p99가 기록되고 p95 < 200ms이며, `GET /api/showcase`의 비교표가 `artifacts/serving/eval_table.json`에서 `split_mode`·2트랙 `data_notice`와 함께 응답한다 — **SERV-10** 로컬 bench · **SERV-13** 쇼케이스 비교표, 수용 기준 '로컬 p95 < 200ms'(PRD §9 수용 기준 표)
  5. `uv run pytest -q`(계약·fallback·dedup·append·DELETE)와 `make smoke` PASS · `/docs` 캡처 확보

**Should 꼬리**: **SERV-11** 완독 직후 `after_completion` 행 → 수용 기준 '완독 → 완독하셨네요 row(Should)'(PRD §9 수용 기준 표) · **SERV-12** `POST /api/ratings`(모델 라벨 미사용) · **SERV-14** `GET /metrics` Bearer·24h `book_stats` 집계. 시간 부족 시 아키텍처 01 §8 티어 표 아래부터 버린다 — Grafana scrape가 가장 먼저, **완독 직후 행과 1탭 별점은 가장 늦게** 버린다(결정 '버리는 순서'(개발일지 2026-09-04 파일 항목 D40)).
**Plans**: 12 plans (wave 1: 5 병렬 · wave 2: 3 · wave 3: 1 Advisor 실측 · wave 4: 3 Should 병렬)

Plans:
- [x] 05-01-PLAN.md — state.py·nearline.py·book_stats.py + `__init__` 공개 표면(D-05~D-08 user_key 상태, rowid 커서·24h 리플레이, user_level 어댑터) [SERV-09·04]
- [x] 05-02-PLAN.md — compose.py Must 5행·dedup(book_id+제목)·배지 6종·메타 조인·비개인화 2행(D-01~D-04) [SERV-01·02·08]
- [x] 05-03-PLAN.md — fallback.py Level1Cache·over_budget·segment_popular + db.py DML 헬퍼·close·backup + schema.sql 인덱스 2개(D-10) [SERV-03]
- [x] 05-04-PLAN.md — persona.py·onboarding_meta.json·demo_api.py(meta·candidates·preferences·events, D-14~D-16·품질 게이트) [SERV-04·05·06]
- [x] 05-05-PLAN.md — privacy_api.py(state·data·DELETE personalization, Codex 필수) [SERV-07]
- [x] 05-06-PLAN.md — api.py 통합 + cascade.py 신설(user_key 해석·셀·0→1→2→3·breakdown·추천 로그·lifespan) + wave 1 게이트 [SERV-01·02·03·06·07·08·09]
- [x] 05-07-PLAN.md — dashboard_api.py GET /api/showcase(비교표 Must) + bench.py(D-11) [SERV-13·10]
- [x] 05-08-PLAN.md — Advisor: app/server.py 주입·StagedPipeline.last_breakdown·n_completed context 분기 1줄×2(D-07·D-09) [SERV-04·09·03]
- [x] 05-09-PLAN.md — Advisor 실측: wave 2 게이트 → make bench p95 < 200 → draft P4·/docs 캡처·Codex 필수 리뷰·PROGRESS·개발일지 D77 [SERV-10·14(설계만)]
- [x] 05-10-PLAN.md — (Should) after_completion 행: Nearline 사전 계산 → 최상단 행 [SERV-11]
- [x] 05-11-PLAN.md — (Should) POST /api/ratings + rating 이벤트 [SERV-12]
- [x] 05-12-PLAN.md — (Should) GET /api/dashboard 최소형(kpi 6·latency·quality·ab_table) [SERV-13]

### Phase 6: 데모 재구성
**Goal**: 심사자가 쇼케이스에서 시작해 취향 설정 → 메인 → 상세 → 뷰어 → 서재 → 재설정 → 대시보드까지 눌러보며 설계 주장을 직접 확인할 수 있고, 그 화면이 로컬 API의 실제 응답으로 그려진다.
**Day**: Day 2 (mock·`api.js`·라우팅) → Day 3~4 (뷰어~쇼케이스·인스펙터·API 전환)
**Depends on**: Phase 1 (같은 origin StaticFiles) · Phase 3 (`books_kr.json` 기준 mock 재생성) · Phase 5 (`?source=api` 전환 시 실제 응답)
**병렬**: Phase 5 (서빙 Must 완성)와 동시 실행 — Demo 레인은 HTTP 계약(mock)만 알면 서버 완성을 기다리지 않는다
**Requirements**: DEMO-01, DEMO-02, DEMO-03, DEMO-04, DEMO-05, DEMO-06, DEMO-09 (Must) · DEMO-07, DEMO-08 (Should)

**착수 전** — ②·③단계가 핵심:
1. 설계서 전수 조사 — 화면 구성 02 전체(§2 페이지별 명세·§3 공통 컴포넌트·§4 상태·§5 이벤트·§7 캡처·§8 증분), 화면 01 §3 PC 레이아웃·§4-2 온보딩 JSON·§4-4 배지 6종·§4-5 페르소나·§5 토큰·§6 상태 패턴, 백엔드 서빙 01 §16 mock 대응표.
2. 기존 구현 인벤토리 — **`demo/` 27파일은 v1 산출물이다.** 유지: `css/tokens.css` 등 5개, `config/onboarding.json`, `js/screens/onboarding_step.js`·`ui.js`, `app.js`의 `state`+`setState`+`render` 패턴.
3. 정합 판정과 **재구성 대상**(파일명 명시) — `js/api.js`(`API_BASE="https://REPLACE-ME.hf.space"`·`/recommend` 접두어 없음·`timestamp`), `js/mock.js`(배지 로직), `scripts/make_mock.py`와 `mock/` 7개(`latency_ms` 객체·`format`·`badge.type "rating"`·criteria 문자열·`cell`/`snapshots_count` 누락), `fallback/popular.json`(Goodbooks 카탈로그), `js/screens/s7_home.js`·`s8_detail.js`(S0~S8 라우팅). 완료 기준에 "구 형태 grep 0건"을 넣는다.
4. 로컬 기동 확인 — `make serve` 후 `http://localhost:8000/?source=api`와 `make demo-serve`의 `?source=mock` 양쪽 모두 콘솔 에러 0.

**Success Criteria** (what must be TRUE):
  1. 구 형태 grep이 0건이다(`hf.space`·`/recommend"`·`timestamp`·`"format"`·`"rating"`)이고, `js/api.js`가 `API_BASE=""`·`/api` 접두어·`ts` 필드·4초 타임아웃 클라이언트 fallback을 쓴다 — **DEMO-01** `api.js` 새 계약
  2. `scripts/make_mock.py`가 `artifacts/serving/books_kr.json` 기준으로 mock 10개를 재생성하고 `/contract-sync`에서 `serving/schemas.py` 검증을 전부 통과한다 — **DEMO-02** mock 재생성·계약 동기화
  3. 해시 라우팅 8페이지가 `state`+`render()` 패턴으로 동작한다 — 쇼케이스 화면(`#/`, 화면 구성 02 §2) → 취향 설정 화면(`#/onboarding`) → 메인 화면(`#/home`) → 책 상세 화면(`#/book/:id`) → 뷰어 시뮬레이션 화면(`#/reader/:id`) → 내 서재 화면(`#/library`) → 취향 재설정 화면(`#/refresh`) → 관제 대시보드 화면(`#/dashboard`). 취향 설정 7단계는 `config/onboarding.json` 1벌 + 공용 렌더러로 그려지고 건너뛰기는 `consent=false`로 메인에 진입한다 — **DEMO-03** 8페이지 라우팅 · **DEMO-04** 취향 설정 7단계·건너뛰기
  4. 메인 화면 카드에 배지 6종(bestseller·review 3단 폴백·author·publisher·buzz·light)과 앵커 reason이 보이고 인스펙터가 `recommendation_id`·`model_version`·`fallback_level`·`latency_breakdown`·α/β/γ·`channel_mix`·모델 전환 라디오를 보여주며, 쇼케이스 화면에 Track A 비교표(`split_mode` 캡션)·단계↔지표 대응 그림·중심 설계 철학 문장·2트랙 데이터 고지가 있다 — **DEMO-05** 배지·인스펙터 · **DEMO-06** 쇼케이스
  5. `?source=mock`과 `?source=api`(로컬 서버) 모두 쇼케이스 화면 → 관제 대시보드 화면 완주에 콘솔 에러 0이고 `?capture=1|2` 스크린샷 모드가 동작한다. `uv run pytest -q`와 `make smoke` PASS — **DEMO-09** 두 모드 완주·캡처

**Should 꼬리**: **DEMO-07** 뷰어 시뮬레이션 화면(`#/reader/:id`)의 "10분 읽기"·"완독" → `reader_open`·`qualified_read`(15분)·`completion` 이벤트 + 1탭 별점 모달 → `POST /api/ratings` · **DEMO-08** 관제 대시보드 화면(`#/dashboard`)이 `GET /api/dashboard` 표시. 시간 부족 시 아키텍처 01 §8 티어 표 아래부터 버린다 — 관제 대시보드가 별점 모달보다 먼저 빠지고, **완독 직후 행·1탭 별점은 가장 늦게** 버린다(결정 '버리는 순서'(개발일지 2026-09-04 파일 항목 D40)).
**Plans**: 7 plans (wave 1 → 4 · 같은 wave 는 files_modified 서로소 · 전부 no_commit)

Plans:
- [ ] 06-01-PLAN.md — `make_mock.py` 재작성(tdd) — 밀리 아티팩트 → `demo/mock/` 13파일, `tests/demo/test_make_mock.py`, popular.json 은 검증만 (DEMO-02)
- [ ] 06-02-PLAN.md — 라우터·앱 셸 — `router.js`·`app.js`·`actions.js`·`presets.js`·`ui.js` 공용 4·`index.html`·`base.css`·`onboarding.json` 진행바·README (DEMO-03·04·09)
- [ ] 06-03-PLAN.md — 데이터 계층 — `api.js`(`API_BASE=""`·`/api`·`ts`·4초 fallback·13 함수)·`mock.js`(5행 compose·배지·페르소나·cell)·`mock_store.js`(세션 DB·DashboardOut 집계) (DEMO-01·02)
- [ ] 06-04-PLAN.md — 뷰어 시뮬레이션·내 서재 — `d4_reader.js`·`d5_library.js` + `reader.css`·`library.css` (DEMO-07·03)
- [ ] 06-05-PLAN.md — 관제 대시보드·쇼케이스 — `d7_dashboard.js`·`d8_showcase.js` + `dashboard.css`·`tokens.css` §6 (DEMO-06·08)
- [ ] 06-06-PLAN.md — 메인·상세·인스펙터 통합 — `d2_home.js`(← s7)·`d3_detail.js`(← s8)·`inspector.js`·`home.css`·`inspector.css` + mock 완주 수동 체크리스트 (DEMO-05·03)
- [ ] 06-07-PLAN.md — Advisor 게이트·인계(autonomous: false) — 구 형태 grep 0·/contract-sync·pytest·smoke·Playwright 완주·캡처 6장·PROGRESS 미결 2줄 (DEMO-09 + 전 ID 재확인)
**UI hint**: yes

### Phase 7: 배포
**Goal**: 심사 기간 내내 살아 있는 URL 하나에서 프론트·API·SQLite가 같은 origin으로 서빙되고, 배포 실패 리스크는 Day 2에 미리 노출되어 Day 4에는 코드 문제만 남는다.
**Day**: Day 2 (스켈레톤) · Day 4 (본배포)
**Depends on**: Phase 1 (Day 2 스켈레톤 배포의 전제 — 로컬 `make smoke` PASS) · Phase 5 · Phase 6 (Day 4 본배포의 전제)
**병렬**: 스켈레톤 배포는 Day 2에 Phase 3·5·6과 병행 가능(사용자 35분 + 빌드 대기). 본배포는 Phase 5·6 완료 후.
**Requirements**: DEPLOY-01, DEPLOY-02, DEPLOY-03 (Must) · DEPLOY-04 (Should)

**착수 전**:
1. 설계서 전수 조사 — 배포 02 전체(§1 필요 조건·§2 배포 파일·§3 스켈레톤·§4 본배포·§7 장애 대응표·§9 실패 시 대체 경로), 아키텍처 01 §5 배포·§6 비용·§7 런북.
2. 기존 구현 인벤토리 — `Dockerfile`(13줄)·`railway.json`·`.dockerignore`는 v2.1 **일치** → 그대로 사용. `git` 미초기화 상태면 Day 1 종료에 `git init` + 첫 커밋(사용자 승인).
3. 정합 판정과 재구성 — 재구성 대상 없음. 두 번째 `uv sync`·`USER` 미지정·`${PORT:-8000}` 세 조건이 유지되는지만 확인한다(이 셋이 빠지면 배포 시점에만 드러나는 결함이 된다).
4. 로컬 기동 확인 — **선행 조건**: `make smoke` PASS + 로컬 docker 스모크(배포 02 §4-2). 로컬이 통과하지 않으면 push하지 않는다.

**Success Criteria** (what must be TRUE):
  1. Day 2 스켈레톤 배포 후 배포 URL의 `/health`가 200이고 정적 데모가 뜨며, Railway 서비스 Restart 후에도 SQLite 데이터가 남는다(볼륨 영구 확인). 재배포 다운타임 실측값이 기록된다 — **DEPLOY-01** Day 2 스켈레톤
  2. Day 4 본배포 후 배포 URL에서 쇼케이스 화면(`#/`) → 관제 대시보드 화면(`#/dashboard`) 완주가 콘솔 에러 0이고, 인스펙터의 모델 전환 라디오로 4 variant를 바꾸면 노출되는 책이 바뀐다 — **DEPLOY-02** Day 4 본배포·완주
  3. `git ls-files | grep -iE "pdf|png|assets"`가 빈 결과이고 UptimeRobot이 `/health`를 5분 간격으로 감시한다 — **DEPLOY-03** 저작권 검사·가동 감시
  4. 배포 전 로컬에서 `uv run pytest -q`·`make smoke`·docker 스모크가 모두 PASS다 (배포는 로컬 통과 후에만 — `../.claude/rules/local-run.md`)

**Should 꼬리**: **DEPLOY-04** Sentry·Grafana Cloud scrape 연결. 시간 부족 시 아키텍처 01 §8 티어 표 아래부터 버린다 — **Grafana scrape가 Should 중 가장 먼저 버려지는 항목**이고, 완독 직후 행·별점은 가장 늦게 버린다(결정 '버리는 순서'(개발일지 2026-09-04 파일 항목 D40)). 배포 자체가 90분을 넘기면 배포 02 §9 대체 경로(로컬 서버 + 로컬 스크린샷)로 전환하고 PDF는 완결한다.
**Plans**: TBD

### Phase 8: PDF 제출물
**Goal**: 설계서의 주장과 앞 페이즈의 실측 숫자가 5페이지 안에 들어가고, 데모·서버가 죽어도 제출물이 완결된다.
**Day**: Day 4 (문장 누적) → Day 5 (조판·제출)
**Depends on**: Phase 2·Phase 4 (`results/latest.csv` 4행) · Phase 5 (`results/latency.json` p95) · Phase 6 (데모 캡처) · Phase 7 (배포 URL·QR)
**병렬**: 없음 — 마지막 페이즈. Day 5는 PDF만, 코드 변경은 PDF 숫자를 깨는 버그 수정으로 한정한다.
**Requirements**: PDF-01, PDF-02, PDF-03 (전부 Must)

**착수 전**:
1. 설계서 전수 조사 — main 설계서 §1 중심 철학·§1-1 4축·§2 페이지 매핑·§9 기억할 5가지·§10 출처, PRD §9 말미 제출물 수용 기준, 화면 구성 02 §7 캡처 계획, `../.claude/rules/report.md`.
2. 기존 구현 인벤토리 — `report/draft.md`(36줄 뼈대)에 첫 실측부터 문장이 누적돼 있어야 한다. `results/latest.csv`·`results/latency.json`·`report/figures/` 존재 확인.
3. 정합 판정과 재구성 — 숫자는 `results/`에서만 인용한다. 서버·mock의 `latency_ms`, 관제 대시보드·Grafana 캡처 수치는 PDF 본문에 쓰지 않는다(관측이 붙어 있다는 증거로만).
4. 로컬 기동 확인 — 캡처를 위해 `make serve`가 떠 있는 상태에서 `?capture=1|2`로 스크린샷을 찍는다.

**Success Criteria** (what must be TRUE):
  1. `report/draft.md`가 main 설계서 §2 페이지 매핑대로 P1~P5를 채우고, 모든 숫자가 `results/latest.csv`·`results/latency.json`에서만 인용되며 데이터 2트랙 각주가 붙어 있다 — **PDF-01** 페이지 매핑·숫자 출처
  2. ★3개(앵커·난이도·시간 가변 가중치)가 각각 소제목 또는 박스로 존재하고, 필수 문장 7개·그림 4종(아키텍처·단계↔지표·비교 막대·데모 캡처)이 들어 있다 — **PDF-02** ★박스·필수 문장·그림
  3. `/pdf-check` 전 항목이 통과하고 5페이지 이내이며 `[재확인]` 마커가 0건이다 — **PDF-03** 최종 점검
  4. 제출 전 `uv run pytest -q`와 `make smoke`가 PASS 상태이고, `FREEZE_BOOK_STATS=1`이 설정되어 화면·PDF 숫자가 어긋나지 않는다

**Should 꼬리**: 없음 (전 항목 Must). PDF는 버리는 순서의 **불변 항목**이다 — Track A 4행 실측·본인 5권 케이스·Must API·쇼케이스 비교표와 함께 어떤 경우에도 버리지 않는다(방법론 01 §6).
**Plans**: TBD

## Progress

**Execution Order:**
Phase 1 → (Phase 2 ‖ Phase 3) → Phase 4 → (Phase 5 ‖ Phase 6) → Phase 7 → Phase 8
(Day 기준: Day 1 = 1·2·3 / Day 2 = 3·4·5·6·7 스켈레톤 / Day 3 = 4·5·6 + freeze / Day 4 = 5·6·7 본배포·8 문장 / Day 5 = 8 조판·제출)

| Phase | Day | Plans Complete | Status | Completed |
|-------|-----|----------------|--------|-----------|
| 1. 로컬 서빙 스켈레톤 | 1 | 2/2 | Complete | 2026-09-05 |
| 2. Track A 정량 평가 기반 | 1 | 6/6 | Complete    | 2026-09-05 |
| 3. 밀리 카탈로그 빌드 | 1~2 | 8/8 | Complete (verify 미실행) | 2026-09-06 |
| 4. 추천 파이프라인과 모델 freeze | 2~3 | 6/6 | Complete | 2026-09-06 |
| 5. 서빙 Must 완성 | 2~4 | 12/12 | Complete | 2026-09-06 |
| 6. 데모 재구성 | 2~4 | 0/7 | Planned | - |
| 7. 배포 | 2 · 4 | 0/TBD | Not started | - |
| 8. PDF 제출물 | 4~5 | 0/TBD | Not started | - |

## Coverage

v1 요구사항 58건(Must 48 · Should 10)이 전부 정확히 한 페이즈에 매핑됐다. 상세 매핑표는 `.planning/REQUIREMENTS.md` Traceability 절.

| Phase | 요구사항 수 | Must | Should |
|-------|------------|------|--------|
| 1. 로컬 서빙 스켈레톤 | 5 | 5 | 0 |
| 2. Track A 정량 평가 기반 | 7 | 6 | 1 |
| 3. 밀리 카탈로그 빌드 | 8 | 7 | 1 |
| 4. 추천 파이프라인과 모델 freeze | 8 | 6 | 2 |
| 5. 서빙 Must 완성 | 14 | 11 | 3 |
| 6. 데모 재구성 | 9 | 7 | 2 |
| 7. 배포 | 4 | 3 | 1 |
| 8. PDF 제출물 | 3 | 3 | 0 |
| **합계** | **58** | **48** | **10** |

---
*Roadmap created: 2026-09-05*
