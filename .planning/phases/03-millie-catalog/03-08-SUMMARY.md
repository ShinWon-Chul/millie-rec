---
phase: 03-millie-catalog
plan: 08
status: partial
subsystem: data
tags: [parser, badge-title, coverage-gate, recollect, tdd]
scope: "Task 1·2 완료 · CHECKPOINT(배치 중단 승인)·Task 3(재수집·최종 스냅샷) 미시작 — 사람 게이트, Advisor 몫"
requires:
  - phase: 03-millie-catalog
    provides: "Plan 01 빌더(read_records·coverage) · Plan 06 make millie 체인"
provides:
  - "millie_parse._NAV_NOISE ⊇ 기능 배지 라벨 7종 + _NAV_NOISE_RE(^종료 D-N$) — 헤더 첫 줄 배지에서 title·subtitle 복구"
  - "파서 회귀 픽스처 2건(badge_docent·badge_free_chatbook) — 실페이지 축약, 리뷰·필명 0"
  - "build_millie_catalog.BADGE_TITLES·BADGE_TITLE_RE·is_badge_title() · coverage()['n_badge_title']·['badge_titles']"
  - "커버리지 게이트가 results/millie_coverage.csv 에 _n_badge_title 행 기록(단언은 Task 3-b0 Advisor)"
  - "scripts/millie_recollect_list.py — JSONL 최신 줄 기준 재수집 대상 TSV"
  - "collect_millie.py --recollect / collect(only=) — 멱등 skip 우회·sitemap 미조회·확장 없음, 예절 루프 무변경"
affects: ["03-08 Task 3 재수집·최종 스냅샷", "Phase 4 TF-IDF 입력(title+description)", "Phase 6 데모 화면 제목"]
tech-stack:
  added: []
  patterns:
    - "배지 라벨 값을 millie_parse·build_millie_catalog·테스트 세 곳에 중복 정의하고 drift 테스트로 묶는다(scripts 간 import 함정 회피)"
    - "collect(only=None) 기본값 keyword — only 가 None 이면 기존 분기와 동일 경로(도는 배치의 재시작 경로 불변)"
key-files:
  created:
    - tests/fixtures/millie/badge_docent.txt
    - tests/fixtures/millie/badge_free_chatbook.txt
    - tests/data/test_millie_recollect.py
    - scripts/millie_recollect_list.py
  modified:
    - scripts/millie_parse.py
    - scripts/build_millie_catalog.py
    - scripts/collect_millie.py
    - tests/data/test_millie_parse.py
    - tests/data/test_millie_catalog.py
no_commit: true
---

# Plan 08 (부분) — 카탈로그 title 배지 오염 수정: 파서 TDD · 게이트 기록 · 재수집 수단

`.planning/phases/03-millie-catalog/03-UAT.md` Test 9 이슈(카탈로그 title 이 밀리 기능 배지 라벨) 중
**Task 1(파서 수정)·Task 2(게이트 강화 + 재수집 수단)만** 수행했다.
CHECKPOINT(배치 중단·최종 스냅샷 확정 승인)와 Task 3(재수집·`make millie`·수치 교체)은 **시작하지 않았다** —
결정 D-03 의 사람 게이트이고 lane 이 Advisor 다. **커밋하지 않았다**(플랜 `no_commit: true`).

## 변경 파일 (순증)

| 경로 | 상태 | 순증 |
|---|---|---|
| `scripts/millie_parse.py` | M | +8 / −3 (270 → 275줄) |
| `scripts/build_millie_catalog.py` | M | +12 / −0 (301 → 313줄) |
| `scripts/collect_millie.py` | M | +33 / −10 = 순증 23 (294 → 317줄) |
| `scripts/millie_recollect_list.py` | NEW | 46줄 |
| `tests/fixtures/millie/badge_docent.txt` | NEW | 1,426 bytes |
| `tests/fixtures/millie/badge_free_chatbook.txt` | NEW | 1,340 bytes |
| `tests/data/test_millie_parse.py` | M | +62 / −0 |
| `tests/data/test_millie_catalog.py` | M | +71 / −0 |
| `tests/data/test_millie_recollect.py` | NEW | 4건 |
| `results/millie_coverage.csv` | 게이트 재실행 산출 | `_n_badge_title,896` 행 추가 |

## Task 1 — RED

```
E       AssertionError: assert '도슨트북' == '12가지 인생의 법칙 ...부 기념 스페셜 에디션)'
E       AssertionError: assert '무료' == '따박따박 경제상식 [ETF 첫걸음]'
E       AssertionError: assert '종료 D-4' == '12가지 인생의 법칙 ...부 기념 스페셜 에디션)'
FAILED tests/data/test_millie_parse.py::test_core_fields[badge_docent]
FAILED tests/data/test_millie_parse.py::test_core_fields[badge_free_chatbook]
FAILED tests/data/test_millie_parse.py::test_badge_header_lines_are_not_title[badge_docent-…]
FAILED tests/data/test_millie_parse.py::test_badge_header_lines_are_not_title[badge_free_chatbook-…]
FAILED tests/data/test_millie_parse.py::test_countdown_badge_line_is_not_title
5 failed, 76 passed in 0.09s
```

