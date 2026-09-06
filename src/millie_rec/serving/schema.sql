-- serving/schema.sql — SQLite DDL (아키텍처 01 §3-4 데이터 저장). CREATE TABLE IF NOT EXISTS 만. 인덱스는 파일 끝(Phase 5).
-- 컬럼 이름은 §3-4 표기 그대로(contracts.Event · Rating · BookStats 필드명과 일치). JSON 컬럼은 TEXT.

-- Must 4
CREATE TABLE IF NOT EXISTS users (
    user_key TEXT PRIMARY KEY, created_at TEXT, consent INTEGER, cell TEXT, is_new INTEGER
);
CREATE TABLE IF NOT EXISTS preference_snapshots (
    snapshot_id TEXT PRIMARY KEY, user_key TEXT, created_at TEXT, reading_time TEXT,
    categories TEXT, criterion TEXT, subcategories TEXT, seeds TEXT, persona TEXT,
    reading_times TEXT, criteria TEXT, authors TEXT  -- JSON: categories subcategories seeds persona reading_times criteria authors
);
CREATE TABLE IF NOT EXISTS events (
    event_id TEXT PRIMARY KEY, user_key TEXT, book_id INTEGER, event_type TEXT, ts TEXT,
    surface TEXT, row_id TEXT, position INTEGER, selected INTEGER,
    recommendation_id TEXT, model_version TEXT, preference_snapshot_id TEXT, candidate_set_id TEXT,
    payload TEXT, quality_flag TEXT  -- JSON: payload
);
CREATE TABLE IF NOT EXISTS recommendations (
    recommendation_id TEXT PRIMARY KEY, user_key TEXT, snapshot_id TEXT, model_version TEXT, cell TEXT,
    forced INTEGER, fallback_level INTEGER, latency_total_ms REAL,
    latency_breakdown TEXT, weights TEXT, rows TEXT, ts TEXT  -- JSON: latency_breakdown weights rows
);

-- Should 3
CREATE TABLE IF NOT EXISTS ratings (
    rating_id TEXT PRIMARY KEY, user_key TEXT, book_id INTEGER, stars INTEGER, ts TEXT, recommendation_id TEXT
);
CREATE TABLE IF NOT EXISTS candidate_sets (
    candidate_set_id TEXT PRIMARY KEY, user_key TEXT, ts TEXT, book_ids TEXT, survey_variant TEXT  -- JSON: book_ids
);
CREATE TABLE IF NOT EXISTS book_stats (
    book_id INTEGER PRIMARY KEY, impressions INTEGER, reader_opens INTEGER, qualified_reads INTEGER,
    completions INTEGER, rating_mean REAL, rating_var REAL, difficulty REAL, n_events INTEGER,
    source TEXT, updated_at TEXT
);

-- Phase 5 인덱스(05-CONTEXT 재량). 리플레이·상태 조회·대시보드 집계 경로. 컬럼 변경 없음
CREATE INDEX IF NOT EXISTS idx_events_user_ts ON events(user_key, ts);
CREATE INDEX IF NOT EXISTS idx_recommendations_user_ts ON recommendations(user_key, ts);
