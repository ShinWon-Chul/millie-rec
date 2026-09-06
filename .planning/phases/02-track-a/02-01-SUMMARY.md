---
phase: 02-track-a
plan: 01
subsystem: data (Track A 데이터 준비 수직 슬라이스)
tags: [goodbooks-10k, holdout-split, onboarding-mask, labels, tdd]
requires: [contracts.py (freeze, 무변경), tests/conftest.py::interactions]
provides:
  - "millie_rec.data 공개 표면 25개 이름 (download_goodbooks · build_goodbooks · load_interactions · load_books · filter_min_interactions · split · Split · select_test_users · mask_onboarding · OnboardingStates · is_positive · relevant_sets + 상수 13개)"
  - "data/processed/{interactions,books}.parquet 빌드 경로 (실행은 Plan 05·06)"
affects:
  - "Plan 02 'retrieval' — PopularityRetriever.fit(train) 입력이 split().train"
  - "Plan 03 'evaluation' — harness 가 OnboardingStates·relevant_sets 를 소비"
  - "Plan 05 'app/cli' — from millie_rec.data import … 로만 접근"
tech-stack:
  added: []          # 의존성 추가 0 (pandas·numpy·pyarrow 기존)
  patterns:
    - "슬라이스 내부 import 1건만: onboarding.py → labels.is_positive (star 의존 준수)"
    - "난수는 np.random.default_rng(seed) 3곳 (split 1 · onboarding 2), seed 기본값 contracts.SEED"
    - "컬럼은 contracts.COL_* 상수만 (goodbooks.py 의 raw CSV 열 이름 리터럴만 예외)"
key-files:
  created:
    - src/millie_rec/data/goodbooks.py
    - src/millie_rec/data/load.py
    - src/millie_rec/data/split.py
    - src/millie_rec/data/onboarding.py
    - src/millie_rec/data/labels.py
    - tests/data/test_goodbooks.py
    - tests/data/test_load.py
    - tests/data/test_split.py
    - tests/data/test_onboarding.py
    - tests/data/test_labels.py
  modified:
    - src/millie_rec/data/__init__.py
decisions:
  - "빈 리스트 컬럼(categories·subcategories)은 [[] for _ in range(len(out))] 그대로 to_parquet 성공 — 플랜 2-a 주의사항의 대체안(빈 튜플·빈 문자열)은 불필요"
  - "goodbooks.py NOISE_TAGS 를 frozenset(\"\"\"…\"\"\".split()) 형태로 작성 — 원소 41개는 플랜과 동일, black 스타일 1원소/1줄 폭발(+45줄)을 피해 파일 116줄 유지"
metrics:
  duration: "~45분"
  tasks: 3
  files: 11
  completed: 2026-09-05
---

# Phase 2 Plan 01: Track A 데이터 준비 Summary

**한 줄:** Goodbooks-10k 멱등 다운로드·parquet 캐시 → 유저≥5·아이템≥5 필터 → 데이터가 스스로 정하는 holdout|temporal 분할 → 온보딩 5권 마스킹 두 상태(n=0 / n≥20) → `rating≥4` 라벨을, 20건의 손계산 테스트로 고정한 `data` 슬라이스.

## 커밋

**커밋하지 않는다 — 작업 트리에 남기고 SUMMARY 에 변경 파일 목록을 적는다** (결정 'D-18 커밋 없음'(.planning/phases/02-track-a/02-CONTEXT.md), 결정 'Phase 1 실행 방식'(../.assets/개발일지/2026-09-05_Day1_GSD_초기화와_계약_freeze.md 항목 D55)).
모든 태스크 커밋 해시 자리는 `(no commit — 사용자 승인 대기)`.

`git log --oneline | head -1` = `8e5172b` (플랜 시작 전과 동일, 커밋 0).

### 변경 파일 (`git status --short -- src/millie_rec/data tests/data`)

```
 M src/millie_rec/data/__init__.py
?? src/millie_rec/data/goodbooks.py
?? src/millie_rec/data/labels.py
?? src/millie_rec/data/load.py
?? src/millie_rec/data/onboarding.py
?? src/millie_rec/data/split.py
?? tests/data/test_goodbooks.py
?? tests/data/test_labels.py
?? tests/data/test_load.py
?? tests/data/test_onboarding.py
?? tests/data/test_split.py
```

