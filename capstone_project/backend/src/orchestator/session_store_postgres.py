"""
session_store.py
----------------

PostgreSQL-backed session management (migrated from SQLite).

Why PostgreSQL over SQLite for Azure Container Apps:
  - Survives container restarts / redeployments (external, managed service)
  - Supports multiple replicas sharing the same session state
  - Azure Database for PostgreSQL Flexible Server is persistent across
    the day unlike some dev-tier Cosmos DB free accounts

Tables:
  sessions    - one row per chat session
  history     - chat turns, scoped by session_id
  documents   - uploaded files, scoped by session_id

Connection pooling:
  Uses psycopg2.pool.ThreadedConnectionPool so that concurrent FastAPI /
  Flask workers share a small pool of persistent connections instead of
  opening a new socket on every request.

Environment variables required:
    DATABASE_URL   - postgres://user:pass@host:5432/dbname
                     (supports ?sslmode=require for Azure)

    Or individual variables (used only when DATABASE_URL is absent):
    POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB,
    POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_SSLMODE
"""

from __future__ import annotations

import os
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone, timedelta
from typing import Generator, Optional
from dotenv import load_dotenv

import psycopg2
import psycopg2.extras
from psycopg2.pool import ThreadedConnectionPool

# ── Connection config ─────────────────────────────────────────────────────────

MAX_HISTORY_ITEMS = 20
_POOL_MIN_CONN    = 1
_POOL_MAX_CONN    = 10
load_dotenv()


def _build_dsn() -> str:
    url = os.environ.get("DATABASE_URL")
    if url:
        # Heroku / Azure-style DATABASE_URL may use 'postgres://' scheme;
        # psycopg2 requires 'postgresql://'
        return url.replace("postgres://", "postgresql://", 1)

    return (
        "host={host} port={port} dbname={db} "
        "user={user} password={password}"
    ).format(
        host     = os.environ["POSTGRES_HOST"],
        port     = os.environ.get("POSTGRES_PORT", "5432"),
        db       = os.environ["POSTGRES_DB"],
        user     = os.environ["POSTGRES_USER"],
        password = os.environ["POSTGRES_PASSWORD"],
        # ssl      = os.environ.get("POSTGRES_SSLMODE", "require"),
    )


_pool: ThreadedConnectionPool = ThreadedConnectionPool(
    minconn=_POOL_MIN_CONN,
    maxconn=_POOL_MAX_CONN,
    dsn=_build_dsn(),
)


@contextmanager
def _get_conn() -> Generator:
    """
    Borrow a connection from the pool, yield a DictCursor, and
    return the connection to the pool when the block exits.
    Rolls back automatically on exception.
    """
    conn = _pool.getconn()
    try:
        with conn:                              # auto commit / rollback
            with conn.cursor(
                cursor_factory=psycopg2.extras.RealDictCursor
            ) as cur:
                yield cur
    finally:
        _pool.putconn(conn)


# ── Schema bootstrap ──────────────────────────────────────────────────────────

