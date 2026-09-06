# Phase 4: 추천 파이프라인과 모델 freeze - Context

**Gathered:** 2026-09-05
**Status:** Ready for planning

<domain>
## Phase Boundary

설계서의 4단계 파이프라인이 실제 코드로 존재한다: 후보 3통로(`retrieval/popularity`(✅)·`retrieval/itemknn`·`retrieval/content` `retrieve()`) → 가중합 랭킹(`ranking/blend.py` α/β/γ 재정규화 + `ranking/hybrid.py` 채널 가중합·난이도 gap 항) → 재순위화(`reranking/mmr.py` + `reranking/guard.py`) → `app/pipeline.py`가 `contracts.VARIANTS` 4종(`pop`·`cf`·`hybrid`·`hybrid_div`)을 dict로 조립한다. 결과물은 ① Track A 비교표 4행 `results/latest.csv`(+`latest_states.csv` n0/n20) ② 서버 `GET /api/recommend?model=` 4 variant 응답(Track B 카탈로그, 서로 다른 책) ③ `cli demo --seeds` 본인 5권 앵커 1장(`report/demo_5books.md`) ④ Day 3 종료 모델·API 응답 형태 freeze 선언이며, 이후 페이즈는 새 모델·후보 통로·응답 필드를 추가하지 않는다(ROADMAP Phase 4 Success Criteria 1~5, REQUIREMENTS REC-01·02·03·05·07·08 Must · REC-04·06 Should).

**쓰기 영역:** Worker = `src/millie_rec/{retrieval,ranking,reranking}/` + `tests/{retrieval,ranking,reranking}/`(+`tests/app/`). Advisor 직접 = `app/pipeline.py`(+분리 파일)·`app/cli.py`·`app/server.py`·`serving/api.py`의 `weights` 배선·`Makefile`·`contracts.py`(변경 없음 목표).
**건드리지 않는 것(재수집과 파일 교집합 0):** `scripts/`·`data/raw/**`·`data/id_map.csv`·`make millie*`·`make mock`·`demo/`(Phase 6)·`serving/schemas*.py`(freeze)·`serving/compose.py`·`state.py`·`nearline.py`(Phase 5). 5권 실측·서버 4 variant 판정은 **재수집 종료 후 최종 `make millie` 1회 뒤에만**(현재 `content_vectors_kr.npz` 8,708행 ≠ `books_kr.json` 9,450권, 배지 제목 728건 미정정 — STATE.md Blockers).

</domain>

<decisions>
## Implementation Decisions

### 가중치 α/β/γ 구조와 hybrid 병합 (ranking 슬라이스 · ★시간 가변 가중치 P3 박스의 증거 구조)
- **D-01 (2단 가중치):** α/β/γ는 **사용자 상태 성분**(explicit_seeds · history · session) 가중치다 — main §5-2 수식 `U_t = α·U_explicit + β·U_longterm + γ·U_session` 그대로. 각 채널은 성분별 점수를 α/β/γ로 합친다: `CF(u) = α·knn(seeds) + β·knn(history) + γ·knn(session)`, `CT(u) = α·sim(seeds) + β·sim(history) + γ·sim(session)`. **채널 가중치** `w_cf·w_content·w_pop`은 `ranking/hybrid.py` 상단 고정 상수(별도 층). `cf` variant = `CF(u)`만(w_content=w_pop=0), `hybrid` = 세 채널 가중합, `hybrid_div` = hybrid + MMR + 가드. n=0에서 β=0이어도 cf는 seeds로 살아 있고, n≥20에서 history 성분이 들어와 hybrid·cf만 변한다 — `latest_states.csv`의 증거 구조.
- **D-02 (스케줄 = 아키 초기값 + main 감쇠 결합, 문서 충돌 해소):** 초기값 α₀=0.6/β₀=0.3/γ₀=0.1·하한 0.2·재정규화는 아키텍처 01 §3-3, 감쇠식은 main §5-2: `α_n = max(0.2, α₀·e^{−n/τ})`, **τ=20**(n=20에서 α≈0.22), 남은 무게는 β:γ = 3:1(초기 배율)로 나눈 뒤 **비어 있는 성분을 빼고 재정규화**(신규: history·session 없음 → α=1.0, β=γ=0 → 응답 `user_state_weights`에 β=0 표시 = REC-03). n = `len(user.history)`(평가·Phase 4엔 이벤트가 없다). 재설정 직후 +0.15·세션 활동 +0.1 부스트는 `blend` 공개 함수의 **입력 인자**로만 두고 적용은 Phase 5 `state.py`. 아키 §3-3 단계 규칙(`reader_open`마다 ±0.05) 문구 갱신은 Advisor 후속(개발일지 D68 장애 ①).
- **D-03 (병합 = min-max 정규화 + 고정 상수, 튜닝 1회):** 채널별 후보 점수를 0~1로 min-max 정규화(채널에 없는 후보는 0) 후 가중합. 초기 `W_CF=0.5, W_CONTENT=0.3, W_POP=0.2`. Day 3 안에 **≤3조합 그리드 1회**만 돌려 고른 뒤 freeze. 버린 조합의 숫자는 `results/eval_<ts>.json` 버전 파일로만 남기고 `latest.csv`·PDF엔 쓰지 않는다. RRF 기각(α/β/γ가 순위로 뭉개져 "가중합 랭커" 서술과 어긋남).
- **D-04 (후보 통로 세부 — Claude 재량 기본안):** `ItemKNNRetriever`: train 전체 행(평점 무관, Phase 2 D-05)의 이진 user×item `scipy.sparse` cosine, 아이템당 이웃 **top-50**을 `artifacts/item_neighbors.npz`(gitignore)에 저장·로드(`make eval` 시간 유지; 없으면 fit), `retrieve` = 사용자 아이템별 이웃 유사도 합 → `seen` 제외 top-k. `ContentRetriever`: 기존 `ContentVectors`(Goodbooks tags TF-IDF)에 `retrieve()` 증분 — seeds(성분별) TF-IDF 평균 벡터 cosine top-k. 채널별 후보 풀 **200**(500~1,000은 production 예시값으로 PDF 표기). 10k×10k 유사도는 chunked top-k로(dense 100M 금지, 아키 §8 리스크 "메모리"). 파라미터는 모듈 상단 상수.

