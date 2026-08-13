import json
import logging
import os
from collections import defaultdict
from typing import Any, Dict, List

from openai import OpenAI

from services.score_dimensions import SCORE_DIMENSIONS, DEFAULT_SCORES


LOGGER = logging.getLogger(__name__)

_DEFAULT_EVALUATION: Dict[str, Any] = {
    "wa_teamwork": 5,
    "loyalty_commitment": 5,
    "humility": 5,
    "kaizen_growth": 5,
    "cultural_fit": 5,
    "notes": "Fallback scoring used due to evaluation parse failure.",
}

_MODEL_NAME = "gpt-4o-mini"
def _api_key() -> str | None:
    """Read the key per call so a late-bound env var is still picked up."""
    return os.getenv("OPENAI_API_KEY")


def _build_user_prompt(question_text: str, question_category: str, answer: str) -> str:
    return (
        "Question asked:\n"
        f"{question_text or question_category}\n\n"
        "Candidate answer:\n"
        f"{answer}"
    )


def _coerce_score(value: Any) -> int:
    try:
        score = int(value)
    except (TypeError, ValueError):
        score = 5
    return max(1, min(10, score))


def _normalize_evaluation(payload: Dict[str, Any]) -> Dict[str, Any]:
    normalized = {
        dim: _coerce_score(payload.get(dim))
        for dim in SCORE_DIMENSIONS
    }
    notes = payload.get("notes", _DEFAULT_EVALUATION["notes"])
    normalized["notes"] = str(notes)
    return normalized


def evaluate_answer(
    question_id: str,
    question_category: str,
    question_text: str,
    answer: str,
) -> Dict[str, Any]:
    LOGGER.debug("[DEBRIEF] Evaluating answer question_id=%s category=%s", question_id, question_category)

    if not _api_key():
        LOGGER.warning("[DEBRIEF] OPENAI_API_KEY is missing; using fallback evaluation")
        return dict(_DEFAULT_EVALUATION)

    client = OpenAI(api_key=_api_key())

    system_prompt = (
        "You are an expert evaluator scoring a job candidate's answer for a Japanese company HR interview.\n"
        "Score the answer on five Japanese HR dimensions:\n\n"
        "1. wa_teamwork — Does the answer prioritise group harmony? Avoid dominant 'I' framing.\n"
        "   High score = team-first language, references to group outcomes.\n"
        "   Low score = individualistic framing, 'I achieved', 'I decided alone'.\n\n"
        "2. loyalty_commitment — Does the answer signal long-term intent?\n"
        "   High score = language of commitment, contributing to company mission long-term.\n"
        "   Low score = job-hopping signals, 'stepping stone', 'looking for new challenges'.\n\n"
        "3. humility — Is self-presentation appropriately humble for Japanese context?\n"
        "   High score = achievements framed with credit to team/circumstances, correct modesty.\n"
        "   Low score = 'I am the best', 'I am confident I can', over-selling.\n\n"
        "4. kaizen_growth — Is growth framed as improvement within the company's framework?\n"
        "   High score = 'I want to develop within the company's methods', continuous improvement.\n"
        "   Low score = 'I want to start my own company', 'expand my personal skills'.\n\n"
        "5. cultural_fit — Does the candidate show awareness of Japanese business culture?\n"
        "   High score = references to company values, keigo-aware phrasing, process respect.\n"
        "   Low score = casual language, ignoring hierarchy, asking about work-life balance too early.\n\n"
        "Each score must be 1 to 10. Be conservative — most foreign candidates score 4-6.\n"
        "A score of 8+ requires explicit, specific evidence. A score of 1-2 means the answer "
        "actively damaged that dimension.\n"
        "Return ONLY JSON."
    )

    try:
        response = client.chat.completions.create(
            model=_MODEL_NAME,
            temperature=0.2,
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": _build_user_prompt(
                        question_text=question_text,
                        question_category=question_category,
                        answer=answer,
                    ),
                },
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "miru_debrief_evaluation",
                    "strict": True,
                    "schema": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "wa_teamwork": {"type": "integer", "minimum": 1, "maximum": 10},
                            "loyalty_commitment": {"type": "integer", "minimum": 1, "maximum": 10},
                            "humility": {"type": "integer", "minimum": 1, "maximum": 10},
                            "kaizen_growth": {"type": "integer", "minimum": 1, "maximum": 10},
                            "cultural_fit": {"type": "integer", "minimum": 1, "maximum": 10},
                            "notes": {"type": "string"},
                        },
                        "required": [
                            "wa_teamwork",
                            "loyalty_commitment",
                            "humility",
                            "kaizen_growth",
                            "cultural_fit",
                            "notes",
                        ],
                    },
                },
            },
        )

        raw_text = response.choices[0].message.content or "{}"
        parsed = json.loads(raw_text)
        return _normalize_evaluation(parsed)
    except Exception as exc:
        LOGGER.warning("[DEBRIEF] Evaluation failed; using fallback. error=%s", exc)
        return dict(_DEFAULT_EVALUATION)


