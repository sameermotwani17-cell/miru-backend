import time
import uuid
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from models.session import SessionState
from services.score_dimensions import SCORE_DIMENSIONS
from store.interview_turns import get_session_turns
from store.sessions import create_session, get_session, delete_session


router = APIRouter(prefix="/api/session", tags=["session"])


class StartSessionRequest(BaseModel):
    user_name: str
    target_role: str
    company: str
    language_mode: str
    duration_mins: int
    cv_context: Optional[str] = None


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
        cv_context=payload.cv_context,
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

    # Derive progress from stored turns rather than SessionState counters.
    # Nothing ever incremented those counters, so this endpoint used to report
    # turn_count=0 and all-zero scores for the entire interview.
    turns = get_session_turns(session_id)
    running_scores = {dim: 0.0 for dim in SCORE_DIMENSIONS}
    if turns:
        for dim in SCORE_DIMENSIONS:
            values = [float(t.get("scores", {}).get(dim, 0) or 0) for t in turns]
            running_scores[dim] = round(sum(values) / len(values), 2)

    return {
        "turn_count": len(turns),
        "scores": running_scores,
        "time_remaining_ms": time_remaining_ms,
    }


@router.delete("/{session_id}")
def delete_session_endpoint(session_id: str) -> Dict[str, bool]:
    delete_session(session_id)
    return {"ok": True}
