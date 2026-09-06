# Phase 5: 서빙 Must 완성 - Context

**Gathered:** 2026-09-06
**Status:** Ready for planning

<domain>
## Phase Boundary

심사자가 배포 URL에서 눌러볼 **API 표면 전체**가 떠 있는 서버 위에 붙는다 — Must 엔드포인트 9개(`/health` · `GET /api/recommend` · `GET /api/meta/onboarding` · `GET /api/candidates/onboarding` · `POST /api/preferences` · `POST /api/events` · `GET /api/users/{key}/state` · `GET /api/users/{key}/data` · `DELETE /api/users/{key}/personalization`) + `GET /api/showcase` 비교표(Must), SQLite 쓰기(스냅샷 append · 이벤트 품질 게이트 · 추천 로그), `state.py`(user_key 상태) · `nearline.py`(30s ∨ 웨이크 루프 · 24h 리플레이), fallback cascade level 1→2→3, `compose.py` Must 5행 + 배지 + 메타 조인, `bench.py` → `results/latency.json` p95 < 200ms. Should 꼬리는 `after_completion` · `POST /api/ratings` · `GET /api/dashboard` 최소형만(D-13).

**쓰기 영역:** Serving 레인 `src/millie_rec/serving/` + `tests/serving/`만. `app/`·`contracts.py`·`Makefile`은 Advisor. `demo/`는 Phase 6 '데모 재구성'(.planning/ROADMAP.md) 레인 — HTTP 계약으로만 만난다.

**🧊 freeze 안에서 한다(04-CONTEXT D-14):** `serving/schemas*.py` 응답 형태 불변(필드 추가 없음), `retrieval/ranking/reranking` 상단 상수 불변, `contracts.VARIANTS` 4종 불변, `artifacts/serving/*` 스냅샷 불변(`make millie*` 금지). 이 페이즈는 **조립·저장·상태·행 구성**만 새로 만든다.

**PDF 기여(4축 태그):** 축③ 추천 구조 — "Offline/Nearline/Online 경계가 코드로 존재"(요청 핸들러는 적재만, Nearline이 갱신) · 축④/실서비스 — "추천 API 장애 ≠ 메인 장애"(cascade 항상 200) · "p95 200ms 예산이 계층 배치를 결정"(`results/latency.json`이 PDF의 유일한 지연 숫자) · ★앵커 행 · ★시간 가변 가중치가 서버 응답 `user_state_weights`에서 실제로 변한다(D-05~D-08).

</domain>

<decisions>
## Implementation Decisions

### Must 5행 채우기 규칙 (`serving/compose.py` · SERV-01·02·08)
- **D-01 (persona_shelf = 개인화 파이프라인 결과):** "오디세우스의 서가"(`persona_shelf`, discover)는 셀 배정 variant(A→`hybrid`, B→`hybrid_div`, `model=` 쿼리 있으면 그것·`forced`)의 `recommend()` 상위 결과를 **그대로** 담는다. `channel_mix`는 items의 `source_channels` 집계(`content`·`popularity`). 앵커=이웃, trending=인기이므로 **4단계 파이프라인 결과가 화면에 나타나는 유일한 행** — 인스펙터 모델 전환 라디오·α/β/γ 변화가 이 행에서 보인다. 제목은 `"{persona.name}의 서가"`(페르소나는 D-16으로 항상 존재).
- **D-02 (fresh_picks = 선택 카테고리 밖 탐색):** "새로운 발견"(`fresh_picks`, explore)은 파이프라인 결과 중 앞 행에 쓰이지 않은 것 가운데 **최신 스냅샷 카테고리에 속하지 않는 책**. 부족하면 **미선택 카테고리 인기(`catalog.popular([cat])`) 라운드로빈**으로 보충. '탐색'의 정의 = "내 카테고리 밖". 비개인화(level 2·3, D-04)에서는 전 카테고리 라운드로빈.
- **D-03 (앵커 seed₁·행 크기):** `anchor_<seed₁>`의 seed₁ = **최신 스냅샷 `seeds[0]`(선택 순서 첫 책)**. `Neighbors.neighbors(seed₁, 20)` → `Catalog.eligible` → dedup → 상위 **12**. reason `"『{seed 제목}』을 좋아하셨다면"`, subtitle "결이 비슷한 책", items `source="content"`·`source_channels=("content",)`, `channel_mix={"content": n}`. **모든 행 12권**(`ROW_SIZE=12` 상수), `items` = 행 순서 평탄화 상위 `k`(기본 40). 이웃 게이트가 전 도서 이웃 ≥5를 보장하므로 빈 앵커 행은 없다. `continue_reading`은 `state.py`의 session·history 중 `reader_open`(완독 아님) 책 최근순(신규는 빈 행 — 프론트가 숨김).
- **D-04 (dedup·비개인화 행):** 행 간 dedup은 **렌더 순서 앞 행 우선**(`continue_reading → anchor → persona_shelf → trending → fresh_picks`). 기준은 `book_id` **그리고 정규화 제목**(공백·기호 제거·소문자) 동일 — 행 내·행 간 모두, 제거 수를 `dedup_removed`에 합산(Phase 3 인계 '제목 중복(도슨트북 2권)'·04 D72 '판본 중복(『데미안』 2·『싯다르타』 3)' 해소). 익명·`consent=false`·level 2·3 응답의 rows = **`trending` + `fresh_picks`만**(개인화 행 없음 = SERV-08): level 2 `trending` = `catalog.popular(스냅샷 categories)`, level 3 `trending` = `catalog.popular()`; `fresh_picks`는 전 카테고리 라운드로빈(아키 §3-11 "diverse popular"). Phase 1 D-02의 "trending 1행"은 이 규칙으로 대체된다(compose가 행 순서 정본).
- **(문서 확정, 재확인)** 배지 6종 규칙은 `../.claude/rules/serving.md` 그대로: 배지 타입 = 최신 스냅샷 `criterion`(S3 기준), `bestseller` 근거 `pop_rank`("인기 N위"), `review` 3단 폴백(`average_rating`+`review_count≥3` → "★4.2 · 리뷰 128" / 별점 결측·`review_count≥10` → "리뷰 128" / 그 외 `bestseller`), `author`·`publisher`는 seeds와 일치할 때만, `buzz`=`millie_label`, `light`는 Should(이 페이즈 미구현 → 배지 생략). 모든 행 items에 `catalog.meta` 5필드(제목·저자·표지·포맷·난이도) 조인 — Phase 3 인계 '익명 level 3 items title None' 해소.

