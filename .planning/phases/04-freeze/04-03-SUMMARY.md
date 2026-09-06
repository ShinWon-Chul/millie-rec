---
phase: 04-freeze
plan: 03
subsystem: reranking
tags: [mmr, diversity, ild, difficulty-guard, resid_z, numpy, tdd]

# Dependency graph
requires:
  - phase: 02-track-a
    provides: "contracts.Reranker·ItemVectors·BookStatsSource Protocol, evaluation/metrics.py::ild_at_k 의 0-벡터 안전 cosine 규약"
  - phase: 03-millie-catalog
    provides: "CatalogKR.stats() 의 resid_z·source(millie_index|category_prior) — 가드 모집단 판정 입력(주입은 Plan 04-04)"
provides:
  - "reranking/mmr.py MMRReranker — 상위 MMR_POOL(50) 풀, λ=LAMBDA_MMR(0.7), 거리 = 1 − cosine(ItemVectors), 그리디 k개 재배열(position 0..k−1)"
  - "reranking/guard.py DifficultyGuard — len(user.history) < 3 신규 사용자에게 상단 N(=K_RANK 10) 안의 source=millie_index ∧ resid_z < −1.0 책을 N 밖으로 내리고 다음 비위반 책을 승격(집합·개수 보존)"
  - "reranking/__init__.py 공개 표면 7개 — app/pipeline.py 가 hybrid_div 조립에 쓰는 유일한 경로"
  - "tests/reranking/ 16건(계약·정확성 손계산·안전성) — MMR k=2 ILD 0.0 → 1.0 상승 소형 증거(REC-05), 가드 12권 재배열 손계산(REC-06)"
affects: [04-04 app/pipeline 조립, 04-05 D-07 게이트·λ 튜닝, 05 serving state.py n_completed 교체, PDF P3 ★난이도 박스]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "star 의존 유지 — reranking 은 contracts Protocol(ItemVectors·BookStatsSource)만 알고 구현체를 import 하지 않는다"
    - "None 주입 = 패스스루 분기(serving/fallback.py 관례) — Track A(BookStatsSource 없음)에서 가드가 무해하게 통과"
    - "0-벡터 안전 cosine 4줄을 evaluation/metrics.ild_at_k 에서 복사(슬라이스 간 import 금지 → 중복 < 결합)"
    - "가짜 어댑터는 상속 없는 테스트 내부 클래스 + 호출 카운터(tests/evaluation/test_harness.py::_OneHot 관례)"

key-files:
  created:
    - src/millie_rec/reranking/mmr.py
    - src/millie_rec/reranking/guard.py
    - tests/reranking/test_mmr.py
    - tests/reranking/test_guard.py
  modified:
    - src/millie_rec/reranking/__init__.py

key-decisions:
  - "MMR 관련성은 풀 안 min-max(분산 0 → 전부 1.0), 동률은 np.argmax 첫 인덱스 = 원 순위 → 같은 입력 같은 결과"
  - "가드 위반 판정은 items 전체에 stats() 1회 — 상단 N 안만 보면 승격 후보(예: 11번 책)의 위반 여부를 모른다"
  - "결측(resid_z None · source=category_prior) 은 가드 모집단 제외 — 움직이지 않는다"
  - "docstring 3줄(guard.py 는 D-08 대리값 문장 포함) — ruff 의 CJK 폭 2 계산 때문에 플랜 verbatim 문장을 줄바꿈으로 나눴다"

patterns-established:
  - "Reranker 는 재배열만 한다 — 입력 book_id 집합의 부분집합만 반환, 새 책·seen 추가 없음(harness 의 ValueError 안전망과 정합)"
  - "freeze 상수는 모듈 상단 대문자 + 근거 주석(D-xx) — 개발일지·PDF 각주가 이 이름을 인용한다"

requirements-completed: [REC-05, REC-06]

# Metrics
duration: 약 25분
completed: 2026-09-06
---

# Phase 4 Plan 03: 재순위화(MMR 다양성 + 신규 사용자 난이도 가드) Summary

