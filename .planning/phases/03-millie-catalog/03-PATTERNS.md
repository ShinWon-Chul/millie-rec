# Phase 3: 밀리 카탈로그 빌드 - Pattern Map

**Mapped:** 2026-09-05
**Files analyzed:** 9 source/script files (4 new + 5 modified) + 7 test files (6 new + 1 extended) + 1 fixture dir
**Analogs found:** 16 / 16 — 이 페이즈는 Phase 1·2 가 남긴 `scripts/build_millie_*.py`·`retrieval/popularity.py`·`retrieval/content.py`·`serving/fallback.py`·`app/pipeline.py` 를 거의 그대로 복제하는 구조라 아날로그 품질이 높다(exact 6 · role-match 10 · no-analog 0). 단, 순수 통계 함수(난이도 z-score)와 SVD 벡터 export 는 코드 아날로그가 부분적이라 규칙·CONTEXT 수식을 함께 인용했다.

## 기준선 (실측 2026-09-05, 이 페이즈 시작 직전)

| 항목 | 값 |
|---|---|
| `uv run python --version` | Python 3.11.6 |
| `uv run pytest --no-header` | **171 passed, 2 skipped**, 2.02s (skip 2 = `test_coverage_gate`·`test_neighbour_quality_gate`, 실산출물 부재) |
| `uv run ruff check .` | All checks passed (`select = ["E","F","I","UP","B"]`, `line-length = 100`, `extend-exclude = ["demo", ".planning"]`) |
| `data/raw/millie_pages.jsonl` | 5,395 줄(중복 포함, 고유 5,157) · `completion_prob`/`expected_min` 은 **int 또는 None**(None 761줄) · 이미지 호스트 `img.millie.co.kr` 4,973 · `image.` 330 · `cover.` 87 · None 3 · `d1miajbjsyro89.cloudfront.net` 2(성인 플레이스홀더) |
| `data/processed/` | `books.parquet`·`interactions.parquet`(Track A)만. **`books_kr.parquet`·`item_edges_kr.parquet` 미생성** → 게이트 테스트 2개 skip 상태 |
| `artifacts/serving/` | `eval_table.json`(447B)·`.gitkeep` 만 |
| `demo/fallback/popular.json` | 현재 mock v1 형태(Goodbooks 40권, `latency_ms` **dict**, items 에 `format` 키). **`RecommendOut.model_validate` 실패 41건**(`latency_ms` float 아님 · `format` extra_forbidden) — export 재작성 시 계약 형태로 바꿔야 한다(아래 "popular.json" 절) |
| `Makefile` | `millie-build`(L13-14: 빌드 + `pytest tests/data -q`) · `millie-edges`(L16-17) · `millie-export`(L19-20, 주석에 `popularity_kr.json`·`content_vectors_kr.npz` 이미 명시) · `millie`(L22 = build→edges→export). **popularity 빌드 타깃 없음** — Advisor 전용 파일이라 planner 는 "Advisor 가 `millie-popularity` 타깃 추가 또는 export 안에서 생성" 중 택1 지시 |
| `scripts/` 줄 수 | `build_millie_catalog.py` 260 · `build_millie_edges.py` 152 · `export_millie_serving.py` 102 · `millie_parse.py` 270 · `collect_millie.py` 283 (D-16: 앞 셋은 분리하지 않음, 새 로직은 새 파일) |
| `src/` 관련 줄 수 | `app/pipeline.py` 55 · `app/server.py` 18 · `data/__init__.py` 57 · `retrieval/content.py` 42 · `retrieval/popularity.py` 58 · `serving/fallback.py` 45 · `serving/api.py` 135(≤150 유지 필수, 이 페이즈 무변경) |

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `scripts/millie_difficulty.py` (NEW) | utility (pure pandas/numpy 통계 함수) | transform | `scripts/build_millie_edges.py` (모듈 상수 + 순수 함수 + `build(df)->df`) + `src/millie_rec/evaluation/metrics.py` (1줄 docstring 순수 함수·경계값 처리) + `scripts/build_millie_catalog.py::_row` L149-190 (`difficulty_source`·결측 대체 규칙의 현 위치) | role-match |
| `scripts/build_millie_catalog.py` (MODIFY) | data builder script | file-I/O · batch | 자기 자신 — `read_records` L86-99 · `coverage` L211-227 · `COLUMNS` L17-23 · `build` L230-245 | exact |
| `scripts/build_millie_edges.py` (MODIFY, 게이트 ③ 미달 시에만) | data builder script | transform | 자기 자신 — `build_texts` L43-49 · `similarity` L52-56 | exact |
| `scripts/build_millie_popularity.py` (NEW) | data builder script | transform → file-I/O | `scripts/build_millie_catalog.py::build_frame` L193-208 (`_pop_key` shelf_count 내림차순·결측 마지막) + `main()` L248-260 | role-match |
| `scripts/export_millie_serving.py` (MODIFY) + `scripts/export_millie_vectors.py` (NEW, export 가 150줄 넘으면) | exporter script | file-I/O | 자기 자신 `_write`·`books_payload`·`edges_payload` L43-88 + `build_millie_edges.py::similarity` L52-56 (TF-IDF 설정 정본) + `serving/compose.py::build_response` L34-60 & `serving/fallback.py::trending_row` L37-45 (popular.json 형태 정본) | exact / role-match |
| `src/millie_rec/data/catalog_kr.py` (NEW) | adapter (`Catalog`·`Neighbors`·`BookStatsSource` Protocol 구현, json 로드) | file-I/O(기동 1회) → request-response | `src/millie_rec/retrieval/popularity.py` L22-58 (Protocol 구현 클래스 + `load(path)` classmethod + json 아티팩트) + `tests/serving/test_smoke.py::_FakeCatalog` L54-64 (Catalog 3메서드 시그니처) | role-match |
| `src/millie_rec/data/vectors_kr.py` (NEW, 줄 수로 분리 권장) | adapter (`ItemVectors` 구현, npz 로드) | file-I/O → transform | `src/millie_rec/retrieval/content.py::ContentVectors` L20-42 (`_index` dict + `vectors()` 0-벡터 패턴) | **exact**(형태 동일, 소스만 npz) |
| `src/millie_rec/data/__init__.py` (MODIFY) | public surface | — | 자기 자신 L1-57 (알파벳 정렬 `__all__`) | exact |
| `src/millie_rec/app/pipeline.py` (MODIFY) | assembly glue (`Pipeline` 구현 + 조립 함수) | request-response | 자기 자신 `PopPipeline` L20-38 · `build_pipelines` L46-55 + `serving/fallback.py::GlobalPopularFallback.recommend` L21-34 (catalog.popular → ScoredItem) | exact |
| `src/millie_rec/app/server.py` (MODIFY, Advisor 전용) | entrypoint | — | 자기 자신 L12-16 (`create_app(...)` 인자만 채움) | exact |
| `tests/data/test_millie_difficulty.py` (NEW) | test | — | `tests/evaluation/test_metrics.py` (손계산 케이스) + `tests/data/test_millie_catalog.py::_load` L83-89 (importlib 로 scripts 로드) | role-match |
| `tests/data/test_millie_popularity.py` (NEW) | test | — | `tests/data/test_millie_edges.py` L27-45 (module-scope `_load` + fixture 빌드 체인) | role-match |
| `tests/data/test_millie_export.py` (NEW — 현재 export 테스트 없음) | test | — | `tests/data/test_millie_edges.py` fixture 체인 + `tests/app/test_export.py` (json 산출물 키 단정) | role-match |
| `tests/data/test_millie_catalog.py::test_coverage_gate` (EXTEND) | test (실데이터 게이트) | — | 자기 자신 L283-312 | exact |
| `tests/data/test_catalog_kr.py` (NEW) | test | — | `tests/retrieval/test_content.py` (shape·L2·미지 id) + `tests/app/test_pipeline.py` L30-42 (Protocol 구현 단정) | role-match |
| `tests/app/test_server_catalog.py` (NEW, 서버 주입) | test | — | `tests/serving/test_smoke.py` L164-198 (`sys.modules.pop` + `importlib.import_module("millie_rec.app.server")` + monkeypatch 배선) | **exact** |
| `tests/fixtures/millie/serving_sample/` (NEW) | fixture | — | `tests/fixtures/millie/sample_records.jsonl` (14줄 · 12권) — export 산출물 형태로 20권 | role-match |

