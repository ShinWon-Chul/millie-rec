---
phase: 04-freeze
plan: 01
subsystem: retrieval
tags: [retrieval, itemknn, content, neighbors, tdd, REC-01]
requires: [contracts.UserState, contracts.Candidate, contracts.CandidateGenerator, contracts.ItemVectors, contracts.Neighbors]
provides:
  - "millie_rec.retrieval.ItemKNNRetriever (CandidateGenerator + Neighbors)"
  - "millie_rec.retrieval.NeighborRetriever (Track B cf 채널 어댑터, source=content)"
  - "millie_rec.retrieval.VectorRetriever (Track B content 채널, ItemVectors 위 dense top-k)"
  - "millie_rec.retrieval.ContentVectors.retrieve (성분별 TF-IDF 평균 벡터 cosine)"
  - "millie_rec.retrieval.retrieve_from_neighbors (두 트랙 공용 이웃→후보 함수)"
  - "millie_rec.retrieval.load_or_fit_itemknn (npz 캐시 meta 무효화)"
affects: [app/pipeline.py, app/pipeline_kr.py, app/cli.py]
tech-stack:
  added: []
  patterns: ["scipy.sparse chunked top-k", "npz 캐시 meta 무효화", "성분 가중 Callable 주입"]
key-files:
  created:
    - src/millie_rec/retrieval/neighbors.py
    - src/millie_rec/retrieval/itemknn.py
    - tests/retrieval/test_neighbors.py
    - tests/retrieval/test_itemknn.py
  modified:
    - src/millie_rec/retrieval/content.py
    - src/millie_rec/retrieval/__init__.py
    - tests/retrieval/test_content.py
decisions: [D-01, D-04, D-10, D-14, D-15]
metrics:
  duration: "약 25분"
  completed: 2026-09-06
  tasks: 3
  files: 7
---

# Phase 4 Plan 01: 후보 3통로 완성 (retrieval) Summary

**한 줄:** scipy.sparse 이진 user×item cosine Item-KNN(이웃 50 · chunked top-k · npz meta 캐시) + 성분별 TF-IDF 평균 벡터 content 후보 + 두 트랙이 공유하는 단일 이웃→후보 함수 `retrieve_from_neighbors` 를 TDD 한 사이클로 만들었다. `tests/retrieval` 31건 + 아키텍처 3건 = 34 passed, 커밋 0.

커밋하지 않는다 — 작업 트리에 남기고 SUMMARY 에 변경 파일 목록을 적는다(`no_commit: true`, 사용자 지시 2026-09-05).

## Task 1 (RED) — 스텁 3파일 + 테스트 3파일

스텁은 Task 2 와 **같은 시그니처**로 두고 값만 틀리게 했다(`NeighborRetriever.name = "neighbor"`, `VectorRetriever.name = "vector"`, 모든 `retrieve` 가 `[]`). 모듈·메서드가 없어 생기는 `ModuleNotFoundError`·`AttributeError` 를 피해 정직한 RED 를 만들기 위한 것이다.

**요약 줄:** `15 failed, 9 passed in 0.83s`
(`uv run pytest tests/retrieval/test_neighbors.py tests/retrieval/test_itemknn.py tests/retrieval/test_content.py --no-header`)

failed 15건 = test_neighbors 5 + test_itemknn 7 + test_content 3. passed 9건 = 기존 `test_content.py` 4건(수정 없이 유지) + 스텁 반환값 `[]`·`fit(self, train)` 시그니처로 우연히 통과한 신규 5건(`test_seen_never_returned`, `test_retrieve_unknown_seed_or_empty_user_gives_empty`, `test_retrieve_never_returns_seen`, `test_fit_takes_only_train_and_seen_items_never_returned`, `test_fit_is_noop_returning_self`). 플랜 예상은 `18 failed, 6 passed` 였고 실측은 15/9 — 판정 기준(플랜 acceptance 명시)인 "failed 사유가 전부 AssertionError 계열" 은 충족했다.

**AssertionError 발췌 6건:**

