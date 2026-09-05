"""HTTP 계약 스키마 — 계약 준수(백엔드 01 §5·§6) + 열거값이 contracts 상수로만 검증되는지."""

import pytest
from pydantic import ValidationError

from millie_rec.contracts import (
    BADGE_TYPES,
    FALLBACK_PERSONALIZED,
    MODEL_VERSION_SUFFIX,
    VARIANTS,
    Badge,
    Recommendation,
    RecommendResponse,
    Row,
    ScoredItem,
)
from millie_rec.serving.schemas import EventIn, RecommendOut


def _response() -> RecommendResponse:
    item = ScoredItem(
        book_id=1,
        score=0.83,
        source="content",
        reason="『나무』를 좋아하셨다면",
        title="t",
        position=0,
        source_channels=("content",),
        badge=Badge(type="bestseller", text="인기 12위"),
        book_format="전자책",
        difficulty=0.42,
    )
    row = Row(
        row_id="anchor_2767",
        title="『나무』를 좋아하셨다면",
        purpose="discover",
        items=(item,),
        subtitle="결이 비슷한 책",
        channel_mix={"content": 1},
    )
    return RecommendResponse(
        items=(Recommendation(book_id=1, score=0.83, title="t"),),
        model_version=f"{VARIANTS[3]}{MODEL_VERSION_SUFFIX}",
        fallback_level=FALLBACK_PERSONALIZED,
        latency_ms=36.3,
        recommendation_id="rec_8f3a2c",
        rows=(row,),
        latency_breakdown={"total": 36.3},
        user_state_weights={"alpha": 1.0},
        user_key="u",
        cell="B",
    )


def test_recommend_roundtrip_matches_contract_fields():
    out = RecommendOut.from_contract(_response(), forced=True)
    d = out.model_dump()
    assert d["latency_ms"] == 36.3 and isinstance(d["latency_ms"], float)
    assert d["rows"][0]["row_id"] == "anchor_2767" and d["rows"][0]["items"][0][
        "source_channels"
    ] == ["content"]
    assert d["rows"][0]["items"][0]["badge"]["type"] in BADGE_TYPES
    assert d["forced"] is True and d["fallback_level"] == 0


def test_enums_come_from_contracts():
    base = dict(event_id="e1", user_key="u", ts="2026-09-07T12:00:00Z")
    EventIn(**base, event_type="completion", row_id="anchor_1")
    with pytest.raises(ValidationError):
        EventIn(**base, event_type="itemknn_click")
    with pytest.raises(ValidationError):
        EventIn(**base, event_type="completion", row_id="not_a_row")
    with pytest.raises(ValidationError):
        RecommendOut.model_validate({"model_version": "x", "fallback_level": 4, "latency_ms": 1.0})