---

## Pattern Assignments

### 0. 모든 신규 `.py` 공통 — 모듈 머리·상수·import 순서

**Analog:** `scripts/build_millie_edges.py` L1-23 (scripts 형), `src/millie_rec/retrieval/popularity.py` L1-19 (슬라이스 형)

```python
"""books_kr.parquet → item_edges_kr.parquet (US-005, 적재 계획 §6).

이웃 정본은 title+description+curator_note 문자 2~4gram TF-IDF cosine top-20(content_sim)이고,
...
"""

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from millie_rec.contracts import DIR_PROCESSED, DIR_RAW

TOP_N = 20
MIN_NEIGHBOURS = 5
CATEGORY_BEST_WEIGHT = 0.2
NGRAM_RANGE = (2, 4)
EDGE_COLUMNS = ("src_book_id", "dst_book_id", "weight", "source")
```

복사할 것: ① 모듈 docstring 첫 줄에 "입력 → 출력 (정본 절)" ② stdlib → 서드파티 → `millie_rec.contracts` 순(ruff `I`) ③ 설정은 모듈 상단 대문자 상수, 뒤 `#` 주석에 정본 ④ 슬라이스 파일은 pandas 를 `if TYPE_CHECKING:` 아래로(`popularity.py` L13-14 — 서빙 기동 시 pandas 미로드) ⑤ ≤150줄.

**scripts ↔ 슬라이스 import 경계:** `scripts/*.py` 는 `tests/test_architecture.py` 검사 대상이 아니다(`SRC = src/millie_rec` 만 rglob, L10·L29). 지금까지 모든 스크립트는 `millie_rec.contracts` 만 import 한다 — 이 관례를 유지한다(`millie_rec.serving` import 금지: popular.json 검증은 테스트에서).

---

### `scripts/millie_difficulty.py` (utility, transform) — NEW

**Analog A — 순수 함수 + 경계값 처리 형태:** `src/millie_rec/evaluation/metrics.py` L11-25

```python
def recall_at_k(ranked: Sequence[int], relevant: Set[int], k: int = K_RECALL) -> float:
    """|L_u[:k] ∩ R_u| / |R_u|. 분모를 min(|R_u|, k) 로 바꾸지 않는다(evaluation.md)."""
    if not relevant:
        return 0.0
    hits = sum(1 for b in ranked[:k] if b in relevant)
    return hits / len(relevant)
```

**Analog B — 결측 대체·`difficulty_source` 판정의 현 위치(이 파일이 이어받는 규칙):** `scripts/build_millie_catalog.py` L152-153, L178-183

```python
    prob, avg_prob = rec.get("completion_prob"), rec.get("category_avg_prob")
    filled = prob is None  # 계획 §4: 결측이면 분야 평균으로 대체 + 출처 표시
    ...
        "completion_prob": avg_prob if filled else prob,
        "category_avg_prob": avg_prob,
        "expected_min": rec.get("expected_min"),
        "category_avg_min": rec.get("category_avg_min"),
        "millie_label": rec.get("millie_label"),
        "difficulty_source": "category_prior" if filled else "millie_index",
```
→ `_row` 는 이미 결측을 `category_avg_prob` 로 채우고 `difficulty_source` 를 찍는다. **난이도 모듈은 `build_frame` 결과 DataFrame(채워진 `completion_prob` + `difficulty_source`)을 입력으로 받아** `resid_z`·`len_z`·`difficulty` 3컬럼을 붙이는 `df -> df` 함수 하나면 된다. 결측 판정은 `difficulty_source == "category_prior"` 컬럼으로(원본 None 을 다시 볼 필요 없음).

**Analog C — 컬럼 dtype 정리(Int64 nullable):** `scripts/build_millie_catalog.py` L203-207

```python
    for col in INT_COLS:
        df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")
```
→ `completion_prob`·`expected_min` 은 `Int64`(nullable) 로 들어온다. z-score 계산 전 `astype("float")` 로 바꿔야 `<NA>` 연산 오류를 피한다. 새 3컬럼은 `Float64` 또는 `float`(NaN=결측) — `difficulty` 결측은 `None`/NaN 으로 두고 export `_clean` 이 `None` 으로 바꾼다(L43-53).

