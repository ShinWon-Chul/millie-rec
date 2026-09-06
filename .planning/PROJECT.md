# millie-rec — 밀리의서재 메인 영역 추천 시스템 (사전과제 ① 5일 데모)

## What This Is

kt 밀리의서재 AI 엔지니어 사전과제 ①("도서 서비스의 메인 영역에 노출할 추천 시스템 설계")의 제출물을 만드는 프로젝트다. 제출물은 PDF 1~5페이지이고, 코드는 그 PDF에 들어갈 **실측 비교표(Track A, Goodbooks-10k)·밀리 공개 도서 카탈로그 위의 데모(Track B)·본인 5권 정성 케이스·배포 URL**을 만들기 위해 존재한다. 심사자가 설계를 "눌러볼" 수 있도록 FastAPI 서버 하나가 API·정적 데모·SQLite를 같은 origin에서 서빙한다.

## Core Value

**설계서의 주장(취향 설정은 갱신되는 explicit prior · 4단계 파이프라인 · 3지표 1:1 대응 · 앵커/난이도/시간 가변 가중치)이 로컬에서 실행되는 코드와 실측 숫자로 증명되어 PDF 5페이지 안에 들어간다.** 데모·서버가 죽어도 PDF는 완결된다.

## Requirements

### Validated

<!-- 09-04 밤까지 저장소에 존재하고 테스트로 확인된 것 (착수 프롬프트 §1 인벤토리) -->

- ✓ Python 계약 `src/millie_rec/contracts.py`(DTO·Protocol·VARIANTS·ROW_IDS·BADGE_TYPES·BookStats 밀리 필드) — Day 1 freeze, 아키텍처 테스트 통과
- ✓ HTTP 계약 `serving/schemas.py`(Must §1~§10) · `schemas_should.py`(§11·§13) — 백엔드 서빙 01 JSON 그대로, 라운드트립 테스트 통과
- ✓ 밀리 도서 페이지 파서 `scripts/millie_parse.py` + 픽스처 8건 + 테스트(라벨 기반, 리뷰·필명 미저장)
- ✓ **REC-01~08 (Validated in Phase 4 '추천 파이프라인과 모델 freeze', 2026-09-06):** 후보 3통로(`retrieval/{popularity,itemknn,content,neighbors}.py`) · 4 variant dict(`app/pipeline.py`·`pipeline_kr.py`) · ★α/β/γ 재정규화·감쇠(`ranking/blend.py`, 서버 β=0 실측) · gap 3항(`ranking/hybrid.py`) · MMR(`reranking/mmr.py`, ILD 0.606→0.684) · 난이도 가드(`reranking/guard.py`) · `cli demo --seeds` 5권 앵커(`report/demo_5books.md`) · 🧊 freeze 선언(STATE·개발일지 D72). `results/latest.csv` 4행(holdout n=2,000): pop 0.063/0.054/0.764 · cf 0.117/0.107/0.643 · hybrid 0.118/0.110/0.606 · hybrid_div 0.116/0.107/0.684
- ✓ 수집기·빌드·이웃·export 스크립트 4개(데이터 세션 작성, 적재 계획 기준) · `data/id_map.csv` 1,066행 · 야간 배치 진행 중(`data/raw/millie_pages.jsonl` 700행+)
- ✓ 배포 단위 `Dockerfile`·`railway.json`·`.dockerignore`(Railway 단일 컨테이너, v2.1)
- ✓ 빌드 도구 `Makefile`(serve·smoke·data·eval·millie-*)·`pyproject.toml`(런타임 8·dev 3)·아키텍처 경계 테스트·Track A 합성 fixture
- ✓ 로컬 서빙 스켈레톤 — `make serve`로 `/health`·정적 데모(`/`)·fallback 추천(level 3)이 아티팩트·DB·네트워크 없이 뜨고 `make smoke` 3점 PASS, SQLite 7테이블 자동 생성. Validated in Phase 1 '로컬 서빙 스켈레톤'(2026-09-05, `uv run pytest --no-header` 104 passed / 2 skipped; 작업 트리 미커밋 — 사용자 승인 대기)
- ✓ Track A 정량 평가 기반 — `make data && make eval`이 Goodbooks-10k(유저별 random holdout 20%, `split_mode=holdout`, 테스트 유저 2,000명 seed 42, 온보딩 5권 마스킹)에서 `results/latest.csv` `pop` 1행(Recall@20 0.063 · NDCG@10 0.054 · ILD@10 0.764)과 `latest_states.csv` n0/n20 2행을 만들고, 3지표 손계산·누수(`seen ∩ R_u`) 테스트가 고정됐다. pop 아티팩트 주입 시 `/api/recommend`가 `fallback_level=0`. EVAL-01~07 전부(Should EVAL-07 `eval_bar.png` 포함). Validated in Phase 2 'Track A 정량 평가 기반'(2026-09-05, `uv run pytest --no-header` 171 passed / 2 skipped, 02-VERIFICATION passed 5/5; 작업 트리 미커밋 — 사용자 승인 대기)

