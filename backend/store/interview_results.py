import json
import logging
from typing import Any, Dict, Optional

from store.db import cursor, is_db_configured

LOGGER = logging.getLogger(__name__)

# In-memory fallback used when the DB is unavailable so requests never crash.
# On serverless this only survives within a single warm instance — it keeps a
# request from 500ing, it does not make results durable.
_fallback: Dict[str, Dict[str, Any]] = {}


def set_interview_results_processing(session_id: str) -> None:
    save_interview_results(str(session_id), {"status": "processing"})


def save_interview_results(session_id: str, results: Dict[str, Any]) -> None:
    sid = str(session_id)
    _fallback[sid] = results

    if not is_db_configured():
        LOGGER.warning(
            "[RESULTS] No DATABASE_URL — results for %s are memory-only and will "
            "not survive a cold start",
            sid,
        )
        return
    try:
        with cursor() as cur:
            cur.execute(
                "INSERT INTO interview_results (session_id, results) VALUES (%s, %s) "
                "ON CONFLICT (session_id) DO UPDATE SET results = EXCLUDED.results, "
                "updated_at = now()",
                (sid, json.dumps(results)),
            )
    except Exception as exc:  # noqa: BLE001
        LOGGER.error(
            "[RESULTS] DB write failed for session %s — using memory fallback: %s",
            sid,
            exc,
        )


def get_interview_results(session_id: str) -> Optional[Dict[str, Any]]:
    sid = str(session_id)

    if is_db_configured():
        try:
            with cursor() as cur:
                cur.execute(
                    "SELECT results FROM interview_results WHERE session_id = %s",
                    (sid,),
                )
                row = cur.fetchone()
            if row is not None:
                results = row["results"]
                if isinstance(results, str):
                    results = json.loads(results)
                return results
        except Exception as exc:  # noqa: BLE001
            LOGGER.error(
                "[RESULTS] DB read failed for session %s — using memory fallback: %s",
                sid,
                exc,
            )

    return _fallback.get(sid)


def clear_interview_results(session_id: str) -> None:
    sid = str(session_id)
    _fallback.pop(sid, None)

    if not is_db_configured():
        return
    try:
        with cursor() as cur:
            cur.execute(
                "DELETE FROM interview_results WHERE session_id = %s", (sid,)
            )
    except Exception as exc:  # noqa: BLE001
        LOGGER.error("[RESULTS] DB delete failed for session %s: %s", sid, exc)