`git diff --stat -- src/millie_rec/data tests/data` (추적 중인 파일은 `__init__.py` 하나):
```
 src/millie_rec/data/__init__.py | 56 ++++++++++++++++++++++++++++++++++++++-
 1 file changed, 55 insertions(+), 1 deletion(-)
```

`wc -l` (전부 ≤150):
```
 57 src/millie_rec/data/__init__.py
116 src/millie_rec/data/goodbooks.py
 25 src/millie_rec/data/labels.py
 42 src/millie_rec/data/load.py
 72 src/millie_rec/data/onboarding.py
 61 src/millie_rec/data/split.py
```

## Task 1 (RED) — 스텁 5 + 테스트 5(20건)

시그니처만 있고 값이 틀린 스텁을 먼저 두어 `ModuleNotFoundError` 가 아닌 **단정 실패**로 RED 를 만들었다.
테스트 건수: `test_labels.py` 2 · `test_split.py` 6 · `test_onboarding.py` 6 · `test_load.py` 2 · `test_goodbooks.py` 4 = **20**.

무엇이 왜 실패했나(AssertionError 발췌):

| 테스트 | 실패 단정 | 왜 |
|---|---|---|
| `test_is_positive_is_rating_ge_4_only` | `assert [False, False... False, False] == [False, False..., True, False]` | 스텁이 전부 False |
| `test_relevant_sets_keeps_only_positive_test_items_per_user` | `assert {} == {1: frozenset({1})}` | 스텁이 빈 dict |
| `test_holdout_when_ts_missing_records_split_mode_holdout` | `AssertionError: assert '' == 'holdout'` | 스텁이 split_mode 를 비워 둠 |
| `test_holdout_partitions_each_user_without_overlap` | `AssertionError: assert set() == {0, 1, 2, 3, 4, 5, ...}` | 스텁 test 가 비어 n≥2 유저가 test 에 없음 |
| `test_holdout_test_size_per_user_is_max1_floor_frac` | `AssertionError: assert 0 == 2` | 유저별 test 행 수 0 |
| `test_holdout_hand_case_10_rows_gives_2_test_rows` | `assert (10, 0) == (8, 2)` | 손계산 10행 → 8/2 |
| `test_temporal_split_no_future_leak` | `AssertionError: assert '' == 'temporal'` | ts 있는 fixture 인데 분기 없음 |
| `test_split_is_reproducible_and_rejects_partial_ts_and_bad_frac` | `Failed: DID NOT RAISE ValueError` | ts 부분 결측·`test_frac=1.5` 검증 없음 |
| `test_mask_onboarding_exposes_exactly_5_seeds_from_train_positives` | `assert 0 == 2` | 스텁이 빈 두 상태 |
| `test_mask_onboarding_nk_state_requires_k_history_and_excludes_seeds` | `assert 0 == 1` | n≥k 상태 없음 |
| `test_select_test_users_requires_5_train_positives_and_1_test_positive` | `assert ((), 0) == ((1,), 2)` | 적격 판정·제외 수 없음 |
| `test_user_state_has_no_negative_structure` | `assert 0 == 1` | 상태가 만들어지지 않음 |
| `test_filter_min_interactions_hand_case` | `assert 27 == 25` | 스텁이 필터하지 않음 |
| `test_build_goodbooks_writes_contract_columns_and_null_ts` | `AssertionError: assert ['user_id', 'book_id'] == ['user_id', '...nt', 'rating']` | 계약 5컬럼 미생성 |
| `test_build_goodbooks_maps_goodreads_id_and_drops_noise_tags` | `AssertionError: assert {'authors', '...on_year', ...} <= {'book_id'}` | books 계약 컬럼 미생성 |
| `test_build_goodbooks_dedupes_repeated_user_book_pairs` | `assert 0 == 4` | (1,1) 중복 제거 후 4행이어야 함 |
| `test_download_is_idempotent_when_files_exist` | `AssertionError: network must not be called` | 스텁이 무조건 `urlretrieve` 호출 |

