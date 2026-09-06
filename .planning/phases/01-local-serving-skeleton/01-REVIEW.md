---
phase: 01-local-serving-skeleton
reviewed: 2026-09-05T02:26:13Z
depth: standard
files_reviewed: 8
files_reviewed_list:
  - src/millie_rec/contracts.py
  - src/millie_rec/serving/__init__.py
  - src/millie_rec/serving/api.py
  - src/millie_rec/serving/db.py
  - src/millie_rec/serving/fallback.py
  - src/millie_rec/serving/schema.sql
  - src/millie_rec/app/server.py
  - tests/serving/test_smoke.py
findings:
  critical: 0
  warning: 1
  info: 6
  total: 7
status: issues_found
---

# Phase 1 '로컬 서빙 스켈레톤': Code Review Report

**Reviewed:** 2026-09-05T02:26:13Z
**Depth:** standard
**Files Reviewed:** 8
**Status:** issues_found

## Summary

Reviewed the Phase 1 '로컬 서빙 스켈레톤'(.planning/ROADMAP.md) serving lane: `create_app`/`/health`/`/api/recommend` (`api.py`), thread-local sqlite3 wrapper (`db.py`), level-3 fallback (`fallback.py`), DDL (`schema.sql`), the uvicorn entry point (`app/server.py`), the serving public surface (`__init__.py`), the single changed line in `contracts.py` (`MODEL_VERSION_FALLBACK`), and the smoke tests.

Overall assessment: the skeleton is small, clean, and consistent with the project rules that apply to this path (`.claude/rules/serving.md`, `architecture.md`, `simplicity.md`, `local-run.md`):

- Star dependency holds — `serving/*` imports only `millie_rec.contracts` and its own slice; `app/server.py` imports only the `millie_rec.serving` public surface. `uv run pytest --no-header` → 104 passed, 2 skipped; `uv run ruff check` / `ruff format --check` clean on the reviewed paths.
- All `src/` files are under the 150-line limit (`api.py` 128, `db.py` 60, `fallback.py` 45, `server.py` 12).
- Both HTTP handlers are sync `def` (threadpool) per the event-loop rule; `db` is keyword-only required; StaticFiles is mounted last; 422 shape matches FastAPI's validation-error contract; `k` is bounded 1..100; `model` is validated against `VARIANTS`.
- Fallback isolation is verified by test (`_Boom` pipeline → 200, level 3, empty trending row), and `Database.ok()` correctly returns `False` on a corrupt DB file (verified empirically: the WAL PRAGMA in `connect()` raises `sqlite3.DatabaseError`, which `ok()` catches).

No Critical issues. One Warning: `/health` can still return 500 if `row_counts()` raises after `ok()` succeeded, which contradicts the `db_ok: bool` degraded-state design and, on Railway, would make the healthcheck restart a container whose `/api/recommend` is still serving. The remaining items are Info-level hardening/drift guards that are cheapest to do now, before the Day 3 API freeze.

Design decisions listed by the orchestrator (unused injection params, no SQLite writes in Phase 1, intentional `except Exception` in `_fallback_response`, f-string table names sourced from `sqlite_master`, no CORS) were treated as given and are not reported as findings.

## Warnings

### WR-01: `/health` returns 500 instead of `db_ok=false` when `row_counts()` fails after `ok()` passed

**File:** `src/millie_rec/serving/api.py:100-108` (and `src/millie_rec/serving/db.py:45-54`)
**Issue:** `health()` guards `row_counts()` only with the preceding `db.ok()` result. `ok()` catches `sqlite3.Error`, but `table_names()` / `row_counts()` do not, and they run on the same already-open connection. Any `sqlite3.Error` raised between the two calls (I/O error on the Railway volume, `database is locked` after the 5 s `busy_timeout`, a table dropped/renamed by a future migration racing a request) propagates out of the handler as an unhandled exception → HTTP 500. `HealthOut.db_ok: bool` exists precisely so the endpoint can report a degraded DB with a 200; a 500 on `/health` would fail the Railway healthcheck (`railway.json` per `.claude/rules/serving.md`) and restart a container whose `/api/recommend` — which does not touch the DB in Phase 1 — is still healthy. This is the same "추천 API 장애 ≠ 메인 장애" principle already applied in `_fallback_response`, just not applied to the DB probe. Probability is low (the corrupt-file case is already handled by `ok()`), but the fix is three lines and this endpoint is the deployment gate.
**Fix:**
```python
# api.py — health()
def health() -> HealthOut:
    try:
        ok = db.ok()
        counts = db.row_counts() if ok else {}
    except sqlite3.Error:  # import sqlite3 at top; or catch Exception and log
        log.exception("health: db probe failed")
        ok, counts = False, {}
    return HealthOut(status="ok", db_ok=ok, db_row_count=counts, uptime_s=perf_counter() - started["t"])
```
Alternatively keep `api.py` free of `sqlite3` by making `Database.row_counts()` itself return `{}` on `sqlite3.Error` (mirroring `ok()`), and have `health()` derive `db_ok` from `ok()` only.

