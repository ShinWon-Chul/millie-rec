---
phase: 03-millie-catalog
plan: 01
subsystem: data
tags: [pandas, numpy, tdd, coverage-gate, difficulty]
requires:
  - phase: 01-local-serving-skeleton
    provides: contracts.py (DIR_PROCESSED·DIR_RAW·FILE_ID_MAP)
provides:
  - scripts/millie_difficulty.py — add_difficulty(df) → resid_z·len_z·difficulty
  - 유효 레코드 정의(D-05)·카운터·D-17 id 부여 범위 in scripts/build_millie_catalog.py
  - 첫 스냅샷 books_kr.parquet 6,977권 + results/millie_coverage.csv (게이트 통과)
affects: [03-02 catalog_kr 어댑터, build_millie_edges 실측, export_millie_serving]
tech-stack:
  added: []
  patterns:
    - "scripts 간 import: sys.path.insert(SCRIPTS_DIR) + import x  # noqa: E402 (importlib 로드 경로에서도 동작)"
    - "난이도 파생은 build_frame 결과 DataFrame 을 받는 순수 df→df 함수 1개"
key-files:
  created:
    - scripts/millie_difficulty.py
    - tests/data/test_millie_difficulty.py
    - results/millie_coverage.csv
  modified:
    - scripts/build_millie_catalog.py
    - tests/data/test_millie_catalog.py
    - data/id_map.csv
key-decisions:
  - "소표본 분야(측정 표본 <20)의 기대값 셀 = (_global, 전역 분위) — 분야 자체 셀을 쓰면 3권 분야 잔차가 전부 0 이 되어 σ(0)=0.5 로 뭉친다"
  - "n_lines 는 badline 포함 비어 있지 않은 줄 수(기존 의미 유지), titleless_ratio 는 read_records 가 계산해 meta 로 넘긴다"
status: complete
commits: 0
---

# Plan 03-01 SUMMARY — 카탈로그 빌더 마감

결정 D-01·D-05·D-06·D-16·D-17(`.planning/phases/03-millie-catalog/03-CONTEXT.md`)을 TDD 한 사이클로 이행했다.
커버리지 게이트 미달 항목 0 · 파서 미스 비율 0.000143(상한 0.005) — `## CHECKPOINT REACHED` 없음.

## 변경 파일

| 경로 | 상태 | 내용 |
|---|---|---|
| `scripts/millie_difficulty.py` | NEW 81줄 | `add_difficulty(df)` + `_category`·`_bins`·`_zscore`, 상수 7개. `millie_rec` import 0 |
| `scripts/build_millie_catalog.py` | M `35+/9-` | `sys.path`+`import millie_difficulty` · `MAX_TITLELESS_RATIO = 0.005` · COLUMNS 3컬럼 · `read_records` 유효 레코드/카운터/JSONDecodeError · `assign_ids` D-17 필터 · `build_frame` 난이도 호출 · `coverage` `**meta` · `main` 출력 |
| `tests/data/test_millie_difficulty.py` | NEW 104줄 | 손계산 테스트 6건 |
| `tests/data/test_millie_catalog.py` | M | EXPECTED_COLUMNS 3컬럼 삽입 · 카운터 단정 3줄 · 신규 테스트 3건 · 게이트 csv 3행 + titleless 비율 단언 (기존 단정 수정·삭제 0) |
| `data/id_map.csv` | M `5913+/0-` | append-only 신규 5,913행 |
| `data/processed/books_kr.parquet` · `millie_raw_coverage.json` | NEW | gitignore |
| `results/millie_coverage.csv` | NEW | 게이트 실측 |

## Task 1 (RED) — 11 failed, 12 passed, 1 skipped

`uv run pytest tests/data/test_millie_difficulty.py tests/data/test_millie_catalog.py --no-header`