금지 오류 0건: `grep -cE "ImportError|ModuleNotFoundError|SyntaxError|NameError|TypeError|KeyError|IndexError"` → **0**.
`uv run pytest tests/test_architecture.py --no-header` → `3 passed` (스텁 단계에서도 star 의존 준수).
테스트 실행 중 네트워크 0: `ls data/raw/goodbooks` 빈 결과.

## Task 2 (GREEN) — 구현

| 파일 | 요지 | 상수 |
|---|---|---|
| `goodbooks.py` (116줄) | `download_goodbooks`: `exists() and st_size > 0` 이면 건너뜀(멱등), 아니면 `.part` 로 받아 `replace`. `build_goodbooks`: `_interactions`(계약 5컬럼, `ts` 전부 None, `event="rating"`, **`drop_duplicates([COL_USER, COL_ITEM], keep="last")`**) + `_books`(`BOOK_COLS` 7 + `categories`·`subcategories` 빈 리스트 + `tags`) → parquet 2개. `_tags_per_book` 이 `count>0` → `NOISE_TAGS` 제외 → **`goodreads_book_id` → `book_id` 매핑** → count 내림차순 상위 `TOP_TAGS` 공백 join | `GOODBOOKS_URL_BASE`(HTTPS 고정) · `FILES`(4) · `RAW_SUBDIR="goodbooks"` · `EVENT_RATING="rating"` · `TOP_TAGS=20` · `NOISE_TAGS`(41개) |
| `load.py` (42줄) | `load_interactions`·`load_books` = `pd.read_parquet` 그대로. `filter_min_interactions` = 안정될 때까지 `value_counts` 2회 + 불리언 마스크(벡터화, 유저 루프 0) | `INTERACTIONS_FILE` · `BOOKS_FILE` · `MIN_USER_INTERACTIONS=5` · `MIN_ITEM_INTERACTIONS=5` |
| `split.py` (61줄) | `split()` 하나가 데이터에서 방식을 결정 — `ts` 전부 결측이면 `_holdout`(유저별 `max(1, floor(n·0.2))`, `default_rng(seed)` + `kind="stable"`), 있으면 `_temporal`(quantile cutoff, 동률은 train, `assert train.ts.max() < test.ts.min()`). ts 부분 결측·`test_frac` 범위 밖은 `ValueError` | `TEST_FRAC=0.2` · `SPLIT_HOLDOUT="holdout"` · `SPLIT_TEMPORAL="temporal"` |
| `onboarding.py` (72줄) | `select_test_users`: 적격 마스크(train 긍정 ≥5 ∧ test 긍정 ≥1)를 벡터로 만든 뒤 `rng.choice` 1회 → `(유저 튜플, 제외 수)`. `mask_onboarding`: 첫 줄 `train[train[COL_USER].isin(users)]` 선필터 후 유저 루프(평가 표본에 한정) → `n0`(seeds 만) · `n_k`(seeds 외 이력 ≥ `k_history` 인 유저만). 미선택 책은 어느 필드에도 부정 신호로 남지 않는다 | `K_HISTORY=20` · `N_TEST_USERS=2000` · `STATE_N0="n0"` · `STATE_NK="n20"` |
| `labels.py` (25줄) | `is_positive` = `df[COL_RATING] >= 4.0` (벡터화 bool Series). `relevant_sets` = test 긍정만 유저별 `frozenset`, 긍정 없는 유저는 키 없음 | `POSITIVE_MIN_RATING=4.0` |

**빈 리스트 컬럼 parquet 처리 결과:** 플랜 2-a 주의사항의 1안 — `out["categories"] = [[] for _ in range(len(out))]` 를 그대로 `to_parquet` — 이 **성공**했다(pyarrow `list<null>`). 대체안(`pd.Series([()]*n)`·빈 문자열)은 쓰지 않았고, Track B `books_kr` 과의 형태 차이 없음.

## Task 3 (REFACTOR) — 공개 표면 · ruff

