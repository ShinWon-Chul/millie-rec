---
phase: 04-freeze
plan: 04
status: complete
executed_by: Advisor(오케스트레이터 세션 직접 — app/·serving/api.py 배선은 Advisor 전용 영역)
executed_at: 2026-09-06
commits: 0   # no_commit — 작업 트리에 남긴다(사용자 지시 2026-09-05)
requirements: [REC-01, REC-02, REC-03]
key-files:
  created:
    - src/millie_rec/app/pipeline_kr.py
    - tests/app/test_variants.py
    - tests/serving/test_api_weights.py
  modified:
    - src/millie_rec/app/pipeline.py
    - src/millie_rec/app/cli.py
    - src/millie_rec/app/server.py
    - src/millie_rec/serving/api.py
    - src/millie_rec/data/vectors_kr.py
    - tests/app/test_pipeline.py
    - tests/app/test_cli.py
    - tests/app/test_server_catalog.py
    - tests/data/test_vectors_kr.py
---

# Plan 04-04 SUMMARY — 조립: 4 variant dict · create_app(weights=) · Track B 파이프라인

## 한 줄
wave 1 세 슬라이스를 `app/` 이 `contracts.VARIANTS` 4종 dict 로 잇고, 서버가 `state_weights` 를 파이프라인과 응답 양쪽에 주입해 `user_state_weights` β=0(REC-03) 을 낸다. 전역 320 passed(기준선 255 → wave 1 후 314 → 320), `make smoke` PASS, 커밋 0.

## Wave 1 게이트(Task 1 시작 전 1회)
| 명령 | 결과 |
|---|---|
| SUMMARY 3파일 | 존재(04-01·02·03) |
| `uv run ruff format --check . && uv run ruff check .` | 클린 |
| `uv run pytest --no-header` | `314 passed, 1 failed`(255 + 54 + 이 플랜 Task 1 선행 5 — `test_coverage_gate` 만 RED, 재수집 중 의도) |
| `make smoke` | PASS |
| scipy/sklearn/pandas 지연 import | `False False False` |

## Task 별 RED → GREEN
- **Task 1** `tests/serving/test_api_weights.py` 4건 + `tests/data/test_vectors_kr.py::test_book_ids_lists_npz_order`: 스텁(시그니처만·`book_ids → []`) 후 RED = `AssertionError` 4건(`{'alpha': 0.0…} == {'alpha': 1.0…}` · `[] == [(7, 8)]` · `0 == 3` · `[] == [1..20]`) → GREEN `tests/serving`+`test_vectors_kr`+아키텍처 33 passed. `api.py` 135→150줄(상한 정확히), `vectors_kr.py` 38→44줄.
- **Task 2** `tests/app/test_pipeline.py`(갱신 2 + 신규 1)·`test_cli.py`(갱신 3): 뼈대(`StagedPipeline.recommend → []`·`fit_pipelines → {pop}`) 후 RED = `AssertionError: assert {'pop'} == {'cf','hybrid','hybrid_div','pop'}` → GREEN 14 passed(+아키텍처). `pipeline.py` 110→149줄(`CatalogPopPipeline` 을 `pipeline_kr.py` 로 이동), `pipeline_kr.py` 123줄, `cli.py` 128→133줄.
- **Task 3** `tests/app/test_variants.py` 5건 + `test_server_catalog.py` 갱신: RED = `test_user_state_weights_beta_zero_for_seeds_only_user` 만 `AssertionError`(fixture 손계산 pop/cf/가드 4건은 Task 2 만으로 이미 성립) → `server.py` `weights=state_weights` 2곳 → GREEN.

## 전역 게이트(Task 3-d)
`uv run ruff format . && uv run ruff check .` 클린 · `uv run pytest --no-header` **320 passed, 1 failed**(`tests/data/test_millie_catalog.py::test_coverage_gate` 만) · `make smoke` PASS · 실 스냅샷 `build_pipelines(catalog=load_catalog(), weights=state_weights)` → `['cf', 'hybrid', 'hybrid_div', 'pop']` · `import millie_rec.app.server` 예외 없음.