```
FAILED tests/retrieval/test_neighbors.py::test_neighbor_retriever_name_and_source
E       AssertionError: assert 'neighbor' == 'content'
E         - content
E         + neighbor

FAILED tests/retrieval/test_neighbors.py::test_retrieve_from_neighbors_returns_content_candidates_sorted
E       assert [] == [2, 3]
E         Right contains 2 more items, first extra item: 2

FAILED tests/retrieval/test_neighbors.py::test_history_component_adds_to_score_when_weights_none
E       assert [] == [3]
E         Right contains one more item: 3

FAILED tests/retrieval/test_neighbors.py::test_k_limits_and_no_neighbors_gives_empty
E       assert 0 == 1
E        +  where 0 = len([])
E        +    where [] = retrieve_from_neighbors(<_Nbrs object>, UserState(user_id=None,
E                        explicit_seeds=(1,), history=(), session=(), context={}), k=1)

FAILED tests/retrieval/test_content.py::test_retrieve_weights_zero_history_component
E       assert [] == [20]
E         Right contains one more item: 20

FAILED tests/retrieval/test_content.py::test_vector_retriever_matches_content_retrieve
E       AssertionError: assert 'vector' == 'content'
E         - content
E         + vector
```

**비-AssertionError 부재 검증:** RED 출력 전체에 대해
`grep -nE "ImportError|ModuleNotFoundError|AttributeError|TypeError|SyntaxError|NameError|IndexError|KeyError"` → `NONE`.
`AssertionError` 문자열은 18회 등장했다. 아키텍처 테스트는 스텁 단계에서도 `3 passed`.

`uv run pytest tests/test_architecture.py --no-header` → `3 passed in 0.02s`

## Task 2 (GREEN) — 구현

**요약 줄:** `34 passed in 0.79s`
(`uv run pytest tests/retrieval tests/test_architecture.py --no-header`, failed 0)

**`src/millie_rec/retrieval/neighbors.py` (80줄, 신규)**
- `SOURCE_CONTENT="content"` · `DEFAULT_WEIGHTS={alpha,beta,gamma: 1.0}` · `N_NEIGHBORS=20` · `WeightFn = Callable[[UserState], dict[str, float]]`.
- `component_weights(user, weights)` — `weights` 가 `None` 이면 세 성분 전부 1.0(retrieval 은 ranking 을 import 할 수 없으므로 α/β/γ 는 Callable 주입, 결정 D-01).
- `weighted_items(user, w)` — seeds→alpha, history→beta, session→gamma 를 `(book_id, 가중치)` 목록으로.
- `retrieve_from_neighbors(nbrs, user, k, *, source, weights, n_neighbors)` — `Σ w_성분 · sim`, `user.seen` 제외, `(−score, book_id)` 정렬 상위 k. **Track A·Track B 이웃→후보의 유일한 구현.**
- `NeighborRetriever` — 임의의 `contracts.Neighbors` 를 감싼 `CandidateGenerator`. `name = "content"`, 기본 `source="content"`(`.claude/rules/data.md`: Track B 는 `itemknn` 이라 쓰지 않는다).

**`src/millie_rec/retrieval/itemknn.py` (149줄, 신규)**
- 상수 값 = 결정 D-04(04-CONTEXT.md, 후보 통로 세부)와 문자 단위 일치: `SOURCE_ITEMKNN="itemknn"` · `KNN_TOP=50` · `POOL=200` · `CHUNK=500` · `ARTIFACT_NAME="item_neighbors.npz"` · `KNN_ARTIFACT=DIR_ARTIFACTS/ARTIFACT_NAME`.
- `fit(train)` — train 1인자. `np.unique` 로 user/item 인덱싱 → `scipy.sparse.csr_matrix` 이진화(`x.data[:] = 1.0`) → 열 L2 정규화 → `CHUNK=500` 블록마다 `(chunk, n_items)` dense cosine 한 장(40MB)만 만들고 `argpartition` 상위 `top=min(KNN_TOP, n-1)` → `sims > 0` 만 이웃으로 유지(공동 소비 0 은 이웃 아님). `import scipy.sparse as sp` 는 **함수 안**(파일 59행) — 서버가 공개 표면을 읽어도 scipy 를 끌어오지 않는다.
- `neighbors(book_id, n)` — `contracts.Neighbors` 도 만족. 패딩 `-1` 제외, fit 이 이미 sim 내림차순 저장. 미지 id·이웃 없음은 `[]`.
- `retrieve(user, k)` — `retrieve_from_neighbors(self, user, k, source=SOURCE_ITEMKNN, weights=self._weights, n_neighbors=KNN_TOP)` 한 줄. 후보 생성 로직 중복 0.
- `save/load` — npz 4키 `book_ids · nbr_ids · nbr_sims · meta`. `np.load` 는 `allow_pickle` 기본 False 유지(위협 T-04-01).
- `load_or_fit_itemknn(train, path, *, weights)` — 캐시 `meta`(train 행 수·유저 수·아이템 수)가 일치할 때만 로드, 불일치면 `log.info` 후 재fit, 읽기 실패(`OSError·ValueError·KeyError`)면 `log.exception` 후 재fit. `path=None` 이면 저장하지 않는다(위협 T-04-06 재현성).