### user_key 상태 모델 (`serving/state.py` · `serving/nearline.py` · SERV-04·07·09)
- **D-05 (history = 읽기 행동만):** 서버 `UserState.history`(β 성분) = `reader_open`·`qualified_read`·`completion` 이벤트의 책(distinct, 최근순). `library_add`(서재 담기)와 seeds 자동 기록은 **넣지 않는다** — seeds는 `explicit_seeds` 성분이고, 담았지만 안 읽은 책은 읽은 책이 아니다. 신규는 history 비어 β=0(REC-03 그대로). 뷰어 시뮬레이션 화면(`#/reader/:id`, ../.assets/설계서/화면 구성 및 디자인/02_화면구성_v2_8페이지.md §2)에서 '읽기'를 누르면 β가 커지는 것이 다음 응답에서 보인다.
- **D-06 (session·session_active):** `UserState.session`(γ 성분) = **최근 30분**(`SESSION_WINDOW_S = 1800`, 모듈 상단 상수) 내 `reader_open`·`detail_click` 책. 창 안에 이벤트 1개 이상이면 `state_weights(user, session_active=True)` → γ +0.1(04-CONTEXT D-02 인자 적용).
- **D-07 (n_completed·user_level):** `n_completed` = `completion` distinct 책 수 — `reranking/guard.py`·`ranking/hybrid.py`의 `len(user.history)` 대리값을 **서버에서는** 이 값으로 교체한다. 교체 방법은 Claude 재량(아래) — 상수·시그니처 freeze 안에서. `user_level` = 완독 책 `difficulty` 평균(결측 제외), 완독 0권이면 **최신 스냅샷 카테고리의 카탈로그 평균 `difficulty`**(04-CONTEXT D-06 "선택 카테고리 prior" 이행). `BookStatsSource.user_level()`을 만족하는 서빙 측 어댑터가 `CatalogKR`을 감싼다(`app/`이 주입).
- **D-08 (저장·리플레이·부스트):** `state.py`가 메모리 dict(`user_key → history · session · n_completed · last_event_ts`)를 들고 **Nearline만 쓴다**(요청 핸들러는 `events` INSERT + `asyncio.Event.set()`만 = SERV-09 경계 증거). 기동 시 `events` 중 `ts ≥ now − 24h` **리플레이**(아키 §3-5). 스냅샷·`users` 행은 이벤트가 아니므로 요청 시 DB 직접 조회. `reset_boost = True` 조건 = **최신 스냅샷이 2번째 이상(`snapshots_count ≥ 2`) ∧ `created_at`이 24h 이내**(취향 재설정 화면(`#/refresh`) 완료 → α +0.15). `DELETE …/personalization`은 메모리 상태·캐시도 함께 제거.
- **(문서 확정, 재확인)** `POST /api/preferences`: 스냅샷 append(`restart=true`도 새 `snap_<6hex>`, 삭제 없음), `users` 행 없으면 생성 — `cell = "A" if int(hashlib.sha256(user_key.encode()).hexdigest()[:8], 16) % 2 == 0 else "B"`(CPython `hash()` 금지), `consent` 저장, seeds마다 `library_add(surface="onboarding")` 이벤트 자동 기록, `consent=false`면 seeds 미저장·스냅샷만 표식. `GET /api/recommend`: `user_key` 있고 스냅샷 있고 `consent=true`면 level 0 경로(`snapshot_id` 없으면 최신), 스냅샷 없음·`consent=false`·익명은 level 3. `DELETE`는 `preference_snapshots`·`events`·`ratings`·`recommendations` 행 삭제 + `users.consent=false`(행 유지) → 이후 항상 level 3.

