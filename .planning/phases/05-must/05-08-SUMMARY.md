---
phase: 05-must
plan: 08
subsystem: 조립(app/ 배선 + Model 레인 1줄×2)
tags: [SERV-04, SERV-09, SERV-03, state, book_stats, last_breakdown, n_completed, tdd]
requires: [serving.StateStore, serving.ServingBookStats, serving.create_app, contracts.UserState.context]
provides: [server.store, server.stats, StagedPipeline.last_breakdown, WithMeta.last_breakdown, build_pipelines(book_stats=), build_pipelines_kr(book_stats=), app.staged]
affects: [05-06 api.py cascade(latency_breakdown 세분 키·state), 05-09 wave 2 게이트, wave 4 after_completion]
tech-stack:
  added: []
  patterns: [threading.local 요청별 기록, 프로퍼티 프록시(WithMeta), 계약 dict 필드 분기(context), 클래스 이동 + re-export]
key-files:
  created:
    - src/millie_rec/app/staged.py
    - tests/app/test_server_state.py
  modified:
    - src/millie_rec/app/server.py
    - src/millie_rec/app/pipeline.py
    - src/millie_rec/app/pipeline_kr.py
    - src/millie_rec/ranking/hybrid.py
    - src/millie_rec/reranking/guard.py
    - tests/ranking/test_hybrid.py
    - tests/reranking/test_guard.py
decisions: [D-07, D-09 (.planning/phases/05-must/05-CONTEXT.md), Advisor 확정 4·5·17 B4, revision C2]
metrics:
  tasks: 2
  files: 9
  tests_added: 7
  completed: 2026-09-06
commits: 0   # no_commit
---

# Phase 5 Plan 08: app 조립 — 상태 주입 · breakdown 타이밍 · n_completed 분기 Summary

`StateStore` 1개를 `create_app(state=)` 와 파이프라인 `book_stats`(`ServingBookStats`) 양쪽에 주입하고, `StagedPipeline` 에 `threading.local` 기반 `last_breakdown`(retrieval·ranking·rerank) 타이밍을 붙였으며, `guard.py`·`hybrid.py` 의 `len(user.history)` 대리값을 `int(user.context.get("n_completed", len(user.history)))` 분기 1줄로 바꿔 서버는 완독 수를, Track A 는 기존 대리값을 쓰게 했다.

## 커밋

**커밋하지 않는다 — 작업 트리에 남기고 이 SUMMARY 에 변경 파일 목록을 적는다**(사용자 지시 2026-09-05, 플랜 frontmatter `no_commit: true`). `commits: 0`. `git log --oneline -1` → `8e5172b chore: project scaffold …`(플랜 시작 시점과 동일, 변화 없음).

## TDD 증거

### RED — 신규 테스트 7건 중 6건 실패, 전부 `AssertionError`

명령: `uv run pytest tests/app/test_server_state.py tests/ranking/test_hybrid.py tests/reranking/test_guard.py --no-header`

요약 줄:

```
6 failed, 19 passed, 2 warnings in 0.27s
```

`AttributeError` · `TypeError` · `ImportError` · `ModuleNotFoundError` · `NameError` · `SyntaxError` **0건**(grep 확인), `AssertionError`/`E  assert` 12줄. 발췌:

```
____________ test_server_injects_state_store_and_serving_book_stats ____________
        store = getattr(server, "store", None)
>       assert isinstance(store, StateStore)
E       assert False
E        +  where False = isinstance(None, StateStore)

____________ test_staged_pipeline_records_last_breakdown_three_keys ____________
        bd = getattr(inner, "last_breakdown", None)
>       assert isinstance(bd, dict)
E       assert False
E        +  where False = isinstance(None, dict)

_______ test_context_n_completed_overrides_history_proxy_in_gap_term _______
>       assert items[0].score == pytest.approx(0.38 + (-0.01 * 5 * 0.4))
E       assert 0.372 == 0.36 ± 3.6e-07

_______________ test_context_n_completed_overrides_history_proxy _______________
>       assert [i.book_id for i in out] == [i.book_id for i in _items()]  # 완독 3 → 패스스루
E       assert [1, 2, 4, 5, 6, 7, ...] == [1, 2, 3, 4, 5, 6, ...]
E         At index 2 diff: 4 != 3
```

