# Requirements: millie-rec (밀리의서재 메인 추천 시스템 5일 데모)

**Defined:** 2026-09-05
**Core Value:** 설계서의 주장이 로컬에서 실행되는 코드와 실측 숫자로 증명되어 PDF 5페이지에 들어간다. 데모·서버가 죽어도 PDF는 완결된다.

> 도출 근거: PRD §9 수용 기준 표 · main 설계서 §8 구현 범위 고정 · 아키텍처 01 §8 범위 티어 · 적재 계획 02 §7 커버리지 게이트·§6 이웃 게이트 · 화면 구성 02 §2 · 루트 `CLAUDE.md` §2 원칙. 각 항목 끝의 **[Must]/[Should]**는 아키 §8 티어. Should는 아키 §8 표 아래부터 버린다(완독 직후 행·별점은 가장 늦게).
> 표기: ID는 `분류-번호`이지만 항상 제목과 함께 쓴다(`.claude/rules/references.md`). 완료 기준 공통: `uv run pytest -q` + `make smoke` PASS(`.claude/rules/local-run.md`).

## v1 Requirements

### 로컬 서빙 스켈레톤 (SKEL)

- [x] **SKEL-01** 개발자가 `make serve`를 실행하면 아티팩트·DB·네트워크 없이 서버가 뜨고 `GET /health`가 200과 `HealthOut`(model_version null 허용)을 반환한다 [Must]
- [x] **SKEL-02** 브라우저에서 `http://localhost:8000/`을 열면 `demo/` 정적 데모가 같은 origin에서 서빙된다(FastAPI StaticFiles) [Must]
- [x] **SKEL-03** 파이프라인이 주입되지 않은 상태에서 `GET /api/recommend?seeds=1,2,3`이 `fallback_level=3` 200 응답(`RecommendOut` 스키마)을 준다 — "추천 API 장애 ≠ 메인 장애" [Must]
- [x] **SKEL-04** SQLite가 `contracts.DIR_DATA_LOCAL/millie.db`에 자동 생성되고 `schema.sql`의 Must 4테이블(users·preference_snapshots·events·recommendations)이 만들어진다 [Must]
- [x] **SKEL-05** `make smoke`가 서버를 띄워 `/health`·`/`·`/api/recommend` 3개를 확인하고 PASS를 출력한다 — 이후 모든 요구사항의 완료 기준 [Must]

### Track A 정량 평가 (EVAL)

- [x] **EVAL-01** 개발자가 `make data`로 Goodbooks-10k를 멱등 다운로드하고 `data/processed/interactions.parquet`·`books.parquet`를 얻는다 [Must]
- [x] **EVAL-02** `split.py`가 `ts` 컬럼이 없으면 유저별 random holdout(seed 고정)으로 나누고 결과에 `split_mode=holdout`을 기록한다; `ts`가 있으면 전역 시점 temporal [Must]
- [x] **EVAL-03** 온보딩 시뮬레이션이 테스트 유저의 첫 5권만 `explicit_seeds`로 노출하고 미선택 책을 부정 신호로 학습하지 않는다(PRD 수용 기준 '미선택 책 ≠ 부정 신호') [Must]
- [x] **EVAL-04** Recall@20·NDCG@10·ILD@10이 순수 함수로 구현되고 손계산 케이스 테스트가 통과한다; 학습에 본 아이템은 추천에서 제외된다 [Must]
- [x] **EVAL-05** `make eval`이 `pop`·`cf`·`hybrid`·`hybrid_div` 4행을 `results/latest.csv`·`results/eval_<ts>.json`(split_mode·n_users·seed·sha)에 기록한다(PRD 수용 기준 '평가 4행 + split_mode 출력') [Must]
- [x] **EVAL-06** n=0(온보딩 5권만)과 n≥k(행동 축적) 상태의 지표가 별도 표로 출력된다 — ★시간 가변 가중치의 증거(PRD 수용 기준 'n=0 vs n≥k 지표 분리') [Must]
- [x] **EVAL-07** 비교 막대그래프 `report/figures/eval_bar.png`가 `results/latest.csv`에서 생성된다 [Should]

