---
phase: 03-millie-catalog
plan: 06
subsystem: app
tags: [assembly, catalog-injection, makefile, make-millie, level0]
requires:
  - phase: 03-millie-catalog
    provides: "Plan 01~05 — 빌더·어댑터·이웃·export 스크립트"
provides:
  - "app/pipeline.py CatalogPopPipeline · load_catalog · build_pipelines(catalog=) 하위 호환"
  - "app/server.py 카탈로그 조건부 주입(catalog·neighbors·book_stats·fallback)"
  - "Makefile millie-build(커버리지 게이트)·millie-edges(이웃 게이트)·millie-popularity·millie-export(3스크립트)·millie 체인"
  - "artifacts/serving/ 4파일 + demo/fallback/popular.json (8,708권 스냅샷, 09-05 20:28)"
affects: ["03-07 popularity 세그먼트", "Phase 4 hybrid_div(VectorsKR)·난이도 가드(stats)", "Phase 5 compose·level 1/2", "Phase 6 데모 재구성"]
tech-stack:
  added: []
  patterns:
    - "CatalogKR 하나가 Catalog·Neighbors·BookStatsSource 를 만족 → create_app 세 인자에 같은 객체(structural typing)"
    - "서버 기동 시 load_catalog() 1회 — 없으면 None(Phase 2 동작), 손상은 log.exception 후 None"
key-files:
  created:
    - tests/app/test_server_catalog.py
    - artifacts/serving/books_kr.json
    - artifacts/serving/item_edges_kr.json
    - artifacts/serving/popularity_kr.json
    - artifacts/serving/content_vectors_kr.npz
  modified:
    - src/millie_rec/app/pipeline.py
    - src/millie_rec/app/server.py
    - tests/app/test_pipeline.py
    - tests/serving/test_smoke.py
    - Makefile
    - demo/fallback/popular.json
    - data/id_map.csv
    - results/millie_coverage.csv
    - results/millie_edges_gate.json
    - report/draft.md
    - ../.assets/설계서/데이터 소스/03_밀리_데이터_적재_트래킹.md
    - ../.assets/개발일지/2026-09-05_Day1_GSD_초기화와_계약_freeze.md
key-decisions:
  - "결정 D-13 '서버 pop 을 Track B 인기로 교체'(.planning/phases/03-millie-catalog/03-CONTEXT.md): catalog 가 있으면 Goodbooks artifacts/popularity.json 을 열지 않는다(테스트 ERROR 로그 0건으로 증명)"
  - "Makefile 게이트 순서: 이웃 게이트를 millie-edges 뒤로(plan-checker BLOCKER — build 직후 tests/data 전체는 stale edges 로 깨짐)"
status: complete   # Task 4 최종 스냅샷 재빌드 2026-09-06 00:32 완료(Phase 4 04-06 게이트에서 실행)
commits: 0
---

# Plan 03-06 SUMMARY — 조립·실측·기록 (Task 1~3 완료, Task 4 체크포인트)

**커밋하지 않았다.** 커밋 대상(사용자 승인 후 Advisor): `artifacts/serving/` 4파일 · `demo/fallback/popular.json` · `results/millie_coverage.csv`·`millie_edges_gate.json` · `data/id_map.csv` · `Makefile` · `src/millie_rec/app/*` · `tests/app/*` · `tests/serving/test_smoke.py`.

## Task 1 — app/ 카탈로그 주입 (D-13), Advisor 직접 TDD

RED(스텁 위, `uv run pytest tests/app --no-header`):
```
E       AssertionError: assert set() == {'pop'}
E       assert False  +  where False = any(<generator …>)            # load_catalog INFO 로그
E       assert False  +  where False = isinstance(None, CatalogKR)
E       assert [4, 17, 5, 20, 18] == [4, 5, 6, 7, 8]                 # 서버가 Goodbooks pop 을 씀
E       assert [] == [1, 2, 3, 4, 5]                                  # 익명 trending 비어 있음
5 failed, 8 passed in 1.44s
```
GREEN: `uv run pytest tests/app tests/serving tests/test_architecture.py --no-header` → **37 passed**. ruff 클린. `pipeline.py` 110줄 · `server.py` 23줄.
- `CatalogPopPipeline(name='pop')`: `popular(n=k+len(seen))` → seen 제외 → `meta` 조인(title·authors·image_url·book_format·difficulty). `load_catalog(serving_dir=DIR_SERVING) -> CatalogKR | None`. `build_pipelines(artifact, *, catalog=None)` — 기존 4건 무수정 통과(하위 호환).
- `server.py`: `catalog = load_catalog()` → `create_app(pipelines=build_pipelines(catalog=catalog), fallback=GlobalPopularFallback(catalog), catalog=catalog, db=…, neighbors=catalog, book_stats=catalog)`. `app.mount` 는 마지막 문장.
- `tests/serving/test_smoke.py` 배선 2곳: `lambda: {…}` → `lambda **_: {…}` + `load_catalog` 를 `lambda: None` 으로 패치(주석 "Phase 3: 실 artifacts 유무와 무관"). 단정 문장 무수정.
- `tests/app/test_server_catalog.py` 2건(fixture 20권): level 0 `pop_v1`·`[4,5,6,7,8]`·"밀리 표본 도서 4" / 익명 level 3 `fallback_v1`·`items == []`·trending 앞 5 = `[1..5]`·18·19·20 없음.

