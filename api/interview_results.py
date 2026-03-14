import logging
from typing import Any, Dict

from fastapi import APIRouter, HTTPException

from services.analytics_engine import get_radar_chart_data
from store.interview_results import get_interview_results
from store.interview_turns import get_session_turns


LOGGER = logging.getLogger(__name__)

interview_results_router = APIRouter(prefix="/api/interview", tags=["interview-results"])


# UPDATE: expose scoring matrix fields in interview results API
#
# The scoring engine now returns a structured scoring payload with:
# - dimension_scores
# - matrix_scores
# - overall
# - cultural_fit_score
#
# Update the interview results endpoint so these fields are included
# in the JSON response returned by:
#
# GET /api/interview/results/{session_id}
#
# Implementation requirements:
# 1. Retrieve the scoring result from the stored interview results object.
# 2. Add the following fields to the API response payload:
#
#   dimension_scores
#   matrix_scores
#   overall
#   cultural_fit_score
#
# 3. Preserve existing fields such as transcript, turns, feedback, etc.
# 4. Maintain backward compatibility (do not remove existing keys).
#
# Desired response structure example:
#
# {
#   "session_id": "...",
#   "transcript": [...],
#   "turns": [...],
#   "dimension_scores": {...},
#   "matrix_scores": {...},
#   "overall": 7.4,
#   "cultural_fit_score": 74.0
# }
#
# The goal is to expose the matrix scoring so the frontend can render
# radar charts and the final cultural fit score.


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
    feedback_package = _build_feedback_package(session_id)
    response_payload: Dict[str, Any] = dict(feedback_package)

    # Keep transcript-like data available from the canonical turn store.
    turns = get_session_turns(session_id)
    transcript_turns = [
        {
            "question_id": str(turn.get("question_id", "")),
            "question": str(turn.get("question_prompt", "")),
            "answer": str(turn.get("answer") or turn.get("user_answer") or ""),
        }
        for turn in turns
    ]

    response_payload.setdefault("session_id", session_id)
    response_payload.setdefault("turns", transcript_turns)
    response_payload.setdefault("transcript", transcript_turns)

    # Prefer matrix payload fields at top-level when already persisted.
    dimension_scores = response_payload.get("dimension_scores")
    matrix_scores = response_payload.get("matrix_scores")
    overall = response_payload.get("overall")
    cultural_fit_score = response_payload.get("cultural_fit_score")

    # Backward-compatible fallbacks from existing structures.
    overall_scores = feedback_package.get("overall_scores", {})
    if not isinstance(overall_scores, dict):
        overall_scores = {}

    final_report = feedback_package.get("final_report", {})
    if not isinstance(final_report, dict):
        final_report = {}

    if not isinstance(dimension_scores, dict):
        candidate_dimension_scores = final_report.get("dimension_scores")
        if isinstance(candidate_dimension_scores, dict):
            dimension_scores = candidate_dimension_scores
        else:
            dimension_scores = {}

    if not isinstance(matrix_scores, dict):
        candidate_matrix_scores = final_report.get("matrix_scores")
        if isinstance(candidate_matrix_scores, dict):
            matrix_scores = candidate_matrix_scores
        else:
            matrix_scores = {}

    if not isinstance(overall, (int, float)):
        candidate_overall = final_report.get("overall")
        if isinstance(candidate_overall, (int, float)):
            overall = float(candidate_overall)
        elif isinstance(matrix_scores, dict) and matrix_scores:
            numeric_values = [
                float(value)
                for value in matrix_scores.values()
                if isinstance(value, (int, float))
            ]
            overall = (sum(numeric_values) / len(numeric_values)) if numeric_values else 0.0
        elif isinstance(overall_scores.get("cultural_fit"), (int, float)):
            overall = float(overall_scores.get("cultural_fit", 0.0))
        else:
            overall = 0.0

    if not isinstance(cultural_fit_score, (int, float)):
        candidate_cultural_fit = final_report.get("cultural_fit_score")
        if isinstance(candidate_cultural_fit, (int, float)):
            cultural_fit_score = float(candidate_cultural_fit)
        else:
            cultural_fit_score = round(float(overall) * 10.0, 2)

    response_payload["dimension_scores"] = dict(dimension_scores)
    response_payload["matrix_scores"] = dict(matrix_scores)
    response_payload["overall"] = round(float(overall), 2)
    response_payload["cultural_fit_score"] = round(float(cultural_fit_score), 2)

    return response_payload


@interview_results_router.get("/results/{session_id}")
def get_results_compat(session_id: str) -> Dict[str, Any]:
    """Backward-compatible alias for clients using /api/interview/results/{session_id}."""
    return get_results(session_id)
