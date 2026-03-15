import json
import logging
from typing import Any, Dict, Optional

LOGGER = logging.getLogger(__name__)

# In-memory fallback used when the DB is unavailable so requests never crash.
_fallback: Dict[str, Dict[str, Any]] = {}


def _get_cursor():
    from store.db import get_cursor
    return get_cursor()


def set_interview_results_processing(session_id: str) -> None:
    save_interview_results(str(session_id), {"status": "processing"})


def save_interview_results(session_id: str, results: Dict[str, Any]) -> None:
    sid = str(session_id)
    # Always keep an in-memory copy so reads work even if DB is down.
    _fallback[sid] = results
    try:
        cur = _get_cursor()
        try:
            cur.execute(
                "INSERT INTO interview_results (session_id, results) VALUES (%s, %s) "
                "ON CONFLICT (session_id) DO UPDATE SET results = EXCLUDED.results",
                (sid, json.dumps(results)),
            )
        finally:
            cur.close()
    except Exception as exc:
        LOGGER.error("[RESULTS] DB write failed for session %s — using memory fallback: %s", sid, exc)


def get_interview_results(session_id: str) -> Optional[Dict[str, Any]]:
    sid = str(session_id)
    try:
        cur = _get_cursor()
        try:
            cur.execute(
                "SELECT results FROM interview_results WHERE session_id = %s",
                (sid,),
            )
            row = cur.fetchone()
        finally:
            cur.close()

        if row is None:
            return _fallback.get(sid)
        results = row["results"]
        if isinstance(results, str):
            results = json.loads(results)
        return results
    except Exception as exc:
        LOGGER.error("[RESULTS] DB read failed for session %s — using memory fallback: %s", sid, exc)
        return _fallback.get(sid)


def clear_interview_results(session_id: str) -> None:
    sid = str(session_id)
    _fallback.pop(sid, None)
    try:
        cur = _get_cursor()
        try:
            cur.execute(
                "DELETE FROM interview_results WHERE session_id = %s",
                (sid,),
            )
        finally:
            cur.close()
    except Exception as exc:
        LOGGER.error("[RESULTS] DB delete failed for session %s: %s", sid, exc)