## Task 2 — Makefile · `make millie` 실측 · 검증

Makefile: `millie-build`(카탈로그 게이트만) · `millie-edges`(+ 이웃 게이트) · `millie-popularity`(신설) · `millie-export`(serving → vectors → fallback) · `millie` 체인. `pytest tests/data -q` 문자열 제거.

`time make millie`(09-05 20:28, 배치 진행 중):
```
books=8708 → data/processed/books_kr.parquet · id_map → data/id_map.csv empty=31 titleless=1
18 passed in 0.25s
edges=323223 {'category_best': 164677, 'content_sim': 158546} → data/processed/item_edges_kr.parquet
11 passed in 2.30s
popularity rows=8708 segments=1 → data/processed/popularity_kr.parquet
books_kr.json 7459.2KB · item_edges_kr.json 9943.8KB · popularity_kr.json 575.4KB
content_vectors_kr.npz 4422.5KB seed=42 · popular.json 18.7KB level=3 fallback_v1
make millie  35.29s user 6.46s system 109% cpu 37.978 total
```
검증(2-c): `find artifacts/serving -size +50M` 0 · `"description"`·`"curator_note"`·`"seg_dist"` 0건 · `git diff --numstat data/id_map.csv` = `7644 0` · 빌드 전 사본(6,980줄 = HEAD 1,067 + Plan 01 append)이 새 파일의 접두로 바이트 동일(8,711줄) · 계약 9키 ⊂ 28키 · `book_format` ⊂ {전자책, 오디오북, 챗북} · `RecommendOut.model_validate(popular.json)` 통과(level 3 · `fallback_v1` · trending 40권) · npz `(8708, 128)` float32 · `popularity_kr.json` 4키·segment {all}.

`results/millie_coverage.csv`: title 1.0000 · image_url 1.0000 · categories 1.0000 · completion_prob 0.8385 · formats 0.9773 · seg_dist 0.8024 · average_rating 0.2603 · `_n_records` 8708 · `_category_distinct` 74 · `_categories_ge_20` 25 · `_n_skipped_empty` 31 · `_n_skipped_titleless` 1 · `_n_success` 8740 — 미달 0.
`results/millie_edges_gate.json`: n_books 8708 · n_edges 323223 · self_edges 0 · min_degree 21 · n_orphans 0 · same_category_share **0.3662**.

전역 게이트(2-d): `uv run ruff format --check . && uv run ruff check .` 클린 · `uv run pytest --no-header` → **228 passed, skipped 0** · `make smoke` → `smoke: PASS`.

level 0 curl(2-e, 포트 8012, 기동 ≈1s):
```
0 pop_v1 [1004, 2081, 2843, 1060, 4320] trending 5
['불편한 편의점', '도슨트북', '무료', '도슨트북', '홍학의 자리']   → 한글 제목 5/5, {1,2,3} 제외
3 fallback_v1 0 40 1004 None                                          → 익명 level 3, trending 40권(카탈로그 인기)
health ok None
```
contract-sync 카탈로그 항목(2-f, 인라인): 계약 9키 존재 · description/curator_note 0 · book_format 값 · id_map 삭제 0 · popular.json RecommendOut 통과 · `grep -c itemknn demo/fallback/popular.json` 0 · `"fallback_v1"` 1.

## Task 3 — 기록
- `report/draft.md` 3-3 절 표 아래 P3 실측 bullet 1개(8,708권 · 표지 100.0% · 완독지수 83.9% · 동일 카테고리 0.366 · SVD 128 · `[숫자는 Day 2 오전 최종 스냅샷 재빌드 후 교체]`).
- 트래킹 03 §1 단계 4~7 ✅ + 수치 · §2 표 `—` 5셀 채움 · §3 로그 1행(첫 스냅샷 → 재빌드) · §4 `make millie` 1줄.
- 개발일지 `2026-09-05_Day1_…md` **D66**(6요소 8줄, 약호 단독 0). D62 중복은 이미 D64 로 정정돼 있음(보고만).
- `../.claude/rules/data.md`: D-08 문구 1 · `*.millie.co.kr` 1 · 구 문구 0 → 이미 반영, 편집 0.

