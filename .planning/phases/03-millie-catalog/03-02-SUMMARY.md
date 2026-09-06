---
phase: 03-millie-catalog
plan: 02
subsystem: data
tags: [catalog, adapter, protocol, json, npz, track-b]

requires:
  - phase: 01-local-serving-skeleton
    provides: "contracts.Catalog·Neighbors·BookStatsSource·ItemVectors Protocol, create_app 주입 표면"
  - phase: 02-track-a
    provides: "retrieval/content.py ItemVectors 0-벡터 규약, retrieval/popularity.py load classmethod 패턴"
provides:
  - "CatalogKR — Catalog·Neighbors·BookStatsSource 를 한 객체로 만족하는 Track B 어댑터"
  - "VectorsKR — content_vectors_kr.npz 를 읽는 ItemVectors 구현"
  - "tests/conftest.py millie_serving_sample — 20권 합성 서빙 산출물 생성기(Plan 06 서버 주입 테스트가 재사용)"
affects: ["03-04 export", "03-06 서버 주입", "Phase 4 hybrid_div·난이도 가드"]

tech-stack:
  added: []
  patterns:
    - "서빙 경로 어댑터는 stdlib json + numpy 만 — pandas import 0(.claude/rules/serving.md)"
    - "app/export.py 의 DIR_SERVING 을 data 슬라이스에 중복 정의(star 의존상 app import 불가)"

key-files:
  created:
    - src/millie_rec/data/catalog_kr.py
    - src/millie_rec/data/vectors_kr.py
    - tests/data/test_catalog_kr.py
    - tests/data/test_vectors_kr.py
  modified:
    - src/millie_rec/data/__init__.py
    - tests/conftest.py

key-decisions:
  - "결정 D-14 'Catalog.eligible() = title ∧ *.millie.co.kr ∧ adult-cover 아님'(.planning/phases/03-millie-catalog/03-CONTEXT.md) 을 urlsplit().hostname.endswith 로 구현 — 부분 문자열 검사가 아니라 hostname 접미 검사라 millie.co.kr.evil.com 을 막는다"
  - "DATA-06(description·curator_note 미노출)을 EXCLUDED_META_KEYS 로 __init__ 에서 한 번 더 제거 — export 가 실수로 넣어도 API 로 나가지 않는다"
  - "DATA-04(결측 difficulty=None)를 BookStats DTO 까지 그대로 보존, source 는 difficulty_source 그대로"

patterns-established:
  - "인덱스·인기 순서는 __init__ 1회 계산(_by_id·_pop_order), 요청마다 재정렬하지 않는다"
  - "load 는 books_kr.json 부재 시 FileNotFoundError·손상 시 ValueError 를 그대로 올린다(부재 처리는 app 로더 몫)"

no_commit: true
---

# Plan 03-02 — 카탈로그 어댑터 CatalogKR·VectorsKR

## 변경 파일 (커밋하지 않았다)

| 경로 | 상태 | 내용 |
|---|---|---|
| `src/millie_rec/data/catalog_kr.py` | NEW 118줄 | `is_eligible` · `CatalogKR`(meta·popular·eligible·neighbors·stats·user_level) · 상수 8개 |
| `src/millie_rec/data/vectors_kr.py` | NEW 38줄 | `VECTORS_KR_NPZ` · `VectorsKR`(load·dim·vectors) |
| `src/millie_rec/data/__init__.py` | MODIFY | 이름 7개 추가(아래) |
| `tests/conftest.py` | MODIFY | `_sample_book` + 세션 fixture `millie_serving_sample`, 상수 5개. 기존 fixture 2개 불변 |
| `tests/data/test_catalog_kr.py` | NEW | 12건 |
| `tests/data/test_vectors_kr.py` | NEW | 4건 |

`data/__init__.py` 에 추가된 이름 7개: 상수 `BOOKS_KR_JSON` `DIR_SERVING` `EDGES_KR_JSON` `VECTORS_KR_NPZ` · 클래스 `CatalogKR` `VectorsKR` · 함수 `is_eligible`. 기존 25개 이름·정렬 규칙(대문자 상수 → 클래스 → 함수) 불변.

## RED (Task 1, 스텁 위)

```
14 failed, 2 passed in 0.07s
E       assert (0 == 2)                                   # test_catalog_kr_satisfies_three_protocol_shapes
E       assert [] == [1, 2, 3, 4, 5, 6, ...]              # test_popular_is_pop_rank_order_of_eligible_only
E       assert ([])                                       # test_popular_with_categories_filters_by_intersection
E       assert [] == [1, 17]                              # test_eligible_rules_title_host_suffix_adult_cover
E       assert [] == [(2, 0.9), (3, 0.8), (4, 0.7)]       # test_neighbors_weight_desc_and_n_cap
E       assert 0 == 2                                     # test_stats_maps_book_stats_and_keeps_none_difficulty
E       assert 0 == 1                                     # test_meta_returns_rows_in_order_and_drops_excluded_keys
E       assert [] == [1]                                  # test_load_without_edges_file_gives_empty_neighbors
E       Failed: DID NOT RAISE FileNotFoundError           # test_load_missing_books_raises_file_not_found
E       Failed: DID NOT RAISE ValueError                  # test_load_corrupt_books_raises_value_error
E       assert 0 == 8                                     # test_vectors_shape_and_dim
E       assert array([0., 0....  0., 0., 0.]) == 1.0 ± 1.0e-05   # test_rows_are_l2_normalized
E       assert (np.False_)                                # test_order_preserved_and_unknown_is_zero
E       assert [] == [0.0, 1.0, 0.0]                      # test_load_from_npz_written_with_savez
```
`grep -nE "ImportError|ModuleNotFoundError|SyntaxError|NameError|TypeError"` → 출력 없음. 같은 시점 `uv run pytest tests/test_architecture.py --no-header` → `3 passed`.

