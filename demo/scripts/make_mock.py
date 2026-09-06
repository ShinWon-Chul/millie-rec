#!/usr/bin/env python3
"""밀리 아티팩트(books_kr·item_edges_kr·eval_table) → demo/mock/*.json 변환기. 표준 라이브러리만."""

import argparse
import hashlib
import itertools
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit

# fmt: off  — 상수 표는 조밀하게 유지한다(포매터가 한 줄 한 항목으로 펼치지 않도록)
ROOT = Path(__file__).resolve().parents[2]
SEED = 42  # 결정성 표시값 — 이 생성기에 난수는 없다
# 본인 5권: 싯다르타 · 데미안 · 위버멘쉬 · 쇼펜하우어 인생수업 · 죽음의 수용소에서
SEEDS = (1012, 2765, 1446, 1222, 2292)
# 카드 필드 화이트리스트 — 블랙리스트가 아니라 이 17개만 통과시킨다(밀리 저작 텍스트 차단)
CARD_KEYS = (
    "book_id", "title", "authors", "image_url", "categories", "subcategories", "publisher",
    "book_format", "pop_rank", "millie_label", "average_rating", "review_count",
    "completion_prob", "category_avg_prob", "expected_min", "difficulty", "formats",
)
ROW_SIZE, ANCHOR_NEIGHBORS, K_ITEMS, N_CANDIDATES, SUPPORTED_MIN = 12, 20, 40, 30, 20
N_PERSONAL_RECS = 10  # 쇼케이스 본인 5권 케이스의 이웃 추천 수
FRESH_POOL_N = 30  # fresh_picks 카테고리별 인기 풀
MISSING_RANK = 10**9  # pop_rank 결측을 맨 뒤로
VARIANTS = ("pop", "cf", "hybrid", "hybrid_div")
MODEL_SUFFIX = "_v1"
SURVEY_VARIANT = "v1"
CRITERIA_IDS = ("author", "publisher", "bestseller", "buzz", "review")  # S3 옵션 순서와 1:1
DEMO_CATEGORIES = ("소설", "인문", "자기계발")
DEMO_CRITERION = "bestseller"
COVER_HOST_SUFFIX, ADULT_COVER_MARK = ".millie.co.kr", "adult-cover"
REVIEW_MIN_COUNT, REVIEW_MIN_COUNT_NO_RATING = 3, 10  # 배지 review 3단 폴백
SOURCE_CONTENT, SOURCE_POPULARITY = "content", "popularity"  # 데모 이웃은 콘텐츠 유사도다
TITLE_CONTINUE, TITLE_FRESH, TITLE_TRENDING = "이어 읽기", "새로운 발견", "지금 많이 읽는 책"
TITLE_PERSONA, TITLE_PERSONA_DEFAULT = "{name}의 서가", "회원님의 서가"
SUBTITLE_ANCHOR = "결이 비슷한 책"
REASON_ANCHOR = "『{title}』을 좋아하셨다면"
HANGUL_BASE, HANGUL_LAST, JONG, JONG_RIEUL = 0xAC00, 0xD7A3, 28, 8
# 세부 카테고리 — serving/onboarding_meta.json 이 정본이라 하드코딩 대신 그 파일을 읽는다
# (밀리 3depth 328종 수집 2026-09-06 이후 28 카테고리로 늘어 손으로 맞출 수 없다)
SUBCATEGORIES = json.loads(
    (ROOT / "src/millie_rec/serving/onboarding_meta.json").read_text(encoding="utf-8")
)["subcategories"]
PERSONAS = (
    ("오디세우스", "오디세이아", "지혜로 승리하리라!"),
    ("셜록 홈즈", "주홍색 연구", "사소한 것이 가장 중요하다."),
    ("돈키호테", "돈키호테", "이룰 수 없는 꿈을 꾸리라!"),
    ("제인 에어", "제인 에어", "나는 나 자신의 주인입니다."),
)
CATEGORY_TO_PERSONA = {
    "경제경영": 0, "자기계발": 0, "IT": 0, "소설": 1, "과학": 1, "철학": 1,
    "인문": 2, "역사": 2, "사회": 2, "에세이/시": 3, "라이프스타일": 3,
}
DESCRIPTION = "회원님은 {cats}{eul} 즐기고, {criterion}{ro} 책을 고르는 독서가입니다."
CATS_NONE, CRITERION_NONE, CATS_SHOWN_MAX = "다양한 분야", "취향", 2
# latency 는 표시값이다 — PDF 숫자는 results/latency.json 만(백엔드 01 §0)
LATENCY = {"feature": 4.0, "retrieval": 12.0, "ranking": 9.0, "rerank": 6.0,
           "compose": 7.0, "total": 38.0}
