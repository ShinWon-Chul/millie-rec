# Phase 2: Track A 정량 평가 기반 - Pattern Map

**Mapped:** 2026-09-05
**Files analyzed:** 16 source files (13 new + 3 modified) + 9 test files
**Analogs found:** 16 / 16 (data·retrieval·evaluation 슬라이스는 `__init__.py` 껍데기만 있어 분석 대상 파일의 아날로그는 전부 `serving/`·`contracts.py`·`scripts/`·`tests/`에서 가져왔다 — 역할 일치(role-match)가 최대치이며 정확 일치(exact)는 없다)

## 기준선 (실측 2026-09-05, 이 페이즈 시작 직전)

| 항목 | 값 |
|---|---|
| `uv run pytest --no-header` | **104 passed, 2 skipped**, 1.60s (Python 3.11.6, `-q`는 `pyproject.toml` L38 `addopts`에 이미 있음) |
| `uv run ruff check .` | All checks passed (`line-length = 100`, `target-version = "py311"`, `select = ["E","F","I","UP","B"]`, `extend-exclude = ["demo"]` — `pyproject.toml` L27-34) |
| git | `8e5172b`, 워킹트리에 `.gitignore`·`.planning/*` 수정만 |
| `.gitignore` | `data/raw/*`·`data/processed/*`·`artifacts/*` 무시, `!artifacts/serving/`·`!**/.gitkeep`·`!report/figures/*.png` 예외. `results/`는 **무시 목록에 없음 = 커밋 대상**. `*.db`·`data/local/` 무시 (`.gitignore` L1-8, L20-22, L30-32) |
| 디렉터리 현황 | `data/processed/` 비어 있음(Track B parquet 미생성) · `data/raw/`에 밀리 수집물만(Goodbooks 없음) · `results/`·`report/figures/`·`artifacts/serving/`은 `.gitkeep`만 |
| `Makefile` | `data`(L7-8) → `uv run python -m millie_rec.app.cli data` · `eval`(L24-25) → `cli eval --variant all` · `smoke`(L33-40) 8010 포트, `seeds=1,2,3&k=5` · `demo`(L27-28) `cli demo --seeds`는 Phase 4 몫 |

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `src/millie_rec/data/load.py` | data loader (download + parquet cache) | file-I/O · batch | `scripts/build_millie_catalog.py` (parquet 쓰기·경로 상수) + `serving/db.py` (경로 해석·mkdir) | role-match |
| `src/millie_rec/data/split.py` | transform (pure) | transform | `tests/conftest.py::interactions` (컬럼 상수·`default_rng(SEED)`) | role-match |
| `src/millie_rec/data/onboarding.py` | transform → `UserState` factory | transform | `contracts.UserState` + `serving/fallback.py` (seen 사용) | role-match |
| `src/millie_rec/data/labels.py` | utility (pure predicate) | transform | `scripts/build_millie_catalog.py::_present` (1줄 docstring 순수 함수) | role-match |
| `src/millie_rec/data/__init__.py` | public surface | — | `serving/__init__.py` | **exact** |
| `src/millie_rec/retrieval/popularity.py` | model (`CandidateGenerator` 구현, fit/save/load) | batch → request-response | `serving/fallback.py::GlobalPopularFallback` (Protocol 구현 클래스 형태·seen 제외) + `scripts/export_millie_serving.py::_write` (json 저장) | role-match |
| `src/millie_rec/retrieval/content.py` | model (`ItemVectors` 구현, TF-IDF) | batch → transform | `scripts/build_millie_edges.py::similarity` (repo 유일 `TfidfVectorizer` 사용) | role-match |
| `src/millie_rec/retrieval/__init__.py` | public surface | — | `serving/__init__.py` | **exact** |
| `src/millie_rec/evaluation/metrics.py` | utility (pure metric functions) | transform | 없음 — 규칙 `.claude/rules/evaluation.md` 지표 정의가 유일한 정본 | no analog (규칙 인용) |
| `src/millie_rec/evaluation/harness.py` | service (user loop, Pipeline 소비) | batch | `serving/api.py::_fallback_response` (Pipeline 호출·예외 격리) + `contracts.EvalResult` | role-match |
| `src/millie_rec/evaluation/report.py` | writer (csv·json) | file-I/O | `scripts/build_millie_catalog.py::coverage`+`build` (json.dumps ensure_ascii·datetime UTC) | role-match |
| `src/millie_rec/evaluation/figures.py` | writer (matplotlib png) | file-I/O | 없음 (repo에 matplotlib 사용 0) | no analog |
| `src/millie_rec/evaluation/__init__.py` | public surface | — | `serving/__init__.py` | **exact** |
| `src/millie_rec/app/pipeline.py` | assembly (variant dict, Candidate→ScoredItem glue) | request-response | `serving/fallback.py::GlobalPopularFallback.recommend` (ScoredItem 생성 형태) + `app/server.py` (공개 표면 import) | role-match |
| `src/millie_rec/app/cli.py` | CLI (argparse subcommands) | batch | `scripts/build_millie_catalog.py::main` (argparse + `DIR_*` 기본값 + print 요약) | role-match |
| `src/millie_rec/app/server.py` (MODIFY) | entrypoint | — | 자기 자신 L10 (`pipelines={}` 자리만) | exact |
| `src/millie_rec/serving/api.py` (MODIFY) | controller | request-response | 자기 자신 L119-126 + `_fallback_response` | exact |
| `tests/data/test_{load,split,onboarding,labels}.py` | test | — | `tests/conftest.py` fixture + `tests/data/test_millie_edges.py` 구조 | role-match |
| `tests/retrieval/test_{popularity,content}.py` | test | — | `tests/serving/test_smoke.py::test_fallback_with_catalog_excludes_seeds_and_marks_popularity` | role-match |
| `tests/evaluation/test_{metrics,harness}.py` | test | — | `tests/conftest.py::item_vectors` + `_Boom`/`_FakeCatalog` 가짜 객체 패턴 | role-match |
| `tests/serving/test_recommend_level0.py` | test | — | `tests/serving/test_smoke.py::_app`·`_Boom`·level 3 단정 | **exact** |

