import json
import logging
import os
from collections import defaultdict
from typing import Any, Dict, List

from openai import OpenAI


LOGGER = logging.getLogger(__name__)

DEBUG_DEBRIEF = True

EVALUATION_DIMENSIONS = [
    "wa_teamwork",
    "loyalty_commitment",
    "humility",
    "kaizen_growth",
    "cultural_fit",
]

_DEFAULT_EVALUATION: Dict[str, Any] = {
    "wa_teamwork": 5,
    "loyalty_commitment": 5,
    "humility": 5,
    "kaizen_growth": 5,
    "cultural_fit": 5,
    "notes": "Fallback scoring used due to evaluation parse failure.",
}

_MODEL_NAME = "gpt-4o-mini"
_API_KEY = os.getenv("OPENAI_API_KEY")


def _build_user_prompt(question_category: str, answer: str) -> str:
    return (
        "Question category:\n"
        f"{question_category}\n\n"
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
        for dim in EVALUATION_DIMENSIONS
    }
    notes = payload.get("notes", _DEFAULT_EVALUATION["notes"])
    normalized["notes"] = str(notes)
    return normalized


def evaluate_answer(question_id: str, question_category: str, answer: str) -> Dict[str, Any]:
    LOGGER.debug("[DEBRIEF] Evaluating answer question_id=%s category=%s", question_id, question_category)
    if DEBUG_DEBRIEF:
        print("[DEBRIEF] Evaluating answer:", question_id)

    if not _API_KEY:
        LOGGER.warning("[DEBRIEF] OPENAI_API_KEY is missing; using fallback evaluation")
        return dict(_DEFAULT_EVALUATION)

    client = OpenAI(api_key=_API_KEY)

    system_prompt = (
        "You are a Japanese HR interviewer evaluating a job candidate.\n"
        "Score the candidate's answer according to Japanese hiring culture.\n\n"
        "Evaluation categories:\n"
        "1. Wa (teamwork harmony)\n"
        "2. Loyalty (long-term commitment)\n"
        "3. Humility\n"
        "4. Kaizen (growth mindset)\n"
        "5. Cultural Fit\n\n"
        "Each score must be from 1 to 10.\n"
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
                    "content": _build_user_prompt(question_category=question_category, answer=answer),
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
        normalized = _normalize_evaluation(parsed)
    except Exception as exc:
        LOGGER.warning("[DEBRIEF] Evaluation failed; using fallback. error=%s", exc)
        normalized = dict(_DEFAULT_EVALUATION)

    LOGGER.debug(
        "[DEBRIEF] Scores returned %s",
        {dim: normalized[dim] for dim in EVALUATION_DIMENSIONS},
    )
    if DEBUG_DEBRIEF:
        print("[DEBRIEF] Result:", {dim: normalized[dim] for dim in EVALUATION_DIMENSIONS})
    return normalized


def generate_interview_debrief(turns: List[Dict[str, Any]]) -> Dict[str, Any]:
    dimension_buckets: Dict[str, List[float]] = defaultdict(list)
    turn_evaluations: List[Dict[str, Any]] = []

    for turn in turns:
        question_id = str(turn.get("question_id", ""))
        question_category = str(turn.get("question_category", ""))
        answer = str(turn.get("answer") or turn.get("user_answer") or "")

        evaluation = evaluate_answer(
            question_id=question_id,
            question_category=question_category,
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

        for dimension in EVALUATION_DIMENSIONS:
            dimension_buckets[dimension].append(float(evaluation[dimension]))

    overall_scores = {
        dimension: round(sum(scores) / len(scores), 2) if scores else 0.0
        for dimension, scores in dimension_buckets.items()
    }

    for dimension in EVALUATION_DIMENSIONS:
        overall_scores.setdefault(dimension, 0.0)

    return {
        "overall_scores": overall_scores,
        "turn_evaluations": turn_evaluations,
    }
