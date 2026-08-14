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
    """Create all required tables if they don't exist and seed default records.

    This runs synchronously and is meant to be called once during
    process pre-warm (before the async event loop is available).
    """
    global _db_path
    if db_path is not None:
        _db_path = db_path

    logger.info("Initializing database at %s", _db_path)
    conn = sqlite3.connect(str(_db_path))
    try:
        # 1. Existing callers table
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

        # 2. products (product_id, shop_id, name, price, unit, stock_qty, last_updated)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS products (
                product_id   TEXT PRIMARY KEY,
                shop_id      TEXT NOT NULL,
                name         TEXT NOT NULL,
                price        REAL NOT NULL,
                unit         TEXT NOT NULL,
                stock_qty    INTEGER NOT NULL,
                last_updated TEXT NOT NULL
            )
            """
        )

        # 3. orders (order_id, customer_user_id, items_json, total, status, delivery_slot, created_at)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS orders (
                order_id         TEXT PRIMARY KEY,
                customer_user_id TEXT NOT NULL,
                items_json       TEXT NOT NULL,
                total            REAL NOT NULL,
                status           TEXT NOT NULL,
                delivery_slot    TEXT NOT NULL,
                created_at       TEXT NOT NULL
            )
            """
        )

        # 4. messages (message_id, from_user_id, from_name, message_text, created_at, read_flag)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                message_id   TEXT PRIMARY KEY,
                from_user_id TEXT NOT NULL,
                from_name    TEXT NOT NULL,
                message_text TEXT NOT NULL,
                created_at   TEXT NOT NULL,
                read_flag    INTEGER NOT NULL DEFAULT 0
            )
            """
        )

        # 5. sales (sale_id, item_name, quantity, unit, amount, sale_date)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sales (
                sale_id   TEXT PRIMARY KEY,
                item_name TEXT NOT NULL,
                quantity  REAL NOT NULL,
                unit      TEXT NOT NULL,
                amount    REAL NOT NULL,
                sale_date TEXT NOT NULL
            )
            """
        )

        # 6. credit (credit_id, customer_name, amount, type, note, created_at)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS credit (
                credit_id     TEXT PRIMARY KEY,
                customer_name TEXT NOT NULL,
                amount        REAL NOT NULL,
                type          TEXT NOT NULL,
                note          TEXT NOT NULL,
                created_at    TEXT NOT NULL
            )
            """
        )

        # 7. call_log (call_id, caller_name, caller_role, call_date, short_summary)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS call_log (
                call_id       TEXT PRIMARY KEY,
                caller_name   TEXT NOT NULL,
                caller_role   TEXT NOT NULL,
                call_date     TEXT NOT NULL,
                short_summary TEXT NOT NULL
            )
            """
        )

        # 10. calls — outcome tracking (channel, duration, outcome, failure_reason)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS calls (
                call_id          TEXT PRIMARY KEY,
                channel          TEXT NOT NULL DEFAULT 'web',
                started_at       TEXT NOT NULL,
                ended_at         TEXT,
                duration_seconds INTEGER,
                outcome          TEXT NOT NULL DEFAULT 'failed',
                failure_reason   TEXT
            )
            """
        )

        # 8. shop_info (shop_id, hours_text, address_text, updated_at)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS shop_info (
                shop_id      TEXT PRIMARY KEY,
                hours_text   TEXT NOT NULL,
                address_text TEXT NOT NULL,
                updated_at   TEXT NOT NULL
            )
            """
        )

        # 9. escalations (escalation_id, caller_name, issue_type, summary, urgency, language, contact_method, status, created_at)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS escalations (
                escalation_id  TEXT PRIMARY KEY,
                caller_name    TEXT NOT NULL,
                issue_type     TEXT NOT NULL,
                summary        TEXT NOT NULL,
                urgency        TEXT NOT NULL,
                language       TEXT NOT NULL,
                contact_method TEXT NOT NULL,
                status         TEXT NOT NULL DEFAULT 'open',
                created_at     TEXT NOT NULL
            )
            """
        )

        conn.commit()
        logger.info("All database tables created successfully.")

        # Seed shop_info if empty
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM shop_info")
        if cursor.fetchone()[0] == 0:
            now = datetime.now(timezone.utc).isoformat()
            cursor.execute(
                """
                INSERT INTO shop_info (shop_id, hours_text, address_text, updated_at)
                VALUES (?, ?, ?, ?)
                """,
                ("primary_shop", "9 AM - 9 PM", "123 Main Street, New Delhi", now),
            )
            logger.info("Seeded default shop_info.")

        # Seed 2 example rows in orders if empty
        cursor.execute("SELECT COUNT(*) FROM orders")
        if cursor.fetchone()[0] == 0:
            now = datetime.now(timezone.utc).isoformat()
            # Order 1
            cursor.execute(
                """
                INSERT INTO orders (order_id, customer_user_id, items_json, total, status, delivery_slot, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "ord_001",
                    "user_rahul",
                    '[{"name": "Milk", "qty": 2, "price": 60}]',
                    120.0,
                    "Pending",
                    "Morning (8 AM - 10 AM)",
                    now,
                ),
            )
            # Order 2
            cursor.execute(
                """
                INSERT INTO orders (order_id, customer_user_id, items_json, total, status, delivery_slot, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "ord_002",
                    "user_ananya",
                    '[{"name": "Bread", "qty": 1, "price": 40}, {"name": "Eggs", "qty": 1, "price": 80}]',
                    120.0,
                    "Delivered",
                    "Evening (6 PM - 8 PM)",
                    now,
                ),
            )
            logger.info("Seeded 2 example rows in orders.")

        # Seed products if empty
        cursor.execute("SELECT COUNT(*) FROM products")
        if cursor.fetchone()[0] == 0:
            now = datetime.now(timezone.utc).isoformat()
            sample_products = [
                ("prod_001", "primary_shop", "Full Cream Milk", 60.0, "1L packet", 15, now),
                ("prod_002", "primary_shop", "Brown Bread", 40.0, "400g loaf", 8, now),
                ("prod_003", "primary_shop", "Farm Fresh Eggs", 80.0, "tray of 12", 20, now),
                ("prod_004", "primary_shop", "Basmati Rice", 110.0, "1kg pack", 50, now),
                ("prod_005", "primary_shop", "Amul Butter", 55.0, "100g pack", 0, now),
            ]
            cursor.executemany(
                """
                INSERT INTO products (product_id, shop_id, name, price, unit, stock_qty, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                sample_products,
            )
            logger.info("Seeded sample products.")

        conn.commit()
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


async def insert_call_start(call_id: str, channel: str, started_at: str) -> None:
    """Insert a new call row when a session begins.

    Called at the start of my_agent() so we have a record even if the agent crashes.
    """
    async with aiosqlite.connect(str(_db_path)) as conn:
        await conn.execute(
            """
            INSERT OR IGNORE INTO calls (call_id, channel, started_at, outcome)
            VALUES (?, ?, ?, 'failed')
            """,
            (call_id, channel, started_at),
        )
        await conn.commit()
    logger.info("Inserted call start: call_id=%s channel=%s", call_id, channel)


async def update_call_end(
    call_id: str,
    ended_at: str,
    duration_seconds: int,
    outcome: str,
    failure_reason: str | None,
) -> None:
    """Update the call row with end-of-call outcome data.

    outcome must be 'success' or 'failed'.
    failure_reason is one of: user_declined | incomplete | tool_error |
    api_error | no_response | hangup  (or None for success).
    """
    async with aiosqlite.connect(str(_db_path)) as conn:
        await conn.execute(
            """
            UPDATE calls
            SET ended_at = ?,
                duration_seconds = ?,
                outcome = ?,
                failure_reason = ?
            WHERE call_id = ?
            """,
            (ended_at, duration_seconds, outcome, failure_reason, call_id),
        )
        await conn.commit()
    logger.info(
        "Updated call end: call_id=%s outcome=%s failure_reason=%s duration=%ss",
        call_id, outcome, failure_reason, duration_seconds,
    )
