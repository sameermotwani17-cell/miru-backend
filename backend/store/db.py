import logging
import os
from contextlib import contextmanager

LOGGER = logging.getLogger(__name__)

# Every table MIRU needs. Serverless functions have no durable local disk, so
# session state and interview turns live here rather than in process memory or
# JSON files on the filesystem.
_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS interview_results (
    session_id TEXT PRIMARY KEY,
    results    JSONB        NOT NULL,
    updated_at TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS interview_sessions (
    session_id TEXT PRIMARY KEY,
    state      JSONB        NOT NULL,
    updated_at TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS interview_turns (
    session_id TEXT PRIMARY KEY,
    turns      JSONB        NOT NULL DEFAULT '[]'::jsonb,
    updated_at TIMESTAMPTZ  NOT NULL DEFAULT now()
);
"""

_conn = None
_schema_ready = False


def database_url() -> str | None:
    """Read DATABASE_URL at call time, not import time.

    Importing this module must never raise: on Vercel an import-time failure
    takes down the whole function cold start, including /health, which is the
    one endpoint you need in order to diagnose a missing env var.
    """
    url = os.getenv("DATABASE_URL")
    return url.strip() if url and url.strip() else None


def is_db_configured() -> bool:
    return database_url() is not None


def _connect():
    global _schema_ready
    import psycopg2

    conn = psycopg2.connect(database_url(), connect_timeout=10)
    conn.autocommit = True
    if not _schema_ready:
        with conn.cursor() as cur:
            cur.execute(_SCHEMA_SQL)
        _schema_ready = True
        LOGGER.info("[DB] Schema verified (results, sessions, turns)")
    LOGGER.info("[DB] Connected")
    return conn


def get_connection():
    """Return a live connection, reconnecting if the socket went away.

    Serverless containers are frozen between invocations, so a connection that
    was healthy on the previous request is routinely dead on the next one.
    """
    global _conn
    import psycopg2

    if not is_db_configured():
        raise RuntimeError("DATABASE_URL is not set")

    try:
        if _conn is None or _conn.closed:
            _conn = _connect()
        else:
            with _conn.cursor() as cur:
                cur.execute("SELECT 1")
    except psycopg2.Error as exc:
        LOGGER.warning("[DB] Connection unusable (%s) — reconnecting", exc)
        try:
            if _conn is not None:
                _conn.close()
        except Exception:  # noqa: BLE001
            pass
        _conn = _connect()
    return _conn


@contextmanager
def cursor():
    """Yield a dict cursor and always close it.

    The previous implementation leaked a cursor on every health probe.
    """
    import psycopg2.extras

    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        yield cur
    finally:
        cur.close()


def get_cursor():
    """Backwards-compatible cursor factory. Caller is responsible for close()."""
    import psycopg2.extras

    return get_connection().cursor(cursor_factory=psycopg2.extras.RealDictCursor)


def ping() -> tuple[bool, str]:
    """Return (alive, detail) for the /health endpoint and the gauntlet."""
    if not is_db_configured():
        return False, "DATABASE_URL is not set"
    try:
        with cursor() as cur:
            cur.execute("SELECT 1 AS ok")
            cur.fetchone()
        return True, "connected"
    except Exception as exc:  # noqa: BLE001
        return False, f"{type(exc).__name__}: {exc}"