### hybrid_div 재순위화와 Should 꼬리 (reranking 슬라이스 · ★난이도 P3)
- **D-05 (Should 범위):** **REC-06 난이도 가드 + REC-04 gap 피처 구현**, **ablation A/B/C AUC 표는 설계만**(PDF "설계만 — ablation 계획" 1줄, PRD AC13 허용 표기). 이유: Track B엔 사용자별 완독 라벨이 없고 책 수준 P_완독을 목표로 쓰면 `resid_z`와 순환. 시간 부족 시 버리는 순서: gap 피처 → 가드(둘 다 아키 §8 티어 표 "난이도 계통", Grafana 바로 위).
- **D-06 (REC-04 gap 피처):** `ranking/hybrid.py` 가중합에 `gap = difficulty − user_level`·`gap⁺ = max(gap,0)`·`n_completed×gap` 세 항을 상수 가중치(음수, 모듈 상단)로 추가. `BookStatsSource`는 주입 optional — None이거나 `difficulty=None`(결측)·`user_level()=None`(신규)이면 **가중 0**. 따라서 Track A 숫자엔 영향 없음(BookStats 없음)·서버 n=0에서도 0 — 이 페이즈의 증거는 "피처 3항이 각각 순위화 입력에 존재"(AC13 피처 목록 검사)까지. `user_level`(완독 책 `difficulty` 가중 평균, n=0이면 선택 카테고리 prior)은 Phase 5 `state.py`가 채운다 — `CatalogKR.user_level()`은 None 유지.
- **D-07 (MMR):** `reranking/mmr.py` — hybrid 순위 **상위 50**을 풀로, `λ=0.7`, 거리 = 1−cosine(`ItemVectors`: Track A `ContentVectors` / Track B `VectorsKR`), k개 재순위화. **완료 게이트** = `latest.csv`에서 `ild(hybrid_div) > ild(hybrid)` ∧ `ndcg(hybrid_div) ≥ 0.8·ndcg(hybrid)`. 미달 시 **λ=0.5로 1회만** 재실행(D-03 튜닝 1회 규칙 공유), 버린 λ는 `eval_<ts>.json`에만. 해석 문단은 `.claude/rules/evaluation.md` 템플릿으로 `report/draft.md` §4-1.
- **D-08 (가드 순서·입력):** `hybrid_div = rank → MMR → guard`. `reranking/guard.py`는 상단 N(=`K_RANK` 10) 안의 위반 책(`source=="millie_index" ∧ resid_z < −1`)을 N 밖으로 내리고 다음 책을 끌어올린다(후보 삭제 아님, main §5-6). 발동 조건 `n_completed < 3`의 `n_completed`는 **Phase 4에서 `len(user.history)` 대리값**(신규=0 → 발동), Phase 5 `state.py`가 completion 이벤트 수로 교체 — 대리값임을 `guard.py` docstring·PDF 각주에 명시. `BookStatsSource`가 None(Track A)이면 패스스루. 결측(`category_prior`, `difficulty=None`)은 모집단 제외.