실패 6건 = `test_server_injects_state_store_and_serving_book_stats` · `test_staged_pipeline_records_last_breakdown_three_keys` · `test_build_pipelines_kr_passes_book_stats_to_guard_and_blend` · `test_server_starts_without_catalog_and_stats_is_none` · `test_context_n_completed_overrides_history_proxy_in_gap_term` · `test_context_n_completed_overrides_history_proxy`.

**RED 전에 미리 넣은 것(플랜 1-a 단서에 따른 명시):** `build_pipelines` · `build_pipelines_kr` 의 `book_stats` **keyword 만** 시그니처에 먼저 추가(값은 무시). 그러지 않으면 두 테스트가 `TypeError: unexpected keyword argument` 로 죽어 RED 로 치지 않기 때문(`../.claude/rules/python-tdd.md` "Red 는 `AssertionError`"). 그래서 `test_build_pipelines_passthrough_book_stats_keyword` 1건은 RED 시점에 이미 통과(7건 중 6건 실패).

### GREEN

명령: `uv run pytest tests/app/test_server_state.py tests/ranking tests/reranking tests/test_architecture.py --no-header`

```
44 passed, 2 warnings in 0.45s
```

(신규 5 + `tests/ranking` 기준선 + 1 + `tests/reranking` 기준선 + 1 + 아키텍처 3)

### REFACTOR / 완료 기준(revision A5 — 자기 경로만)

- `uv run ruff format --check src/millie_rec/app src/millie_rec/ranking/hybrid.py src/millie_rec/reranking/guard.py tests/app/test_server_state.py tests/ranking/test_hybrid.py tests/reranking/test_guard.py` → `13 files already formatted`
- `uv run ruff check <같은 경로>` → `All checks passed!`
- `wc -l` → `server.py 38`(≤40) · `pipeline.py 87` · `staged.py 90` · `pipeline_kr.py 133` (전부 ≤150)
- 재실행 `44 passed`

**05-09 wave 2 게이트로 이관(여기서 돌리지 않음, revision A5):** 전역 `uv run pytest`, `tests/app` 전체, `tests/serving/test_smoke.py`, `make smoke`. 05-06 이 같은 시각에 `serving/api.py` 를 재구성 중이라 결합을 피했다.

## TDD Gate Compliance

커밋 게이트(`test(...)` → `feat(...)`)를 **생략**했다. 사유: 이 프로젝트의 커밋 정책상 Phase 1~5 산출물은 사용자 승인 후 일괄 커밋한다(사용자 지시 2026-09-05, 플랜 `no_commit: true`). 대체 증거 = 위 pytest 요약 줄 2개(RED `6 failed, 19 passed` / GREEN `44 passed`)와 RED 발췌.

## 구현 요지

**`src/millie_rec/app/server.py`** (26 → 38줄) — 세 줄이 늘었다: `store = StateStore()` · `stats = ServingBookStats(catalog, store) if catalog is not None else None` · `create_app(..., book_stats=stats, state=store)`. `build_pipelines(catalog=catalog, weights=state_weights, book_stats=stats)` 로 같은 `stats` 를 파이프라인에도 준다(가드·gap 이 서빙 `user_level`·완독 수를 본다). import 는 공개 표면 1줄(`from millie_rec.serving import Database, GlobalPopularFallback, ServingBookStats, StateStore, create_app, resolve_db_path`) — star 의존 유지. `catalog=None` 이면 `stats is None` 이라 아티팩트 없이 기동한다(`../.claude/rules/local-run.md`). `StaticFiles` 마운트는 그대로 마지막.