### Track B 밀리 카탈로그 (DATA)

- [ ] **DATA-01** `scripts/build_millie_catalog.py`가 `millie_pages.jsonl`을 `data/processed/books_kr.parquet`로 만들고 `book_id`는 `data/id_map.csv` 사전순 surrogate(append-only, 기존 행 변동 0)를 쓴다 [Must]
- [ ] **DATA-02** `books_kr.parquet`가 계약 컬럼 이름 9개(`book_id title authors image_url average_rating ratings_count original_publication_year categories tags`)를 문자 단위로 갖고, `book_format`은 전자책·오디오북·챗북 중 하나다 [Must]
- [ ] **DATA-03** 커버리지 게이트 테스트가 통과한다: title 100%·image_url ≥99%·categories ≥95%·completion_prob ≥70%·formats ≥90%·seg_dist ≥70%·카테고리 종수 ≥8·20권 이상 분야 ≥6 → `results/millie_coverage.csv` [Must]
- [ ] **DATA-04** 난이도가 밀리 완독지수에서 파생된다: `resid_z`·`len_z`, `difficulty=σ(−resid_z)`, 결측은 `difficulty_source=category_prior`·`difficulty=None`(가드 모집단 제외) [Must]
- [ ] **DATA-05** `item_edges_kr.parquet`가 `title+description+curator_note` 문자 2~4gram TF-IDF content_sim top-20(+category_best 보험)으로 만들어지고 이웃 게이트 3(self-edge 0·전 도서 이웃 ≥5·동일 카테고리 ≤70%)을 통과한다 [Must]
- [ ] **DATA-06** `data/catalog_kr.py`가 `contracts.Catalog`·`Neighbors`·`BookStatsSource`를 구현하고 description·curator_note를 노출하지 않는다 [Must]
- [ ] **DATA-07** `make millie-export`가 `artifacts/serving/{books_kr.json,item_edges_kr.json,content_vectors_kr.npz,popularity_kr.json}`과 `demo/fallback/popular.json`(새 스키마)을 파일당 <50MB, description 0건으로 만든다 [Must]
- [ ] **DATA-08** `popularity_kr`에 세그먼트(연령×성별) 인기가 포함되어 fallback level 2 응답이 전역 인기와 다르다 [Should]

### 추천 파이프라인 (REC)

- [x] **REC-01** `PopularityRetriever`·`ItemKNNRetriever`(scipy.sparse cosine, train만)·`ContentRetriever`(TF-IDF, `ItemVectors` 제공)가 `CandidateGenerator` 계약을 만족한다 [Must]
- [x] **REC-02** `app/pipeline.py`가 `contracts.VARIANTS` 4종을 dict로 조립하고 `hybrid`는 cf ∪ content ∪ pop 가중합이다 [Must]
- [x] **REC-03** `ranking/blend.py`가 α/β/γ를 초기값에서 재정규화하고(신규 유저 β=0) 이벤트에 따라 갱신한다 — ★시간 가변 가중치 [Must]
- [x] **REC-04** `ranking/hybrid.py`가 난이도 부호 gap(`difficulty − user_level`)·`gap⁺`·`n_completed×gap`을 피처로 쓰고 결측(None)은 가중 0이다 [Should]
- [x] **REC-05** `reranking/mmr.py`가 `ItemVectors`로 다양성 재순위화를 하여 `hybrid_div`의 ILD@10이 `hybrid`보다 높다 [Must]
- [x] **REC-06** `reranking/guard.py`가 완독 <3 신규 사용자에게 `source=millie_index ∧ resid_z<−1` 책을 상단 N에서 제외한다(PRD 수용 기준 '난이도 가드(Should)') [Should]
- [x] **REC-07** `app/cli.py demo --seeds`가 밀리 카탈로그 내 본인 5권으로 앵커 추천 1장을 출력한다(이웃 = 콘텐츠 유사도 병기) [Must]
- [x] **REC-08** Day 3 종료에 모델 freeze가 STATE.md·개발일지에 선언되고 이후 새 모델·후보 통로가 추가되지 않는다 [Must]

