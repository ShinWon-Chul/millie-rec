---
phase: 02-track-a
plan: 06
subsystem: 실측(Track A wave 3) — make data · make eval · level 0 검증 · draft.md P4 · EVAL-07 그림
tags: [goodbooks-10k, holdout, popularity-baseline, level0, figures, no-commit]
requires:
  - "Plan 01 data 슬라이스(download_goodbooks·build_goodbooks·split·mask_onboarding·relevant_sets)"
  - "Plan 02 retrieval(PopularityRetriever·ContentVectors)"
  - "Plan 03 evaluation(metrics·harness·report.write_results·RunMeta)"
  - "Plan 04 serving/api.py level 0 분기"
  - "Plan 05 app/{pipeline,cli,export,server}.py"
provides:
  - "results/latest.csv — PDF 비교표의 유일한 숫자 출처(pop 1행)"
  - "results/latest_states.csv — n0·n20 두 행(★시간 가변 가중치 대조군)"
  - "results/eval_20260905_0626.json — 실행 메타(seed·git_sha·필터 상수)"
  - "artifacts/serving/eval_table.json — Phase 5 GET /api/showcase 입력"
  - "artifacts/popularity.json — 서버 level 0 주입 입력(gitignore)"
  - "report/figures/eval_bar.png + millie_rec.evaluation.plot_eval_bar (EVAL-07)"
  - "report/draft.md P4 실측 bullet + 각주"
affects:
  - "Phase 4 '추천 파이프라인과 모델 freeze' — cf·hybrid·hybrid_div 행이 같은 하네스로 latest.csv 에 얹힌다"
  - "Phase 5 '서빙 Must 완성' — eval_table.json 형태가 쇼케이스 입력으로 고정됨"
tech-stack:
  added: []
  patterns:
    - "figures.py: matplotlib.use(\"Agg\") 를 pyplot import 보다 먼저(헤드리스), 컬럼 이름은 report.py 상수 재사용(재정의 없음)"
key-files:
  created:
    - src/millie_rec/evaluation/figures.py
    - tests/evaluation/test_figures.py
    - report/figures/eval_bar.png
    - results/latest.csv
    - results/latest_states.csv
    - results/eval_20260905_0626.json
    - artifacts/serving/eval_table.json
    - artifacts/popularity.json
    - data/raw/goodbooks/{ratings,books,book_tags,tags}.csv
    - data/processed/{interactions,books}.parquet
  modified:
    - src/millie_rec/evaluation/__init__.py
    - src/millie_rec/data/goodbooks.py
    - report/draft.md
decisions:
  - "NOISE_TAGS 에 audible·audio-books 2개만 보충 — 상위 45 태그 중 유일한 형식(오디오북) 잡음이고 기존 audiobook·audiobooks·audio 와 같은 개념의 철자 변종. 장르·주제 태그는 하나도 넣지 않았다(ILD 신호 보존)"
  - "재현성 확인 시 2회차 json 이 같은 분(minute) 이름으로 덮어써지므로, 1회차 json 을 스크래치패드에 백업했다가 복원해 results/eval_*.json 을 첫 실행 1개로 유지"
metrics:
  duration: "~13분(실행 시간 합계 26초: make data 15.2s + make eval 7.4s + smoke·gate)"
  tasks: 4
  files: 17
  completed: 2026-09-05
---

# Phase 2 Plan 06: Track A 실측 Summary

Goodbooks-10k 실데이터로 `pop` 기준선을 실측해 **Recall@20 = 0.063 · NDCG@10 = 0.054 · ILD@10 = 0.764**(n=0, 2,000명, `split_mode=holdout`)를 `results/`에 고정하고, 그 아티팩트를 떠 있는 서버에 주입해 `GET /api/recommend?seeds=1,2,3&k=5`가 `fallback_level=0`·`model_version=pop_v1`을 내는 것까지 실측했다. Day 1 최소 종료 조건 "`pop` Recall@20 실측 1개"(`../CLAUDE.md` §5) 달성.

## Task 1 — `make data` (유일한 네트워크 단계)

**1회차(다운로드 포함): 15.2s**