**`src/millie_rec/app/staged.py`** (신규 90줄, Advisor 확정 17 B4) — `PopPipeline`·`StagedPipeline` 을 `pipeline.py`(149줄, 한도 임박) 에서 이동. `POP = VARIANTS[0]`·`MS = 1000.0` 만 자체 정의하고 나머지는 `contracts`·`ranking`·`retrieval` 공개 표면에서 import. `StagedPipeline.__init__` 에 `self._tl = threading.local()`, 읽기는 `@property last_breakdown`(없으면 `{}`) — 스레드풀 핸들러가 동시에 호출해도 다른 요청의 값을 읽지 않는다(revision C2). `recommend` 는 `perf_counter` 4회만 늘었고 상수·로직·반환값은 그대로다.

**`last_breakdown` 세 키 정의 (1줄):** `retrieval` = 채널별 `retrieve(user, pool)` 전부, `ranking` = `blend_channels` + `catalog.eligible` 노출 자격 필터, `rerank` = reranker 루프(MMR → DifficultyGuard) — 단위는 밀리초 `float`.

**`src/millie_rec/app/pipeline.py`** (149 → 87줄) — 상단에 `from millie_rec.app.staged import PopPipeline, StagedPipeline  # 기존 import 경로 유지(re-export)`. `tests/app/test_pipeline.py` 의 `from millie_rec.app.pipeline import StagedPipeline …` 은 무변경으로 통과. 이동으로 쓰이지 않게 된 import(`Sequence` `replace` `CandidateGenerator` `Reranker` `ScoredItem` `blend_channels` `POOL`)를 제거하고, `build_pipelines(..., book_stats: BookStatsSource | None = None)` 를 `build_pipelines_kr(catalog, weights=weights, book_stats=book_stats)` 로 패스스루. `POP/CF/HYBRID/HYBRID_DIV` · `SOURCE_POPULARITY` · `WeightFn` 은 그대로 남아 `pipeline_kr.py` 의 import 가 바뀌지 않았다.

**`src/millie_rec/app/pipeline_kr.py`** (123 → 133줄) — `build_pipelines_kr(catalog, *, weights=None, vectors=None, book_stats=None)`, 본문 첫 줄에 `bs = book_stats or catalog`(주입 없으면 종전대로 카탈로그 자신) → `kw["book_stats"] = bs` · `DifficultyGuard(bs)`. `WithMeta` 에 `last_breakdown` 프로퍼티 프록시 3줄(`getattr(self.inner, "last_breakdown", None)`) — 05-06 cascade 의 `getattr(pipe, "last_breakdown", None)` 이 데코레이터를 통과해 읽는다(D-09).

**`src/millie_rec/ranking/hybrid.py`** — `_gap_bonus` 안 1줄만: `n_completed = int(user.context.get("n_completed", len(user.history)))` + 주석 1줄. `W_GAP, W_GAP_POS, W_NCOMP_GAP = -0.10, -0.20, -0.01` 🧊 무변경.

**`src/millie_rec/reranking/guard.py`** — `rerank` 첫 줄에 같은 분기 1줄을 두고 조건을 `n_completed >= self.min_completed` 로. 모듈 docstring 은 기존 문장을 **그대로 두고** `(교체됨: context["n_completed"], Phase 5 05-08)` 한 줄만 덧붙여 `test_stats_called_once_and_docstring_declares_proxy` 가 요구하는 `"대리값"`·`"Phase 5"`·`"len(user.history)"` 세 문자열이 모두 남는다. `GUARD_MIN_COMPLETED = 3` 🧊 무변경.

## 수용 기준 grep 결과