---

## Pattern Assignments

### 0. 모든 신규 `.py` 파일 공통 — 모듈 머리 형태

**Analog:** `src/millie_rec/serving/fallback.py` L1-10, `serving/db.py` L1-15

```python
"""fallback cascade — Phase 1 은 level 3 만. level 1·2 는 Phase 5 증분(아키텍처 01 §3-11)."""

from collections.abc import Sequence

from millie_rec.contracts import Catalog, Row, ScoredItem, UserState

TRENDING_ROW_ID = "trending"  # contracts.ROW_IDS 안
TRENDING_TITLE = "지금 많이 읽는 책"  # 백엔드 01 §5 응답 예시. Phase 5 compose.py 가 재사용
```

규칙(복사할 것): ① 1줄 모듈 docstring에 정본 절 참조 ② stdlib → 서드파티 → `millie_rec.contracts` 순 import(ruff `I`) ③ 설정은 모듈 상단 대문자 상수 + 뒤 `#` 주석으로 정본 위치 ④ `log = logging.getLogger(__name__)`(api.py L27) ⑤ 파일 ≤150줄.

**Import 허용 형태(`tests/test_architecture.py` L37-42가 정적 검사):**
- 슬라이스 파일(`data/*`, `retrieval/*`, `evaluation/*`, `serving/*`): `from millie_rec.contracts import …` + 자기 슬라이스 내부(`from millie_rec.data.labels import is_positive`)만. **다른 슬라이스 import = 즉시 실패.**
- `app/*`: `from millie_rec.retrieval import PopularityRetriever` ✅ / `from millie_rec.retrieval.popularity import …` ❌ (L41-42 "app 은 공개 표면만").
- 누구도 `millie_rec.app` import 금지(L37-38). tests는 자유.
- 슬라이스 안에 `utils/`·`common/`·`helpers/`·`shared/` 폴더 금지(L50-63).

---

### `src/millie_rec/data/__init__.py`, `retrieval/__init__.py`, `evaluation/__init__.py` (public surface)

**Analog:** `src/millie_rec/serving/__init__.py` L1-17 (exact)

```python
"""serving 슬라이스 공개 표면. 다른 슬라이스는 여기 있는 이름만 import 할 수 있다."""

from millie_rec.serving.api import create_app
from millie_rec.serving.db import Database, resolve_db_path
from millie_rec.serving.fallback import GlobalPopularFallback
from millie_rec.serving.schemas import API_VERSION, EventIn, RecommendOut

__all__ = [
    "API_VERSION",
    "Database",
    ...
]
```

현재 상태(교체 대상): `data/__init__.py` L3 `__all__: list[str] = []`. Phase 2 후 `__all__`에 들어갈 이름(CONTEXT "파일 분할"): data — `load_interactions` `load_books` `split` `mask_onboarding` `is_positive`(+ 필요 시 `download_goodbooks`, `TEST_FRAC`류 상수는 노출 안 함) / retrieval — `PopularityRetriever` `ContentVectors` / evaluation — `recall_at_k` `ndcg_at_k` `ild_at_k` `evaluate` `write_results`(+`plot_eval_bar`). `__all__`은 알파벳 정렬(ruff `RUF022`는 미선택이나 기존 파일이 정렬돼 있음).

---

### `src/millie_rec/data/load.py` (loader, file-I/O)

**Analog A — 경로 상수·mkdir·parquet 쓰기:** `scripts/build_millie_catalog.py` L15, L239-245

```python
from millie_rec.contracts import DIR_PROCESSED, DIR_RAW, FILE_ID_MAP
...
    out_dir.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out_dir / "books_kr.parquet", index=False)
    (out_dir / "millie_raw_coverage.json").write_text(
        json.dumps(coverage(records, meta), ensure_ascii=False, indent=2), encoding="utf-8"
    )
```

**Analog B — 멱등 존재 검사(`if not path.exists()` 스타일):** `scripts/build_millie_catalog.py` L102-104, `serving/db.py` L27-30

```python
def _read_id_list(path: Path) -> list[str]:
    if not path.exists():
        return []
```
```python
    def __init__(self, path: Path) -> None:
        self.path = path
        self._local = threading.local()
        self.path.parent.mkdir(parents=True, exist_ok=True)
```

**Analog C — 컬럼 상수로 DataFrame 조립:** `tests/conftest.py` L7, L17-27

```python
from millie_rec.contracts import COL_EVENT, COL_ITEM, COL_RATING, COL_TS, COL_USER, SEED
...
    df = pd.DataFrame(
        {
            COL_USER: ...,
            COL_ITEM: ...,
            COL_TS: ...,
            COL_EVENT: "completion",
            COL_RATING: ...,
        }
    )
```

**Analog D — dtype 강제(`Int64` nullable):** `scripts/build_millie_catalog.py` L203-207

```python
    for col in INT_COLS:
        df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")
    df["book_id"] = df["book_id"].astype("int64")
```

**contracts 심볼:** `DIR_RAW`, `DIR_PROCESSED`, `COL_USER`, `COL_ITEM`, `COL_TS`, `COL_EVENT`, `COL_RATING`, `EVENT_TYPES`("rating" 포함, L46).
**모듈 상수(CONTEXT):** `GOODBOOKS_URL_BASE`(zygmuntz/goodbooks-10k raw), `FILES=("ratings.csv","books.csv","book_tags.csv","tags.csv")`, `MIN_USER_INTERACTIONS=5`, `MIN_ITEM_INTERACTIONS=5`, `TOP_TAGS=20`, `NOISE_TAGS=(…)`.
**함정(CONTEXT specifics):** `book_tags.csv` 키는 `goodreads_book_id` → `books.csv`로 `book_id` 매핑 필수. `interactions.parquet` `ts`는 전부 None(nullable) — `split()`의 holdout 분기 트리거. 네트워크는 `make data`에서만, 테스트는 다운로드 금지.
**출력 books.parquet 계약 컬럼(data.md Track B와 이름 공유):** `book_id title authors image_url average_rating ratings_count original_publication_year categories(빈 리스트) subcategories tags`.

