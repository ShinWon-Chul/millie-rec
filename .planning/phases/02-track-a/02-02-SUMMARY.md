---
phase: 02-track-a
plan: 02
subsystem: retrieval
tags: [popularity-baseline, tfidf, sklearn, scipy-sparse, item-vectors, candidate-generator, tdd]

# Dependency graph
requires:
  - phase: 01-local-serving-skeleton
    provides: "contracts.py freeze(Candidate·CandidateGenerator·ItemVectors·UserState.seen·DIR_ARTIFACTS) · serving/fallback.py 의 Protocol 구현 클래스 형태와 seen 제외 패턴(형태만 복사, import 아님)"
provides:
  - "PopularityRetriever — contracts.CandidateGenerator 구현. fit(train) 카운트(평점 무관) · retrieve(user, k) 가 user.seen 제외 · save/load 작은 json 아티팩트"
  - "POP_ARTIFACT (artifacts/popularity.json) · TOP_N(1000) · ARTIFACT_NAME · SOURCE_POPULARITY 상수"
  - "ContentVectors — contracts.ItemVectors 구현. Goodbooks tags 단어 TF-IDF → L2 정규화 dense ndarray(미지 id 는 0 벡터)"
  - "retrieval 슬라이스 공개 표면 __all__ 4개 이름(POP_ARTIFACT · TOP_N · ContentVectors · PopularityRetriever)"
  - "tests/retrieval/ 11건(계약·정확성·안전성 3종)"
affects:
  - "Phase 2 Plan 03 '평가 하네스'(.planning/phases/02-track-a/02-03-PLAN.md) — ILD@10 의 벡터 출처가 ContentVectors"
  - "Phase 2 Plan 05 'app 조립'(.planning/phases/02-track-a/) — app/pipeline.py 가 POP_ARTIFACT 존재 검사 + PopularityRetriever.load 로 level 0 주입"
  - "Phase 4 '추천 파이프라인과 모델 freeze'(.planning/ROADMAP.md) — content.py 에 retrieve() 증분(현재 42줄, ≤150줄 예산 여유 108줄)"

# Tech tracking
tech-stack:
  added: []  # 의존성 추가 0 — sklearn·numpy·pandas 는 pyproject 에 이미 있음
  patterns:
    - "Protocol 구현 클래스: 상속 없음(structural typing) · name 클래스 속성 · __init__ 은 주입만"
    - "슬라이스 간 값 중복 > 결합: SOURCE_POPULARITY 를 retrieval 에 재정의(serving import 금지)"
    - "무거운 서드파티(sklearn) 는 메서드 안에서 import — 공개 표면 import 가 서버 기동을 무겁게 하지 않음"
    - "아티팩트는 json.loads + int()/float() 강제 변환(pickle 금지, T-02-07)"

key-files:
  created:
    - src/millie_rec/retrieval/popularity.py
    - src/millie_rec/retrieval/content.py
    - tests/retrieval/test_popularity.py
    - tests/retrieval/test_content.py
  modified:
    - src/millie_rec/retrieval/__init__.py

key-decisions:
  - "SOURCE_POPULARITY='popularity' 를 retrieval 에 중복 정의 — star 의존상 serving/fallback.py 를 import 할 수 없다(architecture.md '5일 프로젝트에서는 중복 < 결합')"
  - "TfidfVectorizer 는 ContentVectors.__init__ 안에서 import — millie_rec.retrieval 공개 표면 import 만으로 sklearn 이 로드되지 않음(실측 '4 False')"
  - "빈 어휘(전 책 tags 빈 문자열)는 처리하지 않는다 — TfidfVectorizer 가 ValueError('empty vocabulary') 를 던지지만 Goodbooks 에서는 발생하지 않음(가정을 명시하고 방어 코드 미작성)"
  - "E501 판정은 ruff(문자 기준) 로 한다 — 플랜의 awk 'length > 100' 은 바이트를 세어 한글 주석에 오탐(기존 repo 파일도 동일하게 걸린다)"