| 검사 | 기대 | 실측 |
|---|---|---|
| `from millie_rec.app.staged import` (pipeline.py) | 1 | 1 |
| `threading.local` (staged.py) | 1 | 1 |
| `state=store` (server.py) | 1 | 1 |
| `ServingBookStats(catalog, store)` (server.py) | 1 | 1 |
| `book_stats=stats` (server.py) | 2 | 2 |
| `self._tl.bd = {"retrieval"` (staged.py) | 1 | 1 |
| `book_stats or catalog` (pipeline_kr.py) | 1 | 1 |
| `int(user.context.get("n_completed", len(user.history)))` | hybrid 1 / guard 1 | 1 / 1 |
| guard.py `"대리값"` · `"Phase 5"` · `"len(user.history)"` | 각 ≥1 | 2 / 2 / 2 |
| `^GUARD_MIN_COMPLETED = 3` · `^W_GAP, W_GAP_POS, W_NCOMP_GAP = -0.10, -0.20, -0.01` | 2행 | 2행(freeze 불변) |
| `wc -l` server / pipeline / staged / pipeline_kr | ≤40 / ≤150 ×3 | 38 / 87 / 90 / 133 |

`git diff --stat -- src/millie_rec/serving src/millie_rec/contracts.py src/millie_rec/retrieval src/millie_rec/ranking/blend.py src/millie_rec/reranking/mmr.py` 에 `contracts.py`(+1) · `retrieval/__init__.py`(+33) · `serving/__init__.py`(+19) 가 보이지만 **이 플랜의 변경이 아니다**(앞 페이즈·05-01 형제 플랜의 미커밋 변경). 같은 diff 를 `last_breakdown|staged|ServingBookStats\(catalog, store\)|n_completed", len` 로 grep → **0건**. `ranking/__init__.py`·`reranking/__init__.py` 의 `M` 도 같은 이유(Phase 4 공개 표면), 이 Worker 는 두 파일을 열지 않았다.

## 개발일지 D77 초안 (6요소 — 05-09 가 기록)

### D77. n_completed 대리값 교체 = UserState.context 분기 1줄(Model 레인 상수 무변경) · cascade.py 신설 · seeds cold-start 는 1행 유지  [축 ③ 추천 구조(★난이도 가드) · main §5-6 / 아키텍처 01 §3-3·§9-3 / 05-CONTEXT D-07·Advisor 확정 3·4·7]

- **문제:** 난이도 가드의 발동 조건은 "완독 3권 미만"인데, Phase 4 코드는 완독 수 대신 `len(user.history)` 를 쓰고 있었다. 서빙에서 `UserState.history` 는 읽기 행동(`reader_open`·`qualified_read`·`completion`) 전부라 완독 수와 다르다. Day 3 freeze 로 상수·시그니처는 못 건드린다.
- **동기:** 완독 이벤트가 쌓이면 가드가 풀리는 동작이 실제로 돌아야 PDF 의 "신규 사용자에게 어려운 책을 밀지 않는다" 문장이 참이 된다. 데모에서 완독 3권을 채우면 추천이 바뀌는 것을 눌러 볼 수 있어야 한다.
- **선택지:** (a) 서버가 완독 책을 `history` 앞쪽에 몰아넣고 임계 3을 그대로 써 "history ≥3 ≈ 완독 ≥3" 으로 근사 — 읽다 만 책이 완독으로 세어져 가드가 일찍 풀린다. (b) `DifficultyGuard(min_completed=…)` 를 조립 시 주입 — 파이프라인은 요청 전에 한 번 조립되므로 사용자별로 다른 값을 줄 수 없다(불가). (c) 이미 계약에 있는 `UserState.context` dict 에 서버가 `n_completed` 를 넣고, 가드·랭커가 그 키를 읽는 분기 1줄을 둔다.
- **근거:** (c)를 택했다. `context: dict[str, str]` 은 `contracts.py` 에 이미 있는 필드라 계약이 바뀌지 않고, 값이 문자열이라 `int()` 한 번이면 된다. 키가 없는 Track A 평가 경로는 `len(user.history)` 기본값으로 떨어져 Goodbooks 비교표 숫자가 흔들리지 않는다. 상수(`GUARD_MIN_COMPLETED=3`·`W_NCOMP_GAP=-0.01`)를 건드리지 않으므로 freeze 안이고, 기존 테스트도 한 줄도 고치지 않았다(가드 docstring 은 문장을 지우지 않고 한 줄 덧붙였다).
- **장애:** 없었다. 다만 `app/pipeline.py` 가 149줄이라 타이밍 코드를 넣을 자리가 없어, 파이프라인 클래스 두 개를 `app/staged.py` 로 옮기고 기존 import 경로는 re-export 로 유지했다(테스트 무수정).
- **결과:** `ranking/hybrid.py` 1줄 · `reranking/guard.py` 1줄. 되돌리는 조건 = `context` 의 키 이름이 `n_completed` 에서 바뀌거나, 완독 수를 `UserState` 정식 필드로 승격할 때.

