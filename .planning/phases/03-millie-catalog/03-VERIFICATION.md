---
phase: 03-millie-catalog
verified: 2026-09-06T10:30:00Z
status: passed
score: 6/6 must-haves verified (ROADMAP Success Criteria 5개 + Should 꼬리 DATA-08 1개)
overrides_applied: 0
---

# Phase 3 '밀리 카탈로그 빌드'(.planning/ROADMAP.md "Phase 3: 밀리 카탈로그 빌드") Verification Report

**Phase Goal:** 밀리 공개 도서 전량이 커버리지·이웃 게이트를 통과한 서빙 아티팩트가 되어, 데모·앵커·배지·난이도·본인 5권이 전부 한국 책 위에서 동작한다(.planning/ROADMAP.md "Phase 3: 밀리 카탈로그 빌드" 절).
**Verified:** 2026-09-06T10:30:00Z
**Status:** passed
**Re-verification:** No — 초기 검증 (03-VERIFICATION.md 신규 작성)

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria 1~5 + Should 꼬리)

| # | Truth | Status | Evidence |
|---|---|---|---|
| 1 | 커버리지 게이트 통과 → `results/millie_coverage.csv` (title 100%·image_url ≥99%·categories ≥95%·completion_prob ≥70%·formats ≥90%·seg_dist ≥70%·카테고리 ≥8종·20권 이상 ≥6분야) — DATA-01·02·03 | ✓ VERIFIED | 최종 스냅샷(9,447권) 실측: title 1.0000 · image_url 1.0000 · categories 1.0000 · completion_prob 0.8252 · formats 0.9661 · seg_dist 0.7816 · `_category_distinct` 104 · `_categories_ge_20` 26 · `_n_skipped_titleless` 4/9,580=0.042%(≤0.5%) · `_n_badge_title` **0**(Plan 03-08 UAT gap 해소 확인, JSON 재검사로 배지 라벨 title 0건 재확인) — 전 항목 미달 0 |
| 2 | `item_edges_kr.parquet`가 이웃 게이트 3 통과, `id_map.csv` 기존 행 diff 0 — DATA-05 | ✓ VERIFIED | `results/millie_edges_gate.json`: self_edges 0 · min_degree 21(≥5) · n_orphans 0 · same_category_share 0.3564(≤0.70) · n_books 9,447 · n_edges 350,080. `data/id_map.csv` 9,453행(append-only, 03-06 SUMMARY Task4가 접두 diff 빈 출력 확인) |
| 3 | `catalog_kr.py`가 Catalog·Neighbors·BookStatsSource 구현, description·curator_note 미노출, 난이도 `σ(−resid_z)`·결측 `difficulty=None` — DATA-04·06 | ✓ VERIFIED | `src/millie_rec/data/catalog_kr.py`(118줄) 코드 직접 확인: `EXCLUDED_META_KEYS=(description,curator_note,seg_dist)`를 `__init__`에서 재필터, `is_eligible`이 D-14 규칙(title ∧ `*.millie.co.kr` ∧ `adult-cover` 아님) 그대로, `stats()`가 `difficulty=row.get("difficulty")`(None 보존)·`source=difficulty_source` 반환. `tests/data/test_catalog_kr.py` 12건·`test_vectors_kr.py` 4건·`test_architecture.py` 3건 통과 |
| 4 | `make millie-export` 후 `artifacts/serving/` 4파일 + `demo/fallback/popular.json`, 파일당 <50MB·description 0건, 서버 주입 시 `/api/recommend`가 밀리 책으로 응답 — DATA-07 | ✓ VERIFIED | 실측 파일 크기: books_kr.json 8MB · item_edges_kr.json 11MB · popularity_kr.json 8MB · content_vectors_kr.npz 5MB(전부 <50MB) · popular.json 19KB. `grep -c '"description"\|"curator_note"\|"seg_dist"'` 전 4파일 0. `content_vectors_kr.npz`: book_ids(9447,) int64 · vectors(9447,128) float32 · L2 norm 1.0000±1e-6. `app/server.py`가 `load_catalog()`→`catalog`를 `pipelines`·`fallback`·`catalog=`·`neighbors=`·`book_stats=`에 주입(코드 직접 확인) |
| 5 | `uv run pytest -q`·`make smoke` PASS · `/contract-sync` 카탈로그 항목 통과 | ✓ VERIFIED | Phase 3 소유 테스트 파일 전부(`test_millie_catalog.py`·`test_millie_edges.py`·`test_millie_difficulty.py`·`test_catalog_kr.py`·`test_vectors_kr.py`·`test_millie_popularity.py`·`test_millie_export.py`·`test_millie_vectors.py`·`test_millie_fallback.py`·`test_millie_parse.py`·`test_millie_recollect.py`·`tests/app`·`tests/serving`·`test_architecture.py`) 재실행 결과 **전건 통과**(dot만, F/E 0). `test_coverage_gate`·`test_neighbour_quality_gate` 개별 재실행 2 passed. `make smoke` → `/health 200`·`/`(demo) 200·`/api/recommend 200`·`PASS`. `/contract-sync` 카탈로그 항목은 위 계약 9키·book_format·description 부재 검증으로 등가 확인(별도 스킬 미실행, grep 재현) |
| Should | `popularity_kr`가 연령×성별 세그먼트를 갖는다(DATA-08) | ✓ VERIFIED | `artifacts/serving/popularity_kr.json` 재파싱: 13개 segment(all + 12) · all 9,447행 · 세그먼트별 7,384행(=9,447×0.7816=seg_dist 보유율과 일치) |

