# Phase 3: 밀리 카탈로그 빌드 - Context

**Gathered:** 2026-09-05
**Status:** Ready for planning

<domain>
## Phase Boundary

밀리 공개 도서 페이지 수집분(`data/raw/millie_pages.jsonl`)이 `books_kr.parquet`(사전순 surrogate `book_id` + `data/id_map.csv` append-only) · `item_edges_kr.parquet`(content_sim + category_best 이웃) · 완독지수 파생 난이도(`resid_z`·`len_z`·`difficulty=σ(−resid_z)`)로 빌드되어 커버리지 게이트·이웃 게이트 3을 통과하고, `make millie-export`가 `artifacts/serving/{books_kr.json, item_edges_kr.json, content_vectors_kr.npz, popularity_kr.json}` + `demo/fallback/popular.json`을 만들며, `data/catalog_kr.py` 어댑터(`Catalog`·`Neighbors`·`BookStatsSource`)를 서버에 주입하면 `/api/recommend`가 밀리 책으로 응답한다(ROADMAP Phase 3 성공 기준 1~5, REQUIREMENTS DATA-01~07 Must · DATA-08 Should).

**이 페이즈가 아닌 것:** 후보 통로·blend·MMR·가드(Phase 4 '추천 파이프라인과 모델 freeze') · compose 5행·SQLite 쓰기·state·level 1/2 cascade(Phase 5 '서빙 Must 완성') · mock 재생성·화면(Phase 6 '데모 재구성') · Railway(Phase 7 '배포'). 수집기·파서 자체는 이미 완료(트래킹 03 §1 단계 1·2 ✅)이며 이 페이즈는 배치 **산출물을 소비**한다.

</domain>

<decisions>
## Implementation Decisions

### 빌드 스냅샷 시점 (data 레인 · 트래킹 03 §1 단계 3~6)
- **D-01:** **지금 있는 5,157권으로 첫 빌드를 한다**(배치는 계속 돈다). 게이트·어댑터·export·서버 주입을 오늘 검증하고, 배치 종료 후 `make millie` 1회로 **재빌드**한다. `id_map.csv`가 append-only라 재빌드에도 기존 `book_id` 변동 0(성공 기준 2의 diff 검증 = `git diff --numstat data/id_map.csv` 삭제 0). walking skeleton 원칙(`../.claude/rules/local-run.md`).
- **D-02:** PDF·쇼케이스·README에 쓰는 카탈로그 규모(N권)·커버리지 수치는 **마지막 재빌드 스냅샷** 기준 — 정본은 `results/millie_coverage.csv`의 `_n_records`와 `collected_at` 범위. Day 3 모델 freeze 전 마지막 `make millie` 이후 재빌드 금지(freeze 이후 카탈로그 변경은 실측·본인 5권 케이스를 깨뜨린다).
- **D-03:** 배치가 **Day 2(09-06) 오전에도 돌고 있으면 그 시점에 중단**하고 그 스냅샷을 최종으로 한다. 결정 '상한 없음'(트래킹 03 헤더, 사용자 2026-09-04)에 **시간 상한**을 보완하는 것이며 번복이 아니다. 미수집 프론티어 수를 `../.assets/설계서/데이터 소스/03_밀리_데이터_적재_트래킹.md` §2에 기록한다.

