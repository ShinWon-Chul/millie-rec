---
phase: 02-track-a
reviewed: 2026-09-05T06:43:38Z
depth: standard
files_reviewed: 35
files_reviewed_list:
  - src/millie_rec/data/goodbooks.py
  - src/millie_rec/data/load.py
  - src/millie_rec/data/split.py
  - src/millie_rec/data/onboarding.py
  - src/millie_rec/data/labels.py
  - src/millie_rec/data/__init__.py
  - src/millie_rec/retrieval/popularity.py
  - src/millie_rec/retrieval/content.py
  - src/millie_rec/retrieval/__init__.py
  - src/millie_rec/evaluation/metrics.py
  - src/millie_rec/evaluation/harness.py
  - src/millie_rec/evaluation/report.py
  - src/millie_rec/evaluation/figures.py
  - src/millie_rec/evaluation/__init__.py
  - src/millie_rec/serving/compose.py
  - src/millie_rec/serving/api.py
  - src/millie_rec/app/pipeline.py
  - src/millie_rec/app/cli.py
  - src/millie_rec/app/export.py
  - src/millie_rec/app/server.py
  - tests/data/test_goodbooks.py
  - tests/data/test_load.py
  - tests/data/test_split.py
  - tests/data/test_onboarding.py
  - tests/data/test_labels.py
  - tests/retrieval/test_popularity.py
  - tests/retrieval/test_content.py
  - tests/evaluation/test_metrics.py
  - tests/evaluation/test_harness.py
  - tests/evaluation/test_report.py
  - tests/evaluation/test_figures.py
  - tests/serving/test_recommend_level0.py
  - tests/serving/test_smoke.py
  - tests/app/test_pipeline.py
  - tests/app/test_cli.py
  - tests/app/test_export.py
findings:
  critical: 0
  warning: 1
  info: 3
  total: 4
status: issues_found
---

# Phase 2 'Track A 정량 평가 기반'(.planning/ROADMAP.md) 코드 리뷰 보고서

**Reviewed:** 2026-09-05T06:43:38Z
**Depth:** standard
**Files Reviewed:** 35 (신규 파일 25 + `serving/api.py` 수정 1 + `__init__.py` 4 + `figures.py`/`app/*` 등)
**Status:** issues_found (Critical 0 · Warning 1 · Info 3)

## Summary

Phase 2 'Track A 정량 평가 기반'(`.planning/ROADMAP.md`)의 산출물(data·retrieval·evaluation 3개 신규 슬라이스 + `serving/api.py` level 0 분기 + `app/{pipeline,cli,export,server}.py`)을 전부 읽고, `.planning/phases/02-track-a/02-CONTEXT.md`의 결정(D-01~D-18)·`.claude/rules/{evaluation,data,python,serving,architecture,simplicity}.md`·`src/millie_rec/contracts.py`(freeze) 대비 검증했다. 추가로 `uv run pytest --no-header`(171 passed, 2 skipped, 0 failed) · `uv run ruff check .`(All checks passed!) · `uv run ruff format --check .`(60 files already formatted)를 직접 실행해 SUMMARY의 게이트 주장을 재확인했다.

**핵심 결론: 누수·정확성·서빙 안전성 관련 치명적 결함은 발견되지 않았다.** 지표 정의(Recall 분모 `|R_u|`, NDCG 이진 gain + `IDCG=min(|R_u|,K)`, ILD 상삼각 `1-cosine` 평균)는 `evaluation.md` 문구와 코드가 줄 단위로 대응하고, 손계산 테스트(`test_metrics.py`)가 이를 고정한다. `harness.py::evaluate`는 `user.seen & relevant`와 파이프라인이 반환한 `seen` 아이템 두 경로 모두를 `ValueError`로 차단해 실제 누수 방지 장치가 이중으로 존재한다. `serving/api.py`의 level 0 분기는 익명 요청·미등록 `model`·파이프라인 예외 세 갈래 모두 안전하게 level 3로 강하하며(`_personalized_response`가 `except Exception`으로 감싸고 `log.exception`만 남긴다), 응답 본문에 예외 문자열이 노출되지 않음을 테스트(`"boom" not in r.text`)가 직접 확인한다. `app/pipeline.py::build_pipelines`는 `OSError|ValueError|KeyError|TypeError` 4종으로 아티팩트 부재·손상·JSON 스키마 불일치를 모두 흡수해 서버 기동을 막지 않는다. `git_sha()`는 argv 리스트 고정·`timeout=5`·`shell=True` 미사용으로 안전하다. star 의존(슬라이스는 `contracts`와 자기 내부만 import, `app`은 공개 표면만)은 `tests/test_architecture.py::test_slice_boundaries`가 통과하는 것으로 확인했고 직접 `grep`으로도 위반 0건을 재확인했다. 파일 길이는 전부 ≤150줄(예산 안), 신규 의존성 0, `np.random.default_rng(SEED)` 외 전역 시드/파이썬 내장 `random` 사용 0건, `eval(`·`exec(`·`shell=True`·`pickle` 0건.

