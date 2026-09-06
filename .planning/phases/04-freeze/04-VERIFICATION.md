---
phase: 04-freeze
verified: 2026-09-06T01:30:00Z
status: passed
score: 5/5 must-haves verified (ROADMAP Success Criteria) · 8/8 requirements (REC-01~08) Complete
overrides_applied: 0
---

# Phase 4 '추천 파이프라인과 모델 freeze' Verification Report

**Phase Goal:** 설계서의 4단계 파이프라인이 실제 코드로 존재하고, 그 결과가 비교표 4행과 본인 5권 앵커 1장이라는 PDF 증거가 된 뒤 모델이 얼어붙는다.
**Verified:** 2026-09-06T01:30:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (ROADMAP.md "Phase 4" Success Criteria)

| # | Truth | Status | Evidence |
|---|---|---|---|
| 1 | `make eval` 결과 `results/latest.csv` 4행(pop·cf·hybrid·hybrid_div) + `split_mode`, 서버 `model=` 쿼리로 4 variant가 서로 다른 책 | ✓ VERIFIED | `results/latest.csv` 4행 실측(`cat` 확인), 전부 `split_mode=holdout`·`*_v1` 접미. 최종 카탈로그 서버 실측(04-06-SUMMARY, 5권 seed): pop∩cf 0·pop∩hybrid 0·pop∩hybrid_div 1·cf∩hybrid 7·cf∩hybrid_div 6·hybrid∩hybrid_div 8 — pairwise 동일 리스트 없음. `model_version` 4종 `pop_v1/cf_v1/hybrid_v1/hybrid_div_v1` |
| 2 | `hybrid_div`의 ILD@10 > `hybrid`, NDCG 하락 대비 다양성 이득 해석 문단이 `report/draft.md`에 존재 | ✓ VERIFIED | `latest.csv`: ild(hybrid_div)=0.684 > ild(hybrid)=0.606; ndcg(hybrid_div)=0.107 ≥ 0.8×0.110=0.088(D-07 게이트 통과). `report/draft.md`에 `"MMR 적용으로 NDCG@10은 …"` 해석 문단 존재(grep 확인) |
| 3 | `user_state_weights`가 재정규화되어 신규 β=0, 이벤트 축적에 α 감쇠 | ✓ VERIFIED | `ranking/blend.py` 상수·수식 코드 확인(`ALPHA0=0.6 TAU=20 ALPHA_FLOOR=0.2`), `tests/ranking/test_blend.py` 8건 통과. 서버 실측: seeds-only 사용자 `user_state_weights == {"alpha":1.0,"beta":0.0,"gamma":0.0}`(04-06-SUMMARY 표) |
| 4 | `cli demo --seeds`가 본인 5권 앵커 1장을 출력, 이웃 = 콘텐츠 유사도 병기 | ✓ VERIFIED | `report/demo_5books.md` 실존(5,125B). "을 좋아하셨다면" 5회·"hybrid_div 상위 10" 1회·"데모 카탈로그의 앵커 이웃은 콘텍츠 유사도다" 1회·`alpha=1.0 beta=0.0 gamma=0.0` 존재(직접 grep 재확인) |
| 5 | Day 3 종료 모델·API 응답 형태 freeze가 STATE.md·개발일지에 선언, `pytest`·`make smoke` PASS | ✓ VERIFIED | `.planning/STATE.md`에 freeze 선언 다수(🧊 FREEZE 선언, Day 3 게이트 ✅), 개발일지 D72 항목이 6요소(문제·동기·선택지·근거·장애·결과) 전부 포함해 존재(직접 읽어 확인). `uv run pytest --no-header` → `327 passed`, `make smoke` → `PASS`(둘 다 이 세션에서 직접 재실행) |

