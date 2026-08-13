"""Session persistence.

Sessions used to live in a module-level dict. That works on a single
long-lived Railway container and breaks completely on serverless: every
request may land on a different instance, so `POST /session/start` and the
next `POST /interview/turn` would not share memory and the interview would
lose the candidate's name, company, CV and timer.

State is therefore stored in Postgres, with an in-process fallback so the
app still runs locally with no DATABASE_URL set.
"""

import json
import logging
from dataclasses import asdict, fields
from typing import Any, Dict, Optional

from models.session import SessionState
from store.db import cursor, is_db_configured
from store.interview_results import clear_interview_results
from store.interview_turns import clear_session_turns

LOGGER = logging.getLogger(__name__)

# Fallback only. Never the source of truth when a database is configured.
_memory: Dict[str, Dict[str, Any]] = {}

_FIELD_NAMES = {f.name for f in fields(SessionState)}


def _to_dict(state: SessionState) -> Dict[str, Any]:
    return asdict(state)


def _from_dict(payload: Dict[str, Any]) -> Optional[SessionState]:
    if not isinstance(payload, dict):
        return None
    # Drop unknown keys so an older row with a since-removed field still loads.
    known = {k: v for k, v in payload.items() if k in _FIELD_NAMES}
    try:
        return SessionState(**known)
    except TypeError as exc:
        LOGGER.warning("[SESSION] Could not rehydrate session state: %s", exc)
        return None


def create_session(state: SessionState) -> None:
    payload = _to_dict(state)
    _memory[state.session_id] = payload

    if not is_db_configured():
        return
    try:
        with cursor() as cur:
            cur.execute(
                "INSERT INTO interview_sessions (session_id, state) VALUES (%s, %s) "
                "ON CONFLICT (session_id) DO UPDATE SET state = EXCLUDED.state, "
                "updated_at = now()",
                (state.session_id, json.dumps(payload)),
            )
    except Exception as exc:  # noqa: BLE001
        LOGGER.error(
            "[SESSION] DB write failed for %s — memory fallback only, this "
            "session will not survive a cold start: %s",
            state.session_id,
            exc,
        )


def get_session(session_id: str) -> Optional[SessionState]:
    sid = str(session_id)

    if is_db_configured():
        try:
            with cursor() as cur:
                cur.execute(
                    "SELECT state FROM interview_sessions WHERE session_id = %s",
                    (sid,),
                )
                row = cur.fetchone()
            if row is not None:
                state = row["state"]
                if isinstance(state, str):
                    state = json.loads(state)
                rehydrated = _from_dict(state)
                if rehydrated is not None:
                    return rehydrated
        except Exception as exc:  # noqa: BLE001
            LOGGER.error("[SESSION] DB read failed for %s: %s", sid, exc)

    cached = _memory.get(sid)
    return _from_dict(cached) if cached else None


def update_session(state: SessionState) -> None:
    """Persist mutations to an existing session."""
    create_session(state)


def delete_session(session_id: str) -> None:
    sid = str(session_id)
    _memory.pop(sid, None)

    if is_db_configured():
        try:
            with cursor() as cur:
                cur.execute(
                    "DELETE FROM interview_sessions WHERE session_id = %s", (sid,)
                )
        except Exception as exc:  # noqa: BLE001
            LOGGER.error("[SESSION] DB delete failed for %s: %s", sid, exc)

    clear_session_turns(sid)
    clear_interview_results(sid)
