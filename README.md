# millie-rec

밀리의서재 메인 영역 추천 시스템 설계 과제의 **실측 데모**. 설계 문서(PDF)에 들어가는 비교표·정성 케이스·지연 시간을 만든다.

```
uv sync
make data            # 공개 데이터 다운로드 → parquet → temporal split
make eval            # Popularity / Item-KNN / Hybrid / Hybrid+MMR → results/latest.csv
make demo SEEDS=...  # 온보딩 5권 → 추천 출력 (cold-start 정성 케이스)
make serve && make bench
```

구조: Vertical Slice — `src/millie_rec/{data,retrieval,ranking,reranking,evaluation,serving}` 이 각각 파이프라인 한 단계를 소유하고 `contracts.py` 의 DTO/Protocol 로만 연결된다. `app/` 이 조립한다.

데이터 (2트랙):
- **Track A 정량 평가** — Goodbooks-10k(CC BY-SA 4.0, github.com/zygmuntz/goodbooks-10k). 유저 단위 평점 로그로 Recall@20/NDCG@10/ILD@10 비교표를 만든다. 타임스탬프가 없어 유저별 random holdout(`split_mode=holdout`).
- **Track B 데모 카탈로그** — 밀리의서재 공개 도서 페이지(sitemap 1,000 + 페이지 내 "분야 BEST"·어워즈 링크 확장, **2026-09-04~05 수집, 9,580페이지 → 유효 9,450권**). 비로그인 화면의 수치·메타·표지 URL만 저장하고 리뷰 텍스트·필명은 저장하지 않는다. 책 소개 텍스트는 TF-IDF 입력 전용으로 화면·API에 노출하지 않는다. 표지는 밀리 CDN 핫링크만. 밀리의서재 요청 시 즉시 삭제한다. 수집 예절: 프로세스당 요청 간 2.5초(병렬 2, 총 ≈0.3 req/s)·식별 UA(`millie-rec-demo-assignment/0.1`)·HTML 미보관. 재현: `.assets/설계서/데이터 소스/03_밀리_데이터_적재_트래킹.md` §4.
- 두 트랙의 숫자를 섞지 않는다. 비교표는 Track A, 데모 화면은 Track B.