- `src/millie_rec/data/__init__.py` 를 25개 이름의 `__all__`(알파벳 정렬)로 교체. `uv run python -c "import millie_rec.data as d; print(len(d.__all__))"` → **25**. 순환 import 없음(`goodbooks → load` 단방향).
- 상수까지 노출한 이유: Plan 05 `app/cli.py` 가 `--processed`/`--raw` 기본값과 D-08 json 메타(`test_frac`·`k_history`·`min_*`)를 리터럴 없이 만들어야 한다.
- `uv run ruff format src/millie_rec/data tests/data` → 14 files 정리, `uv run ruff check` → `All checks passed!`. 행동 변경 없음(포맷 후 재실행 통과).
- 전역 게이트(전체 `uv run pytest` · `ruff check .` · `make smoke`)는 **이 플랜에서 돌리지 않았다** — wave 1 형제 플랜(02-02 retrieval · 02-03 evaluation)의 RED 파일과 경합하므로 wave 종료 후 Advisor 가 1회 실행(02-06-PLAN.md `<wave_gate>`).

## TDD Gate Compliance

프로젝트 커밋 정책상 **커밋 게이트(`test(...)` → `feat(...)`)는 생략**한다(결정 'D-18 커밋 없음'(.planning/phases/02-track-a/02-CONTEXT.md)). 대체 증거는 아래 pytest 출력 3개.

**RED** (`uv run pytest tests/data/test_labels.py tests/data/test_split.py tests/data/test_onboarding.py tests/data/test_load.py tests/data/test_goodbooks.py --no-header`):
```
19 failed, 1 passed in 0.20s
```
AssertionError 발췌:
```
E       AssertionError: assert '' == 'holdout'
E       assert ((), 0) == ((1,), 2)
E       Failed: DID NOT RAISE ValueError
E       AssertionError: network must not be called
```

**GREEN** (같은 명령):
```
20 passed in 0.11s
```

**전체 자기 경로** (`uv run pytest tests/data tests/test_architecture.py --no-header`):
```
111 passed, 2 skipped in 1.09s
```
(Track A 20 + Track B 기존 88 + 아키텍처 3, skip 2 유지, failed 0)

## Deviations from Plan

### 1. [Rule 1 - Bug] RED 정직성을 위해 단정 3곳 보강
- **발견 시점:** Task 1
- **문제:** 플랜대로 쓰면 `test_holdout_partitions_each_user_without_overlap` 는 스텁(`Split(df, df.iloc[0:0], "")`)에서 **통과**하고, `test_user_state_has_no_negative_structure`·`test_mask_onboarding_is_deterministic` 는 빈 튜플 인덱싱으로 `IndexError`(= AssertionError 아님)를 냈다.
- **조치:** ① 분할 테스트에 "n≥2 유저는 전부 test 에 등장" 단정 추가 ② 두 온보딩 테스트 맨 앞에 `len(st.n0) == …` 길이 단정 추가. 플랜이 명시적으로 허용한 보강("예상외 통과가 있으면 단정을 보강한다").
- **파일:** `tests/data/test_split.py`, `tests/data/test_onboarding.py`
- **커밋:** (no commit — 사용자 승인 대기)

### 2. [Rule 3 - Blocking] 스텁의 빈 parquet 에 키 컬럼을 남김
- **문제:** 플랜의 "빈 DataFrame 2개"를 컬럼 없이 쓰면 `test_..._dedupes_...` 의 `duplicated([COL_USER, COL_ITEM])` 와 `set_index(COL_ITEM)` 이 `KeyError` 로 죽어 RED 가 아니게 된다.
- **조치:** 스텁 parquet 을 `pd.DataFrame({COL_USER: Series(int64), COL_ITEM: Series(int64)})`(interactions) / `{COL_ITEM: …}`(books) 로 써서 전부 AssertionError 로 실패시켰다. 스텁은 Task 2 에서 폐기됨.

### 3. [Rule 1 - Bug] `NOISE_TAGS` 표기 형태 변경(원소는 동일)
- **문제:** 플랜의 `frozenset({...,})` 는 magic trailing comma 때문에 ruff format 이 1원소/1줄로 펼쳐 `goodbooks.py` 가 약 160줄이 된다(파일 ≤150 위반).
- **조치:** `frozenset("""…""".split())` 로 표기. **원소 41개는 플랜과 문자 단위로 동일**. 파일 116줄.

