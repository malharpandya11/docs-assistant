"""SQLite persistence for users, auth tokens, and chat history.

Plain stdlib sqlite3, no ORM — matches the rest of this codebase's hand-rolled
style (chunking is regex, retrieval is direct chromadb calls). One connection
per call rather than a shared long-lived one: FastAPI's sync routes run in a
threadpool, and sqlite3 connections aren't safe to share across threads
without extra care. Opening a fresh connection per call is cheap at this
scale and sidesteps that entirely.
"""

import json
import os
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

from common import BASE_DIR

DB_PATH = Path(os.getenv("APP_DB_PATH", BASE_DIR / "app.db"))
TOKEN_TTL_DAYS = 30

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS auth_tokens (
    token TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id),
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS conversations (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id),
    title TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS messages (
    id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL REFERENCES conversations(id),
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    sources TEXT,
    is_error INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_conversations_user ON conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id);
"""


@contextmanager
def get_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_db() as conn:
        conn.executescript(SCHEMA)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    return uuid.uuid4().hex


# --- users ---


def create_user(email: str, password_hash: str) -> dict:
    user_id = _new_id()
    with get_db() as conn:
        conn.execute(
            "INSERT INTO users (id, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
            (user_id, email, password_hash, _now()),
        )
    return {"id": user_id, "email": email}


def get_user_by_email(email: str) -> dict | None:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    return dict(row) if row else None


# --- auth tokens ---


def create_token(user_id: str) -> str:
    token = uuid.uuid4().hex + uuid.uuid4().hex
    expires_at = (datetime.now(timezone.utc) + timedelta(days=TOKEN_TTL_DAYS)).isoformat()
    with get_db() as conn:
        conn.execute(
            "INSERT INTO auth_tokens (token, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
            (token, user_id, _now(), expires_at),
        )
    return token


def get_user_by_token(token: str) -> dict | None:
    with get_db() as conn:
        row = conn.execute(
            """SELECT users.* FROM auth_tokens
               JOIN users ON users.id = auth_tokens.user_id
               WHERE auth_tokens.token = ? AND auth_tokens.expires_at > ?""",
            (token, _now()),
        ).fetchone()
    return dict(row) if row else None


def delete_token(token: str) -> None:
    with get_db() as conn:
        conn.execute("DELETE FROM auth_tokens WHERE token = ?", (token,))


# --- conversations ---


def create_conversation(user_id: str) -> dict:
    conv_id = _new_id()
    ts = _now()
    with get_db() as conn:
        conn.execute(
            "INSERT INTO conversations (id, user_id, title, created_at, updated_at) "
            "VALUES (?, ?, NULL, ?, ?)",
            (conv_id, user_id, ts, ts),
        )
    return {"id": conv_id, "title": None, "created_at": ts, "updated_at": ts}


def list_conversations(user_id: str) -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, title, created_at, updated_at FROM conversations "
            "WHERE user_id = ? ORDER BY updated_at DESC",
            (user_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def get_conversation(conversation_id: str, user_id: str) -> dict | None:
    with get_db() as conn:
        row = conn.execute(
            "SELECT id, title, created_at, updated_at FROM conversations "
            "WHERE id = ? AND user_id = ?",
            (conversation_id, user_id),
        ).fetchone()
    return dict(row) if row else None


def touch_conversation(conversation_id: str, title: str | None = None) -> None:
    with get_db() as conn:
        if title:
            conn.execute(
                "UPDATE conversations SET updated_at = ?, title = COALESCE(title, ?) WHERE id = ?",
                (_now(), title, conversation_id),
            )
        else:
            conn.execute(
                "UPDATE conversations SET updated_at = ? WHERE id = ?", (_now(), conversation_id)
            )


def delete_conversation(conversation_id: str, user_id: str) -> None:
    with get_db() as conn:
        conn.execute("DELETE FROM messages WHERE conversation_id = ?", (conversation_id,))
        conn.execute(
            "DELETE FROM conversations WHERE id = ? AND user_id = ?", (conversation_id, user_id)
        )


# --- messages ---


def add_message(
    conversation_id: str, role: str, content: str, sources: list[str] | None = None, is_error: bool = False
) -> dict:
    msg_id = _new_id()
    ts = _now()
    with get_db() as conn:
        conn.execute(
            "INSERT INTO messages (id, conversation_id, role, content, sources, is_error, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (msg_id, conversation_id, role, content, json.dumps(sources or []), int(is_error), ts),
        )
    return {
        "id": msg_id,
        "role": role,
        "content": content,
        "sources": sources or [],
        "isError": is_error,
        "created_at": ts,
    }


def list_messages(conversation_id: str) -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM messages WHERE conversation_id = ? ORDER BY created_at ASC",
            (conversation_id,),
        ).fetchall()
    result = []
    for row in rows:
        d = dict(row)
        result.append(
            {
                "id": d["id"],
                "role": d["role"],
                "content": d["content"],
                "sources": json.loads(d["sources"]) if d["sources"] else [],
                "isError": bool(d["is_error"]),
                "created_at": d["created_at"],
            }
        )
    return result
