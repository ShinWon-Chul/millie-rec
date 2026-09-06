---
phase: 04-freeze
plan: 02
subsystem: ranking
tags: [ranking, blend, hybrid, min-max, difficulty-gap, tdd, pure-python]

# Dependency graph
requires:
  - phase: 01-local-serving-skeleton
    provides: "contracts.py freeze — UserState·Candidate·ScoredItem·BookStats·Ranker·BookStatsSource Protocol"
  - phase: 02-track-a
    provides: "K_HISTORY=20 두 상태(n0/n20) 평가 유저 형태 — state_weights n 정의의 근거"
provides:
  - "ranking/blend.py state_weights — ★시간 가변 사용자 상태 가중치 α/β/γ(감쇠 τ=20·하한 0.2·빈 성분 제거 재정규화)"
  - "ranking/hybrid.py blend_channels — 채널 슬롯(cf·content·pop) min-max 정규화 + 고정 상수 가중합 + ★난이도 gap 3항"
  - "ranking/hybrid.py HybridRanker — contracts.Ranker 구현(flat Candidate → source 슬롯 그룹화 래퍼)"
  - "ranking/__init__.py 공개 표면 20개 — app 이 import 할 유일한 이름 집합"
affects: [04-04 app 조립·serving weights 배선, 04-05 가중치 튜닝 1회, Phase 5 state.py 부스트·user_level 교체]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "2단 가중치 분리(D-01): 사용자 상태 성분 가중 α/β/γ(blend.py) ↔ 채널 슬롯 가중 W_CF/W_CONTENT/W_POP(hybrid.py)"
    - "채널 슬롯 층 분리: 가중치는 Candidate.source 문자열이 아니라 슬롯 cf·content·pop 에 붙는다(Track B 는 cf 슬롯도 source=content)"
    - "Protocol 주입 optional: BookStatsSource None·user_level() None·difficulty None 세 경로 모두 가중 0(Track A 숫자 불변)"

key-files:
  created:
    - src/millie_rec/ranking/blend.py
    - src/millie_rec/ranking/hybrid.py
    - tests/ranking/test_blend.py
    - tests/ranking/test_hybrid.py
  modified:
    - src/millie_rec/ranking/__init__.py

key-decisions:
  - "state_weights 의 n = len(user.history) — Phase 4 에는 완독 이벤트가 없다(D-02). Phase 5 state.py 가 이벤트 수로 교체"
  - "reset_boost·session_active 는 시그니처로만 받고 Phase 4 에서는 결과에 영향 없음 — 적용은 Phase 5(D-02). 테스트가 무효를 단정"
  - "익명(seeds·history·session 전부 빈) 유저는 합 0 → 나눗셈 회피용 zeros 반환(serving/compose.py ZERO_WEIGHTS 와 같은 값)"
  - "source_channels 는 '그 책이 들어 있던 채널'이고 source 는 '가중 기여 최대 채널' — 서로 다른 규약(정규화 0 인 채널도 source_channels 에는 남는다)"
  - "min-max 분모 0(후보 1개·분산 0) → 1.0(Claude's Discretion, D-03 범위)"
  - "gap 3항은 음수 가중(W_GAP=-0.10·W_GAP_POS=-0.20·W_NCOMP_GAP=-0.01)으로 점수에 더한다 — 어려운 책 감점(D-06)"

patterns-established:
  - "슬롯 dict 공개 함수 + flat 래퍼: blend_channels(슬롯 dict)가 정본, HybridRanker 는 source→슬롯 매핑만 하는 얇은 층"
  - "동률 결정성: 정렬 키 (−score, book_id) · source 동률은 SLOT_ORDER 앞 슬롯 — 같은 입력 → 같은 결과(python.md)"

requirements-completed: [REC-02, REC-03, REC-04]

# Metrics
duration: 약 35분
completed: 2026-09-05
---

# Phase 4 Plan 02: 랭킹 단계(state_weights · blend_channels · HybridRanker) Summary