**손계산 검증 결과 — 전부 맞았다.** `_train()`(u1={1,2,3} u2={1,2} u3={4}, 평점 1~5 혼합)에서 아이템 벡터는 1:{u1,u2} 2:{u1,u2} 3:{u1} 4:{u3}. 구현 실측이 `cos(1,2)=1.0`, `cos(1,3)=cos(2,3)=0.7071`, 4 는 이웃 없음, seeds(1,)+history(2,) 의 3 점수 `1.4142`, β=0 주입 시 `0.7071` 로 테스트 기대값(`pytest.approx(abs=1e-3)`)과 일치. npz `meta == [6, 3, 4]`, `nbr_ids.shape == (4, 50)`, 라운드트립 후 `retrieve` 결과 동일.

**`src/millie_rec/retrieval/content.py` (131줄, 증분)**
- 기존 `ContentVectors.__init__`·`dim`·`vectors` 본문은 그대로. 위치 인자 `books, text_col` 불변, `weights` 는 keyword-only 추가. 기존 테스트 4건 무수정 통과.
- 모듈 함수 2개를 두 클래스가 공유(이중 구현 금지): `_query(vectors, user, weights)` = `Σ_성분 w · mean(성분 아이템 벡터)`(미지 id 는 0 벡터라 자연히 빠지고, 성분 전부 비면 0 벡터) · `_topk_cosine(scores, ids, seen, k, source)` = 점수 > 0 이고 seen 아닌 상위 k, `argpartition` 크기 `k + len(seen)`, `np.lexsort` 로 `(−score, id)` 결정적 정렬.
- `ContentVectors`: `name="content"`, `fit(train)` no-op(`self` 반환 — Protocol·하네스 대칭), `retrieve` = `self._matrix @ q` 후 `_topk_cosine`.
- `VectorRetriever(vectors, ids, *, source, weights)`: 생성 시 dense 행렬 1회, `retrieve` 는 `self._matrix @ q`. `ids=[]` 면 `[]`. `name="content"`.

## Task 3 (REFACTOR) — 공개 표면 · lint

- `src/millie_rec/retrieval/__init__.py` `__all__` **14개 이름**: `KNN_ARTIFACT` `KNN_TOP` `POOL` `POP_ARTIFACT` `SOURCE_CONTENT` `SOURCE_ITEMKNN` `TOP_N` `ContentVectors` `ItemKNNRetriever` `NeighborRetriever` `PopularityRetriever` `VectorRetriever` `load_or_fit_itemknn` `retrieve_from_neighbors`. 내부 이름(`_query`·`_topk_cosine`·`_meta`·`CHUNK`·`WeightFn`·`component_weights`·`weighted_items`)은 노출하지 않았다.
- `uv run python -c "import millie_rec.retrieval as r; print(len(r.__all__))"` → `14`
- `uv run python -c "import millie_rec.retrieval, sys; print('scipy' in sys.modules, 'sklearn' in sys.modules)"` → `False False` (지연 import 유지)
- `uv run ruff format src/millie_rec/retrieval tests/retrieval` → `9 files left unchanged`; `uv run ruff check …` → `All checks passed!`; `uv run ruff format --check …` → `9 files already formatted`
- `uv run pytest tests/retrieval tests/test_architecture.py --no-header` → `34 passed`
- 줄 수: `__init__.py` 34 · `content.py` 131 · `itemknn.py` 149 · `neighbors.py` 80 · `popularity.py` 58 (전부 ≤150)
- star 의존: `grep -rn "millie_rec\.(ranking|reranking|data|evaluation|serving|app)" src/millie_rec/retrieval/` → 출력 없음