### Active

<!-- 이번 마일스톤(5일 데모)에서 만들 것. 상세는 REQUIREMENTS.md -->

- [ ] Track A 평가: Goodbooks-10k holdout에서 `pop`·`cf`·`hybrid`·`hybrid_div` 4행 Recall@20·NDCG@10·ILD@10 실측 + `split_mode` 기록
- [ ] Track B 카탈로그: 밀리 공개 도서 전량 → `books_kr`·content_sim 이웃·완독지수 난이도·`popularity_kr` + 커버리지·이웃 게이트 통과 → `artifacts/serving/*_kr.*`
- [ ] 추천 파이프라인: 후보(pop·cf·content) → 가중합 랭킹(α/β/γ 재정규화, 난이도 부호 gap) → MMR·난이도 가드 → Page Composition Must 5행
- [ ] 서빙 Must: 14 엔드포인트 중 Must 9개, SQLite 4테이블, Nearline 루프, fallback cascade, 품질 게이트, 로컬 bench p95 < 200ms
- [ ] 데모 재구성: v1 데모 27파일을 화면 구성 02의 8페이지(취향 설정→쇼케이스)로 재구성, mock은 밀리 카탈로그·새 스키마로 재생성, 로컬 API 연동
- [ ] 배포: Day 2 Railway 스켈레톤 → Day 4 본배포(로컬 스모크·docker 스모크 통과 후), UptimeRobot
- [ ] 본인 5권 정성 케이스(밀리 카탈로그 내 한국 책) 1장 + 모델 freeze(Day 3)
- [ ] PDF 5p: main 설계서 §2 페이지 매핑, 숫자는 `results/`만, 데이터 2트랙 각주, ★3개 박스, 필수 문장 7개

### Out of Scope

- Two-Tower·ANN 인덱스·multi-task ranker·LightGBM·learned re-ranker — 5일 내 동작 보장 불가, "설계만"(main 설계서 §5-5·§8)
- LLM/Agent·대형 Transformer·강화학습·실시간 전체 재학습 — 문제 본질(추천)과 무관한 복잡도(개발일지 09-03 결정 '5일 내 Two-Tower·LLM 구현 안 함')
- Kafka/Flink 실시간 인프라·K8s autoscaling·interleaving·실제 뷰어 연동·별점의 모델 라벨 사용 — 설계만(main §8)
- 텍스트 기반 난이도(가독성)·Reviewer-affinity 통로·정보나루 coLoan 정본 — 밀리 본문·키 미확보(적재 계획 §4·§6, Should 이하)
- React/Node/npm·브라우저 JS 스코어링·ORM·인증·로그인·검색 — 빌드 리스크·이중 구현·데모 규모 초과(개발일지 09-04 결정 '데모 프론트를 범위에 포함')
- HF Spaces·Cloudflare Pages 배포 — 무료 아님·같은 origin 이점(개발일지 09-04 결정 'HF Spaces 결정 폐기'·'배포 = Railway Hobby')
- 네이버 도서·교보·예스24 크롤링 — robots.txt 차단·약관(개발일지 09-04 결정 '네이버 도서 크롤링 기각')
- 밀리 텍스트(책 소개·큐레이터 문구) 화면 노출·표지 다운로드 — 저작물 재배포 금지(확보 방안 01 §3-2 완화 규칙)