WEIGHTS = {"alpha": 0.7, "beta": 0.2, "gamma": 0.1}  # 표시값(blend.py 공식의 예시 상태)
FIXED_TS = "2026-09-06T00:00:00+00:00"  # 결정성: 계약 파일 안의 시각은 전부 이 상수
DEMO_USER_KEY = "00000000-0000-4000-8000-000000000042"  # 고정 예시 UUID — 개인정보 아님
CONTEXT = "저녁, 하루를 마치며"
NEARLINE_LAG_S = 1.0
PHILOSOPHY = (
    "사용자가 취향 설정에서 직접 알려준 선호를 cold-start(콜드 스타트, 초기 데이터 부족 "
    "상태)의 강한 prior(사전 정보)로 사용하되, 영구적인 취향 label(라벨)로 고정하지 "
    "않는다. 실제 독서 행동과 현재 세션 의도가 축적되면 행동 신호의 비중을 높이고, 취향 "
    "설정을 다시 수행하면 새로운 explicit preference state(명시적 선호 상태)를 생성해 "
    "즉시 반영한다. 이 사용자 상태로 Candidate Retrieval(후보 생성) → Ranking(순위화) → "
    "Re-ranking(재순위화) → Page Composition(페이지 구성)을 수행해 '클릭할 책'이 아니라 "
    "'실제로 읽기 시작할 책'을 메인에 노출한다."
)
METRIC_MAPPING = (
    {"stage": "Candidate Retrieval", "metric": "Recall@20"},
    {"stage": "Ranking", "metric": "NDCG@10"},
    {"stage": "Re-ranking", "metric": "ILD@10"},
)
ROADMAP = (
    "Reviewer-affinity", "Interleaving", "선호 교정 루프", "텍스트 난이도",
    "Two-Tower/ANN", "Kafka/K8s", "피크 autoscaling",
)
DATA_NOTICE = (
    "평가 비교표 = Goodbooks-10k(CC BY-SA 4.0) · 데모 카탈로그 = 밀리의서재 공개 도서 "
    "페이지(수치·메타·표지 URL만, 텍스트 미노출, 요청 시 삭제) · 데모 이웃 = 콘텐츠 "
    "유사도(협업 필터링 아님) · 개인정보 무수집 · 서버 latency는 참고값 · 표지는 밀리 CDN 링크"
)
MDE_NOTE = "데모 표본으로 검정하지 않음 — MDE +1%p 검출에 셀당 n만 명"
KPI_EMPTY_NOTE = "세션 이벤트 집계 전 — 데모 브라우저가 채운다"
KPI_NAMES = (
    ("qualified_reading_start_rate", KPI_EMPTY_NOTE),
    ("first_completion_rate_new", KPI_EMPTY_NOTE),
    ("fallback_rate", KPI_EMPTY_NOTE),
    ("p95_latency_ms", "mock 상수 · 참고용"),
    ("error_rate", KPI_EMPTY_NOTE),
    ("active_user_keys", KPI_EMPTY_NOTE),
)
# 쇼케이스 '기억에 남을 5가지' — 각 주장은 눌러서 확인할 라우트를 가진다
MEMORABLE_5 = (
    {"claim": "취향 설정 = cold-start 입력이자 언제든 갱신되는 explicit preference state",
     "how_to_verify": "취향 재설정 후 인스펙터 snap_01 → snap_02, α +0.15",
     "route": "#/refresh"},
    {"claim": "설문 답변을 전부 같은 feature로 보지 않음 — semantic / item seed / "
              "selection-policy / context / UX layer 분리",
     "how_to_verify": "취향 설정 각 단계의 인스펙터 신호 해석",
     "route": "#/onboarding"},
    {"claim": "클릭이 목표가 아니다 — Qualified Reading Start 중심 KPI + "
              "primary/secondary/guardrail 분리",
     "how_to_verify": "뷰어에서 가상 15분 도달 시 qualified_read, 대시보드 KPI 첫 카드",
     "route": "#/dashboard"},
    {"claim": "Top-K에서 끝나지 않음 — Page Composition까지가 메인 추천 문제",
     "how_to_verify": "메인 5행(이어 읽기·앵커·서가·인기·새로운 발견)과 dedup_removed",
     "route": "#/home"},
    {"claim": "정확도와 production constraint(지연·품질·개인정보·비용)를 같은 수준에서 다룸",
     "how_to_verify": "인스펙터 latency 예산선 200ms · 서재 동의 철회 → level 3",
     "route": "#/library"},
)
FALLBACK_KEYS = {
    "recommendation_id", "model_version", "preference_snapshot_id", "user_key", "cell", "forced",
    "fallback_level", "context", "latency_ms", "latency_breakdown", "user_state_weights",
    "dedup_removed", "nearline_lag_s", "items", "rows",
}
# fmt: on