---

### `src/millie_rec/data/split.py` (transform, pure)

**Analog:** `tests/conftest.py` L15 (rng), `scripts/build_millie_catalog.py` L193-208 (pandas 순수 함수·`reset_index(drop=True)`)

```python
    rng = np.random.default_rng(SEED)
```

**계약 형태 제안(analog 없음 — 규칙 인용):** `.claude/rules/data.md` "Track A split: `split.py` 함수 하나 — `ts` 있으면 전역 시점 temporal(`train.ts.max() < test.ts.min()` 단언), 없으면 유저별 random holdout(seed). 결과 json에 `split_mode` 기록." + CONTEXT D-02 `test_frac=0.2`.

반환은 dict를 API 경계로 넘기지 않는 규칙(`python.md`)에 따라 `frozen dataclass` 또는 `tuple[pd.DataFrame, pd.DataFrame, str]` — planner 판단. `contracts`에 `Split` DTO가 없으므로 슬라이스 내부 dataclass로(계약 변경 금지).

**contracts 심볼:** `SEED`, `COL_USER`, `COL_TS`. **모듈 상수:** `TEST_FRAC = 0.2`.
**테스트 필수(D-16):** temporal 분기 `train[COL_TS].max() < test[COL_TS].min()` · holdout 분기 `split_mode == "holdout"` + 유저별 비율. holdout 테스트는 fixture를 복사해 `df[COL_TS] = None`으로 만든다(CONTEXT "Reusable Assets").

---

### `src/millie_rec/data/onboarding.py` (transform → `UserState`)

**Analog — `UserState` 정의와 `.seen`:** `src/millie_rec/contracts.py` L122-135 (verbatim)

```python
@dataclass(frozen=True, slots=True)
class UserState:
    """추천 입력. train 구간 기록과 explicit seeds 만 — test 라벨은 절대 넣지 않는다."""

    user_id: int | None
    explicit_seeds: tuple[int, ...] = ()  # 온보딩 5권 (strong positive seed)
    history: tuple[int, ...] = ()  # long-term: train 구간 소비
    session: tuple[int, ...] = ()  # 최근 세션 (MVP 에서는 비어 있을 수 있음)
    context: dict[str, str] = field(default_factory=dict)  # 독서 시간대 등

    @property
    def seen(self) -> frozenset[int]:
        """추천에서 제외할 아이템."""
        return frozenset(self.explicit_seeds) | frozenset(self.history) | frozenset(self.session)
```

**두 상태 조립 형태(CONTEXT D-04):**
- n=0: `UserState(user_id=u, explicit_seeds=seeds, history=())`
- n≥k: `UserState(user_id=u, explicit_seeds=seeds, history=tuple(train_items - set(seeds)))`, `K_HISTORY=20` 이상인 유저만.

**contracts 심볼:** `UserState`, `N_ONBOARD_SEEDS`(=5), `SEED`, `COL_USER`, `COL_ITEM`, `COL_RATING`. 같은 슬라이스 `labels.is_positive`는 `from millie_rec.data.labels import is_positive`로 허용.
**모듈 상수:** `K_HISTORY = 20`, `N_TEST_USERS = 2000`.
**테스트 필수(D-16):** 반환 구조에 negative 필드가 없다(`UserState`의 5필드만) · seeds ⊂ 긍정(rating≥4) · `len(seeds) == N_ONBOARD_SEEDS`.

---

### `src/millie_rec/data/labels.py` (pure predicate)

**Analog — 1줄 docstring 순수 함수:** `scripts/build_millie_catalog.py` L45-51

```python
def _present(value: object) -> bool:
    """None·빈 문자열·빈 리스트는 결측. 숫자 0 은 값이다."""
    if value is None:
        return False
```

**형태:** `POSITIVE_MIN_RATING = 4.0` 상수 + `is_positive(df: pd.DataFrame) -> pd.Series`(벡터화, `df[COL_RATING] >= POSITIVE_MIN_RATING`). 근거: 결정 '착수 전 운영 결정 4건'(../.assets/개발일지/2026-09-04_Day0.5_브레인스토밍과_데모명세.md 항목 D45 — `rating≥4`). **contracts 심볼:** `COL_RATING`.

---

### `src/millie_rec/retrieval/popularity.py` (`CandidateGenerator` 구현)

**Analog A — Protocol을 만족하는 클래스 형태(유일한 기존 구현):** `src/millie_rec/serving/fallback.py` L13-34

```python
class GlobalPopularFallback:
    """contracts.Pipeline 구현. catalog 없으면 빈 목록(level 3, 스켈레톤)."""

    name = "fallback"

    def __init__(self, catalog: Catalog | None) -> None:
        self.catalog = catalog

    def recommend(self, user: UserState, k: int) -> list[ScoredItem]:
        if self.catalog is None:
            return []
        ids = [b for b in self.catalog.popular(n=k + len(user.seen)) if b not in user.seen][:k]
        return [
            ScoredItem(
                book_id=b,
                score=float(len(ids) - i),
                source=SOURCE_POPULARITY,
                position=i,
                source_channels=(SOURCE_POPULARITY,),
            )
            for i, b in enumerate(ids)
        ]
```

복사할 것: 클래스 속성 `name = "pop"`(Protocol이 `name: str` 요구), `k + len(user.seen)`만큼 넉넉히 뽑고 `user.seen` 필터 후 `[:k]`, `score=float(...)`.

**Analog B — 만족해야 할 Protocol:** `src/millie_rec/contracts.py` L289-295, L211-215 (verbatim)