### 서빙 Must API (SERV)

- [ ] **SERV-01** `GET /api/recommend`가 Page Composition Must 5행(이어 읽기 → 앵커 행 `anchor_<seed>` → 페르소나 서가 → 지금 많이 읽는 책 → 새로운 발견)을 행 간 dedup 후 `rows`·`items`(평탄화 상위 k)로 반환한다 [Must]
- [ ] **SERV-02** 앵커 행 items의 `source`·`source_channels`·`channel_mix`가 `content`이고 `reason`이 "『시드』… 좋아하셨다면"이다(PRD 수용 기준 '온보딩 5권 → 앵커 row') [Must]
- [ ] **SERV-03** fallback cascade가 코드로 존재한다: 단계별 `perf_counter` 누적 > `BUDGET_MS`(200) 또는 예외 → level 1 캐시 → 2 스냅샷 카테고리 인기 → 3 전역 인기, 항상 200(PRD 수용 기준 '파이프라인 예외 → 인기 row 200') [Must]
- [ ] **SERV-04** `POST /api/preferences`가 스냅샷을 append하고(재설정도 추가, 삭제 없음) `users` 행에 sha256 기반 `cell`을 저장하며 seeds마다 `library_add` 이벤트를 자동 기록한다(PRD 수용 기준 '재설정 → 새 앵커·기록 보존') [Must]
- [ ] **SERV-05** `GET /api/meta/onboarding`·`GET /api/candidates/onboarding`(선택 카테고리 ∩ 카탈로그, `pop_rank` 순, `candidate_set_id` 발급)이 스키마대로 응답한다 [Must]
- [ ] **SERV-06** `POST /api/events`가 품질 게이트(스키마 → `event_id` 중복 무시 → `ts` 검사 → eligible) 후 저장하고 `EventsAccepted`를 반환하며, 모든 노출 로그에 `recommendation_id·model_version·row_id·position`이 있다(PRD 수용 기준 '노출 로그 4필드') [Must]
- [ ] **SERV-07** `GET /api/users/{key}/state`·`/data`(열람)·`DELETE …/personalization`(철회 → consent=false → 이후 항상 level 3)이 동작한다(PRD 수용 기준 '동의 철회 → 비개인화 fallback') [Must]
- [ ] **SERV-08** 건너뛰기(consent=false)·익명 사용자에게는 개인화 행 없이 인기·신간 행만 나온다(PRD 수용 기준 '건너뛰기 → 비개인화 row만') [Must]
- [ ] **SERV-09** `serving/nearline.py` 비동기 루프(30s ∨ 이벤트 웨이크)가 세션을 갱신하고, 요청 핸들러는 이벤트만 적재한다 [Must]
- [ ] **SERV-10** `bench.py`(로컬 uvicorn 1 worker, warmup 50, 요청 500)가 `results/latency.json`에 p50/p95/p99를 기록하고 p95 < 200ms다(PRD 수용 기준 '로컬 p95 < 200ms') [Must]
- [ ] **SERV-11** 완독 이벤트 후 다음 응답 최상단에 `after_completion` 행이 그 책의 콘텐츠 유사도 이웃으로 채워진다(PRD 수용 기준 '완독 → 완독하셨네요 row(Should)') [Should]
- [ ] **SERV-12** `POST /api/ratings`가 `ratings`에 저장하고 `rating` 이벤트를 기록한다(모델 라벨로는 미사용) [Should]
- [ ] **SERV-13** `GET /api/dashboard`·`GET /api/showcase`(비교표는 `artifacts/serving/eval_table.json`, `split_mode` 병기, 2트랙 `data_notice`)가 스키마대로 응답한다 — showcase 비교표는 Must [Must]
- [ ] **SERV-14** `GET /metrics`(Bearer, prometheus-client)·`book_stats.py` 24h 집계(difficulty·n_events만 갱신, 밀리 completion_prob 불변) [Should]

