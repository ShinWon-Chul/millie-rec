<!-- GSD:project-start source:PROJECT.md -->
## Project

**millie-rec — 밀리의서재 메인 영역 추천 시스템 (사전과제 ① 5일 데모)**

kt 밀리의서재 AI 엔지니어 사전과제 ①("도서 서비스의 메인 영역에 노출할 추천 시스템 설계")의 제출물을 만드는 프로젝트다. 제출물은 PDF 1~5페이지이고, 코드는 그 PDF에 들어갈 **실측 비교표(Track A, Goodbooks-10k)·밀리 공개 도서 카탈로그 위의 데모(Track B)·본인 5권 정성 케이스·배포 URL**을 만들기 위해 존재한다. 심사자가 설계를 "눌러볼" 수 있도록 FastAPI 서버 하나가 API·정적 데모·SQLite를 같은 origin에서 서빙한다.

**Core Value:** **설계서의 주장(취향 설정은 갱신되는 explicit prior · 4단계 파이프라인 · 3지표 1:1 대응 · 앵커/난이도/시간 가변 가중치)이 로컬에서 실행되는 코드와 실측 숫자로 증명되어 PDF 5페이지 안에 들어간다.** 데모·서버가 죽어도 PDF는 완결된다.

### Constraints

- **Timeline**: 2026-09-03~09-08, 직장인 퇴근 후 하루 2~3h, 사람 시간 총 12~15h — Day 3 종료 모델·API 형태 freeze, Day 5 PDF만, 한 작업 90분 초과 시 축소
- **Tech stack**: Python 3.11 + uv · pandas/pyarrow · scipy.sparse Item-KNN · sklearn TF-IDF · FastAPI + pydantic · sqlite3 표준 라이브러리(ORM 금지) · 순수 HTML/CSS/JS · Railway Hobby 단일 컨테이너 — 개발일지 결정 그대로, 의존성 추가는 Advisor 승인(+`prometheus-client`·`sentry-sdk`는 Day 4)
- **Architecture**: Contract-First Vertical Slice, star 의존(슬라이스는 `contracts.py`만 import, `app/`이 주입) — `tests/test_architecture.py`가 강제, 파일 ≤150줄(`schemas.py` 예외)
- **Local-first**: 아티팩트·DB·네트워크·클라우드 없이 `make serve`가 뜨고 `make smoke`가 통과해야 한다(`.claude/rules/local-run.md`). 배포는 로컬 통과 후에만
- **Naming**: 약호(`M2`·`D40`·`AC8`·`US-004`·화면 `D4`) 단독 참조 금지, 이름 + 파일 경로(+§)로 직접 언급(`.claude/rules/references.md`). GSD Phase도 번호 + 이름 병기
- **Data/License**: Goodbooks-10k CC BY-SA 4.0 귀속 / 밀리 공개 페이지는 수치·메타·표지 핫링크만, 리뷰 텍스트·필명 미저장, 책 소개는 TF-IDF 입력 전용·미노출, 요청 시 삭제, 단일 스레드·2.5초·식별 UA
- **Copyright**: 과제 PDF·캡처·이력서·`../.assets/`는 이 repo(GitHub public 가능)에 넣지 않는다 — `git ls-files | grep -iE "pdf|png|assets"` 빈 결과
- **Numbers**: PDF 숫자는 `results/latest.csv`·`results/latency.json`(로컬 bench)만. 서버·mock의 `latency_ms`는 참고값
<!-- GSD:project-end -->

<!-- GSD:stack-start source:STACK.md -->
## Technology Stack

정본은 상위 폴더 `../CLAUDE.md` §4 기술 스택과 결정 기준 `../.assets/개발일지/`(항목 D5·D6·D18·D19·D26·D38). 요약: Python 3.11 + uv · pandas/pyarrow · scipy.sparse Item-KNN(Track A) · sklearn TF-IDF · FastAPI + pydantic(`serving/schemas.py`) · sqlite3 표준 라이브러리(WAL, ORM 금지) · 순수 HTML/CSS/JS(`demo/`) · Railway Hobby 단일 컨테이너. 의존성 추가는 Advisor 승인.
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

정본은 `../.claude/rules/*.md`(항상 로드: architecture·simplicity·references·local-run·python-tdd·codex-review / 경로별: python·data·evaluation·serving·demo·report). 핵심: 파일 ≤150줄(`schemas.py` 예외) · TDD(`uv run pytest`만) · 약호 단독 참조 금지(이름 + 경로) · 모든 브리프 완료 기준 = `uv run pytest -q` + `make smoke` · 숫자는 `results/`만 · 이름은 `contracts.py`만.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

정본은 `../.assets/설계서/시스템 아키텍처, 기술 스택 및 배포(프론트, 백엔드 서빙)/01_시스템_아키텍처_기술스택_배포.md`와 `../CLAUDE.md` §3. Contract-First Vertical Slice: 슬라이스(`data retrieval ranking reranking evaluation serving`)는 `src/millie_rec/contracts.py`만 import, `app/`이 주입(star 의존, `tests/test_architecture.py` 강제). HTTP 계약 `serving/schemas.py`·`schemas_should.py`(백엔드 서빙 01). 데모는 `demo/`(src 밖). 현재 구현 인벤토리: `../.assets/설계서/구현 마일스톤/01_마일스톤_착수_프롬프트.md` §1.
<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->
## Project Skills

프로젝트 스킬은 상위 폴더 `../.claude/skills/`에 있다(상위 디렉터리 스킬은 자동 로드됨): `/day-start` `/day-end` `/slice-brief`(Advisor→Opus Worker 브리프·검증) `/eval-run` `/contract-sync` `/deploy-demo` `/pdf-check`. GSD 페이즈 안에서 실행·검증 보조로 쓴다(`../CLAUDE.md` §6-1).
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.

이 프로젝트 보강: 페이즈 실행 중 구현은 Advisor→Opus Worker(`/slice-brief`)로 위임하고, 매 착수 전 4단계(설계서 전수 조사·기존 구현 인벤토리·불일치 재구성·로컬 기동 확인 — `../.assets/설계서/구현 마일스톤/01_마일스톤_착수_프롬프트.md` §0)를 거친다. Phase는 항상 번호 + 이름으로 부른다(예: Phase 1 '로컬 서빙 스켈레톤'). 커밋·push는 사용자가 원격 레포를 만든 뒤 승인 시(2026-09-05 지시).
<!-- GSD:workflow-end -->



<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