### fallback cascade · latency_breakdown · bench (`serving/fallback.py` · `api.py` · `bench.py` · SERV-03·06·10)
- **D-09 (breakdown 키):** `api.py`가 세 구간을 `perf_counter`로 잰다 — `feature`(state·스냅샷 로드) · `pipeline`(`recommend()` 호출) · `compose`(행 구성·메타·배지·로그) + `total`. **파이프라인 객체가 옵션 속성 `last_breakdown: dict[str, float]`(`retrieval`·`ranking`·`rerank`)을 가지면 `getattr`로 읽어 `pipeline` 대신 세분 키로 병합**한다. `contracts.Pipeline` Protocol 무변경, 가짜 Pipeline도 그대로 동작. `StagedPipeline`에 `last_breakdown` 기록을 추가하는 것은 `app/pipeline.py` = **Advisor 몫**(상수·로직 무변경, 타이밍만).
- **D-10 (예산 판정·level 1 캐시):** `recommend()` 반환 시점에 `feature + pipeline` 누적 > `contracts.BUDGET_MS`(200) **또는 예외** → 결과를 버리고 level 1(스레드 중단·타임아웃 없음 — 단순). 캐시 = **직전 level 0 rows**, 키 `(user_key, snapshot_id, variant)`, TTL `contracts.CACHE_TTL_S`(600). **매 level 0 성공 시 저장, fallback 경로에서만 읽는다**(정상 경로는 항상 계산 → bench가 캐시를 우회할 필요 없음). 캐시 응답도 새 `recommendation_id`·`fallback_level=1`·`model_version`은 캐시된 것. 캐시 미스 → level 2(`catalog.popular(스냅샷 categories)`) → 3. 새 스냅샷·`DELETE`·완독(Should) 시 해당 user_key 캐시 무효화. **테스트 주입** = `time.sleep`하는 가짜 Pipeline + `BUDGET_MS` monkeypatch(예산), 예외 던지는 가짜 Pipeline(예외), 캐시 있음/없음 두 경우로 1→2→3 단계 확인.
- **D-11 (bench 모집단 = PDF p95의 정의):** `bench.py`가 서버(`make serve`, 1 worker)에 **`POST /api/preferences`로 user_key 50개를 먼저 만들고**(카탈로그 eligible 무작위 5권 seeds, `contracts.SEED` 고정), warmup 50 후 **500 요청을 user_key 라운드로빈**, `model` 미지정(셀 배정), `k=40`. `results/latency.json` = `p50/p95/p99` + `fallback_level` 분포 + `variant`(model_version) 분포 + 카탈로그 규모 + `created_at`·`git_sha`. 게이트 p95 < 200은 전체 응답 기준. 실제 경로(state 로드·스냅샷 조회·compose 5행·추천 로그 INSERT)를 재므로 "Must 서빙 p95"라 부를 수 있다. `Makefile bench` 타깃은 이미 `python -m millie_rec.serving.bench`를 가리킨다.
- **D-12 (추천 로그 범위):** **모든 응답**(level 0~3, `seeds` 쿼리·익명 포함)을 응답 직전 `recommendations`에 1회 INSERT — 노출 로그 4필드(`recommendation_id·model_version·row_id·position`)의 단일 소스, fallback 발생율·variant 분포가 대시보드에 사용 가능. `rows` JSON은 **`row_id·book_id·position`만 축약**, `weights`·`latency_breakdown`은 그대로 JSON.
- **(문서 확정, 재확인)** `POST /api/events` 품질 게이트 순서: pydantic → `event_id` 중복은 무시하고 `duplicates` 집계 → `ts` 검사(미래 +5분 `ts_future`, 유저 마지막 이벤트보다 1h 이상 과거 `ts_backdated`) → `book_id`가 `Catalog.eligible`에 없으면 `book_ineligible` → INSERT(플래그 붙어도 저장) → `asyncio.Event.set()`. 응답 `202 EventsAccepted`. 단건 객체·`{events:[…]}` 배치(≤50) 모두 허용.

