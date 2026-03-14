import logging
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Query

from services.analytics_engine import get_radar_chart_data
from store.interview_results import get_interview_results
from store.interview_turns import get_session_turns


LOGGER = logging.getLogger(__name__)

interview_results_router = APIRouter(prefix="/api/interview", tags=["interview-results"])

_SCORE_KEYS = ("communication", "clarity", "cultural_fit", "problem_solving")


def _build_feedback_package(session_id: str) -> Dict[str, Any]:
    cached_results = get_interview_results(session_id)
    if cached_results:
        return cached_results
    raise HTTPException(status_code=404, detail="Interview results not ready")


def _build_results_response(session_id: str) -> Dict[str, Any]:
    feedback_package = _build_feedback_package(session_id)
    response_payload: Dict[str, Any] = dict(feedback_package)

    turns = get_session_turns(session_id)
    transcript_turns = [
        {
            "question_id": str(t.get("question_id", "")),
            "question": str(t.get("question_prompt", "")),
            "answer": str(t.get("answer") or t.get("user_answer") or ""),
        }
        for t in turns
    ]

    response_payload.setdefault("session_id", session_id)
    response_payload.setdefault("turns", transcript_turns)
    response_payload.setdefault("transcript", transcript_turns)

    # Aggregate radar scores from stored turns
    overall_scores = feedback_package.get("overall_scores", {})
    if not isinstance(overall_scores, dict):
        overall_scores = {}

    # Build radar_scores from actual per-turn data if not already stored
    if not overall_scores and turns:
        buckets: Dict[str, list] = {k: [] for k in _SCORE_KEYS}
        for t in turns:
            s = t.get("scores", {})
            for k in _SCORE_KEYS:
                v = s.get(k)
                if isinstance(v, (int, float)):
                    buckets[k].append(float(v))
        overall_scores = {
            k: round(sum(v) / len(v), 2) if v else 0.0
            for k, v in buckets.items()
        }

    response_payload["radar_scores"] = overall_scores

    # Build hiring signal
    avg = sum(overall_scores.values()) / len(overall_scores) if overall_scores else 0.0
    if avg >= 7.5:
        hiring_signal = "Strong Hire"
    elif avg >= 6.0:
        hiring_signal = "Hire"
    elif avg >= 4.5:
        hiring_signal = "Borderline"
    else:
        hiring_signal = "No Hire"

    response_payload["hiring_signal"] = hiring_signal

    # Top-level feedback from final_report
    final_report = feedback_package.get("final_report", {})
    if isinstance(final_report, dict):
        response_payload.setdefault("feedback", {
            "summary": final_report.get("overall_summary", ""),
            "strengths": final_report.get("strengths", []),
            "improvement_areas": final_report.get("improvement_areas", []),
            "recommended_focus": final_report.get("recommended_focus", ""),
        })

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
    feedback_package = _build_feedback_package(session_id)
    overall_scores = feedback_package.get("overall_scores", {})
    return get_radar_chart_data(overall_scores)


@interview_results_router.get("/{session_id}/report")
def get_report(session_id: str) -> Dict[str, Any]:
    feedback_package = _build_feedback_package(session_id)
    final_report = feedback_package.get("final_report", {})
    return final_report if isinstance(final_report, dict) else {}


@interview_results_router.get("/{session_id}/feedback")
def get_feedback(session_id: str) -> Dict[str, Any]:
    feedback_package = _build_feedback_package(session_id)
    turn_feedback = feedback_package.get("turn_feedback", [])
    return {"turn_feedback": turn_feedback if isinstance(turn_feedback, list) else []}


@interview_results_router.get("/{session_id}/transcript")
def get_transcript(session_id: str) -> Dict[str, Any]:
    turns = get_session_turns(session_id)
    if not turns:
        raise HTTPException(status_code=404, detail="Interview transcript not found")
    transcript_turns = [
        {
            "question_id": str(t.get("question_id", "")),
            "question": str(t.get("question_prompt", "")),
            "answer": str(t.get("answer") or t.get("user_answer") or ""),
        }
        for t in turns
    ]
    return {"turns": transcript_turns}
