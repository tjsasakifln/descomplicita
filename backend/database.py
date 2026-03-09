"""Minimal persistence layer using SQLite (TD-H04).

Provides lightweight persistence for:
- Search history (who searched what, when)
- User preferences (saved searches, favorite sectors)

Design decisions:
- SQLite chosen for zero-cost POC (no external service needed)
- aiosqlite for async compatibility with FastAPI
- File-based storage at DATA_DIR/descomplicita.db
- Compatible with Railway/Vercel (ephemeral storage is acceptable for POC)
- Future migration path: Supabase PostgreSQL for production persistence
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Optional

import aiosqlite

logger = logging.getLogger(__name__)

# Database file location (configurable via env)
DATA_DIR = os.getenv("DATA_DIR", os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.getenv("DATABASE_URL", os.path.join(DATA_DIR, "descomplicita.db"))

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS search_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT NOT NULL UNIQUE,
    ufs TEXT NOT NULL,
    data_inicial TEXT NOT NULL,
    data_final TEXT NOT NULL,
    setor_id TEXT NOT NULL,
    termos_busca TEXT,
    total_raw INTEGER DEFAULT 0,
    total_filtrado INTEGER DEFAULT 0,
    status TEXT DEFAULT 'queued',
    created_at TEXT NOT NULL,
    completed_at TEXT,
    elapsed_seconds REAL
);

CREATE TABLE IF NOT EXISTS user_preferences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key TEXT NOT NULL UNIQUE,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_search_history_created
    ON search_history(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_search_history_setor
    ON search_history(setor_id);
"""


class Database:
    """Async SQLite database for search history and preferences."""

    def __init__(self, db_path: str = DB_PATH) -> None:
        self.db_path = db_path
        self._db: Optional[aiosqlite.Connection] = None

    async def connect(self) -> None:
        """Open database connection and create schema."""
        self._db = await aiosqlite.connect(self.db_path)
        self._db.row_factory = aiosqlite.Row
        await self._db.executescript(_SCHEMA_SQL)
        await self._db.commit()
        logger.info("Database connected: %s", self.db_path)

    async def close(self) -> None:
        """Close database connection."""
        if self._db:
            await self._db.close()
            self._db = None
            logger.info("Database connection closed")

    # --- Search History ---

    async def record_search(
        self,
        job_id: str,
        ufs: list[str],
        data_inicial: str,
        data_final: str,
        setor_id: str,
        termos_busca: Optional[str] = None,
    ) -> None:
        """Record a new search job in history."""
        if not self._db:
            return
        await self._db.execute(
            """INSERT OR IGNORE INTO search_history
               (job_id, ufs, data_inicial, data_final, setor_id, termos_busca, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                job_id,
                json.dumps(ufs),
                data_inicial,
                data_final,
                setor_id,
                termos_busca,
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        await self._db.commit()

    async def complete_search(
        self,
        job_id: str,
        total_raw: int,
        total_filtrado: int,
        elapsed_seconds: float,
    ) -> None:
        """Update search history with completion data."""
        if not self._db:
            return
        await self._db.execute(
            """UPDATE search_history
               SET status='completed', total_raw=?, total_filtrado=?,
                   elapsed_seconds=?, completed_at=?
               WHERE job_id=?""",
            (
                total_raw,
                total_filtrado,
                round(elapsed_seconds, 2),
                datetime.now(timezone.utc).isoformat(),
                job_id,
            ),
        )
        await self._db.commit()

    async def fail_search(self, job_id: str) -> None:
        """Mark a search as failed in history."""
        if not self._db:
            return
        await self._db.execute(
            """UPDATE search_history SET status='failed', completed_at=? WHERE job_id=?""",
            (datetime.now(timezone.utc).isoformat(), job_id),
        )
        await self._db.commit()

    async def get_recent_searches(self, limit: int = 20) -> list[dict[str, Any]]:
        """Get recent search history."""
        if not self._db:
            return []
        cursor = await self._db.execute(
            """SELECT job_id, ufs, data_inicial, data_final, setor_id,
                      termos_busca, total_raw, total_filtrado, status,
                      created_at, elapsed_seconds
               FROM search_history ORDER BY created_at DESC LIMIT ?""",
            (limit,),
        )
        rows = await cursor.fetchall()
        return [
            {
                "job_id": row["job_id"],
                "ufs": json.loads(row["ufs"]),
                "data_inicial": row["data_inicial"],
                "data_final": row["data_final"],
                "setor_id": row["setor_id"],
                "termos_busca": row["termos_busca"],
                "total_raw": row["total_raw"],
                "total_filtrado": row["total_filtrado"],
                "status": row["status"],
                "created_at": row["created_at"],
                "elapsed_seconds": row["elapsed_seconds"],
            }
            for row in rows
        ]

    # --- User Preferences ---

    async def set_preference(self, key: str, value: Any) -> None:
        """Set a user preference (upsert)."""
        if not self._db:
            return
        await self._db.execute(
            """INSERT INTO user_preferences (key, value, updated_at)
               VALUES (?, ?, ?)
               ON CONFLICT(key) DO UPDATE SET value=?, updated_at=?""",
            (
                key,
                json.dumps(value),
                datetime.now(timezone.utc).isoformat(),
                json.dumps(value),
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        await self._db.commit()

    async def get_preference(self, key: str) -> Optional[Any]:
        """Get a user preference by key."""
        if not self._db:
            return None
        cursor = await self._db.execute(
            "SELECT value FROM user_preferences WHERE key=?", (key,)
        )
        row = await cursor.fetchone()
        if row:
            return json.loads(row["value"])
        return None

    async def get_all_preferences(self) -> dict[str, Any]:
        """Get all user preferences as a dict."""
        if not self._db:
            return {}
        cursor = await self._db.execute("SELECT key, value FROM user_preferences")
        rows = await cursor.fetchall()
        return {row["key"]: json.loads(row["value"]) for row in rows}