**Score:** 5/5 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|---|---|---|---|
| `src/millie_rec/retrieval/{neighbors,itemknn,content}.py` | 후보 3통로 완성 | ✓ VERIFIED | 존재, ≤150줄(149/80/131), `KNN_TOP=50 POOL=200` 확인, `retrieval` 테스트 34건(31+아키텍처3) 포함해 전체 스위트 통과 |
| `src/millie_rec/ranking/{blend,hybrid}.py` | state_weights·blend_channels·gap 3항 | ✓ VERIFIED | 존재, ≤150줄(43/118), `ALPHA0/BETA0/GAMMA0=0.6/0.3/0.1 TAU=20 ALPHA_FLOOR=0.2 W_CF/W_CONTENT/W_POP=0.5/0.3/0.2 W_GAP/W_GAP_POS/W_NCOMP_GAP=-0.10/-0.20/-0.01` 코드에서 직접 확인 |
| `src/millie_rec/reranking/{mmr,guard}.py` | MMR 다양성 + 난이도 가드 | ✓ VERIFIED | 존재, ≤150줄(54/65), `LAMBDA_MMR=0.7 MMR_POOL=50 GUARD_RESID_Z=-1.0 GUARD_MIN_COMPLETED=3` 코드에서 직접 확인 |
| `src/millie_rec/app/pipeline.py` + `pipeline_kr.py` | 4 variant dict 조립(Track A + Track B) | ✓ VERIFIED | 존재, ≤150줄(149/123). `contracts.VARIANTS = ("pop","cf","hybrid","hybrid_div")` 확인 |
| `src/millie_rec/app/demo_cli.py` | `cli demo --find/--seeds` | ✓ VERIFIED | 존재, 149줄. `report/demo_5books.md` 실제 산출물로 동작 확인 |
| `src/millie_rec/serving/api.py` | `create_app(weights=)` 배선 | ✓ VERIFIED | 150줄(상한 정확 도달), `weights: Callable[[UserState], dict[str, float]] | None` 파라미터 존재, `app/server.py`가 `state_weights` 주입 확인 |
| `results/latest.csv` · `latest_states.csv` | 4행·8행 실측 | ✓ VERIFIED | 직접 `cat`으로 확인, 숫자 04-05-SUMMARY와 일치 |
| `report/demo_5books.md` | 본인 5권 앵커 1장 | ✓ VERIFIED | 실존, 내용 grep 검증 통과 |
| `.planning/REQUIREMENTS.md` REC-01~08 | 체크 완료 | ✓ VERIFIED | 8줄 전부 `[x]`, traceability 표 8행 전부 `Complete`(직접 grep 확인) |

### Key Link Verification

| From | To | Via | Status | Details |
|---|---|---|---|---|
| `retrieval/itemknn.py` | `retrieval/neighbors.py` | `retrieve_from_neighbors(self, user, k, source=SOURCE_ITEMKNN, ...)` | WIRED | 04-01-SUMMARY 코드 인용 + 34 passed로 간접 확인 |
| `app/pipeline.py` | `ranking/__init__.py` | `from millie_rec.ranking import ... blend_channels` | WIRED | `app/pipeline.py` 149줄에서 사용, 아키텍처 테스트(star 의존) 3 passed |
| `app/pipeline.py` | `reranking/__init__.py` | `MMRReranker(vectors), DifficultyGuard(book_stats)` — D-08 순서 | WIRED | `StagedPipeline.recommend`에서 rerankers 순차 적용(04-04-SUMMARY 확인) |
| `app/server.py` | `serving/api.py` | `create_app(weights=state_weights)` | WIRED | `server.py` 직접 읽어 `weights=state_weights` 확인, `api.py`가 `_personalized_response`에 전달 |
| `serving/api.py` | `serving/compose.py` | `dataclasses.replace(resp, user_state_weights=...)` | WIRED | `api.py:89` `replace(resp, user_state_weights=dict(shown))` 확인 |

### Requirements Coverage