### 서버 Track B 4 variant와 user_state_weights 경로 (app · serving 배선)
- **D-09 (`user_state_weights` 경로):** `create_app(…, *, weights: Callable[[UserState], dict[str, float]] | None = None)` keyword-only 인자 **추가**(기본값 있는 인자 추가라 Phase 1 D-09 시그니처 규칙 안, `contracts.py` 무변경). `app/server.py`가 ranking 공개 함수 `state_weights`(이름 자유, `ranking/__init__.py` `__all__`)를 주입, `serving/api.py`는 있으면 호출·없으면 현재처럼 0. 파이프라인과 응답이 같은 함수를 쓰므로 표시 혼합비 = 실제 혼합비. `../.claude/rules/serving.md` `create_app` 시그니처 문구는 Advisor가 갱신. Pipeline Protocol 확장(계약 변경·fake 6개 영향)·serving 중복 구현(이중 구현 금지) 기각.
- **D-10 (서버 variant 재료):** Track B에서 **cf 채널 = `CatalogKR.neighbors`** 엣지(content_sim + category_best, 구조적 이웃) · **content 채널 = `VectorsKR`**(SVD 128) seeds 평균 벡터 cosine 전체 검색 · pop = `pop_rank`. 둘 다 `source="content"`·`source_channels=("content",)`(`.claude/rules/data.md`, `itemknn` 표기 금지). blend·hybrid·mmr·guard 코드는 Track A와 **동일**, 어댑터(`Neighbors`·`ItemVectors`·`BookStatsSource`·`Catalog`)만 다르다 — Track A는 `ContentVectors`+`ItemKNNRetriever`, Track B는 `CatalogKR`+`VectorsKR`. 실측(09-05 22:20, 재빌드 전 스냅샷, seeds 3권): cf∩content 1/10 · cf∩pop 1/10 · content∩pop 0/10 → "4 variant가 서로 다른 책" 성립. `model_version`은 `contracts.VARIANTS` 이름 그대로(`cf_v1` 등, 숫자 불혼합은 `results/`가 Track A 전용이라는 규칙으로 지킨다).
- **D-11 (서버 기본·판정):** 기본 variant는 Phase 2 D-11 규칙으로 `hybrid_div`로 자동 이동(상수 추가 없음). "서로 다른 책" 판정 테스트는 `tests/app/`에서 20권 fixture(`tests/fixtures/millie/serving_sample/`)로 4 variant 상위 k 집합이 pairwise 동일하지 않음을 단정(형태는 planner). `app/pipeline.py`(110줄)가 150줄을 넘으면 Track B 조립을 `app/pipeline_kr.py`로 분리(Advisor).

