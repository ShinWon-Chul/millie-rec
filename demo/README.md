# 밀리 메인 추천 데모 (정적 프론트)

밀리의서재 온보딩 7단계와 메인 추천 화면을 PC 브라우저에서 모바일 앱처럼 재현하고,
오른쪽 인스펙터에 **그 순간 시스템이 받는 신호와 파이프라인 내부**를 보여주는 한 페이지짜리 데모.

빌드 도구·npm·Node·프레임워크를 쓰지 않는다. 순수 HTML5 + CSS3 + Vanilla JS(ES2020 module)이고,
외부 리소스는 Pretendard 폰트 CSS 한 줄뿐이다. 폴더를 그대로 Cloudflare Pages에 올리면 배포가 끝난다.

## 실행법

```bash
cd millie-rec/demo
python3 -m http.server 8080
# 브라우저:
#   http://localhost:8080/?source=mock                 (모델 없이 UI만 — 기본 권장)
#   http://localhost:8080/?source=api&api=http://localhost:8000   (로컬 FastAPI와 함께)
#   배포본은 API_BASE(HF Spaces)로 자동 연결, 실패 시 fallback/popular.json
```

`file://`로 직접 열면 ES module과 `fetch`가 CORS로 막힌다. 반드시 HTTP 서버로 열어야 한다.
Chrome 최신(데스크톱)만 지원하고, 화면 폭 1200px 미만에서는 인스펙터가 폰 아래로 스택된다.

## URL 파라미터

| 파라미터 | 값 | 동작 |
|---|---|---|
| `source` | `mock` \| `api` | 데이터 출처. **생략하면 `mock/books.json`이 있으면 자동으로 mock**, 없으면 api |
| `api` | 예: `http://localhost:8000` | `API_BASE`를 이 주소로 덮어쓴다 (`source=api`와 함께) |
| `capture` | `1` | 인스펙터·상단바를 숨기고 페이지 배경을 단색으로 — 폰 프레임만 남는 PDF 스크린샷용 |

PDF용 스크린샷: `?capture=1`로 열고 ⇧⌘4로 프레임 영역을 캡처한다. Retina면 자동 2x.

## `API_BASE` 교체 지점

`js/api.js` 파일 **최상단 상수 하나**만 바꾼다.

```js
// ▼▼ 배포 시 교체 지점 — Hugging Face Spaces 주소를 여기에 넣는다 ▼▼
const API_BASE = "https://REPLACE-ME.hf.space";
```

배포 후 `?source=api`로 접속해 인스펙터의 `source: api` · `fallback_level: 0`을 확인한다.

## 클라이언트 fallback

`source=api`에서 요청이 **4초 안에 응답하지 않거나 네트워크 오류**면 `fallback/popular.json`
(전역 인기 40권)으로 `trending` 행만 렌더하고, 인스펙터에 `fallback_level: 3 (client)` 배너를 띄운다.
"추천 API 장애 ≠ 메인 장애"를 프론트에서도 실증하는 장치다. 브라우저 내 JS 스코어링은 하지 않는다.

## mock 데이터와 그 한계

`mock/*.json`은 `scripts/make_mock.py`가 생성한다. 표준 라이브러리만 쓰고 **시드 42로 완전 결정적**이다.

```bash
python3 scripts/make_mock.py --cache /tmp/goodbooks_books.csv
```