patterns-established:
  - "retrieval 슬라이스 공개 표면: __init__.py 가 알파벳 정렬 __all__ 로 이름만 노출(serving/__init__.py 형태 그대로)"
  - "테스트 3종 구분 주석(# ── 계약 ── / # ── 정확성 ── / # ── 안전성 ──) 을 tests/retrieval 에도 적용"
  - "아티팩트 저장 테스트는 tmp_path 만 — 실제 artifacts/ 를 오염시키지 않는다"

requirements-completed: [EVAL-04]

# Metrics
duration: 18min
completed: 2026-09-05
---

# Phase 2 Plan 02: retrieval 슬라이스(pop 기준선 + 콘텐츠 벡터) Summary

**Goodbooks train 행 카운트로 순위를 만들고 `user.seen` 을 제외하는 `PopularityRetriever`(작은 json 아티팩트 save/load)와, tags 단어 TF-IDF 로 L2 정규화 dense 벡터를 내는 `ContentVectors`(ILD@10 의 벡터 출처)를 TDD 한 사이클로 만들었다 — 11건 GREEN, 커밋 0.**

## Performance

- **Duration:** 약 18분
- **Tasks:** 3/3 (RED → GREEN → REFACTOR)
- **Files modified:** 5 (신규 4 · 수정 1)
- **테스트:** `tests/retrieval` 11 passed · `tests/test_architecture.py` 3 passed (합 14 passed, failed 0)

## Accomplishments

- **EVAL-04 의 retriever 몫 고정:** "학습에 본 아이템은 추천에서 제외" 가 `retrieve` 안의 `if b in user.seen: continue` 와 손계산 테스트 2건(`explicit_seeds=(1,)` → `[2, 3]`, `history=(1,2,3)` → `[]`)으로 코드에 박혔다. `fit` 인자가 1개(`inspect.signature` 단정)라 retriever 가 test 프레임을 알 방법이 구조적으로 없다.
- **결정 'D-05 학습·seen = train 전체 상호작용(평점 무관)'(.planning/phases/02-track-a/02-CONTEXT.md)** 이 테스트로 증명: 평점 `[1,2,3,4,5,1]` 이 섞인 train 에서 카운트가 3/2/1 그대로 나온다.
- **결정 'D-10 아티팩트 있으면 로드, 없으면 level 3'(같은 파일)** 의 입력 형태 확정: `artifacts/popularity.json` = `{"name": "pop", "items": [[book_id, count], …]}`, 상위 `TOP_N=1000`. `save → load → retrieve` 라운드트립이 원본과 동일함을 단정.
- **결정 'D-14 ItemVectors 는 벡터 부분만'(같은 파일)** 준수: `content.py` 42줄, `retrieve()` 없음 — Phase 4 '추천 파이프라인과 모델 freeze'(.planning/ROADMAP.md) 가 같은 파일에 증분할 예산 108줄이 남았다.
- **서버 기동 부담 0 실측:** `import millie_rec.retrieval` 직후 `'sklearn' in sys.modules` 가 `False`(출력 `4 False`).

## Task Commits

**커밋하지 않는다 — 작업 트리에 남기고 SUMMARY 에 변경 파일 목록을 적는다** (결정 'D-18 커밋 없음'(.planning/phases/02-track-a/02-CONTEXT.md), 결정 'Phase 1 실행 방식'(../.assets/개발일지/2026-09-05_Day1_GSD_초기화와_계약_freeze.md 항목 D55)).

| Task | 게이트 | 커밋 | 결과 |
|---|---|---|---|
| Task 1 — 스텁 + 테스트 11건 | RED | (no commit — 사용자 승인 대기) | 11 failed, 전부 AssertionError |
| Task 2 — PopularityRetriever·ContentVectors 구현 | GREEN | (no commit — 사용자 승인 대기) | 11 passed |
| Task 3 — `__init__.py` 공개 표면 + ruff | REFACTOR | (no commit — 사용자 승인 대기) | 14 passed, ruff 클린 |

`git log --oneline | head -1` = `8e5172b`(실행 전후 불변).

## Files Created/Modified

`git status --short -- src/millie_rec/retrieval tests/retrieval`:

```
 M src/millie_rec/retrieval/__init__.py
?? src/millie_rec/retrieval/content.py
?? src/millie_rec/retrieval/popularity.py
?? tests/retrieval/
```