### 본인 5권 케이스와 freeze 선언 (app/cli · REC-07 · REC-08)
- **D-12 (5권 선정 = 사용자 몫, 도우미 포함):** `cli demo --find <제목 일부>`를 추가 — `artifacts/serving/books_kr.json`에서 제목·저자 부분 일치 → `book_id·title·authors·categories` 출력. Worker는 카탈로그 임의 5권(eligible)으로 파이프라인·테스트를 검증하고, **사용자가 5권 제목을 주면 Advisor가 `make demo SEEDS=…` 1회 실측** → `report/draft.md`. 5권은 밀리 카탈로그 안 실제 읽은 한국 책(구체화 F, D32). Day 3 실측 전까지 제공(사용자 할 일).
- **D-13 (출력 형태·위치):** `cli demo --seeds a,b,c,d,e`는 **stdout 마크다운**만 쓴다: seed별 "『시드』을 좋아하셨다면" 표 5개(이웃 top-5: 제목·저자·카테고리·난이도 ●○○ 3분위·`source=content`) + `hybrid_div` 상위 10 표 1개(α/β/γ 표시, 가드 발동 여부) + 고정 문장 "이웃은 콘텍츠 유사도(제목·소개 TF-IDF)이며 협업 필터링 수치와 섞지 않는다"(`.claude/rules/data.md` 고정 문장). 저장은 `Makefile demo`가 `> report/demo_5books.md`로 리다이렉트(cli는 `report/`를 열지 않음 → 소유권 예외 불필요). PDF P5는 이 표를 축약. 실행 전제 = 최종 카탈로그 스냅샷(domain 참조).
- **D-14 (freeze 4종, 3곳 기록):** Day 3 종료 freeze 대상 ① `retrieval/ranking/reranking` 모듈 상단 상수(α₀/β₀/γ₀·τ·하한·W_*·λ·풀 50·이웃 50·가드 임계) ② `contracts.VARIANTS` 4종(새 variant·후보 통로·feature 금지) ③ `artifacts/serving/*` 최종 스냅샷(`make millie` 재실행 금지, Phase 3 D-02) ④ `serving/schemas*.py` 응답 형태. 기록 ① `.planning/STATE.md` Day 3 게이트 ✅ + "freeze" 문구 ② 개발일지 D 항목(6요소, freeze 상수 값과 `results/eval_<ts>.json` 파일명 인용) ③ `report/draft.md` §4-1 표 숫자 교체·해석 문단. Phase 5·6은 상수를 건드리지 않고 조립·화면만.
- **D-15 (검증·완료 형태):** 슬라이스별 3종 테스트(계약·정확성·안전성, `../.claude/rules/python-tdd.md`, Red=`AssertionError`): retrieval — itemknn fit이 train만·`seen` 제외·npz 라운드트립·content `retrieve` seeds 벡터 / ranking — 재정규화 합 1·신규 β=0·n=20 α≈0.22·min-max 경계·gap 결측 가중 0 / reranking — MMR 손계산(3~5 벡터) ILD 상승·가드가 N 안 위반 책을 내리고 후보 수 보존·BookStats None 패스스루 / app — 4 variant dict 키 = VARIANTS·서버 4 variant 상이·`user_state_weights` β=0. `tests/test_architecture.py`는 고치지 않는다. 완료 = `uv run ruff format . && uv run ruff check . && uv run pytest --no-header`(기준선 256 passed 위에 증가) + `make smoke` + **Advisor 실측** `make eval` 4행(D-07 게이트) → `latest.csv`·`latest_states.csv`·`eval_bar.png` 갱신 → draft §4-1. `contracts.py` 무변경이면 Codex 리뷰는 선택(Model 레인); `serving/api.py` `weights` 배선은 보안 표면 아님 → 선택. 커밋은 사용자 승인 후(Phase 1~3 산출물과 일괄, `.planning/` 포함).

### Claude's Discretion
- Item-KNN 세부(유사도 정규화·shrinkage·chunk 크기·npz 포맷)·content `retrieve` 후보 풀 200의 seen 여유·min-max 분모 0 처리(채널 후보 1개일 때).
- 성분별 점수 계산 방식: seeds/history/session 각각 knn·sim을 따로 내고 α/β/γ로 합칠지, 성분 아이템 목록에 가중치를 붙여 한 번에 knn 할지(결과 동일, 성능 기준).
- `blend` 공개 함수 시그니처(`state_weights(user, *, reset_boost=False, session_active=False) -> dict[str, float]`) 이름·인자 형태, `ranking/__init__.py` `__all__`.
- `hybrid_div` on Track A에서 guard 패스스루 구현(BookStatsSource None 분기 vs 주입 자체를 생략).
- 4 variant 조립 코드 위치(`app/pipeline.py` 분리 여부)·`fit_pipelines(train, books)` 시그니처(ContentVectors를 받아야 함 — 현재 `train`만).
- `cli demo` 표의 난이도 3분위 경계(카탈로그 `difficulty` 분포 33/66 분위)·`--find` 매칭 규칙(대소문자·공백 무시).
- 이웃 npz 캐시 무효화(train sha 저장 vs 파일 존재만) — 평가 재현성이 깨지지 않는 쪽.
- Worker 분할(권장): wave 1 = `retrieval`(itemknn + content retrieve) ‖ `ranking`(blend + hybrid) ‖ `reranking`(mmr + guard) 3명 병렬(서로 `contracts`만 의존, conftest fixture 50×8 벡터·20×50 interactions) → wave 2 = Advisor `app/pipeline.py`·`cli.py`(`demo`·`--find`)·`server.py`·`api.py weights` + `tests/app/` → wave 3 = Advisor `make eval` 4행 실측·D-07 게이트·튜닝 1회·`make smoke`·draft §4-1 → (사용자 5권 제공 후) `make demo` → freeze 선언(D-14). 최종은 planner 판단.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.** 경로는 `millie-rec/` 기준 상대 경로.