**`hybrid_div` 의 다양성·난이도 두 단계가 TDD 한 사이클로 존재한다 — MMR 은 손계산 4벡터에서 k=2 ILD 를 0.0 → 1.0 으로 올리고(REC-05), 난이도 가드는 신규 사용자(대리값 `len(user.history)` < 3)에게 `millie_index ∧ resid_z < −1.0` 책을 상단 10 밖으로 내리면서 후보 12권을 하나도 잃지 않는다(REC-06).**

## Performance

- **Duration:** 약 25분
- **Tasks:** 3/3 (RED → GREEN → REFACTOR)
- **Files created:** 4 · **modified:** 1
- **커밋:** 0 — **커밋하지 않는다. 작업 트리에 남기고 이 SUMMARY 에 변경 파일 목록을 적는다**(플랜 frontmatter `no_commit: true`, 사용자 지시 2026-09-05)

## 변경 파일 목록 (작업 트리)

`git status --short -- src/millie_rec/reranking tests/reranking`:

```
 M src/millie_rec/reranking/__init__.py
?? src/millie_rec/reranking/guard.py
?? src/millie_rec/reranking/mmr.py
?? tests/reranking/
```

| 파일 | 상태 | 줄 수 |
|---|---|---|
| `src/millie_rec/reranking/mmr.py` | 신규 | 54 (≤150) |
| `src/millie_rec/reranking/guard.py` | 신규 | 65 (≤150) |
| `src/millie_rec/reranking/__init__.py` | 교체 | 19 |
| `tests/reranking/test_mmr.py` | 신규 | 8 테스트 |
| `tests/reranking/test_guard.py` | 신규 | 8 테스트 |

형제 슬라이스(`retrieval`·`ranking`·`app`·`serving`·`data`)·`contracts.py`·`Makefile`·`pyproject.toml`·`tests/test_architecture.py` 는 **이 플랜에서 열지도 고치지도 않았다**. 의존성 추가 0.

## Task 1 (RED) — 16 failed, 전부 AssertionError

스텁 2파일(상수·시그니처만 맞추고 `rerank` 는 `[]` 반환)을 먼저 두어 import 오류가 아닌 단정 실패로 RED 를 만들었다.

`uv run pytest tests/reranking --no-header` → 요약 줄 **`16 failed in 0.24s`**, 금지 사유(`ImportError`·`ModuleNotFoundError`·`AttributeError`·`TypeError`·`SyntaxError`) 0건, 출력에 등장한 테스트 파일은 `tests/reranking/` 뿐.

발췌 ①:

```
    def test_rerank_returns_k_items_with_positions_and_subset() -> None:
        out = MMRReranker(_Vecs()).rerank(U, _items(), 3)
>       assert len(out) == 3
E       assert 0 == 3
E        +  where 0 = len([])
tests/reranking/test_mmr.py:42: AssertionError
```

발췌 ②:

```
    def test_new_user_violators_in_top_n_are_pushed_out_and_next_ok_promoted() -> None:
        out = DifficultyGuard(_FakeStats(TABLE), top_n=10).rerank(NEW, _items(), 12)
>       assert [i.book_id for i in out] == [1, 2, 4, 5, 6, 7, 8, 9, 10, 12, 3, 11]
E       assert [] == [1, 2, 4, 5, 6, 7, ...]
tests/reranking/test_guard.py:47: AssertionError
```

발췌 ③:

```
    def test_stats_called_once_and_docstring_declares_proxy() -> None:
        s = _FakeStats(TABLE)
        DifficultyGuard(s).rerank(NEW, _items(), 12)
>       assert s.calls == 1
E       assert 0 == 1
E        +  where 0 = <test_guard._FakeStats object at 0x112728b90>.calls
tests/reranking/test_guard.py:95: AssertionError
```

같은 시점 `uv run pytest tests/test_architecture.py --no-header` → `3 passed`.

## Task 2 (GREEN) — 19 passed

`uv run pytest tests/reranking tests/test_architecture.py --no-header` → **`19 passed in 0.22s`**(mmr 8 + guard 8 + 아키텍처 3).

### MMR 손계산 (2차원 4벡터, λ=0.7)

벡터 `1=a=(1,0)` `2=b=(1,0)` `3=c=(0,1)` `4=d=(0.6,0.8)`, 점수 `1.0 > 0.9 > 0.8 > 0.7` → 풀 안 min-max 관련성 `a=1.0 · b=0.6667 · c=0.3333 · d=0.0`. 유사도 `sim(a,b)=1 · sim(a,c)=0 · sim(a,d)=0.6 · sim(c,d)=0.8 · sim(b,d)=0.6`.