collection error·ImportError 0. 전부 `AssertionError`.

## Task 1 — GREEN

`_NAV_NOISE` 에 실측 7종(`읽던 지점 그대로 이어듣기|도슨트북|무료|오브제북|웹소설|웹툰|오디오웹소설`)을 `| _set(...)` 로 합치고,
`_NAV_NOISE_RE = re.compile(r"^종료 D-\d+$")` 추가, `_header` 의 선행 스킵 while 조건 한 줄만 확장.
`_formats`·`_best`·`_BEST_NOISE` diff 0.

```
uv run pytest tests/data/test_millie_parse.py --no-header
81 passed in 0.03s
```

## Task 2 — RED

```
E       AssertionError: assert None == 2
E        +  where None = {...'n_records': 14, ...}.get('n_badge_title')
E       AssertionError: assert set() == {'도슨트북', '무료'...설', '웹툰', ...}
E       AssertionError: assert [] == [('a', 'recol...d', 'best:y')]
E       AssertionError: assert False   # out.exists()  (millie_recollect_list.main 스텁)
E       AssertionError: assert {} == {'aaaa': 'bes...: 'recollect'}
E       assert 'only' in mappingproxy(OrderedDict([('limit', …), ('expand', …), ('shard', …)]))
FAILED tests/data/test_millie_catalog.py::test_raw_coverage_counts_badge_titles_but_keeps_rows
FAILED tests/data/test_millie_catalog.py::test_badge_title_constants_do_not_drift
FAILED tests/data/test_millie_recollect.py::test_badge_title_rows_picks_only_badge_titles_sorted
FAILED tests/data/test_millie_recollect.py::test_recollect_list_main_writes_tsv
FAILED tests/data/test_millie_recollect.py::test_read_recollect_parses_id_and_source
FAILED tests/data/test_millie_recollect.py::test_collect_accepts_only_keyword
```

플랜 2-a 의 지시대로 `BADGE_TITLES = frozenset()`·`badge_title_rows→[]`·`main→pass`·`_read_recollect→{}` 스텁을
먼저 두어 AttributeError·FileNotFoundError 가 아닌 AssertionError 로 떨어뜨렸다.

## Task 2 — GREEN

```
uv run pytest tests/data --no-header
188 passed in 2.66s          # failed 0
```

- `build_millie_catalog`: `BADGE_TITLES`(frozenset 7종)·`BADGE_TITLE_RE`·`is_badge_title()`·
  `coverage()` 에 `n_badge_title`·`badge_titles` 2키. `read_records`·`_row`·`build` 무변경.
- `test_coverage_gate`: `_n_success` 행 바로 아래에 `writer.writerow(["_n_badge_title", report.get("n_badge_title", -1)])` **기록 1줄만**.
  `assert n_badge == 0` 은 넣지 않았다(Task 3-b0 Advisor 몫) — `grep -c "assert n_badge == 0"` = 0.
- `millie_recollect_list.py`(46줄): `badge_title_rows(records)` + `main()` → `data/raw/recollect_badge_titles.txt`.
- `collect_millie.py`: `_read_recollect(path)` 신규 1함수, `collect(..., only=None)`,
  진입부 5줄 치환(`expand = expand and not only` · `sitemap_ids`·`done`·`seen`·`source`·`frontier` only 분기),
  `if DISCOVERED.exists() and not only:`, `main()` 의 `--recollect` + `expand=not args.no_expand and only is None`.
  **`render()`·렌더 루프(`for attempt in (1, 2)` ~ `time.sleep(DELAY_S)`) diff 0** — 2.5초·UA·4xx 3연속 예절 유지.

## 전역 검증

```
uv run pytest --no-header
256 passed, 2 warnings in 3.24s      # 기준선 233 + 파서 17(EXPECTED 2키 × 파라미터화 7종 + 신규 3) + 카탈로그 2 + recollect 4

uv run ruff check .
All checks passed!
```

`<verify><automated>` 두 블록 모두 통과(`TASK1_VERIFY_OK` · `TASK2_VERIFY_OK`).

## 판단 지점

1. **`build_millie_catalog.py` 는 플랜 `max_lines: 300` 을 넘는다(313줄).** 플랜 작성 시점의 286줄이 아니라
   착수 시점 실측이 이미 **301줄**이었다(Plan 06 이후 증가분). 순증은 상한 그대로 **+12** 를 지켰다.
   150줄 예외 3파일의 상한 재조정은 Advisor 판단 사항.