### 데모 재구성 (DEMO)

- [ ] **DEMO-01** `demo/js/api.js`가 `API_BASE=""`(같은 origin)·`/api` 접두어·`ts` 필드·4초 타임아웃 클라이언트 fallback을 쓰고 구 형태(`hf.space`·`/recommend"`·`timestamp`) grep이 0건이다 [Must]
- [ ] **DEMO-02** `scripts/make_mock.py`가 `artifacts/serving/books_kr.json` 기준으로 mock 10개를 재생성하고 `/contract-sync`에서 `serving/schemas.py` 검증을 전부 통과한다(`latency_ms` float, `book_format`, `badge.type` 6종, criteria `{id,label}`, `cell`·`snapshots_count`) [Must]
- [ ] **DEMO-03** 해시 라우팅 8페이지(취향 설정 `#/onboarding`·메인 `#/home`·책 상세 `#/book/:id`·뷔어 시뮬레이션 `#/reader/:id`·내 서재 `#/library`·취향 재설정 `#/refresh`·관제 대시보드 `#/dashboard`·쇼케이스 `#/`)가 `state`+`render()` 패턴으로 동작한다 [Must]
- [ ] **DEMO-04** 취향 설정 7단계가 `config/onboarding.json` 1벌 + 공용 렌더러로 그려지고 건너뛰기는 `consent=false`로 메인에 진입한다 [Must]
- [ ] **DEMO-05** 메인 화면 카드에 배지 6종(`pop_rank` bestseller·review 3단 폴백·author·publisher·millie_label buzz·light)과 앵커 reason이 표시되고 인스펙터가 recommendation_id·model_version·fallback_level·latency_breakdown·α/β/γ·channel_mix·모델 전환 라디오를 보인다 [Must]
- [ ] **DEMO-06** 쇼케이스 페이지가 Track A 비교표(`split_mode` 캡션)·단계↔지표 대응 그림·중심 설계 철학 문장·2트랙 데이터 고지를 보인다 [Must]
- [ ] **DEMO-07** 뷔어 시뮬레이션의 "10분 읽기"·"완독"이 `reader_open`·`qualified_read`(15분)·`completion` 이벤트를 만들고 1탭 별점 모달이 `POST /api/ratings`를 호출한다 [Should]
- [ ] **DEMO-08** 관제 대시보드가 `GET /api/dashboard`를 표시한다 [Should]
- [ ] **DEMO-09** `?source=mock`과 `?source=api`(로컬 서버) 모두 쇼케이스→대시보드 완주가 콘솔 에러 0이고 `?capture=1|2` 스크린샷 모드가 동작한다 [Must]

### 배포 (DEPLOY)

- [x] **DEPLOY-01** Day 2 Railway 스켈레톤: `/health` 200·정적 데모·볼륨 영구 확인(재배포 후 SQLite 유지) [Must]
- [x] **DEPLOY-02** Day 4 본배포: 로컬 `make smoke`·docker 스모크 통과 후 push, 배포 URL에서 쇼케이스→대시보드 완주, 4 variant 전환 시 책이 바뀐다 [Must]
- [x] **DEPLOY-03** `git ls-files`에 과제 PDF·캡처·`.assets`가 없고 UptimeRobot이 `/health`를 감시한다 [Must]
- [~] **DEPLOY-04** ~~Sentry·Grafana Cloud scrape 연결~~ [Should] — **폐기**(Grafana scrape 부분, 결정 'Grafana 폐기'(.planning/phases/07-deploy/07-CONTEXT.md D-05) · 07-04-SUMMARY). Sentry 는 07-01 에서 유지·배포본 DSN 투입

### PDF (PDF)