def _hex(text: str, n: int = 6) -> str:
    """결정적 id 조각. 서버는 난수지만 파일은 같은 입력 → 같은 출력이어야 한다."""
    return hashlib.sha256(text.encode()).hexdigest()[:n]


def _cell() -> str:
    """A/B 셀 — demo_api 와 같은 규칙(user_key sha256 짝수 → A)."""
    return "A" if int(_hex(DEMO_USER_KEY, 8), 16) % 2 == 0 else "B"


def is_eligible(row: dict) -> bool:
    """노출 자격: title 있음 ∧ 표지 호스트 *.millie.co.kr ∧ 성인 표지 플레이스홀더 아님."""
    url = row.get("image_url") or ""
    url = url if isinstance(url, str) else ""
    host = urlsplit(url).hostname or ""
    named = bool(row.get("title"))
    return named and host.endswith(COVER_HOST_SUFFIX) and ADULT_COVER_MARK not in url


def normalize_title(value: object) -> str:
    """dedup 키 — 서버 compose.py 와 같은 정의."""
    return re.sub(r"[^\w]", "", str(value or "")).casefold()


def josa(word: str, with_final: str, without: str) -> str:
    """받침 판정. '으로' 는 ㄹ 받침도 '로'(persona._josa 와 같은 규칙)."""
    if not word:
        return without
    code = ord(word[-1])
    if not HANGUL_BASE <= code <= HANGUL_LAST:
        return without
    final = (code - HANGUL_BASE) % JONG
    if final == 0 or (with_final == "으로" and final == JONG_RIEUL):
        return without
    return with_final


def _rank(card: dict) -> int:
    """pop_rank 결측을 맨 뒤로 — 카탈로그 정렬 키."""
    value = card.get("pop_rank")
    return MISSING_RANK if value is None else int(value)


def load_catalog(artifacts: Path) -> list[dict]:
    """books_kr.json → eligible 카드 배열(pop_rank 순). CARD_KEYS 외 필드는 버린다."""
    rows = json.loads((artifacts / "books_kr.json").read_text(encoding="utf-8"))
    cards = []
    for row in rows:
        if not is_eligible(row):
            continue
        card = {key: row.get(key) for key in CARD_KEYS}
        card["book_id"] = int(row["book_id"])
        card["categories"] = list(card["categories"] or [])
        card["subcategories"] = list(card["subcategories"] or [])
        card["formats"] = list(card["formats"] or [])
        cards.append(card)
    cards.sort(key=lambda c: (_rank(c), c["book_id"]))
    return cards


def load_neighbors(artifacts: Path, ids: set[int]) -> dict[str, list]:
    """item_edges_kr.json → 책별 [dst, weight] 상위 20(source 제외 — 용량)."""
    edges = json.loads((artifacts / "item_edges_kr.json").read_text(encoding="utf-8"))
    out = {}
    for src in sorted(ids):
        picked = [e for e in edges.get(str(src), []) if int(e[0]) in ids]
        picked.sort(key=lambda e: -float(e[1]))
        out[str(src)] = [[int(e[0]), round(float(e[1]), 4)] for e in picked[:ANCHOR_NEIGHBORS]]
    return out


def all_categories(cards: list[dict]) -> tuple[list[str], dict[str, int]]:
    """카테고리 목록(권수 내림차순·동률 이름순)과 권수."""
    counts: dict[str, int] = {}
    for card in cards:
        for cat in card["categories"]:
            counts[cat] = counts.get(cat, 0) + 1
    return sorted(counts, key=lambda c: (-counts[c], c)), counts