2. **게이트가 `-1` 이 아니라 실측 `_n_badge_title,896` 을 기록했다.** 내 pytest 실행 중
   `data/processed/millie_raw_coverage.json` 이 **다른 세션에 의해 21:37 에 재생성**되면서
   새 `n_badge_title` 키를 갖게 됐다(`generated_at 2026-09-05T12:37:25+00:00`, `n_records` 9,450).
   나는 `data/**` 를 쓰지 않았고 `make millie` 도 실행하지 않았다. 현 스냅샷 기준 배지 제목 오염은
   **9,450권 중 896권(9.5%)** — Task 3 재수집 대상 규모의 최신 실측이다.
3. **수집 배치 프로세스가 보이지 않는다.** 세션 종료 시점 `pgrep -fl collect_millie` 빈 출력.
   CHECKPOINT 의 "배치 자연 종료 확인" 여부는 Advisor 가 감시 루프(`PASS2_DONE`) 로 확정해야 한다.

## 하지 않은 것

- CHECKPOINT(사용자 승인)·Task 3 전체 — 재수집 실행·`make millie`·`report/draft.md` 수치 교체·트래킹 문서·개발일지.
- `collect_millie.py` 실행(네트워크 0). `--help` 출력만 확인했다.
- `make millie`·`make millie-build`·`make smoke`(Advisor 종료 시 1회).
- 커밋·`git add` 등 일체.

## git status --short (내 변경분)

```
 M scripts/build_millie_catalog.py
 M scripts/collect_millie.py
 M scripts/millie_parse.py
 M tests/data/test_millie_catalog.py
 M tests/data/test_millie_parse.py
?? scripts/millie_recollect_list.py
?? tests/data/test_millie_recollect.py
?? tests/fixtures/millie/badge_docent.txt
?? tests/fixtures/millie/badge_free_chatbook.txt
?? results/millie_coverage.csv        # 게이트 재실행 산출(원래 미커밋)
```

기존 픽스처 8건 수정 0(`git status --short tests/fixtures/millie/` 에 `M` 없음).
Makefile·`src/**`·`data/id_map.csv` 는 착수 전부터 M 이었고 이번 작업의 변경분이 아니다.

## Task 3 진행 기록 (Advisor, 09-05 21:3x~)
- **CHECKPOINT:** 배치 **자연 종료** 확인 — 마무리 패스 로그 21:28 `SUMMARY 발견 9580 · 수집 141 · 실패 0`, `pgrep` 빈 출력, 사용자 알림 "배치 작업이 모두 끝났습니다"(21:4x). pkill 불필요. JSONL 9,586줄 · 고유 9,580 · title 없는 130건 = 껍데기 129(성인 표지 플레이스홀더) + 파서 미스 1(0.01% ≤ 0.5%).
- **(관측) 21:37 다른 세션 재빌드:** `millie_raw_coverage.json generated_at 12:37:25Z`, parquet 9,450권, id_map 9,452행. Advisor·Worker 는 실행하지 않았다(배치 감시 루프 추정). id_map 불변식 3종 통과(HEAD 1,066행·20:28 사본 접두·연속). 최종 재빌드가 덮어쓴다.
- **3-b0 게이트 단언 활성화(Advisor, 5줄):** `tests/data/test_millie_catalog.py::test_coverage_gate` → RED `AssertionError: 배지 title 896건 — 파서 수정 후 해당 URL 재수집·make millie 재빌드 …` (정직한 실패 1회, 재수집·재빌드로 GREEN 예정).
- **3-b 대상 목록:** `recollect targets=896 / valid=9450` (best 888 · sitemap 6 · awards 2). `종료 D-N` 12건은 배치 마무리 패스가 이벤트 종료 후 재렌더해 이미 실제 제목 — 최신 줄 기준 0건(정규식 정상). 사본 scratch `recollect_targets.txt`, JSONL 9,586줄·md5 저장.
- **3-c 재수집 시작 21:46:** `nohup caffeinate -i -s uv run --with playwright python scripts/collect_millie.py --recollect data/raw/recollect_badge_titles.txt --shard {0,1}/2` → `data/raw/recollect_shard{0,1}.log`. 첫 줄 `recollect 모드: 896건 대상(멱등 skip 우회·확장 없음)`, 페이지당 3.5~7s, 샤드별 ≈448건 → 예상 종료 ≈22:35. 재수집 중 전역 스위트는 `test_coverage_gate` 1건 RED(의도).
- 판단: `build_millie_catalog.py` 313줄(플랜 max 300 초과 — 착수 시점 301줄, 순증 +12 준수) → Advisor 수용(150줄 예외 파일, 결정 D-16).
- 남은 것: 3-c 종료 검증 → 3-d `make millie` → 3-e 검증 → 3-f 문서.