- [x] **PDF-01** `report/draft.md`가 main 설계서 §2 매핑대로 P1~P5를 채우고 숫자는 `results/latest.csv`·`results/latency.json`에서만 인용한다 [Must]
- [x] **PDF-02** ★3개(앵커·난이도·시간 가변 가중치) 박스, 필수 문장 7개, 데이터 2트랙 각주, 그림 4종(아키텍처·단계↔지표·비교 막대·데모 캡처)이 있다 [Must]
- [x] **PDF-03** `/pdf-check` 전 항목 통과, 5페이지 이내, `[재확인]` 마커 0, 제출 09-08 22:00 KST 전 [Must]

## v2 Requirements

Deferred beyond the 5-day submission (main 설계서 §8 "설계만" — PDF 로드맵 문장으로만).

### 설계만 (LATER)

- **LATER-01** Two-Tower + ANN 인덱스 후보 생성
- **LATER-02** multi-task DNN ranker(YouTube MMoE 방향)·learned re-ranker·LightGBM
- **LATER-03** Kafka/Flink 실시간 Nearline·K8s autoscaling·interleaving 실험
- **LATER-04** 텍스트 기반 난이도(가독성)·Reviewer-affinity 후보 통로·정보나루 coLoan 이웃 승격
- **LATER-05** 별점을 모델 라벨로 사용·선호 교정 루프("이 책 추천하지 않기")·Adaptive Preference Elicitation

## Out of Scope

| Feature | Reason |
|---------|--------|
| LLM/Agent·대형 Transformer·강화학습·실시간 전체 재학습 | 문제 본질(추천)과 무관한 복잡도, 5일 내 동작 보장 불가 (main §5-5·§8) |
| React/Node/npm 프론트·브라우저 JS 스코어링 | 빌드 리스크·이중 구현 skew (개발일지 09-04 결정 '데모 프론트를 범위에 포함') |
| ORM·외부 DB·인증·로그인·검색·실제 뷰어 | 데모 규모 초과, sqlite3 표준 라이브러리로 충분 (개발일지 09-04 결정 '로컬 DB = sqlite3') |
| HF Spaces·Cloudflare Pages·Render 배포 | 무료 아님 또는 잠들기·볼륨 없음 (개발일지 09-04 결정 'HF Spaces 결정 폐기'·'배포 = Railway Hobby') |
| 네이버·교보·예스24·왓챠피디아 크롤링 | robots.txt 차단·약관 위반 (개발일지 09-04 결정 '네이버 도서 크롤링 기각') |
| 밀리 책 소개·큐레이터 문구 화면 노출, 표지 다운로드 | 저작물 재배포 금지, 핫링크만 (확보 방안 01 §3-2 완화 규칙) |
| UCSD Goodreads 전면 전환·Goodbooks 카탈로그 데모 | +2h 회수 불가·한국 책 데모 필요 (개발일지 09-04 결정 '적재 범위·스키마·난이도·이웃 결정') |
| 두 트랙 숫자 혼합(밀리 지표를 비교표에) | 밀리 카탈로그엔 유저 로그 없음 — 사실과 다른 표기 금지 |

## Traceability

어느 페이즈가 어느 요구사항을 덮는가. `.planning/ROADMAP.md`(2026-09-05) 작성 시 갱신.
표기 규칙(`.claude/rules/references.md`): ID 단독으로 쓰지 않고 항상 제목과 함께 인용한다 — 예: `**SKEL-03** 파이프라인 없을 때 fallback 200`. 페이즈도 번호 + 이름으로 부른다 — 예: `Phase 3 '밀리 카탈로그 빌드'(.planning/ROADMAP.md)`.