```
INFO millie_rec.data.goodbooks: downloaded ratings.csv (72126826 bytes)
INFO millie_rec.data.goodbooks: downloaded books.csv (3286659 bytes)
INFO millie_rec.data.goodbooks: downloaded book_tags.csv (16665883 bytes)
INFO millie_rec.data.goodbooks: downloaded tags.csv (722480 bytes)
INFO millie_rec.data.goodbooks: built 5976479 interactions, 10000 books
raw=4 files @ …/data/raw/goodbooks → interactions.parquet · books.parquet @ …/data/processed
```

**2회차(멱등 확인 = NOISE_TAGS 보충 후 재빌드): 2.3s, `downloaded` 로그 0줄.** `.part` 잔존 없음.

규모 sanity (전부 CONTEXT "Goodbooks 사실"과 일치):

| 항목 | 실측 | 기대 |
|---|---|---|
| interactions 행 | 5,976,479 | ≈5,976,479 ✅ |
| 유저 | 53,424 | 53,424 ✅ |
| 도서 | 10,000 | 10,000 ✅ |
| `ts` 전부 결측 | `True` | True(타임스탬프 없음) ✅ |
| `event` | `['rating']` | rating ✅ |
| rating 범위 | 1.0 ~ 5.0 | 1~5 ✅ |
| books 행 / 컬럼 | 10,000 / `book_id title authors image_url average_rating ratings_count original_publication_year categories subcategories tags` | ✅ |
| 빈 tags 책 | 0 | 소수 ✅ |

`ratings.csv` 72,126,826 바이트 > 60MB 기준 통과. `git status --short | grep -c "data/raw\|data/processed"` == **0**(gitignore 확인).

### NOISE_TAGS 보충 (D-15, 최대 1회 — 수행함)

상위 45 태그 빈도 실측 발췌:

```
  8333 fiction / 3608 adult / 3603 fantasy / 3243 romance / 2714 contemporary /
  2618 young-adult / 2504 mystery / 2471 novels / 2152 ya / 2000 adventure /
  1929 classics / … / 1131 audible / … / 907 audio-books / 897 thrillers / 889 kids
```

상위 40 안에서 **내용과 무관한 형식 태그는 `audible`(1,131, 31위) 하나**였고, 45위 안의 `audio-books`(907)는 같은 개념(오디오북 형식)의 철자 변종이다. 기존 `NOISE_TAGS`에 이미 `audiobook audiobooks audio`가 있으므로 **누락된 변종 2개만 추가**했다. 장르·주제 태그(`fiction`·`fantasy`·`classics`·`young-adult`·`non-fiction`·`romance`·`mystery`·`historical-fiction`·`science-fiction`·`adult` 등)는 하나도 넣지 않았다 — ILD의 신호이기 때문(T-02-36 완화).

변경은 **추가 2개 태그, 기존 태그 삭제 0개**(줄 재배치로 100자 line-length 유지). `git diff --numstat`은 빈 출력 — `goodbooks.py`가 아직 미커밋 신규 파일(`?? src/millie_rec/data/goodbooks.py`)이라 diff 대상이 아니다. 보충 후 `make data` 재실행 → 빈 tags 책 여전히 0, `uv run pytest tests/data --no-header` → **108 passed, 2 skipped**(failed 0, 잡음 태그 `to-read` 테스트 유지).

## Task 2 — `make eval` 실측

**실행 시간: 7.4s wall (json `elapsed_s`=7.0).** 플랜의 3~8분 예상보다 훨씬 빨랐다(표본 축소 없음, D-01 준수).

stdout 원문:
```
pop: recall@20=0.063 ndcg@10=0.054 ild@10=0.764 n_users=2000 | n20: n_users=1990 recall=0.080
split_mode=holdout n_users=2000/1990 n_excluded=114
→ eval_20260905_0626.json · …/artifacts/serving/eval_table.json · …/artifacts/popularity.json
```

### `results/latest.csv` (전문 — PDF 비교표의 유일한 숫자 출처)
```
variant,recall@20,ndcg@10,ild@10,n_users,split_mode,model_version
pop,0.063,0.054,0.764,2000,holdout,pop_v1
```

### `results/latest_states.csv` (전문)
```
variant,state,recall@20,ndcg@10,ild@10,n_users
pop,n0,0.063,0.054,0.764,2000
pop,n20,0.080,0.087,0.746,1990
```

