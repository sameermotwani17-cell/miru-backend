import json
import logging
import os
from typing import Any, Dict, List

from openai import OpenAI

from services.score_dimensions import SCORE_DIMENSIONS


LOGGER = logging.getLogger(__name__)

_MODEL_NAME = "gpt-4o-mini"
def _api_key() -> str | None:
    """Read the key per call so a late-bound env var is still picked up."""
    return os.getenv("OPENAI_API_KEY")


def _fallback_turn_feedback(turn_evaluations: List[Dict[str, Any]]) -> Dict[str, Any]:
    feedback_items = [
        {
            "question_id": str(t.get("question_id", "")),
            "feedback": "Clear response with relevant intent.",
            "improvement": "Add one concrete example showing team-first thinking and long-term commitment to the company.",
            "rewrite_example": "I worked closely with my team to achieve this outcome, and the experience strengthened my commitment to growing within the organisation long-term.",
        }
        for t in turn_evaluations
    ]
    return {"turn_feedback": feedback_items}


def _fallback_final_report(overall_scores: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "overall_summary": "The interview shows a solid baseline with room to strengthen Japanese HR alignment, particularly around team-first framing and long-term commitment signals.",
        "strengths": ["Shows willingness to contribute", "Demonstrates growth orientation"],
        "improvement_areas": [
            "Use more team-first language (wa_teamwork)",
            "Signal stronger long-term commitment to the company (loyalty_commitment)",
            "Frame achievements with appropriate humility",
        ],
        "recommended_focus": "Practice framing answers around group outcomes, company loyalty, and continuous improvement within the organisation's framework.",
        "overall_scores": dict(overall_scores),
    }


def generate_turn_feedback_batch(turn_evaluations: List[Dict[str, Any]]) -> Dict[str, Any]:
    LOGGER.debug("[FEEDBACK] Generating batch turn feedback")

    if not _api_key():
        return _fallback_turn_feedback(turn_evaluations)

    client = OpenAI(api_key=_api_key())

    system_prompt = (
        "You are MIRU, an AI interview coach specialising in Japanese corporate HR evaluation.\n"
        "For each interview answer provide coaching feedback based on these five Japanese HR dimensions:\n"
        "- wa_teamwork (協調性): group harmony, team-first language\n"
        "- loyalty_commitment (忠誠心): long-term commitment signals\n"
        "- humility (謙虚さ): appropriate modesty, credit to team\n"
        "- kaizen_growth (成長意欲): growth framed within company framework\n"
        "- cultural_fit (文化適合): Japanese business etiquette awareness\n\n"
        "For each answer provide:\n"
        "1. Feedback (what signals were good for Japanese HR)\n"
        "2. One improvement suggestion referencing specific Japanese HR dimensions\n"
        "3. A stronger rewritten version of the answer that scores higher on these dimensions\n\n"
        "The rewritten answer should demonstrate team-first thinking, appropriate humility, "
        "long-term commitment, growth within the company framework, and cultural awareness.\n"
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
        + json.dumps(turn_evaluations, ensure_ascii=False)
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
                                    "required": ["question_id", "feedback", "improvement", "rewrite_example"],
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


def generate_final_report(overall_scores: Dict[str, Any], turn_feedback: List[Dict[str, Any]], transcript_text: str = "") -> Dict[str, Any]:
    LOGGER.debug("[FEEDBACK] Generating final report")

    if not _api_key():
        return _fallback_final_report(overall_scores)

    client = OpenAI(api_key=_api_key())

    system_prompt = (
        "You are MIRU, an AI interview preparation assistant specialising in Japanese corporate HR.\n"
        "Based on the interview results, generate a structured interview report.\n"
        "The five scoring dimensions are Japanese HR criteria:\n"
        "- wa_teamwork (協調性): group harmony, team-first language\n"
        "- loyalty_commitment (忠誠心): long-term commitment signals\n"
        "- humility (謙虚さ): appropriate modesty\n"
        "- kaizen_growth (成長意欲): growth within company framework\n"
        "- cultural_fit (文化適合): Japanese business etiquette\n"
        "Frame all feedback in terms of these dimensions.\n"
        "Return ONLY JSON."
    )

    user_prompt = (
        "Return JSON with overall_summary, strengths, improvement_areas, recommended_focus, overall_scores.\n\n"
        "Interview scores:\n"
        + json.dumps(overall_scores, ensure_ascii=False)
        + "\n\nKey feedback:\n"
        + json.dumps(turn_feedback, ensure_ascii=False)
        + (f"\n\nFull interview transcript:\n{transcript_text}" if transcript_text else "")
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
                                    "cultural_fit": {"type": "number"},
                                },
                                "required": [
                                    "wa_teamwork",
                                    "loyalty_commitment",
                                    "humility",
                                    "kaizen_growth",
                                    "cultural_fit",
                                ],
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


def generate_full_feedback_package(debrief_result: Dict[str, Any], transcript_text: str = "") -> Dict[str, Any]:
    turn_evaluations = list(debrief_result.get("turn_evaluations", []))
    overall_scores = dict(debrief_result.get("overall_scores", {}))

    batch_feedback_result = generate_turn_feedback_batch(turn_evaluations)
    turn_feedback = list(batch_feedback_result.get("turn_feedback", []))

    final_report = generate_final_report(overall_scores, turn_feedback, transcript_text=transcript_text)

    return {
        "turn_feedback": turn_feedback,
        "overall_scores": overall_scores,
        "final_report": final_report,
    }