## TDD Gate Compliance

커밋 게이트(`test(...)` → `feat(...)` 커밋)는 **의도적으로 생략**했다 — 이 프로젝트의 커밋 정책(플랜 frontmatter `no_commit: true`, 사용자 지시 2026-09-05: 커밋은 사용자 승인 후 Advisor 가 Phase 1~3 산출물과 일괄)이 per-task 커밋을 금지하고, 같은 작업 트리에서 형제 플랜 2개(ranking·reranking)가 동시에 돌고 있어 `git add` 가 다른 워커의 미완성 파일을 섞을 위험이 있다.

**대체 증거 = pytest 요약 줄 2개** (`tdd_gate_evidence: pytest-output`):

| 게이트 | 명령 | 요약 줄 |
|---|---|---|
| RED | `uv run pytest tests/retrieval/test_{neighbors,itemknn,content}.py --no-header` | `15 failed, 9 passed in 0.83s` (사유 전부 AssertionError 계열) |
| GREEN | `uv run pytest tests/retrieval tests/test_architecture.py --no-header` | `34 passed in 0.79s` |
| REFACTOR | 위 + `ruff format --check` / `ruff check` | `34 passed` · `All checks passed!` |

## Plan 04-04 인계 — 공개 시그니처 5개

`app/` 는 `from millie_rec.retrieval import …` 로만 가져온다(깊은 import 는 `tests/test_architecture.py` 가 금지).

```python
ItemKNNRetriever(book_ids=None, nbr_ids=None, nbr_sims=None, *, meta=(0, 0, 0), weights=None)
    .fit(train) -> ItemKNNRetriever          # train 1인자
    .neighbors(book_id, n=KNN_TOP) -> list[tuple[int, float]]
    .retrieve(user, k) -> list[Candidate]    # source="itemknn"
    .save(path=KNN_ARTIFACT) -> Path ; ItemKNNRetriever.load(path=KNN_ARTIFACT, *, weights=None)
    .meta -> tuple[int, int, int]            # (train 행, 유저, 아이템)

load_or_fit_itemknn(train, path=None, *, weights=None) -> ItemKNNRetriever

NeighborRetriever(neighbors, *, source=SOURCE_CONTENT, weights=None, n_neighbors=20)
    # Track B cf 채널: NeighborRetriever(catalog_kr)  → source="content"

ContentVectors(books, text_col="tags", *, weights=None)
    # ItemVectors + CandidateGenerator 겸용. Track A content 채널 + MMR 벡터

VectorRetriever(vectors, ids, *, source=SOURCE_CONTENT, weights=None)
    # Track B content 채널: VectorRetriever(vectors_kr, ids=catalog 전체 book_id)
```

**배선 메모 (Advisor):**
- `weights` 는 `Callable[[UserState], dict[str, float]]`(키 `alpha`·`beta`·`gamma`). `None` 이면 세 성분 전부 1.0. `app/server.py`·`app/pipeline.py` 가 `ranking.state_weights` 함수 객체를 그대로 넘기면 된다(결정 D-01·D-09).
- 채널별 후보 풀은 `retrieval.POOL`(=200)을 `retrieve(user, POOL)` 로 쓴다.
- `make eval` 시간 유지는 `load_or_fit_itemknn(train, KNN_ARTIFACT)` 로. **`KNN_TOP` 같은 상수를 바꾸면 `rm -f artifacts/item_neighbors.npz` 를 먼저 해야 한다** — `meta` 는 train 크기만 보고 상수 변경은 감지하지 못한다(위협 T-04-06, Plan 04-05 실측 절차에 반영 필요).
- `VectorRetriever` 는 생성 시 dense 행렬을 한 번 만든다(9,450×128 ≈ 9.7MB). 요청마다 새로 만들지 말고 기동 시 1회 생성해 재사용할 것.
- `ContentVectors.retrieve`·`VectorRetriever.retrieve` 점수는 cosine×|q| 로 단위화되지 않았다 — 채널 내 min-max 정규화(Plan 04-02 `ranking/hybrid.py`)가 흡수한다.