**★시간 가변 가중치 α/β/γ(τ=20 감쇠·하한 0.2·빈 성분 제거 재정규화)와 채널 min-max 가중합 + ★난이도 gap 3항을 순수 파이썬 2파일로 TDD 한 사이클(RED 15 → GREEN 21)로 만들었다. 의존성 추가 0, 커밋 0.**

## Performance

- **Duration:** 약 35분
- **Completed:** 2026-09-05 15:00 UTC
- **Tasks:** 3/3 (RED · GREEN · REFACTOR)
- **Files modified:** 5 (신규 4 + 교체 1)

## 변경 파일 목록 (커밋하지 않는다 — 작업 트리에 남긴다)

**커밋하지 않는다 — 작업 트리에 남기고 SUMMARY 에 변경 파일 목록을 적는다(사용자 지시 2026-09-05).** `git log --oneline | head -1` 은 실행 전후 모두 `8e5172b chore: project scaffold …` 로 불변이다.

| 파일 | 상태 | 줄 수 |
|---|---|---|
| `src/millie_rec/ranking/blend.py` | 신규 (`??`) | 43 |
| `src/millie_rec/ranking/hybrid.py` | 신규 (`??`) | 118 |
| `src/millie_rec/ranking/__init__.py` | 교체 (` M`) | 49 |
| `tests/ranking/test_blend.py` | 신규 (`??`) | 8 테스트 |
| `tests/ranking/test_hybrid.py` | 신규 (`??`) | 10 테스트 |

`git status --short -- src/millie_rec/retrieval src/millie_rec/reranking src/millie_rec/app src/millie_rec/serving src/millie_rec/data src/millie_rec/contracts.py Makefile pyproject.toml tests/test_architecture.py` 에 보이는 변경분은 **이 플랜 실행 전부터 있던 Phase 1~3 미커밋 산출물**이며, 이 플랜은 위 표의 5개 경로만 건드렸다(`ruff format` 도 `src/millie_rec/ranking tests/ranking` 로만 실행). `.planning/STATE.md`·`.planning/ROADMAP.md` 는 이 플랜이 열지도 쓰지도 않았다(둘 다 실행 전부터 ` M` 상태 — 오케스트레이터 소유).

## Accomplishments

### Task 1 (RED) — 스텁 2파일 + 테스트 18건

상수·시그니처는 Task 2 와 동일하고 값만 틀린 스텁(`state_weights` → zeros 고정, `blend_channels`·`HybridRanker.rank` → `[]`)을 먼저 둬서 import 가 살아 있는 상태로 단정만 실패하게 했다.

```
$ uv run pytest tests/ranking --no-header
15 failed, 3 passed in 0.07s
```

플랜 예측(`15 failed, 3 passed`)과 정확히 일치. 스텁에서도 통과한 3건은 `test_keys_are_alpha_beta_gamma_in_order`·`test_boost_flags_accepted_but_not_applied_in_phase4`·`test_empty_channels_give_empty_list`(형태만 단정하는 테스트).

**실패 사유 검증:** 출력 안 `ImportError|ModuleNotFoundError|AttributeError|TypeError|SyntaxError` **0건**, `AssertionError` 18회. AssertionError 발췌 3건:

```
    def test_history_20_with_session_matches_decay_formula() -> None:
        w = state_weights(_u(20, session=True))
>       assert w["alpha"] == pytest.approx(0.221, abs=2e-3)
E       assert 0.0 == 0.221 ± 0.002
tests/ranking/test_blend.py:47: AssertionError
```

```
        assert state_weights(UserState(None)) == {"alpha": 0.0, "beta": 0.0, "gamma": 0.0}
>       assert state_weights(UserState(None, explicit_seeds=(1,)))["alpha"] == 1.0
E       assert 0.0 == 1.0
tests/ranking/test_blend.py:62: AssertionError
```

```
    def test_gap_features_penalize_harder_books_with_negative_weights() -> None:
        stats = _FakeStats(0.5, {1: 0.9, 2: 0.5, 3: None})
        items = blend_channels(U, _channels(), book_stats=stats)
>       assert [i.book_id for i in items] == [1, 2, 3]
E       assert [] == [1, 2, 3]
tests/ranking/test_hybrid.py:88: AssertionError
```