| 파일 | 줄 수 | 역할 |
|---|---|---|
| `src/millie_rec/retrieval/popularity.py` (신규) | 58 (≤150) | `PopularityRetriever` — `fit`/`retrieve`/`save`/`load` + `SOURCE_POPULARITY`·`ARTIFACT_NAME`·`POP_ARTIFACT`·`TOP_N` |
| `src/millie_rec/retrieval/content.py` (신규) | 42 (≤80) | `ContentVectors` — tags 단어 TF-IDF, `vectors(book_ids)` → L2 정규화 dense ndarray |
| `src/millie_rec/retrieval/__init__.py` (수정) | 11 | 공개 표면 `__all__` 4개 (기존 `__all__: list[str] = []` 교체) |
| `tests/retrieval/test_popularity.py` (신규) | 79 | 7건 — 계약 2 · 정확성 3 · 안전성 2 |
| `tests/retrieval/test_content.py` (신규) | 52 | 4건 — 계약 1 · 정확성 2 · 안전성 1 |

`artifacts/popularity.json` 은 **생성되지 않았다**(저장 테스트는 `tmp_path` 만 사용) — `ls artifacts/popularity.json` → 없음.

## TDD Gate Compliance

**커밋 게이트는 이 프로젝트에서 생략한다** — 근거는 결정 'D-18 커밋 없음'(.planning/phases/02-track-a/02-CONTEXT.md)이고, `test(...)`/`feat(...)` 커밋 대신 **아래 pytest 출력 3개가 RED/GREEN/REFACTOR 게이트의 증거**다. 실행 인터프리터는 `uv run python --version` → **Python 3.11.6**(맨 `pytest` 의 3.9.18 아님, `../.claude/rules/python-tdd.md`).

### RED — `uv run pytest tests/retrieval --no-header`

요약 줄:
```
11 failed in 0.08s
```
- `AssertionError` 등장 12회 · `ImportError|ModuleNotFoundError|SyntaxError|NameError` **0회**(스텁을 먼저 만들어 collection error 가 아닌 단정 실패로 RED 를 냈다).

AssertionError 발췌:
```
E       assert (3, 0) == (3, 5)          # test_vectors_shape_and_type — 스텁은 dim 0
E       assert [] == [1, 2]              # test_retrieve_returns_candidates_sorted_by_count_desc
E       assert [] == [2, 3]              # test_retrieve_excludes_user_seen
E       assert 0 == 20                   # test_retrieve_on_fixture_... (interactions fixture)
```
```
>       assert [c.book_id for c in r.retrieve(UserState(None), k=10)] == [1, 2, 3]
E       assert [] == [1, 2, 3]
E         Right contains 3 more items, first extra item: 1
tests/retrieval/test_popularity.py:65: AssertionError
```
```
>       assert payload["name"] == "pop"
E       AssertionError: assert '' == 'pop'
E         - pop
tests/retrieval/test_popularity.py:73: AssertionError
```

### GREEN — `uv run pytest tests/retrieval --no-header`

```
11 passed in 0.77s
```

구현 요지:
- `PopularityRetriever.fit` — `train[COL_ITEM].value_counts()` (평점 컬럼을 읽지 않는다) → `sort_values(["n", COL_ITEM], ascending=[False, True], kind="stable")` 로 동점 시 book_id 오름차순 결정론.
- `PopularityRetriever.retrieve` — 상위부터 순회하며 `user.seen` 을 건너뛰고 `len(out) == k` 에서 중단 → 비용 O(k + |seen|) (위협 T-02-08 완화, 플랜 `<threat_model>`).
- `PopularityRetriever.save/load` — `json.dumps(..., ensure_ascii=False)` / `json.loads` 만(pickle 없음), 항목을 `int()`·`float()` 로 강제 변환 → 형식이 다르면 호출자가 잡을 수 있는 `ValueError`/`KeyError` (위협 T-02-07 완화).
- `ContentVectors` — `TfidfVectorizer(analyzer="word", token_pattern=r"\S+")` (기본 `norm="l2"`), `_index` 로 book_id→행 매핑, 미지 id 는 `np.zeros` 행 그대로 → 순서 보존·0 벡터.
- **상수 값(문자 단위 일치 확인):** `SOURCE_POPULARITY = "popularity"` · `ARTIFACT_NAME = "popularity.json"` · `POP_ARTIFACT = DIR_ARTIFACTS / ARTIFACT_NAME` · `TOP_N = 1000` · `name = "pop"` · `TAGS_COL = "tags"` · `TOKEN_PATTERN = r"\S+"`.
- **sklearn 지연 import 근거:** `ContentVectors.__init__` 안에서 import 한다. 서버(`app/server.py`)가 Plan 05 에서 `from millie_rec.retrieval import POP_ARTIFACT, PopularityRetriever` 를 하게 되는데, 모듈 최상위 import 였다면 그 한 줄이 sklearn 전체를 로드해 기동 시간을 늘린다. 실측으로 확인: `4 False`.