def badge_for(
    card: dict, criterion: str | None, seed_authors=frozenset(), seed_publishers=frozenset()
):
    """배지 6종 — serving/badges.py 1:1. light 는 Should → None."""
    rank, avg = card.get("pop_rank"), card.get("average_rating")
    n = card.get("review_count") or 0
    best = {"type": "bestseller", "text": f"인기 {rank}위"} if rank is not None else None
    if criterion == "bestseller":
        return best
    if criterion == "review":
        if avg is not None and n >= REVIEW_MIN_COUNT:
            return {"type": "review", "text": f"★{avg:.1f} · 리뷰 {n}"}
        if n >= REVIEW_MIN_COUNT_NO_RATING:
            return {"type": "review", "text": f"리뷰 {n}"}
        return best
    if criterion == "author" and card.get("authors") in seed_authors:
        return {"type": "author", "text": f"{card['authors']} 작가"}
    if criterion == "publisher" and card.get("publisher") in seed_publishers:
        return {"type": "publisher", "text": f"{card['publisher']} 출판"}
    if criterion == "buzz" and card.get("millie_label"):
        return {"type": "buzz", "text": str(card["millie_label"])}
    return None


def assign_persona(categories, criterion_label: str | None) -> dict:
    """페르소나 4종 — serving/persona.py 1:1. 미매핑은 sha256 결정적."""
    cats = list(categories)[:CATS_SHOWN_MAX]
    head = cats[0] if cats else ""
    index = CATEGORY_TO_PERSONA.get(head)
    if index is None:
        index = int(_hex(head, 8), 16) % len(PERSONAS) if head else 0
    name, work, quote = PERSONAS[index]
    if len(cats) == CATS_SHOWN_MAX:
        shown = f"{cats[0]}{josa(cats[0], '과', '와')} {cats[1]}"
    else:
        shown = cats[0] if cats else CATS_NONE
    crit = criterion_label or CRITERION_NONE
    text = DESCRIPTION.format(
        cats=shown, eul=josa(shown, "을", "를"), criterion=crit, ro=josa(crit, "으로", "로")
    )
    return {"name": name, "work": work, "quote": quote, "description": text}


def item(card: dict, position: int, *, source: str, reason: str | None = None, score=None) -> dict:
    """ItemOut 13필드 정확히. 배지는 행 조립 마지막에 붙인다."""
    return {
        "book_id": card["book_id"],
        "score": float(ROW_SIZE - position) if score is None else float(score),
        "source": source,
        "reason": reason,
        "title": card.get("title"),
        "authors": card.get("authors"),
        "image_url": card.get("image_url"),
        "position": position,
        "source_channels": [source],
        "badge": None,
        "book_format": card.get("book_format"),
        "difficulty": card.get("difficulty"),
        "subcategories": list(card.get("subcategories") or []),
    }


def row_of(row_id: str, title: str, purpose: str, items: list, subtitle: str | None = None) -> dict:
    """RowOut — channel_mix 는 items 의 source_channels 집계."""
    mix: dict[str, int] = {}
    for entry in items:
        for channel in entry["source_channels"]:
            mix[channel] = mix.get(channel, 0) + 1
    return {"row_id": row_id, "title": title, "purpose": purpose, "items": items,
            "subtitle": subtitle, "channel_mix": mix}


def neighbor_row(row_id, title, subtitle, seed, nbrs, by_id, exclude, purpose="discover"):
    """앵커 행 — 이웃 top-20 에서 자격·중복·시드를 뺀 상위 12. 비면 None."""
    picked = [(b, w) for b, w in nbrs if b in by_id and b not in exclude and b != int(seed)]
    items = [
        item(by_id[b], n, source=SOURCE_CONTENT, reason=title, score=w)
        for n, (b, w) in enumerate(picked[:ROW_SIZE])
    ]
    return row_of(row_id, title, purpose, items, subtitle) if items else None


def round_robin(pools: list[list[int]], n: int, used: set[int]) -> list[int]:
    """카테고리 라운드로빈 — onboarding_api._round_robin 과 같은 규칙."""
    out: list[int] = []
    for group in itertools.zip_longest(*pools):
        for book_id in group:
            if book_id is None or book_id in used or len(out) >= n:
                continue
            used.add(book_id)
            out.append(book_id)
        if len(out) >= n:
            break
    return out


