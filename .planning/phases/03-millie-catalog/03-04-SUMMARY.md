# Plan 03-04 SUMMARY — build_millie_popularity(all) + export books_kr.json 28필드 · popularity_kr.json

Phase 3 '밀리 카탈로그 빌드'(.planning/ROADMAP.md "Phase 3: 밀리 카탈로그 빌드") / Plan 04 (DATA-07).
**커밋하지 않는다** — 변경은 작업 트리에만 남긴다(플랜 frontmatter `no_commit: true`, 선례 결정 'D-18 커밋 없음'(.planning/phases/02-track-a/02-CONTEXT.md)).

## 0. 이전 Worker 부분 산출물 처리 — 3파일 전부 유지(재작성 없음)

세션 한도로 중단된 이전 Worker 가 18:55~18:56 에 남긴 세 파일을 플랜 Task 1 지시와 대조했다.

| 파일 | 플랜 대조 결과 | 처리 |
|---|---|---|
| `scripts/build_millie_popularity.py` (스텁) | 1-a 그대로 — docstring · `POP_COLUMNS` · `SEGMENT_ALL` · `SEG_DIST_COL` · 빈 프레임 `build` · argparse `--books --out` | **유지**, Task 2 에서 `build` 본문만 교체 |
| `tests/data/test_millie_popularity.py` | 1-b 그대로 — `_load` 사본 · module fixture `books`/`pop_mod`/`pop` · `_all_rows` 헬퍼(D-15 범위 규칙) · 테스트 5건 이름·단정 일치 | **유지** |
| `tests/data/test_millie_export.py` | 1-c 그대로 — `inspect.signature` → `pytest.fail` 장치 · `EXPECTED_BOOK_KEYS` 28개 손기입 · 픽스처 체인(catalog → edges → popularity → export) · 테스트 8건 일치 | **유지** |

`scripts/export_millie_serving.py` 는 이전 Worker 가 손대지 않았다(`git diff` 없음) — Task 2 에서 처음 수정했다.
**RED 는 이전 Worker 의 출력을 인정하지 않고 아래 §1 에서 직접 다시 찍었다.**

## 1. Task 1 RED — 직접 실측 (`uv run python --version` = 3.11.6)

```
$ uv run pytest tests/data/test_millie_popularity.py tests/data/test_millie_export.py --no-header
...
___________________ test_popularity_columns_and_all_segment ____________________
pop = Empty DataFrame
Columns: [book_id, segment, score, rank]
Index: []

    def test_popularity_columns_and_all_segment(pop):
        assert list(pop.columns) == EXPECTED_COLUMNS
>       assert "all" in set(pop["segment"])
E       AssertionError: assert 'all' in set()
...
    def test_main_writes_parquet(tmp_path, pop_mod, books, monkeypatch):
...
>       assert len(written[written["segment"] == "all"]) == N_FIXTURE_BOOKS
E       assert 0 == 12
E        +  where 0 = len(Empty DataFrame\nColumns: [book_id, segment, score, rank]\nIndex: [])
...
E           Failed: export 는 popularity_path 를 받아야 한다(DATA-07) — 현 시그니처
            (books_path: pathlib.Path, edges_path: pathlib.Path, out_dir: pathlib.Path) -> dict[str, int]
...
5 failed, 8 errors in 0.31s
```

- popularity 5건: 빈 프레임 스텁 → 전부 `AssertionError`.
- export 8건: fixture 의 `pytest.fail`(현 `export` 3인자) → 전부 `Failed:` (python-tdd.md 가 Red 로 인정하는 형태).
- **금지 오류 0건**: `grep -c "ImportError\|SyntaxError\|NameError\|ModuleNotFoundError"` → `0`.

## 2. Task 2 GREEN

```
$ uv run pytest tests/data/test_millie_popularity.py tests/data/test_millie_export.py --no-header
.............                                                            [100%]
13 passed in 0.98s
```
```
$ uv run ruff format <자기 4파일>   → 4 files left unchanged
$ uv run ruff check  <자기 4파일>   → All checks passed!
$ wc -l  scripts/build_millie_popularity.py   45   (≤150)
         scripts/export_millie_serving.py    102   (≤150)
```

### 구현 내용
- `build_millie_popularity.build(books)` — `rank = books["pop_rank"].astype("int64")` **복사만**(인기 순위 정본 1곳, 재계산 없음 — T-03-16 완화), `score = pd.to_numeric(shelf_count, errors="coerce").astype(float).fillna(0.0)`(Int64 nullable 대응), `segment = "all"`, `sort_values(["segment","rank"])`. Plan 07 이 세그먼트 행을 concat 할 자리에 주석 1줄.
- `export_millie_serving.BOOK_FIELDS` 21 → **28** 로 교체(순서는 아래 §3). `# fmt: skip` 으로 5개씩 묶어 유지.
- `popularity_payload(pop)` 신설 — `sort_values(["segment","rank"])` 후 `_clean` 적용. `_clean` 은 **바꾸지 않았다**(형제 Plan 03-05 가 복사해 쓴다).
- `export` 4인자로 확장, `popularity_kr.json` 을 세 번째 산출물로 `_write`(기존 `assert size < MAX_BYTES` 그대로 적용 — T-03-15).
- 모듈 docstring 을 3파일 산출물 + 형제 스크립트 안내로 갱신.

## 3. `BOOK_FIELDS` 28개 최종 목록 (이 순서 그대로)

