# Phase 2: Track A 정량 평가 기반 - Context

**Gathered:** 2026-09-05
**Status:** Ready for planning

<domain>
## Phase Boundary

PDF 비교표의 유일한 숫자 출처 `results/`를 만든다. Goodbooks-10k(Track A)를 받아 유저별 random holdout으로 나누고, 온보딩 5권 마스킹을 시뮬레이션하고, 3지표(Recall@20·NDCG@10·ILD@10)를 순수 함수로 고정하고, `pop` 기준선 1행을 실측해 떠 있는 서버에 주입(level 0)한다. 이후 Phase 4 '추천 파이프라인과 모델 freeze'(`.planning/ROADMAP.md`)가 `cf`·`hybrid`·`hybrid_div` 행을 얹기만 하면 되는 하네스가 목표다.

이 페이즈가 만드는 것:
- `make data` → `data/raw/`에 Goodbooks-10k 멱등 다운로드 → `data/processed/interactions.parquet`·`books.parquet` — **EVAL-01** Goodbooks 멱등 다운로드
- `data/split.py`: `ts` 없으면 유저별 random holdout(seed 고정), 있으면 전역 temporal, `split_mode` 기록 — **EVAL-02**
- `data/onboarding.py` `mask_onboarding(n=5)`: 5권만 `explicit_seeds`, 미선택 책은 negative가 아니다 — **EVAL-03** = 수용 기준 '미선택 책 ≠ 부정 신호'(`../.assets/PRD/PRD_메인_추천_시스템.md` §9 표, AC7)
- `evaluation/metrics.py` 3지표 순수 함수 + 손계산 테스트, seen 제외 테스트 — **EVAL-04**
- `evaluation/harness.py`·`report.py` → `results/latest.csv`(n=0 4행 구조, Phase 2는 `pop` 1행)·`results/latest_states.csv`·`results/eval_<ts>.json` — **EVAL-05** 기록 구조 · **EVAL-06** n=0 vs n≥k 분리 = 수용 기준 'n=0 vs n≥k 지표 분리'(PRD §9 표, AC9)
- `retrieval/popularity.py` `PopularityRetriever`(train만 fit, seen 제외, save/load) + `retrieval/content.py`의 **`ItemVectors` 벡터 부분만**(Goodbooks tags TF-IDF; `retrieve()`는 Phase 4)
- `app/pipeline.py` `pop` 조립 · `app/cli.py` `data`·`eval` · `app/server.py` pop 아티팩트 있으면 주입 · `serving/api.py` level 0 분기 → `make smoke`가 `fallback_level=0`·`model_version=pop_v1`
- Should 꼬리: **EVAL-07** `evaluation/figures.py` → `report/figures/eval_bar.png`(시간 부족 시 가장 먼저 버림)

**만들지 않는 것:** Item-KNN·Content 후보 생성(`retrieve`)·blend·MMR·guard(Phase 4) · compose 5행·SQLite 쓰기·셀 배정·`user_key` 경로(Phase 5) · Track B 파일(`scripts/`·`data/id_map.csv`·`tests/data/test_millie_*` 불변) · `contracts.py`·`serving/schemas*.py` 변경(계약 freeze, 필요 시 Advisor가 optional 추가 + `/codex:review`).

쓰기 영역: Worker = `src/millie_rec/{data,retrieval,evaluation}/` + `tests/{data,retrieval,evaluation}/` + `serving/api.py` level 0 분기(+`tests/serving/`). Advisor 직접 = `app/{pipeline,cli,server}.py`, 필요 시 `Makefile`. 데이터·아티팩트 파일은 gitignore(`data/raw`·`data/processed`), `results/`는 커밋 대상(커밋 자체는 사용자 승인 후).

</domain>

<decisions>
## Implementation Decisions