## Context

- **설계는 끝났다.** 정본 20개가 `../.assets/설계서/`·`../.assets/PRD/`에 있다(main 설계서, PRD v1.2, 브레인스토밍 구체화, 아키텍처 01·배포 02, 백엔드 API v2, 화면 01·02, 데이터 소스 01·02·03, 방법론 v2, 구현 마일스톤 착수 프롬프트 v3). 참고 입력 5개는 "정본 아님" 헤더가 있다. 09-04 밤 3축 정합성 검수·재검수를 통과했다(`../.assets/검수/`).
- **결정의 기준은 개발일지** `../.assets/개발일지/`의 항목 D1~D49(6요소 형식). 스택·범위·표기 규칙이 어긋나면 개발일지를 따른다.
- **데이터 2트랙, 숫자 불혼합.** Track A(Goodbooks-10k, 유저 로그 有, 타임스탬프 無 → random holdout)는 비교표만. Track B(밀리 공개 도서 페이지 전량, 수치·메타·표지 URL만)는 데모·앵커·배지·난이도만. 데모 이웃은 콘텐츠 유사도(`source_channels=content`), Item-KNN co-read는 Track A 전용.
- **기존 코드 중 v1 산출물(demo/ 27파일)은 설계서와 불일치**(HF 주소·`/recommend` 접두어 없음·`timestamp`·`format`·`badge.type "rating"`·Goodbooks 카탈로그) → 재구성 대상. 계약·스크립트·배포 파일은 일치.
- **작업 방식:** Advisor(이 세션)가 브리프·검증, Opus Worker가 구현(루트 `CLAUDE.md` §6). 매 착수 전 4단계 — 설계서 전수 조사 · 기존 구현 인벤토리 · 불일치 재구성 · 로컬 기동 확인(`../.assets/설계서/구현 마일스톤/01_마일스톤_착수_프롬프트.md` §0).
- **사용자 몫(코드 밖):** Railway 가입·카드·Usage Limit, UptimeRobot·Sentry 계정, 본인 5권 선정(밀리 카탈로그 내), 제출 기한 확인(09-08 22:00 KST 가정), 스크린샷 확인, PDF 조판.

## Constraints

