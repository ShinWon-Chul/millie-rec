# Plan 03-07 SUMMARY — popularity_kr 연령×성별 12세그먼트 증분 (DATA-08 Should)

Phase 3 '밀리 카탈로그 빌드'(.planning/ROADMAP.md "Phase 3: 밀리 카탈로그 빌드") / Plan 07 (DATA-08).
**커밋하지 않는다** — 변경은 작업 트리에만 남겼다(플랜 frontmatter `no_commit: true`, 선례 결정 'D-18 커밋 없음'(.planning/phases/02-track-a/02-CONTEXT.md)). `git log --oneline | head -1` = `8e5172b chore: project scaffold …` 불변.

## 0. 변경 파일 (3개)

| 파일 | 상태 | 내용 |
|---|---|---|
| `scripts/build_millie_popularity.py` | 45 → 77줄 (≤150) | `import json` · `GENDER_LABEL`·`SEGMENT_SEP` 상수 · 새 함수 `segment_rows` · `build` 의 주석 1줄 → concat 3줄 |
| `tests/data/test_millie_popularity.py` | 95 → 178줄 | `import re` 1줄 삽입 + 세그먼트 테스트 5건 **추가만** |
| `artifacts/serving/popularity_kr.json` | 575KB → 7,119.5KB | `make millie-popularity && make millie-export` 재실행 결과(내용 변경 — md5 §5) |

`data/processed/popularity_kr.parquet`(gitignore) 도 재생성됐다. `Makefile` 은 **실행만** 했다(편집 0).

## 1. Task 1 RED — `uv run python --version` = 3.11.6

`segment_rows` 부재로 3건이 `AttributeError: module 'build_millie_popularity' has no attribute 'segment_rows'` 를 먼저 냈다. 플랜 지시대로 스텁 `def segment_rows(books): return pd.DataFrame(columns=list(POP_COLUMNS))` 를 넣어 **전건을 AssertionError 로 전환**한 뒤 다시 찍었다.

```
$ uv run pytest tests/data/test_millie_popularity.py --no-header
__________________ test_segment_rows_labels_are_millie_style ___________________
E       AssertionError: assert set() == {'10대 남성', '1...남성', '40대 여성'}
E         Extra items in the right set: '10대 남성' '40대 남성' '40대 여성' '10대 여성'
___________________ test_segment_score_is_shelf_times_share ____________________
E       AssertionError: ('10대 남성', 2, 0)
E       assert 0 == 1
E        +  where 0 = len(Empty DataFrame\nColumns: [book_id, segment, score, rank]\nIndex: [])
___________ test_segment_rank_is_contiguous_and_can_differ_from_all ____________
E       AssertionError: ('10대 남성', 2, 0)
___________________ test_books_without_seg_dist_only_in_all ____________________
E       assert set() == {1, 2}
E         Extra items in the right set: 1 2
___________________ test_fixture_build_has_all_plus_segments ___________________
E       AssertionError: ('40대 여성', 1, 0)
E       assert 0 == 1
5 failed, 5 passed in 0.15s
```

- 신규 5건 전부 `AssertionError`, 기존 5건 passed.
- **금지 오류 0건**: `grep -cE "ImportError|SyntaxError|AttributeError|ModuleNotFoundError|NameError"` → `0`.

### 손계산 케이스 `_seg_frame()` (3행)
| book | shelf | pop_rank | seg_dist | 의도 |
|---|---|---|---|---|
| 1 | 1000 | 1 | `10대 남10 여10 / 40대 남5 여75` | all 1위 |
| 2 | 900 | 2 | `10대 남50 여40 / 40대 남5 여5` | **'10대 남성' 1위**(45,000 > 10,000) |
| 3 | 800 | 3 | `None` | 세그먼트 행에서 제외 |

'10대 남성' 1위(book 2) ≠ all 1위(book 1) — DATA-08 이 주장하는 "level 2 가 전역 인기와 갈린다" 의 손계산 증거다.

## 2. Task 2 GREEN

```
$ uv run pytest tests/data/test_millie_popularity.py --no-header
..........                                                               [100%]
10 passed in 0.16s

$ uv run pytest tests/data/test_millie_popularity.py tests/data/test_millie_export.py --no-header
18 passed in 0.87s        # export 8건 무수정 통과 — Plan 04 가 all 행 범위로 쓴 덕분

$ uv run pytest --no-header
233 passed, 2 warnings in 2.96s      # 기준선 228 + 신규 5

$ make smoke
smoke: /health 200 · smoke: / (demo static) 200 · smoke: /api/recommend 200 · smoke: PASS

$ uv run ruff format/check scripts/build_millie_popularity.py tests/data/test_millie_popularity.py
2 files left unchanged / All checks passed!
$ uv run ruff check .        → All checks passed!   (전역, format 은 자기 2파일만)
```

