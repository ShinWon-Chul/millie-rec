---
phase: 06-demo-rebuild
plan: 01
subsystem: Demo (mock 생성기)
tags: [demo, mock, generator, tdd, contract]
requires:
  - artifacts/serving/books_kr.json
  - artifacts/serving/item_edges_kr.json
  - artifacts/serving/eval_table.json
  - results/latency.json
  - demo/config/onboarding.json
  - src/millie_rec/serving/schemas.py
  - src/millie_rec/serving/schemas_should.py
provides:
  - demo/mock/catalog_kr.json
  - demo/mock/neighbors_kr.json
  - demo/mock/meta_onboarding.json
  - demo/mock/candidates_onboarding.json
  - demo/mock/preferences_response.json
  - demo/mock/recommend_pop.json
  - demo/mock/recommend_cf.json
  - demo/mock/recommend_hybrid.json
  - demo/mock/recommend_hybrid_div.json
  - demo/mock/state.json
  - demo/mock/dashboard.json
  - demo/mock/showcase.json
  - demo/mock/_manifest.json
affects: [06-02, 06-03, 06-04, 06-05, 06-06]
tech-stack:
  added: []
  patterns: [표준 라이브러리 전용 생성기, 화이트리스트 직렬화, 결정적 빌드(_manifest md5)]
key-files:
  created:
    - tests/demo/test_make_mock.py
    - demo/mock/catalog_kr.json
    - demo/mock/neighbors_kr.json
    - demo/mock/candidates_onboarding.json
    - demo/mock/state.json
    - demo/mock/dashboard.json
    - demo/mock/showcase.json
    - demo/mock/_manifest.json
  modified:
    - demo/scripts/make_mock.py
    - demo/mock/meta_onboarding.json
    - demo/mock/preferences_response.json
    - demo/mock/recommend_pop.json
    - demo/mock/recommend_cf.json
    - demo/mock/recommend_hybrid.json
    - demo/mock/recommend_hybrid_div.json
  deleted:
    - demo/mock/books.json
decisions:
  - "demo/fallback/popular.json 은 읽고 검증만 한다 — 소유권은 scripts/export_millie_fallback.py(06-PATTERNS §0-A)"
  - "showcase.json 의 본인 5권은 anchor_case 가 아니라 ShowcaseOut.personal_case 로 넣는다 — 스키마가 extra=forbid 이므로 스키마가 정본(06-CONTEXT D-08 충돌 해소)"
  - "catalog_kr.json·neighbors_kr.json 은 압축 직렬화, 계약 10파일은 indent=1"
  - "difficulty 값은 반올림하지 않는다 — 06-01-PLAN interfaces '생성기가 값을 바꾸지 않는다'"
metrics:
  duration: 약 65분
  tasks: 3
  files: 16
  completed: 2026-09-06
---

# Phase 6 Plan 01: make_mock 밀리 아티팩트 변환기 Summary

`demo/scripts/make_mock.py` 를 Goodbooks CSV 생성기(v1 407줄)에서 밀리 아티팩트(`artifacts/serving/*.json`) → `demo/mock/*.json` 13파일 변환기로 재작성하고, `tests/demo/test_make_mock.py` 10건이 계약·정확성·안전성을 단정한다.

## 무엇을 했나

| Task | 게이트 | 커밋 |
|---|---|---|
| 1 | RED — `tests/demo/test_make_mock.py` 신규(테스트 10개) | `694405e` |
| 2 | GREEN — `make_mock.py` 재작성 + mock 13파일 재생성 + `books.json` 삭제 | `f860c2e` |
| 3 | REFACTOR — 상수 블록 정리 · ruff 위반 0 · 결정성 실측 | `73e3357` |

세 커밋 모두 pathspec 을 지정해 커밋했고, 건드린 파일은 `demo/mock/**` · `demo/scripts/make_mock.py` · `tests/demo/test_make_mock.py` 16개뿐이다(`git diff --name-only 694405e~1 HEAD` 로 확인). `src/**` · `tests/serving/**` · `.planning/STATE.md` · `Makefile` 등 금지 경로는 0건.

## Red / Green 출력

RED (`uv run pytest tests/demo --no-header`):

```
>       _load().build(sample, out, CONFIG, eval_table=eval_path, seeds=FIXTURE_SEEDS)
E       AttributeError: module 'make_mock' has no attribute 'build'
1 failed, 9 errors in 0.26s
```

GREEN / REFACTOR:

```
uv run pytest tests/demo --no-header      → 10 passed in 0.17s
uv run pytest tests/test_architecture.py  → 3 passed in 0.06s
uv run pytest --no-header (전체)          → 523 passed, 2 warnings in 4.72s
uv run ruff check demo/scripts/make_mock.py tests/demo/test_make_mock.py → All checks passed!
```

전체 523 passed 에는 Phase 5 세션이 같은 작업 트리에서 편집 중인 `tests/serving/**` 이 포함되어 있다. 실행 시점(2026-09-06) 기준 실패 0.

## 실 아티팩트 1회 실행

```
[make_mock] fallback/popular.json ok (1 rows)
[make_mock] wrote 13 files → …/demo/mock (6878 KB)
```

- `ls demo/mock` = 13개. 구 `demo/mock/books.json` 없음.
- 계약 10파일 + `demo/fallback/popular.json` 이 pydantic `model_validate` 를 전부 통과(`ok` 11줄, 예외 0).
- `demo/fallback/popular.json` mtime: 실행 전 `1788622323` → 실행 후 `1788622323` (불변, 쓰기 코드 0건).
- `make mock` 은 실행하지 않았다(`Makefile` 의 `mock` 타겟은 존재하지 않는 `millie_rec.app.cli mock` 을 부른다 — 아래 Advisor 제안).

### `_manifest.json` outputs (바이트)

| 파일 | bytes |
|---|---|
| catalog_kr.json | 4,560,057 |
| neighbors_kr.json | 2,287,133 |
| recommend_pop.json | 43,765 |
| recommend_hybrid.json | 43,488 |
| recommend_cf.json | 43,484 |
| recommend_hybrid_div.json | 41,958 |
| showcase.json | 8,274 |
| candidates_onboarding.json | 8,302 |
| meta_onboarding.json | 3,280 |
| state.json | 1,435 |
| dashboard.json | 1,235 |
| preferences_response.json | 424 |

`du -sh demo/mock` = **6.8M** (`_manifest.json` 747 bytes 포함).

### 결정성 실측

REFACTOR 후 재실행한 결과 `git status --short -- demo/mock` 에 `_manifest.json`(생성 시각) 하나만 남았다. 나머지 12개 산출 JSON 은 Task 2 실행분과 **바이트 단위로 동일**하다. `_manifest.json` 의 `outputs` 도 두 실행이 동일(`outputs identical: True`).

## 06-CONTEXT 결정 이행

| 결정 | 이행 |
|---|---|
| D-02 아티팩트 축약본 | `CARD_KEYS` 16개 화이트리스트로만 조립. `description`·`curator_note`·`seg_dist`·`millie_id`·`tags`·`shelf_count` 원문 0건 |
| D-06 구 mock 삭제·재생성 | `build()` 가 `out/*.json` 을 먼저 전부 지운다. 구 `books.json` 삭제. `popular.json` 재생성은 폐기(06-PATTERNS §0-A) |
| D-08 쇼케이스 실측 숫자 | `eval_table.json` 문자열 → float 변환, `split_mode: holdout`, 본인 5권은 `personal_case`(스키마에 `anchor_case` 없음) |
| D-10 온보딩 메타 출처 | `demo/config/onboarding.json` S1·S3 옵션에서 생성. **`src/millie_rec/serving/onboarding_meta.json`(Phase 5 산출)과 `criteria`·`reading_times`·`subcategories` 가 전부 일치함을 확인했다** |

## 계획과 달라진 점

### 1. [Rule 3] `demo/fallback/popular.json` 은 쓰지 않는다 (계획대로, CONTEXT 와 다름)
- 06-CONTEXT D-06 은 "삭제 후 `make_mock.py` 가 재생성"이라고 적었지만 06-PATTERNS §0-A 실측대로 소유권은 `scripts/export_millie_fallback.py` 다.
- `validate_fallback()` 은 키 집합·`model_version`·`latency_ms` float 만 확인하고 stdout 1줄을 찍는다. `out.parent/"fallback"` 디렉터리를 만들지 않는다(테스트가 단정).
- 참고: 작업 트리의 `demo/fallback/popular.json` 은 이번 작업 이전부터 미커밋 수정 상태였다(`make millie-export` 산출물, mtime 1788622323). 이 플랜은 스테이징하지 않았다.

### 2. [Rule 1] `_rank()` 헬퍼 분리 — `pop_rank` 결측 정렬
- 줄 길이를 줄이려고 `c["pop_rank"] or MISSING_RANK` 로 쓰면 `pop_rank == 0` 이 맨 뒤로 밀린다. 명시적 `None` 판정 함수로 분리했다.