아래 4건은 치명적이지 않은 개선 여지다 — Warning 1건은 코드 스멜(방어 수단이 최적화 플래그에 취약)이고, Info 3건은 향후 Phase(특히 Phase 4 다중 variant)에서 조건이 바뀌면 드러날 수 있는 잠재 리스크를 미리 기록해 두는 것이다.

## Warnings

### WR-01: temporal split의 누수 방지 단언이 `assert` 문 하나에만 의존

**File:** `src/millie_rec/data/split.py:33`
**Issue:** `_temporal()`의 핵심 불변식("train.ts.max() < test.ts.min()", `.claude/rules/data.md` "누수 방지")이 `raise ValueError`가 아니라 파이썬 `assert` 문으로만 강제된다.
```python
assert train[COL_TS].max() < test[COL_TS].min()  # 누수 단언 (data.md Track A split)
```
같은 파일의 다른 불변식들(`test_frac` 범위, ts 부분 결측)은 전부 `raise ValueError`로 명시적으로 강제하는데(L50-54), 유일하게 "미래 데이터 누수"라는 가장 중요한 불변식만 `assert`로 처리해 일관성이 없다. `assert`는 인터프리터가 `-O`(최적화 모드)로 실행되면 **바이트코드에서 완전히 제거**되어 아무 검사도 하지 않고 조용히 통과한다. 현재 `Makefile`·`Dockerfile`·테스트 실행 어디에도 `-O`나 `PYTHONOPTIMIZE`가 쓰이지 않아 실제 발동 가능성은 낮고, Track A 실행 경로(`sp = split(inter)`, `cli.py` L63)도 현재는 `holdout` 분기만 타므로(Goodbooks에 ts가 없음, Phase 2 실측이 이를 확인) 이 분기가 프로덕션에서 아직 실행되지 않는다. 그러나 `evaluation.md`가 "누수 방지"를 지표 정의와 나란히 별도 절로 두고, `harness.py`가 같은 종류의 불변식(`user.seen & relevant`)을 `raise ValueError`로 강제하는 것과 비교하면, 이 파일만 방어 수준이 낮다. 향후 UCSD Poetry 배경 레인(temporal split 실사용, CONTEXT Deferred)이 붙으면 이 경로가 실제로 실행되며, 그때 `assert`가 그대로 남아 있으면 PDF 숫자의 무결성 보증이 한 줄로 약해진다.
**Fix:** `raise ValueError(...)`로 교체(다른 3개 불변식과 동일한 패턴).
```python
if not train[COL_TS].max() < test[COL_TS].min():
    raise ValueError("temporal split leaked future rows into train")
```

## Info

### IN-01: `ContentVectors`는 전 도서 태그가 비어 있는 극단 케이스에 대한 방어 코드가 없다

**File:** `src/millie_rec/retrieval/content.py:23-29`
**Issue:** `TfidfVectorizer.fit_transform(texts)`는 입력 문서 전부가 빈 문자열/불용어뿐이면 `ValueError: empty vocabulary`를 던진다. 현재 Goodbooks-10k 데이터에서는 발생하지 않음이 실측으로 확인됐고(Plan 02 SUMMARY "빈 tags 책 0"), 팀도 이를 의도적으로 방어 코드 없이 둔 것으로 문서화했다(`../.claude/rules/simplicity.md` "예외 계층 만들지 않음"과 일치하는 판단). 다만 review focus의 "빈 그룹" 점검 항목에 해당하고, `make eval`이 이 예외를 잡지 않으므로 만약 태그 파이프라인이 바뀌어(예: `NOISE_TAGS` 확장, 또는 데이터셋 교체) 전 도서 태그가 사라지면 `make eval` 전체가 스택트레이스와 함께 죽는다 — 이는 review_context의 "known and accepted" 목록에는 없는 별도 지점이므로 참고용으로 기록한다.
**Fix:** 현재 그대로 두어도 무방(설계 결정과 일치). 향후 `NOISE_TAGS`를 확장할 때는 `test_build_goodbooks_maps_goodreads_id_and_drops_noise_tags`처럼 "빈 tags 책 수 == 0"을 회귀 테스트로 남겨두는 것을 권장.

### IN-02: `write_results`의 `n_users` 메타는 첫 번째로 등장하는 variant의 값만 남긴다 (Phase 4 다중 variant 대비)

