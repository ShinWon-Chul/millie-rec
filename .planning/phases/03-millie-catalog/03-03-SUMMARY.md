---
phase: 03-millie-catalog
plan: 03
subsystem: data
tags: [tfidf, content-sim, gate, tdd]
requires:
  - phase: 03-millie-catalog
    provides: books_kr.parquet 6,977권 (Plan 03-01)
provides:
  - data/processed/item_edges_kr.parquet — 260,236 엣지 (content_sim 125,454 · category_best 134,782)
  - results/millie_edges_gate.json — 이웃 게이트 3 실측 정본
affects: [03-04 export_millie_serving, 03-05 export_millie_vectors, Plan 06 최종 재빌드]
tech-stack:
  added: []
  patterns:
    - "실데이터 게이트 테스트가 수치를 results/ 에 직접 쓴다 — 기록은 단언보다 먼저(미달이어도 수치가 남는다)"
key-files:
  created:
    - results/millie_edges_gate.json
    - data/processed/item_edges_kr.parquet
  modified:
    - tests/data/test_millie_edges.py
key-decisions:
  - "게이트 ③ 통과(0.3738 ≤ 0.70) — 결정 D-10 '③ 미달 조치는 description 가중 상향만'(.planning/phases/03-millie-catalog/03-CONTEXT.md) 발동 없음. scripts/build_millie_edges.py 무변경"
status: complete
commits: 0
---

# Plan 03-03 SUMMARY — content_sim 이웃 실측·게이트 3

**`scripts/build_millie_edges.py` 는 변경하지 않았다** — 게이트 3개가 첫 시도에 전부 통과했고,
결정 D-10 의 `DESC_REPEAT` 조치는 발동하지 않았다(형제 Plan 03-04·03-05 의 `_load("build_millie_edges")` 회귀 없음).

## 변경 파일

| 경로 | 상태 | 내용 |
|---|---|---|
| `tests/data/test_millie_edges.py` | M `28+/1-` | `import json` · `from datetime import UTC, datetime` · `GATE_JSON` 상수 · docstring 1줄 · `test_neighbour_quality_gate` 에 기록 블록(단언 앞) + `orphans` 줄 재배치 |
| `results/millie_edges_gate.json` | NEW | 게이트 3 실측 정본(테스트가 씀) |
| `data/processed/item_edges_kr.parquet` | NEW | gitignore — 첫 스냅샷 이웃 260,236행 |
| `scripts/build_millie_edges.py` | **무변경** | `git diff --stat` 빈 출력 |

## Task 1 — 기록 추가, 단언 불변

```
uv run ruff format tests/data/test_millie_edges.py   → 1 file reformatted
uv run ruff check  tests/data/test_millie_edges.py   → All checks passed!
git diff --numstat tests/data/test_millie_edges.py   → 28  1  (삭제 1 = orphans 줄 재배치)
uv run pytest tests/data/test_millie_edges.py --no-header
..........s                                                              [100%]
10 passed, 1 skipped in 0.95s
```

| grep | 기준 | 실측 |
|---|---|---|
| `GATE_JSON` | ≥3 | 3 |
| `millie_edges_gate.json` | ≥1 | 2 |
| `same_category_share` | ≥1 | 6 |
| `assert share <= MAX_SAME_CATEGORY_SHARE` | 1 | 1 |
| `assert not orphans` | 1 | 1 |
| `assert thin.empty` | (1 gate + 1 합성) | 2 — 변경 전 `git show HEAD:` 도 2, 불변 |

기록 블록은 `share` 계산·print 직후, 단언 4문장 **앞**에 있다(③ 미달이어도 json 이 남아야 D-10 보고가 가능).

## Task 2 — 실빌드·실측

### 2-a 사전 (books_kr.parquet)

```
rows 6977 · description_na 0.0265 · curator_note_notna 0.0032 · categories_na 0.0
```

Plan 03-01 스냅샷(`_n_records` 6977)과 일치. `data/raw/millie_pages.jsonl` 은 빌드 시점 7,110줄
(배치가 계속 append 중, 마지막 줄 JSON 유효 — `read_best_links` 의 `JSONDecodeError` 미발생).
카탈로그(6,977) 밖 millie_id 의 best_links 는 `id_of.get` None 으로 버려진다(T-03-11 mitigation 실데이터 재확인).

### 2-b 빌드 출력 원문

```
edges=260236 {'category_best': 134782, 'content_sim': 125454} → /Users/shinwonchul/Documents/신원철/밀리의서재/millie-rec/data/processed/item_edges_kr.parquet
        9.41 real         8.27 user         0.73 sys
          1300217856  maximum resident set size
```

