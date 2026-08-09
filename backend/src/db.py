"""SQLite persistence layer for DukaanMitra caller memory.

Provides async helpers to store and retrieve caller information
across agent restarts. Uses aiosqlite for non-blocking runtime
queries and plain sqlite3 for the one-time table creation at startup.
"""

import json
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import aiosqlite

logger = logging.getLogger("agent.db")

# Default DB path: backend/dukaan_mitra.db (sibling of src/)
_DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "dukaan_mitra.db"

_db_path: Path = _DEFAULT_DB_PATH


def init_db(db_path: Path | None = None) -> None:
    """Create the callers table if it doesn't exist.

    This runs synchronously and is meant to be called once during
    process pre-warm (before the async event loop is available).
    """
    global _db_path
    if db_path is not None:
        _db_path = db_path

    logger.info("Initializing caller database at %s", _db_path)
    conn = sqlite3.connect(str(_db_path))
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS callers (
                user_id             TEXT PRIMARY KEY,
                name                TEXT NOT NULL,
                role                TEXT NOT NULL DEFAULT 'customer',
                language_preference TEXT NOT NULL DEFAULT 'English',
                facts               TEXT NOT NULL DEFAULT '{}',
                last_interaction    TEXT NOT NULL
            )
            """
        )
        conn.commit()
        logger.info("Caller database ready.")
    finally:
        conn.close()


async def get_caller(user_id: str) -> dict | None:
    """Return the caller record as a dict, or None if not found."""
    async with aiosqlite.connect(str(_db_path)) as conn:
        conn.row_factory = aiosqlite.Row
        cursor = await conn.execute(
            "SELECT * FROM callers WHERE user_id = ?",
            (user_id,),
        )
        row = await cursor.fetchone()
        if row is None:
            return None

        record = dict(row)
        # Deserialize the JSON facts blob
        try:
            record["facts"] = json.loads(record["facts"])
        except (json.JSONDecodeError, TypeError):
            record["facts"] = {}
        return record


async def upsert_caller(
    user_id: str,
    name: str,
    role: str,
    language_preference: str,
    facts: dict,
) -> None:
    """Insert or update a caller record, setting last_interaction to now."""
    now = datetime.now(timezone.utc).isoformat()
    facts_json = json.dumps(facts, ensure_ascii=False)

    async with aiosqlite.connect(str(_db_path)) as conn:
        await conn.execute(
            """
            INSERT INTO callers (user_id, name, role, language_preference, facts, last_interaction)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                name                = excluded.name,
                role                = excluded.role,
                language_preference = excluded.language_preference,
                facts               = excluded.facts,
                last_interaction    = excluded.last_interaction
            """,
            (user_id, name, role, language_preference, facts_json, now),
        )
        await conn.commit()
        logger.info("Saved caller info for user_id=%s", user_id)