```
E       AssertionError: assert {'book_id', '...expected_min'} == {'book_id', '...ted_min', ...}
E         Extra items in the right set: 'difficulty' 'resid_z' 'len_z'
E       AssertionError: assert 'resid_z' in Index(['book_id', 'categories', 'completion_prob', ...
E       AssertionError: assert 'difficulty' in Index([...])
E       AssertionError: assert 'len_z' in Index([...])
E       AssertionError: assert ['book_id', '...blisher', ...] == ['book_id', '...blisher', ...]
E         At index 27 diff: 'difficulty_source' != 'resid_z'
E       AssertionError: assert None == 12
E        +  where None = <built-in method get of dict object ...>('n_success')
E       AssertionError: assert {'difficulty'...z', 'resid_z'} <= {'authors', '...avg_min', ...}
E       assert 14 == 12   # 유효 레코드 필터 없음 → 껍데기·파서 미스가 카탈로그 행이 됨
E       AssertionError: assert 'ffffffff00000003' not in {'0f1e2d3c4b5a6001', ...}
11 failed, 12 passed, 1 skipped in 0.30s
```

`ImportError`·`ModuleNotFoundError`·`SyntaxError`·`NameError` 0건.
최초 실행에서 `test_derived_difficulty_columns_in_built_frame` 만 `KeyError: 'resid_z'` 로 떨어져,
플랜 Task 1-d 대로 `assert {"resid_z","len_z","difficulty"} <= set(df.columns)` 를 앞에 두어 AssertionError 로 바꿨다.

## Task 2 (GREEN)

```
uv run pytest tests/data/test_millie_difficulty.py tests/data/test_millie_catalog.py tests/data/test_millie_edges.py --no-header
.......................s..........s                                      [100%]
33 passed, 2 skipped in 1.18s
```

`uv run ruff format` + `uv run ruff check` (자기 4파일) → `All checks passed!`

acceptance_criteria:

| 항목 | 기준 | 실측 |
|---|---|---|
| `wc -l scripts/millie_difficulty.py` | ≤150 | **81** |
| `git diff --numstat scripts/build_millie_catalog.py` | 추가 ≤35 · 삭제 ≤10 | **35 / 9** |
| `grep -c "MAX_TITLELESS_RATIO = 0.005"` | 1 | 1 |
| `grep -c "millie_difficulty.add_difficulty(df)"` | 1 | 1 |
| `grep -c "n_skipped_titleless"` (스크립트) | ≥2 | 2 |
| `grep -o "resid_z len_z difficulty difficulty_source" \| wc -l` | 1 | 1 |
| `grep -c "millie_rec\."` (difficulty) | 0 | 0 |
| `grep -c "millie_rec.serving\|app\|data"` (catalog) | 0 | 0 |
| `grep -c "def test_"` difficulty / catalog | 6 / 18 | 6 / 18 |
| `grep -c "_n_skipped_titleless"` / `"0.005"` (테스트) | ≥1 / ≥1 | 1 / 1 |

## Task 3 (실측)

빌드 출력 원문:

```
books=6977 → /Users/shinwonchul/Documents/신원철/밀리의서재/millie-rec/data/processed/books_kr.parquet · id_map → /Users/shinwonchul/Documents/신원철/밀리의서재/millie-rec/data/id_map.csv empty=5 titleless=1
uv run python scripts/build_millie_catalog.py  0.55s user 0.13s system 76% cpu 0.895 total
```

id_map append-only (T-03-01 mitigation):

```
git diff --numstat data/id_map.csv   →  5913	0	data/id_map.csv
diff <(head -1067 data/id_map.csv) $SCRATCH/id_map.before.csv   →  (빈 출력)
id_map ok 6979        # book_id·millie_id unique, 1..6979 연속
```

parquet 확인: 행 **6,977** · 앞 9컬럼 계약 순서 일치 · `book_format` = `['전자책','챗북','오디오북']` ·
`difficulty` 보유율 **0.848** · `len_z` 보유율 0.848 · `difficulty ∈ [0,1]` True ·
컬럼 순서 `millie_label → resid_z → len_z → difficulty → difficulty_source → seg_dist`.

`uv run pytest tests/data/test_millie_catalog.py::test_coverage_gate --no-header -s` → **1 passed**

```
average_rating 보유율 0.282 (임계값 없음, PDF 각주용)
카테고리 28종 · 20권 이상 23종
```