| 단계 | 후보별 MMR = 0.7·rel − 0.3·max_sim | 선택 |
|---|---|---|
| 1 | a 0.7000 · b 0.4667 · c 0.2333 · d 0.0000 (max_sim 전부 0) | **a (book_id 1)** |
| 2 | b 0.4667 − 0.3·1.0 = 0.1667 · c 0.2333 − 0 = **0.2333** · d 0 − 0.3·0.6 = −0.18 | **c (3)** |
| 3 | b 0.4667 − 0.3·max(1.0, 0) = 0.1667 · d 0 − 0.3·max(0.6, 0.8) = −0.24 | **b (2)** |
| 4 | d 만 남음 | **d (4)** |

- k=3 → `[1, 3, 2]` · k=4 → `[1, 3, 2, 4]`
- k=2 → `[1, 3]`, `ild_at_k` 실측: 원 순서 `[1, 2]` = **0.0** → 재순위 `[1, 3]` = **1.0** (REC-05 소형 증거)
- `lam=1.0` → 다양성 항 0 → 관련성 순서 `[1, 2, 3, 4]` 유지
- 안전성: `items=[]` → `[]` · `k=10`/items 4 → 4개 · 미지 id 99(0 벡터) 섞여도 예외 없음(길이 3, 집합 `{1, 99, 3}`) · `pool=2`/`k=3` → 2개(`items[pool:]` 를 뒤에 붙이지 않는다) · items 1개 → position 0
- `vectors.vectors` 는 rerank 1회당 **1회** 호출(카운터 단정)

### 난이도 가드 손계산 (12권)

items `1..12`(점수 12..1), 가짜 stats: `3 → resid_z −1.5 millie_index` · `11 → −1.2 millie_index` · `5 → −2.0 category_prior`(모집단 제외) · 나머지 `0.0 millie_index`. 신규 사용자 `UserState(None, explicit_seeds=(100,))`(history 0 < 3).

| 구간 | 내용 |
|---|---|
| `bad`(위반 집합) | `{3, 11}` — 5 는 category_prior 라 제외 |
| `head`(상단 10) | 1..10 → `head_ok` `[1,2,4,5,6,7,8,9,10]` · `head_bad` `[3]` |
| `rest` | `[11, 12]` → 11 은 위반이라 승격 불가 → `leftover`, 12 → `promoted` |
| 결과 k=12 | `[1, 2, 4, 5, 6, 7, 8, 9, 10, 12, 3, 11]` — 12권 전부 보존, position 0..11 |
| 결과 k=10 | `[1, 2, 4, 5, 6, 7, 8, 9, 10, 12]` — 삭제가 아니라 k 절단 |

- `resid_z None`(millie_index)·`category_prior` 는 모집단 제외 → 순서에서 움직이지 않는다(5 는 그대로 4번째)
- `history=(200, 201, 202)`(≥3) → `[1..12]` 원 순서 패스스루
- `DifficultyGuard(None)`(Track A) → `items[:k]` 원 순서 + position 재부여만
- 위반 없음 → 순서 불변 · `items=[]` → `[]` · `stats` 는 rerank 1회당 **1회** 호출
- `guard.py` 소스에 `대리값` · `Phase 5` · `len(user.history)` 문자열 존재(D-08 의무, `inspect.getsource` 단정)

## Task 3 (REFACTOR) — 공개 표면 7개 + ruff 클린

- `uv run python -c "import millie_rec.reranking as r; print(len(r.__all__))"` → **7** (`GUARD_MIN_COMPLETED` `GUARD_RESID_Z` `GUARD_TOP_N` `LAMBDA_MMR` `MMR_POOL` `DifficultyGuard` `MMRReranker`). `_minmax`·`_reposition`·`MILLIE_INDEX` 는 비공개 유지
- `uv run ruff format --check src/millie_rec/reranking tests/reranking` → `5 files already formatted`
- `uv run ruff check src/millie_rec/reranking tests/reranking` → `All checks passed!`
- `uv run pytest tests/reranking tests/test_architecture.py --no-header` → `19 passed`
- `wc -l` → mmr 54 · guard 65 · `__init__` 19 (전부 ≤150)
- 전역 게이트(`uv run pytest --no-header`·`ruff check .`·`make smoke`)는 이 플랜에서 돌리지 않았다 — wave 1 종료 후 Advisor 1회(04-04-PLAN.md `<wave_gate>`)