### 페이즈 범위·요구사항·이전 결정
- `.planning/ROADMAP.md` — "Phase 4: 추천 파이프라인과 모델 freeze" Goal·착수 전 4단계·Success Criteria 1~5·Should 꼬리
- `.planning/REQUIREMENTS.md` — REC-01~08 원문(Must/Should)
- `.planning/phases/02-track-a/02-CONTEXT.md` — D-04(두 상태 n0/n20, `K_HISTORY=20`)·D-05(학습·seen = train 전체, 정답 rating≥4)·D-06~D-09(결과 파일 형태)·D-11(기본 variant 규칙)·D-14(`ContentVectors` 벡터, `retrieve`는 Phase 4)·Deferred "Item-KNN·Content 후보 생성·blend·MMR·guard → Phase 4"
- `.planning/phases/03-millie-catalog/03-CONTEXT.md` — D-02(freeze 전 마지막 `make millie` 이후 재빌드 금지)·D-08(tags 제외)·D-12(`content_vectors_kr.npz` SVD 128)·D-13(서버 pop = Track B)·D-14(`eligible`)·Claude's Discretion "`user_level()`은 Phase 4 가드 몫"
- `.planning/phases/01-local-serving-skeleton/01-CONTEXT.md` — D-09(`create_app` 시그니처 규칙: 기본값 있는 인자만 추가)
- `.planning/STATE.md` — Blockers(재수집 진행 중·최종 스냅샷 대기·`make millie*` 금지)

### 설계서 (착수 전 ① 전수 조사 대상 절)
- `../.assets/설계서/main 설계서/과제대응전략_최종본(main 설계서).md` §5-1 서빙 파이프라인 4단계(후보 통로·랭킹 피처·가드·앵커 row) · §5-2 ★사용자 상태(수식·상태표·MVP 결정적 스케줄 `α_n = α₀·e^{−n/τ}`) · §5-6 ★난이도 4층(부호 gap·가드 `resid_z<−1 ∧ n_completed<3`·결측 규칙·ablation A/B/C·범위) · §5-7 ★앵커(본인 5권 P5) · §6-1 Offline 3지표
- `../.assets/설계서/시스템 아키텍처, 기술 스택 및 배포(프론트, 백엔드 서빙)/01_시스템_아키텍처_기술스택_배포.md` §3-3 추천 파이프라인(초기값 0.6/0.3/0.1·재정규화·단계 규칙(D-02로 결합)·난이도 Should·이웃 소스·compose 행) · §3-6 Offline(`model_version=<variant>_v1`) · §8 범위 티어(난이도 계통 버리는 순서)·리스크(메모리)
- `../.assets/설계서/브레인스토밍_구체화.md` §2 A 난이도 적합도 · C 앵커 · F 본인 5권
- `../.assets/PRD/PRD_메인_추천_시스템.md` §9 수용 기준 표 — AC1 '온보딩 5권 → 앵커 row' · AC8 '평가 4행 + split_mode 출력' · AC9 'n=0 vs n≥k 지표 분리' · AC10 '난이도 가드(Should)' · AC13 '난이도 4층 피처·ablation'
- `../.assets/설계서/구현 마일스톤/01_마일스톤_착수_프롬프트.md` "마일스톤 '협업·콘텐츠 후보'"·"마일스톤 '랭킹·재순위화·모델 freeze'" 절(브리프 원문·완료 기준)
- `../.assets/설계서/데이터 소스/02_밀리_데이터_적재_계획.md` §4 난이도 · §6 이웃(행 소스 분리)
- 개발일지: 결정 '데모 이웃은 콘텍츠 유사도'(../.assets/개발일지/2026-09-04_Day0.5_브레인스토밍과_데모명세.md 항목 D42) · 결정 '버리는 순서 = 아키 §8 표'(같은 파일 항목 D40) · 결정 'CF는 scipy Item-KNN, ALS는 설계만'(../.assets/개발일지/2026-09-03_*.md 항목 D6) · **결정 'Phase 4 착수 결정 9건'(../.assets/개발일지/2026-09-05_Day1_GSD_초기화와_계약_freeze.md 항목 D68)** · 결정 '밀리 수집 배치 종료·최종 스냅샷 확정'(같은 파일 항목 D67)