### Should 꼬리 범위 · 온보딩 메타 원천 (SERV-05·11·12·13·14)
- **D-13 (Should 포함 범위):** **`after_completion` + `POST /api/ratings` + `GET /api/dashboard` 최소형**을 마지막 wave로 plan에 포함한다(Phase 6 DEMO-07·08의 전제). dashboard 최소형 = `kpi` 6개(`qualified_reading_start_rate`·`first_completion_rate_new`·`fallback_rate`·`p95_latency_ms`·`error_rate`·`active_user_keys`, 전부 `n` 병기) · `events_recent` 50 · `latency` 링버퍼(p50/p95/p99, `by_stage`는 D-09 키) · `by_variant` · `by_hour` · `quality`(`impression_receipt_rate`·`flagged_events`·`feature_freshness_s`); `ab_table`은 셀×신규/기존 집계만, `mde_note`는 고정 문장. **`GET /metrics`·`book_stats.py` 24h 집계는 이 페이즈에서 "설계만"** — `prometheus-client` 의존성 추가하지 않음, Phase 7 '배포'(.planning/ROADMAP.md) DEPLOY-04 Grafana scrape도 자연 폐기(버리는 순서 최하위, 결정 '버리는 순서 = 아키 §8 표'(개발일지 2026-09-04 파일 항목 D40)). `after_completion`은 Nearline이 `completion` 이벤트 시 `Neighbors.neighbors(book, 20)`로 사전 계산해 `state.py`에 저장 → 다음 응답 **최상단** 행 "『X』을 완독하셨네요, 다음은"(`source=content`), 새 완독이 덮어씀. `ratings` = `ratings` INSERT + `rating` 이벤트 자동 기록(모델 라벨 미사용). 시간 부족 시 이 wave만 통째로 버린다.
- **D-14 (온보딩 메타 원천):** `serving/onboarding_meta.json` **1벌**(아키 §9-3 목록의 파일) = `survey_variant="v1"` · `reading_times` 5 · `criteria` 5(`id` = 배지 타입 `author publisher bestseller buzz review`, 라벨은 화면 텍스트) · 카테고리별 `subcategories` 정적 목록(../.assets/설계서/화면 구성 및 디자인/01_기술스택_및_화면설계.md §4-2). **`categories`는 카탈로그에서 계산**: 밀리 분류 전부(형식형 포함, 03-CONTEXT D-07), `supported = eligible 도서 20권 이상`. `demo/config/onboarding.json`과의 텍스트 동일성은 `/contract-sync`가 검사(Phase 6에서 항목 추가) — 각 레인이 서로의 폴더를 읽지 않는다는 규칙 유지.
- **D-15 (후보 30권 배분):** `GET /api/candidates/onboarding` = 선택 카테고리(≤3) **라운드로빈** — 각 카테고리 `catalog.popular([cat])`(`pop_rank` 순)에서 1권씩 돌아가며 `n`(기본 30, ≤60)까지, `eligible` 필터, 카테고리 간 중복 제거. 지배 분야(소설)가 30권을 독식하지 않아 사용자가 세 분야 모두에서 5권을 고를 수 있다. `subcategories`는 카탈로그에 없으므로 **필터에 쓰지 않고 스냅샷에 저장만**. `candidate_set_id = "cand_" + 6hex`, `candidate_sets` INSERT(`survey_variant="v1"`).
- **D-16 (페르소나 매핑):** `serving/persona.py` 상단 **매핑 표(밀리 분류명 → 4종)** — 오디세우스《오디세이아》(경제경영·자기계발·IT 계열) · 셜록 홈즈《주홍색 연구》(추리·과학·철학 계열) · 돈키호테《돈키호테》(인문·역사·사회 계열) · 제인 에어《제인 에어》(에세이·라이프스타일 계열). 실제 밀리 분류명은 Worker가 `artifacts/serving/books_kr.json`의 카테고리 목록을 보고 채운다. **미매핑 카테고리는 첫 카테고리 이름의 sha256으로 4종 중 결정적 선택**(항상 페르소나 존재 → 취향 설정 S6·`persona_shelf` 제목이 비지 않음). `description`은 실제 선택값 삽입: "회원님은 {카테고리 1·2}를 즐기고, {기준 라벨}으로 책을 고르는 독서가입니다." 지배 카테고리 = 스냅샷 `categories[0]`.

### 검증·완료 형태 (모든 브리프 공통)
- **D-17:** 슬라이스별 3종 테스트(계약·정확성·안전성, `../.claude/rules/python-tdd.md`, Red = `AssertionError`), 전부 `tmp_path` SQLite·가짜 Pipeline·20권 fixture(`tests/fixtures/millie/serving_sample/`)로 Model 레인과 독립. 필수 항목: compose — 5행 순서·`row_id` 집합·앵커 `source=content`·reason 문자열·dedup(book_id·제목)·level 3 rows 2행 / state — history 이벤트 종류·30분 창·`n_completed`·`user_level` 카테고리 prior·`reset_boost` 조건·24h 리플레이 / fallback — 예산 초과→1(캐시 有)·→2(캐시 無)·예외→항상 200·`consent=false`→3 / demo_api — 스냅샷 2개 append·`cell` sha256 결정적·`library_add` 자동·events dedup·`quality_flag` 3종·후보 라운드로빈·`candidate_set_id` 발급 / privacy_api — `state` 스키마·`data` 열람·`DELETE` 후 level 3·404 / dashboard_api — `ShowcaseOut` 파싱·`eval_table.json` 그대로·`data_notice` 2트랙 문장. `tests/test_architecture.py`는 고치지 않는다.
- **D-18:** 완료 = `uv run ruff format . && uv run ruff check . && uv run pytest --no-header`(기준선 327 passed 위에 증가) + **매 브리프 후 `make smoke`** + Advisor 실측 `make serve` → `make bench` → `results/latency.json` p95 < 200 → `report/draft.md` P4 실서비스 문장 1줄 + `/docs` 캡처. **Codex 리뷰 필수**(`../.claude/rules/codex-review.md` 표): `privacy_api.py`(동의 철회·열람) · `db.py` 쓰기 헬퍼 → `/codex:review --scope working-tree` + `/codex:adversarial-review`. `contracts.py` 무변경이면 나머지는 선택. 커밋은 사용자 승인 후(Phase 1~4 산출물과 일괄).