### 평가 표본·분할 파라미터 (data 슬라이스 · PDF 각주에 그대로 들어가는 값)
- **D-01:** 테스트 유저 = **2,000명**, `np.random.default_rng(contracts.SEED)`로 적격 유저에서 1회 추출, 전 variant·전 상태 공통(`n_users` 기록). 적격 = 최소 상호작용 필터(유저 ≥5·아이템 ≥5, `.claude/rules/data.md` 상수) 통과 ∧ train 긍정(rating≥4) ≥5(seeds 확보) ∧ test 긍정 ≥1. 제외 수를 json에 기록한다.
- **D-02:** 분할 = **유저별 random holdout, test 20%**(`test_frac=0.2` 상수), seed 고정. `split()`은 함수 하나: `COL_TS`가 전부 결측이면 holdout(`split_mode="holdout"`), 있으면 전역 시점 temporal(`train.ts.max() < test.ts.min()` 단언, `split_mode="temporal"`). Goodbooks는 ts가 없으므로 실측은 holdout이고 **거짓으로 temporal이라 쓰지 않는다**. conftest fixture는 ts가 있어 temporal 분기도 테스트한다.
- **D-03:** seeds = **유저 train 구간의 긍정(rating≥4) 중 seed 고정 무작위 5권**(`contracts.N_ONBOARD_SEEDS`). ts가 없어 "첫 5권"을 시간으로 정할 수 없다 — 온보딩에서 유저가 "좋았던 책"을 고른다는 시뮬레이션. 평점 최고 5권(낙관적)·임의 5권(별점 1~2가 시드)은 기각.
- **D-04:** 두 상태. **n=0** = `UserState(user_id, explicit_seeds=seeds, history=())`. **n≥k** = `UserState(explicit_seeds=seeds, history=seeds 제외 train 전체)`, **k=20**(`K_HISTORY=20` 상수): seeds 외 train 행이 20개 이상인 유저만 n≥k 표에 들어가고 그 `n_users`를 별도 기록(모집단이 n=0과 다름을 표에 명시). 두 상태의 test 정답은 같다 — 달라지는 것은 `UserState`만. `k`는 PDF 각주.
- **D-05:** 행 범위. **학습(pop 카운트, Phase 4 Item-KNN fit)과 `seen` 제외 = train 전체 상호작용(평점 무관, "평점이 있다 = 읽었다")**. **정답 R_u = test 중 rating≥4만**(`data/labels.py`, 결정 '착수 전 운영 결정 4건'(../.assets/개발일지/2026-09-04_Day0.5_브레인스토밍과_데모명세.md 항목 D45)). 라벨(만족)과 소비(읽음)를 구분 — Qualified Reading 서술과 일치. 미선택 책은 어느 단계에서도 negative 라벨을 만들지 않는다(테스트로 단정).

### n=0 vs n≥k 표 형태 (evaluation 슬라이스 · 결과 파일)
- **D-06:** **`results/latest.csv` = n=0 상태의 variant별 4행(Phase 2는 `pop` 1행)** — main 설계서 §6-1 "유저별 초기 5권만 관측된 상태로 마스킹해 온보딩 시뮬레이션"이 메인 비교표의 정의. 수용 기준 '평가 4행 + split_mode 출력'(PRD §9 표, AC8)·`/eval-run` 4행 검사 불변. 컬럼: `variant, recall@20, ndcg@10, ild@10, n_users, split_mode, model_version`, 소수 3자리.
- **D-07:** **`results/latest_states.csv`** = `variant × state(n0 | n20)` 행, 컬럼 `variant, state, recall@20, ndcg@10, ild@10, n_users`. 등록된 **전 variant 자동**(Phase 2는 pop×2 — pop이 상태에 무감한 것이 "가중치 있는 모델만 변한다"의 대조군). PDF P3 ★시간 가변 가중치 박스의 표 출처.
- **D-08:** `results/eval_<YYYYMMDD_HHMM>.json` 하나에 두 표 + 실행 메타: `dataset="goodbooks-10k"`, `split_mode`, `test_frac`, `seed`, `n_users`(상태별), `n_excluded`, `k_recall`, `k_rank`, `n_onboard_seeds`, `k_history`, `min_user_interactions`, `min_item_interactions`, `git_sha`, `elapsed_s`, `created_at`, `rows[]`, `states[]`. `contracts.EvalResult`에는 `state`·`split_mode` 필드가 없으므로 **실행 수준 메타로 기록**하고 계약을 바꾸지 않는다.
- **D-09:** `artifacts/serving/eval_table.json`(Phase 5 SERV-13 `GET /api/showcase`가 읽음)의 형태를 Phase 2가 정한다: `{"rows": <latest.csv 행 그대로>, "meta": {dataset, split_mode, n_users, k_recall, k_rank, seed, git_sha, created_at}}`. **states 표는 넣지 않는다**(쇼케이스는 온보딩 시뮬레이션 비교표 하나만, n≥k 표는 PDF P3 전용). 쓰는 주체는 `app/`(`artifacts/serving/` 소유 규칙) — `cli eval` 끝에 복사.