`results/millie_coverage.csv` 전문:

```
field,non_null_ratio
authors,1.0000
average_rating,0.2825
best_category,1.0000
categories,1.0000
category_avg_min,0.8476
category_avg_prob,0.8469
completion_prob,0.8476
curator_note,0.0032
description,0.9735
expected_min,0.8476
formats,0.9852
image_url,1.0000
millie_label,0.8476
pub_date,0.9895
publisher,1.0000
review_count,0.9950
seg_dist,0.8180
shelf_count,1.0000
subtitle,0.6835
title,1.0000
top_segment,0.8180
_n_records,6977
_category_distinct,28
_categories_ge_20,23
_n_skipped_empty,5
_n_skipped_titleless,1
_n_success,6983
```

게이트 표(적재 계획 02 §7 커버리지 게이트 표) 대비 **미달 항목 0** —
title 1.0000 / image_url 1.0000(≥0.99) / categories 1.0000(≥0.95) / completion_prob 0.8476(≥0.70) /
formats 0.9852(≥0.90) / seg_dist 0.8180(≥0.70) / 카테고리 28종(≥8)·20권 이상 23종(≥6).
파서 미스 비율 1/6,983 = 0.000143 ≤ 0.005(결정 D-06). §7 조치 발동 없음.

마무리: `uv run pytest tests/data/test_millie_difficulty.py tests/data/test_millie_catalog.py --no-header` → **24 passed**(게이트가 이제 실행되어 skip 0).
`git status --short | grep -c "data/processed"` → **0**(gitignore).

## 판단이 필요했던 지점

1. **소표본 분야의 기대값 셀** — 플랜이 남긴 Claude's Discretion. 측정 표본 <20 인 분야는 `(_global, 전역 expected_min 분위)` 셀을 쓴다. 분야 자체 셀을 쓰면 3권 분야의 잔차가 전부 0 → `σ(0)=0.5` 로 뭉친다. `_zscore` 는 분야 표본 <5 이면 전역 std 를 쓰되 평균은 분야 평균을 유지한다.
2. **`coverage()` 의 카운터 전달 방식** — 키를 하나씩 옮기지 않고 `**meta` 로 싣고 `titleless_ratio` 는 `read_records` 가 계산한다. 순증 상한(추가 ≤35줄) 안에 들어가면서 카운터의 단일 출처를 유지한다.
3. **RED 를 AssertionError 로 만들기** — `_row(df, ...)["resid_z"]` 가 KeyError 를 먼저 냈다. 컬럼 존재 단정을 앞세워 해결(플랜 1-d).

## 형제 Worker 관련 관측 (내 변경 아님)

`git status --short` 에 `src/millie_rec/**`·`tests/conftest.py`·`scripts/collect_millie.py`·`.planning/**` 변경이 보인다.
Phase 1·2 의 미커밋 작업(결정 'D-18 커밋 없음'(`.planning/phases/02-track-a/02-CONTEXT.md`))과
동시 실행 중인 Plan 03-02 Worker(`data/catalog_kr.py`·`vectors_kr.py`)의 것이다.
플랜 acceptance_criteria 의 `git diff --stat -- ... src` 빈 출력 조건은 이 동시 작업 때문에 만족되지 않지만,
`tests/fixtures`·`scripts/build_millie_edges.py`·`scripts/export_millie_serving.py`·`scripts/millie_parse.py` 는 변경 0 이다.
`tests/conftest.py` import 오류는 한 번도 발생하지 않았다.

must_not_touch 중 `Makefile`·`pyproject.toml`·`CLAUDE.md`·`.planning/ROADMAP.md`·`.planning/STATE.md` 도 작업 트리에 변경이 있으나 mtime 이 전부 이 세션 첫 쓰기(18:38) 이전이다 — Advisor·이전 페이즈의 것이며 이 Worker 는 건드리지 않았다.

## 커밋

**커밋하지 않는다.** `git log --oneline | head -1` = `8e5172b chore: project scaffold …` (착수 시점과 동일).