**RED 에서 2건은 통과했다**(14 failed / 2 passed, 16건 중): `test_dir_serving_constant_points_to_artifacts_serving`(상수만 단정 — 상수는 플랜 1-a 가 스텁 단계에 정의하라고 지시)과 `test_unknown_ids_are_skipped_not_raised`(빈 리스트 스텁이 "미지 id 는 빈 결과" 를 우연히 만족). 플랜 `<done>` 의 "15건 단정 실패" 는 이 두 건을 감안하지 않은 수치다.

## GREEN (Task 2)

```
uv run pytest tests/data/test_catalog_kr.py tests/data/test_vectors_kr.py tests/test_architecture.py --no-header
19 passed in 0.07s
```
회귀:
```
uv run pytest tests/data tests/serving tests/app --no-header
162 passed, 2 skipped, 2 warnings in 1.91s
```
(형제 Worker Plan 03-01 의 `tests/data/test_millie_*` 도 이 시점에는 전부 green 이었다 — failed 0.)

ruff:
```
uv run ruff format <6파일> → 6 files left unchanged
uv run ruff check  <6파일> → All checks passed!
```

## 줄 수·grep 단언

| 단언 | 결과 |
|---|---|
| `wc -l catalog_kr.py` | 118 (≤150) |
| `wc -l vectors_kr.py` | 38 (≤150) |
| `grep -rn "millie_rec\.(retrieval\|evaluation\|serving\|app)" <두 파일>` | 출력 없음 |
| `grep -c "import pandas\|from pandas\|sklearn"` | 0 · 0 |
| `grep -c "def meta\|def popular\|def eligible\|def neighbors\|def stats\|def user_level"` | 6 |
| `grep -c "EXCLUDED_META_KEYS"` | 2 |
| `grep -c "endswith(COVER_HOST_SUFFIX)"` | 1 |
| `grep -c '"CatalogKR"\|"VectorsKR"\|"DIR_SERVING"\|"BOOKS_KR_JSON"' __init__.py` | 4 |
| `grep -c "def test_"` | 12 (catalog) · 4 (vectors) |
| `grep -c "def millie_serving_sample" tests/conftest.py` | 1 |

## fixture 규격 (Plan 06 서버 주입 테스트가 재사용)

`millie_serving_sample`(session scope) → `books_kr.json`(20행) · `item_edges_kr.json`(문자열 키) · `popularity_kr.json`(segment="all") · `content_vectors_kr.npz`(book_ids int64[20], vectors float32[20,8] 행 L2=1) 이 든 `Path`.

- `book_id` 1..20, `pop_rank == book_id`.
- **자격 없는 3권**: `18`(호스트 `cdn.example.com`) · `19`(`title` None) · `20`(`adult-cover-a.webp`). → `popular()`·`eligible()` 결과는 항상 `[1..17]` 부분집합.
- **`category_prior` 규칙**: 홀수 `book_id` ≥ 15(즉 15·17·19)만 `difficulty_source="category_prior"` · `difficulty=None` · `resid_z=0.0`. 나머지는 `millie_index` · `difficulty=round(σ(−resid_z), 4)`.
- 카테고리 순환 `소설·에세이·경제경영·인문`, 표지 호스트 순환 `img.·image.·cover.millie.co.kr`, `book_format` 순환 `전자책·오디오북·챗북`.
- 이웃: `src i` → `dst = (i+d-1) % 20 + 1`(d=1..5), weight `0.9 0.8 0.7 0.6 0.2`, source 앞 4 `content_sim` 마지막 `category_best`.
- 실 `artifacts/serving/` 은 어떤 테스트도 읽지 않는다.

## 판단이 필요했던 지점

1. **`difficulty` 반올림 vs `pytest.approx` 기본 허용오차.** 플랜은 fixture 에 `round(σ(−resid_z), 4)`, 테스트에 `pytest.approx(1/(1+exp(resid_z)))`(기본 rel=1e-6)를 지시했는데 둘을 같이 쓰면 4자리 반올림 오차(rel≈6.6e-5)로 GREEN 에서도 실패한다. fixture 를 플랜대로 두고 테스트를 `abs=1e-4` 로 지정해 해결했다.
2. **테스트 건수 11 vs 12.** 플랜 acceptance 는 `test_catalog_kr.py` 12건이 아니라 11건을 적었지만, 플랜 1-c 가 **열거한 테스트는 12개**(계약 1 + 정확성 6 + 안전성 4 + 상수 1)다. 열거된 테스트를 정본으로 보고 12건을 썼다 → 합계 `19 passed`(플랜의 18 대신).
3. **RED 에서 2건 통과**(위 RED 절). 스텁이 상수를 정의하고 빈 값을 반환하는 이상 이 2건은 원리적으로 Red 가 될 수 없어, 스텁을 왜곡하는 대신 사실대로 기록했다.

## 커밋

**커밋하지 않았다.** `git add`·`git commit` 미실행(플랜 frontmatter `no_commit: true`, 결정 'D-18 커밋 없음'(.planning/phases/02-track-a/02-CONTEXT.md)). `git diff --stat -- scripts data tests/data/test_millie_catalog.py tests/data/test_millie_edges.py src/millie_rec/serving src/millie_rec/app` 에 보이는 변경은 전부 형제 Worker Plan 03-01 과 기존 세션의 것이며 이 플랜의 변경은 위 표 6파일뿐이다.