### pop 서버 주입 형태 (app · serving)
- **D-10:** **아티팩트 있으면 로드, 없으면 level 3 유지.** `make eval`(cli)이 `PopularityRetriever.save()`로 상위 N(book_id·score, N은 `K_MAX(100)+seen 여유`를 넘는 값, 예 1,000) 작은 json을 `artifacts/` 아래에 쓰고(`artifacts/` 소유 = retrieval, `fit/load`는 retrieval 안에서만), `app/server.py`는 파일이 있으면 `pipelines={"pop": …}`, 없으면 `{}`. 아티팩트·DB·네트워크 없이 기동 원칙(`../.claude/rules/local-run.md`) 유지. 기동 시 parquet fit(6M행 pandas 로드)은 아키텍처 01 §8 리스크 "서빙 pandas 미로드"로 기각. **주의: 서버에 올라가는 Goodbooks `book_id`는 밀리 카탈로그 id와 다른 체계 — Phase 3 '밀리 카탈로그 빌드' 카탈로그 주입 시 교체되는 임시 배선**(Deferred 참조).
- **D-11:** `model` 쿼리가 없을 때 기본 variant = **등록된 것 중 `contracts.VARIANTS` 순서상 마지막**(Phase 2=`pop`, Phase 4=`hybrid_div`). 셀 배정(A→`hybrid`, B→`hybrid_div`, 아키텍처 01 §3-3)은 Phase 5 몫이고 그 전까지의 임시 규칙. 상수 추가 없음.
- **D-12:** level 0 응답 형태(compose.py 이전) = **`trending` 1행에 pop 결과 + `items`에 상위 k 평탄화**. Phase 1 D-02의 행 뼈대(`row_id="trending"`, 제목 "지금 많이 읽는 책", `purpose="fallback"`, `serving/fallback.py`의 `trending_row`) 재사용. 바뀌는 것은 `model_version=f"pop{MODEL_VERSION_SUFFIX}"`·`fallback_level=0`·items·`items`(`Recommendation(book_id, score)`)만. `user_state_weights`는 0 유지(blend는 Phase 4·상태는 Phase 5). 행 순서 정본은 Phase 5 `compose.py`.
- **D-13:** **seeds가 있을 때만 level 0. seeds·`user_key` 모두 없는 익명 요청은 level 3 유지**(백엔드 서빙 01 §5 "익명은 3, 가중치 전부 0"). `make smoke`는 `seeds=1,2,3&k=5`를 주므로 level 0을 본다. `user_key` 경로는 Phase 5 `state.py`. 파이프라인이 예외를 던지면 기존 `_fallback_response`로 level 3 200(Phase 1 D-13 안전성 유지, 테스트 추가).

### ILD 벡터 시점 (retrieval · data)
- **D-14:** **Phase 2에서 `retrieval/content.py`에 `ItemVectors` 구현(벡터 부분만, ≈60줄)을 먼저 만든다** — `books.parquet`의 `tags` 문자열에 sklearn `TfidfVectorizer` fit → `vectors(book_ids)`가 L2 정규화 dense `np.ndarray`. 하네스에 주입해 **pop 1행이 Day 1에 3지표 전부 실측**. 후보 생성 `retrieve()`(`CandidateGenerator`)는 Phase 4 REC-01이 같은 파일에 증분(파일 ≤150줄 유지). 서버에는 Phase 2에서 벡터를 올리지 않는다(평가 전용).
- **D-15:** `books.parquet` `tags` = 책별 `book_tags.csv` count 상위 20개 태그 이름(`tags.csv` 조인) 공백 join. **서가 관리 잡음 태그는 모듈 상단 상수 목록으로 제외**(`to-read`, `currently-reading`, `favorites`, `owned`, `books-i-own`, `kindle`, `library`, `to-buy`, `owned-books`, `default`, `ebook`, `audiobook` 등 — 정확한 목록은 Worker가 태그 빈도 상위를 보고 확정, 상수로 고정). 안 빼면 거의 모든 책이 같은 태그를 공유해 ILD가 일괄 눌린다. `categories`는 빈 리스트(Goodbooks엔 분류 없음, Track A에서 미사용). 나머지 계약 컬럼(`book_id title authors image_url average_rating ratings_count original_publication_year`)은 `books.csv`에서 이름 그대로.

