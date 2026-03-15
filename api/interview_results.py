import logging
from typing import Any, Dict, List

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

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


def _build_transcript(turns: List[Dict[str, Any]], turn_feedback: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Build frontend transcript rows with question/answer and coaching fields."""
    feedback_by_qid: Dict[str, Dict[str, Any]] = {}
    for item in turn_feedback:
        if not isinstance(item, dict):
            continue
        qid = str(item.get("question_id", "")).strip()
        if qid:
            feedback_by_qid[qid] = item

    transcript: List[Dict[str, Any]] = []
    for turn in turns:
        qid = str(turn.get("question_id", "")).strip()
        coaching = feedback_by_qid.get(qid, {})
        question = str(turn.get("question") or turn.get("question_prompt") or "")
        answer = str(turn.get("user_answer") or turn.get("answer") or "")
        transcript.append({
            "question": question,
            "answer": answer,
            "score": float(turn.get("score", 5.0) or 5.0),
            "feedback": str(turn.get("feedback") or coaching.get("feedback") or ""),
            "better_example": str(turn.get("better_example") or coaching.get("rewrite_example") or ""),
        })

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
    cached_results = get_interview_results(session_id)
    if not isinstance(cached_results, dict):
        raise KeyError("results_not_ready")

    if cached_results.get("status") == "processing":
        raise KeyError("results_not_ready")

    if not cached_results:
        raise KeyError("results_not_ready")

    overall_scores = normalize_scores(cached_results.get("overall_scores", {}))
    radar_scores = normalize_scores(cached_results.get("radar_scores", overall_scores))

    turn_feedback = cached_results.get("turn_feedback", [])
    if not isinstance(turn_feedback, list):
        turn_feedback = []

    transcript = _build_transcript(turns, turn_feedback)

    feedback: Dict[str, Any] = {
        "strengths": "",
        "areas_for_improvement": "",
        "summary": "",
    }

    if isinstance(cached_results.get("feedback"), dict):
        cached_feedback = cached_results["feedback"]
        feedback["summary"] = str(cached_feedback.get("summary", ""))
        feedback["strengths"] = _format_list_as_string(cached_feedback.get("strengths", []))
        feedback["areas_for_improvement"] = _format_list_as_string(
            cached_feedback.get("areas_for_improvement", [])
        )

    final_report = cached_results.get("final_report", {})
    if isinstance(final_report, dict):
        if not feedback["summary"]:
            feedback["summary"] = str(final_report.get("overall_summary", ""))
        if not feedback["strengths"]:
            feedback["strengths"] = _format_list_as_string(final_report.get("strengths", []))
        if not feedback["areas_for_improvement"]:
            feedback["areas_for_improvement"] = _format_list_as_string(
                final_report.get("improvement_areas", [])
            )

    hiring_signal = str(
        cached_results.get("hiring_signal")
        or _compute_hiring_signal(radar_scores)
    )

    response_payload: Dict[str, Any] = {
        "session_id": session_id,
        "scores": radar_scores,
        "transcript": transcript,
        "feedback": feedback,
        "final_report": final_report if isinstance(final_report, dict) else {},
        "hiring_signal": hiring_signal,
        "radar_scores": radar_scores,
        "turn_feedback": turn_feedback,
    }

    return response_payload


# ── canonical endpoint: GET /api/interview/results?session_id=... ──────────
@interview_results_router.get("/results")
def get_results_by_query(session_id: str = Query(..., description="Session ID")) -> Dict[str, Any]:
    LOGGER.info("[API] Fetch interview results session_id=%s", session_id)
    try:
        return _build_results_response(session_id)
    except KeyError:
        return JSONResponse(status_code=404, content={"status": "results_not_ready"})


# ── path-param aliases for backward compatibility ──────────────────────────
@interview_results_router.get("/{session_id}/results")
def get_results(session_id: str) -> Dict[str, Any]:
    try:
        return _build_results_response(session_id)
    except KeyError:
        return JSONResponse(status_code=404, content={"status": "results_not_ready"})


@interview_results_router.get("/results/{session_id}")
def get_results_compat(session_id: str) -> Dict[str, Any]:
    try:
        return _build_results_response(session_id)
    except KeyError:
        return JSONResponse(status_code=404, content={"status": "results_not_ready"})


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
    return {"transcript": _build_transcript(turns, [])}


@interview_results_router.get("/{session_id}/debrief-status")
def get_debrief_status(session_id: str) -> Dict[str, str]:
    cached_results = get_interview_results(session_id)
    if isinstance(cached_results, dict):
        if cached_results.get("status") == "processing":
            return {"status": "generating"}
        turn_feedback = cached_results.get("turn_feedback", [])
        if isinstance(turn_feedback, list) and len(turn_feedback) > 0:
            return {"status": "ready"}
        if cached_results.get("status") == "ready":
            return {"status": "ready"}
    return {"status": "generating"}