**수식 정본(CONTEXT Claude's Discretion "난이도 파생 세부" + `.claude/rules/data.md` Track B 난이도 절 verbatim):**
> `resid_z = z_분야(P_완독 − E[P_완독 | 분야, expected_min 분위])`, `len_z = z_분야(expected_min)`. 합성 `difficulty = σ(−resid_z)`. `len_z`는 합성에 넣지 않는다("긴 책 = 어려운 책" 회귀 방지). 결측(표본 20%): `completion_prob := category_avg_prob`, `resid_z := 0`, `difficulty_source := "category_prior"`, **`difficulty := None`**.

**제안 형태(analog 없음 — 규칙 기반):**
```python
N_QUANTILES = 4          # expected_min 분야별 4분위 (CONTEXT 권장)
MIN_CATEGORY_SAMPLE = 20 # 분야 표본 미달 → 전역 분위 (build_millie_catalog.MIN_BOOKS_PER_CATEGORY 와 같은 값이지만 중복 정의)
MIN_Z_SAMPLE = 5         # 분야 표본 <5 또는 std=0 → 전역 std
CATEGORY_COL = "categories"  # 리스트 컬럼 — 분야 = categories[0] (빈 리스트면 None)

def add_difficulty(books: pd.DataFrame) -> pd.DataFrame:
    """resid_z·len_z·difficulty 3컬럼 추가. 입력은 build_frame 결과(completion_prob 이미 채워짐)."""
```
`difficulty = 1/(1+np.exp(resid_z))`(= σ(−resid_z)), `difficulty_source=="category_prior"` 행은 `resid_z=0.0`·`difficulty=NaN`. 분야 키는 `categories` 리스트의 첫 원소(`test_millie_edges.py::_same_category_share` L59-62 가 같은 방식 `list(c)[0] if len(c) else None` 을 쓴다).

**테스트(`tests/data/test_millie_difficulty.py`) 손계산 케이스 제안:** 한 분야 8권, `expected_min` 1..8, `completion_prob` 가 분위 평균에서 ±10 벗어나는 배열 → `resid_z` 부호·`difficulty` 0.5 기준 방향 단정(`resid_z>0 ⇒ difficulty<0.5`) · 결측 행 `resid_z==0 and isna(difficulty)` · 표본 3권 분야는 전역 std 사용(std=0 회피) · 출력 컬럼 3개 존재 + 입력 컬럼 불변.

**scripts 간 import 함정(반드시 브리프에 인라인):** `scripts/` 는 패키지가 아니다. `build_millie_catalog.py` 가 `import millie_difficulty` 를 하려면
- 실행 경로(`uv run python scripts/build_millie_catalog.py`)에서는 `sys.path[0] == scripts/` 라 동작하지만,
- 테스트는 `importlib.util.spec_from_file_location` 로 로드(`test_millie_catalog.py` L83-89)하므로 `scripts/` 가 `sys.path` 에 없다 → `ModuleNotFoundError`(collection error = Red 아님).
- 해법(둘 다 적용 권장): ① `build_millie_catalog.py` 상단 `sys.path.insert(0, str(Path(__file__).resolve().parent))` 후 `import millie_difficulty  # noqa: E402` ② 테스트 `catalog` fixture 에서 `_load("millie_difficulty")` 를 먼저 호출(`_load` 가 `sys.modules[name] = module` 로 등록하므로 이후 `import millie_difficulty` 가 그것을 쓴다, L87).

---

### `scripts/build_millie_catalog.py` (MODIFY — 유효 레코드 필터·카운터·3컬럼)

**변경점 1 — 유효 레코드 필터.** 현재 `read_records` L86-99 는 status 만 본다:

```python
def read_records(jsonl: Path) -> tuple[list[dict], dict]:
    """수집 성공 레코드만, millie_id 기준 마지막 줄(최신 수집)을 남긴다.

    title 이 비어도 성공 페이지는 남긴다 — 그래야 커버리지 게이트가 파서 결함을 잡는다.
    """
    lines = [json.loads(ln) for ln in jsonl.read_text(encoding="utf-8").splitlines() if ln.strip()]
    kept: dict[str, dict] = {}
    skipped = 0
    for rec in lines:
        if not _is_collected(rec):
            skipped += 1
            continue
        kept[rec["millie_id"]] = rec
    return list(kept.values()), {"n_lines": len(lines), "n_skipped_status": skipped}
```
D-05 형태: dedup 후 `kept.values()` 를 세 갈래로 — `title` 있음 → 유효 / `title` 없음 ∧ `shelf_count` 없음 ∧ `category` 없음 → `n_skipped_empty` / `title` 없음 ∧ `shelf_count` 있음 → `n_skipped_titleless`. `meta` dict 에 두 카운터 + `n_success`(dedup 후 성공 수)를 추가하고 docstring 두 번째 문장을 D-05 로 교체. `_present`(L45-51)를 판정에 재사용한다.

**변경점 2 — 카운터·단언 출력.** `coverage()` L211-227 의 dict 에 `n_skipped_empty`·`n_skipped_titleless`·`n_success`·`titleless_ratio` 키 추가(기존 키 유지 — `test_raw_coverage_json_is_written` L271-279 가 `n_records`·`n_lines`·`n_skipped_status`·`fields`·`category_distinct` 를 단정). 모듈 상수 `MAX_TITLELESS_RATIO = 0.005`(D-06). 단언은 스크립트가 아니라 **게이트 테스트**(`test_coverage_gate`)에서: `report["n_skipped_titleless"] / report["n_success"] <= MAX_TITLELESS_RATIO`(테스트는 상수를 import 하지 않고 `0.005` 를 손으로 적는다 — L23 관례).

**변경점 3 — 컬럼.** `COLUMNS` L17-23 에 `resid_z len_z difficulty` 를 `difficulty_source` 앞(또는 뒤)에 추가하고 `build_frame` 끝(L208 `return df` 직전)에서 `millie_difficulty.add_difficulty(df)` 호출. **`tests/data/test_millie_catalog.py::EXPECTED_COLUMNS` L24-59 는 정확한 순서 리스트**라 3컬럼 추가 시 같은 위치에 넣어야 한다 — 이것은 "게이트 강화"가 아니라 계약 컬럼 확장(`.claude/rules/data.md` 밀리 고유 컬럼 목록에 `resid_z len_z difficulty` 가 이미 있음)이므로 허용되는 테스트 수정이다. 브리프에 명시.

**변경점 4 — id 부여 범위(D-17).** `assign_ids` L114-146:

```python
    order = (
        sorted(_read_id_list(raw_dir / "catalog_urls.txt"))
        + _read_id_list(raw_dir / "discovered_urls.txt")
        + sorted(jsonl_ids)
    )
```
현재는 `catalog_urls`·`discovered_urls` 의 **모든** id 에 번호를 준다(미수집·껍데기 포함). 기존 테스트 제약: `test_book_ids_are_lexicographic_over_catalog_urls` L136 `assert FAILED_BOOK in ids` — **sitemap(`catalog_urls.txt`) 항목은 수집 실패여도 id 를 받는다**(재수집 시 id 밀림 방지). `test_discovered_urls_are_appended_in_file_order` L139-151 — discovered 순서 유지. D-17 "신규는 유효분만" 을 만족하는 최소 변경 = `discovered_urls` 목록을 `set(jsonl_ids)`(= 유효 레코드의 id)로 필터하고 `jsonl_ids` 에 유효 레코드만 넘긴다(`build` L234-238). `catalog_urls` 는 그대로. planner 는 이 해석을 브리프에 확정 문장으로 적는다(테스트 두 개 모두 유지 가능).

**함정:** `build()` L233 `records, meta = read_records(jsonl)` 이후 `records` 가 유효 레코드만이면 `coverage(records, meta)` 의 `n_records` 도 유효 수가 된다 — 게이트 분모 = 유효 레코드(D-05 의도와 일치). `test_dedup_keeps_last_collected_and_drops_failed_pages` L114-119 의 `len(df) == 12` 는 픽스처 12권이 전부 title 보유(`fields.title == 1.0` L277)라 변하지 않는다.

---

### `scripts/build_millie_edges.py` (MODIFY — 게이트 ③ 미달 시에만, D-10)

**현재 텍스트·유사도(변경 후보 지점):** L43-56

```python
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
    np.fill_diagonal(sim, -1.0)  # self-edge 금지 (게이트 ①)
    return sim
```
D-10 허용 조치 = "description 가중 상향(title 반복 축소)만". 현재 title 은 1회만 들어가므로 상향 수단은 description 을 2회 join(상수 `DESC_REPEAT = 2`)하는 정도. **먼저 실측**(`make millie-edges` 후 `uv run pytest tests/data/test_millie_edges.py::test_neighbour_quality_gate --no-header -s` 로 `top-20 동일 카테고리 비율 평균` 출력 확인) — 통과하면 이 파일은 무변경. 게이트 함수 `_same_category_share` 는 `tests/data/test_millie_edges.py` L57-71.

**메모리(CONTEXT):** `cosine_similarity` dense 5,157² float64 ≈ 213MB(float32 아님 — sklearn 기본 float64). 9천 권이면 ≈650MB. CONTEXT 허용 범위 안이지만 브리프에 "9천 권 초과 시 chunked top-k" 한 줄.

---

### `scripts/build_millie_popularity.py` (NEW — `popularity_kr` all 세그먼트)

**Analog A — 인기 순위 정의(정본):** `scripts/build_millie_catalog.py` L196-201

```python
    def _pop_key(row: dict) -> tuple[float, int]:
        shelf = row["shelf_count"]
        return (-(shelf if shelf is not None else -1), row["book_id"])

    for rank, row in enumerate(sorted(rows, key=_pop_key), start=1):
        row["pop_rank"] = rank  # shelf_count 내림차순, 결측은 마지막
```
→ `pop_rank` 는 이미 `books_kr.parquet` 에 있다. `segment="all"` 행은 **재계산하지 않고** `books_kr` 의 `pop_rank` 를 `rank`, `shelf_count` 를 `score`(결측 0.0)로 옮긴다(숫자 정본 1곳). 행 스키마 D-15: `{book_id, segment, score, rank}`.

**Analog B — argparse main + parquet 쓰기:** `scripts/build_millie_edges.py` L137-152

```python
def main() -> None:
    ap = argparse.ArgumentParser(description="books_kr.parquet → item_edges_kr.parquet")
    ap.add_argument("--books", type=Path, default=DIR_PROCESSED / "books_kr.parquet")
    ap.add_argument("--out", type=Path, default=DIR_PROCESSED / "item_edges_kr.parquet")
    ...
    args.out.parent.mkdir(parents=True, exist_ok=True)
    edges.to_parquet(args.out, index=False)
    counts = edges["source"].value_counts().to_dict()
    print(f"edges={len(edges)} {counts} → {args.out}")
```
→ 출력 `DIR_PROCESSED / "popularity_kr.parquet"`(`.claude/rules/data.md` Track B 표의 정본 파일명). json 변환은 export 가 담당(아래). `POP_COLUMNS = ("book_id", "segment", "score", "rank")`, `SEGMENT_ALL = "all"`.

**Should 꼬리 재료(이 페이즈 구현 안 함, 상수만 예약):** `seg_dist` 는 parquet 에 **json 문자열**(`_row` L184 `json.dumps(seg, ensure_ascii=False)`), 형태 `{"10대":{"남":1.4,"여":1.0},…,"60대~":{…}}`, 세그먼트 라벨은 `top_segment` 표기 그대로(`"40대 여성"`) — 변환 테이블 만들지 않는다(CONTEXT specifics).

**테스트(`tests/data/test_millie_popularity.py`):** `test_millie_edges.py` L38-48 의 module-scope fixture 체인(`_load("build_millie_catalog").build(FIXTURE, out, raw_dir=out)` → parquet 읽기)을 복사해 `build_millie_popularity.build(books)` 호출. 단정: 컬럼 4개·`segment` 전부 `"all"`·`rank` 가 `pop_rank` 와 동일·`rank` 1..N 연속·`score` 가 shelf_count 내림차순(픽스처 `FIRST_BOOK` shelf 9,814 = rank 1, `NO_SHELF_BOOK` = rank 12).

---

### `scripts/export_millie_serving.py` (MODIFY) + `scripts/export_millie_vectors.py` (NEW 권장)

**현재 전문 핵심:** `scripts/export_millie_serving.py` L17-40, L56-88

```python
MAX_BYTES = 50 * 1024 * 1024
BOOK_FIELDS = (
    "book_id", "title", "authors", "image_url", "average_rating", "ratings_count",
    "original_publication_year", "categories", "subcategories", "book_format", "tags",
    "pop_rank", "completion_prob", "category_avg_prob", "expected_min", "category_avg_min",
    "millie_label", "difficulty_source", "shelf_count", "review_count", "publisher",
)
...
def books_payload(books: pd.DataFrame) -> list[dict]:
    frame = books[list(BOOK_FIELDS)].sort_values("book_id")
    return [{k: _clean(v) for k, v in row.items()} for row in frame.to_dict("records")]


def edges_payload(edges: pd.DataFrame) -> dict[str, list[list]]:
    ordered = edges.sort_values(["src_book_id", "weight"], ascending=[True, False])
    out: dict[str, list[list]] = {}
    for row in ordered.to_dict("records"):
        out.setdefault(str(int(row["src_book_id"])), []).append(
            [int(row["dst_book_id"]), round(float(row["weight"]), 6), str(row["source"])]
        )
    return out


def _write(path: Path, payload: object) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    size = path.stat().st_size
    assert size < MAX_BYTES, f"{path.name} {size}B ≥ {MAX_BYTES}B — 서빙 산출물 상한 초과"
    return size


def export(books_path: Path, edges_path: Path, out_dir: Path) -> dict[str, int]:
    sizes = {
        "books_kr.json": _write(out_dir / "books_kr.json", books_payload(pd.read_parquet(books_path))),
        "item_edges_kr.json": _write(out_dir / "item_edges_kr.json", edges_payload(pd.read_parquet(edges_path))),
    }
    return sizes
```

**변경 1 — `BOOK_FIELDS` 갱신(= `Catalog.meta()` 필드).** CONTEXT: 계약 9개(`book_id title authors image_url average_rating ratings_count original_publication_year categories subcategories`) + `tags`(계약 호환) + `publisher book_format formats pop_rank millie_label review_count shelf_count completion_prob category_avg_prob expected_min category_avg_min difficulty difficulty_source resid_z len_z top_segment subtitle pub_date`. **제외 유지:** `description curator_note seg_dist millie_id isbn13 pages_diag collected_at source rating_observed`. 테스트가 `"description"`·`"curator_note"` 문자열이 `books_kr.json` 에 0건임을 단정한다(`tests/data/test_millie_export.py`).

**변경 2 — `popularity_kr.json`.** `pd.read_parquet(popularity_kr.parquet).to_dict("records")` → `_clean` → `_write`. 행 리스트 그대로(D-15 스키마).

**변경 3 — `content_vectors_kr.npz`(D-12) → 별도 파일 `scripts/export_millie_vectors.py` 권장**(export 102줄 + popular.json 빌더 ≈40줄로 이미 150 근접). TF-IDF 설정은 `build_millie_edges.py` L22·L53 과 **동일 값을 중복 정의**(`NGRAM_RANGE = (2, 4)`, `analyzer="char_wb"`, `min_df=1`, 텍스트 컬럼 `title description curator_note`) — scripts 간 import 함정(위 난이도 절)을 피하기 위한 허용 중복(`architecture.md` "5일 프로젝트에서는 중복 < 결합"). 형태:

```python
from sklearn.decomposition import TruncatedSVD
from sklearn.preprocessing import normalize
from millie_rec.contracts import DIR_ARTIFACTS, DIR_PROCESSED, SEED

SVD_DIM = 128  # D-12. PDF 각주 "다양성 벡터 = TF-IDF SVD 128"

def vectors(texts: list[str]) -> np.ndarray:
    tfidf = TfidfVectorizer(analyzer="char_wb", ngram_range=NGRAM_RANGE, min_df=1).fit_transform(texts)
    dim = min(SVD_DIM, tfidf.shape[0] - 1, tfidf.shape[1] - 1)  # 픽스처 12권에서 SVD 128 은 ValueError
    reduced = TruncatedSVD(n_components=dim, random_state=SEED).fit_transform(tfidf)
    return normalize(reduced).astype(np.float32)
...
np.savez(path, book_ids=books["book_id"].to_numpy(dtype=np.int64), vectors=vec)
```
**함정:** `TruncatedSVD(n_components)` 는 `n_components < n_features` 이고 실질 `≤ n_samples-1` 이어야 한다 → 소형 픽스처(12권·20권)에서는 `dim` 가드 없이는 예외. 난수는 `contracts.SEED`(`python.md`). `np.savez`(비압축) — 5,157×128 float32 ≈ 2.6MB, `_write` 대신 크기 단언만 별도(`path.stat().st_size < MAX_BYTES`).

**변경 4 — `demo/fallback/popular.json`(소유권 예외, `architecture.md` 산출물 표).** 현재 파일은 mock v1 형태로 `RecommendOut` 검증에 **실패**한다(기준선 표). 새 export 는 **`serving/schemas.py::RecommendOut` 가 그대로 파싱하는 형태**로 쓴다. 형태 정본은 서버 level 3 응답 = `serving/compose.py::build_response` L44-60 + `serving/fallback.py::trending_row` L37-45:

```python
    return RecommendResponse(
        items=flat,                       # level 3 이면 ()
        model_version=model_version,      # MODEL_VERSION_FALLBACK = "fallback_v1"
        fallback_level=level,             # FALLBACK_GLOBAL_POP = 3
        latency_ms=ms,                    # float (dict 아님!)
        recommendation_id=new_rec_id(),   # "rec_" + 6hex — 정적 파일은 "rec_static" 등 10자
        rows=(trending_row(items),),
        latency_breakdown={"total": ms},
        user_state_weights=dict(ZERO_WEIGHTS),   # {"alpha":0.0,"beta":0.0,"gamma":0.0}
        context=context,
    )
```
```python
def trending_row(items: Sequence[ScoredItem]) -> Row:
    return Row(
        row_id=TRENDING_ROW_ID,      # "trending"
        title=TRENDING_TITLE,        # "지금 많이 읽는 책"
        purpose=TRENDING_PURPOSE,    # "fallback"
        items=tuple(items),
        channel_mix={SOURCE_POPULARITY: len(items)} if items else {},   # {"popularity": 40}
    )
```
items 의 필드는 `schemas.py::ItemOut` L138-152 와 1:1(`extra="forbid"`): `book_id score source reason title authors image_url position source_channels badge book_format difficulty` — **`format` 키 금지**(현 파일의 실패 원인). 스크립트는 `millie_rec.serving` 을 import 하지 않고 dict 를 직접 조립(`contracts.MODEL_VERSION_FALLBACK`·`FALLBACK_GLOBAL_POP` 만 import), **검증은 `tests/data/test_millie_export.py` 에서 `RecommendOut.model_validate(json.loads(...))`**(tests 는 무엇이든 import 가능). items = `pop_rank` 상위 40(eligible 필터 — export 시점엔 `Catalog` 가 없으니 같은 규칙을 title·`*.millie.co.kr`·`adult-cover` 로 인라인), `score = float(40 - i)`(`fallback.py` L28 관례), `source="popularity"`, `source_channels=["popularity"]`, `position=i`.

**데모 영향(Phase 6 몫, planner 참고):** `demo/js/api.js` L86-87 은 파일을 그대로 spread 만 한다(`{ ...fb, client_fallback_reason }`). `demo/js/inspector.js` L65-69 `latencySection` 은 `latency_ms` 를 dict 로 읽어 단계 막대를 그린다 — float 이 되면 막대가 비고 `total` 이 `NaN%` 가 되지만 예외는 없다. `s7_home.js` L10 `item.format === "PDF"` 는 undefined → false. 즉 **크래시 없음, 표시 열화만** → Phase 6 '데모 재구성'(`make_mock.py` L371-400 의 popular.json 생성 블록도 그때 제거).

**Makefile 연결(Advisor):** `millie-export` 타깃(L19-20)은 `export_millie_serving.py` 하나만 부른다. vectors 를 별도 스크립트로 빼면 `millie-export` 에 `&& uv run python scripts/export_millie_vectors.py` 추가 + popularity 빌드 타깃 신설 → `millie` 체인(L22) 갱신. Advisor 직접 편집(Worker 금지).

---

### `src/millie_rec/data/catalog_kr.py` (adapter — `Catalog`·`Neighbors`·`BookStatsSource`) — NEW

**Analog A — json 아티팩트를 읽는 Protocol 구현 + `load` classmethod:** `src/millie_rec/retrieval/popularity.py` L22-28, L55-58

```python
class PopularityRetriever:
    """전역 인기 상위 k. fit 은 train 만 받는다(Protocol docstring 그대로)."""

    name = "pop"

    def __init__(self, ranked: Sequence[tuple[int, float]] = ()) -> None:
        self._ranked: list[tuple[int, float]] = [(int(b), float(s)) for b, s in ranked]
    ...
    @classmethod
    def load(cls, path: Path = POP_ARTIFACT) -> "PopularityRetriever":
        payload = json.loads(path.read_text(encoding="utf-8"))
        return cls((int(b), float(s)) for b, s in payload["items"])
```
→ `CatalogKR.__init__(self, books: list[dict], edges: dict[str, list[list]] | None = None)` + `@classmethod load(cls, serving_dir: Path = DIR_ARTIFACTS / "serving") -> "CatalogKR"`. **pandas 를 import 하지 않는다**(`serving.md` "서빙 경로에서 pandas import 금지" — json/npz 는 stdlib `json` + numpy 로 충분). 파일 이름 상수: `BOOKS_KR_JSON = "books_kr.json"`, `EDGES_KR_JSON = "item_edges_kr.json"`, `POP_KR_JSON = "popularity_kr.json"`, `VECTORS_KR_NPZ = "content_vectors_kr.npz"`; `DIR_SERVING = DIR_ARTIFACTS / "serving"` 은 `app/export.py` L16 에 같은 이름이 있지만 data 는 app 을 import 못 하므로 **중복 정의**.

**Analog B — 만족해야 할 Protocol(verbatim):** `src/millie_rec/contracts.py` L316-338

```python
class Catalog(Protocol):
    """도서 메타·인기도 (serving compose·fallback 용). data 가 제공하고 app 이 주입."""

    def meta(self, book_ids: Sequence[int]) -> list[dict]: ...
    def popular(self, categories: Sequence[str] = (), n: int = 50) -> list[int]: ...
    def eligible(self, book_ids: Sequence[int]) -> list[int]: ...  # main §7 노출 자격 게이트


class Neighbors(Protocol):
    def neighbors(self, book_id: int, n: int = 20) -> list[tuple[int, float]]: ...


class BookStatsSource(Protocol):
    def stats(self, book_ids: Sequence[int]) -> list[BookStats]: ...
    def user_level(self, user: UserState) -> float | None: ...
```
하나의 클래스가 셋을 모두 구현해도 되고(structural typing — `create_app` 에 같은 객체를 `catalog=`·`neighbors=`·`book_stats=` 로 세 번 넘김), 줄 수 때문에 `Neighbors` 만 `NeighborsKR` 로 분리해도 된다. planner 판단 — 한 클래스면 ≈110줄 예상.

**Analog C — `popular()` 의 호출 형태(소비자가 기대하는 것):** `src/millie_rec/serving/fallback.py` L24

```python
        ids = [b for b in self.catalog.popular(n=k + len(user.seen)) if b not in user.seen][:k]
```
→ `popular(categories=(), n=50)`: `categories` 비면 전체, 아니면 `categories[0] in book["categories"]` 교집합; `pop_rank` 오름차순; **`eligible` 필터 적용 후** 상위 n(CONTEXT Discretion). `__init__` 에서 `self._pop_order = sorted(eligible ids, key=pop_rank)` 를 1회 계산해 요청마다 정렬하지 않는다(`serving.md` "요청마다 fit·재계산 금지").

**`eligible()` 규칙(D-14 verbatim):** `title` 있음 ∧ `image_url` 호스트가 `*.millie.co.kr`(실측 `img.`·`image.`·`cover.` 3종) ∧ 성인 표지 플레이스홀더(`adult-cover`) 아님. 구현: `from urllib.parse import urlsplit` → `host = urlsplit(url).hostname or ""`, `host.endswith(".millie.co.kr")`, `"adult-cover" not in url`. 상수 `COVER_HOST_SUFFIX = ".millie.co.kr"`, `ADULT_COVER_MARK = "adult-cover"`. 실측 분포(기준선 표)로 400권이 `img.` 외 호스트 → `endswith` 필수, 정확 일치 금지.

**`meta()`:** `self._by_id: dict[int, dict]` 에서 `[self._by_id[b] for b in book_ids if b in self._by_id]` — 미지 id 는 건너뛴다(`ContentVectors.vectors` L38 의 `if int(b) in self._index` 관례). 반환 dict 는 `books_kr.json` 행 그대로(export `BOOK_FIELDS` = meta 필드, 정본 1곳).

**`neighbors(book_id, n=20)`:** `item_edges_kr.json` 은 `{ "src": [[dst, weight, source], …] }` 이며 export 가 이미 weight 내림차순으로 정렬(`edges_payload` L62). `[(int(d), float(w)) for d, w, _src in self._edges.get(str(book_id), [])[:n]]`. 키가 **문자열**임에 주의(json).

**`stats()` — `contracts.BookStats` DTO(verbatim):** `contracts.py` L168-192

```python
@dataclass(frozen=True, slots=True)
class BookStats:
    book_id: int
    difficulty: float | None = None  # 0~1 합성 D_book. None = 결측
    completion_rate: float | None = None  # 밀리 P_완독(0~1) 또는 데모 집계
    early_dropoff_rate: float | None = None
    rating_mean: float | None = None
    rating_var: float | None = None
    n_events: int = 0
    source: str = "prior"  # STATS_SOURCES
    completion_prob: float | None = None  # %
    category_avg_prob: float | None = None
    expected_min: float | None = None
    category_avg_min: float | None = None
    resid_z: float | None = None
    len_z: float | None = None
```
매핑: `difficulty=row["difficulty"]`, `completion_rate = row["completion_prob"]/100 if not None`(계약 주석 "0~1" vs `completion_prob` "%"), `source=row["difficulty_source"]`(`STATS_SOURCES` 안), `completion_prob category_avg_prob expected_min category_avg_min resid_z len_z` 그대로, `rating_mean=row["average_rating"]`, 나머지 기본값. `user_level(user) -> None`(Phase 4 가드 몫, 이 페이즈는 `None` 고정).

**import 허용 범위(`tests/test_architecture.py` L37-42 정적 검사):** `millie_rec.contracts` + `millie_rec.data.*` 만. `millie_rec.serving`·`millie_rec.retrieval` import = 즉시 실패.

---

### `src/millie_rec/data/vectors_kr.py` (`ItemVectors`, npz) — NEW, exact analog

**Analog:** `src/millie_rec/retrieval/content.py` L20-42 (전문)

```python
class ContentVectors:
    """L2 정규화 dense 벡터. 미지 id 는 0 벡터(ILD 에서 거리 1)."""

    def __init__(self, books: "pd.DataFrame", text_col: str = TAGS_COL) -> None:
        ...
        self._matrix = vec.fit_transform(texts)  # (n_books, dim), 행 L2=1(빈 문서는 0)
        self._index = {int(b): i for i, b in enumerate(books[COL_ITEM].tolist())}

    @property
    def dim(self) -> int:
        return int(self._matrix.shape[1])

    def vectors(self, book_ids: Sequence[int]) -> np.ndarray:
        out = np.zeros((len(book_ids), self.dim), dtype=float)
        rows = [(i, self._index[int(b)]) for i, b in enumerate(book_ids) if int(b) in self._index]
        if rows:
            dst, src = zip(*rows, strict=True)
            out[list(dst)] = self._matrix[list(src)].toarray()
        return out
```
→ 차이 2줄: `__init__(self, book_ids: np.ndarray, vectors: np.ndarray)` + `@classmethod load(cls, path) -> "VectorsKR"`: `z = np.load(path); cls(z["book_ids"], z["vectors"])`. dense 라 `.toarray()` 없이 `self._matrix[list(src)]`. `contracts.ItemVectors` Protocol(L310-313)은 `vectors(book_ids) -> np.ndarray` 하나. Phase 4 `hybrid_div` 가 서버에서 주입받는다 — 이 페이즈는 `create_app` 인자에 없으므로 **로드·테스트만**(`data/__init__` 노출).

**테스트(`tests/data/test_catalog_kr.py` 안 또는 별도):** `tests/retrieval/test_content.py` L22-52 의 4단정 그대로 — shape `(len(ids), dim)` · 행 L2 norm ≈ 1 · 입력 순서 보존 · 미지 id = 0 벡터. npz 픽스처는 `np.savez(tmp_path/"v.npz", book_ids=np.array([10,20,30]), vectors=np.eye(3, dtype=np.float32))` 로 테스트 안에서 만든다.

---

### `src/millie_rec/data/__init__.py` (MODIFY)

**현재:** L1-57 — `from millie_rec.data.<module> import (...)` 블록 + 알파벳 정렬 `__all__`(대문자 상수 먼저, 그다음 클래스, 그다음 함수 — L31-57 순서 그대로 따른다). 추가: `from millie_rec.data.catalog_kr import CatalogKR`(+ `BOOKS_KR_JSON`·`DIR_SERVING` 등 app 이 존재 검사에 쓸 상수) · `from millie_rec.data.vectors_kr import VectorsKR`. **주의:** `data/__init__` 은 `goodbooks.py`(pandas·urllib 모듈 수준 import) 를 이미 끌어온다 → `app/server.py` 가 `from millie_rec.data import CatalogKR` 를 하면 서버 기동 시 pandas 가 로드된다(현재 서버 경로는 pandas 무로드). `serving.md` 규칙의 취지는 **요청 경로**이며 기동 1회 import 는 허용 범위지만, Advisor 가 인지하고 브리프에 적는다(대안: 없음 — `app` 은 공개 표면만 import 가능, L41-42).

---

### `src/millie_rec/app/pipeline.py` (MODIFY — Track B pop 교체, D-13)

**현재 조립 함수:** L46-55

```python
def build_pipelines(artifact: Path = POP_ARTIFACT) -> dict[str, Pipeline]:
    """서버 기동(D-10): 아티팩트 있으면 pop, 없거나 손상되면 {} — 기동을 막지 않는다."""
    if not artifact.exists():
        log.info("no pop artifact at %s — serving level 3 only", artifact)
        return {}
    try:
        return {POP: PopPipeline(PopularityRetriever.load(artifact))}
    except (OSError, ValueError, KeyError, TypeError):  # json 손상·키 누락·형 불일치
        log.exception("pop artifact unreadable at %s — serving level 3 only", artifact)
        return {}
```
D-13: 서버는 Goodbooks `popularity.json` 을 **로드하지 않는다** → 이 함수는 `build_pipelines(catalog: Catalog | None) -> dict` 로 의미가 바뀐다(`{POP: CatalogPopPipeline(catalog)}` 또는 `{}`). `fit_pipelines(train)` L41-43 은 `make eval` 용으로 불변.

**Track B pop 의 재료(그대로 복제):** `src/millie_rec/serving/fallback.py` L21-34

```python
    def recommend(self, user: UserState, k: int) -> list[ScoredItem]:
        if self.catalog is None:
            return []
        ids = [b for b in self.catalog.popular(n=k + len(user.seen)) if b not in user.seen][:k]
        return [
            ScoredItem(book_id=b, score=float(len(ids) - i), source=SOURCE_POPULARITY,
                       position=i, source_channels=(SOURCE_POPULARITY,))
            for i, b in enumerate(ids)
        ]
```
→ `app/pipeline.py` 에 `class CatalogPopPipeline: name = POP; def __init__(self, catalog: Catalog)` + 위 본문(≈15줄, `app` 은 `millie_rec.serving` 공개 표면 `GlobalPopularFallback` 을 import 할 수 있으나 `name` 이 `"fallback"` 클래스 속성이라 재사용 대신 복제). `k` 상한은 `api.py` L29 `K_MAX = 100` 이 이미 쿼리에서 막는다.

**기존 테스트와의 충돌(브리프에 명시, python-tdd "테스트 고쳐서 통과 금지" 예외 근거 = D-13 의도된 동작 변경):**
- `tests/app/test_pipeline.py::test_build_pipelines_loads_pop_and_recommend_excludes_seen` L30-42 와 `test_build_pipelines_empty_when_artifact_missing`·`..._malformed` L13-26 은 Goodbooks 아티팩트 로드를 단정 → D-13 이후 **대체**(catalog None → `{}`, `_FakeCatalog` → `{"pop"}` + seen 제외). `tests/app/` 는 Advisor 영역.
- `tests/serving/test_smoke.py` L170·L189 는 `monkeypatch.setattr("millie_rec.app.pipeline.build_pipelines", lambda: {})` — **인자 0개 lambda**. `server.py` 가 `build_pipelines(catalog)` 로 호출하면 `TypeError`. 해법: 새 조립 함수 이름을 따로 두고(`build_serving(...)` 또는 `build_catalog()`), `build_pipelines()` 는 **인자 없이** 호출되는 형태를 유지(내부에서 catalog 를 스스로 로드) — 그래야 기존 smoke 테스트 2개가 무수정으로 통과한다. 또는 smoke 테스트를 갱신(Advisor 결정). planner 는 둘 중 하나를 확정해 브리프에 적는다.

---

### `src/millie_rec/app/server.py` (MODIFY — Advisor 전용, 1~4행)

**현재 전문:** L1-18

```python
"""uvicorn 진입점: create_app 주입 + demo/ StaticFiles(마지막). CORS 없음(아키텍처 01 §9-3)."""

from fastapi.staticfiles import StaticFiles

from millie_rec.app.pipeline import build_pipelines
from millie_rec.contracts import ROOT
from millie_rec.serving import Database, GlobalPopularFallback, create_app, resolve_db_path

# Phase 2 ✅ pipelines=build_pipelines()(아티팩트 있으면 pop, D-10),
# Phase 3 → catalog, Phase 5 → neighbors·book_stats·state.
# 이 호출의 인자만 채운다 — 시그니처 불변(CONTEXT D-09).
app = create_app(
    pipelines=build_pipelines(),
    fallback=GlobalPopularFallback(None),
    db=Database(resolve_db_path()),
)
# 반드시 마지막 — 앞에 두면 /health·/api/* 가 StaticFiles 에 가려진다
app.mount("/", StaticFiles(directory=ROOT / "demo", html=True), name="demo")
```
**목표 형태(D-13):** 카탈로그 로더 결과 `catalog`(없으면 `None`)를 `fallback=GlobalPopularFallback(catalog)`, `catalog=catalog`, `neighbors=catalog`, `book_stats=catalog`(한 클래스일 때) 로 넘긴다. `create_app` 시그니처(`serving/api.py` L81-90, keyword-only `catalog db neighbors book_stats state`) 불변. 로더는 `app/pipeline.py`(또는 새 `app/catalog.py`)의 `load_catalog(serving_dir=DIR_SERVING) -> CatalogKR | None`: `books_kr.json` 없으면 `None` + `log.info`, 손상이면 `log.exception` + `None`(`build_pipelines` L48-55 의 예외 집합 `(OSError, ValueError, KeyError, TypeError)` 그대로). **import 시점 부작용 금지**(smoke 테스트가 `sys.modules.pop` 후 재import — 5,157권 json 로드 ≈ 수십 ms 는 허용).

**테스트 제약:** `tests/serving/test_smoke.py::test_server_module_serves_demo_index_and_keeps_api_routes` L164-181 은 `fallback_level == 3` 만 단정(items 비어 있는지는 안 봄) → 실 아티팩트가 있어도 통과. 새 주입 테스트는 **실 `artifacts/serving/` 을 읽지 않도록** 로더도 monkeypatch 한다(아래).

---

### `tests/app/test_server_catalog.py` (서버 주입 테스트) — exact analog

**Analog:** `tests/serving/test_smoke.py` L184-198

```python
def test_server_module_injects_pop_pipeline_when_build_pipelines_returns_pop(
    tmp_path: Path, monkeypatch
):
    """app.server:app — build_pipelines() 가 pop 을 주면 /api/recommend 는 level 0(D-10 배선)."""
    monkeypatch.setenv(ENV_DATA_DIR, str(tmp_path))
    monkeypatch.setattr("millie_rec.app.pipeline.build_pipelines", lambda: {"pop": _FakePop()})
    sys.modules.pop("millie_rec.app.server", None)
    server = importlib.import_module("millie_rec.app.server")
    with TestClient(server.app) as c:
        rec = c.get("/api/recommend", params={"seeds": "1,2,3", "k": 5})
        anon = c.get("/api/recommend")
    assert rec.status_code == 200 and rec.json()["fallback_level"] == FALLBACK_PERSONALIZED
    assert rec.json()["model_version"] == "pop" + MODEL_VERSION_SUFFIX
    assert [i["book_id"] for i in rec.json()["items"]] == [4, 5, 6, 7, 8]
    assert anon.status_code == 200 and anon.json()["fallback_level"] == FALLBACK_GLOBAL_POP  # D-13
```
복사할 것: `ENV_DATA_DIR` → `tmp_path`(실 DB 미접촉) · 로더를 `monkeypatch.setattr("millie_rec.app.<module>.<loader>", lambda: CatalogKR.load(FIXTURE_DIR))` · `sys.modules.pop` 후 `importlib.import_module`. 단정(CONTEXT): `fallback_level == FALLBACK_PERSONALIZED` · `model_version == "pop" + MODEL_VERSION_SUFFIX`(= `"pop_v1"`) · `rows[0]["row_id"] == "trending"` · `items ⊂ fixture ids ∖ seeds` · 익명은 level 3 이지만 `rows[0]["items"]` 가 **비어 있지 않음**(catalog 주입된 fallback) · `rows[0]["items"][0]["title"]` 은 한글 제목(meta 조인은 Phase 5 compose 몫이면 이 단정은 제외 — planner 판단: Phase 3 `CatalogPopPipeline` 이 `ScoredItem.title` 을 채울지). 실 `artifacts/serving/` 은 읽지 않는다.

**대안(더 단순, serving 레인 단독):** `create_app(pipelines={"pop": CatalogPopPipeline(cat)}, fallback=GlobalPopularFallback(cat), catalog=cat, db=Database(tmp_path / DB_FILENAME))` 를 직접 조립(`tests/serving/test_recommend_level0.py::_app` L64-69 형태). 서버 모듈 재import 없이 빠르다. 둘 다 두면 배선·동작을 각각 증명한다.

---

### `tests/fixtures/millie/serving_sample/` (NEW fixture)

**Analog:** `tests/fixtures/millie/sample_records.jsonl`(14줄·12권, 레코드 키 = 실수집과 동일: `millie_id status title category completion_prob category_avg_prob expected_min category_avg_min shelf_count image_url formats millie_label top_segment seg_dist best_links description curator_note …`).

두 가지 방법(planner 택1):
- **정적 커밋(CONTEXT 명시):** 실 `millie_pages.jsonl` 에서 title·description·completion_prob 보유 20권을 골라 임시 jsonl → `build_millie_catalog.build → build_millie_edges → build_millie_popularity → export(+vectors)` 를 `--out tests/fixtures/millie/serving_sample` 로 1회 실행해 `books_kr.json`(description 없음이라 저작 텍스트 미포함) · `item_edges_kr.json` · `popularity_kr.json` · `content_vectors_kr.npz`(SVD dim = min(128, 19)) 를 커밋. 재현 명령을 fixture 폴더 `README` 1줄 또는 테스트 docstring 에 남긴다. `id_map` 은 fixture 전용 임시 경로(`--id-map`)로 — **`data/id_map.csv` 를 건드리지 않는다**.
- **런타임 생성(`test_millie_edges.py` L38-48 패턴):** module-scope fixture 가 `sample_records.jsonl`(12권) 로 tmp 에 빌드·export → `CatalogKR.load(tmp)`. 커밋 파일 0, 단 tests/app 과 tests/data 양쪽에서 쓰려면 `tests/conftest.py` 에 둔다.

---

### `tests/data/test_millie_export.py` (NEW) · `test_coverage_gate` 확장

**Analog — 산출물 키·크기 단정:** `tests/app/test_export.py` L38-55 (`out.exists()` → `json.loads` → `set(d) == {...}`). 단정 목록: ① 4개 파일 존재 + 각 `stat().st_size < 50*1024*1024` ② `books_kr.json` 각 행 키 집합 == 기대 필드 집합(손으로 적음) ∧ `"description" not in raw_text` ∧ `"curator_note" not in raw_text` ③ npz `book_ids.shape[0] == vectors.shape[0]`, `vectors.dtype == float32`, 행 norm ≈ 1, `vectors.shape[1] == min(128, n-1)` ④ `popularity_kr.json` 행 키 == `{"book_id","segment","score","rank"}` ∧ 전부 `"all"` ⑤ `demo/fallback/popular.json`(tmp 경로로 리다이렉트한 것) → `RecommendOut.model_validate` 성공 ∧ `fallback_level == 3` ∧ `rows[0]["row_id"] == "trending"` ∧ `len(items) == min(40, n_eligible)`.

**`test_coverage_gate` 확장(L283-312):** csv 에 `_n_skipped_empty`·`_n_skipped_titleless` 행 추가(L301-303 형식) + `assert report["n_skipped_titleless"] / report["n_success"] <= 0.005`. skip 조건·기존 단정 불변(강화 방향만, D-06).

---

## Shared Patterns

### 파일 쓰기 — `mkdir` → `write_text(ensure_ascii=False, encoding="utf-8")` → 크기 단언
**Source:** `scripts/export_millie_serving.py::_write` L71-76 · **Apply to:** popularity json·popular.json·npz(크기 단언만). parquet 는 `df.to_parquet(path, index=False)`(`build_millie_edges.py` L146).

### json 산출물의 값 정리 — pandas NA/ndarray → 파이썬 기본형
**Source:** `scripts/export_millie_serving.py::_clean` L43-53 · **Apply to:** `books_payload`(difficulty NaN → None) · popularity 행 · popular.json items. 새 float 컬럼(`resid_z len_z difficulty`)의 NaN 이 `None` 으로 나가는지 테스트 1건.

### scripts 테스트 로딩 — importlib
**Source:** `tests/data/test_millie_catalog.py::_load` L83-89 (verbatim)
```python
def _load(name: str):
    """scripts/ 는 패키지가 아니므로 경로로 직접 로드한다."""
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module
```
**Apply to:** 새 tests/data 3파일. 스크립트가 다른 스크립트를 import 하면 **의존 스크립트를 먼저 `_load`** 한다(위 난이도 절 함정).

### Protocol 구현 클래스 — 상속 없음, `load` classmethod, 요청마다 재계산 금지
**Source:** `retrieval/popularity.py` L22-58 · `retrieval/content.py` L20-42 · **Apply to:** `CatalogKR`·`VectorsKR`·`CatalogPopPipeline`. `__init__` 은 주입·인덱스 1회 구축만.

### seen 제외 + 넉넉히 뽑기
**Source:** `serving/fallback.py` L24 `popular(n=k + len(user.seen))` → 필터 → `[:k]` · **Apply to:** `CatalogPopPipeline.recommend`, popular.json 40권 선택(seen 없음).

### 아티팩트 유무에 따른 기동 — 있으면 로드, 없거나 손상이면 None/{} + log
**Source:** `app/pipeline.py::build_pipelines` L46-55 · **Apply to:** 카탈로그 로더. 예외 집합 `(OSError, ValueError, KeyError, TypeError)`, `log.info`(부재)/`log.exception`(손상). 기동을 막지 않는다(`local-run.md` "아티팩트·DB·네트워크 없이 기동").

### 테스트 3종 구분 주석 + 손계산 상수
**Source:** `tests/serving/test_smoke.py` L81·L99·L148 (`# ── 계약 ──`/`# ── 정확성 ──`/`# ── 안전성 ──`), `tests/data/test_millie_catalog.py` L23 "스크립트 상수를 import 하지 않고 손으로 적어 둔다" · **Apply to:** 모든 새 테스트.

### 실데이터 게이트는 산출물 부재 시 skip, 미달은 fail
**Source:** `tests/data/test_millie_catalog.py` L283-289, `test_millie_edges.py` L138-144 · **Apply to:** 확장 게이트. 합성 테스트는 skip 금지(`python-tdd.md` "pytest.skip 으로 실패를 숨기는 것" 금지 — 게이트의 skip 은 산출물 부재 조건이라 예외).

---

## 적용 규칙 발췌 (`/Users/shinwonchul/Documents/신원철/밀리의서재/.claude/rules/`)

| 경로 | 적용 rule 파일 |
|---|---|
| `scripts/*.py` · `tests/data/**` · `tests/fixtures/**` · `data/id_map.csv` | `data.md` · `python.md` · `python-tdd.md` · `simplicity.md` · `architecture.md`(산출물 소유권) |
| `src/millie_rec/data/catalog_kr.py` · `vectors_kr.py` · `data/__init__.py` | `python.md` · `python-tdd.md` · `architecture.md` · `simplicity.md` · `data.md` |
| `src/millie_rec/app/pipeline.py` · `app/server.py` | `architecture.md`(Advisor 전용) · `python.md` · `local-run.md` |
| `tests/app/*` · `tests/serving/*` | `serving.md`(테스트 절) · `python-tdd.md` |
| `demo/fallback/popular.json`(export 가 쓰는 것만) | `architecture.md` 소유권 예외 · `serving.md` 매니페스트 · `demo.md` L13 |

**verbatim 인용(브리프에 그대로 인라인):**
- `architecture.md` import 규칙: "슬라이스(`app` 제외)는 `millie_rec.contracts`와 **자기 슬라이스 내부**만 import한다. 다른 슬라이스 import 금지." / "`app`은 다른 슬라이스의 **공개 이름만** import한다: `from millie_rec.retrieval import ItemKNNRetriever` ✅ / `from millie_rec.retrieval.itemknn import ...` ❌" / "`tests/test_architecture.py`가 위 규칙을 정적으로 검사한다. 실패하면 규칙을 어긴 것이다. **테스트를 고치지 않는다.**"
- `architecture.md` 산출물 소유권: "`artifacts/serving/` | app(`export`) + `scripts/export_millie_serving.py` | serving은 기동 시 읽기만. Dockerfile `COPY` 대상. 파일당 <50MB, `description` 미포함" / "`demo/` | demo 레인 | serving·app은 `demo/`를 읽지 않는다. `artifacts/serving/` export가 `demo/fallback/popular.json`을 갱신하는 것만 허용" / "`data/id_map.csv` · `data/processed/*_kr.parquet` · `scripts/*.py` · `tests/fixtures/millie/` | data 레인(밀리 적재) | append-only id_map."
- `simplicity.md` 코드 규칙: "파일 150줄 이하(`src/` 파이썬). 넘으면 관심사가 2개다." / "함수 우선. 클래스는 `contracts.py`의 Protocol을 만족시킬 때만." / "설정은 모듈 상단 대문자 상수." / "추상화는 두 번째 사용에서. 베이스 클래스·레지스트리·팩토리·플러그인 금지."
- `data.md` (`scripts/` 절): "수집·빌드 스크립트 (`millie-rec/scripts/`, 각 ≤150줄, data 레인 소유)" — D-16 이 3파일(270·283·260줄)을 예외로 확정(개발일지 D 항목 기록 예정). 새 파일은 ≤150.
- `data.md` id: "`book_id`는 계약대로 **int**. 밀리 16자 hex id → `data/id_map.csv`(`millie_id,book_id,first_seen_at`) 사전순 1회 부여, 보충분은 N+1부터 **append-only**. 재수집·재빌드에도 기존 행 변동 0(diff 검증). 경로 상수 `contracts.FILE_ID_MAP`. `shelf_count` 순 id 부여 금지(인기 누설·재부여)."
- `data.md` 텍스트: "**텍스트 2개(`description` ≤400자, `curator_note` ≤100자)는 TF-IDF 입력 전용.** parquet에는 있지만 `artifacts/serving/*`·API·화면에 내보내지 않는다."
- `python-tdd.md` 실행: "`uv run pytest <대상> --no-header` — `-q` 는 pyproject addopts 에 이미 있다. CLI 에 `-q` 를 또 붙이면 `-qq` 가 되어 'N passed' 요약 줄이 사라진다" / "**Red는 `AssertionError`(의도한 단정 실패) 메시지로 확인**한다. `ImportError`·`SyntaxError`·collection error는 Red가 아니다." / "`scripts/`(밀리 적재) | 파서·게이트 함수는 fixture(`tests/fixtures/millie/`) 기반 테스트 필수. 네트워크 호출은 테스트 안 함" / 금지 "테스트를 통과시키려고 `test_architecture.py`나 기존 테스트의 단정을 고치는 것."
- `python.md`: "완료 전 순서대로: `uv run ruff format . && uv run ruff check . && uv run pytest --no-header`. 셋 다 통과해야 완료다." / "난수는 `millie_rec.contracts.SEED` 하나. `np.random.default_rng(SEED)`." / "경로는 `contracts.py`의 `DIR_*` 상수에서 시작한다."
- `serving.md`: "artifacts는 기동 시 1회 로드(`npz`+`json`, **서빙 경로에서 pandas import 금지** — 메모리 0.3GB대). 요청마다 fit·재계산 금지." / 매니페스트 "`books_kr.json`(계약 컬럼 + 밀리 컬럼, **`description`·`curator_note` 미포함**) · `item_edges_kr.json` · `content_vectors_kr.npz`(MMR·ILD) · `popularity_kr.json`(all + 세그먼트) · `eval_table.json` + `demo/fallback/popular.json`. `difficulty`는 `books_kr.json` 컬럼(별도 `difficulty_prior.json` 없음)."
- `local-run.md`: "**모든 브리프의 완료 기준에 로컬 스모크를 넣는다:** `uv run pytest --no-header` + `make smoke`(서버 기동 → `/health`·`/`·`/api/recommend` 확인 → 종료)." / "`artifacts/serving/`이 비어 있으면 빈 `trending` 행 + level 3."

---

## No Analog Found

없음. 부분 아날로그만 있는 두 곳은 규칙·CONTEXT 수식을 정본으로 인용했다:

| File | Role | 부족한 부분 | 대체 정본 |
|---|---|---|---|
| `scripts/millie_difficulty.py` | pure stats | repo 에 z-score·분위 코드 0 | `.claude/rules/data.md` Track B 난이도 절 + CONTEXT Discretion "난이도 파생 세부"(분위 4·표본 <20 전역·<5 또는 std=0 전역 std·σ(−resid_z)·결측 규칙). pandas `groupby(...).transform` + `pd.qcut(duplicates="drop")` 권장 |
| `scripts/export_millie_vectors.py` | exporter (SVD) | repo 에 `TruncatedSVD`·`np.savez` 사용 0 | CONTEXT D-12(`np.savez(path, book_ids=int64[N], vectors=float32[N,128])`, 행 L2≈1) + `build_millie_edges.py::similarity` TF-IDF 설정 + `contracts.SEED` |

---

## Metadata

**Analog search scope:** `src/millie_rec/**`(contracts·data·retrieval·serving·app 20 파일) · `scripts/*.py`(5) · `tests/**`(data·serving·app·retrieval·evaluation 12 파일 + conftest + test_architecture) · `demo/js/api.js`·`inspector.js`·`screens/s7_home.js` · `demo/scripts/make_mock.py` L186-200·L330-400 · `demo/fallback/popular.json` · `Makefile` · `.gitignore` · `pyproject.toml` · `.claude/rules/{data,python,python-tdd,serving,architecture,simplicity,local-run,demo}.md`
**Files scanned:** 42 code/test + 8 rules + 3 build files
**실측 보조:** `uv run pytest --no-header`(171 passed·2 skipped) · `uv run ruff check .`(clean) · `RecommendOut.model_validate(demo/fallback/popular.json)` → 41 validation errors · `millie_pages.jsonl` 키·dtype·호스트 분포(위 기준선 표)
**Pattern extraction date:** 2026-09-05
**Codegraph:** 미사용(파일 수 소규모라 직접 Read/Bash 가 빨랐음. 인덱스는 `millie-rec/.codegraph/`, 호출 시 `projectPath` 필수)