`uv run pytest tests/test_architecture.py --no-header` → `3 passed`(스텁 단계에서도 star 의존 위반 없음).

### Task 2 (GREEN) — 구현 후 21 passed

```
$ uv run pytest tests/ranking tests/test_architecture.py --no-header
.....................                                                    [100%]
21 passed in 0.03s
```

**state_weights 수식 대입표** (α_n = max(0.2, 0.6·e^{−n/20}), 나머지를 β:γ = 3:1 → 빈 성분 제거 → 합 1 재정규화, `round(…, 3)`):

| 입력 | α_raw | β_raw | γ_raw | 유지 성분 | 결과 (α, β, γ) |
|---|---|---|---|---|---|
| seeds만, n=0 | 0.600000 | 0.300000 | 0.100000 | α | **1.0, 0.0, 0.0** (REC-03 신규 β=0) |
| seeds + n=20, session 없음 | 0.220728 | 0.584454 | 0.194818 | α, β | **0.274, 0.726, 0.0** |
| seeds + n=20, session 있음 | 0.220728 | 0.584454 | 0.194818 | α, β, γ | **0.221, 0.584, 0.195** |
| seeds + n=200, session 있음 | 0.200000 (하한) | 0.600000 | 0.200000 | α, β, γ | **0.2, 0.6, 0.2** (정확) |
| history만 n=20 | — | 0.584454 | — | β | **0.0, 1.0, 0.0** |
| 익명(전부 빈) | — | — | — | 없음 (합 0) | **0.0, 0.0, 0.0** |

**blend_channels min-max 손계산표** (채널: cf `[1:4.0, 2:2.0]` · content `[2:1.0, 3:0.5]` · pop `[3:10.0]`, 가중 0.5/0.3/0.2):

| book | cf norm | content norm | pop norm | 기본 점수 | source | source_channels |
|---|---|---|---|---|---|---|
| 1 | 1.0 | — | — | **0.5** | itemknn | `("itemknn",)` |
| 2 | 0.0 | 1.0 | — | **0.3** | content | `("itemknn", "content")` |
| 3 | — | 0.0 | 1.0 (단독→1.0) | **0.2** | popularity | `("content", "popularity")` |

**gap 3항 검증** (`_FakeStats(level=0.5, {1: 0.9, 2: 0.5, 3: None})`, W_GAP=−0.10 · W_GAP_POS=−0.20 · W_NCOMP_GAP=−0.01):

| book | difficulty | gap | n_completed | 보정 | 점수 |
|---|---|---|---|---|---|
| 1 | 0.9 | +0.4 | 0 | −0.04 −0.08 = −0.12 | **0.38** |
| 1 | 0.9 | +0.4 | 2 (`history=(7,8)`) | −0.12 −0.008 | **0.372** |
| 2 | 0.5 | 0.0 | 0 | 0 | 0.3 |
| 3 | None (결측) | — | — | 0 (가중 0) | 0.2 |

None 3경로(`book_stats=None` · `user_level()` None · `difficulty` 전부 None) 모두 점수가 기본 `[0.5, 0.3, 0.2]` 로 불변 — Track A(BookStats 없음)와 서버 신규 유저(n=0) 숫자에 영향 0(D-06).

### Task 3 (REFACTOR) — 공개 표면 20개 + ruff

```
$ uv run python -c "import millie_rec.ranking as r; print(len(r.__all__))"
20
$ uv run ruff format --check src/millie_rec/ranking tests/ranking
5 files already formatted
$ uv run ruff check src/millie_rec/ranking tests/ranking
All checks passed!
$ uv run pytest tests/ranking tests/test_architecture.py --no-header
21 passed in 0.05s
$ wc -l src/millie_rec/ranking/*.py
      49 __init__.py    43 blend.py   118 hybrid.py
```

