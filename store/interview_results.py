import json
import logging
from typing import Any, Dict, Optional

from store.db import get_cursor

LOGGER = logging.getLogger(__name__)


def set_interview_results_processing(session_id: str) -> None:
    sid = str(session_id)
    save_interview_results(sid, {"status": "processing"})


def save_interview_results(session_id: str, results: Dict[str, Any]) -> None:
    sid = str(session_id)
    cur = get_cursor()
    try:
        cur.execute(
            "INSERT INTO interview_results (session_id, results) VALUES (%s, %s) "
            "ON CONFLICT (session_id) DO UPDATE SET results = EXCLUDED.results",
            (sid, json.dumps(results)),
        )
    finally:
        cur.close()


def get_interview_results(session_id: str) -> Optional[Dict[str, Any]]:
    sid = str(session_id)
    cur = get_cursor()
    try:
        cur.execute(
            "SELECT results FROM interview_results WHERE session_id = %s",
            (sid,),
        )
        row = cur.fetchone()
    finally:
        cur.close()

    if row is None:
        return None
    results = row["results"]
    if isinstance(results, str):
        results = json.loads(results)
    return results


def clear_interview_results(session_id: str) -> None:
    sid = str(session_id)
    cur = get_cursor()
    try:
        cur.execute(
            "DELETE FROM interview_results WHERE session_id = %s",
            (sid,),
        )
    finally:
        cur.close()