### 커버리지 게이트 — 유효 레코드 정의와 §7 미달 조치 (적재 계획 02 §7 표)
- **D-04:** 적재 계획 02 §7 표(항목별 미달 시 조치)가 **그대로 정책**이다. 실측(5,157권): image_url 99.9% · categories 99.9% · completion_prob 86.3% · formats 98.8% · seg_dist 83.8% · 카테고리 27종 · 20권 이상 21종 — title을 제외한 전 항목 통과. **미달 조치는 title 항목만 실제로 발동**하며 아래 D-05·D-06으로 처리한다. 다른 항목이 최종 스냅샷에서 미달하면 §7 표를 그대로 적용하고 개발일지 D 항목으로 기록한다(재논의 없음).
- **D-05:** **유효 레코드 = `status == 200` ∧ `title` 있음.** 나머지 성공 페이지는 두 종류로 나눠 **카탈로그·id 부여·게이트 분모에서 제외**하고 `millie_raw_coverage.json`에 건수만 기록한다: ① **껍데기**(title·category·shelf_count 전무, 성인 표지 플레이스홀더 `adult-cover-*.webp` 2건 포함, 현재 5건) → `n_skipped_empty` ② **파서 미스**(title 없음 ∧ shelf_count 있음, 현재 1건: 외국어 분야 shelf 2,038) → `n_skipped_titleless`. 이번 페이즈에는 파서를 고치지 않는다.
- **D-06:** title 게이트 100%는 유효 레코드 정의상 항진이므로 파서 결함 탐지기 역할을 **`n_skipped_titleless / n_success ≤ 0.5%` 단언**(스크립트 상수 `MAX_TITLELESS_RATIO = 0.005`)이 이어받는다. 최종 스냅샷에서 초과하면 그때 파서 수정(픽스처 추가)·해당 URL만 재수집. `tests/data/test_millie_catalog.py::test_coverage_gate`에 이 단언을 추가한다(테스트 수정은 게이트 강화 방향만).
- **D-07:** **밀리 분류를 그대로 분야로 취급**한다 — 형식형 분류(오디오북 673·챗북 165·밀리 오리지널 88·디즈니·도슨트북·오브제북·매거진·세계문학전집)도 `categories` 값이자 게이트 분모다. 카테고리 게이트(종수 ≥8 · 20권 이상 ≥6)와 이웃 게이트 ③ '동일 카테고리' 모두 동일. 화면 01 §8 매핑표 폐기·'밀리 분류 직접 사용' 결정과 일관, 코드 변경 0. (형식형을 빼도 20권 이상 주제 분야 19종이라 게이트 결과는 같다.)

### content_sim 이웃 게이트 (적재 계획 02 §6 · `scripts/build_millie_edges.py`)
- **D-08:** **`tags`는 TF-IDF 입력에서 기본 제외**(현 코드 `with_tags=False` 유지). 설계 문구 "tags 저가중 포함, ③ 미달 시 제거"(`../.claude/rules/data.md` Track B 이웃 절 · 적재 계획 02 §3 content 채널 불릿 · §6 게이트 ③ 조치)를 **코드에 맞춰 Advisor가 갱신**한다. 이웃 텍스트 = `title + description + curator_note`(curator_note 보유 0.4%라 실질 title+description). `--with-tags` 옵션은 남긴다(실험용).
- **D-09:** description 결측 136권(2.6%)·짧은 텍스트 책은 **현 구현대로** category_best(가중 0.2) 보험 + `_top_up`으로 이웃 ≥5만 보장한다. content_sim 최소 cosine 임계는 두지 않는다(근거 없는 상수 금지).
- **D-10:** 게이트 ③(top-20 동일 카테고리 비율 ≤70%) 미달 시 조치는 **description 가중 상향(title 반복 축소)만**. 그래도 미달이면 수치를 기록하고 사용자에게 보고한다 — 동일 카테고리 상한 후처리 같은 새 리랭킹 코드는 만들지 않는다(`../.claude/rules/simplicity.md`).
- **D-11:** **TF-IDF 유지, BM25 기각**(사용자 질문 09-05). 이유: 책↔책 대칭 유사도가 필요(BM25는 질의→문서 비대칭 점수) · MMR·ILD의 `ItemVectors`가 벡터 공간을 요구(BM25는 점수만) · description 400자 클립으로 길이가 균일해 BM25의 길이 정규화 이득이 작음 · sklearn은 기존 의존성(BM25는 새 패키지). PDF P2/P3 "설계만" 항목에 "BM25·문장 임베딩" 1줄.
- **D-12:** `content_vectors_kr.npz`(DATA-07, MMR·ILD용) = **같은 문자 2~4gram TF-IDF 행렬을 `TruncatedSVD` 128차원으로 축소해 L2 정규화한 float32 dense**(5,157×128 ≈ 2.6MB, 재빌드로 9천 권이 돼도 <5MB). 이웃 엣지는 원본 TF-IDF cosine으로, 벡터는 SVD로 — "같은 TF-IDF에서 나온 벡터" 문구 유지. npz에 `book_ids`(int 배열)와 `vectors`를 함께 저장. PDF 각주 1줄("다양성 벡터 = TF-IDF SVD 128").

