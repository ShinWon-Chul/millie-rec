# 자주 쓰는 명령만. 새 타깃 추가는 Advisor 승인.
.PHONY: setup data eval demo serve smoke bench test lint pdf mock export-serving demo-serve millie-collect millie-build millie-edges millie-export millie

setup:        ## 의존성 설치
	uv sync

data:         ## Track A(Goodbooks) 다운로드 + parquet 캐시 + split(holdout|temporal) 요약
	uv run python -m millie_rec.app.cli data

millie-collect: ## Track B 밀리 공개 도서 페이지 수집. playwright 는 dev 전용·런타임 미포함(임시 설치). 멱등·체크포인트·2.5s·식별 UA
	uv run --with playwright python scripts/collect_millie.py

millie-build: ## JSONL → data/processed/books_kr.parquet + data/id_map.csv(append-only) + 커버리지 게이트
	uv run python scripts/build_millie_catalog.py && uv run pytest tests/data -q

millie-edges: ## content_sim + category_best → item_edges_kr.parquet (이웃 게이트 3)
	uv run python scripts/build_millie_edges.py

millie-export: ## artifacts/serving/{books_kr,item_edges_kr,popularity_kr}.json + content_vectors_kr.npz (description 미포함)
	uv run python scripts/export_millie_serving.py

millie: millie-build millie-edges millie-export  ## 수집 이후 전체 재빌드

eval:         ## 전 variant 평가 → results/latest.csv
	uv run python -m millie_rec.app.cli eval --variant all

demo:         ## 본인 5권 cold-start 정성 케이스. 예: make demo SEEDS=1,2,3,4,5
	uv run python -m millie_rec.app.cli demo --seeds $(SEEDS)

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

mock:         ## serving/schemas.py → demo/mock/*.json (mock 은 손으로 쓰지 않는다)
	uv run python -m millie_rec.app.cli mock

export-serving: ## 서빙용 축소 아티팩트 → artifacts/serving/ (파일당 <50MB, GitHub 한도. Dockerfile COPY 대상)
	uv run python -m millie_rec.app.cli export-serving

demo-serve:   ## 정적 데모 로컬 확인: http://localhost:8080/?source=mock
	cd demo && python3 -m http.server 8080

test:
	uv run pytest -q

lint:
	uv run ruff format . && uv run ruff check .

pdf:          ## draft.md → HTML (브라우저에서 PDF 인쇄). LaTeX 없음.
	cd report && pandoc draft.md -s --metadata title="밀리의서재 메인 추천 시스템 설계" -o draft.html && open draft.html
