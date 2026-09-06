# Phase 4: 추천 파이프라인과 모델 freeze - Pattern Map

**Mapped:** 2026-09-05
**Files analyzed:** 소스 13개(신규 8 + 수정 5) + 테스트 7개(신규 6 + 확장 1) + `Makefile` 1
**Analogs found:** 20 / 21 — 후보 생성기·Pipeline glue·서버 배선·테스트 형태는 Phase 2·3 코드가 그대로 아날로그다(exact 9 · role-match 11). **`scipy.sparse` 코사인·MMR·가중합 랭커는 repo 에 코드 아날로그가 0건**(grep `scipy|sparse` → 0) → 규칙·CONTEXT 수식 기반 제안 스니펫을 "No Analog" 절에 두었다.

## 기준선 (실측 2026-09-05 밤, 이 페이즈 시작 직전)

| 항목 | 값 |
|---|---|
| `uv run python --version` | Python 3.11.6 |
| `uv run pytest --no-header` | **255 passed, 1 failed**, 3.29s — 실패 1건 = `tests/data/test_millie_catalog.py::test_coverage_gate`(재수집 진행 중 의도된 RED, STATE.md Blockers). CONTEXT 의 "256 passed" 는 이 1건 포함 수치 |
| 줄 수(150줄 규칙) | `app/pipeline.py` **110** · `retrieval/content.py` **42** · `serving/api.py` **135** · `app/cli.py` 128 · `app/server.py` 23 · `retrieval/popularity.py` 58 · `data/catalog_kr.py` 118 · `data/vectors_kr.py` 38 · `evaluation/harness.py` 67 · `tests/conftest.py` 130 |
| 빈 슬라이스 | `src/millie_rec/ranking/__init__.py`·`reranking/__init__.py` 각 3줄(`__all__: list[str] = []`), `tests/ranking/`·`tests/reranking/` 빈 디렉터리(`__init__` 없음 — 다른 tests 하위도 없음, rootdir 기준 수집) |
| `create_app` 시그니처(verbatim, `serving/api.py` L81-90) | `def create_app(pipelines: dict[str, Pipeline], fallback: Pipeline, *, catalog: Catalog \| None = None, db: Database, neighbors: Neighbors \| None = None, book_stats: BookStatsSource \| None = None, state: object \| None = None) -> FastAPI` |
| `artifacts/serving/` | `books_kr.json` 9,450권(8.3MB) · `content_vectors_kr.npz` **(8,708, 128) float32**(4.5MB, books 와 742권 불일치 = STATE.md Blocker) · `item_edges_kr.json` src 9,450(11MB) · `popularity_kr.json`(7.3MB) · `eval_table.json` |
| `artifacts/popularity.json` | 15KB(Track A pop, `make eval` 산출). `artifacts/*` gitignore, `!artifacts/serving/` 만 커밋 → `item_neighbors.npz` 도 gitignore 자동 |
| Track A | `interactions.parquet` 5,976,479행 × 5, 유저 53,424 · 아이템 10,000(필터 전). `results/latest.csv` pop 1행(0.063/0.054/0.764, n_users 2000, holdout) · `latest_states.csv` n0/n20(n20 n_users 1990) |
| 의존성 | `pyproject.toml` 에 numpy·scipy·pandas·pyarrow·scikit-learn·fastapi·uvicorn·matplotlib — **추가 없음** |
| 테스트 fixture | **`tests/fixtures/millie/serving_sample/` 디렉터리는 없다.** 정본은 `tests/conftest.py::millie_serving_sample`(session scope, `tmp_path_factory` 에 20권 json 3개 + npz 생성, L92-130). CONTEXT D-11 의 경로 표기는 이 fixture 를 가리킨다 |

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `src/millie_rec/retrieval/itemknn.py` (NEW) | retriever (`CandidateGenerator` + `Neighbors` 구현) | batch fit → request-response | `retrieval/popularity.py` L22-58 (fit·retrieve·save/load·seen 제외) + `data/vectors_kr.py` L23-26 (npz `load`) | role-match(fit/retrieve/save/load exact, 유사도 계산 no-analog) |
| `src/millie_rec/retrieval/content.py` (MODIFY — `retrieve()` 증분) | retriever (`ItemVectors` + `CandidateGenerator`) | transform → request-response | 자기 자신 L20-42 (`_matrix`·`_index`) + `popularity.py::retrieve` L39-47 | exact |
| `src/millie_rec/retrieval/__init__.py` (MODIFY) | public surface | — | 자기 자신 L1-11 · `data/__init__.py` L39-72 (알파벳 정렬 `__all__`) | exact |
| `src/millie_rec/ranking/blend.py` (NEW) | utility (순수 함수 `state_weights`) | transform | `evaluation/metrics.py` L11-38 (상수 인자·경계값·1줄 docstring 순수 함수) | role-match |
| `src/millie_rec/ranking/hybrid.py` (NEW) | ranker (`Ranker` 구현, 채널 min-max + 가중합 + gap 3항) | transform | `app/pipeline.py::CatalogPopPipeline.recommend` L57-77 (Candidate/meta → ScoredItem 조립) + `data/catalog_kr.py::stats` L93-115 (BookStats 소비 형태) | role-match |
| `src/millie_rec/ranking/__init__.py` (NEW 내용) | public surface | — | `retrieval/__init__.py` L1-11 | exact |
| `src/millie_rec/reranking/mmr.py` (NEW) | reranker (`Reranker` 구현) | transform | `evaluation/metrics.py::ild_at_k` L28-38 (0-벡터 안전 cosine 행렬) | role-match(거리 계산 exact, 그리디 루프 no-analog) |
| `src/millie_rec/reranking/guard.py` (NEW) | reranker (`Reranker` 구현, 순서 조정) | transform | `data/catalog_kr.py::stats` L93-115 (BookStats 필드) + `serving/fallback.py::GlobalPopularFallback.recommend` L21-24 (`None` 이면 패스스루 분기) | role-match |
| `src/millie_rec/reranking/__init__.py` (NEW 내용) | public surface | — | `retrieval/__init__.py` | exact |
| `src/millie_rec/app/pipeline.py` (MODIFY, Advisor) + `app/pipeline_kr.py` (NEW 권장) | assembly glue (`Pipeline` 구현 + dict 조립) | request-response | 자기 자신 `PopPipeline` L25-43 · `CatalogPopPipeline` L46-77 · `fit_pipelines` L80-82 · `build_pipelines` L97-110 | exact |
| `src/millie_rec/app/cli.py` (MODIFY, Advisor — `demo --seeds`·`demo --find`) | CLI | file-I/O(json 읽기) → stdout | 자기 자신 `cmd_eval` L58-104 · `main` L107-124 (서브커맨드 추가 자리) + `data/catalog_kr.py::CatalogKR.load` L65-71 (books_kr.json 로드) | exact |
| `src/millie_rec/app/server.py` (MODIFY, Advisor — `weights=`) | entrypoint | — | 자기 자신 L13-21 | exact |
| `src/millie_rec/serving/api.py` (MODIFY — `create_app(..., weights=None)`) | controller | request-response | 자기 자신 `create_app` L81-90 · `_personalized_response` L66-78 + `serving/compose.py::build_response` L34-60 (`user_state_weights` 0 고정 자리) | exact |
| `Makefile` (MODIFY, Advisor — `demo` 리다이렉트) | build | — | 자기 자신 L30-31 | exact |
| `tests/retrieval/test_itemknn.py` (NEW) | test | — | `tests/retrieval/test_popularity.py` L1-79 (손계산 `_train()`·`inspect.signature` fit 인자·save/load 라운드트립) | exact |
| `tests/retrieval/test_content.py` (EXTEND — `retrieve`) | test | — | 자기 자신 L12-18 `_books()` + `test_popularity.py::test_retrieve_excludes_user_seen` L42-45 | exact |
| `tests/ranking/test_blend.py` (NEW) | test | — | `tests/evaluation/test_metrics.py` (손계산·`pytest.approx`) | role-match |
| `tests/ranking/test_hybrid.py` (NEW) | test | — | `tests/evaluation/test_harness.py::_OneHot` L30-37 (가짜 Protocol 구현) + `tests/app/test_pipeline.py::_FakeCatalog` L59-79 | role-match |
| `tests/reranking/test_mmr.py`·`test_guard.py` (NEW) | test | — | `tests/evaluation/test_harness.py` L13-37 (`_FakePipeline`·`_OneHot`) · `tests/evaluation/test_metrics.py` ILD 손계산 | role-match |
| `tests/app/test_variants.py` (NEW) 또는 `test_pipeline.py` 확장 | test | — | `tests/app/test_pipeline.py` L51-55·L82-97 + `tests/app/test_server_catalog.py` L20-37 (서버 재import + `millie_serving_sample`) | exact |

---

## Pattern Assignments

### 0. 모든 신규 슬라이스 `.py` 공통 — 모듈 머리·상수·지연 import

**Analog:** `src/millie_rec/retrieval/popularity.py` L1-19 · `retrieval/content.py` L1-25

