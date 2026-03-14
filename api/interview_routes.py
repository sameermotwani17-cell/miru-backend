from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException

from services.interview_engine import run_interview_turn
from store.sessions import get_session


interview_router = APIRouter(prefix="/api", tags=["interview"])


@interview_router.post("/interview/turn")
async def interview_turn(payload: Dict[str, Any]) -> Dict[str, Any]:
    session_id = str(payload.get("session_id") or "").strip()
    if not session_id:
        raise HTTPException(status_code=422, detail="session_id is required")

    # Backward compatibility: older clients still send user_answer.
    user_message = payload.get("user_message")
    if user_message is None:
        user_message = payload.get("user_answer")
    if user_message is None:
        user_message = payload.get("answer")

    user_message = str(user_message or "").strip()
    if not user_message:
        raise HTTPException(status_code=422, detail="user_message is required")

    session_state = get_session(session_id)

    language_mode = str(
        payload.get("language_mode")
        or (session_state.language_mode if session_state else "en")
    )

    company = str(payload.get("company") or (session_state.company if session_state else "rakuten"))

    try:
        duration_mins = int(
            payload.get("duration_mins")
            if payload.get("duration_mins") is not None
            else (session_state.duration_mins if session_state else 15)
        )
    except (TypeError, ValueError):
        duration_mins = 15

    is_demo_mode = bool(payload.get("is_demo_mode", False))

    conversation_history: List[Any]
    if isinstance(payload.get("conversation_history"), list):
        conversation_history = payload.get("conversation_history", [])
    elif session_state and isinstance(session_state.conversation_history, list):
        conversation_history = list(session_state.conversation_history)
    else:
        conversation_history = []

    result = run_interview_turn(
        session_id=session_id,
        company=company,
        language_mode=language_mode,
        duration_mins=duration_mins,
        is_demo_mode=is_demo_mode,
        user_message=user_message,
        conversation_history=conversation_history,
    )

    # Keep session state synchronized for clients that do not pass conversation_history.
    if session_state and isinstance(session_state.conversation_history, list):
        session_state.conversation_history = conversation_history

    return result