| Requirement | 제목 | 티어 | Status | Evidence |
|---|---|---|---|---|
| REC-01 | 후보 3통로(popularity·itemknn·content) | Must | ✓ SATISFIED | `retrieval/{popularity,itemknn,content}.py` 존재, `CandidateGenerator` 계약 테스트 통과 |
| REC-02 | `VARIANTS` 4종 dict 조립·hybrid 가중합 | Must | ✓ SATISFIED | `contracts.VARIANTS` + `app/pipeline.py` `fit_pipelines`/`build_pipelines`, `latest.csv` 4행 실측 |
| REC-03 | α/β/γ 재정규화(신규 β=0) | Must | ✓ SATISFIED | `ranking/blend.py::state_weights`, 서버 실측 `{alpha:1.0,beta:0.0,gamma:0.0}` |
| REC-04 | 난이도 부호 gap 3항(Should) | Should | ✓ SATISFIED | `ranking/hybrid.py` `W_GAP/W_GAP_POS/W_NCOMP_GAP`, None 3경로 가중 0 테스트 |
| REC-05 | MMR 다양성 재순위화 | Must | ✓ SATISFIED | `reranking/mmr.py`, 실측 ild(hybrid_div)=0.684 > ild(hybrid)=0.606 |
| REC-06 | 난이도 가드(Should) | Should | ✓ SATISFIED | `reranking/guard.py`, 12권 손계산 테스트 + `GUARD_RESID_Z/GUARD_MIN_COMPLETED` |
| REC-07 | `cli demo --seeds` 본인 5권 앵커 | Must | ✓ SATISFIED | `report/demo_5books.md` 실존·내용 검증 |
| REC-08 | Day 3 모델 freeze 선언 | Must | ✓ SATISFIED | STATE.md + 개발일지 D72(6요소) + draft §4-1 각주·§5-1 |

**Orphaned requirements:** 없음 — REQUIREMENTS.md 추적표에 Phase 4로 매핑된 8개(REC-01~08) 전부 플랜 6개의 `requirements:` 필드에 나타남.

### Anti-Patterns Found

없음. `retrieval`·`ranking`·`reranking`·`app/pipeline*.py`·`app/demo_cli.py`·`serving/api.py`에서 `TODO|FIXME|XXX|HACK|PLACEHOLDER|placeholder|not yet implemented|coming soon` grep 0건. 각 SUMMARY의 "Known Stubs" 절도 전부 "없음"이며, 유일하게 남은 대리값(`n_completed = len(user.history)`)은 D-08 결정에 따라 코드·docstring·PDF 각주에 명시적으로 문서화된 의도된 이연(Phase 5 인계)이지 은닉된 스텁이 아니다.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|---|---|---|---|
| 전체 테스트 스위트 | `uv run pytest --no-header` | `327 passed` | ✓ PASS |
| 아키텍처(star 의존) | `uv run pytest tests/test_architecture.py --no-header` | `3 passed` | ✓ PASS |
| 로컬 서빙 스모크 | `make smoke` | `/health 200 · / 200 · /api/recommend 200 · smoke: PASS` | ✓ PASS |
| D-07 게이트(ILD 상승·NDCG 유지) | `results/latest.csv` 수치 대조 | `0.684 > 0.606` ∧ `0.107 ≥ 0.088` | ✓ PASS |
| freeze 상수 코드-문서 일치 | grep 상수 8개 파일 | 전부 문자 단위 일치 | ✓ PASS |

### Human Verification Required

없음. 이 페이즈의 모든 must-have는 pytest·grep·csv 수치 대조·make smoke로 객관적 판정이 가능했고, 서버 4 variant 판정·5권 실측은 이미 04-06 플랜 실행 중 사람(사용자)이 5권을 확정하고 최종 카탈로그 스냅샷을 승인한 뒤 Advisor가 실측했다(체크포인트 게이트 이미 통과, SUMMARY에 근거 기록).

### Gaps Summary

없음. ROADMAP Success Criteria 5개 전부 검증됨, REQUIREMENTS REC-01~08 8개 전부 Complete, 아키텍처 경계 위반 없음(`tests/test_architecture.py` 3 passed), freeze 선언이 요구된 3곳(STATE.md·개발일지·draft.md) 모두 실존 확인. 알려진 사소한 문서 불일치(STATE.md frontmatter `completed_phases: 3` — 본문은 Phase 4 완료를 명확히 서술하며 이는 검증 완료 후 다음 세션이 갱신할 카운터일 뿐 목표 달성 여부와 무관) 외에는 관찰된 결함이 없다.

---

_Verified: 2026-09-06T01:30:00Z_
_Verifier: Claude (gsd-verifier)_