부가 확인: `import millie_rec.ranking` 후 `'numpy' in sys.modules` → `False`(순수 파이썬, 서버가 공개 표면을 읽어도 numpy 를 끌어오지 않는다) · `grep -rn "millie_rec\.(retrieval|reranking|data|evaluation|serving|app)" src/millie_rec/ranking/` → 0건(star 의존) · 테스트에 구현 상수 이름(`ALPHA0`·`W_CF`·`W_GAP`) 0회(기대값은 손으로 적었다 — freeze 가 의미를 갖는 조건).

## freeze 상수표 (D-14 ① — 개발일지 D 항목·PDF 각주가 이 이름을 인용한다)

| 이름 | 값 | 파일 | 근거 |
|---|---|---|---|
| `ALPHA0` | 0.6 | `ranking/blend.py` | 아키텍처 01 §3-3 초기값 |
| `BETA0` | 0.3 | `ranking/blend.py` | 아키텍처 01 §3-3 초기값 |
| `GAMMA0` | 0.1 | `ranking/blend.py` | 아키텍처 01 §3-3 초기값 |
| `TAU` | 20 | `ranking/blend.py` | main §5-2 α_n = α₀·e^{−n/τ} |
| `ALPHA_FLOOR` | 0.2 | `ranking/blend.py` | 아키텍처 01 §3-3 하한 |
| `W_CF` | 0.5 | `ranking/hybrid.py` | 결정 D-03 초기값(04-CONTEXT.md) |
| `W_CONTENT` | 0.3 | `ranking/hybrid.py` | 결정 D-03 초기값 |
| `W_POP` | 0.2 | `ranking/hybrid.py` | 결정 D-03 초기값 |
| `W_GAP` | −0.10 | `ranking/hybrid.py` | 결정 D-06 gap 항 |
| `W_GAP_POS` | −0.20 | `ranking/hybrid.py` | 결정 D-06 gap⁺ 항 |
| `W_NCOMP_GAP` | −0.01 | `ranking/hybrid.py` | 결정 D-06 n_completed×gap 항 |

부수 상수(freeze 대상 아님, 이름만 고정): `WEIGHT_KEYS=("alpha","beta","gamma")` · `RESET_BOOST=0.15` · `SESSION_BOOST=0.10`(Phase 5 적용) · `ROUND=3` · `CH_CF/CH_CONTENT/CH_POP="cf"/"content"/"pop"` · `SLOT_ORDER=(cf, content, pop)` · `SLOT_OF_SOURCE={itemknn: cf, content: content, popularity: pop}` · `CHANNEL_WEIGHTS={cf: 0.5, content: 0.3, pop: 0.2}`.

## Plan 04-04 인계 — Advisor 가 `app/`·`serving/api.py` 에 배선할 공개 시그니처

```python
from millie_rec.ranking import (  # 공개 표면 20개 중 배선에 쓰는 것
    CHANNEL_WEIGHTS, CH_CF, CH_CONTENT, CH_POP, HybridRanker, blend_channels, state_weights,
)

def state_weights(
    user: UserState, *, reset_boost: bool = False, session_active: bool = False
) -> dict[str, float]: ...
# → app/server.py 가 create_app(weights=state_weights) 로 주입(D-09).
#   키는 항상 ("alpha","beta","gamma") 순서, 값은 소수 3자리. 익명은 zeros.

def blend_channels(
    user: UserState,
    channels: dict[str, list[Candidate]],        # 슬롯 키: "cf" | "content" | "pop"
    weights: dict[str, float] | None = None,     # None → CHANNEL_WEIGHTS. cf variant = {"cf": 1.0}
    *,
    book_stats: BookStatsSource | None = None,   # None → gap 3항 가중 0
) -> list[ScoredItem]: ...

class HybridRanker:  # contracts.Ranker
    def __init__(
        self,
        weights: dict[str, float] | None = None,
        *,
        book_stats: BookStatsSource | None = None,
        slot_of: dict[str, str] | None = None,   # None → SLOT_OF_SOURCE
    ) -> None: ...
    def rank(self, user: UserState, candidates: list[Candidate]) -> list[ScoredItem]: ...
```