### Claude's Discretion
- **`api.py` 150줄 유지 방법**: 현재 150줄. `create_app`·`/health`·`/api/recommend` 시그니처는 유지하고 user_key 경로·cascade 오케스트레이션은 `fallback.py`(cascade 책임) 또는 새 파일로 뺀다. 새 라우터는 `APIRouter`로 `demo_api.py`·`privacy_api.py`·`dashboard_api.py`에 두고 `create_app`이 `include_router`. 아키 §9-3 목록 외 파일이 필요하면 이름을 정해 브리프에 적고 PROGRESS에 1줄.
- **`n_completed` 대리값 교체 방식**(D-07): guard·hybrid는 `len(user.history)`를 읽는다. 서빙에서 `UserState.history`가 D-05 정의(읽기 행동)라 완독 수와 다르다. 선택지 — (a) `state.py`가 완독 책을 history 앞에 두고 guard 임계 3을 그대로 두어 "history ≥3 = 완독 ≥3"으로 근사, (b) `DifficultyGuard(min_completed=…)` 생성 인자를 `app/`이 상태에 따라 넘김(불가 — 파이프라인은 요청 전 조립). **planner가 (c) `UserState.context["n_completed"]`(dict 필드, 계약 무변경)를 읽는 분기를 guard·hybrid에 1줄 추가하는 안을 검토** — 상수 무변경이라 freeze 안이지만 Model 레인 파일이므로 Advisor 승인 + 개발일지 1줄.
- `/health` 채우기: `model_version` = 기본 variant 버전(`hybrid_div_v1`), `artifacts_loaded_at` = 기동 시각 ISO, `nearline_last_run` = 마지막 루프 시각.
- `seeds` 쿼리와 `user_key`가 함께 오면 `user_key` 우선(seeds는 CLI·bench·cold-start 전용). `snapshot_id`가 그 user_key 것이 아니면 404.
- 세션 만료·history 상한(예: 최근 200권)·리플레이 배치 크기·Nearline 루프 예외 처리(로그 후 계속)·`impression`의 `selected` 채우기(같은 `candidate_set_id`·`book_id`의 `preference_book_selected`).
- `UserStateOut.library` 3분류: `added` = `library_add` 책, `reading` = `reader_open` 있고 `completion` 없음, `completed` = `completion`.
- `GET /api/showcase`: `eval_table` = `artifacts/serving/eval_table.json` 그대로(02-CONTEXT D-09 형태, `p95_ms`는 `results/latency.json` 있으면 병기), `philosophy`·`metric_mapping`·`memorable_5`·`roadmap`·`data_notice`는 모듈 상단 상수(문장은 ../.assets/설계서/백엔드 서빙/01_백엔드_서버_구성.md §13·`../.claude/rules/serving.md` 고지 문장), `personal_case`는 `report/demo_5books.md`가 아니라 SEEDS 상수 5권으로 서버가 계산(Should, 시간 있으면).
- `db.py` 쓰기 헬퍼 형태(`execute`/`executemany` 래퍼, `con.backup()`), thread-local 커넥션 `close()`·lifespan shutdown 훅(01-CONTEXT Deferred). 인덱스 `events(user_key, ts)`·`recommendations(user_key, ts)` 추가는 `schema.sql`에 `CREATE INDEX IF NOT EXISTS`로(DDL 추가는 허용, 컬럼 변경 없음).
- 배치·SQLite 동시성: Nearline은 `asyncio.to_thread`에서 자기 스레드 커넥션 사용, WAL로 읽기·쓰기 병행.
- **Worker 분할(권장, 최종은 planner):** wave 1(서로 다른 파일, 병렬) = `state.py`+`nearline.py` ‖ `compose.py`(5행·dedup·배지·메타 조인) ‖ `fallback.py` level 1·2 + `db.py` 쓰기 헬퍼 ‖ `persona.py`+`onboarding_meta.json`+`demo_api.py`(meta·candidates·preferences·events) ‖ `privacy_api.py` → wave 2 = `api.py` 통합(user_key 경로·cell·breakdown·추천 로그)+`dashboard_api.py`(showcase Must) + Advisor `app/`(create_app `state` 인자 채움·`StagedPipeline.last_breakdown`·`BookStatsSource` 서빙 어댑터 주입) + `bench.py` → wave 3 = Advisor `make bench` 실측·draft P4·`/docs` 캡처·Codex 리뷰 → wave 4(Should) = `after_completion`(compose+nearline)·`ratings`(demo_api)·`dashboard`(dashboard_api).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### HTTP 계약·응답 형태 (freeze — 변경 금지)
- `../.assets/설계서/백엔드 서빙/01_백엔드_서버_구성.md` §0 공통 규약(ID 형식·오류·크기) · §1~§10 Must 엔드포인트 JSON · §13 showcase · §15 이벤트 스키마 대응 — **요청/응답 JSON의 정본**
- `src/millie_rec/serving/schemas.py`(Must §1~§10 pydantic) · `src/millie_rec/serving/schemas_should.py`(§11 dashboard·§13 showcase) — 코드 정본, 라운드트립 테스트 `tests/serving/test_schemas.py`
- `src/millie_rec/contracts.py` — `ROW_IDS`·`ROW_ANCHOR_PREFIX`·`BADGE_TYPES`·`EVENT_TYPES`·`BUDGET_MS`·`FALLBACK_*`·`CACHE_TTL_S`·`NEARLINE_INTERVAL_S`·`MIN_EVENTS_FOR_BOOK_STATS`·DTO(`Row`·`ScoredItem`·`RecommendResponse`·`PreferenceSnapshot`·`Persona`·`Event`)·Protocol(`Catalog`·`Neighbors`·`BookStatsSource`·`Pipeline`)

