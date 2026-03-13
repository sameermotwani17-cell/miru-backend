import logging
from typing import Any, Dict

from fastapi import APIRouter, HTTPException

from services.analytics_engine import get_radar_chart_data
from store.interview_results import get_interview_results
from store.interview_turns import get_session_turns


LOGGER = logging.getLogger(__name__)

interview_results_router = APIRouter(prefix="/api/interview", tags=["interview-results"])


def _build_feedback_package(session_id: str) -> Dict[str, Any]:
    cached_results = get_interview_results(session_id)
    if cached_results:
        LOGGER.info("[CACHE] Using stored results")
        return cached_results

    raise HTTPException(status_code=404, detail="Interview results not ready")


@interview_results_router.get("/{session_id}/radar")
def get_radar(session_id: str) -> Dict[str, float]:
    LOGGER.info("[API] Fetch radar chart")
    feedback_package = _build_feedback_package(session_id)
    overall_scores = feedback_package.get("overall_scores", {})
    return get_radar_chart_data(overall_scores)


@interview_results_router.get("/{session_id}/report")
def get_report(session_id: str) -> Dict[str, Any]:
    LOGGER.info("[API] Fetch final report")
    feedback_package = _build_feedback_package(session_id)
    final_report = feedback_package.get("final_report", {})
    if not isinstance(final_report, dict):
        return {}
    return final_report


@interview_results_router.get("/{session_id}/feedback")
def get_feedback(session_id: str) -> Dict[str, Any]:
    feedback_package = _build_feedback_package(session_id)
    turn_feedback = feedback_package.get("turn_feedback", [])
    if not isinstance(turn_feedback, list):
        turn_feedback = []
    return {"turn_feedback": turn_feedback}


@interview_results_router.get("/{session_id}/transcript")
def get_transcript(session_id: str) -> Dict[str, Any]:
    turns = get_session_turns(session_id)
    if not turns:
        raise HTTPException(status_code=404, detail="Interview transcript not found")

    transcript_turns = [
        {
            "question_id": str(turn.get("question_id", "")),
            "question": str(turn.get("question_prompt", "")),
            "answer": str(turn.get("answer") or turn.get("user_answer") or ""),
        }
        for turn in turns
    ]

    return {"turns": transcript_turns}


@interview_results_router.get("/{session_id}/results")
def get_results(session_id: str) -> Dict[str, Any]:
    LOGGER.info("[API] Fetch interview results")
    return _build_feedback_package(session_id)