| Requirement | 제목 | 티어 | Phase | Status |
|-------------|------|------|-------|--------|
| **SKEL-01** | `make serve` 기동·`/health` 200 | Must | Phase 1 '로컬 서빙 스켈레톤' | Complete |
| **SKEL-02** | 정적 데모 같은 origin 서빙 | Must | Phase 1 '로컬 서빙 스켈레톤' | Complete |
| **SKEL-03** | 파이프라인 없을 때 fallback 200 | Must | Phase 1 '로컬 서빙 스켈레톤' | Complete |
| **SKEL-04** | SQLite 자동 생성·Must 4테이블 | Must | Phase 1 '로컬 서빙 스켈레톤' | Complete |
| **SKEL-05** | `make smoke` 3점 확인 | Must | Phase 1 '로컬 서빙 스켈레톤' | Complete |
| **EVAL-01** | Goodbooks-10k 멱등 다운로드 | Must | Phase 2 'Track A 정량 평가 기반' | Complete |
| **EVAL-02** | `ts` 없으면 random holdout·`split_mode` 기록 | Must | Phase 2 'Track A 정량 평가 기반' | Complete |
| **EVAL-03** | 온보딩 5권 마스킹·미선택 ≠ 부정 신호 | Must | Phase 2 'Track A 정량 평가 기반' | Complete |
| **EVAL-04** | 3지표 순수 함수·손계산 테스트·누수 방지 | Must | Phase 2 'Track A 정량 평가 기반' | Complete |
| **EVAL-05** | `make eval` 4행 + `split_mode` 기록 | Must | Phase 2 'Track A 정량 평가 기반' | Complete |
| **EVAL-06** | n=0 vs n≥k 지표 분리 출력 | Must | Phase 2 'Track A 정량 평가 기반' | Complete |
| **EVAL-07** | 비교 막대그래프 `eval_bar.png` | Should | Phase 2 'Track A 정량 평가 기반' | Complete |
| **DATA-01** | `books_kr.parquet` + 사전순 surrogate `book_id` | Must | Phase 3 '밀리 카탈로그 빌드' | Pending |
| **DATA-02** | 계약 컬럼 9개 문자 일치·`book_format` 3종 | Must | Phase 3 '밀리 카탈로그 빌드' | Pending |
| **DATA-03** | 커버리지 게이트 통과 → `millie_coverage.csv` | Must | Phase 3 '밀리 카탈로그 빌드' | Pending |
| **DATA-04** | 완독지수 파생 난이도 `σ(−resid_z)`·결측 None | Must | Phase 3 '밀리 카탈로그 빌드' | Pending |
| **DATA-05** | content_sim TF-IDF 이웃·이웃 게이트 3 | Must | Phase 3 '밀리 카탈로그 빌드' | Pending |
| **DATA-06** | `catalog_kr.py` 어댑터·밀리 텍스트 미노출 | Must | Phase 3 '밀리 카탈로그 빌드' | Pending |
| **DATA-07** | `make millie-export` 서빙 아티팩트 4+1 | Must | Phase 3 '밀리 카탈로그 빌드' | Pending |
| **DATA-08** | `popularity_kr` 세그먼트 인기 → fallback level 2 | Should | Phase 3 '밀리 카탈로그 빌드' | Pending |
| **REC-01** | 후보 3통로(popularity·itemknn·content) | Must | Phase 4 '추천 파이프라인과 모델 freeze' | Complete |
| **REC-02** | `VARIANTS` 4종 dict 조립·hybrid 가중합 | Must | Phase 4 '추천 파이프라인과 모델 freeze' | Complete |
| **REC-03** | α/β/γ 재정규화·이벤트 갱신(신규 β=0) | Must | Phase 4 '추천 파이프라인과 모델 freeze' | Complete |
| **REC-04** | 난이도 부호 gap·`gap⁺`·`n_completed×gap` 피처 | Should | Phase 4 '추천 파이프라인과 모델 freeze' | Complete |
| **REC-05** | MMR 다양성 재순위화(`hybrid_div` ILD 상승) | Must | Phase 4 '추천 파이프라인과 모델 freeze' | Complete |
| **REC-06** | 난이도 가드(완독 <3 · `resid_z<−1` 상단 제외) | Should | Phase 4 '추천 파이프라인과 모델 freeze' | Complete |
| **REC-07** | `cli demo --seeds` 본인 5권 앵커 1장 | Must | Phase 4 '추천 파이프라인과 모델 freeze' | Complete |
| **REC-08** | Day 3 모델 freeze 선언 | Must | Phase 4 '추천 파이프라인과 모델 freeze' | Complete |
| **SERV-01** | Page Composition Must 5행·행 간 dedup | Must | Phase 5 '서빙 Must 완성' | Pending |
| **SERV-02** | 앵커 행 content 채널·『시드』 reason | Must | Phase 5 '서빙 Must 완성' | Pending |
| **SERV-03** | fallback cascade level 1→2→3·항상 200 | Must | Phase 5 '서빙 Must 완성' | Pending |
| **SERV-04** | 스냅샷 append·`cell` sha256·`library_add` 자동 | Must | Phase 5 '서빙 Must 완성' | Pending |
| **SERV-05** | 온보딩 메타·후보(`pop_rank` 순·`candidate_set_id`) | Must | Phase 5 '서빙 Must 완성' | Pending |
| **SERV-06** | 이벤트 품질 게이트·노출 로그 4필드 | Must | Phase 5 '서빙 Must 완성' | Pending |
| **SERV-07** | 열람·삭제·철회 API(철회 후 항상 level 3) | Must | Phase 5 '서빙 Must 완성' | Pending |
| **SERV-08** | 건너뛰기·익명은 비개인화 행만 | Must | Phase 5 '서빙 Must 완성' | Pending |
| **SERV-09** | Nearline 비동기 루프(30s ∨ 이벤트 웨이크) | Must | Phase 5 '서빙 Must 완성' | Pending |
| **SERV-10** | 로컬 bench p95 < 200ms → `latency.json` | Must | Phase 5 '서빙 Must 완성' | Pending |
| **SERV-11** | 완독 직후 `after_completion` 행 | Should | Phase 5 '서빙 Must 완성' | Pending |
| **SERV-12** | `POST /api/ratings` 저장(모델 라벨 미사용) | Should | Phase 5 '서빙 Must 완성' | Pending |
| **SERV-13** | 대시보드·쇼케이스(비교표는 Must) | Must | Phase 5 '서빙 Must 완성' | Pending |
| **SERV-14** | `/metrics` Bearer·24h `book_stats` 집계 | Should | Phase 5 '서빙 Must 완성' | Pending |
| **DEMO-01** | `api.js` 새 계약(`API_BASE=""`·`/api`·`ts`)·구 형태 grep 0 | Must | Phase 6 '데모 재구성' | Pending |
| **DEMO-02** | mock 재생성 + `/contract-sync` 전부 통과 | Must | Phase 6 '데모 재구성' | Pending |
| **DEMO-03** | 해시 라우팅 8페이지·`state`+`render()` | Must | Phase 6 '데모 재구성' | Pending |
| **DEMO-04** | 취향 설정 7단계 공용 렌더러·건너뛰기 `consent=false` | Must | Phase 6 '데모 재구성' | Pending |
| **DEMO-05** | 배지 6종·앵커 reason·인스펙터 6섹션 | Must | Phase 6 '데모 재구성' | Pending |
| **DEMO-06** | 쇼케이스 비교표·단계↔지표 그림·2트랙 고지 | Must | Phase 6 '데모 재구성' | Pending |
| **DEMO-07** | 뷰어 시뮬레이션 이벤트 3종 + 1탭 별점 모달 | Should | Phase 6 '데모 재구성' | Pending |
| **DEMO-08** | 관제 대시보드가 `GET /api/dashboard` 표시 | Should | Phase 6 '데모 재구성' | Pending |
| **DEMO-09** | `?source=mock`·`?source=api` 완주 콘솔 에러 0·`?capture` | Must | Phase 6 '데모 재구성' | Pending |
| **DEPLOY-01** | Day 2 Railway 스켈레톤·볼륨 영구 확인 | Must | Phase 7 '배포' | Complete(09-06, 07-02·07-04 표식 이름 확인) |
| **DEPLOY-02** | Day 4 본배포·배포 URL 완주·variant 전환 | Must | Phase 7 '배포' | Complete(09-06, 07-03 12/12·4 variant) |
| **DEPLOY-03** | 저작권 검사(`git ls-files`)·UptimeRobot 감시 | Must | Phase 7 '배포' | Complete(09-06, 07-04 게이트) |
| **DEPLOY-04** | Sentry·Grafana Cloud scrape 연결 | Should | Phase 7 '배포' | Dropped(Grafana 폐기 D-05 · Sentry 유지) |
| **PDF-01** | `draft.md` P1~P5·숫자는 `results/`만 | Must | Phase 8 'PDF 제출물' | Complete (2026-09-06, 08-VERIFICATION passed) |
| **PDF-02** | ★3개 박스·필수 문장 7개·그림 4종 | Must | Phase 8 'PDF 제출물' | Complete (2026-09-06, 08-VERIFICATION passed) |
| **PDF-03** | `/pdf-check` 통과·5페이지 이내·기한 내 제출 | Must | Phase 8 'PDF 제출물' | Complete (2026-09-06, 08-VERIFICATION passed) |