### `results/eval_20260905_0626.json` 메타 요약
`dataset=goodbooks-10k` · `split_mode=holdout` · `test_frac=0.2` · `seed=42` · `n_users={'n0': 2000, 'n20': 1990}` · `n_excluded=114` · `k_recall=20` · `k_rank=10` · `n_onboard_seeds=5` · `k_history=20` · `min_user_interactions=5` · `min_item_interactions=5` · `git_sha=8e5172b` · `elapsed_s=7.0` · `created_at=2026-09-05T06:26:19+00:00` · `rows` 1개 · `states` 2개. 검증 스크립트 출력: `json ok {'n0': 2000, 'n20': 1990} excluded 114 sha 8e5172b elapsed 7.0` / `artifacts ok 1000`.

### 파생 아티팩트
- `artifacts/serving/eval_table.json` — `{rows, meta}` 2키만(**`states` 없음**, D-09). `meta = {dataset, split_mode, n_users:2000, k_recall:20, k_rank:10, seed:42, git_sha:8e5172b, created_at}`.
- `artifacts/popularity.json` — `name="pop"`, `items` **1,000개**(gitignore).

### 이상치 판단 — **이상치 없음**
플랜의 4개 중단 조건(`recall@20==1.0` · `>1.0` · `ndcg@10>1.0` · `ild@10==0.0`)과 `n20`의 `n_users==0` 중 **해당 없음**. 세 지표 모두 개구간 (0,1)(`awk` 검사 → `1`).

n0 vs n20 차이(Recall 0.063 → 0.080, NDCG 0.054 → 0.087, ILD 0.764 → 0.746, 모집단 2000 → 1990)는 **정상 범위**로 기록한다: n0은 `UserState.seen`이 seeds 5권뿐이라 pop 상위에 이미 읽은 train 책이 남고, n20은 train 이력 전체를 제외하므로 n20 Recall이 높게 나오는 것이 기대 동작이며 모집단도 다르다. 상수 `K_HISTORY`는 건드리지 않았다.

### 재현성
`make eval` 재실행 후 `diff` 결과 — `latest.csv`·`latest_states.csv` 모두 **바이트 동일(빈 출력)**. 2회차 json은 같은 분(minute) 파일명으로 덮어써져 개수는 1개 유지되지만, 1회차 파일을 스크래치패드에 백업했다가 복원해 **첫 실행의 기록을 보존**했다. `ls results/eval_*.json | wc -l` == 1.

## Task 3 — 전역 게이트 + level 0 실측 + `draft.md` P4

- `uv run pytest --no-header` → **169 passed, 2 skipped**(아티팩트 있는 상태, failed 0) — Task 4 이후 최종 **171 passed, 2 skipped**
- `uv run ruff format --check .` → `60 files already formatted` · `uv run ruff check .` → `All checks passed!`
- `make smoke` → `smoke: /health 200` / `smoke: / (demo static) 200` / `smoke: /api/recommend 200` / **`smoke: PASS`**

### level 0 실측 3줄 (포트 8012, 별도 기동 후 kill)
```
--- level0:     0 pop_v1 [4, 17, 5, 20, 18] trending 5
--- anonymous:  3 fallback_v1 []
--- health:     ok True None
```
`fallback_level=0` · `model_version=pop_v1` · items 5개이며 `book_id ∉ {1,2,3}`(seeds 제외 확인) · `rows[0].row_id="trending"`. 익명 요청은 level 3 유지(D-13). `/health.model_version`은 `None` — Phase 5 '서빙 Must 완성' 몫(Plan 04 결정).

### `report/draft.md` 수정 2건
① P4 괄호 줄의 `temporal split` → `random holdout(\`split_mode=holdout\`)`(W5 — Goodbooks에 타임스탬프가 없어 거짓 표기 금지, D-02). `grep -c "temporal split"` == 0.
② 기존 Phase 1 bullet 아래 실측 bullet 1줄 추가(원문):