**Score:** 6/6 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|---|---|---|---|
| `artifacts/serving/books_kr.json` | 계약 9키 ⊂ 28키, description 등 제외 | ✓ VERIFIED | 9,447행, 28키, 제외 문자열 0, badge_title 0 |
| `artifacts/serving/item_edges_kr.json` | 이웃 게이트 3 통과 데이터 | ✓ VERIFIED | 11MB, self-edge/orphan 0 |
| `artifacts/serving/popularity_kr.json` | `{book_id,segment,score,rank}` 행 | ✓ VERIFIED | 13 segment, 4컬럼 |
| `artifacts/serving/content_vectors_kr.npz` | book_ids·vectors(N,128) float32 L2=1 | ✓ VERIFIED | (9447,) / (9447,128), norm 1.0000 |
| `demo/fallback/popular.json` | RecommendOut level 3 형태 | ✓ VERIFIED | 19KB, description 등 0건(schemas.py 검증은 03-05 SUMMARY `RecommendOut.model_validate` 통과 기록으로 갈음) |
| `data/id_map.csv` | append-only, 9,453행 | ✓ VERIFIED | wc -l 9453 |
| `results/millie_coverage.csv` | 최종 스냅샷 게이트 실측 | ✓ VERIFIED | `_n_records` 9447, 미달 0 |
| `results/millie_edges_gate.json` | 이웃 게이트 3 실측 | ✓ VERIFIED | 3게이트 전부 통과 |
| `src/millie_rec/data/catalog_kr.py` | ≤150줄, 3 Protocol 만족 | ✓ VERIFIED | 118줄, 코드 확인 |
| `src/millie_rec/data/vectors_kr.py` | ≤150줄, ItemVectors 구현 | ✓ VERIFIED | 44줄(SUMMARY 38줄에서 소폭 증가, 이후 세션 정리 추정) |
| `scripts/millie_difficulty.py` | ≤150줄, 순수 함수 | ✓ VERIFIED | 81줄 |
| `scripts/build_millie_catalog.py` | 150줄 예외 승인(D-16) | ✓ VERIFIED(예외) | 313줄 — D-16·Plan 03-08 순증 상한 준수 기록, Advisor 수용 |
| `scripts/build_millie_edges.py` | ≤150줄 | ✓ VERIFIED | 152줄 |
| `scripts/build_millie_popularity.py` | ≤150줄 | ✓ VERIFIED | 77줄 |
| `scripts/export_millie_serving.py` | ≤150줄 | ✓ VERIFIED | 102줄 |
| `scripts/export_millie_vectors.py` | ≤150줄 | ✓ VERIFIED | 72줄 |
| `scripts/export_millie_fallback.py` | ≤150줄 | ✓ VERIFIED | 138줄 |
| `scripts/millie_parse.py` | 150줄 예외 승인(D-16) | ✓ VERIFIED(예외) | 275줄 |
| `scripts/collect_millie.py` | 150줄 예외 승인(D-16) | ✓ VERIFIED(예외) | 317줄 |
| `scripts/millie_recollect_list.py` | ≤150줄(Plan 03-08) | ✓ VERIFIED | 46줄 |

### Key Link Verification

