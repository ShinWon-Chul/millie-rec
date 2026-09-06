"""books_kr.parquet → artifacts/serving/content_vectors_kr.npz (DATA-07).

D-12: 이웃과 같은 문자 2~4gram TF-IDF 를 TruncatedSVD 128 로 축소한 L2 float32.
MMR·ILD 의 ItemVectors 입력이다(PDF 각주 "다양성 벡터 = TF-IDF SVD 128").
"""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize

from millie_rec.contracts import DIR_ARTIFACTS, DIR_PROCESSED, SEED

SVD_DIM = 128  # D-12. PDF 각주 "다양성 벡터 = TF-IDF SVD 128"
NGRAM_RANGE = (2, 4)  # build_millie_edges.py 와 같은 값(중복 정의 — scripts 간 import 함정)
TEXT_COLS = ("title", "description", "curator_note")
MAX_BYTES = 50 * 1024 * 1024
VECTORS_NAME = "content_vectors_kr.npz"


def _text(value: object) -> str:
    return value if isinstance(value, str) and value else ""


def build_texts(books: pd.DataFrame) -> list[str]:
    """build_millie_edges.build_texts(with_tags=False) 와 같은 join (tags 제외, D-08)."""
    return [
        " ".join(p for p in (_text(row[c]) for c in TEXT_COLS) if p)
        for row in books[list(TEXT_COLS)].to_dict("records")
    ]


def vectors(texts: list[str]) -> np.ndarray:
    """TF-IDF(char_wb 2~4gram) → TruncatedSVD(min(128, n-1, features-1), SEED) → 행 L2 → float32."""
    tfidf = TfidfVectorizer(analyzer="char_wb", ngram_range=NGRAM_RANGE, min_df=1).fit_transform(
        texts
    )
    # TruncatedSVD 는 n_components < n_features 이고 실질 ≤ n_samples-1 — 소형 픽스처 가드
    dim = max(1, min(SVD_DIM, tfidf.shape[0] - 1, tfidf.shape[1] - 1))
    reduced = TruncatedSVD(n_components=dim, random_state=SEED).fit_transform(tfidf)
    return normalize(reduced).astype(np.float32)


def export_vectors(books_path: Path, out_path: Path) -> int:
    """book_id 오름차순으로 book_ids·vectors 를 한 npz 에 쓴다(vectors_kr.py 가 읽는 키)."""
    books = pd.read_parquet(books_path).sort_values("book_id").reset_index(drop=True)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez(
        out_path,
        book_ids=books["book_id"].to_numpy(dtype=np.int64),
        vectors=vectors(build_texts(books)),
    )
    size = out_path.stat().st_size
    assert size < MAX_BYTES, f"{out_path.name} {size}B ≥ {MAX_BYTES}B — 서빙 산출물 상한 초과"
    return size


def main() -> None:
    parser = argparse.ArgumentParser(description="밀리 카탈로그 다양성 벡터 export")
    parser.add_argument("--books", type=Path, default=DIR_PROCESSED / "books_kr.parquet")
    parser.add_argument("--out", type=Path, default=DIR_ARTIFACTS / "serving" / VECTORS_NAME)
    args = parser.parse_args()
    size = export_vectors(args.books, args.out)
    print(f"{args.out.name} {size / 1024:.1f}KB seed={SEED} → {args.out}")


if __name__ == "__main__":
    main()