### 아키텍처·서빙 규칙
- `../.assets/설계서/시스템 아키텍처, 기술 스택 및 배포(프론트, 백엔드 서빙)/01_시스템_아키텍처_기술스택_배포.md` §3-2 API 계층(엔드포인트↔파일 표) · §3-3 추천 파이프라인(셀 배정·compose 행 정의) · §3-4 SQLite · §3-5 Nearline 루프 · §3-8 개인정보·보안 · §3-9 품질 게이트 · §3-10 A/B 배정(sha256) · §3-11 fallback cascade·이벤트 루프 규칙 · §8 범위 티어 · §9-3 serving 파일 분할(각 ≤150줄)
- `../.claude/rules/serving.md` — 위 문서의 요약 + 배지 6종 규칙 + `create_app` 시그니처 + 테스트 목록 + 2트랙 고지 문장
- `../.claude/rules/architecture.md` — star 의존(serving은 `contracts`만 import), 산출물 소유권(`$DATA_DIR/millie.db`는 `serving/db.py`로만, `demo/`는 읽지 않음), Advisor 전용 파일
- `../.claude/rules/local-run.md` — 매 브리프 `make smoke`, 아티팩트·네트워크 없이 기동
- `../.claude/rules/simplicity.md` · `../.claude/rules/python-tdd.md` · `../.claude/rules/codex-review.md`(privacy·db 필수 리뷰) · `../.claude/rules/references.md`
- `../.claude/rules/data.md` — 데모 이웃 = 콘텐츠 유사도(`source_channels=("content",)`, `itemknn` 표기 금지), 표지 핫링크·텍스트 미노출

### 화면·이벤트 매핑 (서버 효과의 정본)
- `../.assets/설계서/화면 구성 및 디자인/02_화면구성_v2_8페이지.md` §2 메인 화면(`#/home`) 행 표·내 서재 화면(`#/library`)·취향 재설정 화면(`#/refresh`) · §5 UI 행동 → 이벤트 → 서버 효과 표(13종 1:1)
- `../.assets/설계서/화면 구성 및 디자인/01_기술스택_및_화면설계.md` §4-2 온보딩 JSON 정본(reading_times·criteria·subcategories 텍스트) · §4-4 배지 개인화 · §4-5 페르소나 4종 규칙
- `demo/config/onboarding.json` — 화면 텍스트 정본(서버는 읽지 않음, `serving/onboarding_meta.json`과 동일성은 `/contract-sync`)

### 설계 근거·수용 기준
- `../.assets/설계서/main 설계서/과제대응전략_최종본(main 설계서).md` §5-1 4단계 파이프라인·[4] Page Composition · §5-2 ★시간 가변 가중치 · §5-3 취향 재설정 = 스냅샷 append · §5-6 난이도 가드 · §5-7 앵커 · §7 실서비스 제약(개인정보·품질·응답 지연)
- `../.assets/PRD/PRD_메인_추천_시스템.md` §9 수용 기준 표 — '온보딩 5권 → 앵커 row' · '재설정 → 새 앵커·기록 보존' · '건너뛰기 → 비개인화 row만' · '동의 철회 → 비개인화 fallback' · '파이프라인 예외 → 인기 row 200' · '노출 로그 4필드' · '로컬 p95 < 200ms' · '완독 → 완독하셨네요 row(Should)'
- `../.assets/설계서/데이터 소스/02_밀리_데이터_적재_계획.md` §5 별점 결측(review 배지 3단 폴백) · §6 이웃·행 표(`similar_readers` 소스 분기)
- `.planning/REQUIREMENTS.md` SERV-01~14 · `.planning/ROADMAP.md` Phase 5 절(Success Criteria 5개)