## 변경 파일 목록

`git status --short -- src/millie_rec/retrieval tests/retrieval`:

```
 M src/millie_rec/retrieval/__init__.py
?? src/millie_rec/retrieval/content.py
?? src/millie_rec/retrieval/itemknn.py
?? src/millie_rec/retrieval/neighbors.py
?? src/millie_rec/retrieval/popularity.py
?? tests/retrieval/
```

`??` 는 이 플랜이 만든 것이 아니라 **repo 전체가 아직 미커밋**이기 때문이다(HEAD = `8e5172b chore: project scaffold …`). 이 플랜이 실제로 쓴 파일은 7개:

| 파일 | 상태 | 줄 |
|---|---|---|
| `src/millie_rec/retrieval/neighbors.py` | 신규 | 80 |
| `src/millie_rec/retrieval/itemknn.py` | 신규 | 149 |
| `src/millie_rec/retrieval/content.py` | 증분(기존 42줄 유지 + retrieve·VectorRetriever) | 131 |
| `src/millie_rec/retrieval/__init__.py` | 수정(`__all__` 4→14) | 34 |
| `tests/retrieval/test_neighbors.py` | 신규 (test 6건) | 84 |
| `tests/retrieval/test_itemknn.py` | 신규 (test 8건) | 106 |
| `tests/retrieval/test_content.py` | 증분(기존 4건 무수정 + 6건 추가 = 10건) | 110 |

`popularity.py`·`test_popularity.py` 는 읽기만 했다(mtime 09-05 15:01·15:02, 이 세션 시작 23:55 이전).

## Deviations from Plan

### Rule 3 — 진행을 막는 문제 자동 수정

**1. [Rule 3] RED 에서 `IndexError` 가 난 단정 1건의 순서를 바꿨다**
- **발견 시점:** Task 1 RED 확인
- **문제:** `test_weights_callable_scales_components` 가 `assert out[0].book_id == 3` 으로 시작해, 스텁이 `[]` 를 돌려줄 때 `IndexError: list index out of range` 로 죽었다. `.claude/rules/python-tdd.md` 는 RED 를 `AssertionError` 로만 인정한다.
- **수정:** 첫 단정을 `assert [c.book_id for c in out] == [3]` 으로 바꿨다(같은 것을 검사하되 빈 리스트에서 AssertionError 가 나게). 뒤의 `out[0].score` 단정은 유지.
- **파일:** `tests/retrieval/test_neighbors.py`

**2. [Rule 3] E501(줄 100자) 3건 — 한국어 docstring 을 줄이거나 두 줄로 나눴다**
- `neighbors.py::NeighborRetriever` docstring → 요약 줄 + 본문 2줄로 분할
- `itemknn.py::load_or_fit_itemknn` docstring → `"""캐시 meta 가 train 과 같으면 로드, 아니면 fit 후 저장. path None 이면 저장 안 함."""`
- `tests/retrieval/test_content.py`·`test_neighbors.py` 모듈·클래스 docstring 각 1줄
- 내용은 그대로. `awk 'length > 100'` 은 바이트를 세므로 한국어 줄을 오탐한다(한글 1자 = UTF-8 3바이트) — 실제 판정은 ruff E501(문자 기준)로 했고 `All checks passed!`.

**3. [Rule 3] `itemknn.py` 를 149줄로 압축**
- 플랜 스니펫을 그대로 쓰면 153줄로 150줄 제한(`.claude/rules/simplicity.md`)을 넘었다. `_meta()` 의 여러 줄 return 을 한 줄로 합쳐(84자) 149줄로 맞췄다. 로직 변경 없음.

### 플랜 acceptance 문구 중 이 repo 상태에서 판정 불가한 것 2건 (수정하지 않음)

