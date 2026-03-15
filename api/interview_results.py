import logging
from typing import Any, Dict, List

from fastapi import APIRouter, Query

from services.analytics_engine import get_radar_chart_data
from services.score_dimensions import DEFAULT_SCORES, SCORE_DIMENSIONS
from store.interview_results import get_interview_results
from store.interview_turns import get_session_turns


LOGGER = logging.getLogger(__name__)

interview_results_router = APIRouter(prefix="/api/interview", tags=["interview-results"])


def _aggregate_scores_from_turns(turns: List[Dict[str, Any]]) -> Dict[str, float]:
    buckets: Dict[str, List[float]] = {k: [] for k in SCORE_DIMENSIONS}
    for t in turns:
        s = t.get("scores", {})
        for k in SCORE_DIMENSIONS:
            v = s.get(k)
            if isinstance(v, (int, float)):
                buckets[k].append(float(v))
    return {
        k: round(sum(v) / len(v), 2) if v else 5.0
        for k, v in buckets.items()
    }


def _build_transcript(turns: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """Reconstruct role-based conversation transcript from stored turns."""
    transcript: List[Dict[str, str]] = []
    for turn in turns:
        response = turn.get("interviewer_response", "")
        question = turn.get("question_prompt", "")
        answer = turn.get("user_answer", "") or turn.get("answer", "")

        if response:
            transcript.append({"role": "assistant", "content": response})
        if question:
            transcript.append({"role": "assistant", "content": question})
        if answer:
            transcript.append({"role": "user", "content": answer})

    return transcript


def _format_list_as_string(value: Any) -> str:
    if isinstance(value, list):
        return "\n".join(f"- {item}" for item in value if item)
    return str(value or "")


def normalize_scores(scores: Dict[str, Any]) -> Dict[str, float]:
    return {
        dim: float(scores.get(dim, DEFAULT_SCORES[dim]))
        for dim in SCORE_DIMENSIONS
    }


def _compute_hiring_signal(scores: Dict[str, float]) -> str:
    avg = sum(scores.get(d, 0) for d in SCORE_DIMENSIONS) / len(SCORE_DIMENSIONS)
    if avg >= 7.5:
        return "Strong Hire"
    if avg >= 6:
        return "Hire"
    if avg >= 4.5:
        return "Borderline"
    return "No Hire"


def _build_results_response(session_id: str) -> Dict[str, Any]:
    turns = get_session_turns(session_id)
    cached_results = get_interview_results(session_id) or {}

    # Aggregate scores from stored turn data
    overall_scores = _aggregate_scores_from_turns(turns)

    # Override with debrief scores if available (more accurate)
    if isinstance(cached_results.get("overall_scores"), dict):
        debrief_scores = cached_results["overall_scores"]
        if all(k in debrief_scores for k in SCORE_DIMENSIONS):
            overall_scores = {k: float(debrief_scores[k]) for k in SCORE_DIMENSIONS}

    radar_scores = normalize_scores(overall_scores)

    # Build role-based transcript
    transcript = cached_results.get("transcript", _build_transcript(turns))
    if not isinstance(transcript, list):
        transcript = []

    # Build feedback block
    feedback: Dict[str, Any] = {
        "strengths": "",
        "areas_for_improvement": "",
        "summary": "",
    }
    final_report = cached_results.get("final_report", {})
    if isinstance(final_report, dict):
        feedback["summary"] = str(final_report.get("overall_summary", ""))
        feedback["strengths"] = _format_list_as_string(final_report.get("strengths", []))
        feedback["areas_for_improvement"] = _format_list_as_string(
            final_report.get("improvement_areas", [])
        )

    if cached_results.get("hiring_signal"):
        hiring_signal = str(cached_results.get("hiring_signal"))
    elif cached_results.get("status") == "processing" or (not turns and not cached_results):
        hiring_signal = "Pending"
    else:
        hiring_signal = _compute_hiring_signal(radar_scores)
    turn_feedback = cached_results.get("turn_feedback", [])
    if not isinstance(turn_feedback, list):
        turn_feedback = []

    response_payload: Dict[str, Any] = {
        "session_id": session_id,
        "scores": radar_scores,
        "transcript": transcript,
        "feedback": feedback,
        "hiring_signal": hiring_signal,
        "radar_scores": radar_scores,
        "turn_feedback": turn_feedback,
    }

    return response_payload


# ── canonical endpoint: GET /api/interview/results?session_id=... ──────────
@interview_results_router.get("/results")
def get_results_by_query(session_id: str = Query(..., description="Session ID")) -> Dict[str, Any]:
    LOGGER.info("[API] Fetch interview results session_id=%s", session_id)
    return _build_results_response(session_id)


# ── path-param aliases for backward compatibility ──────────────────────────
@interview_results_router.get("/{session_id}/results")
def get_results(session_id: str) -> Dict[str, Any]:
    return _build_results_response(session_id)


@interview_results_router.get("/results/{session_id}")
def get_results_compat(session_id: str) -> Dict[str, Any]:
    return _build_results_response(session_id)


@interview_results_router.get("/{session_id}/radar")
def get_radar(session_id: str) -> Dict[str, float]:
    turns = get_session_turns(session_id)
    cached_results = get_interview_results(session_id)
    overall_scores = _aggregate_scores_from_turns(turns)
    if cached_results and isinstance(cached_results.get("overall_scores"), dict):
        overall_scores = {k: float(v) for k, v in cached_results["overall_scores"].items()}
    return get_radar_chart_data(overall_scores)


@interview_results_router.get("/{session_id}/report")
def get_report(session_id: str) -> Dict[str, Any]:
    cached_results = get_interview_results(session_id)
    if not cached_results:
        return {"error": "Session not found"}
    final_report = cached_results.get("final_report", {})
    return final_report if isinstance(final_report, dict) else {}


@interview_results_router.get("/{session_id}/feedback")
def get_feedback(session_id: str) -> Dict[str, Any]:
    cached_results = get_interview_results(session_id)
    if not cached_results:
        return {"turn_feedback": []}
    turn_feedback = cached_results.get("turn_feedback", [])
    return {"turn_feedback": turn_feedback if isinstance(turn_feedback, list) else []}


@interview_results_router.get("/{session_id}/transcript")
def get_transcript(session_id: str) -> Dict[str, Any]:
    turns = get_session_turns(session_id)
    if not turns:
        return {"error": "Session not found"}
    return {"transcript": _build_transcript(turns)}


@interview_results_router.get("/{session_id}/debrief-status")
def get_debrief_status(session_id: str) -> Dict[str, str]:
    cached_results = get_interview_results(session_id)
    if isinstance(cached_results, dict):
        turn_feedback = cached_results.get("turn_feedback", [])
        if isinstance(turn_feedback, list) and len(turn_feedback) > 0:
            return {"status": "ready"}
    return {"status": "pending"}