### 검증·완료 형태
- **D-16:** 슬라이스별 3종 테스트(계약·정확성·안전성, `../.claude/rules/python-tdd.md`), Red는 `AssertionError`로 확인. 필수 항목: `data` — temporal 분기 `train.ts.max() < test.ts.min()` · holdout 분기 `split_mode=="holdout"`·유저별 비율 · `mask_onboarding` 반환에 negative 구조가 없고 seeds ⊂ 긍정 · 라벨 `rating≥4` / `retrieval` — pop이 `user.seen`을 제외 · fit이 train만 받음 · save/load 라운드트립 · `vectors()` shape·정규화 / `evaluation` — Recall·NDCG·ILD 손계산(3~5 아이템) · 하네스가 test 라벨을 `UserState`에 넣지 않음(`user.seen ∩ R_u == ∅` 단정) · 두 상태 출력 / `serving` — 가짜 Pipeline 주입 시 `fallback_level==0`·`model_version=="pop_v1"`·`rows[0].row_id=="trending"`·`items` 비어 있지 않음 · 익명 요청은 level 3 · 파이프라인 예외 → level 3 200. `tests/test_architecture.py`는 고치지 않는다.
- **D-17:** 완료 기준 = `uv run ruff format . && uv run ruff check . && uv run pytest --no-header`(기준선 104 passed / 2 skipped 위에 증가) + `make smoke` PASS(pop 아티팩트 있을 때 level 0) + **Advisor가 `make data && make eval` 실측** → `results/latest.csv` `pop` 1행·`latest_states.csv` 2행·`eval_<ts>.json`·`artifacts/serving/eval_table.json` 존재 → `report/draft.md` P4/P5에 실측 문장 1줄. `contracts.py` 무변경이면 Codex 리뷰는 선택(`../.claude/rules/codex-review.md` Model 레인 행).
- **D-18:** 커밋 없음(Phase 1 산출물 커밋도 사용자 승인 대기, 결정 'Phase 1 실행 방식'(../.assets/개발일지/2026-09-05_Day1_GSD_초기화와_계약_freeze.md 항목 D55)). `results/`는 커밋 대상 파일이므로 승인 시 함께.

### Claude's Discretion
- **다운로드 구현**: GitHub `zygmuntz/goodbooks-10k` raw CSV 4개(`ratings.csv`≈69MB·`books.csv`·`book_tags.csv`·`tags.csv`) 또는 release zip, `data/raw/goodbooks/` 존재+크기 검사로 멱등, `to_read.csv` 미사용. 네트워크는 `make data`에서만 — 테스트는 절대 다운로드하지 않음(conftest fixture).
- **`interactions.parquet`의 `event` 값**: 데이터 사실 그대로 `"rating"`(`contracts.EVENT_TYPES`에 있음) 권장. `ts`는 전부 None(nullable). 첫 파싱 후 parquet 캐시.
- **파일 분할**: `data/{load,split,onboarding,labels}.py` · `retrieval/{popularity,content}.py` · `evaluation/{metrics,harness,report,figures}.py` · `app/{pipeline,cli}.py`(+`server.py` 수정). 각 ≤150줄, `__init__.py` `__all__`에 공개 이름 추가(`load_interactions`·`load_books`·`split`·`mask_onboarding`·`is_positive`·`PopularityRetriever`·`ContentVectors`(이름 자유)·`recall_at_k`·`ndcg_at_k`·`ild_at_k`·`evaluate`·`write_results` 등).
- **Pipeline 어댑터 위치**: `pop` variant는 retriever 단독이라 `Candidate → ScoredItem` 변환 glue가 필요. `app/pipeline.py`의 작은 래퍼(조립 glue, 비즈니스 규칙 없음) 또는 retrieval 공개 함수 — planner 판단. `pipelines` dict는 `contracts.VARIANTS` 이름 그대로.
- **CLI**: `argparse` 서브커맨드 `data`, `eval --variant all|pop|…`(등록된 variant만 실행), Makefile `data`·`eval` 타깃은 이미 이 진입점을 가리킴(`uv run python -m millie_rec.app.cli …`). 새 타깃 불필요.
- **`/health`**: pipelines가 비어 있지 않으면 `model_version`=기본 variant의 버전, `artifacts_loaded_at`=로드 시각 ISO — Phase 2에서 채울지 Phase 5로 미룰지 planner 판단(스키마 optional이라 어느 쪽도 계약 안).
- **git sha 취득**: `subprocess.run(["git","rev-parse","--short","HEAD"])` 실패 시 `null`.
- **아티팩트 파일 이름·N**: `artifacts/popularity.json` 등, N=1,000 권장. `.gitignore`의 `artifacts/`(단 `artifacts/serving/`는 커밋) 확인.
- **Worker 분할(권장)**: wave 1 = `data` ‖ `evaluation` ‖ `retrieval` 3명 병렬(서로 `contracts`만 의존, evaluation·retrieval 테스트는 conftest fixture) → wave 2 = `serving` level 0 분기(+테스트, 작은 브리프) ‖ Advisor `app/pipeline.py`·`cli.py`·`server.py` → wave 3 = Advisor `make data && make eval` 실측·`make smoke`·`draft.md`. EVAL-07 막대그래프는 wave 3 끝에 시간 남으면.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.** 경로는 `millie-rec/` 기준 상대 경로.

