---
phase: 04-freeze
plan: 05
status: complete
executed_by: Advisor(오케스트레이터 세션 직접 — app/·Makefile·results·report 는 Advisor 영역)
executed_at: 2026-09-06
commits: 0   # no_commit — 작업 트리에 남긴다(사용자 지시 2026-09-05)
requirements: [REC-02, REC-05, REC-07]
key-files:
  created:
    - src/millie_rec/app/demo_cli.py
    - tests/app/test_demo_cli.py
    - results/eval_20260905_1514.json
    - artifacts/item_neighbors.npz
  modified:
    - src/millie_rec/app/cli.py
    - Makefile
    - results/latest.csv
    - results/latest_states.csv
    - artifacts/serving/eval_table.json
    - artifacts/popularity.json
    - report/figures/eval_bar.png
    - report/draft.md
---

# Plan 04-05 SUMMARY — Track A 실측 4행 · D-07 게이트 · cli demo 도우미 · draft §4-1

## 한 줄
`make eval` 1회(1분 49초)로 4 variant × 2 상태 8행 실측을 얻었고 D-07 게이트·기대 관계 3개가 **초기 상수 그대로 전부 성립**해 λ·W 튜닝 재실행이 없었다. `cli demo --find/--seeds` + `make demo` 리다이렉트 완성, draft §4-1 표·해석 문단·`[Phase 4]` 마커 0. 전역 325 passed, smoke PASS, 커밋 0.

## Task 2 (Advisor 실측) — `results/latest.csv` (Goodbooks-10k · holdout · n=2,000 · seed 42)
| variant | Recall@20 | NDCG@10 | ILD@10 |
|---|---:|---:|---:|
| pop | 0.063 | 0.054 | 0.764 |
| cf | 0.117 | 0.107 | 0.643 |
| hybrid | 0.118 | 0.110 | 0.606 |
| hybrid_div | 0.116 | 0.107 | 0.684 |

`results/latest_states.csv` n≥20(n=1,990): pop 0.080/0.087/0.746 · cf 0.207/0.237/0.738 · hybrid 0.204/0.240/0.717 · hybrid_div 0.205/0.238/0.780.

**판정(2-c 스크립트):** `D-07 gate: True`(ILD 0.606→0.684 ↑ ∧ NDCG 0.107 ≥ 0.8×0.110) · `recall(cf)>pop: True`(0.117 > 0.063) · `ndcg(hybrid)>=cf: True`(0.110 ≥ 0.107). → 튜닝 0회. **채택 상수(freeze 후보) = `W_CF, W_CONTENT, W_POP = 0.5, 0.3, 0.2` · `LAMBDA_MMR = 0.7`** (코드 줄 grep 일치).

| 실행 파일 | 상수 | 채택 |
|---|---|---|
| `results/eval_20260905_0626.json` | Phase 2 pop 1행 기준선 | 이전 |
| `results/eval_20260905_1514.json` | W 0.5/0.3/0.2 · λ 0.7 | **채택(최종)** |

그림 `report/figures/eval_bar.png` 50,579B 갱신 · `artifacts/serving/eval_table.json` rows `['pop','cf','hybrid','hybrid_div']` · `artifacts/item_neighbors.npz` 6.1MB(gitignore 확인) · `artifacts/popularity.json` 갱신.

## Task 1 — `cli demo` (TDD)
RED: 서브파서 뼈대(`print("")`) 후 `uv run pytest tests/app/test_demo_cli.py` → `AssertionError` 3건(`'| book_id | 제목 | 저자 | 분야 |' in '\n'` · `0 == 5` · 고정 문장 부재), 2건은 SystemExit 경로라 통과. GREEN: 5 passed. `demo_cli.py` 149줄 · `cli.py` 135줄 · `open(`/`write_text`/`report/` 0건(stdout 만) · `GUARD_RESID_Z`·`GUARD_MIN_COMPLETED` 는 reranking 공개 상수 import. `Makefile demo` → `> report/demo_5books.md`.

실 카탈로그 동작 확인(재빌드 전 스냅샷 — **판정 아님, PDF 사용 금지**): `--find 위버멘쉬` → `| 1446 | 위버멘쉬 | 프리드리히 니체 / 어나니머스 옮김 | 철학 |`; `--seeds 1446,1004,2081,2843,1060` → 앵커 표 5 + hybrid_div 표 1 + `alpha=1.0 beta=0.0 gamma=0.0 · 가드 활성(n_completed=0<3) · … 0권` + 고정 문장. 이웃에 배지 제목(『읽던 지점 그대로 이어듣기』『도슨트북』『무료』)이 노출 → STATE Blockers(배지 제목 728건) 그대로이며 최종 `make millie` 뒤 Plan 04-06 에서만 판정한다.

## Task 3 — `report/draft.md`
§4-1 표 8행(csv 문자 단위 일치 검사 `mismatch []`) · 해석 문단(evaluation.md 템플릿: "MMR 적용으로 NDCG@10은 0.110→0.107 … ILD@10은 0.606→0.684" + "hybrid는 n≥20(α 하한 0.2 근방, β가 대부분)에서 pop 대비 NDCG@10 격차를 0.153") · 측정 설계 마커 제거 + "조정 없이 freeze"·"실측 통과: ILD +0.078, NDCG −2.7%" · 각주 freeze 상수 1구 · §2-2·§5-2 마커 제거 · §5-2 "설계만(ablation 계획)" 1구. `[Phase 4]` 0 · `[Phase 3~4]`·`[Phase 4~8]` 2 불변.

## 전역 게이트
`uv run ruff format --check . && uv run ruff check .` 클린 · `uv run pytest --no-header` **325 passed, 1 failed**(`test_coverage_gate` 만) · `make smoke` PASS · `results/eval_*.json` 2개(≤4).

## Plan 04-06 인계(사용자 게이트)
1. 재수집은 종료됨(`pgrep -f collect_millie` 빈 출력, 2026-09-06 00:0x 확인). **최종 `make millie` 1회는 아직 미실행** — 실행 전 STATE Blockers 절차(JSONL md5 불변 → `badge_title_remaining` 점검 → `id_map.csv` 백업 → `time make millie` → 게이트 `_n_badge_title,0` → 233+ 테스트 → smoke) 를 따른다.
2. 사용자 5권 제목 → `uv run python -m millie_rec.app.cli demo --find <제목 일부>` 로 book_id 확인 → `make demo SEEDS=a,b,c,d,e` 1회 → `report/demo_5books.md`.
3. 서버 4 variant 판정(최종 스냅샷): `GET /api/recommend?model=<v>&seeds=<5권>&k=10` 4종 상위 10 상이 + 배지 제목 0.

커밋하지 않는다 — 작업 트리에 남기고 SUMMARY 에 변경 파일 목록을 적는다.
