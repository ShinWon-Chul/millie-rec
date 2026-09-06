---
phase: 06-demo-rebuild
plan: 07
role: Advisor 전역 게이트 · 실측 · 인계
executed: 2026-09-06
commits: 0
---

# Phase 6 '데모 재구성'(.planning/ROADMAP.md "Phase 6: 데모 재구성") 검증 노트

Advisor(오케스트레이터) 세션이 직접 실행했다. **코드는 한 줄도 고치지 않았다** — 게이트 실패는
소유 플랜(06-01~06-06 `files_modified`)에 수정 브리프로 되돌리는 것이 이 플랜의 규칙이다.
아래 모든 수치는 이 세션에서 실행한 명령의 출력 원문이다.

실행 환경: 데모 정적 서버 `make demo-serve`(8080), api 관측용 uvicorn 8022(플랜의 8000 대신 —
Phase 5 '서빙 Must 완성' 세션과 포트가 겹치지 않게). Playwright는 repo 밖 스크래치패드에
`uv run --with playwright`로 임시 설치했다.

---

## 1. 구 형태 grep (DEMO-01 · 06-CONTEXT D-07)

```
cd demo && grep -rnE 'hf\.space|"/recommend"|\btimestamp\b|"format"\s*:|"type"\s*:\s*"rating"|\btype:\s*"rating"|static_popular|REPLACE-ME|books\.json|zygmuntz|CSV_URL' \
  --include='*.js' --include='*.json' --include='*.html' --include='*.py' --include='*.md' --include='*.css' . | wc -l
0
```

**0건.** v1 데모의 흔적이 `demo/` 전체에서 사라졌다. wave 3 직전까지 남아 있던 4건
(`inspector.js:106`·`:110`·`:48`, `s7_home.js:38`)은 06-06이 `d2_home.js`·`d3_detail.js` 개명
재작성과 인스펙터 확장에서 정리했다.

예외적으로 남겨야 하는 문자열 2곳은 저작권 고지다. `demo/README.md`와
`demo/mock/showcase.json`의 `data_notice`에 있는 `Goodbooks-10k(CC BY-SA 4.0)` 표기는
`../CLAUDE.md` §3-6 데이터 2트랙 규칙과 §7 공개 규칙이 요구하는 출처 표시이므로 유지한다.

## 2. `/contract-sync` 6항

| # | 항목 | 명령 · 결과 | 판정 |
|---|---|---|---|
| 1 | 이름 정본 — variant 4종 | `recommend_{pop,cf,hybrid,hybrid_div}.json` 의 `model_version` = `pop_v1` `cf_v1` `hybrid_v1` `hybrid_div_v1` · `"(pop\|cf\|hybrid\|hybrid_div)_mock"` grep 0건 | ✅ |
| 2 | 형태 — 계약 mock 10 + fallback | `model_validate` 11/11 통과 (아래 출력) | ✅ |
| 3 | 문서 — 백엔드 01 §5·§13 키 집합 | 10개 mock 전부 해당 pydantic 모델로 파싱되므로 여분 키·누락 키 0(모델이 `_Strict` 기반) | ✅ |
| 4 | freeze 기록 | `PROGRESS.md` 7·14·16행에 두 계약 Day 1 freeze와 Day 3 모델·API freeze 기록 존재 | ✅ |
| 5 | Track B — 저작 텍스트·형식·배지·통로 | `description`/`curator_note` grep **0** · `book_format` = `{전자책 6087, 오디오북 2990, 챗북 367}` 3값만 · `itemknn` grep **0** · mock 안 `"type"` 값 = `bestseller` (나머지 5종은 `mock.js` 표시 규칙이 런타임 생성, `BADGE_TYPES` 6종 부분집합) | ✅ |
| 6 | 생성기 — `_manifest.json` | `seed 42`, `outputs` 12개, 입력 4개 md5 기록 · `showcase.json` mtime(1788656195) ≥ `make_mock.py` mtime(1788656181) | ✅ |

```
ok   meta_onboarding.json -> OnboardingMeta
ok   candidates_onboarding.json -> CandidateSet
ok   preferences_response.json -> PreferencesResponse
ok   recommend_pop.json -> RecommendOut
ok   recommend_cf.json -> RecommendOut
ok   recommend_hybrid.json -> RecommendOut
ok   recommend_hybrid_div.json -> RecommendOut
ok   state.json -> UserStateOut
ok   dashboard.json -> DashboardOut
ok   showcase.json -> ShowcaseOut
ok   fallback/popular.json -> RecommendOut
--- ok=11 fail=0
```

