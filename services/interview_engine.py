import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from prompts.system_prompt import build_system_prompt
from services.debrief_engine import generate_interview_debrief
from services.feedback_engine import generate_full_feedback_package
from services.llm_client import call_llm
from store.interview_results import get_interview_results, save_interview_results
from store.interview_turns import get_session_turns, store_interview_turn


LOGGER = logging.getLogger(__name__)

MAX_TURNS = 10

PROMPT_DIR = Path(__file__).resolve().parents[1] / "prompts"
INTERVIEWER_PROMPT_DIR = PROMPT_DIR / "interviewer"

_SUPPORTED_COMPANIES = ("rakuten", "toyota", "softbank", "sony", "uniqlo")

_SCORE_KEYS = ("communication", "clarity", "cultural_fit", "problem_solving")

CLOSING_RESPONSE = (
    "Thank you for your time today. It has been a pleasure speaking with you. "
    "This concludes our interview. Please wait for your assessment."
)


def _load_prompt_text(file_path: Path) -> Optional[str]:
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            return file.read()
    except OSError:
        return None


def _load_hr_prompt(filename: str) -> str:
    path = PROMPT_DIR / filename
    text = _load_prompt_text(path)
    return text or ""


HR_PROMPT_EN = _load_hr_prompt("hr_en.txt")
HR_PROMPT_JP = _load_hr_prompt("hr_jp.txt")


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


def _build_turn_prompt(user_message: str, turn_index: int) -> str:
    if turn_index == 0:
        return (
            f"The candidate has just joined the interview. Their opening message: \"{user_message}\"\n\n"
            "Instructions:\n"
            "- In 'interviewer_response': Greet the candidate warmly and professionally by name (if known). "
            "Do not ask a question here.\n"
            "- In 'next_question': Ask the candidate to introduce themselves. "
            "This is the first question of the interview."
        )
    return (
        f"Candidate's answer: {user_message}\n\n"
        "Instructions:\n"
        "- In 'interviewer_response': Acknowledge their answer briefly and naturally (1-3 sentences). "
        "Do not repeat back what they said. Do not use filler like 'I see' or 'That is interesting'. "
        "Reference a specific detail from their answer.\n"
        "- In 'next_question': Ask one focused follow-up question that flows naturally from their answer. "
        "Vary the type across the interview: behavioral, situational, motivational, or values-based. "
        "Never repeat a question already asked."
    )


def _trigger_debrief(session_id: str) -> None:
    try:
        if get_interview_results(session_id) is None:
            turns = get_session_turns(session_id)
            debrief = generate_interview_debrief(turns)
            feedback_package = generate_full_feedback_package(debrief)
            save_interview_results(session_id, feedback_package)
    except Exception as exc:
        LOGGER.warning("[DEBRIEF] Failed to generate debrief for session %s: %s", session_id, exc)


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

    The LLM fully controls the interview: it generates interviewer_response,
    next_question, and scores in one call. No static question registry is used.
    """

    previous_turns = get_session_turns(session_id)
    turn_index = len(previous_turns)

    # Interview complete — already at or past the turn limit
    if turn_index >= MAX_TURNS:
        _trigger_debrief(session_id)
        return {"interview_complete": True}

    LOGGER.info("[INTERVIEW] session=%s turn=%s/%s", session_id, turn_index + 1, MAX_TURNS)

    hr_prompt = _get_hr_prompt(company=company, language_mode=language_mode)

    system_prompt = build_system_prompt(
        company=company,
        language_mode=language_mode,
        duration_mins=duration_mins,
        is_demo_mode=is_demo_mode,
        hr_persona=hr_prompt,
        cv_context=cv_context,
    )

    # Build conversation for LLM — filter malformed messages
    clean_history: List[Dict[str, str]] = []
    for msg in conversation_history:
        if (
            isinstance(msg, dict)
            and msg.get("role") in {"system", "user", "assistant"}
            and msg.get("content")
        ):
            clean_history.append({"role": msg["role"], "content": str(msg["content"])})

    turn_prompt = _build_turn_prompt(user_message, turn_index)

    llm_response = call_llm(
        system_prompt=system_prompt,
        conversation=clean_history,
        user_message=turn_prompt,
    )

    interviewer_response = str(llm_response.get("interviewer_response") or "").strip()
    next_question = str(llm_response.get("next_question") or "").strip()
    scores = _normalize_scores(llm_response.get("scores"))
    is_wrapping_up = bool(llm_response.get("is_wrapping_up", False))

    # Determine if this is the final turn
    is_last_turn = (turn_index + 1 >= MAX_TURNS) or is_wrapping_up
    interview_complete = is_last_turn

    if is_last_turn:
        next_question = CLOSING_RESPONSE

    # Update conversation history in-place for stateful clients
    if isinstance(conversation_history, list):
        conversation_history.append({"role": "user", "content": user_message})
        conversation_history.append({"role": "assistant", "content": interviewer_response})
        if next_question:
            conversation_history.append({"role": "assistant", "content": next_question})

    turn_number = turn_index + 1
    question_id = f"Q_LLM_{turn_number:02d}"

    try:
        store_interview_turn(
            session_id=session_id,
            turn_index=turn_number,
            question_id=question_id,
            question_category="adaptive",
            question_prompt=next_question,
            user_answer=user_message,
            interviewer_response=interviewer_response,
            scores=scores,
        )
    except Exception as exc:
        LOGGER.warning("[INTERVIEW] Failed to persist turn: %s", exc)

    if interview_complete:
        _trigger_debrief(session_id)

    return {
        "next_question": next_question,
        "interviewer_response": interviewer_response,
        "interview_complete": interview_complete,
        "question_id": question_id,
        "scores": scores,
        "is_wrapping_up": is_wrapping_up,
        "session_id": session_id,
        "turn": turn_number,
    }