**배선 주의 3가지**

1. **Track B 는 `HybridRanker` 를 쓰지 말고 `blend_channels` 에 슬롯 dict 를 직접 넘긴다.** Track B 의 cf 채널(`CatalogKR.neighbors`)도 `Candidate.source="content"` 라(`.claude/rules/data.md`) `SLOT_OF_SOURCE` 가 content 슬롯으로 밀어 넣는다. `channels={"cf": 이웃후보, "content": 벡터후보, "pop": 인기후보}` 로 app 이 조립하면 표기(`source="content"`)와 가중(슬롯 `cf`)이 동시에 맞는다. 또는 `slot_of=` 로 다른 매핑을 주입할 수 있다.
2. **variant 별 가중치는 `weights` dict 로만 준다.** `pop` = `{"pop": 1.0}`, `cf` = `{"cf": 1.0}`, `hybrid`/`hybrid_div` = `None`(=`CHANNEL_WEIGHTS`). 가중치가 없는 슬롯은 후보에서 통째로 빠진다.
3. **`ScoredItem` 의 `title`·`authors`·`image_url` 은 채우지 않는다.** 랭커는 meta 조인을 하지 않는다(Track B 는 `app/pipeline*` 가 `catalog.meta` 로 채우는 기존 `CatalogPopPipeline` 패턴 유지). 랭커가 채우는 필드는 `book_id`·`score`·`source`·`position`·`source_channels`·`difficulty` 6개다.

## Deviations from Plan

### 자동 수정 (Rule 3 — 완료 기준 자체가 막히는 문제)

**1. [Rule 3 - Blocking] 플랜이 verbatim 으로 준 docstring 3줄이 ruff E501(100자) 위반 → 2줄로 분할**
- **발견 시점:** Task 1(테스트 작성 직후)·Task 3(ruff)
- **문제:** 한글 docstring 3개가 각각 104·105·103자로 `line-length = 100`(pyproject.toml `[tool.ruff]`)을 넘겨 `ruff check` 가 실패했다. 플랜 완료 기준(`ruff check` 클린)과 플랜 본문(docstring verbatim)이 충돌.
- **수정:** 의미·용어를 유지한 채 개행만 넣었다 — `tests/ranking/test_hybrid.py` 첫 줄, `src/millie_rec/ranking/blend.py` 모듈 docstring, 같은 파일 `state_weights` docstring 2번째 줄.
- **영향:** 없음(문자열 내용만). 상수·로직·테스트 단정 무변경.

**2. [Rule 3 - Blocking] 인덱스 단정 앞에 book_id 목록 단정을 먼저 둠 (RED 유효성)**
- **발견 시점:** Task 1
- **문제:** 플랜의 hybrid 테스트 7건이 `items[0].score` 처럼 바로 인덱싱하는데, RED 스텁은 `[]` 를 반환하므로 `IndexError` 가 난다. `.claude/rules/python-tdd.md` 는 **`AssertionError` 만 RED 로 인정**한다.
- **수정:** 각 테스트의 첫 단정을 `assert [i.book_id for i in items] == [...]` 로 두고 그 뒤에 플랜의 인덱스 단정을 그대로 남겼다. 스텁에서는 첫 단정이 AssertionError 로 멈춘다.
- **영향:** 단정이 1개 늘었을 뿐 기대값은 플랜과 동일. RED 결과가 플랜 예측(`15 failed, 3 passed`)과 정확히 일치.

### 판정 기준 교체 (문서화만)

**3. 줄 길이 검사는 `awk 'length > 100'` 대신 ruff E501 을 사용**
- 플랜 수용 기준의 `awk 'length > 100' … | wc -l` == 0 은 macOS awk 가 **바이트**를 세기 때문에 한글 주석이 있는 파일에서 항상 0 이 아니다(실측 10). 문자 기준 검사(`ruff check` E501 · Python `len(line)`)로 판정했고 둘 다 위반 0이다. 이 항목만 기준을 바꿨고 나머지 수용 기준 grep 은 플랜 그대로 통과했다.