### 서빙 주입·popularity_kr 범위 (app · serving · data)
- **D-13:** **`artifacts/serving/books_kr.json`이 있으면 `app/server.py`가 `catalog=CatalogKR(...)`·`neighbors=`·`book_stats=`를 주입하고 `pipelines["pop"]`을 Track B 인기(`pop_rank` 순, `user.seen` 제외)로 바꾼다.** Goodbooks `pop` 아티팩트(Phase 2 D-10)는 서버에서 **로드하지 않는다**(평가 전용, `make eval`에서만). 카탈로그가 없으면 Phase 2 동작 그대로(아티팩트·DB·네트워크 없이 기동 원칙). `model_version`은 `pop_v1` 유지, `fallback_level=0`, `rows[0].row_id=="trending"`(Phase 2 D-12 형태 불변). Phase 2 Deferred '서버의 Goodbooks pop 배선 교체'의 이행.
- **D-14:** **`Catalog.eligible()` = `title` 있음 ∧ `image_url` 호스트가 `*.millie.co.kr`(실측 `img.`·`image.`·`cover.` 3종, 400권이 `img.` 외 호스트) ∧ 성인 표지 플레이스홀더(`adult-cover`) 아님.** 평가·인기·난이도 결측은 자격 기준에 넣지 않는다(결측 책은 가드 모집단 제외·UI 미표시일 뿐 노출은 허용, 적재 02 §4). `../.claude/rules/data.md` "표지는 `img.millie.co.kr` 핫링크만" 문구는 `*.millie.co.kr`로 Advisor가 갱신.
- **D-15:** **`popularity_kr`는 `all` 세그먼트(`pop_rank` 순)만 Must**로 만든다. 파일 스키마는 `{book_id, segment, score, rank}` 행 리스트로 세그먼트 필드를 **지금 고정**하고 행은 `segment="all"`만. 연령×성별 12세그먼트(`shelf_count × seg_dist[age][gender]`, seg_dist 보유 83.8%)는 **Should 꼬리**로 같은 스크립트·같은 파일에 증분(DATA-08). fallback level 2 응답 테스트는 Phase 5 `state.py` 이후에만 가능하므로 이 페이즈 완료 기준에 넣지 않는다.

### Advisor 판단 (ROADMAP 착수 전 3 "150줄 초과 파일 분리 여부는 Advisor 판단")
- **D-16:** **`millie_parse.py`(270줄)·`collect_millie.py`(283줄)·`build_millie_catalog.py`(260줄)는 분리하지 않는다.** 셋 다 테스트 통과·배치 사용 중인 dev 전용 스크립트라 분리는 회귀 위험만 있고 PDF에 기여하지 않는다(최소 변경 원칙, CLAUDE.md §2-9). **새 로직은 새 파일로**: 난이도 파생 → `scripts/millie_difficulty.py`(순수 함수, ≤150줄, `build_millie_catalog.py`가 import) · 세그먼트 인기 → `scripts/build_millie_popularity.py`(≤150줄) · SVD 벡터는 `build_millie_edges.py`가 아니라 `export_millie_serving.py` 또는 새 `scripts/export_millie_vectors.py`(export가 150줄을 넘으면 분리). 150줄 규칙 예외 3건은 개발일지 D 항목에 기록.
- **D-17:** **id 부여는 유효 레코드(D-05)에만.** 기존 `id_map.csv` 1,066행(sitemap 1,000 + 초기 발견분)은 껍데기여도 불변(append-only) — id가 있는데 책이 없는 행은 허용. 신규 4,110건 중 유효분만 N+1부터 `discovered_urls.txt` 순서로 부여(기존 `assign_ids`·`test_discovered_urls_are_appended_in_file_order` 유지).

