"""serving 슬라이스 공개 표면. 다른 슬라이스는 여기 있는 이름만 import 할 수 있다."""

from millie_rec.serving.schemas import API_VERSION, EventIn, RecommendOut

__all__ = ["API_VERSION", "EventIn", "RecommendOut"]