def dedup(rows: list[dict]) -> tuple[list[dict], int]:
    """book_id ∧ 정규화 제목, 앞 행 우선. position 재부여 · channel_mix 재계산."""
    seen_ids, seen_titles, removed, out = set(), set(), 0, []
    for row in rows:
        kept = []
        for entry in row["items"]:
            key = normalize_title(entry["title"])
            if entry["book_id"] in seen_ids or (key and key in seen_titles):
                removed += 1
                continue
            seen_ids.add(entry["book_id"])
            if key:
                seen_titles.add(key)
            kept.append({**entry, "position": len(kept)})
        out.append(row_of(row["row_id"], row["title"], row["purpose"], kept, row["subtitle"]))
    return out, removed


def _shelf(variant, cards, by_id, nbrs, seeds, categories, exclude) -> list[dict]:
    """persona_shelf 아이템 — variant 별 표시 규칙(스코어링 아님)."""
    seed_ids = {int(s) for s in seeds}
    chosen = set(categories)
    if variant == "pop":
        ids = [c["book_id"] for c in cards
               if set(c["categories"]) & chosen and c["book_id"] not in exclude | seed_ids]
        return [item(by_id[b], n, source=SOURCE_POPULARITY) for n, b in enumerate(ids[:ROW_SIZE])]
    weighted: dict[int, float] = {}
    for seed in seeds:
        for dst, weight in nbrs.get(str(int(seed)), []):
            if dst in by_id and dst not in exclude and dst not in seed_ids:
                weighted[dst] = max(weighted.get(dst, 0.0), float(weight))
    ranked = sorted(weighted, key=lambda b: (-weighted[b], b))
    if variant == "hybrid_div":
        pools = [[b for b in ranked if cat in by_id[b]["categories"]] for cat in categories]
        pools.append([b for b in ranked if not set(by_id[b]["categories"]) & chosen])
        ranked = round_robin(pools, len(ranked), set())
    items = [item(by_id[b], n, source=SOURCE_CONTENT, score=weighted[b])
             for n, b in enumerate(ranked[:ROW_SIZE])]
    if len(items) < ROW_SIZE:
        used = exclude | seed_ids | {i["book_id"] for i in items}
        extra = [c["book_id"] for c in cards if c["book_id"] not in used][:ROW_SIZE - len(items)]
        items += [item(by_id[b], len(items) + n, source=SOURCE_POPULARITY)
                  for n, b in enumerate(extra)]
    return items


def compose(variant, cards, by_id, nbrs, seeds, categories, criterion, persona_name) -> dict:
    """Must 5행 + 배지 + dedup → RecommendOut."""
    seed_ids = [int(s) for s in seeds if int(s) in by_id]
    exclude = set(seed_ids)
    rows = [row_of("continue_reading", TITLE_CONTINUE, "resume", [])]
    if seed_ids:
        seed1 = seed_ids[0]
        head = REASON_ANCHOR.format(title=by_id[seed1]["title"])
        anchor = neighbor_row(f"anchor_{seed1}", head, SUBTITLE_ANCHOR, seed1,
                              nbrs.get(str(seed1), []), by_id, exclude)
        if anchor is not None:
            rows.append(anchor)
            exclude |= {i["book_id"] for i in anchor["items"]}
    shelf = _shelf(variant, cards, by_id, nbrs, seeds, categories, exclude)
    name = TITLE_PERSONA.format(name=persona_name) if persona_name else TITLE_PERSONA_DEFAULT
    rows.append(row_of("persona_shelf", name, "discover", shelf))
    exclude |= {i["book_id"] for i in shelf}
    trend = [c["book_id"] for c in cards if c["book_id"] not in exclude][:ROW_SIZE]
    rows.append(row_of("trending", TITLE_TRENDING, "fallback",
                       [item(by_id[b], n, source=SOURCE_POPULARITY) for n, b in enumerate(trend)]))
    exclude |= set(trend)
    order, _ = all_categories(cards)
    others = [c for c in order if c not in set(categories)] or list(order)
    pools = [[c["book_id"] for c in cards
              if cat in c["categories"] and c["book_id"] not in exclude][:FRESH_POOL_N]
             for cat in others]
    fresh = round_robin(pools, ROW_SIZE, set(exclude))
    rows.append(row_of("fresh_picks", TITLE_FRESH, "explore",
                       [item(by_id[b], n, source=SOURCE_POPULARITY) for n, b in enumerate(fresh)]))
    authors = frozenset(by_id[s]["authors"] for s in seed_ids if by_id[s].get("authors"))
    publishers = frozenset(by_id[s]["publisher"] for s in seed_ids if by_id[s].get("publisher"))
    for row in rows:
        for entry in row["items"]:
            entry["badge"] = badge_for(by_id[entry["book_id"]], criterion, authors, publishers)
    rows, removed = dedup(rows)
    return {
        "recommendation_id": "rec_" + _hex(variant),
        "model_version": variant + MODEL_SUFFIX,
        "preference_snapshot_id": "snap_" + _hex("demo"),
        "user_key": DEMO_USER_KEY,
        "cell": _cell(),
        "forced": True,
        "fallback_level": 0,
        "context": CONTEXT,
        "latency_ms": LATENCY["total"],
        "latency_breakdown": dict(LATENCY),
        "user_state_weights": dict(WEIGHTS),
        "dedup_removed": removed,
        "nearline_lag_s": NEARLINE_LAG_S,
        "items": [i for row in rows for i in row["items"]][:K_ITEMS],
        "rows": rows,
    }