### Claude's Discretion
- **난이도 파생 세부**(`scripts/millie_difficulty.py`): 분야별 `expected_min` 분위 구간 수(권장 4분위, 분야 표본 <20이면 전역 분위), `E[P_완독 | 분야, 분위]` = 그 셀 평균, `resid = P − E`, `resid_z` = 분야 내 z(표본 <5 또는 std=0이면 전역 std), `len_z` = 분야 내 z(expected_min), `difficulty = 1/(1+exp(resid_z))`. 결측(`completion_prob` None)은 `completion_prob := category_avg_prob`·`resid_z := 0`·`len_z`는 expected_min 있으면 계산·`difficulty := None`·`difficulty_source="category_prior"`(적재 02 §4). 분위 수·최소 표본 상수는 모듈 상단.
- **`catalog_kr.py` 위치·구성**: `src/millie_rec/data/catalog_kr.py` ≤150줄, **`artifacts/serving/*.json`·`.npz`를 읽는다**(`data/processed/*.parquet`는 gitignore라 Docker 런타임에 없음). `Catalog.meta()`가 노출하는 필드 = 계약 9개 + `publisher book_format formats pop_rank millie_label review_count shelf_count completion_prob difficulty difficulty_source top_segment subtitle pub_date`; **`description`·`curator_note`·`seg_dist` 원본은 제외**(DATA-06). `popular(categories, n)`은 `pop_rank` 오름차순 + `eligible` 필터. `Neighbors.neighbors(book_id, n)`은 엣지 weight 내림차순. `BookStatsSource.stats()`는 `contracts.BookStats`(source=`difficulty_source`). Track B `ItemVectors`(npz) 구현을 같은 파일에 둘지 `data/vectors_kr.py`로 뺄지는 줄 수로 planner 판단 — Phase 4 `hybrid_div`가 서버에서 쓴다.
- **Track B `pop` Pipeline 구현 위치**: `serving/fallback.py`의 `GlobalPopularFallback(catalog)`(Phase 1 D-10)가 이미 `catalog.popular()` 상위 k를 `ScoredItem(source="popularity")`로 만든다. `name="pop"`으로 쓰는 얇은 래퍼를 `app/pipeline.py`에 두거나(조립 glue) `retrieval/`에 `CatalogPopularity` 공개 함수를 두는지는 planner 판단. `seen` 제외·`k` 상한 100 유지.
- **`demo/fallback/popular.json` 새 스키마**: 백엔드 서빙 01의 fallback 절과 `serving/schemas.py` `RecommendOut` level 3 형태(`rows=[trending]`, items = `popular()` 상위 40, `model_version=MODEL_VERSION_FALLBACK`)를 따른다. 정확한 형태는 planner가 백엔드 01·`demo/js/api.js`의 클라이언트 fallback 읽기 코드로 확인. `artifacts/serving/` export가 `demo/fallback/popular.json`을 갱신하는 것은 소유권 예외로 허용(`../.claude/rules/architecture.md` 산출물 소유권 표).
- **export 세부**: `books_kr.json` 필드 = `meta()` 필드와 동일(`export_millie_serving.py` `BOOK_FIELDS` 갱신), `item_edges_kr.json`은 현 형태 유지, 파일당 <50MB 단언, `description` 0건 grep 단언을 `tests/data/`에 추가. 유사도 행렬은 5,157² dense float32 ≈ 106MB 메모리 — 9천 권 재빌드(≈330MB)까지는 허용, 넘으면 chunked top-k.
- **서버 주입 테스트**: `tests/serving/` 또는 `tests/app/`에 소형 fixture(`tests/fixtures/millie/serving_sample/` 20권 json·npz)로 `create_app(catalog=CatalogKR(fixture))`를 조립해 `/api/recommend?seeds=…&k=5` items ⊂ fixture ids · `fallback_level==0` · `model_version=="pop_v1"` 단정. 실제 `artifacts/serving/`는 테스트가 읽지 않는다.
- **Worker 분할(권장)**: wave 1 = `millie_difficulty.py` + `build_millie_catalog.py` 연결 + 유효 레코드·카운터·게이트 단언 ‖ `build_millie_edges.py` 실행·게이트 3 실측(코드 변경은 게이트 ③ 미달 시에만) → wave 2 = `catalog_kr.py`(+fixture·테스트) ‖ `export` 확장(SVD npz·popularity_kr·popular.json) → wave 3 = Advisor `app/server.py` 주입 + `make millie` 실측 + `make smoke` + `/contract-sync` 카탈로그 항목 + `report/draft.md` P3 1줄. 서로 다른 파일만 만지므로 wave 안 병렬 가능.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 페이즈 범위·요구사항
- `.planning/ROADMAP.md` — Phase 3 '밀리 카탈로그 빌드' Goal·착수 전 4단계·Success Criteria 1~5·Should 꼬리
- `.planning/REQUIREMENTS.md` — DATA-01~08 원문(Must/Should)
- `.planning/phases/02-track-a/02-CONTEXT.md` — D-10(서버 pop 임시 배선)·D-12(level 0 응답 형태)·D-14(ItemVectors 벡터 계약)·Deferred '서버의 Goodbooks pop 배선 교체'
- `.planning/phases/01-local-serving-skeleton/01-CONTEXT.md` — D-02(`trending` 행에 `catalog.popular()`)·D-09(`create_app` 주입 표면 `catalog`·`neighbors`·`book_stats`)·D-10(`GlobalPopularFallback(catalog)`)