**peak RSS 1,300,217,856 B ≈ 1.24 GB · 9.41 s.** 플랜 2-b 의 중단 기준(RSS > 2GB)·`MemoryError` 미발생.
architect 추정(6,977² float64 dense ≈ 390MB + `np.argsort` 2회) 범위 안이다.
Plan 06 최종 재빌드에서 카탈로그가 9천 권을 넘으면 같은 배수로 ≈2.1GB 가 되어 기준에 닿는다 —
`sim.astype(np.float32)` + `order` 1회 계산(현재 `_content_pairs`·`_top_up` 이 각각 argsort) 같은 최소 변경은 별도 브리프 몫(이 플랜 범위 밖).

content_sim 이 6,977×20 = 139,540 이 아니라 125,454 인 이유: `_merge` 가 동률·열세 content 쌍을
가중 0.2 의 `category_best` 로 넘기고(겹치는 쌍은 큰 가중 우선), cosine ≤0 쌍은 버리기 때문이다.

### 2-c 게이트 실측 — 3개 전부 통과

```
uv run pytest tests/data/test_millie_edges.py::test_neighbour_quality_gate --no-header -s
top-20 동일 카테고리 비율 평균 0.374 (기준 ≤0.7)
.
1 passed in 0.89s
```

`results/millie_edges_gate.json` 전문:

```json
{
  "generated_at": "2026-09-05T09:53:37+00:00",
  "n_books": 6977,
  "n_edges": 260236,
  "sources": {
    "category_best": 134782,
    "content_sim": 125454
  },
  "self_edges": 0,
  "min_degree": 21,
  "n_orphans": 0,
  "same_category_share": 0.3738,
  "max_same_category_share": 0.7
}
```

| 게이트 | 기준 | 실측 | 판정 |
|---|---|---|---|
| ① self-edge | 0 | 0 | 통과 |
| ② 전 도서 이웃 | ≥5 | min_degree **21** · orphans 0 | 통과 |
| ③ top-20 동일 카테고리 비율 | ≤0.70 | **0.3738** | 통과 (여유 0.33) |

**조치: 무변경.** `DESC_REPEAT` 상수를 만들지 않았다(결정 D-10 — 통과하면 코드를 건드리지 않는다).
`git diff --stat scripts/build_millie_edges.py` 빈 출력.

### 2-d 이웃 sanity (정성 미리보기, 숫자 아님)

첫 책 `위쳐 : 이성의 목소리`(소설)의 상위 5 이웃:

| 이웃 | weight | source |
|---|---|---|
| 위쳐 1 : 엘프의 피 | 0.601 | content_sim |
| 위쳐 : 운명의 검 | 0.2 | category_best |
| 위쳐 2 : 경멸의 시간 - 상 | 0.2 | category_best |
| 위쳐 2 : 경멸의 시간 - 하 | 0.2 | category_best |
| 위쳐 3 : 불의 세례 - 상 | 0.2 | category_best |

같은 시리즈가 붙는다 — 제목 문자 2~4gram 이 지배적이다. 동일 카테고리 비율 0.374 는
분야 편중이 아니라 시리즈·주제 근접으로 설명된다.

### 2-e 마무리

```
uv run pytest tests/data/test_millie_catalog.py tests/data/test_millie_edges.py --no-header
.............................                                            [100%]
29 passed in 2.02s
```

failed 0 · **skipped 0**(두 실데이터 게이트가 이제 전부 돈다).

```
git status --short -- tests/data/test_millie_edges.py results/ scripts/build_millie_edges.py data/processed/item_edges_kr.parquet
 M tests/data/test_millie_edges.py
?? results/millie_edges_gate.json
```
(다른 `results/*` 항목은 Phase 2·Plan 03-01 산출로 내 변경이 아니다. `item_edges_kr.parquet` 은 gitignore 라 뜨지 않는다.)

## 후속 플랜에 넘기는 관측 (내 범위 밖, 수정하지 않음)

1. **실데이터 content_sim 최대 weight = 1.0000000000000095** (float 오차, 텍스트가 동일한 중복 도서 존재).
   합성 픽스처 테스트 `test_content_sim_weights_are_cosine_scores` 의 `max() <= 1.0` 은 합성 데이터라 통과하지만,
   Plan 03-04 export·`serving/schemas.py` 가 weight 에 `le=1.0` 같은 상한을 두면 실데이터에서 걸린다.
2. **`min_degree` 21** — `_top_up`(≥5)이 한 번도 필요하지 않았다. category_best 보험(D-09)이 실효적으로 두껍다.
3. 배치가 계속 돌아 jsonl 은 7,110줄이지만 카탈로그는 6,977권이다. Plan 06 최종 재빌드 때 두 수치가 다시 벌어진다.

## 커밋

**커밋하지 않았다.** `git log --oneline | head -1` = `8e5172b chore: project scaffold — contracts freeze, serving schemas, demo mock, GSD planning docs`(착수 시점과 동일).