def meta_onboarding(cards: list[dict], config: Path) -> dict:
    """화면 텍스트 정본은 demo/config/onboarding.json — S1 옵션 = 시간대, S3 옵션 = 기준 라벨."""
    steps = {s["id"]: s for s in json.loads(config.read_text(encoding="utf-8"))["steps"]}
    order, counts = all_categories(cards)
    return {
        "survey_variant": SURVEY_VARIANT,
        "reading_times": list(steps["S1"]["options"]),
        "criteria": [{"id": i, "label": label}
                     for i, label in zip(CRITERIA_IDS, steps["S3"]["options"], strict=True)],
        "categories": [{"name": c, "supported": counts[c] >= SUPPORTED_MIN,
                        "subcategories": list(SUBCATEGORIES.get(c, []))} for c in order],
    }


def candidates(cards: list[dict], by_id: dict, categories=DEMO_CATEGORIES, n=N_CANDIDATES) -> dict:
    """취향 설정 S5 후보 — 카테고리 라운드로빈(pop_rank 순)."""
    pools = [[c["book_id"] for c in cards if cat in c["categories"]] for cat in categories]
    ids = round_robin(pools, n, set())
    return {
        "candidate_set_id": "cand_" + _hex("demo"),
        "survey_variant": SURVEY_VARIANT,
        "created_at": FIXED_TS,
        "items": [{"book_id": b, "title": by_id[b]["title"], "authors": by_id[b]["authors"],
                   "image_url": by_id[b]["image_url"], "position": pos,
                   "book_format": by_id[b]["book_format"]} for pos, b in enumerate(ids)],
    }


def preferences_response(persona: dict) -> dict:
    return {"user_key": DEMO_USER_KEY, "preference_snapshot_id": "snap_" + _hex("demo"),
            "created_at": FIXED_TS, "cell": _cell(), "snapshots_count": 1, "persona": persona}


def user_state(by_id: dict, seeds, categories, criterion: str) -> dict:
    """UserStateOut — 시드 5권이 서재 added 버킷에 담긴 상태."""
    library = [{"book_id": int(s), "title": by_id[int(s)]["title"],
                "authors": by_id[int(s)]["authors"],
                "image_url": by_id[int(s)]["image_url"]} for s in seeds if int(s) in by_id]
    return {
        "user_key": DEMO_USER_KEY, "consent": True, "cell": _cell(), "is_new": False,
        "library": {"added": library, "reading": [], "completed": []},
        "snapshots": [{"snapshot_id": "snap_" + _hex("demo"), "created_at": FIXED_TS,
                       "categories": list(categories), "criterion": criterion, "active": True}],
        "user_state_weights": dict(WEIGHTS), "nearline_lag_s": NEARLINE_LAG_S,
    }