### 데이터 설계 정본
- `../.assets/설계서/데이터 소스/02_밀리_데이터_적재_계획.md` — §3 스키마·계약 매핑(컬럼 목록·`ratings_count`·`tags` 호환 전용) · §4 난이도(`resid_z`·`len_z`·σ(−resid_z)·결측 규칙) · §5 별점 결측 · §6 이웃(E-2 채택·게이트 3·행 소스 분리·고정 문장) · §7 수집 스크립트·**커버리지 게이트 표(미달 시 조치)** · §8 버리는 순서 · §9 리스크 · §12 Advisor 검증 절차
- `../.assets/설계서/데이터 소스/03_밀리_데이터_적재_트래킹.md` — §1 단계 표(3 ▶ 진행 → 4·5·6·7 이 페이즈) · §2 수치(재빌드 후 기록) · §4 재실행 방법 · §5 예절 체크
- `../.assets/설계서/데이터 소스/01_한국_도서_데이터_확보_방안.md` §3-2 — 완화 규칙 6개(코드가 그대로 구현)
- `../.claude/rules/data.md` — Track B 스키마·난이도·이웃·스크립트·커버리지 게이트 규칙(D-08·D-14로 문구 2곳 갱신 예정)

### 아키텍처·계약
- `src/millie_rec/contracts.py` — `Catalog`·`Neighbors`·`BookStatsSource`·`ItemVectors` Protocol, `BookStats` DTO(밀리 필드 6개), `FILE_ID_MAP`·`DIR_ARTIFACTS`·`DIR_PROCESSED`, `MODEL_VERSION_FALLBACK`
- `../.assets/설계서/시스템 아키텍처, 기술 스택 및 배포(프론트, 백엔드 서빙)/01_시스템_아키텍처_기술스택_배포.md` §3-3 파이프라인·§8 티어·§9-3 serving 파일 분할
- `../.assets/설계서/백엔드 서빙/01_백엔드_서버_구성.md` — `/api/recommend` 응답·fallback 절(`demo/fallback/popular.json` 형태 확인용)
- `../.claude/rules/architecture.md` — 산출물 소유권 표(`artifacts/serving/`·`demo/fallback/popular.json` 예외), star 의존
- `../.claude/rules/simplicity.md` · `../.claude/rules/python-tdd.md` · `../.claude/rules/local-run.md` — 150줄·TDD Red=AssertionError·`make smoke`