## Deviations from Plan

### 1. [플랜 명시 재량] RED 전에 `book_stats` keyword 선추가

플랜 1-a 의 단서("`TypeError: unexpected keyword 'book_stats'` 도 RED 아님 → 시그니처는 테스트 전에 keyword 만 먼저 추가해도 된다 — 그 경우 SUMMARY 에 명시") 를 따랐다. `build_pipelines` · `build_pipelines_kr` 에 값을 쓰지 않는 keyword 만 먼저 넣고 RED 를 찍은 뒤, GREEN 에서 실제로 배선했다.

### 2. [Rule 3 - 블로킹] `test_build_pipelines_passthrough_book_stats_keyword` 는 명시 artifact 경로를 쓴다

플랜의 예시는 `build_pipelines(catalog=None, weights=None, book_stats=object())` 였으나, 이 머신에는 `artifacts/popularity.json` 이 실제로 있어 기본 `POP_ARTIFACT` 로는 `{}` 가 아니라 pop 파이프라인이 돌아온다(머신 상태 의존). `tests/app/test_pipeline.py::test_build_pipelines_empty_when_artifact_missing` 과 같은 관례로 `build_pipelines(tmp_path / "none.json", catalog=None, book_stats=object()) == {}` 로 썼다. 검사 목적(keyword 수용)은 동일하다.

### 3. [플랜 재량] `self._tl.bd` 한 줄을 지역 변수 3개로 나눠 씀

플랜 pseudocode 를 그대로 쓰면 `ruff format` 이 dict 를 4줄로 펼쳐 수용 기준 grep(`self._tl.bd = {"retrieval"` 한 줄)이 깨졌다(line-length 100). `ret, rank, rer = (t1 - t) * MS, (t2 - t1) * MS, (perf_counter() - t2) * MS` 를 앞 줄에 두고 dict 를 한 줄로 유지했다. 값·키·의미 동일.

### 4. [플랜 재량] `staged.py` 가 `POP = VARIANTS[0]` 을 자체 정의

`pipeline.py` 는 `POP, CF, HYBRID, HYBRID_DIV = VARIANTS` 를 그대로 유지해야 `pipeline_kr.py` 의 import 가 안 바뀐다. 순환 import 를 피하려고 `staged.py` 는 `PopPipeline.name` 용으로 `VARIANTS[0]` 만 따로 읽는다(이름의 정본은 여전히 `contracts.VARIANTS`, 중복 < 결합).

### 5. [플랜 보강] `WithMeta.last_breakdown` 프록시를 테스트로도 단정

플랜 테스트 목록에는 안쪽 `StagedPipeline` 만 있었으나, D-09 소비자(05-06 cascade)는 `WithMeta` 를 통해 읽으므로 `test_staged_pipeline_records_last_breakdown_three_keys` 마지막 줄에 프록시 단정 1줄을 더했다.

## 동시 진행 중(wave 2 병렬) 실패 목록

**없음.** 자기 경로 테스트 44건 전부 통과했고, `serving/api.py`(05-06 편집 중) 로 인한 `ImportError` 는 RED·GREEN 어느 실행에서도 발생하지 않았다(재시도 불필요).

## 인증 게이트

없음.

## Known Stubs

없음. `stats is None`(catalog 없음) 은 스텁이 아니라 `../.claude/rules/local-run.md` 가 요구하는 기동 경로다.

## Threat Flags