## TDD Gate Compliance

| Gate | 증거 | 상태 |
|---|---|---|
| RED | `16 failed`, 전 실패 사유 `AssertionError`(발췌 3건 위), 금지 사유 0건 | ✅ |
| GREEN | `19 passed`(16 + 아키텍처 3) | ✅ |
| REFACTOR | `__init__.py` 공개 표면 7개 + 자기 경로 ruff format/check 클린 → 재통과 `19 passed` | ✅ |

커밋 gate(`test(...)` → `feat(...)`)는 **적용 대상이 아니다** — 플랜 frontmatter `no_commit: true`(사용자 승인 후 Advisor 일괄 커밋). gate 증거 형태는 `tdd_evidence: pytest-output` 규정대로 pytest 출력이다.

## Freeze 상수 (D-14 ①, Day 3 종료 freeze 대상)

| 이름 | 값 | 파일 | 근거 |
|---|---|---|---|
| `LAMBDA_MMR` | `0.7` | `reranking/mmr.py` | D-07(게이트 미달 시 0.5 로 **1회만** — Plan 04-05) |
| `MMR_POOL` | `50` | `reranking/mmr.py` | D-07 hybrid 순위 상위 50 을 풀로 |
| `GUARD_RESID_Z` | `-1.0` | `reranking/guard.py` | main §5-6 `resid_z < −1`(엄격 부등호 — 경계 −1.0 은 위반 아님) |
| `GUARD_MIN_COMPLETED` | `3` | `reranking/guard.py` | main §5-6 완독 <3 신규 사용자 |
| `GUARD_TOP_N` | `K_RANK`(10) | `reranking/guard.py` | 상단 N. 값의 정본은 `contracts.K_RANK` |
| `MILLIE_INDEX` | `STATS_SOURCES[0]` = `"millie_index"` | `reranking/guard.py` | 비공개 상수, 정본은 `contracts.STATS_SOURCES` |

## Plan 04-04 인계 (Advisor 가 `app/pipeline.py` 에 배선)

```python
from millie_rec.reranking import DifficultyGuard, MMRReranker

# 생성자 시그니처 (keyword-only 튜닝 인자)
MMRReranker(vectors: ItemVectors, *, lam: float = 0.7, pool: int = 50)
DifficultyGuard(
    book_stats: BookStatsSource | None = None,
    *, top_n: int = 10, resid_z_max: float = -1.0, min_completed: int = 3,
)

# 조립 순서 = D-08 hybrid_div = rank → MMR → guard
rerankers = (MMRReranker(vectors), DifficultyGuard(book_stats))
```