### 계약·규칙 (코드 정본)
- `src/millie_rec/contracts.py` — `VARIANTS`·`MODEL_VERSION_SUFFIX`·`K_RECALL=20`·`K_RANK=10`·`SEED`·`UserState(explicit_seeds, history, session).seen`·`Candidate(source)`·`ScoredItem(source_channels, difficulty, reason)`·`BookStats(difficulty, resid_z, source)`·`STATS_SOURCES`·Protocol `CandidateGenerator`·`Ranker`·`Reranker`·`ItemVectors`·`Neighbors`·`BookStatsSource`·`Pipeline`·`Catalog`. **변경 없음 목표**(필요 시 optional 추가만, Advisor + `/codex:review`)
- `src/millie_rec/retrieval/{popularity,content}.py` — `PopularityRetriever`(패턴: fit·retrieve·save/load·`seen` 제외), `ContentVectors`(`retrieve` 증분 대상, ≤150줄)
- `src/millie_rec/app/pipeline.py` — `PopPipeline`·`CatalogPopPipeline`·`fit_pipelines`·`build_pipelines`·`load_catalog`(dict 조립 자리, 110줄)
- `src/millie_rec/app/cli.py` — `cmd_eval` 흐름(`fit_pipelines(sp.train)`·`ContentVectors(books)`·`evaluate`·`write_results`·`write_eval_table`·pop `save`)·`argparse` 서브커맨드(`demo`·`--find` 추가 자리)
- `src/millie_rec/app/server.py` — `create_app(pipelines=build_pipelines(catalog=…), fallback, catalog, db, neighbors=catalog, book_stats=catalog)` — `weights=` 추가 자리
- `src/millie_rec/serving/api.py` — `create_app` 시그니처·`_personalized_response`·`user_state_weights` 0 고정 자리
- `src/millie_rec/data/{catalog_kr,vectors_kr}.py` — `CatalogKR`(`neighbors`·`stats`·`user_level=None`·`eligible`)·`VectorsKR`(npz, 미지 id 0 벡터)
- `src/millie_rec/evaluation/harness.py` — `evaluate(pipeline, users, vectors)`: `seen` 반환 시 ValueError(파이프라인이 seen을 반드시 제외해야 함)
- `tests/conftest.py`(interactions 20×50 ts 있음·item_vectors 50×8) · `tests/evaluation/test_harness.py`(`_FakePipeline` 패턴) · `tests/app/test_pipeline.py`(조립 테스트 패턴) · `tests/test_architecture.py`(star 의존, 고치지 않는다)
- `../.claude/rules/evaluation.md`(variant 고정·해석 문장 템플릿·트랙 분리) · `../.claude/rules/data.md`(Track B `cf`·`hybrid` 채널 = content 표기·고정 문장) · `../.claude/rules/serving.md`(`create_app` 시그니처 — D-09로 갱신) · `../.claude/rules/architecture.md`(star 의존·`artifacts/` = retrieval 소유·`report/` = 사람) · `../.claude/rules/simplicity.md`(150줄·튜닝 Day 4 전·함수 우선) · `../.claude/rules/python-tdd.md`·`python.md`(`uv run`·Red=AssertionError·`default_rng(SEED)`) · `../.claude/rules/local-run.md`(`make smoke`) · `../.claude/rules/report.md`(`[Phase N]` 마커·숫자 출처) · `../.claude/rules/codex-review.md`(Model 레인 선택) · `../.claude/rules/references.md`