def init_db() -> None:
    """
    Idempotent schema creation.
    Call once at application startup.
    """
    with _get_conn() as cur:

        cur.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id   TEXT PRIMARY KEY,
                created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
                last_active  TIMESTAMPTZ NOT NULL DEFAULT now(),
                turn_count   INTEGER     NOT NULL DEFAULT 0
            );
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS history (
                id          BIGSERIAL   PRIMARY KEY,
                session_id  TEXT        NOT NULL
                                REFERENCES sessions(session_id)
                                ON DELETE CASCADE,
                role        TEXT        NOT NULL,
                text        TEXT        NOT NULL,
                created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
            )
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_history_session
                ON history(session_id, id)
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                file_id       TEXT        PRIMARY KEY,
                session_id    TEXT        NOT NULL
                                  REFERENCES sessions(session_id)
                                  ON DELETE CASCADE,
                original_name TEXT        NOT NULL,
                size_bytes    BIGINT      NOT NULL,
                status        TEXT        NOT NULL DEFAULT 'indexed',
                uploaded_at   TIMESTAMPTZ NOT NULL DEFAULT now()
            )
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_documents_session
                ON documents(session_id)
        """)


init_db()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _now() -> datetime:
    return datetime.now(timezone.utc)


# ── SessionStore ──────────────────────────────────────────────────────────────

class SessionStore:

    # ── Session creation / lookup ─────────────────────────────────────────────

    def make_session(
        self,
        session_id: Optional[str] = None,
        reset: bool = False,
    ) -> str:
        """
        Return an active session_id.

        - session_id=None or reset=True  → always create a new session.
        - session_id given + exists      → return it unchanged.
        - session_id given + not found   → create a new one.
        """
        if not reset and session_id:
            if self.session_exists(session_id):
                return session_id

        new_id = str(uuid.uuid4())
        with _get_conn() as cur:
            cur.execute(
                """
                INSERT INTO sessions (session_id, created_at, last_active, turn_count)
                VALUES (%s, now(), now(), 0)
                """,
                (new_id,),
            )
        return new_id

    def session_exists(self, session_id: str) -> bool:
        with _get_conn() as cur:
            cur.execute(
                "SELECT 1 FROM sessions WHERE session_id = %s",
                (session_id,),
            )
            return cur.fetchone() is not None

    # ── History read / write ──────────────────────────────────────────────────

    def append_history(self, session_id: str, role: str, text: str) -> None:
        with _get_conn() as cur:

            # Insert new turn
            cur.execute(
                """
                INSERT INTO history (session_id, role, text, created_at)
                VALUES (%s, %s, %s, now())
                """,
                (session_id, role, text),
            )

            # Trim to MAX_HISTORY_ITEMS — keep the N most-recent rows
            cur.execute(
                """
                DELETE FROM history
                WHERE session_id = %s
                  AND id NOT IN (
                      SELECT id FROM history
                      WHERE session_id = %s
                      ORDER BY id DESC
                      LIMIT %s
                  )
                """,
                (session_id, session_id, MAX_HISTORY_ITEMS),
            )

            # Refresh session metadata
            cur.execute(
                """
                UPDATE sessions
                SET last_active = now(),
                    turn_count  = (
                        SELECT COUNT(*) / 2
                        FROM history
                        WHERE session_id = %s
                    )
                WHERE session_id = %s
                """,
                (session_id, session_id),
            )

    def get_history(self, session_id: str) -> list[dict]:
        with _get_conn() as cur:
            cur.execute(
                """
                SELECT role, text, created_at AS timestamp
                FROM history
                WHERE session_id = %s
                ORDER BY id ASC
                """,
                (session_id,),
            )
            return [dict(row) for row in cur.fetchall()]

    def history_context(self, session_id: str) -> Optional[str]:
        history = self.get_history(session_id)
        if not history:
            return None
        return "\n".join(
            f"{item['role'].capitalize()}: {item['text']}"
            for item in history
        )

    # ── Document tracking ─────────────────────────────────────────────────────

    def add_document(
        self,
        session_id: str,
        file_id: str,
        original_name: str,
        size_bytes: int,
    ) -> None:
        with _get_conn() as cur:
            cur.execute(
                """
                INSERT INTO documents
                    (file_id, session_id, original_name, size_bytes, status, uploaded_at)
                VALUES (%s, %s, %s, %s, 'indexed', now())
                ON CONFLICT (file_id) DO NOTHING
                """,
                (file_id, session_id, original_name, size_bytes),
            )

    def list_documents(self, session_id: str) -> list[dict]:
        with _get_conn() as cur:
            cur.execute(
                """
                SELECT file_id, original_name, size_bytes, status, uploaded_at
                FROM documents
                WHERE session_id = %s
                ORDER BY uploaded_at DESC
                """,
                (session_id,),
            )
            return [dict(row) for row in cur.fetchall()]

    def has_documents(self, session_id: str) -> bool:
        with _get_conn() as cur:
            cur.execute(
                "SELECT 1 FROM documents WHERE session_id = %s LIMIT 1",
                (session_id,),
            )
            return cur.fetchone() is not None

    def delete_document(self, session_id: str, file_id: str) -> bool:
        with _get_conn() as cur:
            cur.execute(
                "DELETE FROM documents WHERE session_id = %s AND file_id = %s",
                (session_id, file_id),
            )
            return cur.rowcount > 0

    # ── Session listing / metadata ────────────────────────────────────────────

    def get_session_info(self, session_id: str) -> Optional[dict]:
        with _get_conn() as cur:
            cur.execute(
                """
                SELECT session_id, created_at, last_active, turn_count
                FROM sessions
                WHERE session_id = %s
                """,
                (session_id,),
            )
            row = cur.fetchone()
            return dict(row) if row else None

    def list_sessions(self) -> list[dict]:
        with _get_conn() as cur:
            cur.execute(
                """
                SELECT session_id, created_at, last_active, turn_count
                FROM sessions
                ORDER BY last_active DESC
                """
            )
            return [dict(row) for row in cur.fetchall()]

    # ── Maintenance ───────────────────────────────────────────────────────────

    def delete_session(self, session_id: str) -> None:
        """
        Delete a session and all its history / documents.
        ON DELETE CASCADE handles the child rows automatically.
        """
        with _get_conn() as cur:
            cur.execute(
                "DELETE FROM sessions WHERE session_id = %s",
                (session_id,),
            )

    def cleanup_inactive(self, max_age_minutes: int = 60) -> int:
        """
        Delete sessions that have been idle longer than max_age_minutes.
        ON DELETE CASCADE removes their history and documents automatically.

        TIP: for automatic cleanup without a cron job, enable pg_cron on
        Azure Database for PostgreSQL Flexible Server and schedule:

            SELECT cron.schedule(
                'cleanup-sessions',
                '0 * * * *',
                $$DELETE FROM sessions
                  WHERE last_active < now() - INTERVAL '60 minutes'$$
            );
        """
        cutoff = _now() - timedelta(minutes=max_age_minutes)
        with _get_conn() as cur:
            cur.execute(
                "DELETE FROM sessions WHERE last_active < %s",
                (cutoff,),
            )
            return cur.rowcount


session_store = SessionStore()