> - (Day 1 실측, Phase 2 'Track A 정량 평가 기반') Popularity(전역 인기) 기준선 1행: Recall@20 = 0.063 · NDCG@10 = 0.054 · ILD@10 = 0.764 (n=0 온보딩 시뮬레이션, `results/latest.csv`). 같은 pop 모델을 n≥20 이력 상태(n_users=1990)에서 재측정하면 Recall@20 = 0.080 · NDCG@10 = 0.087 (`results/latest_states.csv`). 두 값의 차이는 모델이 아니라 **추천 제외 범위의 차이**에서 온다 — n=0 은 `UserState.seen` 이 seeds 5권뿐이어서 pop 상위에 이미 읽은 train 책이 남고, n≥20 은 train 이력 전체를 제외한다(모집단도 다르다). 따라서 pop 의 두 값은 ★시간 가변 가중치의 **바닥선**이고, Phase 4 의 `hybrid` 는 여기에 β(행동 이력 가중치) 변화가 더해져 n≥k 에서 pop 대비 격차가 벌어져야 증거가 된다. 각주: Goodbooks-10k(CC BY-SA 4.0), 유저 ≥5·아이템 ≥5 필터, 유저별 random holdout 20%(`split_mode=holdout`, 타임스탬프 없음), 테스트 유저 2,000명(seed 42), 온보딩 시뮬레이션 = train 긍정(rating≥4) 중 무작위 5권을 seeds 로 노출, n≥k 표는 seeds 외 이력 ≥20인 유저, 정답 = test 긍정(rating≥4), 학습(pop 카운트) = train 전체 / 추천 제외 = 해당 상태의 `UserState.seen`(n0: seeds 5권, n20: seeds + train 이력).

숫자는 전부 `awk`로 `results/latest.csv`·`latest_states.csv`에서 **쉘 변수로 뽑아 문자열 치환**했다 — 손으로 타이핑하지 않았다. 검증: `grep -q "Recall@20 = $(awk -F, 'NR==2{print $2}' results/latest.csv)"` 통과(0.063). grep 카운트: Phase 2 bullet 1 · `split_mode=holdout` 2 · `temporal split` 0 · `CC BY-SA 4.0` 1 · `results/latest_states.csv` 1 · `추천 제외 범위의 차이` 1 · `거의 같다` 0.

## Task 4 — EVAL-07 `evaluation/figures.py` (수행함, 생략 아님)

TDD 3단계:
- **RED:** `tests/evaluation/test_figures.py` 2건 + 아무것도 쓰지 않는 스텁 → `2 failed`, 실패 유형 **`AssertionError: assert False where False = exists()`** (두 테스트 모두).
- **GREEN:** `figures.py` 44줄(≤150) 구현 → `uv run pytest tests/evaluation --no-header` → **20 passed**(Plan 03의 18 + 2).
- **REFACTOR:** 없음(최소 변경 원칙 — 이번 브리프가 만든 파일 안에서도 정리할 것이 없었다).

`evaluation/__init__.py`에 `plot_eval_bar` 추가 → `__all__` **13개**. `matplotlib.use("Agg")`가 `import matplotlib.pyplot`보다 앞(헤드리스). 컬럼 상수는 `report.py`에서 import(재정의 없음).

실제 그림: `uv run python -c "from millie_rec.evaluation import plot_eval_bar; print(plot_eval_bar())"` → `report/figures/eval_bar.png`, **38,767 바이트**(>10KB), PNG 시그니처 확인. `git status`에 나타남(`.gitignore` 예외 `!report/figures/*.png` 동작 확인). 그림의 시각적 판단은 Advisor(사람) 몫.

`uv run pytest tests/test_architecture.py --no-header` → **3 passed**(star 의존 위반 없음).

## Deviations from Plan

### 자동 처리 없음 — 계획대로 실행됨

코드 결함 발견 0건, Rule 1~4 발동 0건. 다만 **플랜의 수용 기준 수치 2개가 미커밋 작업 트리 때문에 다르게 측정**되어 기록한다(코드 변경이 아니라 측정 맥락 차이):

1. **`git diff --numstat report/draft.md`가 `2\t1`이 아니라 `3\t1`.** `draft.md`는 HEAD 기준으로 이미 Phase 1의 bullet 1줄이 미커밋 상태(`1\t0`)였고, 여기에 이번 변경(+2/−1)이 얹혔다. 이번 플랜의 순수 기여는 정확히 **추가 2줄·삭제 1줄**이다.
2. **`git diff --numstat src/millie_rec/data/goodbooks.py`가 빈 출력.** 파일이 아직 untracked(`??`)라 diff 대상이 아니다. 삭제된 기존 태그는 0개임을 파일 내용으로 확인했다.