### REFACTOR — `uv run pytest tests/retrieval tests/test_architecture.py --no-header`

```
14 passed in 0.79s
```
- `uv run ruff format --check src/millie_rec/retrieval tests/retrieval` → `5 files already formatted`
- `uv run ruff check src/millie_rec/retrieval tests/retrieval` → `All checks passed!`
- `uv run python -c "import millie_rec.retrieval as r; import sys; print(len(r.__all__), 'sklearn' in sys.modules)"` → `4 False`
- `wc -l` → `popularity.py 58` · `content.py 42` · `__init__.py 11` (전부 예산 안)
- star 의존: `grep -rn "millie_rec\.\(data\|evaluation\|serving\|app\)" src/millie_rec/retrieval/` → 출력 없음

## Decisions Made

1. **`SOURCE_POPULARITY` 중복 정의** — `tests/test_architecture.py` L39-40 이 `retrieval → serving` import 를 막으므로 `serving/fallback.py` L10 의 상수를 가져올 수 없다. 같은 값 `"popularity"` 를 `popularity.py` 상단에 재정의했다(`../.claude/rules/architecture.md` "5일 프로젝트에서는 중복 < 결합"). 값이 갈라지면 `contracts.Candidate.source` 허용값 주석이 판정 기준이다.
2. **빈 어휘 가정(방어 코드 없음)** — 입력 `books` 의 **모든** 행 `tags` 가 빈 문자열/NaN 이면 `TfidfVectorizer.fit_transform` 이 `ValueError("empty vocabulary; perhaps the documents only contain stop words")` 를 던진다. Goodbooks-10k 는 책마다 태그가 붙어 있어 발생하지 않으므로 try/except 를 넣지 않았다(`../.claude/rules/simplicity.md` "예외 계층 만들지 않음"). 한 책만 비어 있는 경우는 정상 동작하며 그 행이 0 벡터가 됨을 테스트 `test_unknown_id_and_empty_tags_give_zero_rows` 가 단정한다.
3. **동점 정렬 규칙** — 카운트가 같으면 `book_id` 오름차순(`kind="stable"`). 명세에 없었지만 같은 입력 → 같은 `results/latest.csv` 를 위해 결정론이 필요하다(`../.claude/rules/python.md` "같은 입력 → 같은 결과여야 PDF 숫자가 재현된다").

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `test_vectors_preserve_input_order` 가 스텁에서 통과해 RED 가 되지 않음**
- **Found during:** Task 1 (RED)
- **Issue:** 플랜 behavior 가 지정한 단정은 `np.array_equal(cv.vectors([20, 10]), cv.vectors([10, 20])[::-1])` 하나뿐인데, 스텁이 `np.zeros((n, 0))` 을 반환하면 양쪽 다 `(2, 0)` 이라 `array_equal` 이 **True** 가 된다. 11건 중 1건이 RED 없이 통과하면 그 테스트는 아무것도 증명하지 못한다(`../.claude/rules/python-tdd.md` "Red 는 AssertionError 로 확인").
- **Fix:** 같은 테스트에 `assert cv.vectors([20, 10]).shape == (2, DIM)` 한 줄을 앞에 추가. 순서 보존 단정은 그대로 두었다.
- **Files modified:** `tests/retrieval/test_content.py`
- **Verification:** RED 출력에 `E assert (2, 0) == (2, 5)` 등장 → 11건 전부 AssertionError.
- **Committed in:** (no commit — 사용자 승인 대기)

