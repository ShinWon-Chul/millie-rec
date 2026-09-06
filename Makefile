# 자주 쓰는 명령만. 새 타깃 추가는 Advisor 승인.
.PHONY: setup data eval demo serve smoke bench test lint pdf mock export-serving demo-serve docker-up docker-down millie-collect millie-reviews millie-subcats millie-build millie-edges millie-popularity millie-export millie

setup:        ## 의존성 설치
	uv sync

data:         ## Track A(Goodbooks) 다운로드 + parquet 캐시 + split(holdout|temporal) 요약
	uv run python -m millie_rec.app.cli data

millie-collect: ## Track B 밀리 공개 도서 페이지 수집. playwright 는 dev 전용·런타임 미포함(임시 설치). 멱등·체크포인트·2.5s·식별 UA
	uv run --with playwright python scripts/collect_millie.py

millie-reviews: ## 리뷰 JSONL → review_*.parquet + results/review_tuples_report.json + artifacts/serving/review_agg_kr.json. books_kr 파이프라인(freeze D72)과 독립
	uv run python scripts/build_millie_reviews.py && uv run pytest tests/data/test_millie_reviews_build.py --no-header && uv run python scripts/export_millie_reviews.py

millie-subcats: ## 3depth JSONL → subcategories_kr.parquet + results/subcat_meta.json·subcat_coverage.csv, books_kr.parquet·books_kr.json 의 subcategories 키만 패치(다른 키 바이트 동일)
	uv run pytest tests/data/test_millie_subcats.py --no-header && uv run python scripts/build_millie_subcats.py

millie-build: ## JSONL → books_kr.parquet + id_map.csv(append-only) + 커버리지 게이트(이웃 게이트는 millie-edges 뒤)
	uv run python scripts/build_millie_catalog.py && uv run pytest tests/data/test_millie_catalog.py --no-header

millie-edges: ## content_sim + category_best → item_edges_kr.parquet + 이웃 게이트 3
	uv run python scripts/build_millie_edges.py && uv run pytest tests/data/test_millie_edges.py --no-header

millie-popularity: ## books_kr.parquet → popularity_kr.parquet (all 세그먼트 Must · 연령×성별 Should, D-15)
	uv run python scripts/build_millie_popularity.py

millie-export: ## artifacts/serving/{books_kr,item_edges_kr,popularity_kr}.json + content_vectors_kr.npz + demo/fallback/popular.json (description 미포함)
	uv run python scripts/export_millie_serving.py && uv run python scripts/export_millie_vectors.py && uv run python scripts/export_millie_fallback.py

millie: millie-build millie-edges millie-popularity millie-export  ## 수집 이후 전체 재빌드

eval:         ## 전 variant 평가 → results/latest.csv
	uv run python -m millie_rec.app.cli eval --variant all

demo:         ## 본인 5권 cold-start 정성 케이스 → report/demo_5books.md (D-13). 예: make demo SEEDS=1,2,3,4,5 · 검색: uv run python -m millie_rec.app.cli demo --find 제목
	uv run python -m millie_rec.app.cli demo --seeds $(SEEDS) > report/demo_5books.md && echo "→ report/demo_5books.md"

serve:        ## FastAPI 로컬 서빙 (데모 http://localhost:8000/?source=api). 아티팩트 없어도 뜬다(fallback level 3)
	uv run uvicorn millie_rec.app.server:app --port 8000

smoke:        ## 로컬 기동 스모크 — 모든 브리프의 완료 기준(.claude/rules/local-run.md). 서버를 8010 포트로 띄워 3개 확인 후 종료
	@uv run uvicorn millie_rec.app.server:app --port 8010 --log-level warning & echo $$! > .uvicorn.pid; sleep 3; \
	 ok=1; \
	 curl -fsS localhost:8010/health >/dev/null && echo "smoke: /health 200" || ok=0; \
	 curl -fsS -o /dev/null localhost:8010/ && echo "smoke: / (demo static) 200" || ok=0; \
	 curl -fsS "localhost:8010/api/recommend?seeds=1,2,3&k=5" >/dev/null && echo "smoke: /api/recommend 200" || ok=0; \
	 kill $$(cat .uvicorn.pid) 2>/dev/null; rm -f .uvicorn.pid; \
	 [ $$ok = 1 ] && echo "smoke: PASS" || (echo "smoke: FAIL"; exit 1)

bench:        ## p50/p95/p99 → results/latency.json (serve 가 떠 있어야 함)
	uv run python -m millie_rec.serving.bench

mock:         ## artifacts/serving/* → demo/mock/*.json (mock 은 손으로 쓰지 않는다). cli mock 서브커맨드는 없다
	uv run python demo/scripts/make_mock.py

export-serving: ## 서빙용 축소 아티팩트 → artifacts/serving/ (파일당 <50MB, GitHub 한도. Dockerfile COPY 대상)
	uv run python -m millie_rec.app.cli export-serving

demo-serve:   ## 정적 데모 로컬 확인: http://localhost:8080/?source=mock
	cd demo && python3 -m http.server 8080

docker-up:    ## 로컬 Docker 스모크(배포 02 §4-2) — 빌드 → 기동(/data 볼륨) → 3점 스모크 → URL. 예: make docker-up PORT=8001
	PORT=$(or $(PORT),8000) scripts/docker_up.sh

docker-down:  ## 컨테이너 정리(볼륨·이미지 유지). 전부: scripts/docker_down.sh --all
	scripts/docker_down.sh

test:
	uv run pytest -q

lint:
	uv run ruff format . && uv run ruff check .

pdf:          ## draft.md → HTML 로컬 미리보기(mermaid 렌더). 제출 조판은 Notion 붙여넣기 → PDF 내보내기 5장.
	cd report && pandoc draft.md -s --mathjax -H mermaid.html --metadata title="밀리의서재 메인 추천 시스템 설계" -o draft.html && open draft.html