```python
class CandidateGenerator(Protocol):
    """retrieval 슬라이스. fit 은 train 구간만 받는다."""

    name: str

    def fit(self, train: "pd.DataFrame") -> "CandidateGenerator": ...
    def retrieve(self, user: UserState, k: int) -> list[Candidate]: ...
```
```python
@dataclass(frozen=True, slots=True)
class Candidate:
    book_id: int
    source: str  # "popularity" | "itemknn" | "content" | "explicit" (데모 카탈로그 이웃 = content)
    score: float
```

**Analog C — json 아티팩트 저장(크기 단언·mkdir):** `scripts/export_millie_serving.py` L71-76

```python
def _write(path: Path, payload: object) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    size = path.stat().st_size
    assert size < MAX_BYTES, f"{path.name} {size}B ≥ {MAX_BYTES}B — 서빙 산출물 상한 초과"
    return size
```

**contracts 심볼:** `Candidate`, `CandidateGenerator`, `UserState`, `COL_ITEM`, `DIR_ARTIFACTS`. `source="popularity"` 리터럴은 `fallback.py` L10 `SOURCE_POPULARITY`와 같은 값이지만 serving import 불가 → 같은 이름 상수를 retrieval 안에 **중복 정의**한다(architecture.md "5일 프로젝트에서는 중복 < 결합").
**모듈 상수:** `ARTIFACT_NAME = "popularity.json"`, `TOP_N = 1000`(D-10, `K_MAX(100)+seen 여유`).
**save/load:** `save(path: Path | None = None)` → `DIR_ARTIFACTS / ARTIFACT_NAME`에 `{"name": "pop", "items": [[book_id, count], …]}`; `@classmethod load(path) -> PopularityRetriever`. fit/load는 retrieval 안에서만(architecture.md 산출물 소유권 표 `artifacts/` = retrieval).
**테스트 필수(D-16):** `user.seen` 제외 · `fit(train)`만 받음(test 행 카운트 미포함 단정) · save/load 라운드트립(`tmp_path`).

---

### `src/millie_rec/retrieval/content.py` (`ItemVectors` 구현, 벡터 부분만)

**Analog — repo 유일 TF-IDF 사용:** `scripts/build_millie_edges.py` L12-22, L43-56

```python
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
...
NGRAM_RANGE = (2, 4)
...
def build_texts(books: pd.DataFrame, with_tags: bool = False) -> list[str]:
    """tags 는 기본 제외 — 어휘 25토큰이면 다양성 재순위화가 카테고리 중복 제거로 퇴화한다."""
    cols = ["title", "description", "curator_note"] + (["tags"] if with_tags else [])
    return [
        " ".join(p for p in (_text(row[c]) for c in cols) if p)
        for row in books[cols].to_dict("records")
    ]


def similarity(texts: list[str]) -> np.ndarray:
    vec = TfidfVectorizer(analyzer="char_wb", ngram_range=NGRAM_RANGE, min_df=1)
    sim = cosine_similarity(vec.fit_transform(texts))
```

**차이(Track A 전용):** Goodbooks `tags`는 밀리 25토큰 어휘가 아닌 수천 태그이므로 **단어 단위**(`analyzer="word"`, 기본값) TF-IDF를 `tags` 컬럼에 fit(CONTEXT D-14·D-15). `TfidfVectorizer`는 기본 `norm="l2"`라 행이 이미 L2 정규화 — `vectors()`는 `.toarray()` dense 반환. data.md "`tags` 단독 TF-IDF 금지"는 **Track B** 문장이며 Track A는 D-14/D-15가 우선(NOISE_TAGS 제거로 대응).

**만족해야 할 Protocol:** `contracts.py` L310-313 (verbatim)

```python
class ItemVectors(Protocol):
    """아이템 콘텐츠 벡터 (MMR·ILD 용). retrieval 이 제공하고 app 이 주입."""

    def vectors(self, book_ids: Sequence[int]) -> "np.ndarray": ...
```

**contracts 심볼:** `ItemVectors`, `COL_ITEM`(books.parquet의 `book_id` 컬럼명과 동일 문자열). `books.parquet` 컬럼 `tags`는 계약 컬럼 이름 그대로(리터럴 허용 — `COL_*`에 `tags` 상수 없음).
**형태:** `class ContentVectors: def __init__(self, books: pd.DataFrame) → fit` + `vectors(book_ids)` → `(len(book_ids), n_features)` ndarray, 미지 id는 0 벡터. `retrieve()`는 Phase 4가 같은 파일에 증분(≤150줄 유지 → Phase 2 분량 ≈60줄).
**테스트 필수(D-16):** `vectors()` shape == `(len(ids), dim)` · 각 행 L2 norm ≈ 1(0 벡터 제외). fixture: `tests/conftest.py::item_vectors`는 랜덤 dense 50×8이라 ILD 테스트용이고, content 테스트는 소형 `pd.DataFrame({COL_ITEM: [...], "tags": ["a b", "b c", ...]})`를 테스트 안에서 만든다.

---

### `src/millie_rec/evaluation/metrics.py` (pure functions) — **No code analog**

정본은 `.claude/rules/evaluation.md` "지표 정의" 절(그대로 구현):
- `recall_at_k(ranked: Sequence[int], relevant: set[int], k: int) -> float` = `|L_u[:k] ∩ R_u| / |R_u|`. **분모를 `min(|R_u|,K)`로 바꾸지 않는다.**
- `ndcg_at_k(ranked, relevant, k) -> float` = DCG/IDCG, 이진 gain, 할인 `1/log2(i+1)` (i 1-based), IDCG는 `min(|R_u|, K)`개 기준.
- `ild_at_k(vectors: np.ndarray, k: int) -> float` = 상위 k 아이템 모든 쌍 `(1 − cosine)` 평균. `vectors`는 `contracts.ItemVectors.vectors(ranked[:k])` 결과를 그대로 받는다(evaluation은 Protocol을 통해서만 벡터를 안다).