## 관측 (수정하지 않음 — 후속 페이즈 인계)
1. **익명 level 3 응답의 items `title` 이 None** — serving `GlobalPopularFallback` 이 meta 조인을 안 한다(Phase 1 설계). 정적 `popular.json` 은 제목 포함. Phase 5 compose/fallback 몫(`serving/**` must_not_touch).
2. level 0 상위 5 에 `'도슨트북'` 제목이 2권(다른 book_id, 같은 제목) · `'무료'` 라는 제목의 책이 3위 — 제목 중복·플레이스홀더성 도서. `eligible()` 규칙(D-14)엔 안 걸린다. Phase 5 dedup·Phase 6 화면 확인 때 검토(데이터 품질 메모).
3. `/health.model_version` 은 pop 주입 후에도 None(Phase 5 연기 항목, 기존 고민 포인트).
4. 이웃 빌드 peak RSS 1.24GB @6,977권(03-03 실측) — 8,708권 재빌드는 성공(≈10s). 9천 권 초과 시 `sim.astype(np.float32)` 최소 변경 검토(Task 4 전).
5. `_category_distinct` 28 → 74 로 급증(배치 확장으로 소분류 유입). 20권 이상 분야 25 — 게이트(≥6) 여유.
6. Phase 6 인계: `demo/js/inspector.js` `"static_popular"` 라벨 → `fallback_v1` · `latency_ms` float 화로 막대 비어도 크래시 없음 · **`make mock` 실행 금지**(`make_mock.py` 가 v1 popular.json 을 덮어씀).
7. Phase 4 인계: `VectorsKR`(`content_vectors_kr.npz`)·`CatalogKR.neighbors`·`stats` 는 이미 주입 표면에 있음(`neighbors=`·`book_stats=`) — `hybrid_div` 는 `app/` 에서 `VectorsKR.load()` 로 소비.

## CHECKPOINT REACHED — Task 4 최종 스냅샷 재빌드 (사람 게이트)
- 진입 조건: `pgrep -f collect_millie` 가 비거나(배치 자연 종료) **Day 2(09-06) 오전 사용자 승인 후 `pkill -f collect_millie`**(D-03). 20:31 현재 배치 2샤드 진행 중(jsonl 8,810줄 · discovered 8,681줄).
- 절차(Task 4-b~4-e): 프론티어 수 기록 → `cp data/id_map.csv <scratch>/id_map.final_before.csv` → `make millie` → 2-c·2-d·2-e 재검증 → draft `[숫자는 … 교체]` 마커 제거·트래킹 §2 최종 행·D66 결과 줄 추가 → 이후 `make millie` 재실행 금지(Day 3 freeze).
- 이 플랜은 Task 4 전까지 **부분 완료**(플랜 verification 절).


## Task 4 완료 — 최종 스냅샷 재빌드(2026-09-06 00:31~32, Phase 4 04-06 Task 1 사용자 승인 후 실행)
- 진입: `pgrep -f collect_millie` 빈 출력 · 재수집 로그 2개 SUMMARY(수집 453+443=896, 실패 0) · JSONL 10,482줄(고유 9,580).
- 프론티어(4-b): discovered 8,929 + sitemap 1,000 → 알려진 id 9,580 전량 수집 → 미수집 프론티어 0.
- 재빌드(4-c): `cp data/id_map.csv <scratch>/id_map.final_before.csv` → `time make millie` 37s → `_n_records 9447 · _n_badge_title 0 · titleless 4 · empty 129` · 이웃 게이트 통과(엣지 350,080·동일 카테고리 0.3564·orphan 0) · 벡터 9,447 = 책 수 · id_map 접두 diff 빈 출력(9,453행, 삭제 0) · `uv run pytest --no-header` 327 passed(`test_coverage_gate` 통과) · `make smoke` PASS · 서버 level 0 4 variant 배지 제목 0(04-06 SUMMARY).
- 수치 교체(4-d): `report/draft.md` P3 문장 8,708→9,447·완독지수 83.9%→82.5%·동일 카테고리 0.366→0.356, 마커 제거 · 트래킹 03 §2 '최종 스냅샷' 행 · 개발일지 D66 결과 줄.
- freeze(4-e): 이후 `make millie*` 재실행 금지(Phase 4 D-14 ③, 개발일지 D72). 커밋 없음.