없음 — 새 네트워크 엔드포인트·인증 경로·파일 접근·스키마 변경이 없다. `context["n_completed"]` 는 서버(`state.py`)만 채우는 내부 값이고(T-05-08-01), `int()` 방어 코드는 플랜대로 넣지 않았다.

## 변경 파일 (`git status --short -- src/millie_rec/app src/millie_rec/ranking src/millie_rec/reranking tests/app tests/ranking tests/reranking`)

```
 M src/millie_rec/ranking/__init__.py      ← 이 플랜 아님(Phase 4 공개 표면)
 M src/millie_rec/reranking/__init__.py    ← 이 플랜 아님(Phase 4 공개 표면)
?? src/millie_rec/app/pipeline.py
?? src/millie_rec/app/pipeline_kr.py
?? src/millie_rec/app/server.py
?? src/millie_rec/app/staged.py
?? src/millie_rec/ranking/hybrid.py
?? src/millie_rec/reranking/guard.py
?? tests/app/
?? tests/ranking/
?? tests/reranking/
```

(`??` 는 파일이 아직 한 번도 커밋되지 않았기 때문 — 마지막 커밋이 scaffold 하나뿐이다.) 이 플랜이 실제로 만든/고친 9파일:

| 파일 | 변경 |
|---|---|
| `src/millie_rec/app/staged.py` | 신규(90줄) — `PopPipeline`·`StagedPipeline` 이동 + `last_breakdown` |
| `src/millie_rec/app/server.py` | 상태·어댑터 주입 3줄(26 → 38줄) |
| `src/millie_rec/app/pipeline.py` | 클래스 이동 + re-export + `book_stats` 패스스루(149 → 87줄) |
| `src/millie_rec/app/pipeline_kr.py` | `book_stats or catalog` + `WithMeta.last_breakdown`(123 → 133줄) |
| `src/millie_rec/ranking/hybrid.py` | 분기 1줄 + 주석 1줄 |
| `src/millie_rec/reranking/guard.py` | 분기 1줄 + docstring 1줄 덧붙임 |
| `tests/app/test_server_state.py` | 신규 5건 |
| `tests/ranking/test_hybrid.py` | 1건 추가(기존 단정 무수정) |
| `tests/reranking/test_guard.py` | 1건 추가(기존 단정 무수정) |

## 05-09 인계

1. **wave 2 게이트에서 반드시 확인:** 전역 `uv run pytest --no-header` · `tests/app` 전체(특히 `test_variants.py`·`test_server_catalog.py`·`test_pipeline.py`) · `tests/serving/test_smoke.py` · `make smoke`. 이 플랜은 05-06 의 `api.py` 재구성과 충돌을 피하려 자기 경로만 돌렸다(revision A5).
2. **`test_variants.py` 무영향 근거(정적 확인):** 서버 경로의 `book_stats` 가 `CatalogKR` → `ServingBookStats` 로 바뀌지만, `CatalogKR.user_level()` 은 항상 `None` 을 돌려주고(`data/catalog_kr.py`) `ServingBookStats.user_level()` 도 `user_key`·`categories` 가 없는 seeds 요청에서는 `None` 이라 gap 3항이 양쪽 모두 0이다. 가드 발동 조건도 `context` 없는 요청에서는 `len(user.history)` 기본값으로 같다.
3. **D77 초안**은 위 절 그대로 `../.assets/개발일지/` 에 옮긴다. 새 항목 번호는 `grep -h '^### D' ../.assets/개발일지/*.md | tail -3` 로 마지막 번호를 확인한 뒤 확정한다(`../.claude/rules/references.md`).
4. **Codex 리뷰:** 이 플랜은 `contracts.py`·`serving/**` 를 건드리지 않았으므로 `../.claude/rules/codex-review.md` 표의 **필수** 항목에 해당하지 않는다(선택 — `/codex:review --scope working-tree`).

## Self-Check: PASSED