**contracts 심볼:** `K_RECALL`(20), `K_RANK`(10) — 기본값으로만, 함수는 k 인자를 받는다.
**형태 규칙(simplicity.md):** 함수 우선, 클래스 없음. numpy 사용, 파이썬 루프는 리스트 길이 k(≤20)에서만.
**테스트(python-tdd.md "경로 전부"):** 3~5 아이템 손계산 케이스 — 예 `ranked=[1,2,3], relevant={2,9}, k=3` → recall 0.5, ndcg = (1/log2(3)) / 1.0. ILD: 직교 두 벡터 → 1.0, 동일 벡터 → 0.0. 빈 relevant/빈 ranked 경계.

---

### `src/millie_rec/evaluation/harness.py` (service, user loop)

**Analog A — Pipeline 호출 + 예외 격리:** `src/millie_rec/serving/api.py` L59-64

```python
    """전역 인기 fallback. 예외가 나도 빈 trending 행으로 200 — 추천 API 장애 ≠ 메인 장애(D-13)."""
    try:
        items = fallback.recommend(user, k)
    except Exception:
        log.exception("fallback pipeline failed; serving empty trending row")
        items = []
```
(하네스에서는 예외를 숨기지 말고 전파 — 숫자 출처이므로. 인용 목적은 "`Pipeline.recommend(user, k)`가 유일한 호출 표면"임을 보이기 위함.)

**Analog B — 소비하는 Protocol·DTO:** `contracts.py` L341-346, L273-285 (verbatim)

```python
class Pipeline(Protocol):
    """조립된 추천기. evaluation · serving 은 이것만 안다."""

    name: str

    def recommend(self, user: UserState, k: int) -> list[ScoredItem]: ...
```
```python
@dataclass(frozen=True, slots=True)
class EvalResult:
    variant: str
    recall: float
    ndcg: float
    ild: float
    n_users: int
    k_recall: int
    k_rank: int
    seed: int
    model_version: str
    created_at: str
    p95_ms: float | None = None
```

**contracts 심볼:** `Pipeline`, `ItemVectors`, `UserState`, `EvalResult`, `K_RECALL`, `K_RANK`, `SEED`, `MODEL_VERSION_SUFFIX`, `VARIANTS`. 같은 슬라이스 `metrics`는 `from millie_rec.evaluation.metrics import …`.
**시그니처 제안:** `evaluate(pipeline: Pipeline, users: Sequence[tuple[UserState, set[int]]], vectors: ItemVectors, *, k_recall=K_RECALL, k_rank=K_RANK) -> EvalResult`. `state` 라벨(`n0`/`n20`)은 `EvalResult`에 필드가 없으므로(D-08) 호출자(cli/report)가 실행 메타로 들고 간다. 하네스는 `data` 슬라이스를 import할 수 없다 → `UserState`·정답 집합은 `app/cli.py`가 만들어 넘긴다.
**테스트 필수(D-16):** 하네스가 test 라벨을 `UserState`에 넣지 않는다 → 가짜 Pipeline이 받은 `user`를 기록해 `user.seen ∩ R_u == ∅` 단정(가짜 객체 패턴은 `tests/serving/test_smoke.py::_Boom` L33-39 참조) · 두 상태 출력.

---

### `src/millie_rec/evaluation/report.py` (csv·json writer)

**Analog A — 메타 json(UTC ISO·ensure_ascii·indent):** `scripts/build_millie_catalog.py` L10, L134, L211-227, L242-244

```python
from datetime import UTC, datetime
...
    now = datetime.now(UTC).isoformat(timespec="seconds")
...
    return {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "n_records": n,
        ...
    }
...
    (out_dir / "millie_raw_coverage.json").write_text(
        json.dumps(coverage(records, meta), ensure_ascii=False, indent=2), encoding="utf-8"
    )
```

**Analog B — csv 쓰기(id_map):** `scripts/build_millie_catalog.py` L143-145

```python
    pd.DataFrame(rows, columns=["millie_id", "book_id", "first_seen_at"]).sort_values(
        "book_id"
    ).to_csv(path, index=False)
```

**contracts 심볼:** `DIR_RESULTS`, `EvalResult`, `VARIANTS`(행 순서 정렬 기준).
**출력 정본(D-06~D-08):** `results/latest.csv` 컬럼 `variant, recall@20, ndcg@10, ild@10, n_users, split_mode, model_version`(소수 3자리, `float_format="%.3f"`) · `results/latest_states.csv` 컬럼 `variant, state, recall@20, ndcg@10, ild@10, n_users` · `results/eval_<YYYYMMDD_HHMM>.json` 키: `dataset, split_mode, test_frac, seed, n_users{n0,n20}, n_excluded, k_recall, k_rank, n_onboard_seeds, k_history, min_user_interactions, min_item_interactions, git_sha, elapsed_s, created_at, rows[], states[]`. git sha는 `subprocess.run(["git","rev-parse","--short","HEAD"], capture_output=True, text=True)` 실패 시 `None`(CONTEXT 재량).
**`artifacts/serving/eval_table.json`은 report.py가 쓰지 않는다** — `artifacts/serving/` 소유는 app(export)이므로 `app/cli.py`가 `latest.csv` 행을 복사해 `{"rows": [...], "meta": {...}}`로 쓴다(D-09).

---

### `src/millie_rec/evaluation/figures.py` (matplotlib png, Should) — **No code analog**

규칙만: `.claude/rules/evaluation.md` "비교 막대그래프는 `figures.py`가 matplotlib로 `report/figures/eval_bar.png`에 생성한다." **contracts 심볼:** `DIR_FIGURES`, `VARIANTS`. `matplotlib.use("Agg")` 후 import pyplot(헤드리스). `.gitignore` L21 `!report/figures/*.png`로 결과 커밋 가능. EVAL-07 — 시간 부족 시 가장 먼저 버림.

---

### `src/millie_rec/app/pipeline.py` (assembly glue)