### 계약·규칙 (코드 정본)
- `src/millie_rec/contracts.py` — `SEED`·`COL_USER/ITEM/TS/EVENT/RATING`·`K_RECALL=20`·`K_RANK=10`·`N_ONBOARD_SEEDS=5`·`VARIANTS`·`MODEL_VERSION_SUFFIX`·`DIR_RAW/PROCESSED/ARTIFACTS/RESULTS/FIGURES`·`UserState.seen`·`Candidate`·`ScoredItem`·`Recommendation`·`EvalResult`·`CandidateGenerator`·`ItemVectors`·`Pipeline` Protocol. **변경 금지**(optional 추가만, Advisor + `/codex:review`)
- `src/millie_rec/serving/api.py` — L123 주석 "Phase 2 가 pipelines["pop"] 을 주입하면 여기에 level 0 분기를 추가한다", `_fallback_response(level=)`, `create_app(pipelines, fallback, *, catalog, db, …)` 시그니처 불변
- `src/millie_rec/serving/fallback.py` — `trending_row(items)`·`GlobalPopularFallback`(D-12 재사용)
- `src/millie_rec/serving/schemas.py` — `RecommendOut.from_contract`·`HealthOut`. **변경 금지**
- `src/millie_rec/app/server.py` — 현재 `create_app(pipelines={}, …)` 호출 + StaticFiles 마지막. Phase 2는 `pipelines` 인자만 채운다(Phase 1 CONTEXT D-09)
- `tests/conftest.py` — 합성 fixture `interactions`(유저 20×아이템 50, **ts 있음**)·`item_vectors`(50×8). 유지·재사용
- `tests/test_architecture.py` — star 의존 검사. 슬라이스는 `contracts`와 자기 내부만, `app`은 `from millie_rec.<slice> import <공개 이름>`만. **고치지 않는다**
- `tests/serving/test_smoke.py` — `_app()` 조립 패턴·level 3 단정(level 0 테스트 작성 패턴)
- `../.claude/rules/data.md` Track A 규칙 — 컬럼·필터 상수·`mask_onboarding`·라벨·`split_mode` 거짓 표기 금지
- `../.claude/rules/evaluation.md` — 지표 정의(Recall 분모 |R_u|, NDCG 이진·IDCG=min(|R_u|,K), ILD 1−cosine)·variant 고정·결과 파일·누수 방지·해석 문장 템플릿
- `../.claude/rules/python.md` — `uv run`만, `default_rng(SEED)`, 컬럼명은 `contracts` 상수, 유저 루프는 평가에서만
- `../.claude/rules/python-tdd.md` — Red=`AssertionError`, 3종 테스트, `metrics.py`·`split.py`는 경로 전부 테스트
- `../.claude/rules/architecture.md` — 레인·산출물 소유권(`artifacts/`=retrieval, `artifacts/serving/`=app export, `results/`=evaluation)
- `../.claude/rules/simplicity.md` — 파일 ≤150줄, 함수 우선, 클래스는 Protocol 만족 시만(`PopularityRetriever`·`ItemVectors` 구현체가 그 경우)
- `../.claude/rules/local-run.md` — 아티팩트 없이 기동, 모든 브리프 완료 기준 `uv run pytest --no-header` + `make smoke`
- `../.claude/rules/references.md` — 약호 단독 금지 · `../.claude/rules/codex-review.md` — Model 레인은 선택