**File:** `src/millie_rec/evaluation/report.py:104-107`
**Issue:**
```python
n_users: dict[str, int] = {}
for s, r in states:
    n_users.setdefault(s, r.n_users)
```
`states`는 `(state, EvalResult)` 튜플 시퀀스이고 여러 variant가 같은 `state`(`n0`/`n20`)로 여러 번 나타날 수 있다(Phase 4부터 `cf`·`hybrid`·`hybrid_div`가 추가됨, `contracts.VARIANTS`). `setdefault`는 그 state에 대해 **처음 정렬된 variant**(현재는 `VARIANTS` 순 정렬이므로 항상 `pop`)의 `n_users`만 기록하고, 이후 variant의 `n_users`가 다르더라도 조용히 무시한다. `.claude/rules/evaluation.md`("같은 split, 같은 테스트 유저 샘플")가 성립하는 한 모든 variant의 `n_users`는 항상 같아야 하므로 Phase 2 범위에서는 실제 문제가 없다. 그러나 이 함수 자체에는 "값이 실제로 같은지" 검증하는 코드가 없어, Phase 4에서 어떤 variant가 콜드스타트 등으로 인해 표본을 다르게 필터링하는 버그가 생겨도 `eval_<ts>.json`의 `n_users`는 아무 경고 없이 첫 variant 값으로 통일되어 보고된다 — 그 자체가 "PDF 숫자의 유일한 출처"인 파일의 조용한 오차 은폐 경로가 될 수 있다.
**Fix:** Phase 4에서 `cf` 등을 추가할 때, `n_users.setdefault` 대신 같은 state의 모든 variant `n_users`가 일치하는지 단언(`assert len({r.n_users for s2, r in states if s2 == s}) == 1`)하거나 값이 다르면 `ValueError`를 내는 방어를 추가하는 것을 권장. Phase 2 범위(단일 variant `pop`)에서는 현재 동작에 문제가 없다.

### IN-03: `serving/compose.py::build_response`의 `items[:k]` 재슬라이스는 항상 no-op이지만 코드 의도를 흐린다

**File:** `src/millie_rec/serving/compose.py:46`
**Issue:** `items`는 이미 호출부(`api.py::_personalized_response`, `_fallback_response`)에서 `pipe.recommend(user, k)` / `fallback.recommend(user, k)`로 최대 `k`개까지만 생성된 리스트를 넘겨받는다. `build_response` 내부에서 다시 `items[:k]`로 슬라이스하는 것은 현재 호출 경로 어디에서도 실질적인 효과가 없는 방어적 중복이다(버그는 아님 — 잘못된 `items`가 들어와도 안전하게 자르는 유효한 방어이긴 하다). 코드 품질 관점에서만 기록.
**Fix:** 선택 사항. 그대로 두어도 무방(방어적 프로그래밍으로 볼 수 있음). 정리하려면 "이 함수는 `items`가 이미 k개 이하임을 가정하지 않는다"는 주석 한 줄을 추가하는 편이 의도가 더 분명해진다.

---

## 검증 명령 (직접 실행, Worker 보고 재확인)

| 명령 | 결과 |
|---|---|
| `uv run pytest --no-header` | `171 passed, 2 skipped` |
| `uv run ruff check .` | `All checks passed!` |
| `uv run ruff format --check .` | `60 files already formatted` |
| `grep -rn "np.random.seed\|random.seed\|import random\\b" src/millie_rec/{data,retrieval,evaluation,serving,app}` | 0건 |
| `grep -rn "shell=True\|os.system\|eval(\|exec(\|pickle"` (동일 범위) | 0건 |
| `wc -l` (리뷰 대상 `src/` 파일 전체) | 전부 ≤150줄 |

## 검증하지 않은 것 (범위 밖)

- `contracts.py`·`serving/schemas.py`는 이번 페이즈에서 변경되지 않았으므로(freeze) 계약 자체는 리뷰 대상이 아니었다(변경 여부만 확인 — 무변경 확인됨).
- `make serve`/`make smoke`를 통한 실제 서버 기동 재현은 하지 않았다(코드 정적 분석 + 기존 pytest 스위트로 충분히 커버된다고 판단, `tests/serving/test_smoke.py`가 이미 실서버 조립 경로를 TestClient로 검증).

---

**한 줄 검증:** Track A 파이프라인(누수 방지 이중 장치·지표 정의 일치·level 0 서빙 안전망)에 치명적 결함 없음 — Warning 1건(`assert` 기반 temporal 누수 검사, 현재 미사용 경로)과 Info 3건(모두 향후 대비용 관찰)만 발견됨. `.planning/phases/02-track-a/02-REVIEW.md`