def dashboard_empty() -> dict:
    """DashboardOut 빈 집계 — 값은 브라우저가 세션 이벤트로 채운다(고정 예시 숫자 금지)."""
    return {
        "generated_at": FIXED_TS, "window": "all",
        "kpi": {name: {"value": 0.0, "n": 0, "note": note} for name, note in KPI_NAMES},
        "ab_table": [], "mde_note": MDE_NOTE,
        "latency": {"p50": 0.0, "p95": 0.0, "p99": 0.0, "by_stage": {}},
        "quality": {"impression_receipt_rate": 0.0, "flagged_events": 0.0,
                    "feature_freshness_s": 0.0},
        "events_recent": [], "impressions_log": [], "by_variant": {}, "by_hour": [],
    }


def _p95_by_variant(latency: Path | None) -> dict[str, float]:
    """results/latency.json 은 전역 p95 1개 + 벤치된 variant 목록이다."""
    if latency is None or not Path(latency).exists():
        return {}
    data = json.loads(Path(latency).read_text(encoding="utf-8"))
    p95 = data.get("p95")
    if p95 is None:
        return {}
    benched = data.get("variants", {})
    return {v: round(float(p95), 1) for v in VARIANTS if f"{v}{MODEL_SUFFIX}" in benched}


def personal_case(by_id: dict, nbrs: dict, seeds) -> dict | None:
    """본인 5권 + 콘텐츠 유사도 이웃 10권. 5권 중 하나라도 없으면 None(화면 '5권 선정 대기')."""
    picked = [int(s) for s in seeds]
    if not picked or any(s not in by_id for s in picked):
        return None
    books = [{"book_id": s, "title": by_id[s]["title"], "authors": by_id[s]["authors"],
              "image_url": by_id[s]["image_url"], "reason": None, "badge": None} for s in picked]
    pools = [[d for d, _ in nbrs.get(str(s), [])] for s in picked]
    seen_ids = set(picked)
    seen_titles = {normalize_title(by_id[s]["title"]) for s in picked}
    recs: list[dict] = []
    for group in itertools.zip_longest(*pools):
        for index, dst in enumerate(group):
            if dst is None or dst in seen_ids or dst not in by_id or len(recs) >= N_PERSONAL_RECS:
                continue
            key = normalize_title(by_id[dst]["title"])
            if key and key in seen_titles:
                continue
            seen_ids.add(dst)
            seen_titles.add(key)
            recs.append({
                "book_id": dst, "title": by_id[dst]["title"],
                "authors": by_id[dst]["authors"], "image_url": by_id[dst]["image_url"],
                "reason": REASON_ANCHOR.format(title=by_id[picked[index]]["title"]),
                "badge": badge_for(by_id[dst], DEMO_CRITERION),
            })
        if len(recs) >= N_PERSONAL_RECS:
            break
    return {"seeds": books, "recommendations": recs}


def showcase(eval_table: Path, latency: Path | None, by_id: dict, nbrs: dict, seeds) -> dict:
    """ShowcaseOut — 숫자 원천은 eval_table.json 1곳(문자열 → float 변환만 한다)."""
    table = json.loads(Path(eval_table).read_text(encoding="utf-8"))
    p95 = _p95_by_variant(latency)
    rows = [{"variant": r["variant"], "recall_at_20": float(r["recall@20"]),
             "ndcg_at_10": float(r["ndcg@10"]), "ild_at_10": float(r["ild@10"]),
             "p95_ms": p95.get(r["variant"])} for r in table["rows"]]
    return {
        "philosophy": PHILOSOPHY,
        "eval_table": {"split_mode": table["meta"]["split_mode"],
                       "source": {"metrics": "results/latest.csv", "p95": "results/latency.json"},
                       "rows": rows},
        "metric_mapping": [dict(m) for m in METRIC_MAPPING],
        "personal_case": personal_case(by_id, nbrs, seeds),
        "memorable_5": [dict(m) for m in MEMORABLE_5],
        "roadmap": list(ROADMAP),
        "data_notice": DATA_NOTICE,
    }


def validate_fallback(path: Path | None) -> None:
    """소유권은 scripts/export_millie_fallback.py — 읽고 확인만 하고 절대 쓰지 않는다."""
    if path is None or not Path(path).exists():
        print("[make_mock] warn: fallback/popular.json 없음 — make millie-export 가 만든다")
        return
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    ok = (set(data) == FALLBACK_KEYS and data.get("model_version") == "fallback_v1"
          and isinstance(data.get("latency_ms"), float))
    n = len(data.get("rows", []))
    print(f"[make_mock] fallback/popular.json {'ok' if ok else 'MISMATCH'} ({n} rows)")