### PDF·설계 주장
- `../.assets/설계서/main 설계서/과제대응전략_최종본(main 설계서).md` §5-6 난이도 feature(★)·§5-7 앵커(★)·§7 노출 자격
- `../.assets/PRD/PRD_메인_추천_시스템.md` §9 수용 기준 표 — '난이도 가드(Should)'·'난이도 4층 피처·ablation'

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `scripts/build_millie_catalog.py`(260줄): `read_records`(status 필터·dedup) · `assign_ids`(append-only, 사전순 + discovered 순) · `_row`(계약 컬럼 매핑, `book_format` 우선순위, `difficulty_source` 판정, `completion_prob` 결측 대체) · `coverage()` → `millie_raw_coverage.json`. **`resid_z`·`len_z`·`difficulty` 컬럼이 없다**(COLUMNS에 미포함) → D-16 새 파일로 추가.
- `scripts/build_millie_edges.py`(152줄): `TfidfVectorizer(analyzer="char_wb", ngram_range=(2,4))` · `build_texts(with_tags=False)` · content top-20 + category_best(0.2) 병합 · `_top_up` ≥5. **게이트 3 충족 로직은 이미 있다.** SVD 벡터 export는 없음.
- `scripts/export_millie_serving.py`(102줄): `books_kr.json`·`item_edges_kr.json`만, `MAX_BYTES` 50MB 검사, `BOOK_FIELDS`로 description 제외. **`content_vectors_kr.npz`·`popularity_kr.json`·`demo/fallback/popular.json` 없음.**
- `tests/data/test_millie_catalog.py`(312줄, 15 tests) · `test_millie_edges.py`(169줄, 11 tests): 합성 픽스처 테스트 + 실데이터 게이트 2개(`test_coverage_gate`·`test_neighbour_quality_gate`, 산출물 없으면 skip). `results/millie_coverage.csv`를 게이트 테스트가 쓴다.
- `tests/fixtures/millie/` 픽스처 8건 + `sample_records.jsonl`.
- `serving/fallback.py` `GlobalPopularFallback(catalog)` — `catalog.popular()` → `ScoredItem(source="popularity")` (Track B pop Pipeline 재료).
- `Makefile` `millie-build`·`millie-edges`·`millie-export`·`millie` 타깃 존재.

### Established Patterns
- data 레인 스크립트는 `scripts/`에 argparse `main()` + 순수 함수, 상수는 모듈 상단, 테스트는 `tests/data/`에서 `importlib`로 스크립트 로드.
- 실데이터 게이트 테스트는 산출물 부재 시 `pytest.skip` — Worker는 산출물 없이도 합성 테스트로 Red/Green 가능.
- `app/server.py`는 "아티팩트 있으면 로드, 없으면 스킵" 패턴(Phase 2 D-10) — 카탈로그 주입도 같은 패턴.

### Integration Points
- `app/server.py`(Advisor 전용): `create_app(pipelines=…, fallback=GlobalPopularFallback(catalog), catalog=…, db=…, neighbors=…, book_stats=…)` — Phase 1 D-09 시그니처 그대로 채움.
- `src/millie_rec/data/__init__.py` `__all__`에 `CatalogKR`(이름 자유) 추가 → `app`은 공개 이름만 import.
- `make smoke`(`seeds=1,2,3&k=5`)는 카탈로그 주입 후 밀리 `book_id` 1·2·3을 seeds로 보고 level 0 — 기대값 변경 없음.
- `/contract-sync` 카탈로그 항목(성공 기준 5) — `artifacts/serving/books_kr.json` 필드가 `serving/schemas.py` 도서 스키마와 맞는지.

### 실측 사실 (2026-09-05 16:00, 배치 진행 중)
| 항목 | 값 |
|---|---|
| `millie_pages.jsonl` | 5,157 고유 millie_id (status 전부 200) |
| `id_map.csv` | 1,066행, 신규 4,110 대기 |
| 배치 | 프론티어 2,482 · ≈6s/권 → 4~7h |
| title 없음 | 6 (껍데기 5 · 파서 미스 1) |
| description 없음 | 136 (2.6%) · curator_note 보유 0.4% · description 평균 341자 |
| 이미지 호스트 | `img.`·`image.`·`cover.millie.co.kr` + `d1miajbjsyro89.cloudfront.net`(성인 표지 플레이스홀더) |
| best_links 보유 | 99.9% (category_best 재료) |
| seg_dist 형태 | `{"10대":{"남":1.4,"여":1.0}, …, "60대~":{…}}` · `top_segment` "40대 여성" |
| millie_label | 마니아 1,728 · 밀리 픽 1,291 · 히든 739 · 홀릭 706 · None 712 |

</code_context>

<specifics>
## Specific Ideas