**Analog A — `ScoredItem` 생성 형태(Candidate → ScoredItem 변환의 모델):** `serving/fallback.py` L25-34 (위 popularity 절 인용 참조). `ScoredItem` 정의: `contracts.py` L218-232 — 필수 `book_id, score`, 선택 `source, position, source_channels`.

**Analog B — app이 허용하는 import 형태:** `src/millie_rec/app/server.py` L5-6

```python
from millie_rec.contracts import ROOT
from millie_rec.serving import Database, GlobalPopularFallback, create_app, resolve_db_path
```

**형태(CONTEXT 재량 "Pipeline 어댑터 위치"):** 
```python
class PopPipeline:  # contracts.Pipeline 구현 — retriever 단독 variant 의 glue
    name = "pop"
    def __init__(self, retriever: PopularityRetriever) -> None: ...
    def recommend(self, user: UserState, k: int) -> list[ScoredItem]:
        return [ScoredItem(book_id=c.book_id, score=c.score, source=c.source, position=i,
                           source_channels=(c.source,)) for i, c in enumerate(self._r.retrieve(user, k))]
```
+ `build_pipelines() -> dict[str, Pipeline]`: `DIR_ARTIFACTS / "popularity.json"` 있으면 `{"pop": PopPipeline(PopularityRetriever.load(...))}` 아니면 `{}`. dict 키는 `contracts.VARIANTS` 이름 그대로. 비즈니스 규칙 0(architecture.md "Service/Application Layer").
**contracts 심볼:** `Pipeline`, `ScoredItem`, `UserState`, `VARIANTS`, `DIR_ARTIFACTS`. `from millie_rec.retrieval import PopularityRetriever`(공개 표면).

---

### `src/millie_rec/app/cli.py` (argparse subcommands)

**Analog — argparse + `DIR_*` 기본값 + print 요약:** `scripts/build_millie_catalog.py` L248-260

```python
def main() -> None:
    ap = argparse.ArgumentParser(description="밀리 원본 JSONL → books_kr.parquet")
    ap.add_argument("--jsonl", type=Path, default=DIR_RAW / "millie_pages.jsonl")
    ap.add_argument("--out", type=Path, default=DIR_PROCESSED)
    ...
    args = ap.parse_args()
    df = build(args.jsonl, args.out, args.raw_dir, args.id_map)
    print(f"books={len(df)} → {args.out / 'books_kr.parquet'} · id_map → {args.id_map}")


if __name__ == "__main__":
    main()
```

**차이:** 서브커맨드(`sub = ap.add_subparsers(dest="cmd", required=True)`; `data`, `eval --variant all|pop|…`). Makefile L8·L25가 `python -m millie_rec.app.cli data|eval --variant all`을 이미 호출 → `if __name__ == "__main__": main()` 필수. `eval` 흐름(CONTEXT Integration Points): `load_interactions()` → `split()` → 적격 유저 표본(`N_TEST_USERS`) → `mask_onboarding` 두 상태 → `build_pipelines()`의 등록 variant × 2 상태 `evaluate()` → `write_results()` → `eval_table.json` 복사(app 소유) → `PopularityRetriever.save()`. **주의:** eval에서 pop은 파일이 아니라 train으로 새로 fit해야 하므로 `build_pipelines()`와 별도로 `fit_pipelines(train) -> dict`가 필요(planner 판단, 같은 `pipeline.py`).
**import 형태:** `from millie_rec.data import load_interactions, load_books, split, mask_onboarding` / `from millie_rec.retrieval import PopularityRetriever, ContentVectors` / `from millie_rec.evaluation import evaluate, write_results` / `from millie_rec.app.pipeline import …`(app 내부는 자유).

---

### `src/millie_rec/app/server.py` (MODIFY — L10 `pipelines={}`만)

**현재 전문:** `src/millie_rec/app/server.py` L1-12

```python
"""uvicorn 진입점: create_app 주입 + demo/ StaticFiles(마지막). CORS 없음(아키텍처 01 §9-3)."""

from fastapi.staticfiles import StaticFiles

from millie_rec.contracts import ROOT
from millie_rec.serving import Database, GlobalPopularFallback, create_app, resolve_db_path

# Phase 2 → pipelines["pop"], Phase 3 → catalog, Phase 5 → neighbors·book_stats·state.
# 이 호출의 인자만 채운다 — 시그니처 불변(CONTEXT D-09).
app = create_app(pipelines={}, fallback=GlobalPopularFallback(None), db=Database(resolve_db_path()))
# 반드시 마지막 — 앞에 두면 /health·/api/* 가 StaticFiles 에 가려진다
app.mount("/", StaticFiles(directory=ROOT / "demo", html=True), name="demo")
```

**변경 = 1행:** `pipelines={}` → `pipelines=build_pipelines()` + `from millie_rec.app.pipeline import build_pipelines`. StaticFiles 마운트 순서 불변(`tests/serving/test_smoke.py::test_server_module_serves_demo_index_and_keeps_api_routes` L152-166이 검사). 이 테스트는 `sys.modules.pop` 후 재import하므로 `build_pipelines()`는 import 시점 부작용(네트워크·pandas 로드) 없이 파일 존재 검사 + 작은 json 로드만.

---

### `src/millie_rec/serving/api.py` (MODIFY — `recommend()` L119-126 level 0 분기)

**현재 핸들러:** `src/millie_rec/serving/api.py` L110-126

```python
    @app.get("/api/recommend", response_model=RecommendOut)
    def recommend(
        user_key: Annotated[str | None, Query()] = None,
        snapshot_id: Annotated[str | None, Query()] = None,
        model: Annotated[str | None, Query()] = None,
        k: Annotated[int, Query(ge=1, le=K_MAX)] = K_DEFAULT,
        context: Annotated[str | None, Query()] = None,
        seeds: Annotated[str | None, Query()] = None,
    ) -> RecommendOut:
        t0 = perf_counter()
        if model is not None and model not in VARIANTS:
            raise _422("model", f"model must be one of {list(VARIANTS)}")
        user = UserState(user_id=None, explicit_seeds=_parse_seeds(seeds))
        # Phase 2 가 pipelines["pop"] 을 주입하면 여기에 level 0 분기를 추가한다
        # user_key·snapshot_id 는 Phase 5(state.py) 몫 — Phase 1 은 쿼리 계약만 받는다
        resp = _fallback_response(fallback, user, k, t0, context)
        return RecommendOut.from_contract(resp, forced=model is not None)
```