**2. [Rule 3 - Blocking] 테스트 파일 머리 docstring E501(112 > 100)**
- **Found during:** Task 3 (REFACTOR, `uv run ruff check`)
- **Issue:** 플랜이 문자 그대로 지정한 `tests/retrieval/test_popularity.py` 머리 docstring 이 112자로 `line-length = 100`(`pyproject.toml`) 위반.
- **Fix:** 플랜 Task 2-c 가 허용한 대로("docstring·주석·문자열은 의미 변경 없이 100자 이내로 줄바꿈해도 된다") 의미 변경 없이 두 줄로 나눔.
- **Files modified:** `tests/retrieval/test_popularity.py`
- **Verification:** `uv run ruff check src/millie_rec/retrieval tests/retrieval` → `All checks passed!`
- **Committed in:** (no commit — 사용자 승인 대기)

### 판정 기준을 바꾼 항목 (fix 아님 — 측정 도구 교체)

**3. Task 2 acceptance `awk 'length > 100' … | wc -l == 0` 는 달성 불가(오탐) — ruff 로 대체 판정**
- **Found during:** Task 2 준비 (사전 확인)
- **Issue:** macOS `awk` 의 `length` 는 **바이트**를 센다(실측: `printf '가나다' | awk '{print length}'` → `9`). 한글 주석 1줄이 곧바로 100바이트를 넘어, `uv run ruff check .` 를 통과하는 **기존 repo 파일들**(`serving/api.py`·`db.py`·`fallback.py`·`__init__.py` 등)도 이 명령에 걸린다. 즉 이 기준을 만족시키려면 프로젝트 컨벤션인 한글 주석·docstring 을 버려야 한다.
- **판정:** 기준의 의도는 "ruff E501 위반 0" 이므로 **문자 기준**으로 재측정했다.
  - `uv run ruff check src/millie_rec/retrieval tests/retrieval` → `All checks passed!` (E501 0건)
  - 문자 길이 직접 확인 → `char>100: 0 []`
  - 참고로 플랜의 바이트 기준 명령은 `9` 를 출력한다(전부 한글 주석 줄, 기존 repo 파일과 동일한 성격).
- **Files modified:** 없음
- **Impact:** 없음 — 실제 스타일 게이트(ruff)는 클린.

**4. Task 3 acceptance `git diff --stat -- src/millie_rec/contracts.py src/millie_rec/serving scripts` 가 비어 있지 않음 (이번 실행과 무관)**
- **Issue:** 해당 명령이 `src/millie_rec/contracts.py`(+1)·`src/millie_rec/serving/__init__.py`(+13)을 출력한다.
- **판정:** **이번 실행의 변경이 아니다.** 두 파일의 mtime 은 `09-05 11:12`(Phase 1 '로컬 서빙 스켈레톤' 작업 시각)이고 이 플랜의 쓰기는 `15:01` 이후다. diff 내용도 Phase 1 산출물(`MODEL_VERSION_FALLBACK` 상수 추가, serving 공개 표면 확장)이다. 결정 'D-18 커밋 없음'(02-CONTEXT.md) 때문에 Phase 1 산출물이 커밋되지 않은 채 작업 트리에 남아 있어, "기준선 대비 diff 없음" 이라는 이 기준은 커밋이 있는 프로젝트에서만 성립한다.
- **확인:** 이번 실행이 건드린 파일은 `git status --short -- src/millie_rec/retrieval tests/retrieval` 의 5개뿐이다.
- **Files modified:** 없음

---

**Total deviations:** 2 auto-fixed (Rule 3 blocking ×2) + 2 판정 기준 재해석(코드 변경 없음)
**Impact on plan:** 두 auto-fix 는 TDD 게이트의 유효성(진짜 RED)과 프로젝트 lint 게이트 통과를 위해 필요했다. 스코프 확장 없음 — `files_modified` 5개 밖의 파일을 만들거나 고치지 않았고, 의존성 추가 0, `contracts.py`·`tests/test_architecture.py`·`serving/`·`scripts/` 무변경.

## Issues Encountered