Rule 4(구조 변경) 해당 없음. `contracts.py`·형제 슬라이스·`Makefile`·`pyproject.toml`·`tests/test_architecture.py` 무변경, 의존성 추가 0.

## TDD Gate Compliance

플랜 frontmatter `no_commit: true`(사용자 지시 2026-09-05: 커밋은 사용자 승인 후 Advisor 가 일괄) 때문에 **커밋 기반 게이트 증거(`test(...)` → `feat(...)` → `refactor(...)` 커밋 3개)를 만들지 않았다.** 대체 증거는 `tdd_gate_evidence: pytest-output` 규약에 따른 pytest 출력이며 위 Task 1~3 절에 그대로 인용했다:

| 게이트 | 증거 | 결과 |
|---|---|---|
| RED | `uv run pytest tests/ranking --no-header` (스텁 상태) | `15 failed, 3 passed` · AssertionError 18회 · import/타입 오류 0 |
| GREEN | 같은 명령 + `tests/test_architecture.py` (구현 후) | `21 passed` |
| REFACTOR | `ruff format --check` + `ruff check` + 재실행 | 클린 · `21 passed` 유지 · `__all__` 20개 |

또한 wave 1 병렬(형제 Worker 가 `retrieval`·`reranking` 에서 RED 진행 중)이라 전체 트리 `uv run pytest`·`ruff check .`·`make smoke` 는 **이 플랜에서 돌리지 않았다** — wave 1 종료 후 Advisor 1회(04-04-PLAN.md `<wave_gate>`).

## Known Stubs

없음. Task 1 의 스텁 2개는 Task 2 에서 실제 구현으로 교체됐다(`grep -c STUB src/millie_rec/ranking/*.py` → 0).

의도된 미구현(플랜 범위 밖, 문서화된 대리값):
- `reset_boost`·`session_active` 는 시그니처로 받기만 하고 적용은 Phase 5 `serving/state.py`(결정 D-02). 무효임을 `test_boost_flags_accepted_but_not_applied_in_phase4` 가 단정.
- `n_completed = len(user.history)` 는 대리값이며 Phase 5 가 완독 이벤트 수로 교체한다(결정 D-08). `_gap_bonus` 주석에 명시.
- `user_level()` 은 Phase 4 에서 `CatalogKR` 이 None 을 반환하므로 서버 경로의 gap 3항은 실제로 0이다 — 이 플랜의 증거는 "피처 3항이 각각 순위화 입력에 존재"까지(결정 D-05·D-06, 수용 기준 '난이도 4층 피처·ablation'(../.assets/PRD/PRD_메인_추천_시스템.md §9 수용 기준 표)).

## Threat Flags

없음. `<threat_model>` 의 T-04-07~T-04-12 밖의 새 표면(네트워크·인증·파일 접근·스키마)을 만들지 않았다. 순수 함수 2개 + 상태 없는 클래스 1개, I/O·로깅·난수 0.

- T-04-07(ZeroDivision): `total <= 0.0` 분기로 방어, `test_anonymous_is_all_zero_and_seeds_user_is_not` 가 단정.
- T-04-12(평가 누수·seen): `blend_channels` 가 `user.seen` 을 결과에 넣지 않는다, `test_seen_candidates_are_never_returned` 가 단정. `harness.evaluate` 의 seen 반환 ValueError 와 이중 방어.

## Self-Check: PASSED

- `src/millie_rec/ranking/blend.py` FOUND · `src/millie_rec/ranking/hybrid.py` FOUND · `src/millie_rec/ranking/__init__.py` FOUND · `tests/ranking/test_blend.py` FOUND · `tests/ranking/test_hybrid.py` FOUND
- 커밋 해시 없음 — `no_commit: true` 로 의도된 것. `git log --oneline | head -1` = `8e5172b`(실행 전과 동일)
- `uv run pytest tests/ranking tests/test_architecture.py --no-header` → `21 passed`(재실행 확인)
