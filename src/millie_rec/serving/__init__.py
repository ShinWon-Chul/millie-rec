"""serving 슬라이스 공개 표면. 다른 슬라이스는 여기 있는 이름만 import 할 수 있다."""

from millie_rec.serving.api import create_app
from millie_rec.serving.book_stats import ServingBookStats
from millie_rec.serving.db import Database, resolve_db_path
from millie_rec.serving.fallback import GlobalPopularFallback
from millie_rec.serving.nearline import NearlineLoop
from millie_rec.serving.schemas import API_VERSION, EventIn, RecommendOut
from millie_rec.serving.state import StateStore

__all__ = [
    "API_VERSION",
    "Database",
    "EventIn",
    "GlobalPopularFallback",
    "NearlineLoop",
    "RecommendOut",
    "ServingBookStats",
    "StateStore",
    "create_app",
    "resolve_db_path",
]