**응답 조립 모델(level 0은 이 함수를 복제해 `model_version`·`fallback_level`·`items`만 바꾼다):** L50-76

```python
def _fallback_response(
    fallback: Pipeline, user: UserState, k: int, t0: float, context: str | None,
    *, level: int = FALLBACK_GLOBAL_POP,
) -> RecommendResponse:
    ...
    ms = (perf_counter() - t0) * 1000
    return RecommendResponse(
        items=(),  # 행 평탄화 상위 k 는 Phase 5 compose.py
        model_version=MODEL_VERSION_FALLBACK,
        fallback_level=level,
        latency_ms=ms,
        recommendation_id=_new_rec_id(),
        rows=(trending_row(items),),
        latency_breakdown={"total": ms},
        user_state_weights=dict(ZERO_WEIGHTS),
        context=context,
    )
```

**level 0 분기 형태(D-11·D-12·D-13):**
```python
        if user.explicit_seeds and pipelines:  # D-13: seeds 없는 익명은 level 3 유지
            name = model if model in pipelines else _default_variant(pipelines)  # D-11: VARIANTS 순서상 마지막 등록
            try:
                items = pipelines[name].recommend(user, k)
                resp = _personalized_response(name, items, k, t0, context)  # fallback_level=FALLBACK_PERSONALIZED
            except Exception:
                log.exception("pipeline %s failed; falling back to level 3", name)
                resp = _fallback_response(fallback, user, k, t0, context)
        else:
            resp = _fallback_response(fallback, user, k, t0, context)
```
`_personalized_response`는 `RecommendResponse(items=tuple(Recommendation(book_id=i.book_id, score=i.score) for i in items[:k]), model_version=f"{name}{MODEL_VERSION_SUFFIX}", fallback_level=FALLBACK_PERSONALIZED, rows=(trending_row(items),), …ZERO_WEIGHTS 유지)`. `model`이 `VARIANTS`에는 있지만 미등록(예 `model=cf`)이면 — 422가 아니라 기본 variant 또는 level 3 중 planner 판단(테스트 L100-103 `model=pop` + level 3 단정은 **pipelines={}일 때**만이라 충돌 없음).
**추가 import(모두 contracts):** `FALLBACK_PERSONALIZED`, `MODEL_VERSION_SUFFIX`, `Recommendation`. `RecommendOut.from_contract`(`schemas.py` L182-187)는 `asdict(r)`로 그대로 직렬화하므로 스키마 변경 없음. 파일 현재 128줄 → 분기 추가 후 ≤150줄 유지 필요(헬퍼 1개까지).

---

### `tests/serving/test_recommend_level0.py` (exact analog)

**Analog:** `tests/serving/test_smoke.py` L33-66, L144-148

```python
class _Boom:
    """recommend 가 항상 예외 — '추천 API 장애 ≠ 메인 장애' 증거용 가짜 Pipeline."""

    name = "boom"

    def recommend(self, user: UserState, k: int) -> list[ScoredItem]:
        raise RuntimeError("boom")
...
def _app(tmp_path: Path, fallback=None):
    return create_app(
        pipelines={},
        fallback=fallback or GlobalPopularFallback(None),
        db=Database(tmp_path / DB_FILENAME),
    )


@pytest.fixture
def client(tmp_path: Path):
    with TestClient(_app(tmp_path)) as c:  # with 블록이어야 lifespan(스키마 적용)이 돈다
        yield c
...
def test_recommend_when_fallback_raises_still_200_level3(tmp_path: Path):
    with TestClient(_app(tmp_path, fallback=_Boom())) as c:
        r = c.get("/api/recommend", params={"seeds": "1"})
    assert r.status_code == 200
    assert r.json()["fallback_level"] == FALLBACK_GLOBAL_POP and r.json()["rows"][0]["items"] == []
```

**level 0 테스트:** `_app`에 `pipelines: dict | None = None` 인자를 추가한 로컬 복사본(기존 test_smoke.py는 수정 금지) + `_FakePop`(name="pop", `recommend`가 seeds 제외 `ScoredItem` 5개 반환). 단정(D-16): `fallback_level == FALLBACK_PERSONALIZED` · `model_version == "pop" + MODEL_VERSION_SUFFIX` · `rows[0]["row_id"] == "trending"` · `items != []` · seeds ∉ items · seeds 없는 요청 → `FALLBACK_GLOBAL_POP` · `pipelines={"pop": _Boom()}` → 200 level 3. 파일 헤더 docstring은 test_smoke.py L1-5 형식(3종 구분 `# ── 계약 ──` 섹션 주석 L69·L87·L136).

---

### `tests/data/*`, `tests/retrieval/*`, `tests/evaluation/*` (test files)

**Analog A — fixture 사용(유일한 허용 데이터):** `tests/conftest.py` L12-34 (session scope `interactions` 20×50 ts 있음 · `item_vectors` 50×8). 새 fixture가 필요하면 각 `tests/<slice>/conftest.py`에 소형으로(다운로드·실데이터 금지).

**Analog B — 파일 헤더·모듈 상수 스타일:** `tests/data/test_millie_edges.py` L1-22

```python
"""US-005 이웃 빌더 단위 테스트 + 적재 계획 §6 이웃 품질 게이트 3개.

게이트: ① self-edge 0 ② 전 도서 이웃 ≥5 ③ top-20 동일 카테고리 비율 ≤70%.
"""
...
MIN_NEIGHBOURS = 5
TOP_N = 20
```
(테스트는 구현 상수를 import하지 않고 기대값을 손으로 적는다 — `test_millie_catalog.py` L24 주석 "스크립트 상수를 import 하지 않고 손으로 적어 둔다".)