### 빌드 (읽기만·Advisor 변경)
- `Makefile` — `eval`(`cli eval --variant all`)·`demo`(`cli demo --seeds $(SEEDS)` → D-13 리다이렉트 추가)·`smoke`. `pyproject.toml` — numpy·scipy·scikit-learn 이미 포함, **의존성 추가 없음**
- `results/latest.csv`·`latest_states.csv`·`eval_20260905_0626.json`(pop 1행 기준선: Recall 0.063·NDCG 0.054·ILD 0.764 / n20 0.080·0.087·0.746) · `report/draft.md` §2-2·§4-1·§5-2·§5-3(`[Phase 4]` 마커, D68 반영 문장)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `PopularityRetriever` — `CandidateGenerator` 구현 패턴(fit train만·`seen` 제외·save/load json). `ItemKNNRetriever`는 같은 패턴 + npz.
- `ContentVectors.vectors(book_ids)` — L2 정규화 dense, 미지 id 0 벡터. `retrieve()`를 같은 파일에 증분(현재 42줄).
- `VectorsKR`(38줄)·`CatalogKR.neighbors/stats/eligible` — Track B 어댑터 완성. Phase 4는 **주입만**.
- `PopPipeline`/`CatalogPopPipeline` — `Candidate → ScoredItem` glue(`position`·`source_channels`) 패턴. 4 variant Pipeline 구현체(retriever들 + ranker + reranker 조립)는 이 패턴 확장 — 위치는 `app/pipeline.py`(조립 glue) 또는 슬라이스 공개 함수, planner 판단.
- `harness.evaluate`가 seen 반환을 ValueError로 잡는다 → MMR·가드가 seen을 다시 넣지 않는지 자동 검증.
- `tests/fixtures/millie/serving_sample/`(20권 json·npz, Phase 3) — 서버 4 variant 테스트 fixture.
- 기준선: `uv run pytest --no-header` **256 passed**(2026-09-05 21:4x, 03-08 Task 1·2 후; 재수집 중 `test_coverage_gate` 1건 RED는 의도), Python 3.11.6, `make eval` 7초(pop).

### Established Patterns
- star 의존: `retrieval`·`ranking`·`reranking`은 `millie_rec.contracts`와 자기 내부만. `ranking`은 `ItemVectors`·`BookStatsSource`를 Protocol로 받는다(구현체 import 금지). `app`은 각 슬라이스 `__init__.py` `__all__`의 공개 이름만 → `__all__` 갱신이 Worker 범위.
- `SOURCE_POPULARITY="popularity"` 중복 정의(retrieval·serving·app) — "중복 < 결합". `SOURCE_CONTENT="content"`·`SOURCE_ITEMKNN="itemknn"`도 같은 방식(contracts 승격은 세 번째 필요 시 Advisor).
- 상수는 모듈 상단 대문자(`ALPHA0=0.6`·`TAU=20`·`ALPHA_FLOOR=0.2`·`W_CF`·`LAMBDA_MMR=0.7`·`MMR_POOL=50`·`KNN_TOP=50`·`POOL=200`·`GUARD_RESID_Z=-1.0`·`GUARD_MIN_COMPLETED=3`), docstring 1줄, `logging` 기본, 파일 ≤150줄.
- sklearn·scipy는 함수 안에서 import(서버가 retrieval 공개 표면을 읽어도 끌어오지 않게, `content.py` 패턴).
- "아티팩트 있으면 로드, 없으면 fit/skip" 패턴(Phase 2 D-10·Phase 3 D-13) → `item_neighbors.npz`도 동일.

### Integration Points
- `app/pipeline.py::fit_pipelines(train)` → `(train, books)`로 확장해 `ContentVectors`를 content retriever·MMR 양쪽에 주입; dict 키 = `VARIANTS` 4종. `build_pipelines(catalog=)`는 Track B 4 variant(D-10) 조립 — `neighbors`·`vectors_kr`·`book_stats` 인자 추가.
- `app/cli.py::cmd_eval` — `wanted` 4개 루프는 이미 `VARIANTS` 순서, `missing` 검사가 Phase 4 메시지를 낸다. `demo`·`--find` 서브커맨드 추가(`make demo` 타깃 존재).
- `app/server.py` — `weights=state_weights` 1인자 추가; `build_pipelines(catalog=catalog, …)`가 4 variant를 등록하면 `/api/recommend?model=` 4종 응답·기본 `hybrid_div`.
- `serving/api.py::create_app` — `weights` 인자·`_personalized_response`의 `user_state_weights` 채우기(Worker serving 소범위 브리프 또는 Advisor 직접, ≤10줄).
- Phase 5 `compose.py`가 앵커 행을 만들 때 `Neighbors`를 직접 쓰고(SERV-02), `hybrid_div` Pipeline은 `persona_shelf`/`items` 평탄화에 쓰인다 — Phase 4는 Pipeline까지만.
- `results/latest.csv` 4행 → `/eval-run`·`eval_table.json`(쇼케이스)·`eval_bar.png`·draft §4-1 표.

</code_context>

<specifics>
## Specific Ideas