- **`millie_coverage.csv` 기대 행(첫 빌드)**: `title,1.0000` · `image_url,≥0.999` · `categories,≥0.999` · `completion_prob,≈0.863` · `formats,≈0.988` · `seg_dist,≈0.838` · `_n_records,≈5151` · `_category_distinct,27` · `_categories_ge_20,21` + 신설 `_n_skipped_empty,5` · `_n_skipped_titleless,1`.
- **`popularity_kr.json` 행 예시**: `{"book_id": 812, "segment": "all", "score": 9814.0, "rank": 1}` — 세그먼트 확장 시 `"segment": "40대 여성"` 같은 밀리 표기 그대로(변환 테이블 만들지 않음).
- **`content_vectors_kr.npz`**: `np.savez(path, book_ids=<int64[N]>, vectors=<float32[N,128]>)`, 행 L2 norm ≈ 1.
- **카탈로그 주입 후 `GET /api/recommend?seeds=1,2,3&k=5` 기대**: `model_version="pop_v1"`, `fallback_level=0`, `rows[0].row_id="trending"`, `items[*].book_id ∈ books_kr ∖ {1,2,3}`, `catalog.meta(items)`의 `title`이 한국어 책 제목.
- **PDF 문장 후보(P3 데이터·★난이도)**: "데모 카탈로그는 밀리의서재 공개 도서 페이지 N권(2026-09-0x 수집, 수치·메타·표지 URL만). 난이도는 밀리 완독지수에서 분야·길이 조건부 잔차 `resid_z`로 파생(`σ(−resid_z)`), 완독지수 결측 13.7%는 가드 모집단에서 제외. 이웃은 제목·소개 문자 2~4gram TF-IDF cosine(다양성 벡터는 SVD 128), 협업 필터링 수치와 섞지 않는다." — 숫자는 최종 스냅샷 `results/millie_coverage.csv`로 교체.
- 개발일지 D 항목 2건 예정(Advisor): ① Phase 3 착수 결정(스냅샷 시점·유효 레코드·tags 제외·SVD 벡터·서버 pop 교체·eligible·popularity_kr 범위) ② 150줄 예외 3파일 + BM25 기각.

</specifics>

<deferred>
## Deferred Ideas

- **연령×성별 세그먼트 인기·fallback level 2 검증** → Should 꼬리(D-15). level 2 응답 테스트는 Phase 5 '서빙 Must 완성' `state.py` 이후.
- **`similar_readers` 소스 분리(세그먼트 인기 vs content_sim, 제목 분기)** → Phase 5 `compose.py`(적재 02 §6 행 표).
- **정보나루 coLoan(`co_loan` 엣지) 승격** → Day 3 Should(키·200권 매칭률 ≥40%, 적재 02 §6 E-1). 이 페이즈 무관.
- **쪽수 200권 진단(`pages_diag`·`corr(pages, expected_min)`)** → Day 2 Should(적재 02 §4 C-1). 미측정이면 "시간 제약 폐기"로만 서술.
- **BM25·문장 임베딩 이웃** → 채택하지 않음(D-11). PDF "설계만" 1줄.
- **파서 수정(title 미스 1건)·`millie_parse.py`·`collect_millie.py`·`build_millie_catalog.py` 150줄 분리** → 채택하지 않음(D-05·D-16). 최종 스냅샷 파서 미스 >0.5%면 재검토.
- **content_sim 최소 cosine 임계·동일 카테고리 상한 후처리** → 채택하지 않음(D-09·D-10).
- **형식형 밀리 분류(오디오북·챗북 등) 별도 목록** → 채택하지 않음(D-07). 온보딩 카테고리 선택지 구성은 Phase 6 '데모 재구성' `config/onboarding.json`에서 화면 기준으로 결정.
- **Goodbooks `pop` 아티팩트 서버 로드** → 폐기(D-13). 평가 전용.
- **`Catalog.eligible()`에 난이도 결측·평가 기준 포함** → 채택하지 않음(D-14).
- **배치 계속 두고 Day 3 freeze 직전 재빌드** → 채택하지 않음(D-03). Day 2 오전 중단.

### Reviewed Todos (not folded)
없음 — `todo match-phase 3` 결과 0건.

</deferred>

---

*Phase: 03-millie-catalog*
*Context gathered: 2026-09-05*