### Deferred Issues
없음.

## Threat Flags
없음 — 이 플랜은 새 네트워크 엔드포인트·인증 경로·스키마를 만들지 않았다(`figures.py`는 로컬 파일 읽기/쓰기, 서버에 노출되지 않음). 등록된 위협 T-02-30~36의 mitigate 항목은 전부 수용 기준으로 확인됨(HTTPS 상수 URL·규모 sanity·멱등 2회차 네트워크 0·숫자 csv 복사 검증·NOISE_TAGS 근거 기록).

## Known Stubs
없음. `figures.py` RED 단계의 스텁은 GREEN에서 완전히 대체됐다.

## 변경 파일 목록 (`git status --short`, `.planning/` 제외)

**커밋 대상(미커밋, 승인 대기):**
```
 M report/draft.md
 M src/millie_rec/evaluation/__init__.py
?? artifacts/serving/eval_table.json
?? report/figures/eval_bar.png
?? results/eval_20260905_0626.json
?? results/latest.csv
?? results/latest_states.csv
?? src/millie_rec/evaluation/figures.py
?? tests/evaluation/test_figures.py
   (+ src/millie_rec/data/goodbooks.py — 이번 플랜에서 NOISE_TAGS 2개 보충, Plan 01 산출물로 미커밋)
```

**gitignore(추적 안 함, 의도대로 `git status`에 나타나지 않음):**
```
data/raw/goodbooks/{ratings,books,book_tags,tags}.csv   (총 ≈92MB)
data/processed/{interactions,books}.parquet             (21.3MB / 1.5MB)
artifacts/popularity.json                               (items 1,000개)
```

**커밋하지 않는다 — 작업 트리에 남기고 SUMMARY에 변경 파일 목록을 적는다. `results/`·`eval_table.json`·png 커밋은 사용자 승인 후 Advisor가 한다**(`no_commit: true`, 결정 'Phase 1 실행 방식'(`../.assets/개발일지/2026-09-05_Day1_GSD_초기화와_계약_freeze.md` 항목 D55)). `git log --oneline | head -1`은 `8e5172b`로 불변.

## Requirements 달성

| ID | 증거 |
|---|---|
| EVAL-01 | `make data` 15.2s 다운로드 + 2.3s 멱등 재실행, 2 parquet |
| EVAL-02 | `eval_*.json`·`latest.csv`·`draft.md` 모두 `split_mode=holdout`, `temporal split` 표기 0건 |
| EVAL-05 | `results/latest.csv` `pop` 1행 + `eval_*.json`(seed 42·git_sha 8e5172b) — ROADMAP Success Criterion 1 |
| EVAL-06 | `latest_states.csv` `pop,n0,…,2000` + `pop,n20,…,1990` — ROADMAP Success Criterion 4 |
| EVAL-07 | `report/figures/eval_bar.png` 38,767 바이트 + 테스트 2건 |
| ROADMAP SC 5 | `/api/recommend?seeds=1,2,3&k=5` → `fallback_level=0`·`pop_v1`, `make smoke` PASS, 171 passed |

## Self-Check: PASSED

- 파일 존재: `results/latest.csv` · `results/latest_states.csv` · `results/eval_20260905_0626.json` · `artifacts/serving/eval_table.json` · `artifacts/popularity.json` · `data/processed/{interactions,books}.parquet` · `data/raw/goodbooks/` 4개 CSV · `src/millie_rec/evaluation/figures.py` · `tests/evaluation/test_figures.py` · `report/figures/eval_bar.png` — 전부 FOUND
- 커밋 해시: **해당 없음 (no commit — 사용자 승인 대기)**. `git log` HEAD `8e5172b` 불변으로 커밋 0건 확인
- 최종 게이트: `uv run pytest --no-header` 171 passed / 2 skipped / 0 failed · `uv run ruff format --check .` + `ruff check .` 클린 · `make smoke: PASS`
