"""persona.py — 계약(4종 텍스트) · 정확성(매핑·조사·문장) · 안전성(항상 존재).

Phase 5 '서빙 Must 완성'(.planning/ROADMAP.md) Plan 05-04. 05-CONTEXT D-16 · revision A1.
"""

import hashlib

from millie_rec.contracts import Persona
from millie_rec.serving.persona import (
    CATEGORY_TO_PERSONA,
    PERSONAS,
    _josa,
    assign_persona,
    persona_index,
)

# demo/mock/preferences_response.json 의 description 정본 문장(revision A1)
MOCK_SENTENCE = "회원님은 IT와 소설을 즐기고, 베스트셀러로 책을 고르는 독서가입니다."


def _sha_index(name: str) -> int:
    return int(hashlib.sha256(name.encode()).hexdigest()[:8], 16) % 4


# ── 계약 ────────────────────────────────────────────────────────────────
def test_personas_four_names_works_quotes():
    assert [p.name for p in PERSONAS] == ["오디세우스", "셜록 홈즈", "돈키호테", "제인 에어"]
    assert PERSONAS[0].work == "오디세이아" and PERSONAS[0].quote == "지혜로 승리하리라!"
    assert PERSONAS[1].work == "주홍색 연구" and PERSONAS[1].quote == "사소한 것이 가장 중요하다."
    assert PERSONAS[2].work == "돈키호테" and PERSONAS[2].quote == "이룰 수 없는 꿈을 꾸리라!"
    assert PERSONAS[3].work == "제인 에어" and PERSONAS[3].quote == "나는 나 자신의 주인입니다."


# ── 정확성 ──────────────────────────────────────────────────────────────
def test_persona_index_mapping_table_and_dominant_first_category():
    assert persona_index(["경제경영"]) == persona_index(["자기계발"]) == persona_index(["IT"]) == 0
    assert [persona_index([c]) for c in ("소설", "과학", "철학")] == [1, 1, 1]
    assert [persona_index([c]) for c in ("인문", "역사", "사회")] == [2, 2, 2]
    assert [persona_index([c]) for c in ("에세이/시", "라이프스타일")] == [3, 3]
    assert persona_index(["인문", "IT"]) == 2  # 지배 카테고리 = categories[0]
    assert set(CATEGORY_TO_PERSONA.values()) == {0, 1, 2, 3}


def test_persona_index_unmapped_is_sha256_deterministic_and_empty_is_zero():
    assert "오디오북" not in CATEGORY_TO_PERSONA
    assert persona_index(["오디오북"]) == _sha_index("오디오북")
    assert persona_index(["오디오북"]) == persona_index(["오디오북"])
    assert persona_index(["미분류"]) == _sha_index("미분류")
    assert persona_index([]) == 0


def test_josa_final_consonant_rules_including_rieul_and_non_hangul():
    assert _josa("소설", "을", "를") == "을"
    assert _josa("IT", "을", "를") == "를"  # 한글 음절 아님 → 받침 없음 취급
    assert _josa("베스트셀러", "으로", "로") == "로"
    assert _josa("평가", "으로", "로") == "로"
    assert _josa("취향", "으로", "로") == "으로"
    assert _josa("서울", "으로", "로") == "로"  # ㄹ 받침 예외
    assert _josa("IT", "과", "와") == "와"
    assert _josa("소설", "과", "와") == "과"


def test_assign_persona_description_matches_mock_sentence():
    p = assign_persona(["IT", "소설"], "베스트셀러")
    assert p.name == "오디세우스" and p.work == "오디세이아"
    assert p.quote == "지혜로 승리하리라!"
    assert p.description == MOCK_SENTENCE
    flipped = assign_persona(["소설", "IT"], "베스트셀러")
    assert flipped.name == "셜록 홈즈"
    assert (
        flipped.description == "회원님은 소설과 IT를 즐기고, 베스트셀러로 책을 고르는 독서가입니다."
    )


# ── 안전성 ──────────────────────────────────────────────────────────────
def test_assign_persona_always_returns_persona_even_without_inputs():
    solo = assign_persona(["소설"], None)
    assert solo.description == "회원님은 소설을 즐기고, 취향으로 책을 고르는 독서가입니다."
    empty = assign_persona([], "리뷰, 별점 등 대중의 평가")
    assert isinstance(empty, Persona) and empty.name == "오디세우스"
    assert empty.description == (
        "회원님은 다양한 분야를 즐기고, 리뷰, 별점 등 대중의 평가로 책을 고르는 독서가입니다."
    )
    assert isinstance(assign_persona([], None), Persona)