### 설계서 (착수 전 ① 전수 조사 대상 절)
- `../.assets/설계서/main 설계서/과제대응전략_최종본(main 설계서).md` §5-2 ★사용자 상태(MVP 문장: "n=0 vs n≥k에서 Recall/NDCG가 어떻게 달라지는지 실측해 P3에 표로") · §6-1 Offline 3지표(분할 원칙·`split_mode=holdout` 각주·비교표 4행·2트랙 문장) · §8 5일 계획(Day 1 종료 조건 "Popularity@K 실측")
- `../.assets/PRD/PRD_메인_추천_시스템.md` §6-1 Offline(★증거 문장) · §9 수용 기준 표 AC7 '미선택 책 ≠ 부정 신호'·AC8 '평가 4행 + split_mode 출력'·AC9 'n=0 vs n≥k 지표 분리' · §11 리스크("공개 데이터에 타임스탬프 부족 → 분할 방식 한계 PDF 명시")
- `../.assets/설계서/데이터 소스/01_한국_도서_데이터_확보_방안.md` §1 R1(유저 로그는 Track A만) · §4-1 Track A 확정 · §4-3 브릿지("Goodreads에서 측정, 한국 카탈로그에서 서빙" — D-10 임시 배선의 근거)
- `../.assets/설계서/구현 마일스톤/01_마일스톤_착수_프롬프트.md` §0 착수 전 4단계 · §1 인벤토리 · "마일스톤 'Track A 평가 기반'" 절(브리프 원문·완료 기준)
- `../.assets/설계서/시스템 아키텍처, 기술 스택 및 배포(프론트, 백엔드 서빙)/01_시스템_아키텍처_기술스택_배포.md` §3-3 추천 파이프라인(variant dict·기본 셀 배정은 Phase 5) · §3-6 Offline(`make eval`→`results/`, `eval_table.json`, `model_version=<variant>_v1`) · §8 범위 티어·리스크("서빙 pandas 미로드")
- `../.assets/설계서/백엔드 서빙/01_백엔드_서버_구성.md` §5 `GET /api/recommend`(레거시 `seeds`, "익명은 3, 가중치 전부 0" — D-13 근거)
- `../.assets/설계서/바이브 코딩 구현을 위한 프로그래밍 방법론과 아키텍처/01_개발_방법론_및_아키텍처.md` §3-2 슬라이스 파일 목록·공개 표면
- 개발일지: 결정 '적재 범위·스키마·난이도·이웃 결정'(../.assets/개발일지/2026-09-04_Day0.5_브레인스토밍과_데모명세.md 항목 D37 — Track A holdout·Poetry 배경 레인) · 결정 '데모 이웃은 콘텐츠 유사도'(같은 파일 항목 D42) · 결정 '착수 전 운영 결정 4건'(같은 파일 항목 D45 — `rating≥4`) · 결정 'Phase 1 실행 방식'(../.assets/개발일지/2026-09-05_Day1_GSD_초기화와_계약_freeze.md 항목 D55 — 커밋 0)
- `.planning/ROADMAP.md` "Phase 2: Track A 정량 평가 기반" · `.planning/REQUIREMENTS.md` EVAL-01~07 · `.planning/phases/01-local-serving-skeleton/01-CONTEXT.md` D-02(trending 행)·D-09(`create_app` 시그니처)·D-10(`GlobalPopularFallback`)·D-13(안전성 테스트)