### 앞 페이즈 결정 (이 페이즈가 이행·대체하는 항목)
- `.planning/phases/01-local-serving-skeleton/01-CONTEXT.md` — D-02(trending 1행 → D-04로 대체) · D-03(rec_id 발급) · D-05(7테이블 DDL) · D-06(행 쓰기는 Phase 5) · D-08(SQLite 연결) · D-09(`create_app` 시그니처) · D-10(level 1·2는 `fallback.py` 증분) · Deferred `db.py close()`
- `.planning/phases/02-track-a/02-CONTEXT.md` — D-09(`eval_table.json` 형태) · D-11(기본 variant 임시 규칙 → 셀 배정으로 대체) · D-12(level 0 형태) · D-13(익명 level 3)
- `.planning/phases/03-millie-catalog/03-CONTEXT.md` — D-13(CatalogKR 주입) · D-14(`eligible`) · D-15(`popularity_kr` all 세그먼트 → level 2는 `catalog.popular(categories)`) · Deferred(제목 중복·`similar_readers` 소스 분리)
- `.planning/phases/04-freeze/04-CONTEXT.md` — D-02(`state_weights` 부스트 인자) · D-06(`user_level` 카테고리 prior) · D-08(`n_completed` 대리값 교체) · D-09(`weights` 배선) · D-14(🧊 freeze 4종)
- 개발일지 `../.assets/개발일지/` — 결정 '버리는 순서 = 아키 §8 표'(2026-09-04 파일 항목 D40) · '두 계약 Day 1 freeze'(항목 D44) · '로컬 DB = sqlite3 표준 라이브러리'(항목 D19) · freeze 선언(2026-09-06 파일 항목 D72) · 이 페이즈 논의 결정(2026-09-06 파일 항목 D73)

### 배포 연계(참고)
- `../.assets/설계서/시스템 아키텍처, 기술 스택 및 배포(프론트, 백엔드 서빙)/02_배포_절차_및_설정.md` §3-2 볼륨 영구성 확인(`/health.db_row_count`) · §4 본배포 선행 조건

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `serving/api.py`(150줄, 한도 도달): `create_app(pipelines, fallback, *, catalog, db, neighbors, book_stats, state, weights)` — `state=None` 인자가 비어 있어 `state.py` 객체를 받을 자리가 이미 있다. `_personalized_response`(level 0, 예외→3)·`_fallback_response`·`_parse_seeds`·`_422` 재사용. `K_DEFAULT=40, K_MAX=100`.
- `serving/compose.py`(60줄): `build_response(items, *, model_version, level, k, t0, context)`·`new_rec_id()`·`default_variant()`·`ZERO_WEIGHTS` — 5행 조립으로 확장(Phase 2 D-12 형태를 대체).
- `serving/fallback.py`(45줄): `GlobalPopularFallback(catalog)`(`contracts.Pipeline`)·`trending_row()`·상수 `TRENDING_*`·`SOURCE_POPULARITY` — level 1·2 cascade를 같은 파일에 증분.
- `serving/db.py`(60줄): `Database(path)` thread-local 연결·`apply_schema()`·`row_counts()`·`ok()`·`resolve_db_path()` — 쓰기 헬퍼 추가.
- `serving/schema.sql`: Must 4 + Should 3 테이블 DDL 완료(컬럼명 = 백엔드 §3-4 그대로). `preference_snapshots.persona` JSON, `events.quality_flag`, `recommendations.rows` JSON 이미 존재.
- `data/catalog_kr.py` `CatalogKR`: `meta()`(계약 9 + 밀리 필드 `publisher book_format pop_rank millie_label review_count shelf_count completion_prob difficulty difficulty_source top_segment …`, `description` 없음) · `popular(categories, n)`(`pop_rank` 순 + eligible) · `eligible()` · `neighbors(book_id, n)`(weight 내림차순) · `stats()` · `user_level()`(현재 None) — 한 객체가 `Catalog`·`Neighbors`·`BookStatsSource` 세 Protocol 만족, `app/server.py`가 이미 주입.
- `ranking.state_weights(user, *, reset_boost=False, session_active=False) -> dict` — D-06·D-08 부스트 인자 그대로 사용. `app/server.py`가 `weights=state_weights`로 이미 주입.
- `app/pipeline_kr.py`: `WithMeta` 데코레이터가 파이프라인 items에 `catalog.meta` 5필드를 조인 — compose는 이미 조인된 items를 받되 fallback·앵커·후보 items는 compose가 직접 `catalog.meta` 조인. `StagedPipeline.recommend()`가 채널별 `retrieve → blend_channels → rerankers` 순서라 `last_breakdown`(D-09) 기록 지점이 명확.
- `artifacts/serving/`: `books_kr.json` 9,447권 · `item_edges_kr.json` · `content_vectors_kr.npz` · `popularity_kr.json`(all) · `eval_table.json`(4행) — 🧊 최종 스냅샷, 읽기만.
- `tests/serving/test_smoke.py`·`test_recommend_level0.py`·`test_api_weights.py` — 가짜 Pipeline·`tmp_path` DB로 `create_app`을 직접 조립하는 패턴(그대로 따른다). `tests/fixtures/millie/serving_sample/` 20권 fixture.
- `Makefile`: `bench` 타깃(`python -m millie_rec.serving.bench`)·`smoke`(8010 포트 3점)·`serve` 존재. `bench.py`는 아직 없음.