**4. `git status --short -- <must_not_touch>` → "출력 없음" 은 성립할 수 없다**
- repo 전체가 아직 미커밋이라(HEAD = 스캐폴드 커밋 1개) Phase 1~3 산출물과 형제 워커의 파일이 모두 `M`/`??` 로 보인다. 플랜은 그것들이 커밋돼 있다고 가정했다.
- **대체 검증(mtime):** 이 세션은 09-05 23:55 이후에 시작했다. `Makefile` 20:21 · `pyproject.toml` 15:12 · `contracts.py` 11:12 · `tests/test_architecture.py` 09-04 — 전부 세션 시작 전이다. `ranking/*`·`reranking/*` 의 00:00 mtime 은 병렬 워커 2명의 것이고 내 Bash 호출은 그 경로에 쓴 적이 없다.
- **결론:** `must_not_touch` 위반 없음. 커밋 0(`git log --oneline | head -1` = `8e5172b`, 플랜 시작 전과 동일).

**5. `grep -n 'def __init__(self, books: "pd.DataFrame", text_col: str = TAGS_COL' content.py` → 1행이 안 나온다**
- `weights` keyword-only 를 추가하자 `ruff format` 이 시그니처를 여러 줄로 나눴다. 의도(기존 위치 인자 `books`·`text_col` 불변, `weights` 는 `*` 뒤 추가)는 지켜졌고 기존 테스트 4건이 무수정 통과한다.

## Known Stubs

없음. Task 1 의 스텁은 Task 2 에서 전부 실제 구현으로 대체됐고, `ContentVectors.fit`·`NeighborRetriever.fit`·`VectorRetriever.fit` 의 `return self` 는 스텁이 아니라 의도된 no-op 이다(벡터·이웃은 생성자가 이미 받았다 — `contracts.CandidateGenerator` Protocol 대칭용, 평가 하네스가 `fit` 을 호출한다).

## Threat Flags

없음 — 플랜 `<threat_model>` 밖의 새 보안 표면은 만들지 않았다. `mitigate` 3건은 코드에 존재한다: T-04-01 `np.load` allow_pickle 기본 False + `load_or_fit_itemknn` 의 예외 처리 · T-04-02 `CHUNK=500` chunked top-k + `top = min(KNN_TOP, n-1)` · T-04-06 npz `meta` 불일치 시 재fit(테스트 `test_load_or_fit_uses_cache_only_when_meta_matches`).

## 다음 단계 (Advisor)

1. wave 1 세 플랜(04-01·04-02·04-03)이 끝난 뒤 전역 게이트 1회: `uv run ruff format . && uv run ruff check . && uv run pytest --no-header`(기준선 255 passed + 이 플랜 20건) + `make smoke`. `tests/data/test_millie_catalog.py::test_coverage_gate` 1 failed 는 Phase 3 몫(재수집 중 의도된 RED).
2. Plan 04-04 에서 위 "공개 시그니처 5개" 로 `app/pipeline.py`·`pipeline_kr.py` 4 variant 조립 + `weights=state_weights` 주입.
3. Plan 04-05 실측 절차에 `rm -f artifacts/item_neighbors.npz` 를 선행 단계로 넣는다(상수 변경 시 캐시가 감지하지 못함).

## Self-Check: PASSED

| 검사 | 결과 |
|---|---|
| `src/millie_rec/retrieval/neighbors.py` 존재 | FOUND (80줄) |
| `src/millie_rec/retrieval/itemknn.py` 존재 | FOUND (149줄) |
| `src/millie_rec/retrieval/content.py` 존재 | FOUND (131줄) |
| `tests/retrieval/test_neighbors.py` 존재 · `def test_` 6개 | FOUND |
| `tests/retrieval/test_itemknn.py` 존재 · `def test_` 8개 | FOUND |
| `tests/retrieval/test_content.py` 존재 · `def test_` 10개 | FOUND |
| `uv run pytest tests/retrieval tests/test_architecture.py --no-header` | 34 passed, 0 failed |
| `uv run ruff check` / `ruff format --check` (자기 경로) | All checks passed / 9 files already formatted |
| `__all__` 길이 | 14 |
| 공개 표면 import 시 scipy·sklearn 로드 | False False |
| src 파일 ≤150줄 | 전부 통과 (최대 149) |
| star 의존 위반 grep | 출력 없음 |
| 커밋 수 | 0 (HEAD `8e5172b` 불변) |
| 커밋 해시 검증 | 해당 없음 — `no_commit: true` |
