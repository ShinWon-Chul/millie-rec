"""페르소나 4종 매핑 — S6 설명 레이어, 모델 입력 아님(화면 01 §4-5, 05-CONTEXT D-16).

항상 존재한다(미매핑은 sha256 결정적). 조사는 받침 판정(revision A1).
"""

import hashlib
from collections.abc import Sequence
from dataclasses import replace

from millie_rec.contracts import Persona

# 화면 01 §4-5 페르소나 4종. description 은 템플릿을 채운 뒤 replace 로 넣는다
PERSONAS: tuple[Persona, ...] = (
    Persona("오디세우스", "오디세이아", "지혜로 승리하리라!", ""),
    Persona("셜록 홈즈", "주홍색 연구", "사소한 것이 가장 중요하다.", ""),
    Persona("돈키호테", "돈키호테", "이룰 수 없는 꿈을 꾸리라!", ""),
    Persona("제인 에어", "제인 에어", "나는 나 자신의 주인입니다.", ""),
)
# 밀리 분류명(artifacts/serving/books_kr.json 실측 29종) → PERSONAS 인덱스. 나머지는 sha256(D-16)
CATEGORY_TO_PERSONA: dict[str, int] = {
    "경제경영": 0,
    "자기계발": 0,
    "IT": 0,
    "소설": 1,
    "과학": 1,
    "철학": 1,
    "인문": 2,
    "역사": 2,
    "사회": 2,
    "에세이/시": 3,
    "라이프스타일": 3,
}
DESCRIPTION = "회원님은 {cats}{eul} 즐기고, {criterion}{ro} 책을 고르는 독서가입니다."
CATS_NONE, CRITERION_NONE = "다양한 분야", "취향"
CATS_SHOWN_MAX = 2  # 문장에 넣는 카테고리 수(화면 01 §4-5 "카테고리 1·2")
HANGUL_BASE, HANGUL_LAST, JONG = 0xAC00, 0xD7A3, 28
JONG_RIEUL = 8  # ㄹ 받침 — '으로' 는 '로' 를 쓴다


def _josa(word: str, with_final: str, without_final: str) -> str:
    """받침 판정(revision A1): 한글 음절이 아니면 받침 없음. '으로' 는 ㄹ 받침도 '로'."""
    if not word:
        return without_final
    code = ord(word[-1])
    if not HANGUL_BASE <= code <= HANGUL_LAST:
        return without_final
    final = (code - HANGUL_BASE) % JONG
    if final == 0 or (with_final == "으로" and final == JONG_RIEUL):
        return without_final
    return with_final


def persona_index(categories: Sequence[str]) -> int:
    """지배 카테고리(categories[0]) 로 고른다. 미매핑은 sha256 결정적 선택(D-16)."""
    if not categories:
        return 0
    head = categories[0]
    if head in CATEGORY_TO_PERSONA:
        return CATEGORY_TO_PERSONA[head]
    return int(hashlib.sha256(head.encode()).hexdigest()[:8], 16) % len(PERSONAS)


def assign_persona(categories: Sequence[str], criterion_label: str | None) -> Persona:
    """항상 Persona 를 준다(None 없음). description 에 실제 선택값을 조사와 함께 삽입."""
    base = PERSONAS[persona_index(categories)]
    cats = list(categories)[:CATS_SHOWN_MAX]
    if len(cats) == CATS_SHOWN_MAX:
        shown = f"{cats[0]}{_josa(cats[0], '과', '와')} {cats[1]}"
    else:
        shown = cats[0] if cats else CATS_NONE
    crit = criterion_label or CRITERION_NONE
    return replace(
        base,
        description=DESCRIPTION.format(
            cats=shown,
            eul=_josa(shown, "을", "를"),
            criterion=crit,
            ro=_josa(crit, "으로", "로"),
        ),
    )