**Coverage:**
- v1 requirements: 58 total (Must 48 · Should 10)
- Mapped to phases: 58 ✓ (모든 요구사항이 정확히 한 페이즈에 매핑)
- Unmapped: 0

**Phase별 분포:**

| Phase | Day | 요구사항 | Must | Should |
|-------|-----|----------|------|--------|
| Phase 1 '로컬 서빙 스켈레톤' | 1 | SKEL-01, SKEL-02, SKEL-03, SKEL-04, SKEL-05 | 5 | 5 |
| Phase 2 'Track A 정량 평가 기반' | 1 | EVAL-01, EVAL-02, EVAL-03, EVAL-04, EVAL-05, EVAL-06, EVAL-07 | 6 | 1 |
| Phase 3 '밀리 카탈로그 빌드' | 1~2 | DATA-01, DATA-02, DATA-03, DATA-04, DATA-05, DATA-06, DATA-07, DATA-08 | 7 | 1 |
| Phase 4 '추천 파이프라인과 모델 freeze' | 2~3 | REC-01, REC-02, REC-03, REC-04, REC-05, REC-06, REC-07, REC-08 | 6 | 2 |
| Phase 5 '서빙 Must 완성' | 2~4 | SERV-01, SERV-02, SERV-03, SERV-04, SERV-05, SERV-06, SERV-07, SERV-08, SERV-09, SERV-10, SERV-11, SERV-12, SERV-13, SERV-14 | 11 | 3 |
| Phase 6 '데모 재구성' | 2~4 | DEMO-01, DEMO-02, DEMO-03, DEMO-04, DEMO-05, DEMO-06, DEMO-07, DEMO-08, DEMO-09 | 7 | 2 |
| Phase 7 '배포' | 2 · 4 | DEPLOY-01, DEPLOY-02, DEPLOY-03, DEPLOY-04 | 3 | 1 |
| Phase 8 'PDF 제출물' | 4~5 | PDF-01, PDF-02, PDF-03 | 3 | 0 |

**병렬 실행:** Phase 2 'Track A 정량 평가 기반' ‖ Phase 3 '밀리 카탈로그 빌드' (Day 1) · Phase 5 '서빙 Must 완성' ‖ Phase 6 '데모 재구성' (Day 2~4).

**Should 버리는 순서:** 각 페이즈의 Should는 그 페이즈 끝부분에 둔다. 시간 부족 시 아키텍처 01 §8 티어 표 아래부터 버리며, 완독 직후 행(`after_completion`)·1탭 별점은 가장 늦게 버린다(결정 '버리는 순서'(개발일지 2026-09-04 파일 항목 D40)). Grafana scrape가 가장 먼저 버려진다.

---
*Requirements defined: 2026-09-05*
*Last updated: 2026-09-05 after roadmap creation (58/58 mapped)*
