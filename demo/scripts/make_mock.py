#!/usr/bin/env python3
"""데모용 mock 데이터 생성기 — 표준 라이브러리만 사용, 시드 42로 완전 결정적.

Goodbooks-10k `books.csv`(영어책 메타)에서 ratings_count 상위 400권을 뽑아
밀리 카테고리를 임의 배정한다. 실제 태그 매핑은 Day 2 콘텐츠 채널 작업이므로
여기서는 하지 않는다 — books.json 최상단 `_note`가 그 사실을 명시한다.

    python3 scripts/make_mock.py --cache /path/to/books.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import sys
import urllib.request
from pathlib import Path

CSV_URL = "https://raw.githubusercontent.com/zygmuntz/goodbooks-10k/master/books.csv"
POOL_SIZE = 400
SEED = 42

# 밀리 온보딩 카테고리 20개. 문서 §8에서 "대응 태그 없음"인 6개는 supported=False.
UNSUPPORTED = ["라이프스타일", "외국어", "매거진", "사회", "부모", "웹툰/웹소설"]
CATEGORIES = [
    "소설",
    "인문",
    "경제경영",
    "자기계발",
    "에세이/시",
    "라이프스타일",
    "어린이",
    "과학",
    "외국어",
    "철학",
    "역사",
    "매거진",
    "사회",
    "부모",
    "청소년",
    "종교",
    "IT",
    "여행",
    "만화",
    "웹툰/웹소설",
]
# IT·소설·철학은 캡처에서 확인된 값 그대로. 나머지는 데모용 임의 구성.
SUBCATEGORIES = {
    "IT": [
        "개발/프로그래밍",
        "그래픽/멀티미디어",
        "IT 교양",
        "e비즈니스",
        "오피스 활용",
        "컴퓨터 수험서",
    ],
    "소설": ["추리/스릴러", "SF", "판타지", "영미 소설", "한국 소설", "일본 소설", "유럽 소설"],
    "철학": ["동양", "정치/경제", "예술/문화", "서양"],
    "인문": ["심리학", "인물/평전", "언어/기호", "문화인류"],
    "경제경영": ["경제 일반", "재테크/투자", "마케팅/브랜드", "리더십"],
    "자기계발": ["성공/처세", "시간 관리", "습관/루틴", "공부법"],
    "에세이/시": ["국내 에세이", "해외 에세이", "시", "그림 에세이"],
    "과학": ["물리/천문", "생명과학", "수학", "과학 교양"],
    "역사": ["세계사", "한국사", "고대 문명", "전쟁사"],
    "어린이": ["그림책", "창작 동화", "학습 만화", "어린이 교양"],
    "청소년": ["청소년 소설", "진로/공부", "청소년 교양"],
    "종교": ["기독교", "불교", "종교학"],
    "만화": ["그래픽 노블", "코믹스", "카툰"],
    "여행": ["국내 여행", "해외 여행", "테마 여행"],
}
# goodbooks-10k는 영미 소설 편중이라 배정 가중치도 그에 맞춘다.
WEIGHTS = {
    "소설": 26,
    "청소년": 10,
    "어린이": 8,
    "인문": 8,
    "에세이/시": 6,
    "과학": 6,
    "역사": 6,
    "경제경영": 5,
    "자기계발": 5,
    "철학": 5,
    "종교": 4,
    "만화": 3,
    "여행": 3,
    "IT": 3,
}
PERSONAS = {
    "모험·전략": ("오디세우스", "오디세이아", "지혜로 승리하리라!", ("경제경영", "자기계발", "IT")),
    "추리·분석": (
        "셜록 홈즈",
        "주홍색 연구",
        "사소한 것이 가장 중요하다.",
        ("소설", "과학", "철학"),
    ),
    "이상·도전": ("돈키호테", "돈키호테", "이룰 수 없는 꿈을 꾸리라!", ("인문", "역사", "사회")),
    "내면·성장": (
        "제인 에어",
        "제인 에어",
        "나는 나 자신의 주인입니다.",
        ("에세이/시", "라이프스타일"),
    ),
}


def load_pool(cache: Path) -> list[dict]:
    if not cache.exists():
        cache.parent.mkdir(parents=True, exist_ok=True)
        print(f"[make_mock] books.csv 다운로드 → {cache}", file=sys.stderr)
        urllib.request.urlretrieve(CSV_URL, cache)
    with cache.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    rows.sort(key=lambda r: -int(r["ratings_count"] or 0))
    return rows[:POOL_SIZE]


def assign(rows: list[dict]) -> list[dict]:
    """시드 고정 RNG로 카테고리·세부 카테고리·PDF 여부를 결정적으로 배정."""
    rng = random.Random(SEED)
    names = list(WEIGHTS)
    weights = [WEIGHTS[n] for n in names]
    books = []
    for rank, row in enumerate(rows, start=1):
        picked = rng.choices(names, weights=weights, k=rng.choice([1, 1, 1, 2]))
        cats = list(dict.fromkeys(picked))
        subs = []
        for cat in cats:
            pool = SUBCATEGORIES[cat]
            subs += rng.sample(pool, k=min(len(pool), rng.choice([1, 1, 2])))
        year = row["original_publication_year"]
        books.append(
            {
                "book_id": int(row["book_id"]),
                "title": row["title"],
                "authors": row["authors"],
                "image_url": row["image_url"],
                "average_rating": float(row["average_rating"] or 0),
                "ratings_count": int(row["ratings_count"] or 0),
                "year": int(float(year)) if year else None,
                "pop_rank": rank,
                "format": "PDF" if rng.random() < 0.34 else None,
                "categories": cats,
                "subcategories": list(dict.fromkeys(subs)),
            }
        )
    return books


def josa(word: str, with_final: str, without: str) -> str:
    """받침 유무로 조사를 고른다. 한글 음절이 아니면(영문·숫자) 받침 없음으로 취급."""
    if not word:
        return without
    code = ord(word[-1])
    final = (code - 0xAC00) % 28 if 0xAC00 <= code <= 0xD7A3 else 0
    if final == 8 and without == "로":  # ㄹ 받침은 '으로'가 아니라 '로'
        return without
    return with_final if final else without


def reviews_ko(n: int) -> str:
    if n >= 10000:
        return f"{round(n / 10000)}만"
    if n >= 1000:
        return f"{round(n / 1000)}천"
    return str(n)


def badge_for(book: dict, criterion: str, seed_authors: set[str]) -> dict | None:
    """문서 §4-4: S3 선택 기준이 카드 배지 타입을 결정한다(Artwork Personalization)."""
    if criterion == "베스트셀러":
        return {"type": "bestseller", "text": f"인기 {book['pop_rank']}위"}
    if criterion == "리뷰, 별점 등 대중의 평가":
        return {
            "type": "rating",
            "text": f"★ {book['average_rating']:.2f} · 리뷰 {reviews_ko(book['ratings_count'])}",
        }
    if criterion == "좋아하는 작가":
        first = book["authors"].split(",")[0].strip()
        return {"type": "author", "text": f"{first}의 다른 책"} if first in seed_authors else None
    if criterion == "화제작 (SNS,셀럽 추천, 수상도서)":
        recent = (book["year"] or 0) >= 2010
        return {"type": "buzz", "text": "요즘 화제" if recent else "수상작"}
    return None  # 좋아하는 출판사 — Goodbooks-10k에 출판사 컬럼이 없어 배지 생략


def item(book: dict, pos: int, score: float, channels: list[str], badge, reason) -> dict:
    return {
        "book_id": book["book_id"],
        "title": book["title"],
        "authors": book["authors"],
        "image_url": book["image_url"],
        "position": pos,
        "score": round(score, 3),
        "source_channels": channels,
        "badge": badge,
        "reason": reason,
        "format": book["format"],
    }


def persona_for(categories: list[str], criterion: str) -> dict:
    """지배 카테고리(첫 선택) → 페르소나 4종 중 1개. 설명은 실제 선택값을 문장에 삽입."""
    name, work, quote = PERSONAS["모험·전략"][:3]
    matches = (p[:3] for cat in categories for p in PERSONAS.values() if cat in p[3])
    name, work, quote = next(matches, (name, work, quote))
    head = (
        f"{categories[0]}{josa(categories[0], '과', '와')} {categories[1]}"
        if len(categories) > 1
        else (categories[0] if categories else "다양한 분야")
    )
    crit = criterion or "나만의 기준"
    return {
        "name": name,
        "work": work,
        "quote": quote,
        "description": (
            f"회원님은 {head}{josa(head, '을', '를')} 즐기고, "
            f"{crit}{josa(crit, '으로', '로')} 책을 고르는 독서가입니다."
        ),
    }


def build_rows(
    books: list[dict], cats: list[str], criterion: str, model: str
) -> tuple[list[dict], int]:
    """계약 형태 검증용 예시 rows. 런타임 조립은 js/mock.js가 담당한다."""
    seeds = [b for b in books if set(b["categories"]) & set(cats)][:5]
    seed_ids = {b["book_id"] for b in seeds}
    seed_authors = {s["authors"].split(",")[0].strip() for s in seeds}
    in_cat = [b for b in books if set(b["categories"]) & set(cats) and b["book_id"] not in seed_ids]
    rest = [b for b in books if b["book_id"] not in seed_ids and b not in in_cat]

    def mk(pool, channels, reason_tpl, n=12):
        out = []
        for i, b in enumerate(pool[:n]):
            reason = reason_tpl.format(seed=seeds[0]["title"]) if reason_tpl else None
            out.append(
                item(b, i, 0.9 - i * 0.03, channels, badge_for(b, criterion, seed_authors), reason)
            )
        return out

    by_rating = sorted(in_cat, key=lambda b: -b["average_rating"])
    by_pop = sorted(rest, key=lambda b: -b["ratings_count"])
    by_year = sorted(books, key=lambda b: -(b["year"] or 0))
    if model == "pop":
        by_rating, by_year = by_pop, by_pop
    rows = [
        {
            "row_id": "persona_shelf",
            "title": "오디세우스의 서가",
            "purpose": "discover",
            "channel_mix": {"content": 12, "itemknn": 0, "popularity": 0},
            "items": []
            if model == "cf"
            else mk(by_rating, ["content"], "『{seed}』을 좋아하셨다면"),
        },
        {
            "row_id": "similar_readers",
            "title": "비슷한 독자들이 읽은 책",
            "purpose": "discover",
            "channel_mix": {"content": 0, "itemknn": 12, "popularity": 0},
            "items": mk(by_pop, ["itemknn"], None),
        },
        {
            "row_id": "trending",
            "title": "지금 많이 읽는 책",
            "purpose": "fallback",
            "channel_mix": {"content": 0, "itemknn": 0, "popularity": 12},
            "items": mk(sorted(books, key=lambda b: -b["ratings_count"]), ["popularity"], None),
        },
        {
            "row_id": "fresh_picks",
            "title": "새로운 발견",
            "purpose": "explore",
            "channel_mix": {"content": 12, "itemknn": 0, "popularity": 0},
            "items": mk(by_year, ["content"], None),
        },
    ]
    seen, removed = set(), 0
    for row in rows:
        kept = []
        for it in row["items"]:
            if it["book_id"] in seen:
                removed += 1
                continue
            seen.add(it["book_id"])
            it["position"] = len(kept)
            kept.append(it)
        row["items"] = kept
    return rows, removed


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default="/tmp/goodbooks_books.csv", help="books.csv 캐시 경로")
    ap.add_argument("--out", default=str(Path(__file__).resolve().parent.parent))
    args = ap.parse_args()
    out = Path(args.out)
    (out / "mock").mkdir(parents=True, exist_ok=True)
    (out / "fallback").mkdir(parents=True, exist_ok=True)

    books = assign(load_pool(Path(args.cache)))
    def write(p, o):
        (out / p).write_text(json.dumps(o, ensure_ascii=False, indent=1), encoding="utf-8")

    write(
        "mock/books.json",
        {"_note": "mock — 카테고리는 데모용 임의 배정", "seed": SEED, "books": books},
    )
    write(
        "mock/meta_onboarding.json",
        {
            "categories": [{"name": c, "supported": c not in UNSUPPORTED} for c in CATEGORIES],
            "subcategories": SUBCATEGORIES,
            "readingTimes": [
                "아침, 하루를 시작할 때",
                "점심시간이나 짧은 휴식 시간",
                "저녁, 하루를 마치며",
                "잠들기 전",
                "주말이나 휴일, 여유로울 때 몰아서",
            ],
            "criteria": [
                "좋아하는 작가",
                "좋아하는 출판사",
                "베스트셀러",
                "화제작 (SNS,셀럽 추천, 수상도서)",
                "리뷰, 별점 등 대중의 평가",
            ],
        },
    )

    cats, criterion = ["IT", "소설", "철학"], "베스트셀러"
    write(
        "mock/preferences_response.json",
        {
            "user_key": "u_9f21",
            "preference_snapshot_id": "snap_01",
            "created_at": "2026-09-04T23:36:00+09:00",
            "persona": persona_for(cats, criterion),
        },
    )
    for model in ("pop", "cf", "hybrid", "hybrid_div"):
        rows, removed = build_rows(books, cats, criterion, model)
        write(
            f"mock/recommend_{model}.json",
            {
                "recommendation_id": "rec_8f3a2c",
                "model_version": f"{model}_mock",
                "preference_snapshot_id": "snap_01",
                "user_key": "u_9f21",
                "fallback_level": 0,
                "cell": "B",
                "latency_ms": {
                    "feature": 3,
                    "retrieval": 21,
                    "ranking": 14,
                    "rerank": 4,
                    "compose": 2,
                    "total": 44,
                },
                "user_state_weights": {"alpha": 0.6, "beta": 0.3, "gamma": 0.1},
                "dedup_removed": removed,
                "rows": rows,
            },
        )

    pop = sorted(books, key=lambda b: -b["ratings_count"])[:40]
    write(
        "fallback/popular.json",
        {
            "recommendation_id": "rec_client_fb",
            "model_version": "static_popular",
            "preference_snapshot_id": None,
            "user_key": None,
            "fallback_level": 3,
            "cell": None,
            "latency_ms": {
                "feature": 0,
                "retrieval": 0,
                "ranking": 0,
                "rerank": 0,
                "compose": 0,
                "total": 0,
            },
            "user_state_weights": {"alpha": 0.0, "beta": 0.0, "gamma": 0.0},
            "dedup_removed": 0,
            "rows": [
                {
                    "row_id": "trending",
                    "title": "지금 많이 읽는 책",
                    "purpose": "fallback",
                    "channel_mix": {"content": 0, "itemknn": 0, "popularity": 40},
                    "items": [
                        item(b, i, 1.0 - i * 0.01, ["popularity"], None, None)
                        for i, b in enumerate(pop)
                    ],
                }
            ],
        },
    )
    print(f"[make_mock] {len(books)}권 · mock/ 6개 · fallback/ 1개 생성 완료")


if __name__ == "__main__":
    main()