### 빌드 (읽기만)
- `Makefile` — `data`·`eval`(`cli eval --variant all`)·`smoke`(8010, `seeds=1,2,3&k=5`) 타깃 이미 존재. 새 타깃 불필요
- `pyproject.toml` — numpy·scipy·pandas·pyarrow·scikit-learn·matplotlib 이미 포함. **의존성 추가 없음**
- `README.md` L16 — Track A 문장·Goodbooks 출처(`github.com/zygmuntz/goodbooks-10k`)·CC BY-SA 4.0 귀속

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `contracts.UserState.seen` — `explicit_seeds ∪ history ∪ session` frozenset. pop의 seen 제외와 하네스 누수 단정이 이 속성 하나로 성립
- `serving/fallback.py::trending_row(items)` — level 0 응답의 행 뼈대(D-12), 새 행 상수 불필요
- `serving/api.py::_fallback_response(…, level=)` — 파이프라인 예외 시 level 3 경로 재사용(D-13)
- `tests/conftest.py::interactions`(ts 있음)·`item_vectors`(50×8) — split temporal 분기·ILD 손계산·MMR 대비 벡터 테스트에 그대로 사용. holdout 분기는 fixture에서 `ts`를 None으로 바꿔 테스트
- `tests/serving/test_smoke.py::_app(tmp_path, fallback=)` — `pipelines={"pop": FakePipeline()}`만 추가해 level 0 테스트 작성
- 기준선: `uv run pytest --no-header` **104 passed / 2 skipped**(2026-09-05 Phase 1 검증), Python 3.11.6. `-q`는 pyproject `addopts`에 이미 있어 CLI에 붙이지 않는다

### Established Patterns
- star 의존: `data`·`retrieval`·`evaluation`은 `from millie_rec.contracts import …`와 자기 내부만. `app/pipeline.py`는 `from millie_rec.retrieval import PopularityRetriever`처럼 공개 표면만 → 각 슬라이스 `__init__.py` `__all__` 갱신이 Worker 범위
- 파일 ≤150줄 · docstring 1줄 · 설정은 모듈 상단 대문자 상수(`TEST_FRAC=0.2`, `N_TEST_USERS=2000`, `K_HISTORY=20`, `MIN_USER_INTERACTIONS=5`, `MIN_ITEM_INTERACTIONS=5`, `NOISE_TAGS=(…)`, `TOP_TAGS=20`) · `logging` 기본
- 난수는 `np.random.default_rng(SEED)` 하나. 같은 입력 → 같은 `latest.csv`
- 행렬 연산은 numpy/scipy; 유저 단위 파이썬 루프는 평가 하네스에서만 허용
- 현재 `data/`·`retrieval/`·`evaluation/` 슬라이스는 `__init__.py`(`__all__=[]`)만 — **전부 신규, 재구성 대상 없음**. `results/`·`report/figures/`는 `.gitkeep`만

### Integration Points
- `serving/api.py::recommend` L123 — `if seeds and pipelines: pipe = pipelines[model or <VARIANTS 마지막 등록>]` 분기 신설 → `RecommendResponse(model_version=…, fallback_level=0, rows=(trending_row(items),), items=…)` → 기존 `RecommendOut.from_contract`
- `app/server.py` — `pipelines={}` 자리를 `build_pipelines()`(아티팩트 있으면 `{"pop": …}`)로. 시그니처·StaticFiles 순서 불변
- `app/cli.py` — `data`(load→parquet), `eval`(load parquet → split → sample users → mask → 등록 variant × 2 상태 → report → `artifacts/serving/eval_table.json` 복사 → pop `save()`)
- Phase 3 '밀리 카탈로그 빌드'가 `catalog=` 주입 시 D-10의 Goodbooks pop 배선을 Track B 인기로 교체(Deferred) · Phase 4가 `pipelines`에 `cf`·`hybrid`·`hybrid_div`를 추가하면 D-11 기본 variant가 `hybrid_div`로 자동 이동 · Phase 5 `compose.py`가 D-12의 단일 `trending` 행을 Must 5행으로 대체
- `/eval-run` 스킬이 `results/latest.csv`를 읽어 PDF 비교표 형식으로 출력·diff — 컬럼 이름(D-06)이 그 입력

</code_context>

<specifics>
## Specific Ideas

- **Goodbooks-10k 사실(다운로드 전 확인용):** 유저 53,424 · 평점 5,976,479행(1~5) · 도서 10,000 · 타임스탬프 없음. `ratings.csv(user_id, book_id, rating)`, `books.csv(book_id, goodreads_book_id, authors, original_publication_year, title, average_rating, ratings_count, image_url, …)`, `book_tags.csv(goodreads_book_id, tag_id, count)`, `tags.csv(tag_id, tag_name)`. `book_tags`는 `goodreads_book_id` 키 — `books.csv`로 `book_id`에 매핑해야 한다(함정).
- **`latest.csv` 기대 형태(Phase 2 종료):**
  ```
  variant,recall@20,ndcg@10,ild@10,n_users,split_mode,model_version
  pop,0.xxx,0.xxx,0.xxx,2000,holdout,pop_v1
  ```