```python
"""pop 기준선 — contracts.CandidateGenerator 구현.

train 전체 행 카운트(평점 무관, CONTEXT D-05) · seen 제외 · 작은 json 아티팩트(D-10).
"""

import json
from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING

from millie_rec.contracts import COL_ITEM, DIR_ARTIFACTS, Candidate, UserState

if TYPE_CHECKING:
    import pandas as pd

SOURCE_POPULARITY = "popularity"  # serving/fallback.py 와 같은 값 — serving import 불가라 중복 정의
ARTIFACT_NAME = "popularity.json"
POP_ARTIFACT = DIR_ARTIFACTS / ARTIFACT_NAME  # app/pipeline.py 가 존재 검사만 한다(D-10)
TOP_N = 1000  # D-10: K_MAX(100) + seen 여유. 서빙은 이 상위 N 만 안다
```
```python
    def __init__(self, books: "pd.DataFrame", text_col: str = TAGS_COL) -> None:
        # sklearn 은 여기서만 import — 서버가 retrieval 공개 표면을 읽어도 sklearn 을 끌어오지 않게
        from sklearn.feature_extraction.text import TfidfVectorizer
```
복사할 것: ① docstring 첫 줄 "무엇 — 계약 Protocol 이름 (근거 결정)" ② stdlib → 서드파티 → `millie_rec.contracts` 순(ruff `I`) ③ pandas 는 `TYPE_CHECKING` 아래, **scipy·sklearn 은 함수 안에서 import**(서버가 `millie_rec.retrieval` 공개 표면을 import 해도 로드되지 않게 — `app/server.py` → `app/pipeline.py` → `from millie_rec.retrieval import …` 경로가 실제로 있다) ④ 상수는 모듈 상단 대문자 + `#` 주석에 근거(D-xx) ⑤ 중복 상수(`SOURCE_*`)는 "serving import 불가라 중복 정의" 주석 그대로 ⑥ ≤150줄.

**Phase 4 상수 이름(CONTEXT Established Patterns, 브리프에 그대로):** `ALPHA0=0.6 BETA0=0.3 GAMMA0=0.1 TAU=20 ALPHA_FLOOR=0.2`(blend) · `W_CF=0.5 W_CONTENT=0.3 W_POP=0.2` + gap 3항 음수 상수(hybrid) · `LAMBDA_MMR=0.7 MMR_POOL=50`(mmr) · `GUARD_RESID_Z=-1.0 GUARD_MIN_COMPLETED=3`(guard) · `KNN_TOP=50 POOL=200`(itemknn) · `SOURCE_ITEMKNN="itemknn" SOURCE_CONTENT="content"`. **freeze 대상(D-14 ①)** — 이 이름들이 개발일지 D 항목·draft §4-1 각주에 인용된다.

**import 허용 범위(`tests/test_architecture.py` L37-42, 정적 검사):** `retrieval`·`ranking`·`reranking` 파일은 `millie_rec.contracts` + 자기 슬라이스 내부만. `ranking/hybrid.py` 가 `millie_rec.retrieval` 을 import 하면 즉시 실패 → 채널 이름은 `Candidate.source` 문자열로만 본다(`SOURCE_ITEMKNN` 을 ranking 에 **중복 정의**). `app` 은 `from millie_rec.ranking import state_weights` 처럼 공개 표면만(L41-42, `len(parts) > 2` 면 위반).

---

### `src/millie_rec/retrieval/itemknn.py` (retriever, batch fit → request-response) — NEW

**Analog A — 클래스 뼈대·fit 은 train 1인자·retrieve 의 seen 제외·save/load:** `retrieval/popularity.py` L22-58 (전문은 §0 + 아래)

```python
class PopularityRetriever:
    """전역 인기 상위 k. fit 은 train 만 받는다(Protocol docstring 그대로)."""

    name = "pop"

    def __init__(self, ranked: Sequence[tuple[int, float]] = ()) -> None:
        self._ranked: list[tuple[int, float]] = [(int(b), float(s)) for b, s in ranked]

    def fit(self, train: "pd.DataFrame") -> "PopularityRetriever":
        counts = train[COL_ITEM].value_counts()  # 평점 무관 — "평점이 있다 = 읽었다"(D-05)
        ...
        return self

    def retrieve(self, user: UserState, k: int) -> list[Candidate]:
        out: list[Candidate] = []
        for b, s in self._ranked:  # 상위부터 k 개에서 멈춘다 — 전 카탈로그 순회 아님
            if b in user.seen:
                continue
            out.append(Candidate(book_id=b, source=SOURCE_POPULARITY, score=s))
            if len(out) == k:
                break
        return out

    def save(self, path: Path = POP_ARTIFACT, *, top_n: int = TOP_N) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        ...
        return path

    @classmethod
    def load(cls, path: Path = POP_ARTIFACT) -> "PopularityRetriever":
        payload = json.loads(path.read_text(encoding="utf-8"))
        return cls((int(b), float(s)) for b, s in payload["items"])
```
→ `ItemKNNRetriever` 는 같은 4메서드 + `name = "cf"`(= `VARIANTS[1]`; Track A 의 `Candidate.source` 는 `SOURCE_ITEMKNN="itemknn"`, `contracts.Candidate.source` 주석 L214 허용값). `fit` 인자는 **`train` 1개만**(`test_popularity.py` L59-61 이 `inspect.signature` 로 단정하는 형태를 itemknn 테스트도 복제). `__init__` 은 이웃 테이블 주입만(`load` 가 부른다) — 요청마다 재계산 금지.