- **Timeline**: 2026-09-03~09-08, 직장인 퇴근 후 하루 2~3h, 사람 시간 총 12~15h — Day 3 종료 모델·API 형태 freeze, Day 5 PDF만, 한 작업 90분 초과 시 축소
- **Tech stack**: Python 3.11 + uv · pandas/pyarrow · scipy.sparse Item-KNN · sklearn TF-IDF · FastAPI + pydantic · sqlite3 표준 라이브러리(ORM 금지) · 순수 HTML/CSS/JS · Railway Hobby 단일 컨테이너 — 개발일지 결정 그대로, 의존성 추가는 Advisor 승인(+`prometheus-client`·`sentry-sdk`는 Day 4)
- **Architecture**: Contract-First Vertical Slice, star 의존(슬라이스는 `contracts.py`만 import, `app/`이 주입) — `tests/test_architecture.py`가 강제, 파일 ≤150줄(`schemas.py` 예외)
- **Local-first**: 아티팩트·DB·네트워크·클라우드 없이 `make serve`가 뜨고 `make smoke`가 통과해야 한다(`.claude/rules/local-run.md`). 배포는 로컬 통과 후에만
- **Naming**: 약호(`M2`·`D40`·`AC8`·`US-004`·화면 `D4`) 단독 참조 금지, 이름 + 파일 경로(+§)로 직접 언급(`.claude/rules/references.md`). GSD Phase도 번호 + 이름 병기
- **Data/License**: Goodbooks-10k CC BY-SA 4.0 귀속 / 밀리 공개 페이지는 수치·메타·표지 핫링크만, 리뷰 텍스트·필명 미저장, 책 소개는 TF-IDF 입력 전용·미노출, 요청 시 삭제, 단일 스레드·2.5초·식별 UA
- **Copyright**: 과제 PDF·캡처·이력서·`../.assets/`는 이 repo(GitHub public 가능)에 넣지 않는다 — `git ls-files | grep -iE "pdf|png|assets"` 빈 결과
- **Numbers**: PDF 숫자는 `results/latest.csv`·`results/latency.json`(로컬 bench)만. 서버·mock의 `latency_ms`는 참고값

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| GSD 페이즈 루프 채택, `.planning/`은 millie-rec/ 안, STATE.md가 진행 정본(PROGRESS.md는 이력·미결 파일로) | 사용자 09-05 지시. 루트 폴더엔 과제 PDF·이력서가 있어 repo 밖 | — Pending |
| 설계서 20개 완비 → GSD 도메인 리서치·코드 매핑 생략, 요구사항은 PRD §9 수용 기준 + main §8 범위 + 아키 §8 티어에서 도출 | 리서치는 설계서와 중복, 인벤토리는 착수 프롬프트 §1에 실측 | — Pending |
| 첫 페이즈 = 로컬 서빙 스켈레톤(walking skeleton) | 이후 모든 슬라이스를 떠 있는 서버에 붙여 로컬 검증(개발일지 09-04 결정 '참조 표기 규칙 + 전 과정 로컬 기동') | — Pending |
| 데이터 2트랙(Goodbooks 평가 / 밀리 데모), 데모 이웃 = 콘텐츠 유사도 | 유저 로그는 Goodbooks에만, 한국 책·완독지수는 밀리에만(개발일지 09-04 결정 '데모 카탈로그 주력 = 밀리 공개 도서 페이지'·'데모 이웃은 콘텐츠 유사도') | — Pending |
| 난이도 = 밀리 완독지수 파생 `σ(−resid_z)`, `pages`·`speed_z` 폐기 | 공개 페이지에 쪽수 없음, 길이 교란 회피(개발일지 09-04 결정 '적재 범위·스키마·난이도·이웃 결정') | — Pending |
| Should 버리는 순서 = 아키 §8 표 아래부터, 완독 직후 행·별점은 가장 늦게 | PDF 가치 최고, 비용은 조건문(개발일지 09-04 결정 '버리는 순서') | — Pending |
| α/β/γ = 사용자 상태 성분 가중치(2단), 초기값 0.6/0.3/0.1 + 감쇠 τ=20 + 빈 성분 재정규화 · 채널 가중 W 0.5/0.3/0.2 min-max 가중합 · MMR λ=0.7 → 난이도 가드 | 설계서 두 문구 결합(아키 §3-3 + main §5-2), Track A 실측이 D-07 게이트·기대 관계를 초기 상수로 통과해 튜닝 0회(개발일지 09-05 D68·09-06 D70) | ✓ Good — Phase 4 실측 4행 통과 |
| 🧊 Day 3 freeze 4종: 슬라이스 상단 상수 · `VARIANTS` 4종 · `artifacts/serving/*` 최종 스냅샷 9,447권 · `schemas*.py` 응답 형태 | PDF 숫자·5권 앵커 재현성(개발일지 09-06 D72) | ✓ Good — 이후 페이즈 조립·화면만 |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions (그리고 `../.assets/개발일지/` 6요소 항목 — 결정의 정본은 개발일지)
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-09-06 after Phase 4 '추천 파이프라인과 모델 freeze' completion (verification passed 5/5 · REC-01~08 Complete · 🧊 freeze declared, uncommitted — Phase 3 verification pending)*