### 3. `ruff format` 을 `demo/scripts/make_mock.py` 에 적용하지 않았다
- 적용 시 594줄 → **795줄**로 늘어난다(포매터가 상수 표를 한 줄 한 항목으로 펼침). 같은 플랜의 `max_lines: 350` 과 정반대 방향이다.
- 대신 상수 블록을 `# fmt: off` / `# fmt: on` 으로 감싸고 E501 26건을 손으로 고쳤다. `uv run ruff check` 는 `All checks passed!`.
- `pyproject.toml` 의 `[tool.ruff] extend-exclude = ["demo", ".planning"]` 상 이 경로는 포매터의 소유가 아니다.

## 남은 편차 (Advisor 판단 필요)

### A. `demo/scripts/make_mock.py` 612줄 — 계획의 `max_lines: 350` 초과
- 파일을 쪼개면 같은 플랜의 다른 수용 기준 4개가 기계적으로 깨진다: `grep 'def is_eligible' make_mock.py` · `grep 'SEEDS = (1012, …)' make_mock.py` · `grep 'Goodbooks-10k(CC BY-SA 4.0)' make_mock.py` · popular.json 쓰기 grep — 전부 `make_mock.py` 단일 파일을 전제로 쓰여 있다. 또한 `demo/scripts/` 는 패키지가 아니라 형제 모듈 import 에 `sys.path` 조작 + `# noqa: E402` 가 필요하다.
- 350줄은 계획자가 파일을 쓰기 전에 추정한 값이고, 실제 로직만 약 460줄이다. `.claude/rules/simplicity.md` 의 150줄 규칙은 `src/` 파이썬 대상이며 이 파일은 단일 소유 빌드 스크립트다.
- **판단**: 단일 파일 유지. 분할이 필요하다면 수용 기준 4개를 같이 고쳐야 하므로 Advisor 결정 사항으로 남긴다.

### B. `du -sh demo/mock` = 6.8M — 계획의 ≤6M 초과
- 계획이 처방한 감량은 전부 적용했다: 카드 16필드만 · 이웃 top-20 절단 · `source` 제외 · 압축 직렬화.
- 초과 원인은 계획의 바이트 추정이 낮았기 때문이다. `catalog_kr.json` 4.56MB 중 약 2.15MB 가 **키 이름 반복**(9,444행 × 16키 × 평균 14자)이다. 필드 값은 `image_url` 961KB · `difficulty` 274KB · `title` 216KB 순.
- 더 줄이려면 배열 dict → 열지향(헤더 1줄 + 값 배열) 으로 형태를 바꿔야 하는데, 이는 wave 2 의 4개 플랜이 읽는 인터페이스 변경(아키텍처 결정)이라 이 플랜에서 하지 않았다.
- 위협 등록부 `T-06-01-06` 의 disposition 이 `accept` 이므로 현 상태로 인계하고 수치만 보고한다.

## Advisor 제안

이 플랜의 쓰기 영역이 아니어서 손대지 않은 것들이다.

1. **`Makefile` 의 `mock` 타겟**이 존재하지 않는 `uv run python -m millie_rec.app.cli mock` 을 부른다. `uv run python demo/scripts/make_mock.py` 로 고쳐야 `make mock` 이 동작한다(06-CONTEXT D-02 가 이미 지적).
2. **`.planning/REQUIREMENTS.md` DEMO-09** 문구를 "mock 완주(Phase 6) + api 완주(Phase 7 배포 전 게이트)"로 1줄 수정(06-CONTEXT D-09).
3. **`06-01-PLAN.md` frontmatter 의 `no_commit: true`** 와 오케스트레이터 지시("commit each task atomically")가 충돌한다. 오케스트레이터 지시를 따라 3커밋을 만들었다. 다음 wave 브리프에서 둘 중 하나로 정리가 필요하다.
4. **앵커 행에 같은 제목 다른 book_id 가 남는다.** `anchor_1012`("『싯다르타』을 좋아하셨다면")의 1위가 book_id 1335 『싯다르타』(다른 판본)이다. 서버 `serving/rows.py neighbor_row` 도 시드를 book_id 로만 제외하므로 동작은 일치하지만, 화면상 어색하다. 시드 제목까지 dedup 대상에 넣을지는 Phase 5 세션(`compose.py` 소유) 결정 사항이다.

## Known Stubs