### Established Patterns
- 핸들러는 전부 동기 `def`(스레드풀), Nearline만 `async` + `asyncio.to_thread`, `uvicorn --workers 1`.
- 상수는 모듈 상단 대문자, 설정 프레임워크 없음, 환경변수 해석은 `db.py`·`app/server.py`의 `os.environ.get`만.
- 예외는 로그 후 강하(500·예외 문자열 노출 없음). `log.exception` 사용.
- 새 공개 이름은 `serving/__init__.py` `__all__`에 추가(현재 `API_VERSION Database EventIn GlobalPopularFallback RecommendOut create_app resolve_db_path`).
- 파일 ≤150줄(`schemas.py` 예외). `api.py`가 이미 150줄이므로 새 엔드포인트는 반드시 별도 파일.
- ID 규약: `rec_<6hex>`(있음) · `snap_<6hex>` · `cand_<6hex>` · `rat_<6hex>` = `uuid.uuid4().hex[:6]`.

### Integration Points
- `create_app(..., state=<StateStore>)` — `app/server.py`가 `state.py` 객체와 `BookStatsSource` 서빙 어댑터(D-07 `user_level`)를 주입(Advisor).
- lifespan: 스키마 적용(있음) → 24h 리플레이 → Nearline 태스크 시작 → shutdown 시 태스크 취소(01 Deferred `close()` 재검토).
- `POST /api/events` → `db` INSERT → `asyncio.Event.set()` → `nearline.py` 루프 → `state.py` dict 갱신 → 다음 `GET /api/recommend`가 읽음.
- `GET /api/showcase` ← `artifacts/serving/eval_table.json`(02 D-09 형태) + `results/latency.json`(D-11, 있으면).
- Phase 6 데모는 `?source=api`로 이 엔드포인트들을 호출 — 응답 형태는 mock(`make mock`, `schemas.py` 기준)과 동일해야 하며 `/contract-sync`가 검사.

</code_context>

<specifics>
## Specific Ideas

- "4단계 파이프라인 결과가 화면에 나타나는 유일한 행이 `persona_shelf`" — 인스펙터 모델 전환 라디오로 이 행의 책이 바뀌는 것이 Phase 7 DEPLOY-02 완주 기준("variant 전환 시 책이 바뀐다")의 실체다.
- bench는 "Must 서빙 p95"여야 한다 — state 로드·스냅샷 조회·5행 compose·추천 로그 쓰기를 전부 포함한 실제 경로(D-11). seeds cold-start 경로 숫자를 PDF에 쓰지 않는다.
- 페르소나는 항상 존재한다(D-16) — 화면 S6과 `persona_shelf` 제목이 비는 경우를 만들지 않는다.
- Nearline 경계는 코드 증거다 — 요청 핸들러 어디에도 `state` dict 쓰기가 없어야 한다(테스트로 단정 가능: `POST /api/events` 직후 상태 미변경, 루프 1회 후 변경).

</specifics>

<deferred>
## Deferred Ideas

- **`GET /metrics`(Bearer, prometheus-client)·`book_stats.py` 24h 집계·`FREEZE_BOOK_STATS`** → 설계만(D-13). PDF "설계만 — 관측" 1줄. `prometheus-client`·`sentry-sdk` 의존성 미추가. Phase 7 DEPLOY-04 Grafana scrape 자연 폐기.
- **`GET /api/admin/export`(Could)** → 안 함.
- **`similar_readers`·`anchor_<seed₂>`·`light_start` Should 행** → 이 페이즈에 넣지 않음(버리는 순서상 `after_completion`보다 아래, 04-CONTEXT·03-CONTEXT Deferred 유지). `light` 배지도 함께.
- **`personal_case`(showcase 5권)** → Should, wave 4에 시간 남으면(SEEDS 상수 1012,2765,1446,1222,2292).
- **`ab_table` 층화 집계·MDE 계산** → 고정 문장(D-13). 검정 없음.
- **세그먼트(연령×성별) 인기 level 2** → `popularity_kr` all만 Must(03 D-15). level 2는 스냅샷 카테고리 인기.
- **`UserState.context`에 `n_completed` 넣는 분기(Model 레인 1줄)** → Claude 재량 항목, planner가 채택 여부 결정 후 Advisor 승인.
- **CORS** → 없음(01 D-11 유지).
- **`contracts.Pipeline`에 `breakdown()` 메서드 추가** → 채택하지 않음(D-09 duck-typed 속성).
- **타임아웃 스레드 강제 중단·단계별 중간 예산 판정** → 채택하지 않음(D-10).
- **history에 `library_add` 포함** → 채택하지 않음(D-05).
- **서버가 `demo/config/onboarding.json` 직접 읽기** → 채택하지 않음(D-14).
- **전체 events 리플레이** → 채택하지 않음(D-08, 24h).

### Reviewed Todos (not folded)
없음 — `todo match-phase 5` 결과 0건.

</deferred>

---

*Phase: 05-must*
*Context gathered: 2026-09-06*
