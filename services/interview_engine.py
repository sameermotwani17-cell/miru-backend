import logging
from typing import Any, Dict, List

from prompts.system_prompt import build_system_prompt
from services.debrief_engine import generate_interview_debrief
from services.feedback_engine import generate_full_feedback_package
from services.llm_client import call_llm
from services.question_registry import get_next_question
from store.interview_results import get_interview_results, save_interview_results
from store.interview_turns import get_session_turns, store_interview_turn


LOGGER = logging.getLogger(__name__)


_SCORE_KEYS = (
    "jiko_pr",
    "shibou_douki",
    "kyouchousei",
    "seichou_iyoku",
    "bunka_tekigou",
)


def _default_scores() -> Dict[str, int]:
    return {
        "jiko_pr": 5,
        "shibou_douki": 5,
        "kyouchousei": 5,
        "seichou_iyoku": 5,
        "bunka_tekigou": 5,
    }


def _normalize_scores(raw_scores: Any) -> Dict[str, int]:
    if not isinstance(raw_scores, dict):
        return _default_scores()

    normalized: Dict[str, int] = {}
    for key in _SCORE_KEYS:
        value = raw_scores.get(key)
        if value is None:
            return _default_scores()
        try:
            score = int(value)
        except (TypeError, ValueError):
            return _default_scores()
        normalized[key] = max(1, min(10, score))

    # Conservative cultural-fit guardrail for low teamwork alignment.
    if normalized["kyouchousei"] <= 3:
        max_allowed_bunka = max(1, normalized["kyouchousei"] + 2)
        normalized["bunka_tekigou"] = min(normalized["bunka_tekigou"] - 1, max_allowed_bunka)
        normalized["bunka_tekigou"] = max(1, normalized["bunka_tekigou"])

    return normalized


def run_interview_turn(
    company: str,
    language_mode: str,
    duration_mins: int,
    is_demo_mode: bool,
    user_message: str,
    conversation_history: List[Any],
    session_id: str = "default_session",
) -> Dict[str, Any]:
    """
    Run a single MIRU interview turn.

    Steps:
    1. Build system prompt
    2. Append user message to conversation history
    3. Call the LLM
    4. Safely normalize the response into MIRU's schema
    """

    previous_turns = get_session_turns(session_id)
    turn_index = len(previous_turns)
    question = get_next_question(turn_index)

    if question is None:
        cached_results = get_interview_results(session_id)
        if cached_results is None:
            turns = get_session_turns(session_id)
            debrief = generate_interview_debrief(turns)
            feedback_package = generate_full_feedback_package(debrief)
            save_interview_results(session_id, feedback_package)
        return {
            "interview_complete": True,
        }

    LOGGER.info("[INTERVIEW] Turn %s", turn_index + 1)
    LOGGER.info("[QUESTION_ID] %s", question["question_id"])
    LOGGER.info("[CATEGORY] %s", question["category"])

    # Build system prompt
    system_prompt = build_system_prompt(
        company=company,
        language_mode=language_mode,
        duration_mins=duration_mins,
        is_demo_mode=is_demo_mode,
    )

    # Copy conversation history and append latest message
    updated_conversation = list(conversation_history)
    updated_conversation.append({
        "role": "user",
        "content": user_message
    })

    # Call LLM
    llm_response = call_llm(
        system_prompt=system_prompt,
        conversation=updated_conversation,
        user_message=user_message,
    )

    # -------- SAFE NORMALIZATION --------

    agent_text = str(question["prompt"])

    scores = _normalize_scores(llm_response.get("scores"))

    is_wrapping_up = bool(llm_response.get("is_wrapping_up", False))

    question_id = str(question["question_id"])

    response_payload = {
        "agent_text": agent_text,
        "scores": scores,
        "is_wrapping_up": is_wrapping_up,
        "question_id": question_id,
    }

    # Persistence is best-effort and must not break interview flow.
    try:
        store_interview_turn(
            session_id=session_id,
            turn_index=turn_index + 1,
            question_id=str(response_payload["question_id"]),
            question_category=str(question["category"]),
            question_prompt=str(response_payload["agent_text"]),
            user_answer=user_message,
            scores=response_payload["scores"],
        )
    except Exception as exc:
        LOGGER.warning("Failed to persist interview turn: %s", exc)

    # Return normalized response
    return response_payload