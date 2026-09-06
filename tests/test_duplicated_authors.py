"""의도적 중복 2벌이 갈라지지 않는지 — serving/authors.py 와 ranking/authors.py.

ranking 은 serving 을 import 할 수 없어(star 의존, test_architecture.py) 같은 로직을 복제했다
(개발일지 2026-09-07 파일 항목 D92 · 설계서 데이터 소스 09 §7).
복제의 유일한 위험은 조용한 드리프트다. 2026-09-07 실측으로 카탈로그 9,447권 전량에서
두 구현의 결과가 완전히 같았다 — 그 상태를 못박는다.
"""

from millie_rec.ranking import authors as rank_authors
from millie_rec.serving import authors as serv_authors

# 실측으로 정한 규칙의 경계를 다 지나는 입력들(§7 검증 케이스 + 역할어 공백 경계 24건 대표)
CASES = (
    None,
    "",
    "저자 1",
    "김영하 (지음)",
    "안제이사프콥스키, 함미라 옮김",
    "히가시노 게이고, 양윤옥 옮김",
    "히가시노게이고",
    "루이스 캐럴 글, 존 테니얼 그림, 손영미 옮김",
    "셰익스피어 원작 / 김철 편역",
    "이종인 역",
    "편집부",
    "저작권팀",
    "Disney Books",
    "에이든토저",  # 공백 없이 '저' 로 끝난다 — 잘라내면 실제 이름이 훼손된다
    "로베르토발저",
    "송기역",
    "억만장자 메신저",
    "허준성 외공저",
    "서귤 글그림",
    "박주홍 감역",
    "홍길동 지음 글 그림",  # 역할어 반복 제거
    "A, B · C & D",
    "글",  # 역할어만 있는 조각
    "가",  # 한 글자
)


def test_two_implementations_agree_on_split() -> None:
    for value in CASES:
        assert serv_authors.split_authors(value) == rank_authors.split_authors(value), value


def test_two_implementations_agree_on_key() -> None:
    for value in CASES:
        names = serv_authors.split_authors(value)
        serving_keys = frozenset(serv_authors.key(n) for n in names)
        assert serving_keys == rank_authors.keys_of(value), value


def test_role_word_needs_a_space_before_it() -> None:
    """공백을 요구하지 않으면 카탈로그 실측 24건에서 실제 작가 이름이 잘린다."""
    for whole in ("에이든토저", "로베르토발저", "송기역", "억만장자 메신저"):
        assert serv_authors.split_authors(whole) == (whole,)
    assert serv_authors.split_authors("김영하 지음") == ("김영하",)


def test_translator_segment_is_dropped_not_just_the_role_word() -> None:
    """역할어만 지우면 역자가 작가가 된다 — 조각째 버려야 한다."""
    assert serv_authors.split_authors("안제이사프콥스키, 함미라 옮김") == ("안제이사프콥스키",)
    assert rank_authors.keys_of("안제이사프콥스키, 함미라 옮김") == frozenset({"안제이사프콥스키"})