## Info

### IN-01: Thread-local connections are never closed; lifespan has no shutdown step

**File:** `src/millie_rec/serving/db.py:24-39`, `src/millie_rec/serving/api.py:92-96`
**Issue:** `Database` exposes no `close()`, and the lifespan does nothing after `yield`. Each threadpool thread that serves `/health` opens a connection that lives until interpreter exit, and the `-wal`/`-shm` sidecar files remain on disk after shutdown. Bounded by the threadpool size, so not a leak in practice — but Phase 5 (`nearline.py`, `con.backup()`) will want an orderly close, and tests on non-POSIX platforms would fail to delete `tmp_path` while connections are open.
**Fix:** Add `def close(self) -> None: con = getattr(self._local, "con", None); if con: con.close(); self._local.con = None` and call `db.close()` after `yield` in `lifespan`. (Closing other threads' connections is not possible with `threading.local`; closing the lifespan thread's connection is the achievable minimum.)

### IN-02: Table identifiers in `row_counts()` are unquoted

**File:** `src/millie_rec/serving/db.py:53`
**Issue:** Not a security finding (names come from `sqlite_master`, as the comment states). Robustness only: `SELECT COUNT(*) FROM {t}` breaks if a future `schema.sql` adds a table whose name needs quoting (reserved word, hyphen, FTS shadow tables like `x_content`). Quoting costs nothing and removes the constraint on future DDL.
**Fix:** `f'SELECT COUNT(*) FROM "{t.replace(chr(34), chr(34) * 2)}"'` — or simply `f'SELECT COUNT(*) FROM "{t}"'` given the names are DDL-controlled.

### IN-03: `TRENDING_ROW_ID` / `TRENDING_PURPOSE` membership in contracts is asserted only by comment

**File:** `src/millie_rec/serving/fallback.py:7-10`
**Issue:** The comments say "contracts.ROW_IDS 안" / "contracts.ROW_PURPOSES 안", but nothing enforces it at import time. Drift (e.g. a contracts rename) would surface only as a 500 when `RowOut.row_id` (`RowId` AfterValidator in `schemas.py:46`) rejects the response at request time.
**Fix:** Import `ROW_IDS, ROW_PURPOSES` from `millie_rec.contracts` and add a module-level guard:
```python
assert TRENDING_ROW_ID in ROW_IDS and TRENDING_PURPOSE in ROW_PURPOSES  # drift guard, import-time
```

### IN-04: `MODEL_VERSION_FALLBACK` duplicates the `_v1` suffix literal

**File:** `src/millie_rec/contracts.py:63`
**Issue:** The one changed line hardcodes `"fallback_v1"` directly under `MODEL_VERSION_SUFFIX = "_v1"`. If the suffix is ever bumped, the fallback version string silently stays at `_v1`. The name choice itself (not borrowing a `VARIANTS` name, per the 숫자 불혼합 rule) is correct.
**Fix:** `MODEL_VERSION_FALLBACK = "fallback" + MODEL_VERSION_SUFFIX  # level 3 응답 …`

### IN-05: `context` query parameter is unbounded and echoed back

**File:** `src/millie_rec/serving/api.py:116`
**Issue:** `context: str | None` is accepted with no length constraint and returned verbatim in `RecommendOut.context`. Harmless in Phase 1 (JSON response, nothing persisted), but Phase 5 writes recommendations to SQLite, so an unbounded free-text field will land in the `recommendations` table. Adding a bound now does not change the wire shape and avoids touching the contract after the Day 3 freeze.
**Fix:** `context: Annotated[str | None, Query(max_length=64)] = None` (pick the bound matching the `context` vocabulary in 백엔드 서빙 01 §5).

### IN-06: Server-module test leaves a stale `millie_rec.app.server` bound to a deleted `tmp_path`

**File:** `tests/serving/test_smoke.py:157-158`
**Issue:** The test pops and re-imports `millie_rec.app.server` under a monkeypatched `DATA_DIR`, but does not remove it afterwards. The module (and its `Database(tmp_path/millie.db)`) remains in `sys.modules` for the rest of the session pointing at a directory pytest will delete. No current test imports it afterwards, so this is latent; a future test that does `import millie_rec.app.server` would inherit the stale app instead of a fresh one.
**Fix:** Use `monkeypatch.delitem(sys.modules, "millie_rec.app.server", raising=False)` before the import — monkeypatch undoes it at teardown — or pop again in a `finally:`.

---

_Reviewed: 2026-09-05T02:26:13Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
