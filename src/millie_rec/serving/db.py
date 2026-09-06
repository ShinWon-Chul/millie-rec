"""SQLite: thread-local 연결 · PRAGMA · schema.sql · DML 헬퍼 · close · backup (아키 01 §3-4)."""

import os
import sqlite3
import threading
from collections.abc import Sequence
from pathlib import Path

from millie_rec.contracts import DB_FILENAME, DIR_DATA_LOCAL, ENV_DATA_DIR

SCHEMA_PATH = Path(__file__).parent / "schema.sql"
# journal_mode 만 파일에 남고 나머지 둘은 연결 단위 — 연결마다 3개 전부 실행한다
PRAGMAS = ("PRAGMA journal_mode=WAL", "PRAGMA busy_timeout=5000", "PRAGMA synchronous=NORMAL")
SQL_TABLES = (
    "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
)


def resolve_db_path() -> Path:
    """$DATA_DIR/millie.db 가 있으면 그것, 없으면 contracts.DIR_DATA_LOCAL / millie.db."""
    env = os.environ.get(ENV_DATA_DIR)
    return (Path(env) if env else DIR_DATA_LOCAL) / DB_FILENAME


class Database:
    """threading.local 연결 보유. 핸들러는 스레드풀에서 돌므로 스레드마다 연결 1개."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._local = threading.local()
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def connect(self) -> sqlite3.Connection:
        con = getattr(self._local, "con", None)
        if con is None:
            con = sqlite3.connect(self.path)
            con.row_factory = sqlite3.Row  # query() 가 dict(r) 가능한 행을 준다
            for pragma in PRAGMAS:
                con.execute(pragma)
            self._local.con = con
        return con

    def apply_schema(self) -> None:
        """schema.sql 을 executescript 로 적용(IF NOT EXISTS → 멱등). 행은 쓰지 않는다(D-06)."""
        self.connect().executescript(SCHEMA_PATH.read_text(encoding="utf-8"))

    def table_names(self) -> list[str]:
        return [r[0] for r in self.connect().execute(SQL_TABLES).fetchall()]

    def row_counts(self) -> dict[str, int]:
        """D-07: 스키마의 모든 테이블 COUNT(*), 0 건도 키 포함."""
        con = self.connect()
        # 테이블 이름은 sqlite_master 에서 온 값만 — 사용자 입력이 아니라 f-string 이 안전하다
        return {
            t: con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in self.table_names()
        }

    def ok(self) -> bool:
        try:
            return self.connect().execute("SELECT 1").fetchone()[0] == 1
        except sqlite3.Error:
            return False

    def execute(self, sql: str, params: Sequence[object] = ()) -> int:
        """DML 1문 + 커밋(with con). rowcount 반환 — DELETE 집계·중복 판정용. 항상 ? 바인딩."""
        con = self.connect()
        with con:  # 예외 시 롤백, 정상 시 커밋 — 커밋해야 Nearline 스레드에서 보인다
            return con.execute(sql, tuple(params)).rowcount

    def executemany(self, sql: str, rows: Sequence[Sequence[object]]) -> int:
        """배치 DML + 커밋. rowcount 를 문별로 합산(INSERT OR IGNORE 중복은 0 으로 빠진다)."""
        con = self.connect()
        with con:
            return sum(con.execute(sql, tuple(r)).rowcount for r in rows)

    def query(self, sql: str, params: Sequence[object] = ()) -> list[sqlite3.Row]:
        """SELECT. row_factory=sqlite3.Row 이므로 r["col"]·dict(r) 가능."""
        return self.connect().execute(sql, tuple(params)).fetchall()

    def close(self) -> None:
        """현재 스레드 연결만 닫는다(lifespan shutdown 이 호출). 두 번 불러도 안전."""
        con = getattr(self._local, "con", None)
        if con is not None:
            con.close()
            self._local.con = None

    def backup(self, dest: Path) -> Path:
        """con.backup() 스냅샷 — WAL 중 파일 복사 금지(../.claude/rules/serving.md)."""
        dest.parent.mkdir(parents=True, exist_ok=True)
        out = sqlite3.connect(dest)
        try:
            self.connect().backup(out)
        finally:
            out.close()
        return dest