```
book_id · title · authors · image_url · average_rating
ratings_count · original_publication_year · categories · subcategories · tags
publisher · subtitle · pub_date · book_format · formats
pop_rank · millie_label · review_count · shelf_count · completion_prob
category_avg_prob · expected_min · category_avg_min · resid_z · len_z
difficulty · difficulty_source · top_segment
```
제외(변경 없음): `millie_id rating_observed description curator_note seg_dist isbn13 pages_diag collected_at source` — T-03-14 완화. 이 28키는 **3벌**(`tests/conftest.py` fixture `millie_serving_sample` · `tests/data/test_millie_export.py` 의 `EXPECTED_BOOK_KEYS` · 스크립트 `BOOK_FIELDS`)이 서로 같아야 하고, `test_books_json_keys_match_serving_sample_fixture` 가 드리프트를 잡는다.

## 4. 새 시그니처와 CLI (Plan 06 `make millie` 가 호출할 형태)

```python
export(books_path: Path, edges_path: Path, popularity_path: Path, out_dir: Path) -> dict[str, int]
```
| 스크립트 | CLI 인자 | 기본값 |
|---|---|---|
| `scripts/build_millie_popularity.py` | `--books` / `--out` | `DIR_PROCESSED/books_kr.parquet` / `DIR_PROCESSED/popularity_kr.parquet` |
| `scripts/export_millie_serving.py` | `--books` / `--edges` / `--popularity` / `--out` | `DIR_PROCESSED/{books_kr,item_edges_kr,popularity_kr}.parquet` / `DIR_ARTIFACTS/serving` |

`popularity_kr` 행 스키마(D-15 고정): `{"book_id": 812, "segment": "all", "score": 9814.0, "rank": 1}`.

## 5. 검증 단언 전부

| 항목 | 기대 | 실측 |
|---|---|---|
| `grep -c 'def test_' test_millie_popularity.py` | 5 | 5 |
| `grep -c 'def test_' test_millie_export.py` | **8** | 8 |
| `grep -c '"top_segment",' export_millie_serving.py` | 1 | 1 |
| `grep -c '"description"\|"curator_note"\|"seg_dist"\|"millie_id"' export_millie_serving.py` | 0 | 0 |
| `grep -c 'popularity_kr.json' export_millie_serving.py` | ≥2 | 2 |
| `grep -c 'def popularity_payload' export_millie_serving.py` | 1 | 1 |
| `grep -c 'millie_rec.serving\|app\|data'` 두 스크립트 | 0 0 | 0 0 |
| `len(BOOK_FIELDS)` | 28 | 28 |
| `git status --short artifacts demo` | 내 변경 0 | 0 (`artifacts/serving/eval_table.json` 은 Phase 2 산출물, mtime 15:26 < 내 세션 20:20) |
| `git log --oneline \| head -1` | 불변 | `8e5172b chore: project scaffold …` |

**플랜 acceptance 의 export 테스트 수 `7` 은 집계 오류다 — 플랜 1-c 가 열거한 8개가 정본이고, `13 passed`(5+8)가 Task 2 acceptance 와도 일치한다.**

## 6. 판단 지점 (플랜에서 벗어난 곳)

1. **docstring·주석 줄바꿈 (E501).** 플랜이 verbatim 으로 지시한 docstring 4개와 주석 2개가 `line-length = 100`(pyproject `[tool.ruff]`)을 최대 144자까지 넘겨 `uv run ruff check` 가 9건 실패했다. **문구는 한 글자도 지우지 않고** 두 번째 줄로 내려 다중행 docstring·2줄 주석으로 만들었다(요약 줄만 100자 이내). ruff 클린이 완료 기준이라 이 조정은 불가피했다.
2. **`BOOK_FIELDS` 에 `# fmt: skip`.** 플랜이 "한 줄에 4~5개씩"을 요구했는데 ruff format 은 magic trailing comma 때문에 한 줄 1개로 펼친다. `# fmt: skip` 으로 5개씩 6줄 형태를 유지했다.
3. **실행 금지 준수.** 두 스크립트를 실 경로로 **실행하지 않았다**. `artifacts/serving/`·`data/processed/` 갱신은 Plan 06 `make millie` 몫.
4. **`_clean` 무변경.** 형제 Plan 03-05 가 복사해 쓰므로 손대지 않았다(충돌 회피).
5. **범위 준수.** `ruff`·`pytest` 는 자기 4파일/2테스트 파일에만 돌렸다. 전역 `ruff .`·전체 `pytest`·`make smoke` 는 Advisor 의 wave 종료 기준선.

## 7. 변경 파일 (커밋하지 않음)

```
M scripts/export_millie_serving.py      (+25 −25 — BOOK_FIELDS 28 · popularity_payload · export 4인자 · --popularity · docstring)
?? scripts/build_millie_popularity.py   (신규 45줄)
?? tests/data/test_millie_popularity.py (신규 5 테스트)
?? tests/data/test_millie_export.py     (신규 8 테스트)
?? .planning/phases/03-millie-catalog/03-04-SUMMARY.md
```
must_not_touch 경로 무변경 — `git diff` 에 보이는 `Makefile`·`pyproject.toml`·`src/**`·`tests/conftest.py`·`scripts/build_millie_catalog.py` 변경은 전부 내 세션 이전(Plan 01·02·Advisor)의 것이다.