- 파일 존재: `src/millie_rec/app/staged.py` · `server.py` · `pipeline.py` · `pipeline_kr.py` · `src/millie_rec/ranking/hybrid.py` · `src/millie_rec/reranking/guard.py` · `tests/app/test_server_state.py` 전부 확인
- 커밋 해시 없음 — `no_commit: true` 이므로 검증 대상 없음(`commits: 0`), `git log --oneline -1` 이 플랜 시작 시점과 동일
- `uv run pytest tests/app/test_server_state.py tests/ranking tests/reranking tests/test_architecture.py --no-header` → `44 passed`
- `uv run ruff format --check` · `uv run ruff check`(자기 경로 13파일) → 클린
- 수용 기준 grep 11항목 전부 기대값 일치(위 표), freeze 상수 2행 불변
- `must_not_touch` 경로에 이 플랜의 이름 0건(grep 확인)

## Codex 수정 반영 (2026-09-06, 브리프 C — F4 Model 레인)

Codex P1 지적 F4: `ranking/blend.py::state_weights` 가 `reset_boost`·`session_active` 를 인자로만 받고 적용하지 않았다. 04-CONTEXT D-02 가 적용을 Phase 5 `state.py` 로 미뤘는데 아무도 잇지 않았고, 파이프라인 리트리버는 `retrieval/neighbors.py::component_weights` 를 통해 1인자 `weights(user)` 로만 호출하므로 kwargs 는 ranking 까지 도달할 경로가 없었다. ★시간 가변 가중치(main §5-2)의 부스트 절반이 죽어 있던 셈이다.

**수정**

- `raw`(α/β/γ) 계산 직후 · `present` 필터 앞에서 기존 상수 `RESET_BOOST=0.15` 는 α 에, `SESSION_BOOST=0.10` 은 γ 에 더한다. 이후 기존 present 필터와 합 1 재정규화가 그대로 돈다 — 익명은 여전히 전부 0, seeds 없으면 α 는 0, session 비어 있으면 γ 는 0.
- 플래그 출처는 kwargs ∨ `user.context`(`"reset_boost"`/`"session_active"` == `"1"`). serving cascade 가 파이프라인 호출 전에 `context` 에 기록하는 것이 계약이다. 🧊 freeze 상수(ALPHA0/BETA0/GAMMA0/TAU/ALPHA_FLOOR/RESET_BOOST/SESSION_BOOST/ROUND) 값은 무변경.
- docstring·상수 주석에서 "적용은 Phase 5 state.py" 문구 제거.

**손계산 기대값** (n=20, seeds 5권, session 1권 — α₀·e^{−20/20} = 0.220728, 나머지 0.779272 를 β:γ = 3:1)

| 호출 | α | β | γ | 재정규화 전 합 |
|---|---|---|---|---|
| 기준(플래그 없음) | 0.221 | 0.584 | 0.195 | 1.00 |
| `session_active=True` | 0.201 | 0.531 | 0.268 | 1.10 |
| `reset_boost=True` | 0.322 | 0.508 | 0.169 | 1.15 |

**변경 파일**

| 파일 | 변경 |
|---|---|
| `src/millie_rec/ranking/blend.py` | 43 → 49줄(부스트 4줄 + 플래그 병합 2줄, 주석·docstring 문구) |
| `tests/ranking/test_blend.py` | 73 → 131줄. `test_boost_flags_accepted_but_not_applied_in_phase4` → `test_boost_flags_applied_phase5` 로 교체(Phase 4 유예를 고정하던 유일한 단정), 신규 4건 추가. 다른 기존 단정 무수정 |

**검증**

- Red `uv run pytest tests/ranking/test_blend.py --no-header` → `3 failed, 9 passed in 0.04s` (전부 AssertionError)
- Green 같은 명령 → `12 passed in 0.01s`
- `uv run pytest tests/ranking tests/evaluation tests/app tests/test_architecture.py --no-header` → `76 passed, 2 warnings in 1.77s`
- `uv run ruff format` · `uv run ruff check`(두 파일) 클린
- 평가는 플래그를 넘기지 않으므로 `results/latest.csv` 무영향(Track A 경로 수치 동일)