- **`latest.csv` 기대 형태(Phase 4 종료):** `pop,cf,hybrid,hybrid_div` 4행 × `recall@20,ndcg@10,ild@10,n_users=2000,split_mode=holdout,model_version=<v>_v1`. 기대 관계: recall(cf) > recall(pop) · ndcg(hybrid) ≥ ndcg(cf) · ild(hybrid_div) > ild(hybrid) ∧ ndcg 하락 ≤20%. `latest_states.csv`: hybrid·cf의 n20 행이 n0 대비 벌어지고 pop은 바닥선(Phase 2 D60 해석).
- **`user_state_weights` 기대:** seeds만 → `{"alpha":1.0,"beta":0.0,"gamma":0.0}` / history 20 → α≈0.22, β≈0.585, γ≈0.195(β:γ=3:1, 합 1.0, 소수 3자리).
- **서버 4 variant 실측(2026-09-05 22:20, 재빌드 전 스냅샷 books 9,450·vectors 8,708):** seeds `[1446, 1086, 1378]`(『위버멘쉬』·『요즘 어른을 위한 최소한의…』·『청춘의 독서』) — cf(엣지) top3에 배지 제목 책('읽던 지점 그대로 이어…') 2권 노출 → **최종 재빌드 전 판정 금지**의 근거. content(SVD) top3 『거꾸로 읽는 세계사』·『노자를 읽다』·『열한 계단』. 가드 대상 책이 cf top10에 1권.
- **밀리 데이터 성립 판정(사용자 질문 09-05, D68):** 실행·검증 가능 = 서버 4 variant 상이·가드 모집단(millie_index 7,799권 중 resid_z<−1 1,173권)·gap 입력(difficulty 82.5%)·MMR 벡터·5권 앵커 / 정량 증명은 Track A만 = α/β/γ n≥20 효과·Recall/NDCG/ILD·MMR 게이트 / 밀리에 해당 없음 = Item-KNN co-read / 대리값 = `n_completed=len(history)`, `user_level=None`(Phase 5). PDF 각주 1문장으로 네 구분을 적는다.
- **`cli demo` 표 헤더 예:** `| # | 책 | 저자 | 분야 | 난이도 | 근거 |` / 근거 셀 = `content 0.41` · 첫 줄 "『위버멘쉬』을 좋아하셨다면 — 이웃은 콘텐츠 유사도(제목·소개 TF-IDF)".
- **PDF 해석 문단 자리(draft §4-1 "측정 설계 `[Phase 4]`" 아래):** 템플릿 "MMR 적용으로 NDCG@10은 x→y로 소폭 하락했지만 ILD@10은 a→b로 개선됐다. 동일 장르 반복을 줄이는 UX 목적상 허용 가능한 trade-off이며 최종 판단은 A/B로 한다."

</specifics>

<deferred>
## Deferred Ideas

- **ablation A/B/C AUC 표(AC13)** → 설계만(D-05). 실서비스 사용자별 완독 라벨 확보 후.
- **`user_level`(완독 책 `difficulty` 가중 평균·카테고리 prior)·`n_completed` = completion 이벤트 수·재설정/세션 부스트 적용** → Phase 5 '서빙 Must 완성' `state.py`(D-02·D-06·D-08 대리값 교체).
- **compose Must 5행·앵커 행 `reason`·`channel_mix`** → Phase 5 SERV-01·02. Phase 4는 Pipeline까지.
- **아키텍처 01 §3-3 단계 규칙 문구 → D-02 결합안으로 갱신·`serving.md` `create_app` 시그니처 갱신** → Advisor 후속(문서, 이 페이즈 실행 중).
- **content_sim ↔ Item-KNN overlap@20 참고 수치** → Day 3 Should(evaluation.md), 시간 있으면. 비교표엔 넣지 않음.
- **정보나루 coLoan 엣지 승격** → Day 3 Should(적재 02 §6), 이 페이즈 무관.
- **`SOURCE_*` 상수 contracts 승격** → 세 번째 슬라이스 필요 시.
- **Pipeline Protocol `weights()` 메서드·variant별 상이한 가중치** → 채택하지 않음(D-09).
- **RRF 병합·λ 그리드 ILD 최대화·가드 후 MMR** → 채택하지 않음(D-03·D-07·D-08).
- **임시 5권으로 먼저 실측 후 교체** → 채택하지 않음(D-12, freeze 이후 재실행 위험).
- **`hybrid_div`의 Track B ILD 참고 수치(유저 로그 불필요)** → 비교표·PDF 금지(evaluation.md 트랙 분리), 필요 시 개발일지 참고값만.

### Reviewed Todos (not folded)
없음 — `todo match-phase 4` 결과 0건.

</deferred>

---

*Phase: 04-freeze*
*Context gathered: 2026-09-05*
