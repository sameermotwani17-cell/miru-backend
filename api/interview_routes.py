from typing import Any, Dict

from fastapi import APIRouter, HTTPException

from services.interview_engine import run_interview_turn
from store.sessions import get_session


interview_router = APIRouter(prefix="/api", tags=["interview"])


@interview_router.post("/interview/turn")
async def interview_turn(payload: Dict[str, Any]) -> Dict[str, Any]:
    session_id = str(payload.get("session_id") or "").strip()
    if not session_id:
        raise HTTPException(status_code=422, detail="session_id is required")

    force_complete = bool(payload.get("force_complete", False))

    # Accept user_answer or user_message
    user_message = payload.get("user_answer") or payload.get("user_message") or payload.get("answer")
    user_message = str(user_message or "").strip()
    if not user_message and not force_complete:
        raise HTTPException(status_code=422, detail="user_answer is required")

    session_state = get_session(session_id)

    language_mode = str(
        payload.get("language")
        or payload.get("language_mode")
        or (session_state.language_mode if session_state else "en")
    )

    company = str(
        payload.get("company")
        or (session_state.company if session_state else "rakuten")
    )

    try:
        duration_mins = int(
            payload.get("duration_mins")
            if payload.get("duration_mins") is not None
            else (session_state.duration_mins if session_state else 15)
        )
    except (TypeError, ValueError):
        duration_mins = 15

    max_questions = payload.get("max_questions")
    if max_questions is not None:
        try:
            max_questions = int(max_questions)
        except (TypeError, ValueError):
            max_questions = None

    is_demo_mode = bool(payload.get("is_demo_mode", False))

    # CV context — from session only (never trust client-sent CV)
    cv_context: str | None = session_state.cv_context if session_state else None
    if cv_context:
        cv_context = str(cv_context).strip() or None

    # Candidate identity and session timer — sourced from session state only
    user_name = session_state.user_name if session_state else ""
    target_role = session_state.target_role if session_state else ""
    timer_end_epoch: int | None = session_state.timer_end_epoch if session_state else None

    # transcript_history and conversation_history from the client are intentionally ignored.
    # The backend reconstructs transcript state from stored turns (single source of truth).

    result = run_interview_turn(
        session_id=session_id,
        company=company,
        language_mode=language_mode,
        duration_mins=duration_mins,
        is_demo_mode=is_demo_mode,
        user_message=user_message,
        cv_context=cv_context,
        user_name=user_name,
        target_role=target_role,
        timer_end_epoch=timer_end_epoch,
        max_questions=max_questions,
        force_complete=force_complete,
    )

    voice_mode = bool(payload.get("voice_mode", False))
    if not voice_mode:
        result.pop("voice_audio", None)

    # Guarantee tts_text is always present for ElevenLabs (speech generated on frontend)
    # Include next_question so the candidate hears both the acknowledgment and the next question.
    interviewer_response = str(result.get("interviewer_response") or "")
    next_q = str(result.get("next_question") or "")
    tts_parts = [p for p in [interviewer_response, next_q] if p]
    result["tts_text"] = " ".join(tts_parts)
    print("TTS text:", result["tts_text"])

    return result