`demo/mock/meta_onboarding.json`이 `src/millie_rec/serving/onboarding_meta.json`과
`criteria`·`reading_times`·`subcategories` 전부 일치함을 06-01이 확인했다(06-CONTEXT D-10의
"Phase 5 산출물이 아직 없을 수 있다"는 전제는 해소됐다 — 파일이 실재한다). 두 파일의 텍스트
동일성 검사를 `/contract-sync` 항목 7로 추가하는 제안은 §8과 `PROGRESS.md`에 남겼다.

## 3. pytest · ruff · smoke

```
uv run pytest --no-header        → 529 passed in 5.27s      (failed 0)
uv run pytest tests/demo         → 10 passed                (exit 0)
uv run ruff check demo/scripts tests/demo → All checks passed!
make smoke →
  smoke: /health 200
  smoke: / (demo static) 200
  smoke: /api/recommend 200
  smoke: PASS
```

529건은 Phase 5 '서빙 Must 완성'의 신규 테스트를 포함한 전체 수치다. Phase 6이 추가한 것은
`tests/demo/test_make_mock.py` 10건이다.

## 4. 크기 · 색 리터럴 · 구문

```
wc -l demo/js/*.js demo/js/screens/*.js demo/css/*.css | awk '$1>250'   → 빈 출력
node --check (demo JS 전 파일)                                          → 실패 0
grep -rn 'innerHTML' demo/js/screens | wc -l                            → 0
grep -rn 'href="javascript' demo/js | wc -l                             → 0
```

최대 파일은 `demo/js/mock.js` 249줄, `app.js` 248줄, `mock_store.js` 245줄로 250줄 상한 안이다.
`router.js`는 28줄(상한 30). 화면 파일에 `innerHTML`이 0인 것은 화면이 `render(state) → string`
순수 함수이고 주입은 `app.js`가 전담한다는 부록 E 규약이 지켜졌다는 뜻이다.

**색 리터럴 — `tokens.css` 밖 16건 잔존(Should, 조치하지 않음).**

| 파일 | 소유 | 건수 | 줄 |
|---|---|---|---|
| `demo/css/base.css` | 06-02 | 7 | 18 `#1F2024` · 40 `#000` · 41 `rgba(0,0,0,.55)` · 71 `rgba(18,18,18,0)` · 80 `rgba(255,255,255,.45)` · 84 `#FFFFFF`/`#1A1A1A` · 144 `#1A1B1E` |
| `demo/css/onboarding.css` | v1 재사용(Phase 6 무소유) | 9 | 13 · 44 · 74 · 79 · 85 · 91 · 107 · 118 · 122 |

06-06이 소유한 `home.css`·`inspector.css`는 **0건**으로 정리됐고, 06-05가 추가한
`dashboard.css`·`reader.css`·`library.css`도 0건이다. `base.css:129 .modal-wrap__dim`은 이미
`var(--dim)`으로 치환돼 있다. 남은 16건은 v1에서 이어받은 것이고 화면 결과에 영향이 없어
**판단: 수용**한다(범위 4분류 Should, `.claude/rules/simplicity.md` — PDF에 기여하지 않는
작업은 하지 않는다). `onboarding.css`는 Phase 6 어느 플랜의 `files_modified`에도 없다.

## 5. codegraph

```
cd millie-rec && codegraph sync .   → Done
```

## 6. DEMO-01~09 재확인

