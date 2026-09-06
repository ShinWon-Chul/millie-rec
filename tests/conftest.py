"""소형 합성 데이터. 실데이터 대신 모든 슬라이스 테스트가 이것을 쓴다."""

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from millie_rec.contracts import COL_EVENT, COL_ITEM, COL_RATING, COL_TS, COL_USER, SEED

N_USERS, N_ITEMS, N_ROWS = 20, 50, 400

N_SAMPLE_BOOKS = 20  # millie_serving_sample 권수
SAMPLE_CATEGORIES = ("소설", "에세이", "경제경영", "인문")
SAMPLE_COVER_HOSTS = ("img.millie.co.kr", "image.millie.co.kr", "cover.millie.co.kr")
SAMPLE_FORMATS = ("전자책", "오디오북", "챗북")
SAMPLE_VECTOR_DIM = 8


@pytest.fixture(scope="session")
def interactions() -> pd.DataFrame:
    """유저 20 × 아이템 50, ts 오름차순. 인기도 편향을 줘 popularity 가 의미 있게."""
    rng = np.random.default_rng(SEED)
    p = rng.dirichlet(np.ones(N_ITEMS) * 0.3)
    df = pd.DataFrame(
        {
            COL_USER: rng.integers(0, N_USERS, N_ROWS),
            COL_ITEM: rng.choice(N_ITEMS, N_ROWS, p=p),
            COL_TS: pd.to_datetime("2020-01-01")
            + pd.to_timedelta(np.sort(rng.integers(0, 365, N_ROWS)), "D"),
            COL_EVENT: "completion",
            COL_RATING: rng.integers(1, 6, N_ROWS).astype(float),
        }
    )
    return df.drop_duplicates([COL_USER, COL_ITEM]).reset_index(drop=True)


@pytest.fixture(scope="session")
def item_vectors() -> np.ndarray:
    """아이템 50 × 8 차원 콘텐츠 벡터 (ILD·MMR 테스트용)."""
    rng = np.random.default_rng(SEED)
    return rng.random((N_ITEMS, 8))


def _sample_book(i: int) -> dict:
    """books_kr.json 28키 행 1개. 자격 없는 3권: 18(외부 호스트)·19(title None)·20(성인 표지)."""
    cat = SAMPLE_CATEGORIES[(i - 1) % len(SAMPLE_CATEGORIES)]
    host = SAMPLE_COVER_HOSTS[(i - 1) % len(SAMPLE_COVER_HOSTS)]
    book_format = SAMPLE_FORMATS[(i - 1) % len(SAMPLE_FORMATS)]
    image_url = f"https://{host}/cover/{i}.jpg"
    if i == 18:
        image_url = f"https://cdn.example.com/{i}.jpg"
    elif i == 20:
        image_url = "https://d1miajbjsyro89.cloudfront.net/adult-cover-a.webp"
    measured = i % 2 == 0 or i < 15  # 홀수 id ≥15 는 완독지수 결측 → category_prior
    resid_z = round((i % 7 - 3) * 0.5, 3) if measured else 0.0
    len_z = round((i % 5 - 2) * 0.4, 3)
    difficulty = round(float(1 / (1 + np.exp(resid_z))), 4) if measured else None
    return {
        "book_id": i,
        "title": None if i == 19 else f"밀리 표본 도서 {i}",
        "authors": f"저자 {i}",
        "image_url": image_url,
        "average_rating": round(3.5 + i % 5 * 0.2, 1),
        "ratings_count": i * 3,
        "original_publication_year": 2000 + i,
        "categories": [cat],
        "subcategories": [],
        "tags": f"{cat} 전자책",
        "publisher": "표본 출판사",
        "subtitle": None,
        "pub_date": f"20{i:02d}.01.01",
        "book_format": book_format,
        "formats": [book_format],
        "pop_rank": i,
        "millie_label": None,
        "review_count": i * 3,
        "shelf_count": 10_000 - i * 100,
        "completion_prob": 50 + i,
        "category_avg_prob": 60,
        "expected_min": 100 + i * 10,
        "category_avg_min": 200,
        "resid_z": resid_z,
        "len_z": len_z,
        "difficulty": difficulty,
        "difficulty_source": "millie_index" if measured else "category_prior",
        "top_segment": "40대 여성",
    }


@pytest.fixture(scope="session")
def millie_serving_sample(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """20권 합성 서빙 산출물 4개(books_kr·item_edges_kr·popularity_kr json + npz).

    book_id 1..20, pop_rank == book_id. 자격 없는 3권: 18(호스트 cdn.example.com) ·
    19(title None) · 20(adult-cover). 홀수 id ≥15 는 difficulty_source=category_prior
    (difficulty None). 실 artifacts/serving 은 어떤 테스트도 읽지 않는다.
    """
    out = tmp_path_factory.mktemp("millie_serving_sample")
    ids = list(range(1, N_SAMPLE_BOOKS + 1))
    books = [_sample_book(i) for i in ids]

    weights = (0.9, 0.8, 0.7, 0.6, 0.2)
    edges = {
        str(i): [
            [(i + d - 1) % N_SAMPLE_BOOKS + 1, w, "content_sim" if n < 4 else "category_best"]
            for n, (d, w) in enumerate(zip(range(1, 6), weights, strict=True))
        ]
        for i in ids
    }
    popularity = [
        {"book_id": i, "segment": "all", "score": float(10_000 - i * 100), "rank": i} for i in ids
    ]

    rng = np.random.default_rng(SEED)
    vectors = rng.random((N_SAMPLE_BOOKS, SAMPLE_VECTOR_DIM))
    vectors = vectors / np.linalg.norm(vectors, axis=1, keepdims=True)
    np.savez(
        out / "content_vectors_kr.npz",
        book_ids=np.array(ids, dtype=np.int64),
        vectors=vectors.astype(np.float32),
    )
    for name, payload in (
        ("books_kr.json", books),
        ("item_edges_kr.json", edges),
        ("popularity_kr.json", popularity),
    ):
        (out / name).write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return out