| 단언 | 기대 | 실측 |
|---|---|---|
| `wc -l scripts/build_millie_popularity.py` | ≤150 | **77** |
| `grep -c "def segment_rows"` | 1 | 1 |
| `grep -c 'GENDER_LABEL = {"남": "남성", "여": "여성"}'` | 1 | 1 |
| `grep -c "def test_" tests/data/test_millie_popularity.py` | 10 | 10 |
| `find artifacts/serving -size +50M \| wc -l` | 0 | 0 |

## 3. 재빌드·재export 실측

```
$ make millie-popularity && make millie-export
popularity rows=92552 segments=13 → data/processed/popularity_kr.parquet
books_kr.json 7459.2KB · item_edges_kr.json 9943.8KB · popularity_kr.json 7119.5KB
content_vectors_kr.npz 4422.5KB seed=42 · popular.json 18.7KB level=3 fallback_v1
```

검증 블록 출력:
```
segments ok {'10대 남성': 6987, '10대 여성': 6987, '20대 남성': 6987, '20대 여성': 6987,
             '30대 남성': 6987, '30대 여성': 6987, '40대 남성': 6987, '40대 여성': 6987,
             '50대 남성': 6987, '50대 여성': 6987, '60대~ 남성': 6987, '60대~ 여성': 6987,
             'all': 8708}
distinct top-1 across segments: 5
```
- **13종**(all + 12), 라벨 전부 정규식 `^(10대|20대|30대|40대|50대|60대~) (남성|여성)$` 매치, 세그먼트별 rank 1..6987 연속, 행 스키마 4컬럼.
- 세그먼트 행 수 92,552 − 8,708 = **83,844 = 6,987 × 12**. 6,987/8,708 = **0.8024** = `seg_dist` 보유율(게이트 ≥0.70 통과)과 정확히 일치 — 결측 책 1,721권은 all 행에만 있다.

### `distinct top-1` = 5 (Phase 5 참고)
전 세그먼트 1위가 같은 책이 아니다(1 이 아님 = 데이터가 세그먼트별로 갈린다).

| 1위 book_id | 세그먼트 |
|---|---|
| 1004 | `all` · 40대 여성 · 50대 남/여 · 60대~ 남/여 |
| 2843 | 20대 남성 · 30대 남성 · 40대 남성 |
| 2081 | 20대 여성 · 30대 여성 |
| 1151 | 10대 남성 |
| 2204 | 10대 여성 |

**12세그먼트 중 7개의 1위가 `all` 1위(1004)와 다르다.** DATA-08 의 데이터 전제는 실측으로 성립한다. 다만 이것은 데이터 성질이지 응답 검증이 아니다(§6).

## 4. 기존 단정 범위 축소 — **하지 않았다(0곳)**

플랜 Task 1 "주의" 절이 대비한 상황은 발생하지 않았다. Plan 04 가 이미 헬퍼 `_all_rows(pop)`(주석 "단정은 segment == 'all' 행 위에서만 — Plan 07 세그먼트 행이 붙어도 안 바뀐다")를 두고 5건 전부 그 범위로 썼기 때문에, 이 플랜은 **순수 증분**이다. 기존 5건의 단정은 한 줄도 수정·삭제하지 않았고 `tests/data/test_millie_export.py` 도 must_not_touch 그대로다(무수정 8건 통과).

주의: `git diff tests/data/test_millie_popularity.py | grep "^-" | grep -c "assert"` 는 `0` 이지만 이 파일은 아직 **untracked(`??`)** 라 `git diff` 가 원래 비어 있다 — 위 acceptance 는 그 명령이 아니라 "Plan 04 가 `_all_rows` 범위로 썼다" 는 사실이 근거다. 내 편집은 ① 임포트 블록에 `import re` 1줄 삽입(isort 순서 `importlib.util` → `re` → `sys`) ② 파일 끝에 5건 추가, 둘뿐이다.

## 5. md5 전후 비교 — popularity_kr.json 만 변경

`make millie-export` 는 books·edges·vectors·fallback 도 같은 입력으로 다시 쓰므로 멱등성을 md5 로 확인했다.