| ID | 판정 근거 | 결과 |
|---|---|---|
| **DEMO-01** | §1 grep 0건 + `grep -c 'const API_BASE = ""' demo/js/api.js` = 1 + `api.js`에 `/api` 접두어·`ts`·4초 타임아웃·`client_fallback_reason` | ✅ |
| **DEMO-02** | §2 6항 전부 ✅ (mock 10 + `fallback/popular.json` model_validate 11/11) | ✅ |
| **DEMO-03** | `router.js` `ROUTES` 8항목(`""` `onboarding` `home` `book/:id` `reader/:id` `library` `refresh` `dashboard`) + §9 완주에서 8페이지 전부 도달 | ✅ |
| **DEMO-04** | 취향 설정 7단계가 `config/onboarding.json` 1벌 + `onboarding_step.js` 공용 렌더러로 렌더(§9 step 3, 후보 30권) · 건너뛰기 = `skipUser` 프리셋에서 `consent=false` → 행 `trending`+`fresh_picks`·비개인화 배너 | ✅ |
| **DEMO-05** | §9 step 9에서 배지 39개·reason 9개·`recommendation_id` 표시 · `grep -c 'data-type=' demo/css/home.css` = 6 · 인스펙터 6섹션(신호 해석·이벤트 로그·latency·U_t·모델 전환/응답 ID·행별 채널 믹스) 캡처 확인 | ✅ (배지 6종 중 5종 실측 — 아래 주) |
| **DEMO-06** | 쇼케이스 캡처 확인 — 철학 문장 · Track A 비교표 4행 · `split_mode: holdout` 캡션 + `출처 results/latest.csv`·`p95 출처 results/latency.json` · 단계↔지표 그림(Recall@20→NDCG@10→ILD@10→Page Composition) · 2트랙 데이터 고지 | ✅ |
| **DEMO-07** | §9 step 13 — `#/reader/:id`에서 10분 읽기 2회 → "도달" 표시(T=15분) → 완독 → 별점 모달 4점 → step 14에서 `after_completion` 행 생성 | ✅ (mock. api `POST /api/ratings` 호출은 Phase 7 게이트) |
| **DEMO-08** | §9 step 20 — `#/dashboard` KPI 6칸 · MDE 고지 문구 · `BUDGET 200ms` 예산선 | ✅ (mock 세션 집계. api `/api/dashboard`는 06-06이 200 확인) |
| **DEMO-09** | §9 mock 완주 17/17 · 콘솔 에러 0 · pageerror 0 · 404 0 · `?capture=1\|2` 동작 · §3 pytest·smoke PASS | ✅ (mock 판정. api 완주는 Phase 7로 이관 — 06-CONTEXT D-09) |

**배지 6종 중 5종 주:** `light`("가볍게")는 범위 4분류 Should라 `make_mock.py`가 생성하지 않는다
(`mock.js:86` 주석). CSS는 `home.css`에 준비돼 있어 서버가 내려주면 즉시 그려진다. 06-06이 S3
기준별로 완주해 실측한 렌더 건수는 `author` 7 · `publisher` 8 · `bestseller` 43 · `buzz` 34 ·
`review`(3단 폴백 포함) 39이다. PDF 문장은 "6종 중 5종 실측"으로 쓴다.

## 7. Codex 교차검증

`../.claude/rules/codex-review.md`의 "언제" 표에 따라 **생략**한다. 이 페이즈의 변경은 전부
`demo/` 레인이고 계약·serving 변경이 0이다 — `git status --short src | wc -l` = 0(Phase 5 세션이
`20d5fa3`로 자기 산출물을 이미 커밋했고, Phase 6은 `src/**`를 한 줄도 건드리지 않았다).
표에서 `demo/`·문서는 "생략" 행이다.

## 8. 재위임 목록

**코드 재위임 0건.** 06-06이 올린 관측 6건은 전부 Advisor 판단으로 종결했다.

| # | 대상(소유) | 관측 | 판단 |
|---|---|---|---|
| 1 | `demo/js/app.js:134`(06-02) | 비개인화 배너를 폰 셸에서 모든 화면에 그린다. 화면 구성 02 §2는 배너를 D2 요소로 규정 | **수용.** 배너가 알리는 상태(동의 철회)는 화면과 무관하게 참이고, 서재에서도 같은 상태다. 완주에서 배너 중복 렌더 0(§9 step 19 `banner=1`) |
| 2 | `demo/js/screens/d5_library.js`(06-04) + `serving/schemas.py` `LibraryBook`(계약) | 서재 "담은 책" 5권 전부 저자가 "저자 미상". `authorOf`가 `state.recommend.rows`에서 찾는데 시드 5권은 dedup `exclude`로 행에 실리지 않는다 | **계약 미변경 · `PROGRESS.md` 미결로 이관.** `LibraryBook`에 `authors` optional 추가가 필요한데 `src/**`는 Phase 5 세션 소유이고 계약은 Day 3 freeze 상태다. 화면은 `book_id`로 라우팅·dedup하므로 동작에 문제 없다 |
| 3 | `demo/css/base.css`(06-02) 7건 · `onboarding.css`(무소유) 9건 | 색 리터럴 잔존 | **수용** — §4 판단 기록 |
| 4 | `demo/js/mock.js:86`(06-03) | `light` 배지 미생성 | **의도된 Should 미구현** — §6 배지 주 |
| 5 | `demo/js/inspector.js`(06-06) + `app.js`(06-02) | 미지원 카테고리 인스펙터 행이 S2 `disabled` 때문에 실전에서 뜰 수 없다 | **방어 코드로 존치** — 프리셋·api 응답이 미지원 이름을 넣을 수 있다 |
| 6 | `demo/fallback/popular.json` | Phase 6 착수 전부터 워킹 트리 수정 상태 | `export_millie_serving.py` 산출물이고 `RecommendOut` 검증을 통과한다(§2). Phase 5 커밋 `20d5fa3`가 `demo/`를 제외했으므로 Phase 6 커밋과 함께 처리 |