- **`latest_states.csv` 기대 형태:** `variant,state,recall@20,ndcg@10,ild@10,n_users` / `pop,n0,…,2000` / `pop,n20,…,<n≥k 적격 수>`
- **level 0 `GET /api/recommend?seeds=1,2,3&k=5` 기대 응답 예시:**
  ```json
  {"recommendation_id":"rec_…","model_version":"pop_v1","fallback_level":0,"forced":false,
   "latency_ms":1.2,"latency_breakdown":{"total":1.2},"user_state_weights":{"alpha":0.0,"beta":0.0,"gamma":0.0},
   "items":[{"book_id":…,"score":…}],
   "rows":[{"row_id":"trending","title":"지금 많이 읽는 책","purpose":"fallback","items":[…5개, book_id ∉ {1,2,3}]}]}
  ```
  같은 요청에서 `seeds`를 빼면 Phase 1과 동일한 level 3 응답.
- **PDF 각주 문장(Phase 2가 근거를 만드는 것):** "Goodbooks-10k(CC BY-SA 4.0), 유저 ≥5·아이템 ≥5 필터, 유저별 random holdout 20%(`split_mode=holdout`, 타임스탬프 없음), 테스트 유저 2,000명(seed 42), 온보딩 시뮬레이션 = train 긍정 중 무작위 5권을 seeds로 노출, n≥k 표는 seeds 외 이력 ≥20인 유저." — `report/draft.md` P4에 실측과 함께 1줄.
- **★시간 가변 가중치 증거의 해석 방향(P3):** pop은 두 상태에서 거의 같고(seen이 늘어난 만큼만 변동), Phase 4의 `hybrid`는 n≥k에서 β가 살아나 달라져야 한다 — Phase 2는 그 대조군 행을 먼저 만든다.

</specifics>

<deferred>
## Deferred Ideas

- **서버의 Goodbooks pop 배선 교체** → Phase 3 '밀리 카탈로그 빌드'가 `catalog=` 주입 시(또는 Phase 4 브릿지 `build_pipeline(variant, catalog)`), 서버의 `pop`은 Track B 인기(`popularity_kr`/`Catalog.popular`)로. D-10은 level 0 배선의 walking-skeleton 증명일 뿐 데모 카탈로그와 id 체계가 다르다.
- **UCSD Poetry 배경 레인(temporal split)** → Should, 60분 하드 중단(결정 '적재 범위·스키마·난이도·이웃 결정'(../.assets/개발일지/2026-09-04_Day0.5_브레인스토밍과_데모명세.md 항목 D37)). 성공 시에만 `split_mode=temporal`. Phase 2 범위 밖 — `split()`의 temporal 분기는 fixture로만 검증.
- **Item-KNN·Content 후보 생성(`retrieve`)·blend·MMR·guard** → Phase 4 REC-01~06. `content.py`는 Phase 2 벡터 위에 증분.
- **`user_key`·스냅샷·셀 배정·SQLite 쓰기·compose 5행** → Phase 5 SERV-01~09. D-11 기본 variant 규칙은 셀 배정이 붙으면 대체.
- **쇼케이스에 n≥k 표 노출** → 채택하지 않음(D-09). PDF P3 전용.
- **`contracts.EvalResult`에 `state`·`split_mode` 필드 추가** → 채택하지 않음(D-08 실행 메타로). 필요해지면 Advisor가 optional 추가 + `/codex:review`.
- **`/health.model_version`·`artifacts_loaded_at` 채우기** → Claude 재량(Phase 2 또는 Phase 5).
- **EVAL-07 막대그래프** → Should 꼬리, wave 3 끝에 시간 남으면. 없으면 PDF는 표만.
- **`to_read.csv`를 암묵 신호로 사용** → 채택하지 않음(라벨 정의 `rating≥4` 유지).
- **매 실행 유저 재표본** → 채택하지 않음(seed 고정 1회 추출, 재현성).

### Reviewed Todos (not folded)
없음 — `todo match-phase 2` 결과 0건.

</deferred>

---

*Phase: 02-track-a*
*Context gathered: 2026-09-05*
