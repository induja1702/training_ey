"""
session_store.py

SQLite-backed session management, extended with per-session document
tracking so each chat session only "sees" the documents uploaded within it.

Tables:
  sessions    - one row per chat session
  history     - chat turns, scoped by session_id
  documents   - uploaded files, scoped by session_id (this is what lets
                upload_api.py and chat.py agree on "which docs belong to
                this chat")
"""

import sqlite3
import threading
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "sessions.db"
MAX_HISTORY_ITEMS = 20

_write_lock = threading.Lock()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def _connect():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                session_id   TEXT PRIMARY KEY,
                created_at   TEXT NOT NULL,
                last_active  TEXT NOT NULL,
                turn_count   INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS history (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id  TEXT NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
                role        TEXT NOT NULL,
                text        TEXT NOT NULL,
                timestamp   TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS documents (
                file_id       TEXT PRIMARY KEY,
                session_id    TEXT NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
                original_name TEXT NOT NULL,
                size_bytes    INTEGER NOT NULL,
                status        TEXT NOT NULL DEFAULT 'indexed',
                uploaded_at   TEXT NOT NULL
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_history_session ON history(session_id, id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_documents_session ON documents(session_id)")


init_db()


class SessionStore:
    # -----------------------------------------------------------
    # Session creation / lookup
    # -----------------------------------------------------------
    def make_session(self, session_id: str | None = None, reset: bool = False) -> str:
        with _write_lock, _connect() as conn:
            exists = False
            if session_id:
                row = conn.execute("SELECT 1 FROM sessions WHERE session_id = ?", (session_id,)).fetchone()
                exists = row is not None

            if reset or not session_id or not exists:
                session_id = str(uuid.uuid4())
                now = _now_iso()
                conn.execute(
                    "INSERT INTO sessions (session_id, created_at, last_active, turn_count) VALUES (?, ?, ?, 0)",
                    (session_id, now, now),
                )
            return session_id

    def session_exists(self, session_id: str) -> bool:
        with _connect() as conn:
            row = conn.execute("SELECT 1 FROM sessions WHERE session_id = ?", (session_id,)).fetchone()
            return row is not None

    # -----------------------------------------------------------
    # History read/write
    # -----------------------------------------------------------
    def append_history(self, session_id: str, role: str, text: str) -> None:
        with _write_lock, _connect() as conn:
            now = _now_iso()
            conn.execute(
                "INSERT INTO history (session_id, role, text, timestamp) VALUES (?, ?, ?, ?)",
                (session_id, role, text, now),
            )
            conn.execute("UPDATE sessions SET last_active = ? WHERE session_id = ?", (now, session_id))
            conn.execute(
                """
                DELETE FROM history
                WHERE session_id = ? AND id NOT IN (
                    SELECT id FROM history WHERE session_id = ? ORDER BY id DESC LIMIT ?
                )
                """,
                (session_id, session_id, MAX_HISTORY_ITEMS),
            )
            count = conn.execute(
                "SELECT COUNT(*) AS c FROM history WHERE session_id = ?", (session_id,)
            ).fetchone()["c"]
            conn.execute("UPDATE sessions SET turn_count = ? WHERE session_id = ?", (count // 2, session_id))

    def get_history(self, session_id: str) -> list[dict]:
        with _connect() as conn:
            rows = conn.execute(
                "SELECT role, text, timestamp FROM history WHERE session_id = ? ORDER BY id ASC",
                (session_id,),
            ).fetchall()
            return [dict(row) for row in rows]

    def history_context(self, session_id: str) -> str | None:
        history = self.get_history(session_id)
        if not history:
            return None
        return "\n".join(f"{item['role'].capitalize()}: {item['text']}" for item in history)

    # -----------------------------------------------------------
    # Document tracking — scopes uploads to a single chat session
    # -----------------------------------------------------------
    def add_document(self, session_id: str, file_id: str, original_name: str, size_bytes: int) -> None:
        with _write_lock, _connect() as conn:
            conn.execute(
                "INSERT INTO documents (file_id, session_id, original_name, size_bytes, status, uploaded_at) "
                "VALUES (?, ?, ?, ?, 'indexed', ?)",
                (file_id, session_id, original_name, size_bytes, _now_iso()),
            )

    def list_documents(self, session_id: str) -> list[dict]:
        with _connect() as conn:
            rows = conn.execute(
                "SELECT file_id, original_name, size_bytes, status, uploaded_at FROM documents "
                "WHERE session_id = ? ORDER BY uploaded_at DESC",
                (session_id,),
            ).fetchall()
            return [dict(row) for row in rows]

    def has_documents(self, session_id: str) -> bool:
        with _connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM documents WHERE session_id = ? LIMIT 1", (session_id,)
            ).fetchone()
            return row is not None

    def delete_document(self, session_id: str, file_id: str) -> bool:
        with _write_lock, _connect() as conn:
            cur = conn.execute(
                "DELETE FROM documents WHERE session_id = ? AND file_id = ?", (session_id, file_id)
            )
            return cur.rowcount > 0

    # -----------------------------------------------------------
    # Session listing / metadata
    # -----------------------------------------------------------
    def get_session_info(self, session_id: str) -> dict | None:
        with _connect() as conn:
            row = conn.execute(
                "SELECT session_id, created_at, last_active, turn_count FROM sessions WHERE session_id = ?",
                (session_id,),
            ).fetchone()
            return dict(row) if row else None

    def list_sessions(self) -> list[dict]:
        with _connect() as conn:
            rows = conn.execute(
                "SELECT session_id, created_at, last_active, turn_count FROM sessions ORDER BY last_active DESC"
            ).fetchall()
            return [dict(row) for row in rows]

    # -----------------------------------------------------------
    # Maintenance
    # -----------------------------------------------------------
    def delete_session(self, session_id: str) -> None:
        with _write_lock, _connect() as conn:
            conn.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))

    def cleanup_inactive(self, max_age_minutes: int = 60) -> int:
        with _write_lock, _connect() as conn:
            cutoff = datetime.now(timezone.utc).timestamp() - max_age_minutes * 60
            rows = conn.execute("SELECT session_id, last_active FROM sessions").fetchall()
            to_delete = [
                row["session_id"] for row in rows
                if datetime.fromisoformat(row["last_active"]).timestamp() < cutoff
            ]
            for sid in to_delete:
                conn.execute("DELETE FROM sessions WHERE session_id = ?", (sid,))
            return len(to_delete)


session_store = SessionStore()