- 두 클래스 모두 `contracts.Reranker` 를 만족한다: `rerank(user, items, k) -> list[ScoredItem]`. 순차 적용 시 **MMR 이 먼저 k 개로 줄이므로**, 가드가 상단 N 밖으로 내릴 여유를 주려면 MMR 에 `k` 를 여유 있게(예: `k` 대신 후보 여유분) 넘길지 여부는 조립 쪽 판단이다 — 가드는 `items` 가 `top_n` 이하일 때도 안전하게 동작하지만(위반 책이 뒤로 가고 k 절단), 승격할 비위반 책이 없으면 순서만 바뀐다.
- Track A(`BookStatsSource` 없음)는 `DifficultyGuard(None)` 로 주입해도 되고 주입 자체를 생략해도 된다 — 둘 다 패스스루(04-CONTEXT.md Claude's Discretion).
- Track A 의 `ItemVectors` 는 `ContentVectors`, Track B 는 `VectorsKR` — reranking 코드는 동일하고 어댑터만 다르다(D-10).

## fixture 가드 모집단 사실 (`tests/conftest.py::millie_serving_sample`, 20권)

`resid_z = round((i % 7 − 3) · 0.5, 3)`(measured 만), `measured = i % 2 == 0 or i < 15`:

| 구분 | book_id | 비고 |
|---|---|---|
| 가드 위반(모집단 ∧ `resid_z < −1.0`) | **7, 14** | 둘 다 `resid_z = −1.5`, `millie_index` |
| 경계 `−1.0`(위반 아님, 엄격 부등호) | **1, 8** | `millie_index` |
| 결측 → 모집단 제외 | **15, 17, 19** | `category_prior`, `difficulty=None`, `resid_z=0.0` |

플랜 본문의 "1·8·15 가 −1.0 경계" 표기 중 **15 는 경계가 아니라 결측(`category_prior`)** 이다 — Plan 04-04 의 서버 4 variant 테스트에서 이 fixture 로 가드 발동을 단정할 때 위 표를 쓴다.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] 플랜 verbatim docstring 이 ruff E501 을 위반 → 줄바꿈으로 분할**
- **Found during:** Task 2 (GREEN) 직후 `ruff check`
- **Issue:** ruff 의 line-length 100 은 **CJK 문자를 폭 2 로 계산**한다. 플랜이 verbatim 으로 지정한 `mmr.py` 모듈 docstring(105), `MMRReranker` 클래스 docstring(110), `guard.py` docstring 3줄(111·101·103)이 모두 초과 → `ruff check` 4 errors.
- **Fix:** 문장 내용·의무 문자열(`대리값`·`Phase 5`·`len(user.history)`)을 그대로 유지한 채 줄바꿈만 추가했다. `mmr.py` 는 1줄 docstring → 요약 1줄 + 상세 1줄, `MMRReranker` 도 같은 형태. 상수·주석·알고리즘은 플랜 그대로.
- **Files modified:** `src/millie_rec/reranking/mmr.py`, `src/millie_rec/reranking/guard.py`
- **Commit:** 없음(`no_commit: true`)

### 수용 기준 중 이 작업 트리에서 성립하지 않는 항목 1건

Task 3 수용 기준의 `git status --short -- src/millie_rec/retrieval src/millie_rec/ranking … Makefile pyproject.toml` **출력 없음**은 이 트리에서 성립할 수 없다 — repo 에 커밋이 1개(scaffold)뿐이어서 Phase 1~3 산출물 전체가 아직 미커밋 상태이고, 같은 트리에서 wave 1 병렬 Worker 2명(`retrieval`·`ranking`)이 동시에 쓰고 있다. **이 플랜이 편집한 파일은 위 "변경 파일 목록" 5개뿐**이며, 금지 경로는 읽기조차 하지 않았다(`contracts.py`·`metrics.py`·`popularity.py`·`conftest.py`·`test_architecture.py` 는 읽기만). 확인 방법은 `git status` 가 아니라 이 목록과 Advisor 의 `git diff` 검증이다.

`git log --oneline | head -1` → `8e5172b chore: project scaffold …` (불변, 커밋 0).

같은 이유로 `.planning/STATE.md`·`.planning/ROADMAP.md` 도 `git status` 에 ` M` 으로 보이지만 **이 Worker 가 건드린 것이 아니다**(오케스트레이터·planner 세션 소유). 이 플랜이 `.planning/` 에 쓴 파일은 이 SUMMARY 1개뿐이다.

## Known Stubs

없음 — Task 1 의 스텁 2파일은 Task 2 에서 전부 실제 구현으로 교체됐고(`rerank` 가 `[]` 를 반환하는 코드 경로 없음), 하드코딩된 빈 값·placeholder·TODO 는 남아 있지 않다. `user_level()`·`n_completed` 의 실제 값은 Phase 5 `state.py` 몫으로 **설계상 이연**이며, 가드는 `len(user.history)` 대리값으로 지금 동작한다(D-08, docstring 명시).

## Self-Check: PASSED

- `src/millie_rec/reranking/mmr.py` FOUND · `src/millie_rec/reranking/guard.py` FOUND · `src/millie_rec/reranking/__init__.py` FOUND · `tests/reranking/test_mmr.py` FOUND · `tests/reranking/test_guard.py` FOUND
- `uv run pytest tests/reranking tests/test_architecture.py --no-header` → `19 passed`
- `uv run ruff format --check` + `uv run ruff check`(자기 경로) 클린
- `len(millie_rec.reranking.__all__)` == 7
- 커밋 해시 없음(의도) — `no_commit: true`
