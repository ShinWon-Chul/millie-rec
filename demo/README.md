# 밀리의서재 메인 추천 시스템 — 설계 데모(정적 프론트)

해시 라우팅 8페이지짜리 한 장짜리 SPA다. 폰 프레임(390×844) 오른쪽에 인스펙터(560px)를 두어
**그 순간 시스템이 받는 신호와 파이프라인 내부**를 같이 보여주고, 관제 대시보드와 쇼케이스는
폰 프레임 없이 전폭 페이지로 그린다.

빌드 도구·npm·Node·프레임워크를 쓰지 않는다. 순수 HTML5 + CSS3 + Vanilla JS(ES2020 module)이고,
외부 리소스는 Pretendard 폰트 CSS 한 줄뿐이다.

## 실행법

```bash
make demo-serve      # → http://localhost:8080/?source=mock   (서버 없이 UI만 — 기본 권장)
make serve           # → http://localhost:8000/?source=api    (FastAPI가 /에 이 폴더를 서빙)
```

`file://`로 직접 열면 ES module과 `fetch`가 CORS로 막힌다. 반드시 HTTP 서버로 열어야 한다.
Chrome 최신(데스크톱)만 지원하고, 화면 폭 1200px 미만에서는 인스펙터가 폰 아래로 스택된다.

## URL 파라미터

| 파라미터 | 값 | 동작 |
|---|---|---|
| `source` | `mock` \| `api` | 데이터 출처. **생략하면 `/health`가 200이면 `api`, 아니면 `mock`** |
| `api` | 예: `http://localhost:8000` | `API_BASE`(기본 `""` = 같은 origin)를 이 주소로 덮어쓴다 |
| `capture` | `1` | 상단바·인스펙터를 숨겨 폰 프레임만 남긴다 (PDF 캡처용) |
| `capture` | `2` | 상단바만 숨기고 인스펙터를 남긴다 (신호 해석까지 담는 캡처) |

PDF용 스크린샷은 `?capture=1` 또는 `?capture=2`로 열고 ⇧⌘4로 영역을 캡처한다. Retina면 자동 2x.

## 라우트 8개

| 라우트 | 페이지 | 프레임 |
|---|---|---|
| `#/` | 쇼케이스 랜딩 (평가 비교표·본인 5권·기억할 5가지) | PC 전폭 |
| `#/onboarding` | 취향 설정 7단계 (S0~S6) | 폰 |
| `#/home` | 메인 (5행 구성 · 배지 · 앵커 행) | 폰 |
| `#/book/:id` | 책 상세 (바텀시트) | 폰 |
| `#/reader/:id` | 뷰어 시뮬레이션 — 데모 전용 | 폰 |
| `#/library` | 내 서재 (스냅샷 타임라인 · 열람/삭제/철회) | 폰 |
| `#/refresh` | 취향 재설정 (취향 설정 컴포넌트 재진입, 새 스냅샷) | 폰 |
| `#/dashboard` | 관제 대시보드 — 데모 전용 | PC 전폭 |

알 수 없는 해시는 쇼케이스로 떨어진다. 라우트 표의 정본은 `js/router.js` 하나다.

## 폴더 구조

```text
demo/
├── index.html                 페이지 1장 (상단바 · 폰 + 인스펙터 · 전폭 페이지 · 토스트)
├── css/                       tokens · base · onboarding · home · inspector · reader · library · dashboard
├── js/
│   ├── router.js              해시 → {page, params} (≤30줄, 라우트 표의 정본)
│   ├── app.js                 state 1개 + setState 1개 + render 1개 + 이벤트 큐(log/flush)
│   ├── actions.js             data-act 딕셔너리 + 취향 설정 단계 머신(S1~S5)
│   ├── presets.js             쇼케이스 시나리오 프리셋 3종
│   ├── api.js                 source=api|mock 스위치, 4초 타임아웃 → 클라이언트 fallback
│   ├── mock.js · mock_store.js  브라우저 내 상태 시뮬레이션 (점수 계산은 하지 않는다)
│   ├── inspector.js           우측 신호 해석 패널
│   └── screens/               ui.js(공용) · s0_start · onboarding_step · s6_persona · d2~d8
├── config/onboarding.json     화면 텍스트·옵션·선택 제한·진행바의 정본
├── mock/                      생성기 산출물 — 손으로 편집하지 않는다
├── fallback/popular.json      서버 무응답 시 인기 40권 (`make millie-export` 산출)
└── scripts/make_mock.py       mock 생성기 (표준 라이브러리, 결정적)
```

## mock 재생성

```bash
uv run python demo/scripts/make_mock.py
```

`make mock` 타겟은 아직 이 생성기를 가리키지 않으므로 **쓰지 않는다**(Makefile 정정은 미결 항목).
`mock/*.json` 손편집 금지 — `_manifest.json`의 입력 md5·출력 bytes가 재생성 판정 근거다.

## 계약

응답 형태의 정본은 `src/millie_rec/serving/schemas.py`·`schemas_should.py`이고, 문서 정본은
`.assets/설계서/백엔드 서빙/01_백엔드_서버_구성.md`다. mock과 api는 **같은 형태**를 반환해야 하며
`/contract-sync` 스킬이 이를 검증한다. `latency_ms`는 float(단계별은 `latency_breakdown`),
타임스탬프 필드 이름은 `ts`다. mock의 지연값은 표시용이며 PDF 숫자로 쓰지 않는다.

## 클라이언트 fallback

`source=api`에서 요청이 4초 안에 응답하지 않거나 네트워크 오류면 `fallback/popular.json`으로
`trending` 행만 렌더하고 배너와 인스펙터에 `fallback_level: 3 (client)`를 띄운다.
"추천 API 장애 ≠ 메인 장애"를 프론트에서도 실증하는 장치다. 브라우저 내 JS 스코어링은 하지 않는다.

## 데이터 고지

평가 비교표 = Goodbooks-10k(CC BY-SA 4.0) · 데모 카탈로그 = 밀리의서재 공개 도서 페이지(수치·메타·표지
URL만, 텍스트 미노출, 요청 시 삭제) · 데모 이웃 = 콘텐츠 유사도(협업 필터링 아님) · 개인정보 무수집 ·
서버 latency는 참고값. 표지는 밀리 CDN 핫링크만 쓰고 이미지를 저장하지 않으며, 밀리 저작 텍스트
(책 소개·큐레이터 노트·리뷰)는 화면에 노출하지 않는다.

## 규칙

- 상태를 바꾸는 곳은 `setState` 하나, 화면을 그리는 곳은 `render()` 하나.
  화면별 파일은 `render(state) → HTML 문자열`만 반환하고 이벤트는 `actions.js`가 위임으로 처리한다.
- 색·간격·타이포 리터럴은 `css/tokens.css`에만 둔다. JS/CSS 파일은 250줄 이하.
- 화면 문구는 `config/onboarding.json`, 이름은 `src/millie_rec/contracts.py`가 정본이다.
- 자세한 규칙은 `.claude/rules/demo.md`, 화면 정본은 `.assets/설계서/화면 구성 및 디자인/`의
  `01_기술스택_및_화면설계.md`와 `02_화면구성_v2_8페이지.md`다.
- 밀리 로고·3D 캐릭터 등 자사 에셋은 쓰지 않는다. 캐릭터 자리는 이모지로 대체했다.