def _write(out: Path, name: str, payload, *, compact: bool = False) -> int:
    text = (json.dumps(payload, ensure_ascii=False, separators=(",", ":")) if compact
            else json.dumps(payload, ensure_ascii=False, indent=1))
    path = out / name
    path.write_text(text, encoding="utf-8")
    return path.stat().st_size


def _md5(path: Path) -> str | None:
    return hashlib.md5(Path(path).read_bytes()).hexdigest() if Path(path).exists() else None


def build(
    artifacts, out, config, *, eval_table=None, latency=None, fallback=None, seeds=SEEDS
) -> dict[str, int]:
    """밀리 아티팩트 → mock 13파일. 시각·난수 없음(_manifest.json 만 예외)."""
    artifacts, out, config = Path(artifacts), Path(out), Path(config)
    eval_path = Path(eval_table) if eval_table else artifacts / "eval_table.json"
    out.mkdir(parents=True, exist_ok=True)
    for stale in out.glob("*.json"):
        stale.unlink()
    cards = load_catalog(artifacts)
    by_id = {c["book_id"]: c for c in cards}
    nbrs = load_neighbors(artifacts, set(by_id))
    meta = meta_onboarding(cards, config)
    label = next(c["label"] for c in meta["criteria"] if c["id"] == DEMO_CRITERION)
    persona = assign_persona(DEMO_CATEGORIES, label)
    sizes = {
        "catalog_kr.json": _write(out, "catalog_kr.json", cards, compact=True),
        "neighbors_kr.json": _write(out, "neighbors_kr.json", nbrs, compact=True),
        "meta_onboarding.json": _write(out, "meta_onboarding.json", meta),
        "candidates_onboarding.json": _write(
            out, "candidates_onboarding.json", candidates(cards, by_id)),
        "preferences_response.json": _write(
            out, "preferences_response.json", preferences_response(persona)),
        "state.json": _write(
            out, "state.json", user_state(by_id, seeds, DEMO_CATEGORIES, DEMO_CRITERION)),
        "dashboard.json": _write(out, "dashboard.json", dashboard_empty()),
    }
    for variant in VARIANTS:
        payload = compose(variant, cards, by_id, nbrs, seeds, DEMO_CATEGORIES,
                          DEMO_CRITERION, persona["name"])
        sizes[f"recommend_{variant}.json"] = _write(out, f"recommend_{variant}.json", payload)
    if eval_path.exists():
        sizes["showcase.json"] = _write(
            out, "showcase.json", showcase(eval_path, latency, by_id, nbrs, seeds))
    else:
        print(f"[make_mock] warn: {eval_path.name} 없음 — showcase.json 건너뜀")
    manifest = {
        "generated_at": datetime.now(UTC).isoformat(), "seed": SEED,
        "generator": "demo/scripts/make_mock.py",
        "inputs": {"books_kr.json": _md5(artifacts / "books_kr.json"),
                   "item_edges_kr.json": _md5(artifacts / "item_edges_kr.json"),
                   "eval_table.json": _md5(eval_path), "onboarding.json": _md5(config)},
        "outputs": dict(sizes),
    }
    sizes["_manifest.json"] = _write(out, "_manifest.json", manifest)
    default_fb = out.parent / "fallback" / "popular.json"
    validate_fallback(fallback if fallback is not None else default_fb)
    return sizes


def main() -> None:
    ap = argparse.ArgumentParser(description="밀리 아티팩트 → demo/mock/*.json 생성")
    ap.add_argument("--artifacts", type=Path, default=ROOT / "artifacts" / "serving")
    ap.add_argument("--out", type=Path, default=ROOT / "demo" / "mock")
    ap.add_argument("--config", type=Path, default=ROOT / "demo" / "config" / "onboarding.json")
    ap.add_argument("--latency", type=Path, default=ROOT / "results" / "latency.json")
    args = ap.parse_args()
    sizes = build(args.artifacts, args.out, args.config, latency=args.latency)
    total = sum(sizes.values()) / 1024
    print(f"[make_mock] wrote {len(sizes)} files → {args.out} ({total:.0f} KB)")


if __name__ == "__main__":
    main()
