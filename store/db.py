import logging
import os

import psycopg2
import psycopg2.extras

LOGGER = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL environment variable is not set")

_conn: psycopg2.extensions.connection | None = None


def _connect() -> psycopg2.extensions.connection:
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True
    LOGGER.info("[DB] Connected to Supabase database")
    return conn


def get_connection() -> psycopg2.extensions.connection:
    """Return a live connection, reconnecting automatically if needed."""
    global _conn
    try:
        if _conn is None or _conn.closed:
            _conn = _connect()
        else:
            # Lightweight liveness check — no round-trip needed for autocommit.
            _conn.cursor().execute("SELECT 1")
    except psycopg2.OperationalError as exc:
        LOGGER.warning("[DB] Connection lost (%s) — reconnecting…", exc)
        _conn = _connect()
    return _conn


def get_cursor() -> psycopg2.extras.RealDictCursor:
    return get_connection().cursor(cursor_factory=psycopg2.extras.RealDictCursor)