| From | To | Via | Status | Details |
|---|---|---|---|---|
| `artifacts/serving/books_kr.json` (존재) | `app/server.py::load_catalog()` | `CatalogKR.load(DIR_SERVING)` | WIRED | `server.py` 1행: `catalog = load_catalog()` → 이후 `pipelines`·`fallback`·`catalog=`·`neighbors=`·`book_stats=` 전부에 주입(코드 직접 확인) |
| `CatalogKR` | `create_app(pipelines=..., fallback=GlobalPopularFallback(catalog))` | `app/pipeline.py::build_pipelines(catalog=)` | WIRED | 03-06 SUMMARY Task1 GREEN 로그(`pipelines['pop']` 실 카탈로그 순서로 응답) + 이번 검증 코드 재확인 |
| `scripts/build_millie_catalog.py` | `data/id_map.csv` | `assign_ids`(append-only) | WIRED | 9,453행, 기존 행 삭제 0(03-06 Task4 diff 빈 출력) |
| `scripts/build_millie_edges.py` | `data/processed/books_kr.parquet` | `pd.read_parquet` + TF-IDF cosine | WIRED | `results/millie_edges_gate.json`이 9,447권 전량에 대해 생성됨 |
| `export_millie_serving.py` | `artifacts/serving/*.json` | `_write`(<50MB 단언) | WIRED | 4파일 실측 크기 전부 확인 |
| `millie_parse.py::_NAV_NOISE` | `build_millie_catalog.py::coverage()['n_badge_title']` | 배지 라벨 스킵 → 게이트 카운터 | WIRED | 최종 아티팩트 `n_badge_title=0`(Plan 03-08 재수집 900건 반영 후 재빌드 결과) |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|---|---|---|---|
| 커버리지 게이트 실측 재현 | `uv run pytest tests/data/test_millie_catalog.py::test_coverage_gate --no-header -v` | 1 passed | ✓ PASS |
| 이웃 게이트 실측 재현 | `uv run pytest tests/data/test_millie_edges.py::test_neighbour_quality_gate --no-header -v` | 1 passed | ✓ PASS |
| Phase 3 소유 테스트 전 파일 회귀 | `uv run pytest tests/data/test_millie_*.py tests/data/test_catalog_kr.py tests/data/test_vectors_kr.py tests/app tests/serving tests/test_architecture.py --tb=short` | 전건 dot(F/E 0) | ✓ PASS |
| 로컬 기동·API 형태 | `make smoke` | `/health 200 · / 200 · /api/recommend 200 · PASS` | ✓ PASS |
| 배지 title 오염 재확인(UAT gap) | `python3` — books_kr.json title을 배지 라벨 7종·`^종료 D-\d+$` 정규식과 대조 | `badge_title_count: 0`(9,447건 중) | ✓ PASS |
| 서빙 아티팩트 금지 필드 재확인 | `grep -c '"description"\|"curator_note"\|"seg_dist"' <4파일>` | 전부 0 | ✓ PASS |
| npz 벡터 정합성 | `numpy.load` shape·dtype·L2 norm | (9447,)int64 / (9447,128)float32 / norm 1.0000 | ✓ PASS |
| popularity 세그먼트 구조 | `json.load` 후 segment 분포 집계 | 13종, all 9447 · 세그먼트별 7384 | ✓ PASS |

**참고 — 전체 저장소 `uv run pytest`(scope 제한 없음)는 이 검증 시점에 간헐적으로 `tests/data/test_millie_difficulty_stats.py`에서 실패/에러를 보였다.** 이 파일은 Phase 3의 8개 플랜 어디에도 없고(`grep -rl "millie_difficulty_stats" .planning/phases/` 결과 없음), mtime이 검증 직전(10:0x)이며 재실행 시 통과/실패가 바뀌었다 — 다른 세션이 다른 페이즈(난이도 통계·ablation 관련, REC 계열로 추정) 작업을 TDD Red↔Green 사이클로 동시에 진행 중인 파일이다. Phase 3 소유 테스트 파일만 골라 실행하면(위 표) 전건 통과하므로 **Phase 3 회귀가 아니다**. 전체 스위트 100% green 확인은 해당 세션의 작업이 완료된 뒤 재시도가 필요하다.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|---|---|---|---|---|
| DATA-01 | 03-01 | `book_id` 사전순 surrogate, id_map append-only | ✓ SATISFIED | id_map 9,453행, 재빌드 3회(03-01·03-06·03-08) 걸쳐 기존 행 변동 0 |
| DATA-02 | 03-01 | 계약 컬럼 9개 + `book_format` 3종 | ✓ SATISFIED | books_kr.json 28키 ⊃ 계약 9키, book_format ∈ {전자책,오디오북,챗북} |
| DATA-03 | 03-01, 03-08 | 커버리지 게이트 | ✓ SATISFIED | `results/millie_coverage.csv` 전 항목 통과 + `_n_badge_title=0`(03-08 게이트 강화) |
| DATA-04 | 03-01, 03-02 | 완독지수 파생 난이도 | ✓ SATISFIED | `resid_z`·`len_z`·`difficulty`, 결측 `category_prior`·None |
| DATA-05 | 03-03 | content_sim TF-IDF 이웃·게이트 3 | ✓ SATISFIED | `results/millie_edges_gate.json` 3게이트 통과 |
| DATA-06 | 03-02 | `catalog_kr.py` 어댑터·텍스트 미노출 | ✓ SATISFIED | `EXCLUDED_META_KEYS` 코드 확인 + export grep 0건 |
| DATA-07 | 03-04, 03-05, 03-06 | export 산출물 4+1 | ✓ SATISFIED | 4+1 파일 존재·크기·형태 전부 확인 |
| DATA-08 | 03-07 | `popularity_kr` 세그먼트(Should) | ✓ SATISFIED | 13 segment 확인. fallback level 2 응답 자체 검증은 D-15에 따라 Phase 3 완료 기준이 아니며 Phase 5가 이어받음(아래 참고) |