**Analog C — Protocol 구현 단위 테스트:** `tests/serving/test_smoke.py` L127-133

```python
def test_fallback_with_catalog_excludes_seeds_and_marks_popularity():
    items = GlobalPopularFallback(_FakeCatalog()).recommend(
        UserState(user_id=None, explicit_seeds=(1,)), k=10
    )
    assert [i.book_id for i in items] == [2, 3, 4, 5]
    assert all(i.source == "popularity" and i.source_channels == ("popularity",) for i in items)
```

**주의:** `tests/data/test_millie_*.py` 3개는 Track B — 불변. 새 Track A 테스트는 `tests/data/test_load.py` 등 별도 파일. `tests/retrieval/`·`tests/evaluation/` 디렉터리는 신설(`__init__.py` 불필요 — 기존 `tests/serving/`도 없음).

---

## Shared Patterns

### 컬럼·경로·난수 — 문자열 리터럴 금지
**Source:** `src/millie_rec/contracts.py` L18-35, L55-63 · **Apply to:** data·retrieval·evaluation·app 전부
```python
SEED = 42
ROOT = Path(__file__).resolve().parents[2]
DIR_RAW = ROOT / "data" / "raw"
DIR_PROCESSED = ROOT / "data" / "processed"
DIR_ARTIFACTS = ROOT / "artifacts"
DIR_RESULTS = ROOT / "results"
DIR_FIGURES = ROOT / "report" / "figures"
COL_USER = "user_id"; COL_ITEM = "book_id"; COL_TS = "ts"; COL_EVENT = "event"; COL_RATING = "rating"
K_RECALL = 20; K_RANK = 10; N_ONBOARD_SEEDS = 5
VARIANTS = ("pop", "cf", "hybrid", "hybrid_div")
MODEL_VERSION_SUFFIX = "_v1"  # model_version = f"{variant}{MODEL_VERSION_SUFFIX}"
FALLBACK_PERSONALIZED, FALLBACK_CACHE, FALLBACK_SEGMENT_POP, FALLBACK_GLOBAL_POP = 0, 1, 2, 3
```
난수는 `np.random.default_rng(SEED)`(conftest L15). **`contracts.py`는 이 페이즈에서 무변경**(D-08 — `EvalResult`에 `state`·`split_mode` 없음 → 실행 메타로).

### Protocol 구현 클래스 — `name` 속성 + Protocol 메서드만
**Source:** `serving/fallback.py` L13-21 · **Apply to:** `PopularityRetriever`(CandidateGenerator), `ContentVectors`(ItemVectors), `PopPipeline`(Pipeline). 상속 없음(structural typing), `name = "<variant>"` 클래스 속성, `__init__`은 주입만.

### seen 제외
**Source:** `serving/fallback.py` L24 `[b for b in ... if b not in user.seen][:k]` · **Apply to:** `popularity.py::retrieve`, 하네스 누수 단정 `user.seen ∩ R_u == ∅`.

### 파일 쓰기 — mkdir → write_text(ensure_ascii=False, encoding="utf-8")
**Source:** `scripts/export_millie_serving.py` L71-76, `scripts/build_millie_catalog.py` L240-244 · **Apply to:** `load.py`(parquet), `popularity.py::save`, `report.py`, `cli.py`(eval_table.json).

### 에러 처리 — 예외 계층 없음, `log.exception` + 안전 기본값(서빙만)
**Source:** `serving/api.py` L27, L60-64 · **Apply to:** `api.py` level 0 분기(예외 → level 3 200). **평가·데이터 경로는 예외를 숨기지 않는다**(숫자 출처). `simplicity.md`: 재시도·캐시 데코레이터·예외 클래스 금지.

### 테스트 3종 구분 주석
**Source:** `tests/serving/test_smoke.py` L69, L87, L136 (`# ── 계약 ──` / `# ── 정확성 ──` / `# ── 안전성 ──`) · **Apply to:** 모든 새 테스트 파일. Red는 `AssertionError`로 확인(`python-tdd.md`).

---

## No Analog Found

| File | Role | Data Flow | Reason / 대체 정본 |
|---|---|---|---|
| `evaluation/metrics.py` | pure metric functions | transform | repo에 지표 코드 0. `.claude/rules/evaluation.md` "지표 정의" 절이 정본(Recall 분모 `|R_u|`, NDCG 이진·IDCG=min(|R_u|,K), ILD 1−cosine 쌍 평균) |
| `evaluation/figures.py` | matplotlib writer | file-I/O | repo에 matplotlib 사용 0. `evaluation.md` "figures.py → report/figures/eval_bar.png" + `.gitignore` L21 |
| `data/split.py` (holdout 로직) | transform | transform | 기존 split 코드 없음. `data.md` Track A split 문장 + CONTEXT D-02가 정본. `default_rng` 형태만 conftest에서 |
| `data/load.py` (HTTP 다운로드) | loader | network | repo에 다운로드 코드는 `scripts/collect_millie.py`(playwright, 부적합). stdlib `urllib.request.urlretrieve` + 존재·크기 검사 — CONTEXT 재량 |

---

## Metadata

**Analog search scope:** `src/millie_rec/**` (contracts·serving·app 12 파일), `scripts/*.py` (5), `tests/**` (6), `Makefile`, `pyproject.toml`, `.gitignore`, `.claude/rules/{data,evaluation,python,python-tdd,serving,report,architecture,simplicity}.md`
**Files scanned:** 26 source/test + 8 rules + 3 build files
**Pattern extraction date:** 2026-09-05
**Codegraph:** 미사용(파일 33개 규모라 직접 Read가 더 빨랐음. 인덱스는 `millie-rec/.codegraph/`에 존재, `projectPath` 필수)