**Analog B — npz 로드·`with np.load` 핸들 닫기:** `data/vectors_kr.py` L23-26
```python
    @classmethod
    def load(cls, path: Path = DIR_SERVING / VECTORS_KR_NPZ) -> "VectorsKR":
        with np.load(path) as z:  # 파일 핸들을 닫는다
            return cls(z["book_ids"], z["vectors"])
```
→ `KNN_ARTIFACT = DIR_ARTIFACTS / "item_neighbors.npz"`. `save`: `np.savez(path, book_ids=int64[n], nbr_ids=int64[n, KNN_TOP], nbr_sims=float32[n, KNN_TOP], meta=np.array([n_rows, n_users, n_items]))` — 이웃 <50 인 아이템은 `-1`/`0.0` 패딩. **캐시 무효화(Claude's Discretion):** 비용 0 인 `meta`(train 행 수·유저 수·아이템 수) 비교를 권장 — 셋이 같으면 로드, 다르면 재fit. 파일 존재만 보면 필터 상수 변경 후 옛 이웃을 쓰게 되어 재현성이 깨진다.

**Analog C — `Neighbors` Protocol 을 같은 클래스가 만족(Track B 어댑터와 대칭):** `data/catalog_kr.py::neighbors` L89-91
```python
    def neighbors(self, book_id: int, n: int = 20) -> list[tuple[int, float]]:
        edges = self._edges.get(str(int(book_id)), [])  # json 키는 문자열
        return [(int(dst), float(w)) for dst, w, _source in edges[:n]]
```
→ `ItemKNNRetriever.neighbors(book_id, n)` 를 같은 시그니처로 두면 **retrieve 로직을 `Neighbors` 위에서 한 번만 쓴다**: `retrieve = Σ_{i∈user items} w_component(i) · sim(i, ·)` 를 모듈 함수 `retrieve_from_neighbors(nbrs: Neighbors, user, k, *, source, weights) -> list[Candidate]` 로 빼고, Track A 는 `self`, Track B 는 `CatalogKR`(D-10 "cf 채널 = `CatalogKR.neighbors` 엣지") 을 넣는 얇은 `NeighborRetriever(neighbors: Neighbors, source=SOURCE_CONTENT)` 클래스 하나(≈15줄, 같은 파일 또는 `retrieval/neighbors.py`). "이중 구현 금지"(simplicity.md) 충족. `Candidate.source` 는 Track A `itemknn` / Track B `content`(`.claude/rules/data.md` "itemknn 이라 쓰지 않는다").

**성분별 가중(D-01, Claude's Discretion "성분별 점수 계산 방식") — 권장:** `UserState` 는 `explicit_seeds`·`history`·`session` 세 튜플(contracts L127-129). 성분 아이템에 가중치를 붙여 **한 번에** 이웃 합을 내는 쪽이 3회 knn 보다 빠르고 결과가 같다:
```python
def _weighted_items(user: UserState, w: dict[str, float]) -> list[tuple[int, float]]:
    """(book_id, α|β|γ) — 비어 있는 성분은 자연히 0 항."""
    return (
        [(b, w["alpha"]) for b in user.explicit_seeds]
        + [(b, w["beta"]) for b in user.history]
        + [(b, w["gamma"]) for b in user.session]
    )
```
`w` 는 생성 시 주입되는 `weights: Callable[[UserState], dict[str, float]] | None`(app 이 `ranking.state_weights` 를 넘긴다 — retrieval 은 ranking 을 import 할 수 없으므로 **Callable 주입**이 유일한 경로, `create_app(weights=)` D-09 와 같은 형태). `None` 이면 세 성분 전부 1.0(테스트·pop 대칭 기본값). 후보 풀 `POOL=200`: `retrieve(user, k)` 는 `k` 를 그대로 받되 app 이 `POOL` 로 부른다(Protocol 시그니처 불변).

**유사도 계산 — repo 아날로그 없음 → "No Analog" 절의 제안 스니펫(chunked top-k) 사용.**

**테스트(`tests/retrieval/test_itemknn.py`) — `test_popularity.py` 형태 그대로:** 손계산 `_train()`(유저 3 × 아이템 4, 예: 아이템 1·2 를 같은 두 유저가 읽어 cos=1.0, 아이템 4 는 단독 → 이웃 없음) → ① 계약: `Candidate` 타입·`source=="itemknn"`·점수 내림차순·`name=="cf"` ② 정확성: seeds `(1,)` 이면 2 가 1순위, `seen` 제외(`UserState(None, history=(1,2,3,4))` → `[]`), 성분 가중 `weights=lambda u: {"alpha":1,"beta":0,"gamma":0}` 로 history 무시 확인 ③ 안전성: `inspect.signature(fit).parameters == ["self","train"]`(L61 verbatim) · `save`→`load` 라운드트립 후 `retrieve` 동일 · `neighbors(4) == []` · fixture `interactions`(20×50) 로 `len(out) == 20`.

---

### `src/millie_rec/retrieval/content.py` (MODIFY — `retrieve()` 증분, 현재 42줄)

**현재 전문 핵심(L20-42, 위 §0 포함):**
```python
class ContentVectors:
    """L2 정규화 dense 벡터. 미지 id 는 0 벡터(ILD 에서 거리 1)."""

    def __init__(self, books: "pd.DataFrame", text_col: str = TAGS_COL) -> None:
        ...
        self._matrix = vec.fit_transform(texts)  # (n_books, dim), 행 L2=1(빈 문서는 0)
        self._index = {int(b): i for i, b in enumerate(books[COL_ITEM].tolist())}

    def vectors(self, book_ids: Sequence[int]) -> np.ndarray:
        out = np.zeros((len(book_ids), self.dim), dtype=float)
        rows = [(i, self._index[int(b)]) for i, b in enumerate(book_ids) if int(b) in self._index]
        if rows:
            dst, src = zip(*rows, strict=True)
            out[list(dst)] = self._matrix[list(src)].toarray()
        return out
```
**증분(D-04 "seeds(성분별) TF-IDF 평균 벡터 cosine top-k"):** `_matrix` 는 scipy CSR(행 L2=1) → 사용자 벡터 `q = Σ w_c · mean(rows of component c)` 를 dense (dim,) 로 만들고 `scores = self._matrix @ q`(CSR·dense = dense (n_books,)) → `seen`·`q==0` 처리 → `np.argpartition(-scores, k+len(seen))` 로 상위 → seen 제외 → `Candidate(source=SOURCE_CONTENT, score=float)`. 역인덱스 `self._ids = np.array(books[COL_ITEM])` 1줄 추가(`_index` 의 역). `name = "content"`(Protocol `CandidateGenerator.name` — variant 이름이 아니라 채널 이름, `VARIANTS` 에 없어도 됨). `weights` 주입은 itemknn 과 동일 Callable(기본 None = 1.0). **`fit(train)` 은 필요 없다**(벡터는 books 로 생성) — Protocol 은 structural typing 이라 `fit` 없이도 `retrieve` 만으로 app 이 쓸 수 있지만, 하네스 대칭을 위해 `fit(self, train): return self` 1줄(no-op) 두는 쪽을 권장(D-15 "content `retrieve` seeds 벡터" 테스트가 fit 유무를 단정하지 않게 planner 가 확정).

**Track B 대칭(D-10 "content 채널 = `VectorsKR` seeds 평균 벡터 cosine 전체 검색"):** `VectorsKR`(data 슬라이스, `vectors(book_ids)` 만 노출, 전체 id 열람 없음)은 `retrieve` 가 없다. 두 선택지 — planner 확정:
- (a) `retrieval` 에 `VectorRetriever(vectors: ItemVectors, ids: Sequence[int], source=SOURCE_CONTENT)` — `__init__` 에서 `vectors.vectors(ids)` 1회 호출로 dense 행렬(9,450×128 float ≈ 9.7MB) 을 쥔다. `ids` 는 app 이 `catalog.popular(n=10**6)`(eligible 전량, `CatalogKR.popular` L76-82 은 `_pop_order[:n]`) 로 얻어 넘긴다 → data 슬라이스 무변경. `content.py` 의 cosine top-k 를 모듈 함수 `_topk_cosine(matrix, q, seen, k)` 로 빼서 두 클래스가 공유(이중 구현 금지).
- (b) `VectorsKR.book_ids` 프로퍼티 1줄 추가(data 슬라이스 — 이 페이즈 쓰기 영역 밖, Advisor 승인 필요) 후 (a) 와 동일.
권장 (a). `content.py` 는 42 + retrieve ≈25 + VectorRetriever ≈20 = ≈90줄.

**테스트(`tests/retrieval/test_content.py` 확장):** 기존 `_books()`(L12-18: `10 "fantasy magic"`, `20 "magic romance"`, `30 "history war"`) 그대로 → `retrieve(UserState(None, explicit_seeds=(10,)), k=2)` 는 `[20]`(30 은 직교라 점수 0 — 0점 후보 포함 여부를 단정으로 고정: "점수 0 은 제외" 권장, `test_vectors_rows_are_l2_normalized_and_orthogonal_when_no_shared_tags` L31-35 가 `v[0] @ v[2] == 0.0` 을 이미 보장) · seen(10) 미포함 · `Candidate.source == "content"` · 미지 seed(99) 만이면 `[]`.

---

### `src/millie_rec/retrieval/__init__.py` (MODIFY)

**현재 전문(L1-11):**
```python
"""retrieval 슬라이스 공개 표면. 다른 슬라이스는 여기 있는 이름만 import 할 수 있다."""

from millie_rec.retrieval.content import ContentVectors
from millie_rec.retrieval.popularity import POP_ARTIFACT, TOP_N, PopularityRetriever

__all__ = [
    "POP_ARTIFACT",
    "TOP_N",
    "ContentVectors",
    "PopularityRetriever",
]
```
→ 추가: `KNN_ARTIFACT`·`ItemKNNRetriever`·`NeighborRetriever`(또는 `retrieve_from_neighbors`)·`VectorRetriever`·`SOURCE_CONTENT`·`SOURCE_ITEMKNN`. 정렬 규칙 = `data/__init__.py` L39-72: 대문자 상수 → 클래스 → 함수, 각 알파벳순(ruff `I` 는 import 블록만 정렬, `__all__` 순서는 관례). **app 이 쓰는 이름만** 노출(`_topk_cosine` 같은 내부 함수는 제외).

---

### `src/millie_rec/ranking/blend.py` (utility, 순수 함수) — NEW

**Analog — 상수 기본 인자 + 경계값 + 1줄 docstring 순수 함수:** `evaluation/metrics.py` L11-25
```python
def recall_at_k(ranked: Sequence[int], relevant: Set[int], k: int = K_RECALL) -> float:
    """|L_u[:k] ∩ R_u| / |R_u|. 분모를 min(|R_u|, k) 로 바꾸지 않는다(evaluation.md)."""
    if not relevant:
        return 0.0
    hits = sum(1 for b in ranked[:k] if b in relevant)
    return hits / len(relevant)
```
**제안 형태(D-02 verbatim 수식, Claude's Discretion 시그니처):**
```python
ALPHA0, BETA0, GAMMA0 = 0.6, 0.3, 0.1  # 아키텍처 01 §3-3 초기값. freeze(D-14 ①)
TAU = 20  # main §5-2 α_n = α₀·e^{−n/τ}. n=20 → α≈0.22
ALPHA_FLOOR = 0.2  # 아키텍처 01 §3-3 하한
WEIGHT_KEYS = ("alpha", "beta", "gamma")  # 응답 user_state_weights 키 = compose.ZERO_WEIGHTS 키
RESET_BOOST, SESSION_BOOST = 0.15, 0.10  # D-02: 인자로만 받고 적용은 Phase 5 state.py


def state_weights(
    user: UserState, *, reset_boost: bool = False, session_active: bool = False
) -> dict[str, float]:
    """α_n = max(0.2, 0.6·e^{−n/20}), 나머지를 β:γ=3:1 → 비어 있는 성분 제거 → 합 1 재정규화."""
    n = len(user.history)  # D-02: Phase 4 는 이벤트가 없다 — history 권수가 n
    alpha = max(ALPHA_FLOOR, ALPHA0 * math.exp(-n / TAU))
    rest = 1.0 - alpha
    raw = {"alpha": alpha, "beta": rest * BETA0 / (BETA0 + GAMMA0), "gamma": rest * GAMMA0 / (BETA0 + GAMMA0)}
    present = {"alpha": bool(user.explicit_seeds), "beta": bool(user.history), "gamma": bool(user.session)}
    kept = {k: v for k, v in raw.items() if present[k]}
    total = sum(kept.values()) or 1.0
    return {k: round(kept.get(k, 0.0) / total, 3) for k in WEIGHT_KEYS}
```
`round(…, 3)` 은 CONTEXT specifics "소수 3자리" — 단, 반올림 후 합이 1.000 이 아닐 수 있어 테스트는 `sum(...) == pytest.approx(1.0, abs=2e-3)` 로. **응답 dict 키는 `serving/compose.py` L21 `ZERO_WEIGHTS = {"alpha": 0.0, "beta": 0.0, "gamma": 0.0}` 와 동일**(`tests/serving/test_smoke.py` L32·L109 가 이 키를 단정).

**⚠ CONTEXT 내부 불일치(planner 가 테스트 기대값을 확정해야 함):** specifics 의 "history 20 → α≈0.22, β≈0.585, γ≈0.195(합 1.0)" 은 **session 이 비어 있지 않을 때**의 값이다. D-02 "비어 있는 성분을 빼고 재정규화" 를 적용하면 평가 유저(session 항상 `()`)는 γ 가 빠져 `α≈0.273, β≈0.727` 이 된다. 또 `mask_onboarding`(L69-71) 의 n_k 상태는 `history = rest`(seeds 외 **train 전체**, `len ≥ 20`)라 n 은 20 이 아니라 유저별 20~수백 → 대부분 `ALPHA_FLOOR` 에 닿는다. 테스트는 (i) `UserState(None, explicit_seeds=(1,), history=tuple(range(20)), session=(99,))` 로 0.220/0.585/0.195 를, (ii) session 없는 n=20 으로 0.273/0.727/0.0 을, (iii) seeds 만 → `{1.0, 0.0, 0.0}`(REC-03) 을 각각 단정하는 3건이 D-02 를 정확히 증명한다. PDF 문장(draft §2-2 L104)은 이미 "재정규화로 α=1" 만 말하므로 문서 충돌은 없다.

---

### `src/millie_rec/ranking/hybrid.py` (ranker) — NEW

**Analog A — 여러 소스에서 `ScoredItem` 조립·`position`·`source_channels`:** `app/pipeline.py::CatalogPopPipeline.recommend` L57-77
```python
        ids = [b for b in self.catalog.popular(n=k + len(user.seen)) if b not in user.seen][:k]
        meta = {int(m["book_id"]): m for m in self.catalog.meta(ids)}
        items = []
        for i, b in enumerate(ids):
            m = meta.get(b, {})
            items.append(
                ScoredItem(
                    book_id=b,
                    score=float(len(ids) - i),
                    source=SOURCE_POPULARITY,
                    position=i,
                    source_channels=(SOURCE_POPULARITY,),
                    title=m.get("title"),
                    ...
                    difficulty=m.get("difficulty"),
                )
            )
```
→ `HybridRanker.rank(user, candidates) -> list[ScoredItem]`: ① 채널별 그룹(`c.source`) → 채널 안 min-max(후보 1개·분모 0 이면 1.0, Claude's Discretion) ② `score = Σ_ch W[ch] · norm_ch.get(book, 0.0)` ③ gap 3항(아래) ④ 내림차순 정렬 → `ScoredItem(book_id, score, source=최대 기여 채널, position=i, source_channels=tuple(sorted(기여 채널)), difficulty=stats.difficulty)`. **meta 조인(title·authors·image_url)은 하지 않는다** — Track B 는 `app/pipeline_kr.py` 가 `catalog.meta` 로 채우고(`CatalogPopPipeline` L59 패턴), Track A 는 필요 없다. `W = {SOURCE_ITEMKNN: W_CF, SOURCE_CONTENT: W_CONTENT, SOURCE_POPULARITY: W_POP}` — Track B 는 cf 채널도 `source="content"` 라 **W_CF 가 붙지 않는다**. 해법(planner 택1): (a) Track B `NeighborRetriever` 는 `Candidate.source="content"` 로 두고 `HybridRanker(channel_weights={…})` 를 생성 시 주입해 app 이 Track B 용 dict 를 넘긴다(`{content: W_CF + W_CONTENT, popularity: W_POP}` 처럼) — 단 두 content 채널이 한 그룹으로 합쳐져 min-max 가 섞인다 (b) `Candidate.source` 는 표기(`content`)이고 **채널 키는 retriever 의 `name`** 으로 잡는다: `rank(user, candidates)` 시그니처가 `list[Candidate]` 하나라 retriever 이름이 안 들어오므로, app 이 `candidates` 를 넘기기 전에 `(name, Candidate)` 로 태깅할 수 없다 → (a) 가 현실적. 또는 (c) `Candidate.source` 에 Track B 도 내부적으로 `itemknn`/`content` 를 쓰고 **ScoredItem 으로 바꿀 때만** `source_channels=("content",)` 로 표기 정규화(app 의 Track B glue 에서 `dataclasses.replace`). (c) 가 랭커 코드를 Track 무관하게 유지(D-10 "blend·hybrid·mmr·guard 코드는 동일, 어댑터만 다르다")하며 `.claude/rules/data.md` 는 **표기(`Candidate.source`·`ScoredItem.source_channels`)** 만 규정한다 — 그러나 `Candidate.source` 도 규정 대상이라 (c) 는 규칙 위반 소지. **권장 (a) + 채널 가중치 dict 주입.**

**Analog B — `BookStats` 소비(gap 피처 입력):** `data/catalog_kr.py::stats` L93-115 (BookStats 생성 측) · `contracts.BookStats` L168-192 · `BookStatsSource` L334-338
```python
class BookStatsSource(Protocol):
    def stats(self, book_ids: Sequence[int]) -> list[BookStats]: ...
    def user_level(self, user: UserState) -> float | None: ...
```
→ D-06: `HybridRanker(book_stats: BookStatsSource | None = None)`. `rank` 안에서 `level = book_stats.user_level(user) if book_stats else None`; `level is None` 이면 gap 항 **전부 0**(Phase 4 는 `CatalogKR.user_level` 이 `None` 고정 L117-118 → 서버에서도 0, Track A 는 `None` 주입 → 0). 결측 `difficulty=None` 도 0. 3항: `gap = difficulty − level`, `gap_pos = max(gap, 0)`, `n_completed × gap`(`n_completed = len(user.history)` 대리값, D-08). 상수 `W_GAP, W_GAP_POS, W_NCOMP_GAP`(음수, 모듈 상단). **AC13 증거 = "피처 3항이 각각 순위화 입력에 존재"** → 테스트가 `level` 을 주는 가짜 `BookStatsSource`(`user_level` 이 0.5 반환)로 gap 항이 점수를 **실제로 바꾸는지**(음수 가중 → difficulty 높은 책 하락) 단정 + `None` 3경로(소스 None·difficulty None·level None) 모두 가중 0 단정.

**가짜 Protocol 구현 테스트 패턴:** `tests/evaluation/test_harness.py::_OneHot` L30-37 · `tests/app/test_pipeline.py::_FakeCatalog` L59-79 — 상속 없이 메서드만 갖는 클래스. `_FakeStats.stats(ids) -> [BookStats(book_id=b, difficulty=…, resid_z=…, source="millie_index")]`, `user_level(user) -> 0.5`.

---

### `src/millie_rec/ranking/__init__.py` · `reranking/__init__.py` (현재 `__all__: list[str] = []`)

`retrieval/__init__.py` 형태로 교체. ranking: `ALPHA0 ALPHA_FLOOR TAU W_CF W_CONTENT W_POP HybridRanker state_weights`(+ `WEIGHT_KEYS`). reranking: `LAMBDA_MMR MMR_POOL GUARD_MIN_COMPLETED GUARD_RESID_Z DifficultyGuard MMRReranker`. `app/pipeline.py`·`app/server.py` 가 여기 이름만 import.

---

### `src/millie_rec/reranking/mmr.py` (reranker) — NEW

**Analog — 0-벡터 안전 cosine 행렬(거리 = 1 − cos):** `evaluation/metrics.py::ild_at_k` L28-38 (verbatim)
```python
def ild_at_k(vectors: np.ndarray, k: int = K_RANK) -> float:
    """상위 k 아이템 모든 쌍 (1 − cosine) 평균. 쌍이 없으면 0. 0 벡터의 cosine 은 0(거리 1)."""
    v = np.asarray(vectors, dtype=float)[:k]
    n = v.shape[0]
    if n < 2:
        return 0.0
    norms = np.linalg.norm(v, axis=1, keepdims=True)
    unit = v / np.where(norms == 0, 1.0, norms)
    cos = unit @ unit.T
    iu = np.triu_indices(n, k=1)
    return float(np.mean(1.0 - cos[iu]))
```
→ `MMRReranker(vectors: ItemVectors, *, lam: float = LAMBDA_MMR, pool: int = MMR_POOL)`. `rerank(user, items, k)`: `head = items[:pool]`; `V = vectors.vectors([i.book_id for i in head])` **1회 호출**(요청마다 book 단위 호출 금지); `unit` 정규화는 위 4줄 그대로; `sim = unit @ unit.T`; relevance = `items` 점수를 min-max(pool 안, 분모 0 → 1.0) 로 0~1; 그리디 k 회: `mmr = lam·rel − (1−lam)·max_{s∈selected} sim[i, s]`(selected 비면 rel 만). 반환 = 선택 순서로 `dataclasses.replace(item, position=i)` + `items[pool:]` 는 붙이지 않는다(k 개만). **seen 을 다시 넣지 않는다** — 입력 items 만 재배열하므로 자동 보장(`harness.evaluate` L47-52 가 반환 seen 을 ValueError 로 잡는 안전망). λ 는 생성 인자(D-07 "λ=0.5 로 1회만 재실행" 은 app 조립 상수 변경으로).

**테스트(`tests/reranking/test_mmr.py`) 손계산:** 벡터 4개 — `a=(1,0)`, `b=(1,0)`(a 와 동일), `c=(0,1)`, `d=(0.6,0.8)`; 점수 a=1.0 > b=0.9 > c=0.8 > d=0.7. λ=0.7, k=3 → 1위 a, 2위는 b(mmr=0.7·0.67−0.3·1.0=0.17) vs c(0.7·0.33−0=0.23) → **c**, 3위 d vs b… 손으로 확정해 순서 단정 + `ild_at_k(reranked) > ild_at_k(original)`(정확성) + `len == k`·`position` 0..k−1·book_id 집합 ⊂ 입력(계약) + `items` 가 `k` 미만·빈 목록·미지 id(0 벡터) 에서 예외 없음(안전성). `_OneHot`(test_harness L30-37) 재사용 가능.

---

### `src/millie_rec/reranking/guard.py` (reranker, 순서 조정) — NEW

**Analog A — `None` 주입 시 패스스루 분기:** `serving/fallback.py::GlobalPopularFallback` L18-24
```python
    def __init__(self, catalog: Catalog | None) -> None:
        self.catalog = catalog

    def recommend(self, user: UserState, k: int) -> list[ScoredItem]:
        if self.catalog is None:
            return []
```
→ `DifficultyGuard(book_stats: BookStatsSource | None = None, *, top_n: int = K_RANK, resid_z_max: float = GUARD_RESID_Z, min_completed: int = GUARD_MIN_COMPLETED)`. `rerank(user, items, k)`: `if self.book_stats is None or len(user.history) >= min_completed: return items[:k]`(패스스루 — Track A·이력 충분). 위반 판정은 `stats(ids[:top_n])` 1회 → `s.source == "millie_index" and s.resid_z is not None and s.resid_z < resid_z_max`(결측·`category_prior` 는 모집단 제외, D-08). 위반 책을 **상단 N 밖의 첫 자리 뒤로 밀고**(삭제 아님) 다음 책을 끌어올린다: `head = [i for i in items[:top_n] if ok]`, `promoted = items[top_n:]` 에서 채우되 promoted 도 위반이면 건너뜀, 최종 `head + violators + rest` 순으로 `position` 재부여, `[:k]`. **후보 수 보존**(`len(out) == min(len(items), k)`) 단정.

**Analog B — `BookStats` 필드:** `contracts.py` L177-192 (`difficulty`·`source`·`resid_z`). `STATS_SOURCES = ("millie_index", "category_prior", "behavior", "prior")` L83 — 문자열은 `contracts` 상수를 쓰지 말고 `MILLIE_INDEX = "millie_index"` 를 guard 상단에 두거나 `STATS_SOURCES[0]` 로 참조(둘 다 허용, 정본은 contracts).

**docstring 필수 문구(D-08):** "`n_completed` 는 Phase 4 에서 `len(user.history)` 대리값 — Phase 5 `state.py` 가 completion 이벤트 수로 교체". PDF 각주와 같은 문장.

**테스트(`tests/reranking/test_guard.py`):** 가짜 `_FakeStats` 가 book 3 만 `resid_z=-1.5, source="millie_index"`, book 5 는 `resid_z=-2.0, source="category_prior"`(모집단 제외) → items 1..12 점수 내림차순, `top_n=10, k=12`, 신규 유저(`history=()`) → 3 이 10 밖으로, 11 이 안으로, 5 는 그대로, 총 12개·집합 동일(정확성) · `history` 3권 이상이면 무변경 · `book_stats=None` 이면 `items[:k]` 그대로(안전성) · 반환 `ScoredItem` `position` 연속(계약).

---

### `src/millie_rec/app/pipeline.py` (MODIFY, Advisor) + `app/pipeline_kr.py` (NEW 권장)

**현재 조립 함수(L80-82, L97-110):**
```python
def fit_pipelines(train: "pd.DataFrame") -> dict[str, Pipeline]:
    """make eval 용: train 으로 새로 fit. 키는 contracts.VARIANTS 이름 그대로."""
    return {POP: PopPipeline(PopularityRetriever().fit(train))}
```
```python
def build_pipelines(
    artifact: Path = POP_ARTIFACT, *, catalog: Catalog | None = None
) -> dict[str, Pipeline]:
    """서버 기동. 카탈로그 있으면 Track B pop(D-13, Goodbooks 아티팩트는 열지 않음), 없으면 D-10."""
    if catalog is not None:
        return {POP: CatalogPopPipeline(catalog)}
    ...
```
**glue 클래스(Pipeline 구현) — `PopPipeline` L25-43 확장형, 한 개만:**
```python
class StagedPipeline:
    """contracts.Pipeline — retrievers(풀 POOL) → ranker → rerankers(순서대로) → 상위 k."""

    def __init__(self, name: str, retrievers: Sequence[CandidateGenerator], ranker: Ranker,
                 rerankers: Sequence[Reranker] = (), *, pool: int = POOL, meta: Catalog | None = None) -> None: ...

    def recommend(self, user: UserState, k: int) -> list[ScoredItem]:
        cands = [c for r in self.retrievers for c in r.retrieve(user, self.pool)]
        items = self.ranker.rank(user, cands)
        for rr in self.rerankers:
            items = rr.rerank(user, items, k)
        return [replace(i, position=n) for n, i in enumerate(items[:k])]  # + Track B 는 meta 조인
```
`name` 은 인스턴스 속성(Protocol `name: str` 은 클래스·인스턴스 어느 쪽이든 만족 — `tests/serving/test_recommend_level0.py::_FakeNamed` L48-52 가 같은 방식). 4 variant dict(D-01): `pop` = `PopPipeline`(불변) · `cf` = `StagedPipeline("cf", [knn], HybridRanker(channel_weights={itemknn: 1.0}))` · `hybrid` = `[knn, content, pop]` + `HybridRanker()` · `hybrid_div` = hybrid + `[MMRReranker(vectors), DifficultyGuard(None)]`. **`fit_pipelines(train)` → `fit_pipelines(train, books)`** (CONTEXT Integration Points: `ContentVectors` 를 content retriever·MMR 양쪽에 주입). `cmd_eval` L69-70 은 이미 `vectors = ContentVectors(books)` 를 만들고 있으니 `fit_pipelines(sp.train, vectors)` 로 재사용(TF-IDF 1회).

**⚠ 기존 코드 의존(브리프에 명시):** `app/cli.py` L101-102 `pop = pipes.get(VARIANTS[0]); ap = pop.retriever.save(...)` — `pipes["pop"]` 이 `.retriever` 속성을 가진 `PopPipeline` 이어야 한다. `pop` variant 는 `PopPipeline` 그대로 두면 무변경.

**줄 수:** 110 + `StagedPipeline` ≈25 + Track A 조립 ≈20 = ≈155 → **150 초과** → D-11 대로 Track B 조립을 `app/pipeline_kr.py` 로 분리(`build_pipelines_kr(catalog, vectors_kr, *, weights) -> dict`), `pipeline.py::build_pipelines` 는 그것을 호출만. `server.py` 의 `build_pipelines(catalog=catalog)` 호출은 **keyword 만** 유지 — `tests/serving/test_smoke.py` L173·L195 가 `lambda **_: {}` 로 대체하므로 위치 인자를 넣으면 `TypeError`. `load_catalog` 도 `lambda: None`(L171) 이라 **0 인자 호출 유지**(`test_server_catalog.py` L22 동일).

**Track B 재료(D-10):** `catalog.neighbors`(`CatalogKR` L89-91) → `NeighborRetriever(catalog, source="content")` · `VectorsKR.load(DIR_SERVING / VECTORS_KR_NPZ)`(`data/__init__` 공개) → `VectorRetriever(vectors_kr, ids=catalog.popular(n=10**6))` + `MMRReranker(vectors_kr)` · `pop` = `CatalogPopPipeline` 을 `pop` 채널 retriever 로도 쓰려면 `Candidate` 가 필요 → `catalog.popular` 를 감싸는 ≈8줄 `_CatalogPopRetriever` 또는 `PopularityRetriever(ranked=[(b, float(n-i)) for i,b in enumerate(catalog.popular(n=TOP_N))])` 로 **기존 클래스 재사용**(권장 — `PopularityRetriever.__init__` L27-28 이 ranked 주입을 받는다) · `DifficultyGuard(catalog)`(`CatalogKR` 가 `BookStatsSource`) · meta 조인은 `CatalogPopPipeline` L59-75 의 dict 패턴을 `StagedPipeline(meta=catalog)` 가 마지막에 적용. 로더 실패 시 `(OSError, ValueError, KeyError, TypeError)` → `log.exception` + `{POP: CatalogPopPipeline(catalog)}` 만(기동을 막지 않는다, `load_catalog` L85-94 패턴).

---

### `src/millie_rec/app/cli.py` (MODIFY, Advisor — `demo --seeds` · `demo --find`)

**Analog — 서브커맨드 등록·인자 기본값·`func` 디스패치:** L107-124
```python
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("data", help="Goodbooks-10k 멱등 다운로드 + parquet 캐시")
    d.add_argument("--raw", type=Path, default=DIR_RAW / RAW_SUBDIR)
    d.add_argument("--processed", type=Path, default=DIR_PROCESSED)
    d.set_defaults(func=cmd_data)
    e = sub.add_parser("eval", help="등록 variant × 두 상태 평가 → results/")
    e.add_argument("--variant", choices=[ALL, *VARIANTS], default=ALL)
    ...
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    args.func(args)
```
→ `m = sub.add_parser("demo", help="본인 5권 앵커 케이스(stdout 마크다운) · --find 제목 검색")`, `--seeds`(str, `_parse` 는 `serving/api.py::_parse_seeds` L36-43 과 같은 로직을 **중복 정의** — app 은 serving 공개 표면에 `_parse_seeds` 가 없다), `--find`(str), `--serving` (Path, `DIR_SERVING`), `--k`(int, `K_RANK`). `cmd_demo(args)`: `catalog = load_catalog(args.serving)`(`app/pipeline.py` L85) → `None` 이면 `SystemExit("카탈로그 없음 — make millie 후")`(L74 `raise SystemExit(f"...")` 관례). `--find`: `catalog.meta(catalog.popular(n=10**6))` 순회로 `title`·`authors` 부분 일치(대소문자·공백 무시 = `"".join(s.split()).casefold()`, Claude's Discretion) → `book_id·title·authors·categories` 행 출력. `--seeds`: `pipes = build_pipelines(catalog=catalog, …)`; seed 별 `catalog.neighbors(seed, n=5)` → `meta` 조인 → 표(D-13 헤더 `| # | 책 | 저자 | 분야 | 난이도 | 근거 |`, 난이도 ●○○ 3분위 경계는 `catalog.meta(all)` 의 `difficulty` 33/66 분위) → `hybrid_div.recommend(UserState(None, explicit_seeds=seeds), K_RANK)` 표 + `state_weights(user)` 표시 + 가드 발동 여부(guard 전후 상단 N 집합 비교는 pipeline 내부라 알 수 없음 → `DifficultyGuard` 를 별도 호출해 비교하거나 "발동 조건 충족(n_completed=0)" 만 표기, planner 확정) + 고정 문장(`.claude/rules/data.md` "데모 카탈로그의 앵커 이웃은 콘텐츠 유사도다. …"). **`print` 만, `report/` 를 열지 않는다**(D-13). 128 + ≈40줄 → **150 근접** → `cmd_demo` 를 `app/demo_cli.py` 로 분리하고 `cli.py` 는 `set_defaults(func=cmd_demo)` 만(app 내부 import 허용).

**⚠ 기존 테스트 충돌(Advisor 영역 `tests/app/test_cli.py`, D-15 "기존 테스트 단정 수정 금지" 의 예외 = Phase 4 의도된 동작 변경, 브리프에 명시):**
- `test_eval_end_to_end_on_synthetic_parquet` L76-79: `len(states) == 3` · `states[2] == "pop,n20,0.000,0.000,0.000,0"` — 4 variant 등록 시 states 는 헤더 + 8행. `lines[1]` pop 단정은 유지 가능(정렬 `_order` L81-84).
- `test_eval_unregistered_variant_exits` L99-106: `--variant cf` 가 `SystemExit` — cf 등록 후 **실패**. 삭제 또는 `choices` 검증(`argparse` 가 잘못된 이름을 이미 거부)으로 대체.
- 합성 parquet(L28-60) 은 유저 30 × 아이템 40 × 15권, `ts` 없음 → holdout. Item-KNN chunk 크기가 40 보다 커도 동작해야 한다(`min(chunk, n_items)`).
- `tests/app/test_pipeline.py::test_fit_pipelines_keys_are_variants_and_recommend_returns_k` L51-55: `set(pipes) == {"pop"}` → `== set(VARIANTS)` 로, 시그니처 `fit_pipelines(interactions, ContentVectors(books))` 로 갱신(books fixture 없음 — `interactions` 의 아이템 50개로 `pd.DataFrame({COL_ITEM: range(50), "tags": …})` 를 테스트 안에서 만든다).

---

### `src/millie_rec/app/server.py` (MODIFY, Advisor — `weights=` 1줄)

**현재 전문 핵심(L13-21):**
```python
catalog = load_catalog()
app = create_app(
    pipelines=build_pipelines(catalog=catalog),
    fallback=GlobalPopularFallback(catalog),
    catalog=catalog,
    db=Database(resolve_db_path()),
    neighbors=catalog,
    book_stats=catalog,
)
```
→ `from millie_rec.ranking import state_weights` + `weights=state_weights` 1줄 + `build_pipelines(catalog=catalog, weights=state_weights)`(같은 함수 → "표시 혼합비 = 실제 혼합비", D-09). `VectorsKR` 로드는 `build_pipelines` 안에서(`server.py` 는 인자만 채운다, Phase 1 D-09 주석 L11 유지). **import 시점 부작용은 이미 있음**(`load_catalog()` 모듈 수준) — `VectorsKR.load` 4.5MB 추가는 허용 범위지만 실패 시 `None` 으로 강하(`hybrid_div` 미등록 → 기본 variant 는 `default_variant` 로 `hybrid` 가 됨, `compose.py` L24-27).

---

### `src/millie_rec/serving/api.py` (MODIFY — `weights` 인자, 135 → ≤150)

**현재(L66-78, L81-90):**
```python
def _personalized_response(
    pipe: Pipeline, fallback: Pipeline, user: UserState, k: int, t0: float, context: str | None
) -> RecommendResponse:
    """level 0. 파이프라인 예외는 level 3 로 강하 — 500 도 예외 문자열 노출도 없다(Phase 2 D-13)."""
    try:
        items = pipe.recommend(user, k)
    except Exception:
        log.exception("pipeline %s failed; falling back to level 3", pipe.name)
        return _fallback_response(fallback, user, k, t0, context)
    version = f"{pipe.name}{MODEL_VERSION_SUFFIX}"
    return build_response(
        items, model_version=version, level=FALLBACK_PERSONALIZED, k=k, t0=t0, context=context
    )
```
```python
def create_app(
    pipelines: dict[str, Pipeline],
    fallback: Pipeline,
    *,
    catalog: Catalog | None = None,
    db: Database,
    neighbors: Neighbors | None = None,
    book_stats: BookStatsSource | None = None,
    state: object | None = None,
) -> FastAPI:
```
`user_state_weights` 0 고정 자리 = `serving/compose.py::build_response` L58 `user_state_weights=dict(ZERO_WEIGHTS)`. **`compose.py` 는 Phase 5 몫(CONTEXT domain "건드리지 않는 것")** → `api.py` 안에서 `RecommendResponse`(frozen dataclass) 를 `dataclasses.replace(resp, user_state_weights=weights(user))` 로 덮는다(≈4줄): `create_app(..., weights: Callable[[UserState], dict[str, float]] | None = None)` keyword-only 추가(D-09, Phase 1 D-09 규칙 "기본값 있는 인자만 추가") → `_personalized_response(..., weights)` 에 전달 → 성공 경로에서만 `replace`; fallback 경로는 0 유지(백엔드 01 §5 "익명은 가중치 전부 0"). `weights` 호출도 `try` 안에 넣어 예외 시 level 3 강하. 135 + ≈8 = 143줄. `Callable` 은 `collections.abc` 에서. `test_smoke.py` L109 `user_state_weights == ZERO_WEIGHTS`(level 3) 와 `test_recommend_level0.py` 의 level 0 단정(있다면 `ZERO_WEIGHTS` 비교) 을 브리프 전에 grep — level 0 에서 0 을 단정하는 기존 테스트가 있으면 `weights=None` 기본값이 그것을 보호한다.

**테스트(`tests/app/test_variants.py` 또는 `tests/serving/`):** `create_app(pipelines={"pop": _FakePop()}, fallback=…, db=Database(tmp), weights=lambda u: {"alpha": 1.0, "beta": 0.0, "gamma": 0.0})` → `seeds=1,2,3` 응답 `user_state_weights["beta"] == 0.0`(REC-03), 익명은 `ZERO_WEIGHTS`. `_app` 조립 패턴 = `tests/serving/test_recommend_level0.py::_app` L64-69.

---

### `Makefile` (MODIFY, Advisor — L30-31)

```makefile
demo:         ## 본인 5권 cold-start 정성 케이스. 예: make demo SEEDS=1,2,3,4,5
	uv run python -m millie_rec.app.cli demo --seeds $(SEEDS)
```
→ `… demo --seeds $(SEEDS) > report/demo_5books.md && echo "→ report/demo_5books.md"`(D-13). `.PHONY` L2 에 `demo` 이미 있음. `report/` 소유는 사람(architecture.md) — 셸 리다이렉트는 cli 가 여는 것이 아니라 허용.

---

### `tests/app/test_variants.py` (NEW) — 서버 4 variant 상이(D-11)

**Analog A — `fit_pipelines` 키 단정:** `tests/app/test_pipeline.py` L51-55
```python
def test_fit_pipelines_keys_are_variants_and_recommend_returns_k(interactions):
    pipes = fit_pipelines(interactions)
    assert set(pipes) == {"pop"}
    assert all(name in VARIANTS for name in pipes)
    assert len(pipes["pop"].recommend(UserState(None), 5)) == 5
```
→ `set(pipes) == set(VARIANTS)` · 각 `recommend(UserState(None, explicit_seeds=(1,2,3)), 20)` 이 seen 을 안 돌려주고 `len ≤ 20` · `hybrid_div` 와 `hybrid` 의 상위 10 순서가 다르거나 같음(같을 수 있음 — 단정은 "집합 pairwise 비동일" 대신 `evaluate` 의 ValueError 없음 + `ild(hybrid_div) ≥ ild(hybrid)` 를 fixture 로).

**Analog B — 서버 재import + 20권 fixture:** `tests/app/test_server_catalog.py` L20-37 (verbatim)
```python
def _server(tmp_path: Path, monkeypatch, serving_dir: Path):
    monkeypatch.setenv(ENV_DATA_DIR, str(tmp_path))
    monkeypatch.setattr("millie_rec.app.pipeline.load_catalog", lambda: CatalogKR.load(serving_dir))
    sys.modules.pop("millie_rec.app.server", None)
    return importlib.import_module("millie_rec.app.server")


def test_server_injects_catalog_pop_level0_with_korean_titles(
    tmp_path: Path, monkeypatch, millie_serving_sample
):
    server = _server(tmp_path, monkeypatch, millie_serving_sample)
    with TestClient(server.app) as c:
        rec = c.get("/api/recommend", params={"seeds": "1,2,3", "k": 5}).json()
    assert rec["fallback_level"] == FALLBACK_PERSONALIZED
    assert rec["model_version"] == "pop_v1"
```
→ Phase 4: 같은 `_server` 로 `model=` 4종 호출 → `model_version == f"{v}_v1"` 4개 · 상위 k `book_id` 리스트가 pairwise 동일하지 않음(fixture 20권: 엣지는 `(i+d-1)%20+1` 순환 구조 L105-111, 벡터는 `default_rng(SEED)` 랜덤 L116-118, pop 은 `pop_rank == book_id` — 세 채널이 서로 다른 순서를 내므로 성립 기대; **실패하면 fixture 가 아니라 단정을 "4 집합 중 최소 2쌍 상이" 로 완화**, planner 판단) · `model` 없이 호출 → `model_version == "hybrid_div_v1"`(D-11 기본 = `default_variant` 마지막 등록) · `user_state_weights == {"alpha": 1.0, "beta": 0.0, "gamma": 0.0}`(D-09·REC-03) · `rows[0]["items"][0]["title"]` 이 한글(meta 조인). **`VectorsKR` 로드 경로**: `build_pipelines` 가 `catalog` 만 받으면 npz 경로를 알 수 없다 → `load_catalog` 처럼 `serving_dir` 기준 로더 `load_vectors_kr(serving_dir=DIR_SERVING)` 를 `app/pipeline_kr.py` 에 두고 테스트가 같은 방식으로 monkeypatch(`lambda: VectorsKR.load(serving_dir / VECTORS_KR_NPZ)`).

**fixture 사실(`tests/conftest.py` L46-89):** 자격 없는 3권 = 18(외부 호스트)·19(title None)·20(adult-cover) → `popular()` 에 없음. 홀수 id ≥15 는 `difficulty=None`·`category_prior`. `resid_z = (i%7−3)·0.5` → **id 1·8·15 가 `resid_z=-1.5 < -1`, source millie_index(1·8; 15 는 category_prior 라 제외)** → 가드 모집단 = {1, 8}. seeds `1,2,3` 이면 1 은 seen → 8 만 가드 대상 — 서버 가드 발동 테스트에 쓸 수 있는 손계산 사실.

---

## Shared Patterns

### Protocol 구현 클래스 — 상속 없음, `name` 속성, `__init__` 은 주입·인덱스 1회
**Source:** `retrieval/popularity.py` L22-28 · `data/catalog_kr.py` L43-63 · `serving/fallback.py` L13-19 · **Apply to:** `ItemKNNRetriever`·`NeighborRetriever`·`VectorRetriever`·`HybridRanker`·`MMRReranker`·`DifficultyGuard`·`StagedPipeline`. 요청마다 fit·행렬 재계산 금지(serving.md).

### seen 제외 + 넉넉히 뽑기 + `[:k]`
**Source:** `retrieval/popularity.py` L41-46(조기 종료 루프) · `serving/fallback.py` L24 `popular(n=k + len(user.seen))` · **Apply to:** itemknn·content `retrieve`(argpartition 크기 `k + len(seen)`), `StagedPipeline.recommend` 마지막 `[:k]`. 안전망 = `evaluation/harness.py` L47-52 (seen 반환 → ValueError).

### Candidate → ScoredItem 조립(`position`·`source_channels`)
**Source:** `app/pipeline.py::PopPipeline.recommend` L33-43 · `CatalogPopPipeline.recommend` L57-77 · **Apply to:** `HybridRanker.rank`(점수·채널), `StagedPipeline`(position 재부여·meta 조인). `dataclasses.replace` 로 frozen DTO 갱신.

### 가중치 Callable 주입(슬라이스 간 함수 전달)
**Source:** `create_app(..., weights=...)`(D-09) 와 동일 관례 — **Apply to:** `ItemKNNRetriever(weights=)`·`VectorRetriever(weights=)`·`ContentVectors.retrieve` — retrieval 은 ranking 을 import 할 수 없으므로 app 이 `state_weights` 함수 객체를 넘긴다. 기본값 `None` = 성분 가중 1.0.

### 아티팩트 유무·손상 → 로드/fit 분기 + 로그, 기동을 막지 않음
**Source:** `app/pipeline.py::load_catalog` L85-94 · `build_pipelines` L103-110 · **Apply to:** `item_neighbors.npz`(있고 meta 일치 → load, 아니면 fit 후 save) · `VectorsKR` 로더. 예외 집합 `(OSError, ValueError, KeyError, TypeError)`, `log.info`(부재)/`log.exception`(손상).

### 0-벡터 안전 cosine
**Source:** `evaluation/metrics.py::ild_at_k` L34-36 (`np.where(norms == 0, 1.0, norms)`) · **Apply to:** MMR 유사도 행렬, content `retrieve` 의 사용자 벡터(seeds 전부 미지 id → q=0 → 후보 없음).

### 테스트 3종 구분 주석 + 손계산 상수 + 가짜 Protocol
**Source:** `tests/retrieval/test_popularity.py` L25·L41·L58 (`# ── 계약 ──`/`# ── 정확성 ──`/`# ── 안전성 ──`) · `tests/evaluation/test_harness.py::_FakePipeline`·`_OneHot` L13-37 · **Apply to:** 신규 테스트 7개. `pytest.approx` 로 float. 상수는 import 하지 않고 손으로 적는다(`test_vectors_kr.py` L10 `DIM = 8  # conftest … 의 SAMPLE_VECTOR_DIM`).

### 서버 재import 배선 테스트
**Source:** `tests/app/test_server_catalog.py::_server` L20-24 · `tests/serving/test_smoke.py` L164-204 · **Apply to:** `test_variants.py`. `ENV_DATA_DIR` → `tmp_path`, 로더 monkeypatch(0 인자 lambda), `sys.modules.pop` 후 `importlib.import_module`, `with TestClient(...)`(lifespan).

---

## 기존 테스트와의 충돌 — Phase 4 가 갱신해야 하는 단정(Advisor 영역, 의도된 동작 변경)

| 테스트 | 현재 단정 | Phase 4 후 | 조치 |
|---|---|---|---|
| `tests/app/test_pipeline.py::test_fit_pipelines_keys_are_variants_and_recommend_returns_k` L51-55 | `set(pipes) == {"pop"}`, `fit_pipelines(interactions)` 1인자 | 4 variant, `(train, vectors)` | 단정·호출 갱신 |
| `tests/app/test_cli.py::test_eval_end_to_end_on_synthetic_parquet` L76-79 | `len(states) == 3`, `states[2] == "pop,n20,…"` | 헤더 + 8행 | `len == 9`, pop 행 인덱스 유지 |
| `tests/app/test_cli.py::test_eval_unregistered_variant_exits` L99-106 | `--variant cf` → `SystemExit` | cf 등록됨 | 삭제(argparse `choices` 가 오타를 이미 422 격으로 거부) |
| `tests/serving/test_smoke.py` L171-173·L193-195 | `load_catalog` 0인자·`build_pipelines(**_)` | 불변이어야 함 | `server.py` 는 keyword 호출만 유지(위 server.py 절) |
| `tests/test_architecture.py` | star 의존 | 불변 | **고치지 않는다** |

---

## No Analog Found

repo 에 코드 아날로그가 없어 규칙·CONTEXT 수식으로 제안한 것(planner 는 이 스니펫을 브리프에 인라인):

| File | Role | 부족한 부분 | 대체 정본·제안 |
|---|---|---|---|
| `retrieval/itemknn.py` fit | scipy.sparse 이진 user×item cosine, 아이템당 top-50 | `scipy` import 0건 | 아래 스니펫 A |
| `ranking/hybrid.py` | 채널 min-max + 가중합 | 순수 산술 | 아래 스니펫 B |
| `reranking/mmr.py` | 그리디 MMR 루프 | 없음 | 아래 스니펫 C(거리 계산은 `ild_at_k` 재사용) |

**스니펫 A — chunked top-k Item-KNN(D-04 "dense 100M 금지", 아키 §8 리스크 "메모리"):**
```python
KNN_TOP = 50  # D-04 아이템당 이웃. freeze
CHUNK = 500  # (CHUNK × n_items) dense 한 장 = 500×10k×8B = 40MB


def fit(self, train: "pd.DataFrame") -> "ItemKNNRetriever":
    """이진 user×item(평점 무관, Phase 2 D-05) → 열 L2 정규화 → 청크별 item-item cosine → top-50."""
    import scipy.sparse as sp

    users, u_idx = np.unique(train[COL_USER].to_numpy(), return_inverse=True)
    items, i_idx = np.unique(train[COL_ITEM].to_numpy(), return_inverse=True)
    x = sp.csr_matrix((np.ones(len(train), dtype=np.float32), (u_idx, i_idx)), shape=(len(users), len(items)))
    x.data[:] = 1.0  # 중복 (user,item) 행이 합쳐져 2 가 되지 않게
    norms = np.sqrt(np.asarray(x.multiply(x).sum(axis=0)).ravel())
    xn = x @ sp.diags(1.0 / np.where(norms == 0, 1.0, norms))  # 열 L2=1
    xnt = xn.T.tocsr()  # (n_items, n_users)
    n = len(items); top = min(KNN_TOP, n - 1)
    nbr_ids = np.full((n, KNN_TOP), -1, dtype=np.int64); nbr_sims = np.zeros((n, KNN_TOP), dtype=np.float32)
    for s in range(0, n, CHUNK):
        block = (xnt[s : s + CHUNK] @ xn).toarray()  # (chunk, n_items) cosine
        rows = np.arange(block.shape[0]); block[rows, s + rows] = -1.0  # self 제외
        idx = np.argpartition(-block, top, axis=1)[:, :top]
        sims = np.take_along_axis(block, idx, axis=1)
        order = np.argsort(-sims, axis=1, kind="stable")
        idx, sims = np.take_along_axis(idx, order, axis=1), np.take_along_axis(sims, order, axis=1)
        keep = sims > 0  # 공동 소비 0 은 이웃이 아니다
        nbr_ids[s : s + CHUNK, :top] = np.where(keep, items[idx], -1); nbr_sims[s : s + CHUNK, :top] = np.where(keep, sims, 0.0)
    self._ids, self._nbr_ids, self._nbr_sims = items, nbr_ids, nbr_sims
    self._index = {int(b): i for i, b in enumerate(items.tolist())}
    return self
```
비용 추정: Goodbooks 필터 후 10k 아이템·6M 비영 → 청크 20개, 각 sparse·sparse 곱 (500×53k)·(53k×10k) ≈ 1~3s → 전체 30~60s, `make eval` 7s 에서 ≈1분으로 증가 → npz 캐시가 의미 있다(D-04). 합성 fixture(50 아이템)에선 즉시. `np.argpartition(-block, top)` 은 `top < n_items` 필수 → `top = min(KNN_TOP, n-1)` 가드(합성 `_train()` 아이템 3~4개에서 ValueError 방지 — Phase 3 `TruncatedSVD` 가드와 같은 함정).

**스니펫 B — 채널 min-max + 가중합(D-03):**
```python
W_CF, W_CONTENT, W_POP = 0.5, 0.3, 0.2  # D-03 초기값. Day 3 ≤3조합 그리드 1회 후 freeze
CHANNEL_WEIGHTS = {SOURCE_ITEMKNN: W_CF, SOURCE_CONTENT: W_CONTENT, SOURCE_POPULARITY: W_POP}


def _minmax(cands: list[Candidate]) -> dict[int, float]:
    """채널 안 0~1. 후보 1개·분산 0 이면 1.0(Claude's Discretion)."""
    if not cands:
        return {}
    lo, hi = min(c.score for c in cands), max(c.score for c in cands)
    span = hi - lo
    return {c.book_id: (c.score - lo) / span if span > 0 else 1.0 for c in cands}
```
`rank`: `by_ch = defaultdict(list)` → `norm = {ch: _minmax(v)}` → `books = ∪ keys` → `score[b] = Σ_ch w[ch]·norm[ch].get(b, 0.0)` + gap 항 → 정렬 `(-score, book_id)`(동률 결정적 — `python.md` "같은 입력 → 같은 결과").

**스니펫 C — MMR 그리디(D-07, 거리 = 1 − cosine, λ=0.7, 풀 50):**
```python
def rerank(self, user: UserState, items: list[ScoredItem], k: int) -> list[ScoredItem]:
    head = list(items[: self.pool])
    if len(head) <= 1:
        return [replace(i, position=n) for n, i in enumerate(head[:k])]
    v = self.vectors.vectors([i.book_id for i in head])  # 1회 호출
    norms = np.linalg.norm(v, axis=1, keepdims=True)
    unit = v / np.where(norms == 0, 1.0, norms)  # metrics.ild_at_k L34-35 그대로
    sim = unit @ unit.T
    rel = _minmax_scores([i.score for i in head])  # 0~1
    selected: list[int] = []
    remaining = set(range(len(head)))
    while remaining and len(selected) < k:
        def mmr(i: int) -> float:
            div = max(sim[i, j] for j in selected) if selected else 0.0
            return self.lam * rel[i] - (1 - self.lam) * div
        best = min(remaining, key=lambda i: (-mmr(i), i))  # 동률은 원 순위
        selected.append(best); remaining.remove(best)
    return [replace(head[i], position=n) for n, i in enumerate(selected)]
```
k ≤ 50·풀 50 이라 O(k·pool) 파이썬 루프 ≈2,500 회/유저 → 2,000 유저 × 2 상태 ≈ 수 초. 허용(python.md "유저 단위 루프는 평가에서만" — 여기는 유저 1명 내부 루프).

---

## 적용 규칙 발췌 (`/Users/shinwonchul/Documents/신원철/밀리의서재/.claude/rules/`)

| 경로 | 적용 rule 파일 |
|---|---|
| `src/millie_rec/{retrieval,ranking,reranking}/*.py` · `tests/{retrieval,ranking,reranking}/**` | `python.md` · `python-tdd.md` · `architecture.md` · `simplicity.md` · (retrieval 표기) `data.md` Track B 절 |
| `src/millie_rec/app/*.py` · `tests/app/**` | `architecture.md`(Advisor 전용) · `python.md` · `local-run.md` |
| `src/millie_rec/serving/api.py` · `tests/serving/**` | `serving.md` · `python-tdd.md` · `codex-review.md`(보안 표면 아님 → 선택) |
| `results/**` · draft §4-1 | `evaluation.md` · `report.md` |
| `Makefile` | `local-run.md`(`make smoke` 완료 기준) |

**verbatim 인용(브리프에 그대로 인라인):**
- `architecture.md` import: "슬라이스(`app` 제외)는 `millie_rec.contracts`와 **자기 슬라이스 내부**만 import한다. 다른 슬라이스 import 금지." / "슬라이스가 다른 슬라이스의 결과를 필요로 하면(예: MMR·ILD가 아이템 벡터 필요) `contracts.py`의 Protocol(`ItemVectors`, `Pipeline`)로 받고, `app/`이 실제 객체를 주입한다." / "`app`은 다른 슬라이스의 **공개 이름만** import한다" / "`tests/test_architecture.py`가 위 규칙을 정적으로 검사한다. … **테스트를 고치지 않는다.**"
- `architecture.md` 소유권: "`artifacts/` | retrieval | `fit`/`load`는 retrieval 안에서만" / "`report/` | 사람 | evaluation이 `figures/`에 그림을 쓰는 것은 허용" / "`contracts.py` `pyproject.toml` `Makefile` `app/`은 Advisor 전용. Worker가 필요하다고 판단하면 수정하지 말고 보고한다."
- `architecture.md` shared 금지: "같은 코드가 **3개** 슬라이스에서 필요해질 때 Advisor 승인으로 `millie_rec/_shared/<topic>.py` 하나를 만든다. 그 전까지 중복은 허용한다. 5일 프로젝트에서는 중복 < 결합." → `SOURCE_*` 상수 retrieval·ranking·serving·app 중복 허용(CONTEXT Deferred "contracts 승격은 세 번째 필요 시").
- `simplicity.md`: "파일 150줄 이하(`src/` 파이썬). 넘으면 관심사가 2개다." / "함수 우선. 클래스는 `contracts.py`의 Protocol을 만족시킬 때만." / "설정은 모듈 상단 대문자 상수." / "Day 3 종료 후: 새 모델·후보 통로·feature 금지. 파라미터 튜닝은 Day 4 시작 전까지만." / "돌아가는 Item-KNN > 완벽한 ALS."
- `python.md`: "행렬 연산은 numpy/scipy.sparse. 파이썬 루프로 유저×아이템을 돌지 않는다. 유저 단위 루프는 평가에서만 허용." / "난수는 `millie_rec.contracts.SEED` 하나." / "완료 전 순서대로: `uv run ruff format . && uv run ruff check . && uv run pytest --no-header`."
- `python-tdd.md`: "**Red는 `AssertionError`(의도한 단정 실패) 메시지로 확인**한다. `ImportError`·`SyntaxError`·collection error는 Red가 아니다." / "슬라이스마다 **최소 3종**: ① 계약 준수 ② 정확성(손계산 가능한 소형 예제) ③ 안전성(누수 / 경계 / fallback)" / "`-q` 는 pyproject addopts 에 이미 있다 … `-qq` 가 되어 'N passed' 요약 줄이 사라진다".
- `evaluation.md`: "`contracts.VARIANTS` 순서 그대로: 1. `pop` 2. `cf`(Item-KNN) 3. `hybrid`(cf + content/explicit-seed 병합) 4. `hybrid_div`(+MMR). 다른 이름 금지" / "평가 대상은 `contracts.Pipeline` 하나다. evaluation은 retriever·ranker를 직접 알지 않는다." / "**PDF 숫자는 이 파일(`results/latest.csv`)에서만 복사한다.** 소수 3자리." / 해석 템플릿 "MMR 적용으로 NDCG@10은 x→y로 소폭 하락했지만 ILD@10은 a→b로 개선됐다. …"
- `data.md`: "Track B에는 유저 로그가 없다. 데모 variant `cf`·`hybrid`의 이웃 채널은 content_sim이며 `Candidate.source`·`ScoredItem.source_channels`는 **`content`**로 표기한다. `itemknn`이라 쓰지 않는다." / 고정 문장 "데모 카탈로그의 앵커 이웃은 콘텍츠 유사도다. 협업 필터링(Item-KNN)의 Recall·NDCG는 유저 단위 로그가 있는 Goodbooks(Track A)에서만 측정하며 두 트랙의 숫자를 섞지 않는다." / "결측 책은 가드 모집단 제외·UI 미표시·`L_user` 가중 0."
- `serving.md`: "`create_app(pipelines: dict[str, Pipeline], fallback: Pipeline, *, catalog: Catalog | None = None, db: Database, neighbors: Neighbors | None = None, book_stats: BookStatsSource | None = None, state=None) -> FastAPI` — `fallback` 뒤는 keyword-only" (D-09 로 `weights` 추가 — 문구 갱신은 Advisor) / "서빙 점수 함수는 `retrieval/`·`ranking/` 슬라이스 함수를 app이 주입한 그대로(skew 방지)." / "artifacts는 기동 시 1회 로드 … 요청마다 fit·재계산 금지."
- `local-run.md`: "**모든 브리프의 완료 기준에 로컬 스모크를 넣는다:** `uv run pytest --no-header` + `make smoke`" / "`artifacts/serving/`이 비어 있으면 빈 `trending` 행 + level 3."

---

## Metadata

**Analog search scope:** `src/millie_rec/**`(contracts · retrieval 3 · ranking/reranking `__init__` · data 7 · evaluation 4 · serving 5 · app 4) · `tests/**`(conftest · retrieval 2 · evaluation 1 · app 4 · serving 2 · test_architecture) · `Makefile` · `pyproject.toml` · `.gitignore` · `results/*` · `artifacts/**` 크기·shape · `report/draft.md` `[Phase 4]` 마커 위치(L104·106·192-198·233) · `.claude/rules/{architecture,simplicity,python,python-tdd,evaluation,serving,data,report,local-run}.md`
**Files scanned:** 31 code/test + 9 rules + 4 build/result
**실측 보조:** `uv run pytest --no-header` 255 passed / 1 failed(의도) · `grep -rn "scipy\|sparse" src/ scripts/` → 0 · `artifacts/serving` books 9,450 / vectors (8,708, 128) float32 / edges src 9,450 · `interactions.parquet` 5,976,479 × 5
**Pattern extraction date:** 2026-09-05
**Codegraph:** 미사용(Phase 3 와 동일 이유 — 파일 수 소규모라 직접 Read 가 빨랐음. 인덱스 `millie-rec/.codegraph/`, 호출 시 `projectPath` 필수)