- `demo/mock/dashboard.json` 은 **의도된 빈 집계**다(`kpi` 6개 전부 `value 0.0 · n 0`, `ab_table` `events_recent` `impressions_log` `by_variant` `by_hour` 빈 배열). 06-CONTEXT D-03 "고정 예시 숫자 금지 — 세션 이벤트 직접 집계"에 따라 값은 06-05 `d7_dashboard.js` 가 sessionStorage 이벤트로 채운다.
- `demo/mock/recommend_*.json` 의 `continue_reading` 행은 items 0개다. 읽던 책이 없는 초기 상태의 정상 표현이며, 화면은 빈 행을 숨긴다(06-PATTERNS §2-5).

## wave 2 인계

wave 2 의 4개 플랜은 아래 형태를 **그대로** 믿고 쓰면 된다. 전부 `demo/mock/` 아래 UTF-8 JSON 이다.

### 카탈로그 축약본 2개 (계약 외 · 압축 직렬화 · `06-03 mock.js` 전용)

| 파일 | 최상위 | 레코드 수 |
|---|---|---|
| `catalog_kr.json` | 배열 | 9,444 |
| `neighbors_kr.json` | 객체 | 9,444 키 |

`catalog_kr.json` 원소 = **정확히 16키, 이 순서**:
`book_id`(int) `title`(str) `authors`(str\|null) `image_url`(str) `categories`(list[str]) `publisher`(str\|null) `book_format`(str\|null) `pop_rank`(int\|null) `millie_label`(str\|null) `average_rating`(float\|null) `review_count`(int\|null) `completion_prob`(int\|null) `category_avg_prob`(int\|null) `expected_min`(int\|null) `difficulty`(float\|null) `formats`(list[str])

- 배열은 `pop_rank` 오름차순 정렬(결측은 맨 뒤). 첫 원소 = book_id 1004 『불편한 편의점』 `pop_rank` 1.
- `difficulty` 는 `difficulty_source == "category_prior"` 인 책이 `null` — 난이도 점은 그때 미표시.
- 밀리 저작 텍스트(설명문·큐레이터 노트·리뷰) 0건. 표지는 `*.millie.co.kr` 핫링크만.

`neighbors_kr.json` = `{"<book_id>": [[dst:int, weight:float], …]}`, 키는 **문자열**, 값은 최대 20개, `weight` 내림차순·소수 4자리, `dst` 는 카탈로그에 있는 책만. 예: `"1": [[159, 0.603], [1121, 0.2]]`.

### 계약 10개 (pydantic 검증 통과 · `indent=1`)

| 파일 | 모델 | 최상위 키 / 레코드 수 |
|---|---|---|
| `meta_onboarding.json` | `OnboardingMeta` | `survey_variant` `reading_times`(5) `criteria`(5) `categories`(29) |
| `candidates_onboarding.json` | `CandidateSet` | `candidate_set_id` `survey_variant` `created_at` `items`(30) |
| `preferences_response.json` | `PreferencesResponse` | `user_key` `preference_snapshot_id` `created_at` `cell` `snapshots_count` `persona` |
| `recommend_pop.json` | `RecommendOut` | 15키, `rows` 5행, `items` 40 |
| `recommend_cf.json` | `RecommendOut` | 15키, `rows` 5행, `items` 40 |
| `recommend_hybrid.json` | `RecommendOut` | 15키, `rows` 5행, `items` 40 |
| `recommend_hybrid_div.json` | `RecommendOut` | 15키, `rows` 5행, `items` 39 |
| `state.json` | `UserStateOut` | `library.added`(5) `reading`(0) `completed`(0), `snapshots`(1) |
| `dashboard.json` | `DashboardOut` | `kpi`(6) `ab_table`(0) `latency` `quality`(3) |
| `showcase.json` | `ShowcaseOut` | `eval_table.rows`(4) `metric_mapping`(3) `personal_case` `memorable_5`(5) `roadmap`(7) |

세부 형태:

- `meta_onboarding.categories[]` = `{name, supported, subcategories}`. 29종 중 `supported: true` 27종(권수 ≥ 20). `subcategories` 가 비지 않은 것은 `소설`·`철학`·`IT` 3종뿐. 정렬은 권수 내림차순·동률 이름순. `criteria[]` = `{id, label}`, id 순서 **`author` `publisher` `bestseller` `buzz` `review`**.
- `candidates_onboarding.items[]` = `{book_id, title, authors, image_url, position, book_format}`, 소설·인문·자기계발 라운드로빈 30권.
- `preferences_response.persona` = `{name, work, quote, description}`. 현재 값은 셜록 홈즈(카테고리 `소설` 지배).
- `RecommendOut` 최상위 15키: `recommendation_id` `model_version` `preference_snapshot_id` `user_key` `cell` `forced` `fallback_level` `context` `latency_ms` `latency_breakdown` `user_state_weights` `dedup_removed` `nearline_lag_s` `items` `rows`.
  - `latency_ms` 는 **float 38.0**, 단계별은 `latency_breakdown` = `{feature, retrieval, ranking, rerank, compose, total}` 이고 `total == latency_ms`. 표시값이며 PDF 숫자가 아니다.
  - `model_version` = `"{variant}_v1"`. `cell` = `"B"`. `forced` = `true`. `fallback_level` = 0. `user_state_weights` = `{alpha:0.7, beta:0.2, gamma:0.1}`. `nearline_lag_s` = 1.0. `context` = `"저녁, 하루를 마치며"`.
  - `rows[]` = `{row_id, title, purpose, items, subtitle, channel_mix}`. 5행 순서와 items 수:

    | row_id | purpose | pop | cf | hybrid | hybrid_div |
    |---|---|---|---|---|---|
    | `continue_reading` | resume | 0 | 0 | 0 | 0 |
    | `anchor_1012` | discover | 8 | 8 | 8 | 8 |
    | `persona_shelf` | discover | 12 | 11 | 11 | 8 |
    | `trending` | fallback | 10 | 11 | 11 | 12 |
    | `fresh_picks` | explore | 12 | 11 | 11 | 11 |

    `dedup_removed` = pop 6 · cf 7 · hybrid 7 · hybrid_div 9.
    행 제목: `이어 읽기` / `『싯다르타』을 좋아하셨다면`(subtitle `결이 비슷한 책`) / `셜록 홈즈의 서가` / `지금 많이 읽는 책` / `새로운 발견`.
  - `items[]`(= `rows[].items[]`) = **12키**: `book_id` `score` `source` `reason` `title` `authors` `image_url` `position` `source_channels` `badge` `book_format` `difficulty`. `source`·`source_channels` 는 `"content"` 또는 `"popularity"` 만 — **`itemknn` 0건**(Track B 는 콘텐츠 유사도다). `badge` 는 `null` 또는 `{type, text}`, 현재 criterion 이 `bestseller` 라 전부 `{"type":"bestseller","text":"인기 N위"}`.
- `state.library.{added,reading,completed}[]` = `{book_id, title, image_url}`. `snapshots[]` = `{snapshot_id, created_at, categories, criterion, active}`.
- `dashboard.kpi` 키 6개: `qualified_reading_start_rate` `first_completion_rate_new` `fallback_rate` `p95_latency_ms` `error_rate` `active_user_keys`, 각 값 `{value, n, note}`. `latency` = `{p50, p95, p99, by_stage}`. `quality` = `{impression_receipt_rate, flagged_events, feature_freshness_s}`.
- `showcase.eval_table` = `{split_mode:"holdout", source:{metrics,p95}, rows:[…4]}`, 행 = `{variant, recall_at_20, ndcg_at_10, ild_at_10, p95_ms}` **전부 float**(예: pop `0.063`/`0.054`/`0.764`). `p95_ms` 는 로컬 bench 가 있는 `hybrid`·`hybrid_div` 만 `79.5`, `pop`·`cf` 는 `null`.
  `metric_mapping` = `[{stage:"Candidate Retrieval",metric:"Recall@20"}, {"Ranking","NDCG@10"}, {"Re-ranking","ILD@10"}]`.
  `personal_case` = `{seeds:[…5], recommendations:[…10]}`, 각 원소 `{book_id, title, image_url, reason, badge}`. 시드 5권 = 싯다르타(1012) · 데미안(2765) · 위버멘쉬(1446) · 쇼펜하우어 인생수업(1222) · 빅터 프랭클의 죽음의 수용소에서(2292). 추천 10권의 `reason` 은 전부 `『…』을 좋아하셨다면` 형태.
  `memorable_5[]` = `{claim, how_to_verify, route}` 5개, `roadmap` = 문자열 7개, `data_notice` = 2트랙 고지 1문장.

### 재생성 방법

```bash
uv run python demo/scripts/make_mock.py     # make mock 은 쓰지 않는다
```

`--artifacts` `--out` `--config` `--latency` 로 경로를 덮을 수 있다. mock JSON 손편집 금지(`.claude/rules/demo.md`) — `_manifest.json` 의 입력 md5·출력 bytes 가 `/contract-sync` 의 재생성 판정 근거다.

## Self-Check: PASSED

산출 파일 16개 전부 존재, 구 `demo/mock/books.json` 삭제 확인, 커밋 3개(`694405e` `f860c2e` `73e3357`) 존재. 누락 0건.