- `uv run ruff format` 이 `tests/retrieval/test_popularity.py` 의 `unseen_test` DataFrame 리터럴을 한 줄로 합쳤다(1 file reformatted). 행동 변경 없음, 이후 `--check` 클린.
- 그 외 없음. 형제 플랜(02-01 `data`, 02-03 `evaluation`)과의 파일 충돌 없음 — 전역 게이트(`uv run pytest --no-header` 전체 · `ruff check .` · `make smoke`)는 실행하지 않았다(wave 1 종료 후 Advisor 1회, 02-06-PLAN.md `<wave_gate>`).

## 사용자 지시 대비 자체 점검

| 지시 | 결과 |
|---|---|
| 다른 기능에 부작용 0 | `files_modified` 5개만 변경. 서버·계약·scripts 무변경. 기존 테스트 수정 0 |
| 모듈성 | 파일 하나 = 관심사 하나(`popularity.py` 인기 후보 / `content.py` 벡터). `src/` 최대 58줄. 공개 이름은 `__init__.py` `__all__` 4개만 |
| 클린코드 규칙 | 클래스는 Protocol 만족용 2개뿐(상속 없음) · 상수는 모듈 상단 대문자 · docstring 1줄 요약 · 예외 계층 0 · 컬럼은 `contracts.COL_ITEM` |
| 최소 변경 | 요청하지 않은 리팩토링·주석 추가 없음. Refactor 는 이번 브리프가 만든 5개 파일 안에서만 |

**플랜과 지시의 긴장:** 없음. 위 deviation 3·4 는 플랜의 *검증 명령*이 프로젝트 실태(한글 주석 · 커밋 없는 작업 트리)와 어긋난 경우이고, 플랜의 *구현 지시*(코드 골격·상수·시그니처)는 문자 단위로 그대로 따랐다.

## User Setup Required

None — 외부 서비스·네트워크·계정 설정 없음. 테스트는 다운로드하지 않는다(`tests/conftest.py` 합성 fixture + 인라인 소형 DataFrame).

## Next Phase Readiness

**준비된 것**
- Plan 03 '평가 하네스'는 `ContentVectors` 를 `contracts.ItemVectors` 로 주입받아 ILD@10 을 계산할 수 있다(하네스 테스트 자체는 conftest `item_vectors` fixture 로 독립).
- Plan 05 'app 조립'은 `from millie_rec.retrieval import POP_ARTIFACT, PopularityRetriever` 로 level 0 배선을 만들 수 있다. `POP_ARTIFACT` 존재 검사 → `PopularityRetriever.load(POP_ARTIFACT)` → `Candidate → ScoredItem` glue(app 몫).
- `cli eval` 이 `PopularityRetriever(...).fit(train).save()` 를 호출하면 `artifacts/popularity.json` 이 생긴다(아직 없음 — 의도, `.gitignore` 가 `artifacts/*` 무시).

**남은 주의점**
- 서버에 올라가는 Goodbooks `book_id` 는 밀리 카탈로그 id 와 다른 체계다 — Phase 3 '밀리 카탈로그 빌드'(.planning/ROADMAP.md) 에서 교체될 임시 배선(02-CONTEXT.md Deferred).
- 전역 게이트(`uv run pytest --no-header` 기준선 104 passed / 2 skipped → +11 기대 · `ruff check .` · `make smoke` level 3)는 **아직 실행하지 않았다.** wave 1 세 플랜이 끝난 뒤 Advisor 1회.

## Self-Check: PASSED

- 파일 존재: `src/millie_rec/retrieval/popularity.py` FOUND · `src/millie_rec/retrieval/content.py` FOUND · `src/millie_rec/retrieval/__init__.py` FOUND · `tests/retrieval/test_popularity.py` FOUND · `tests/retrieval/test_content.py` FOUND
- 테스트 수: `grep -c "def test_"` → test_popularity.py **7**, test_content.py **4** (합 11, 플랜 기대치 일치)
- 커밋: 없음(의도) — `git log --oneline | head -1` = `8e5172b`, 실행 전과 동일. SUMMARY 의 커밋 칸은 `(no commit — 사용자 승인 대기)`
- 게이트: `uv run pytest tests/retrieval tests/test_architecture.py --no-header` → **14 passed** · ruff format/check 클린 · 각 `src/` 파일 ≤150줄
- 미생성 확인: `artifacts/popularity.json` 없음

---
*Phase: 02-track-a · Plan 02 (retrieval 슬라이스)*
*Completed: 2026-09-05*
