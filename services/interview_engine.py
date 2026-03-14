import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from prompts.system_prompt import build_system_prompt
from services.debrief_engine import generate_interview_debrief
from services.feedback_engine import generate_full_feedback_package
from services.llm_client import call_llm
from services.question_registry import get_next_question
from store.interview_results import get_interview_results, save_interview_results
from store.interview_turns import get_session_turns, store_interview_turn


LOGGER = logging.getLogger(__name__)

PROMPT_DIR = Path(__file__).resolve().parents[1] / "prompts"
INTERVIEWER_PROMPT_DIR = PROMPT_DIR / "interviewer"

_SUPPORTED_COMPANIES = ("rakuten", "toyota", "softbank", "sony", "uniqlo")


def _load_prompt_text(file_path: Path) -> Optional[str]:
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            return file.read()
    except OSError:
        return None


with open(PROMPT_DIR / "hr_en.txt", "r", encoding="utf-8") as file:
    HR_PROMPT_EN = file.read()

with open(PROMPT_DIR / "hr_jp.txt", "r", encoding="utf-8") as file:
    HR_PROMPT_JP = file.read()


COMPANY_HR_PROMPTS: Dict[tuple, str] = {}
for _company_name in _SUPPORTED_COMPANIES:
    for _language_key in ("en", "jp"):
        _text = _load_prompt_text(INTERVIEWER_PROMPT_DIR / f"{_company_name}_{_language_key}.txt")
        if _text:
            COMPANY_HR_PROMPTS[(_company_name, _language_key)] = _text


def _normalize_language_mode(language_mode: str) -> str:
    normalized = str(language_mode or "").strip().lower()
    if normalized in {"jp", "ja", "japanese"}:
        return "jp"
    return "en"


def _get_hr_prompt(company: str, language_mode: str) -> str:
    company_key = str(company or "").strip().lower()
    language_key = _normalize_language_mode(language_mode)

    company_prompt = COMPANY_HR_PROMPTS.get((company_key, language_key))
    if company_prompt:
        return company_prompt

    if language_key == "jp":
        return HR_PROMPT_JP
    return HR_PROMPT_EN


_SCORE_KEYS = ("communication", "clarity", "cultural_fit", "problem_solving")


def _default_scores() -> Dict[str, int]:
    return {
        "communication": 5,
        "clarity": 5,
        "cultural_fit": 5,
        "problem_solving": 5,
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

    return normalized


def run_interview_turn(
    company: str,
    language_mode: str,
    duration_mins: int,
    is_demo_mode: bool,
    user_message: str,
    conversation_history: List[Any],
    session_id: str = "default_session",
    cv_context: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Run a single MIRU interview turn.

    Steps:
    1. Build system prompt (with CV context if provided)
    2. Append user message to conversation history
    3. Call the LLM for interviewer_response + scores
    4. Return next_question from registry + LLM interviewer_response
    """

    previous_turns = get_session_turns(session_id)
    turn_index = len(previous_turns)
    question = get_next_question(turn_index)

    # Interview is complete — generate debrief if not already done
    if question is None:
        cached_results = get_interview_results(session_id)
        if cached_results is None:
            turns = get_session_turns(session_id)
            debrief = generate_interview_debrief(turns)
            feedback_package = generate_full_feedback_package(debrief)
            save_interview_results(session_id, feedback_package)
        return {"interview_complete": True}

    LOGGER.info("[INTERVIEW] Turn %s", turn_index + 1)
    LOGGER.info("[QUESTION_ID] %s", question["question_id"])
    LOGGER.info("[CATEGORY] %s", question["category"])

    hr_prompt = _get_hr_prompt(company=company, language_mode=language_mode)

    system_prompt = build_system_prompt(
        company=company,
        language_mode=language_mode,
        duration_mins=duration_mins,
        is_demo_mode=is_demo_mode,
        hr_persona=hr_prompt,
        cv_context=cv_context,
    )

    # Build conversation — use transcript_history passed in, or the running history
    updated_conversation = list(conversation_history)
    updated_conversation.append({"role": "user", "content": user_message})

    prompt = (
        f"Candidate's answer:\n{user_message}\n\n"
        "Respond naturally to what they said (1-3 sentences), then score this answer. "
        "Do NOT ask the next question in 'interviewer_response' — that is handled separately."
    )

    llm_response = call_llm(
        system_prompt=system_prompt,
        conversation=updated_conversation,
        user_message=prompt,
    )

    # Next question always comes from the registry (deterministic)
    next_question_text = str(question["prompt"])
    question_id = str(question["question_id"])
    turn_number = turn_index + 1

    interviewer_response = str(llm_response.get("interviewer_response") or "").strip()
    scores = _normalize_scores(llm_response.get("scores"))
    is_wrapping_up = bool(llm_response.get("is_wrapping_up", False))

    # Update running conversation history for stateful clients
    if isinstance(conversation_history, list):
        conversation_history.append({"role": "user", "content": user_message})
        conversation_history.append({"role": "assistant", "content": interviewer_response})

    response_payload = {
        "next_question": next_question_text,
        "interviewer_response": interviewer_response,
        "interview_complete": False,
        "question_id": question_id,
        "scores": scores,
        "is_wrapping_up": is_wrapping_up,
        "session_id": session_id,
        "turn": turn_number,
    }

    try:
        store_interview_turn(
            session_id=session_id,
            turn_index=turn_number,
            question_id=question_id,
            question_category=str(question["category"]),
            question_prompt=next_question_text,
            user_answer=user_message,
            scores=scores,
        )
    except Exception as exc:
        LOGGER.warning("Failed to persist interview turn: %s", exc)

    return response_payload
