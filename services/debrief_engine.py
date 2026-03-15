import json
import logging
import os
from collections import defaultdict
from typing import Any, Dict, List

from openai import OpenAI

from services.score_dimensions import SCORE_DIMENSIONS


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
_API_KEY = os.getenv("OPENAI_API_KEY")


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

    if not _API_KEY:
        LOGGER.warning("[DEBRIEF] OPENAI_API_KEY is missing; using fallback evaluation")
        return dict(_DEFAULT_EVALUATION)

    client = OpenAI(api_key=_API_KEY)

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


def generate_interview_debrief(turns: List[Dict[str, Any]]) -> Dict[str, Any]:
    dimension_buckets: Dict[str, List[float]] = defaultdict(list)
    turn_evaluations: List[Dict[str, Any]] = []

    for turn in turns:
        question_id = str(turn.get("question_id", ""))
        question_category = str(turn.get("question_category", ""))
        question_text = str(turn.get("question_prompt", ""))
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
        dimension: round(sum(scores) / len(scores), 2) if scores else 0.0
        for dimension, scores in dimension_buckets.items()
    }

    for dimension in SCORE_DIMENSIONS:
        overall_scores.setdefault(dimension, 0.0)

    return {
        "overall_scores": overall_scores,
        "turn_evaluations": turn_evaluations,
    }