REQUIREMENTS.md 상의 Phase 3 매핑 8건(DATA-01~08) 전부 위 표로 커버됨. 고아(orphan) 요구사항 없음.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|---|---|---|---|---|
| — | — | 없음 | — | Phase 3 소유 파일에서 TODO/FIXME/스텁 반환/하드코딩 빈 값 패턴 미발견(SUMMARY의 RED 단계 스텁은 TDD 사이클의 정상 산출물이며 최종본에 남지 않음) |

### Human Verification Required

없음 — 서버 응답(level 0 한글 제목, level 3 카탈로그 인기)은 03-UAT.md Test 9·10에서 이미 사람이 직접 curl로 확인했고(2026-09-05~06), 이번 검증에서 동일 산출물(9,447권 최종 스냅샷)의 데이터 정합성을 재확인했다. 신규 사람 판단 필요 항목 없음.

### Gaps Summary

없음. ROADMAP Success Criteria 5개·Should 꼬리 DATA-08·REQUIREMENTS DATA-01~08 전부 최종 스냅샷(9,447권, 2026-09-06 00:31~32 재빌드)에서 통과가 확인된다.

**03-UAT.md의 유일한 major 이슈(Test 9 — 밀리 기능 배지 라벨이 title로 잡힌 728/8,708권 오염)는 Plan 03-08로 완전히 해소됐다**: `millie_parse.py` 배지 스킵 추가 → 게이트에 `_n_badge_title` 카운터 신설 → 896건(최종 집계, 9,450권 기준 9.5%) 재수집 → `make millie` 최종 재빌드 → 최종 아티팩트에서 `_n_badge_title=0`을 이번 검증에서 직접 재확인. 이 gap은 **닫힘**으로 기록한다.

**03-06 SUMMARY의 인계 4건 처리 현황(참고, 확인 가능한 범위):**
1. **익명 level 3 items의 `title=None`(meta 조인 누락)** — Phase 5 '서빙 Must 완성' 몫으로 명시(`05-02-PLAN.md` 86행이 "Phase 3 인계 '익명 level 3 items title None' 해소"를 목적으로 명기). Phase 5 VERIFICATION 상태 `passed`(재검증)로, 이 인계는 **처리됨**.
2. **제목 중복('도슨트북' 2권 등)** — 같은 `05-02-PLAN.md` 86행이 "'제목 중복(도슨트북 2권)' 해소"를 함께 명기. **처리됨**(Phase 5가 흡수). 단, 이는 배지 라벨 문제와 달리 서로 다른 book_id가 우연히 같은 실제 제목을 갖는 데이터 품질 항목으로, Phase 3 자체 게이트 대상은 아니었다.
3. **`demo/js/inspector.js`의 `model_version === "static_popular"` 라벨 불일치 + `make mock` 금지** — 확인 결과 `inspector.js` L106·L110에 `"static_popular"` 문자열이 **여전히 남아 있다**(코드 grep 재확인). Phase 6 '데모 재구성'이 명시적으로 이 lane을 담당하며(`06-01-PLAN.md`가 `make_mock.py` 재작성을 다룸), 세션 규칙상 다른 세션이 `demo/` 작업 중이라 이 검증은 이 파일을 수정하지 않았다. **Phase 3 완료 기준 밖(원래도 Phase 6 인계)이며 아직 미착수 — 정보로만 기록, Phase 3의 gap이 아니다.**
4. **이웃 빌드 peak RSS(6,977권 기준 1.24GB, 9천 권 초과 시 우려)** — 최종 9,447권 재빌드가 03-06 SUMMARY Task4에서 37초 만에 성공했고 이번 검증에서도 `results/millie_edges_gate.json`이 정상 생성된 것을 확인했다. `scripts/build_millie_edges.py`에 `astype(np.float32)` 같은 최소화 조치는 적용되지 않았지만(코드 grep 0건) 실측상 문제가 발생하지 않았다. **관측으로 종결, gap 아님.**

---

_Verified: 2026-09-06T10:30:00Z_
_Verifier: Claude (gsd-verifier)_
