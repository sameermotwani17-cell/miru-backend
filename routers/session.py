import time
import uuid
from typing import Any, Dict

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from models.session import SessionState
from store.sessions import create_session, get_session, delete_session


router = APIRouter(prefix="/api/session", tags=["session"])


class StartSessionRequest(BaseModel):
    user_name: str
    target_role: str
    company: str
    language_mode: str
    duration_mins: int


@router.post("/start")
def start_session(payload: StartSessionRequest) -> Dict[str, Any]:
    session_id = str(uuid.uuid4())
    now_ms = int(time.time() * 1000)
    timer_end_epoch = now_ms + payload.duration_mins * 60 * 1000

    state = SessionState(
        session_id=session_id,
        user_name=payload.user_name,
        target_role=payload.target_role,
        company=payload.company,
        language_mode=payload.language_mode,
        duration_mins=payload.duration_mins,
        timer_end_epoch=timer_end_epoch,
    )

    create_session(state)

    return {
        "session_id": session_id,
        "timer_end_epoch": timer_end_epoch,
    }


@router.get("/{session_id}/state")
def get_session_state(session_id: str) -> Dict[str, Any]:
    state = get_session(session_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Session not found")

    now_ms = int(time.time() * 1000)
    time_remaining_ms = max(state.timer_end_epoch - now_ms, 0)

    return {
        "turn_count": state.turn_count,
        "scores": state.running_scores,
        "time_remaining_ms": time_remaining_ms,
    }


@router.delete("/{session_id}")
def delete_session_endpoint(session_id: str) -> Dict[str, bool]:
    delete_session(session_id)
    return {"ok": True}