**05-05가 올린 계약 관측 1건**(`ShowcaseBook`에 `authors` 없음 → D8이 `book_id`로 동명 도서
구분)도 위 2번과 같은 종류로, 같은 미결 항목에 묶어 이관한다.

## 9. Playwright mock 완주

스크립트: `<scratchpad>/pw_demo06/run.py` · 결과 원문: 같은 폴더 `result.json`.
`goto`는 전부 `wait_until="domcontentloaded"` + 셀렉터 대기(이미지 CDN 대기 금지,
`../.claude/rules/demo.md`).

```
=== 17/17 OK · console_error=0 · pageerror=0 · 404=0 · shots=12 ===
```

| # | 단계 | 실측 |
|---|---|---|
| 1 | `#/` 쇼케이스 | 비교표 4행 · `split_mode` 표기 |
| 2~3 | `#/onboarding` S0→S5 | 후보 30권 중 5권 선택, 기준 = 베스트셀러 |
| 9 | `#/home` | `rows=['anchor_1004','persona_shelf','trending','fresh_picks']` · 배지 39 · reason 9 · `rec_` 표시 |
| 10 | 모델 라디오 | `pop_v1` · `hybrid_v1` · `hybrid_div_v1` 전부 인스펙터에 반영 |
| 11 | 캡처 모드 | `capture=1` topbar=False inspector=False / `capture=2` inspector=True |
| 12 | 앵커 타일 → 상세 | `#/book/2099` 바텀시트 |
| 13 | 뷰어 | 10분 읽기 2회 → "도달" 표시 → 완독 → 별점 4점 |
| 14 | 완독 후 홈 | `rows=['after_completion','anchor_1004','persona_shelf','trending','fresh_picks']` |
| 15 | `#/library` | 버킷 3 · 타임라인 1 |
| 16~17 | `#/refresh` | 헤더 "취향 다시 설정" · 재설정 후 타임라인 2 |
| 18 | 내 데이터 보기 | JSON `<pre>` 모달 표시 후 닫힘 |
| 19 | 동의 철회 | 배너 1 · `rows=['trending','fresh_picks']` · `fallback_v1` |
| 20 | `#/dashboard` | KPI 6 · MDE 고지 · `BUDGET 200ms` |
| 21 | D8 프리셋 3 | `skipUser`=비개인화 2행 / `newUser`=`anchor_2623` 개인화 / `resetUser`=`anchor_621` |

**콘솔 에러 0건 · uncaught 0건 · 404 0건.**

`continue_reading` 행은 step 9·14에서 화면에 나타나지 않는데, 이것이 정상이다. 서버와 같이
빈 `items`로 내려오고 화면이 `items.length === 0`인 행을 숨긴다(06-03 인계). 인스펙터의 행별
채널 믹스에는 `continue_reading — (0권)`으로 남아 있어 숨김이 데이터 누락이 아님을 보여준다.

첫 실행에서 step 18·19가 실패했는데 앱이 아니라 검증 스크립트의 셀렉터 문제였다.
`data-act="closeModal"`이 모달 배경 `div.modal-wrap__dim`과 닫기 `button` 양쪽에 붙어 있어
`.first`가 배경을 잡았다. `.modal button[data-act="closeModal"]`로 좁혀 재실행해 17/17이 됐다.
`demo/` 코드는 수정하지 않았다.

## 10. 캡처 (스크래치패드 12장, repo 반입 0)

`<scratchpad>/pw_demo06/shots/` · `device_scale_factor=2` · `git status --short | grep -ci png` = 0.

| 화면 02 §7 캡처 계획 | 파일 |
|---|---|
| ① 온보딩 S3 + 인스펙터 | `p1_onboarding_s3_inspector.png` · `p1_onboarding_s3_capture2.png` |
| ② 메인 배지·앵커 | `p3_home_badges_anchor.png` · `p3_home_capture1.png` |
| ③ hybrid vs hybrid_div | `p5_home_hybrid.png` · `p5_home_hybrid_div.png` |
| ④ 뷰어 완독→별점→다음은 | `p3_reader_1.png` · `p3_reader_2.png` · `p3_reader_3.png` |
| ⑤ 서재 타임라인·철회 | `p3_library_timeline.png` |
| ⑥ 대시보드 · 쇼케이스 | `p4_dashboard.png` · `p4_showcase.png` |