### 4. [문서화만] `awk 'length > 100'` 수용 기준은 macOS 에서 사용 불가
- Task 2 수용 기준의 `awk 'length > 100' … | wc -l == 0` 은 macOS BSD awk 가 **바이트**를 세어 한글 docstring에서 거짓 양성을 낸다(이미 커밋된 `data/__init__.py` L1 도 108바이트로 걸린다). 실제 게이트인 `uv run ruff check --select E501` (문자 폭 기준)로 대체 검증했고 `All checks passed!`. **주의:** ruff 는 한글을 폭 2로 세므로 파이썬 `len()` 보다 엄격하다 — 이 때문에 `labels.py`·`test_labels.py` 의 근거 줄을 두 줄로 나눴다.

### 5. [플랜 지시 그대로 — 미해결로 남김] RED 에서 1건 통과
- `test_load_functions_read_parquet_as_is` 는 플랜이 스텁에서도 진짜 `pd.read_parquet` 을 쓰라고 지시했기 때문에 RED 단계에서 통과했다(19 failed / 1 passed). 한 줄짜리 통과 함수의 계약 테스트라 더 강화할 단정이 없다. GREEN 에서도 같은 구현.

### 사용자 지시와의 긴장
없음. 지시 4개(다른 기능 무영향 · 모듈성 · 클린코드 규칙 · 최소 변경)와 플랜이 충돌한 지점 없음. 요청하지 않은 리팩토링·주석 추가 0, `files_modified` 밖 파일 변경 0.

## Known Stubs

없음. Task 1 의 스텁 5파일은 Task 2 에서 전부 실구현으로 교체됐다(`grep -c "스텁" src/millie_rec/data/*.py` → 0).

## 미구현으로 남긴 분기 (의도적)

`../.claude/rules/data.md` 의 "`mask_onboarding(n=5)`: 테스트 유저의 첫 n권(`ts` 있으면 시간순, 없으면 seed 고정 무작위)" 중 **`ts` 있으면 시간순 첫 n권 분기는 미구현**이다 — 결정 'D-03 seeds = train 긍정 중 seed 고정 무작위 5권'(.planning/phases/02-track-a/02-CONTEXT.md) 잠금. UCSD Poetry temporal 배경 레인 착수 시 재검토한다.

## Threat Flags

없음. 플랜 `<threat_model>` 의 mitigate 6건은 코드에 존재한다 — T-02-01(HTTPS 리터럴 + 고정 `FILES`, `.part` → `replace`, `subprocess`·`shell=True` 0), T-02-02(`exists() and st_size > 0` 멱등, 재시도 루프 없음), T-02-04(`mask_onboarding` 은 test 인자를 받지 않는다 · `select_test_users` 는 test 를 적격 판정에만 사용 · 테스트가 `101 not in seen` 단정), T-02-05(`split_mode` 를 사람이 고를 수 없고 temporal 은 `assert train.ts.max() < test.ts.min()`). 새 보안 표면 없음.

## 다음 플랜을 위한 메모

- `split()` 은 `Split(train, test, split_mode)` frozen dataclass 를 돌려준다 — D-08 실행 메타의 `split_mode` 는 여기서 읽는다(`contracts.EvalResult` 변경 없음).
- `mask_onboarding` 의 `n_k` 는 **n=0 과 모집단이 다르다**(seeds 외 이력 ≥ `K_HISTORY=20` 인 유저만). `latest_states.csv` 의 `n_users` 를 상태별로 따로 기록해야 한다(D-07).
- Goodbooks `ratings.csv` 의 (user, book) 중복은 `build_goodbooks` 단계에서 이미 제거된다 — 하네스의 누수 검사는 그 위에서 돈다.

## Self-Check: PASSED

- 생성 파일 11개 전부 존재 확인(`ls` — src 5 + tests 5 + `__init__.py` 수정 1)
- 커밋 해시 검증 항목 없음(커밋 0 — `git log --oneline | head -1` = `8e5172b`, 플랜 시작 전과 동일)
- `must_not_touch` 전부 무변경: `git status --short -- scripts data/id_map.csv tests/data/test_millie_*.py Makefile pyproject.toml` → 빈 결과
- `src/millie_rec/contracts.py` 의 ` M` 표시는 **이 플랜 시작 전부터 있던 워킹트리 변경**(1 insertion)이며 이 실행에서 건드리지 않았다
