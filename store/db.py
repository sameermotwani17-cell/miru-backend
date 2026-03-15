import logging
import os

import psycopg2
import psycopg2.extras

LOGGER = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL environment variable is not set")

_conn: psycopg2.extensions.connection | None = None

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS interview_results (
    session_id TEXT PRIMARY KEY,
    results    JSONB        NOT NULL,
    updated_at TIMESTAMPTZ  NOT NULL DEFAULT now()
);
"""


def _connect() -> psycopg2.extensions.connection:
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True
    LOGGER.info("[DB] Connected to Supabase database")
    # Ensure the table exists the first time we connect.
    with conn.cursor() as cur:
        cur.execute(_SCHEMA_SQL)
    LOGGER.info("[DB] Schema verified (interview_results table ready)")
    return conn


def get_connection() -> psycopg2.extensions.connection:
    """Return a live connection, reconnecting automatically if needed."""
    global _conn
    try:
        if _conn is None or _conn.closed:
            _conn = _connect()
        else:
            _conn.cursor().execute("SELECT 1")
    except psycopg2.OperationalError as exc:
        LOGGER.warning("[DB] Connection lost (%s) — reconnecting…", exc)
        _conn = _connect()
    return _conn


def get_cursor() -> psycopg2.extras.RealDictCursor:
    return get_connection().cursor(cursor_factory=psycopg2.extras.RealDictCursor)