**`p4_dashboard.png`는 재캡처했다.** 완주 스크립트의 순서상 대시보드가 동의 철회(step 19) *뒤에*
찍혀서 세션 집계가 전부 0이고 fallback 100%·모델 분포 `fallback_v1` 하나인 빈 화면이 나왔다.
세션 집계 대시보드로서는 정직한 결과지만(D-03) PDF 그림으로는 아무것도 보여주지 못한다.
`recapture_dashboard.py`로 철회 **전** 상태 — 온보딩 완주 + 2권 완독 + 별점 2건 — 에서 다시 찍었다.
코드는 고치지 않았고 캡처 시점만 옮겼다. 재캡처 KPI 실측:

```
Qualified Reading Start rate  100.0%  n = 2   (QRS = 가상 15분 도달 / 뷰어 진입)
첫 완독 도달률 (신규)          100.0%  n = 1
fallback %                      0.0%  n = 3
p95 latency                    38.0ms  n = 3   (mock 상수 · 참고용 — PDF 숫자 아님)
오류율                          0.0%  n = 3
활성 user_key                       1  n = 210
```

콘솔 에러 0 · pageerror 0. **Phase 8 주의: 대시보드 캡처는 반드시 철회 전에 찍는다.**

`report/figures/`로 복사하는 것은 Phase 8 'PDF 제출물' 몫이다. 캡처에 밀리 표지 이미지가
포함되므로(밀리 CDN 핫링크 렌더) repo public 공개 판단도 Phase 8에서 한다 —
Phase 5 커밋 `20d5fa3`가 `.gitignore`에 `report/figures/` 제외를 이미 넣었다.

**상단바 `version`과 인스펙터 `model_version`이 다르게 보이는 것은 정상이다.** 상단바는
`state.health.model_version`(서비스 기본 모델, `/health`)을, 인스펙터는 이 응답이 실제 사용한
`recommend.model_version`을 표시한다. 셀 A 배정 시 각각 `hybrid_div_v1`·`hybrid_v1`이 된다.
PDF 캡처를 읽는 사람이 오해하지 않도록 캡션에 한 줄 붙이는 것을 Phase 8에 권한다.

## 11. api 모드 관측 (완주 판정 아님)

스크립트 `<scratchpad>/pw_demo06/api_probe.py` · 결과 `api_result.json`.
uvicorn 8022, 읽기 경로만(Phase 5 세션의 SQLite 카운트를 흔들지 않기 위해 쓰기 요청 없음).

```
showcase_tbody_rows : 4
home_rows           : ['trending', 'fresh_picks']
model_version_seen  : hybrid_div_v1
banner_count        : 1
console_errors      : []
page_errors         : []
non_2xx             : []        (총 요청 61건)
```

**404 목록 = 빈 목록.** 플랜은 "아직 없는 엔드포인트가 404로 남을 것"을 전제했으나 Phase 5가
12개 라우트를 전부 등록한 뒤라 비-2xx가 하나도 없다. `#/home`이 익명 2행으로 뜨는 것은 스냅샷
없는 방문의 정상 강등이다. `?source=api` 완주 자체는 06-CONTEXT D-09대로 Phase 7 '배포'의
사전 게이트로 남긴다.

## 12. 인계

- **Phase 7 '배포'(.planning/ROADMAP.md "Phase 7: 배포") 사전 게이트:** `make serve` +
  `?source=api`로 쇼케이스→대시보드 완주. 이 노트 §11이 읽기 경로만 확인했으므로, 쓰기 경로
  (`POST /api/preferences`·`/api/events`·`/api/ratings`, `DELETE …/personalization`)를 포함한
  완주가 게이트 내용이다. §11의 비-2xx 0건이 그대로 유지돼야 한다.
- **Phase 8 'PDF 제출물' 캡처 원본:** `<scratchpad>/pw_demo06/shots/` 12장. `report/figures/`
  복사·표지 이미지 공개 판단은 Phase 8.
- **재위임 상태: 0건.** 06-06 관측 6건 + 06-05 관측 1건 전부 §8에서 종결하거나
  `PROGRESS.md` 미결로 이관했다.
- **커밋:** 이 플랜은 0건. Phase 6 전체는 `694405e`~`844fb74`(20d5fa3 제외) 16커밋으로 이미
  작업 트리에 반영돼 있고, `git status --short demo tests/demo | wc -l` = 1
  (`demo/fallback/popular.json` — §8 6번).
- **STATE.md:** 이 세션은 직접 편집하지 않는다. Phase 5 세션과 공유하는 파일이므로 GSD 도구의
  최소 갱신만 사용한다(06-CONTEXT "두 세션 병렬" 절).