def _evaluate_turns(turns: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Evaluate a list of interview turns and return raw debrief scores."""
    dimension_buckets: Dict[str, List[float]] = defaultdict(list)
    turn_evaluations: List[Dict[str, Any]] = []

    for turn in turns:
        question_id = str(turn.get("question_id", ""))
        question_category = str(turn.get("question_category", ""))
        question_text = str(turn.get("question") or turn.get("question_prompt", ""))
        answer = str(turn.get("answer") or turn.get("user_answer") or "")

        evaluation = evaluate_answer(
            question_id=question_id,
            question_category=question_category,
            question_text=question_text,
            answer=answer,
        )

        turn_evaluations.append(
            {
                "question_id": question_id,
                "question_category": question_category,
                "answer": answer,
                "evaluation": evaluation,
            }
        )

        for dimension in SCORE_DIMENSIONS:
            dimension_buckets[dimension].append(float(evaluation[dimension]))

    overall_scores = {
        dimension: round(sum(scores) / len(scores), 2) if scores else None
        for dimension, scores in dimension_buckets.items()
    }

    for dimension in SCORE_DIMENSIONS:
        overall_scores.setdefault(dimension, None)

    return {
        "overall_scores": overall_scores,
        "turn_evaluations": turn_evaluations,
    }


def _calculate_hiring_signal(scores: Dict[str, Any]) -> str:
    avg = sum(float(scores.get(d, 0)) for d in SCORE_DIMENSIONS) / len(SCORE_DIMENSIONS)
    if avg >= 7.5:
        return "Strong Hire"
    if avg >= 6:
        return "Hire"
    if avg >= 4.5:
        return "Borderline"
    return "No Hire"


def generate_interview_debrief(session_id: str) -> None:
    """
    Generate a full interview debrief for a session and persist the results.

    Fetches stored turns, evaluates them, builds a feedback package, and
    calls save_interview_results so the /api/interview/results endpoint can
    return them. Safe to call multiple times — skips if results already ready.
    """
    # Local imports to avoid circular dependencies at module load time.
    from store.interview_turns import get_session_turns
    from store.interview_results import (
        get_interview_results,
        save_interview_results,
        set_interview_results_processing,
    )
    from services.feedback_engine import generate_full_feedback_package

    existing = get_interview_results(session_id)
    if existing is not None and existing.get("status") == "ready":
        LOGGER.debug("[DEBRIEF] Results already ready for session %s, skipping.", session_id)
        return

    set_interview_results_processing(session_id)
    turns = get_session_turns(session_id)

    # Build transcript text from stored turns for deterministic, context-aware debrief.
    transcript_lines = []
    for t in turns:
        q = t.get("question_prompt", "") or t.get("question", "")
        a = t.get("user_answer", "") or t.get("answer", "")
        if q and a:
            transcript_lines.append(f"Interviewer: {q}")
            transcript_lines.append(f"Candidate: {a}")

    LOGGER.info("Debrief transcript lines: %d", len(transcript_lines))

    if len(transcript_lines) < 2:
        LOGGER.warning("[DEBRIEF] Transcript empty for session %s – using fallback evaluation.", session_id)

    transcript_text = "\n".join(transcript_lines)

    try:
        debrief = _evaluate_turns(turns)
    except Exception as exc:
        LOGGER.error("[DEBRIEF] Turn evaluation failed for session %s: %s", session_id, exc)
        debrief = {
            "overall_scores": dict(DEFAULT_SCORES),
            "turn_evaluations": [],
        }

    try:
        feedback_package = generate_full_feedback_package(debrief, transcript_text=transcript_text)
    except Exception as exc:
        LOGGER.warning("[DEBRIEF] Feedback package failed for session %s: %s", session_id, exc)
        feedback_package = {
            "overall_scores": dict(DEFAULT_SCORES),
            "turn_feedback": [],
            "transcript": [],
            "hiring_signal": "Evaluation incomplete",
            "final_report": {
                "overall_summary": "Debrief generation fallback applied.",
                "strengths": [],
                "improvement_areas": [],
                "recommended_focus": "",
                "overall_scores": dict(DEFAULT_SCORES),
            },
        }

    normalized_scores = {
        dim: float(feedback_package.get("overall_scores", {}).get(dim, DEFAULT_SCORES[dim]))
        for dim in SCORE_DIMENSIONS
    }
    feedback_package["overall_scores"] = normalized_scores
    feedback_package.setdefault("turn_feedback", [])
    feedback_package.setdefault("hiring_signal", _calculate_hiring_signal(normalized_scores))

    final_report = feedback_package.get("final_report", {})
    if not isinstance(final_report, dict):
        final_report = {}

    turn_feedback = feedback_package.get("turn_feedback", [])
    feedback_by_qid: Dict[str, Dict[str, Any]] = {}
    for item in turn_feedback:
        if isinstance(item, dict):
            qid = str(item.get("question_id", "")).strip()
            if qid:
                feedback_by_qid[qid] = item

    transcript = []
    for turn in turns:
        qid = str(turn.get("question_id", "")).strip()
        coaching = feedback_by_qid.get(qid, {})
        transcript.append({
            "question": str(turn.get("question") or turn.get("question_prompt") or ""),
            "answer": str(turn.get("user_answer") or turn.get("answer") or ""),
            "score": float(turn.get("score", 5.0) or 5.0),
            "feedback": str(turn.get("feedback") or coaching.get("feedback") or ""),
            "better_example": str(turn.get("better_example") or coaching.get("rewrite_example") or ""),
        })

    results = {
        "status": "ready",
        "session_id": session_id,
        "overall_scores": normalized_scores,
        "scores": normalized_scores,
        "radar_scores": normalized_scores,
        "transcript": transcript,
        "turn_feedback": turn_feedback,
        "hiring_signal": feedback_package.get("hiring_signal", _calculate_hiring_signal(normalized_scores)),
        "final_report": final_report,
        "feedback": {
            "summary": str(final_report.get("overall_summary", "")),
            "strengths": final_report.get("strengths", []),
            "areas_for_improvement": final_report.get("improvement_areas", []),
        },
    }

    save_interview_results(session_id, results)
    LOGGER.info("[DEBRIEF] Results saved for session %s", session_id)
    LOGGER.info("Debrief generated for session %s", session_id)