원본은 [Goodbooks-10k](https://github.com/zygmuntz/goodbooks-10k) `books.csv`의
`ratings_count` 상위 400권이다. 캐시 파일은 저장소에 넣지 않는다(`--cache`로 외부 경로 지정).

**한계 — PDF에 "공개 데이터 시뮬레이션"으로 명시할 것:**

- **카테고리는 데모용 임의 배정이다.** 밀리 카테고리 14개와 세부 카테고리를 시드 고정 RNG로
  기계적으로 붙였을 뿐, 실제 태그 매핑(Goodreads shelves ↔ 밀리 카테고리)은 Day 2 콘텐츠 채널
  작업이다. `mock/books.json` 최상단 `_note`가 이 사실을 명시한다.
- **영어책이다.** 한글 UI 위에 영어 제목·저자·표지가 뜬다.
- 세부 카테고리 중 **IT·소설·철학 3그룹만 실제 캡처에서 옮긴 값**이고 나머지 11개 그룹은 데모용 구성이다.
- S2 카테고리 20개 중 6개(라이프스타일·외국어·매거진·사회·부모·웹툰/웹소설)는 대응 태그가 없어
  `supported: false`로 회색 비활성 처리되고, 인스펙터에 "데모 데이터 미지원"으로 표기된다.
- **출판사 컬럼이 없다.** S3에서 "좋아하는 출판사"를 고르면 배지를 생략하고 인스펙터에
  "데모 데이터 미지원"을 표시한다(§4-4 규칙).
- 표지는 `images.gr-assets.com` 원본 URL을 그대로 쓴다. 링크가 죽으면 `<img>`가 스스로 제거되고
  제목 첫 글자 + 해시 색상 플레이스홀더가 드러난다.
- `latency_ms`는 **고정값 + ±3ms 지터**다. 서버 측정값이 아니므로 **PDF 숫자로 쓰지 않는다**
  (p95는 로컬 `bench.py` 값만 쓴다).

## 폴더 구조

```text
demo/
├── index.html                 페이지 1장 (폰 프레임 + 인스펙터)
├── css/
│   ├── tokens.css             디자인 토큰 — 색·간격·폰트 전부 여기
│   ├── base.css               reset, 2열 레이아웃, 폰 프레임, 상태바, capture 모드
│   ├── onboarding.css         S0~S6
│   ├── home.css               S7~S8
│   └── inspector.css          우측 패널
├── js/
│   ├── app.js                 state + setState + render() + 이벤트 위임 + 프리셋
│   ├── api.js                 source=api|mock 스위치, API_BASE, 4초 타임아웃 → 클라이언트 fallback
│   ├── mock.js                mock 엔진 — 후보 생성·스냅샷·페르소나·행 조립·배지
│   ├── inspector.js           우측 패널 6섹션
│   └── screens/               ui.js(공용) · s0_start · onboarding_step(S1~S5 공용) · s6_persona · s7_home · s8_detail
├── config/onboarding.json     단계별 질문·옵션·선택 제한·레이아웃
├── mock/                      books(400권) · meta_onboarding · preferences_response · recommend_{pop,cf,hybrid,hybrid_div}
├── fallback/popular.json      서버 무응답 시 인기 40권 (/recommend 응답 형태)
└── scripts/make_mock.py       mock 생성기 (표준 라이브러리, 시드 42)
```

## 화면과 인스펙터

`S0` 시작(건너뛰기 → `consent=false` → S7) · `S1~S5` 온보딩(공용 렌더러 1벌 + 설정 JSON) ·
`S6` 페르소나 · `S7` 메인 · `S8` 책 상세 바텀시트 · `S9` 취향 재설정(= S1~S6 재진입, 새 스냅샷).

인스펙터 6섹션: ① 시나리오 프리셋 3종 ② 현재 단계의 신호 해석 ③ 이벤트 로그(최근 20건)
④ 파이프라인·latency 바(BUDGET 200ms 기준선) ⑤ `U_t` 가중치 α/β/γ ⑥ 모델 전환 라디오
(`pop`/`cf`/`hybrid`/`hybrid_div`) + `recommendation_id`/`model_version`/`snapshot_id`/
`fallback_level`/`dedup_removed`/행별 `channel_mix`.

시나리오 프리셋은 각각 상태를 초기화한 뒤 실행된다.

| 프리셋 | 결과 |
|---|---|
| 신규 유저 A | 저녁·IT/소설/철학·베스트셀러·개발/프로그래밍·SF·서양 + 시드 5권 자동 → S6 |
| 건너뛰기 유저 | `consent=false` → S7, `trending` 1행, `fallback_level 3`, 가중치 전부 0 |
| 재설정 유저 | `snap_01` + `reader_open` 2건 상태로 S7, "취향 다시 설정" 칩 강조 |

## 규칙

- 상태를 바꾸는 곳은 `setState` 하나, 화면을 그리는 곳은 `render()` 하나.
  화면별 파일은 `render(state) → HTML 문자열`만 반환하고 이벤트는 `app.js`가 위임으로 처리한다.
- 응답 스키마의 정본은 `.assets/설계서/백엔드 서빙/01_백엔드_서버_구성.md` §3이다.
  mock과 api는 **같은 형태**를 반환해야 한다.
- 밀리 로고·3D 캐릭터 등 자사 에셋은 쓰지 않는다. 캐릭터 자리는 이모지로 대체했다.