```
$ diff md5.before md5.after
4c4
< MD5 (artifacts/serving/popularity_kr.json) = 9338edf8de595f8c50d6219841eacf39
---
> MD5 (artifacts/serving/popularity_kr.json) = 48ea45a9dcd21392aea9e716d40f9b87
```
`books_kr.json` · `item_edges_kr.json` · `content_vectors_kr.npz`(SVD `random_state=SEED` 라 바이트 동일) · `eval_table.json` · `demo/fallback/popular.json` **5개 md5 동일**. `results/` 는 이 플랜이 건드리지 않는다(git status 변동 없음).

`git status --short` 에서 `demo/fallback/popular.json` 이 ` M` 으로 보이지만 이는 **내 실행 이전부터 미커밋 상태**였던 것이고(브리프 §6 이 예고), md5 가 전후 동일하므로 이 플랜의 변경이 아니다.

## 6. 판단 지점

1. **`GENDER_LABEL` 은 변환 테이블이 아니다.** 밀리 원본 `seg_dist` 키는 `남`·`여` 인데 같은 원본의 `top_segment` 는 `"40대 여성"` 이라 쓴다 — 즉 2항목 상수는 새 분류 체계를 만드는 게 아니라 **같은 원본의 두 표기를 일치시키는 것**이다(`.planning/phases/03-millie-catalog/03-CONTEXT.md` "변환 테이블 없음" 과 충돌하지 않음). 폐기된 카테고리 매핑표(화면 설계 01 §8)와는 성격이 다르다.
2. **플랜의 테스트 4를 한 줄 강화했다.** 플랜 초안대로면 `assert 3 not in set(세그먼트 행 book_id)` 가 세그먼트 행이 **하나도 없을 때 공허하게 통과**해 Red 가 되지 않는다. `assert set(seg_only["book_id"]) == {1, 2}` 를 앞에 넣어 실패하게 만들었다(단정 추가, 완화 아님). RED 출력 `assert set() == {1, 2}` 가 그 증거다.
3. **`build()` 최소 변경 준수.** all 프레임 계산·정렬·값은 그대로 두고 `all_rows` 변수로 받아 concat 만 붙였다. `build()`/parquet 에서는 all 행이 앞에 온다. 단 `artifacts/serving/popularity_kr.json` 은 `export_millie_serving.popularity_payload` 가 `sort_values(["segment","rank"])` 로 다시 정렬하므로 **세그먼트 라벨 사전순**이다(`"10대 남성"` < `"all"`) — 파일 첫 행이 all 이 아니다. 소비자는 순서가 아니라 `segment` 필드로 조회해야 한다(Phase 5 주의).
4. **`json.loads` 실패를 삼키지 않았다**(T-03-30) — 손상된 seg_dist 는 빌드 단계에서 예외로 드러난다. 가드는 결측(`None`·비문자열·빈 문자열)에만 건다.
5. **`share` 는 내보내지 않는다**(T-03-29) — 행은 `score`(shelf×share)·`rank` 4컬럼뿐이고 `seg_dist` 원본 json 은 export 화이트리스트에서 계속 제외다.

## 7. Phase 5 '서빙 Must 완성' 인계

- `artifacts/serving/popularity_kr.json` 은 이제 `all` 8,708행 + 12세그먼트 각 6,987행이다. fallback level 2 는 `segment` 필드를 **라벨 문자열**(`"40대 여성"`)로 조회한다 — 연령 키 6종 × `남성|여성`, 구분자는 공백 1칸.
- **level 2 응답이 전역 인기와 다른지 검증하는 것은 이 플랜의 완료 기준이 아니다**(결정 D-15). `serving/state.py`·`fallback.py` 가 생긴 뒤 Phase 5 에서 판정한다. 이 플랜이 넘기는 것은 §3 의 데이터 전제(12세그먼트 중 7개의 1위가 all 과 다름)까지다.
- `similar_readers` 행이 이 세그먼트 인기를 쓰면 제목은 **"또래 독자들이 많이 담은 책"** 이다. "비슷한 취향 독자" 문구는 금지(유저 유사도가 없다 — `../.claude/rules/data.md` 행 소스 분리).
- 온보딩 화면의 연령·성별 **입력**은 Phase 6 '데모 재구성' 몫이다.
- `seg_dist` 결측 1,721권(19.76%)은 어떤 세그먼트 행에도 없다 — level 2 가 세그먼트 인기만으로 응답하면 이 책들은 후보에서 빠진다. Phase 5 가 all 행과 섞을지 결정해야 한다.
