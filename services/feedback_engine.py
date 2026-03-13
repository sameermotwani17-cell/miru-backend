import json
import logging
import os
from typing import Any, Dict, List

from openai import OpenAI


LOGGER = logging.getLogger(__name__)

_MODEL_NAME = "gpt-4o-mini"
_API_KEY = os.getenv("OPENAI_API_KEY")


def _fallback_turn_feedback(turn_evaluations: List[Dict[str, Any]]) -> Dict[str, Any]:
    feedback_items: List[Dict[str, str]] = []
    for turn in turn_evaluations:
        feedback_items.append(
            {
                "question_id": str(turn.get("question_id", "")),
                "feedback": "Clear response with relevant intent.",
                "improvement": "Add one concrete example with your personal action and outcome.",
                "rewrite_example": "I collaborated closely with my team, aligned on goals, and reflected on feedback to improve results over time.",
            }
        )

    return {"turn_feedback": feedback_items}


def _fallback_final_report(overall_scores: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "overall_summary": "The interview shows a solid baseline with room to strengthen evidence depth and impact clarity.",
        "strengths": [
            "Collaborative communication",
            "Positive growth orientation",
        ],
        "improvement_areas": [
            "Use more measurable outcomes",
            "Show clearer long-term commitment signals",
        ],
        "recommended_focus": "Practice concise STAR examples that emphasize teamwork, humility, kaizen mindset, and sustained contribution.",
        "overall_scores": dict(overall_scores),
    }


def generate_turn_feedback_batch(turn_evaluations: List[Dict[str, Any]]) -> Dict[str, Any]:
    LOGGER.debug("[FEEDBACK] Generating batch turn feedback")

    if not _API_KEY:
        LOGGER.warning("[FEEDBACK] OPENAI_API_KEY is missing; using fallback turn feedback")
        return _fallback_turn_feedback(turn_evaluations)

    client = OpenAI(api_key=_API_KEY)

    system_prompt = (
        "You are MIRU, an AI interview coach helping candidates prepare for Japanese job interviews.\n"
        "For each interview answer provide:\n"
        "1. Feedback (what was good)\n"
        "2. One improvement suggestion\n"
        "3. A stronger rewritten version of the answer\n\n"
        "The rewritten answer should emphasize teamwork, humility, learning mindset, and long-term commitment.\n"
        "Return ONLY JSON."
    )

    user_prompt = (
        "Return ONLY JSON in this format:\n"
        "{\n"
        "  \"turn_feedback\": [\n"
        "    {\n"
        "      \"question_id\": \"...\",\n"
        "      \"feedback\": \"...\",\n"
        "      \"improvement\": \"...\",\n"
        "      \"rewrite_example\": \"...\"\n"
        "    }\n"
        "  ]\n"
        "}\n\n"
        "Interview answers and scores:\n"
        f"{json.dumps(turn_evaluations, ensure_ascii=False)}"
    )

    try:
        response = client.chat.completions.create(
            model=_MODEL_NAME,
            temperature=0.2,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "miru_turn_feedback_batch",
                    "strict": True,
                    "schema": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "turn_feedback": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "additionalProperties": False,
                                    "properties": {
                                        "question_id": {"type": "string"},
                                        "feedback": {"type": "string"},
                                        "improvement": {"type": "string"},
                                        "rewrite_example": {"type": "string"},
                                    },
                                    "required": [
                                        "question_id",
                                        "feedback",
                                        "improvement",
                                        "rewrite_example",
                                    ],
                                },
                            }
                        },
                        "required": ["turn_feedback"],
                    },
                },
            },
        )

        parsed = json.loads(response.choices[0].message.content or "{}")
        turn_feedback = parsed.get("turn_feedback", [])
        if not isinstance(turn_feedback, list):
            return _fallback_turn_feedback(turn_evaluations)

        return {"turn_feedback": turn_feedback}
    except Exception as exc:
        LOGGER.warning("[FEEDBACK] Batch turn feedback failed; using fallback. error=%s", exc)
        return _fallback_turn_feedback(turn_evaluations)


def generate_final_report(overall_scores: Dict[str, Any], turn_feedback: List[Dict[str, Any]]) -> Dict[str, Any]:
    LOGGER.debug("[FEEDBACK] Generating final report")

    if not _API_KEY:
        LOGGER.warning("[FEEDBACK] OPENAI_API_KEY is missing; using fallback final report")
        return _fallback_final_report(overall_scores)

    client = OpenAI(api_key=_API_KEY)

    system_prompt = (
        "You are MIRU, an AI interview preparation assistant.\n"
        "Based on the interview results, generate a structured interview report.\n"
        "Return ONLY JSON."
    )

    user_prompt = (
        "Return JSON with:\n"
        "{\n"
        "  \"overall_summary\": \"...\",\n"
        "  \"strengths\": [\"...\"],\n"
        "  \"improvement_areas\": [\"...\"],\n"
        "  \"recommended_focus\": \"...\",\n"
        "  \"overall_scores\": {...}\n"
        "}\n\n"
        "Interview scores:\n"
        f"{json.dumps(overall_scores, ensure_ascii=False)}\n\n"
        "Key feedback:\n"
        f"{json.dumps(turn_feedback, ensure_ascii=False)}"
    )

    try:
        response = client.chat.completions.create(
            model=_MODEL_NAME,
            temperature=0.2,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "miru_final_interview_report",
                    "strict": True,
                    "schema": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "overall_summary": {"type": "string"},
                            "strengths": {"type": "array", "items": {"type": "string"}},
                            "improvement_areas": {"type": "array", "items": {"type": "string"}},
                            "recommended_focus": {"type": "string"},
                            "overall_scores": {
                                "type": "object",
                                "additionalProperties": False,
                                "properties": {
                                    "wa_teamwork": {"type": "number"},
                                    "loyalty_commitment": {"type": "number"},
                                    "humility": {"type": "number"},
                                    "kaizen_growth": {"type": "number"},
                                    "cultural_fit": {"type": "number"}
                                },
                                "required": [
                                    "wa_teamwork",
                                    "loyalty_commitment",
                                    "humility",
                                    "kaizen_growth",
                                    "cultural_fit"
                                ]
                            },
                        },
                        "required": [
                            "overall_summary",
                            "strengths",
                            "improvement_areas",
                            "recommended_focus",
                            "overall_scores",
                        ],
                    },
                },
            },
        )

        parsed = json.loads(response.choices[0].message.content or "{}")
        if not isinstance(parsed, dict):
            return _fallback_final_report(overall_scores)
        parsed["overall_scores"] = dict(overall_scores)
        return parsed
    except Exception as exc:
        LOGGER.warning("[FEEDBACK] Final report generation failed; using fallback. error=%s", exc)
        return _fallback_final_report(overall_scores)


def generate_full_feedback_package(debrief_result: Dict[str, Any]) -> Dict[str, Any]:
    turn_evaluations = list(debrief_result.get("turn_evaluations", []))
    overall_scores = dict(debrief_result.get("overall_scores", {}))

    batch_feedback_result = generate_turn_feedback_batch(turn_evaluations)
    turn_feedback = list(batch_feedback_result.get("turn_feedback", []))

    final_report = generate_final_report(overall_scores, turn_feedback)

    return {
        "turn_feedback": turn_feedback,
        "overall_scores": overall_scores,
        "final_report": final_report,
    }