## 줄 수
| 파일 | 이전 | 이후 |
|---|---|---|
| `app/pipeline.py` | 110 | 149 |
| `app/pipeline_kr.py` | — | 123 |
| `app/cli.py` | 128 | 133 |
| `app/server.py` | 23 | 26 |
| `serving/api.py` | 135 | 150 |
| `data/vectors_kr.py` | 38 | 44 |

## 기존 테스트 갱신(의도된 변경, 04-CONTEXT D-15 예외 · 플랜 Advisor 확정 5)
| 파일 | 이전 단정 | 이후 | 이유 |
|---|---|---|---|
| `tests/app/test_pipeline.py` `test_fit_pipelines_…` | `set(pipes) == {"pop"}` | `== set(VARIANTS)` + 4 variant 각 k=5·seen 미포함·position | fit_pipelines 가 4종 |
| `tests/app/test_pipeline.py` `test_build_pipelines_with_catalog_…` | — | `load_vectors_kr` monkeypatch(None) 추가 | 벡터 없음 → pop 만 경로 고정 |
| `tests/app/test_cli.py` e2e | `len(states) == 3` · latest 1행 | `len(states) == 9` · latest 5행 · knn npz 존재 | 4 variant × 2 상태 |
| `tests/app/test_cli.py` `test_eval_unregistered_variant_exits` | `--variant cf` → SystemExit | 이름 변경 + `--variant nope`(argparse choices) | cf 가 등록됨 |
| `tests/app/test_server_catalog.py` | 기본 요청 → `pop_v1` | `model=pop` 명시 + `load_vectors_kr` fixture 패치 | 기본 variant 가 `hybrid_div` 로 자동 이동(D-11) |

## fixture 손계산 vs 실측(20권 `millie_serving_sample`, seeds 1,2,3, k=10)
pop `[4..13]` ✓ · cf `[4, 5, 6, 7, 8]` ✓ · `7 ∈ hybrid` ✓ · `7 ∉ hybrid_div`(가드) ✓ · 4 variant 집합 pairwise 상이 ✓ · 18·19·20 없음 ✓ · `hybrid_div` 첫 title `밀리 표본 도서 …` ✓ · `user_state_weights == {1.0, 0.0, 0.0}` ✓.

## Plan 04-05 인계
- `make eval` 첫 실행 — `artifacts/item_neighbors.npz` 없음(캐시 무효화 불필요). `load_or_fit_itemknn` 은 meta(train 행·유저·아이템 수) 불일치 시 자동 refit.
- `cli demo` 가 쓸 시그니처: `build_pipelines_kr(catalog: CatalogKR, *, weights=None, vectors=None) -> dict[str, Pipeline]`(vectors None 이면 `load_vectors_kr()` 시도) · `load_vectors_kr(serving_dir=DIR_SERVING) -> VectorsKR | None` · `load_catalog(serving_dir) -> CatalogKR | None`.
- 실 스냅샷(재수집 후 `make millie` 미실행 상태, books 9,450·vectors 8,708)에서 4 variant 등록됨 — **판정은 Plan 04-06 최종 스냅샷 뒤**.

## Deviation
- 플랜의 verbatim docstring 여러 줄이 ruff E501(CJK 폭 2) 위반 → 의미 유지하며 축약. `WithMeta.recommend` 를 한 줄 comprehension 대신 루프로(가독성·줄 폭).
- Task 1 을 wave 1 실행 중에 선행(wave 1 결과와 파일 교집합 0) — 전역 카운트가 플랜 예상 309 대신 314 로 시작.

커밋하지 않는다 — 작업 트리에 남기고 SUMMARY 에 변경 파일 목록을 적는다.
