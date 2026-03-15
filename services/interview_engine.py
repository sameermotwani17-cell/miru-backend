import difflib
import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from prompts.system_prompt import build_system_prompt
from services.debrief_engine import generate_interview_debrief
from services.feedback_engine import generate_full_feedback_package
from services.llm_client import call_llm
from store.interview_results import get_interview_results, save_interview_results
from store.interview_turns import get_session_turns, store_interview_turn


LOGGER = logging.getLogger(__name__)

# Safety backstop — prevents runaway sessions if timer_end_epoch is not set.
# Primary completion signal is time-based (timer_end_epoch).
SAFETY_MAX_TURNS = 30

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


def _rebuild_transcript(existing_turns: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """
    Reconstruct the conversation transcript from stored turns.
    Backend is the single source of truth — client-sent history is never used.
    """
    transcript: List[Dict[str, str]] = []
    for turn in existing_turns:
        interviewer_response = turn.get("interviewer_response", "")
        if interviewer_response:
            transcript.append({"role": "assistant", "content": interviewer_response})

        user_answer = turn.get("user_answer", "") or turn.get("answer", "")
        if user_answer:
            transcript.append({"role": "user", "content": user_answer})

    return transcript


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


_DUPLICATE_SIMILARITY_THRESHOLD = 0.6


def _is_duplicate_question(a: str, b: str) -> bool:
    """Return True if a and b are likely the same question (similarity > 0.8)."""
    if not a or not b:
        return False
    similarity = difflib.SequenceMatcher(None, a.lower(), b.lower()).ratio()
    return similarity > 0.8


def _fix_duplicate_question(
    interviewer_response: str,
    next_question: str,
) -> Tuple[str, str]:
    """
    Guard against the LLM embedding the question inside interviewer_response.

    Rule:
      If interviewer_response is sufficiently similar to next_question
      (regardless of punctuation), the LLM has collapsed both fields into one.
      In that case we:
        - keep next_question as the canonical question
        - clear interviewer_response so the candidate never hears it twice

    We do NOT gate on a '?' because the LLM sometimes phrases the duplicate as
    an imperative ("Please introduce yourself.") which carries no question mark
    yet is still a duplicate of the next_question field.

    The similarity check uses difflib's SequenceMatcher — fast, dependency-free,
    and robust enough against minor paraphrasing.
    """
    if not interviewer_response or not next_question:
        return interviewer_response, next_question

    resp_norm = interviewer_response.lower().strip()
    q_norm = next_question.lower().strip()

    similarity = difflib.SequenceMatcher(None, resp_norm, q_norm).ratio()

    if similarity >= _DUPLICATE_SIMILARITY_THRESHOLD:
        LOGGER.debug(
            "[INTERVIEW] Duplicate question detected (similarity=%.2f); "
            "clearing interviewer_response to avoid double-prompt.",
            similarity,
        )
        return "", next_question

    return interviewer_response, next_question


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
    session_id: str = "default_session",
    cv_context: Optional[str] = None,
    user_name: str = "",
    target_role: str = "",
    timer_end_epoch: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Run a single MIRU interview turn.

    The backend is the single source of truth for conversation state.
    Transcript is always rebuilt from stored turns — never from client-sent history.
    The LLM generates interviewer_response, next_question, and scores each turn.

    Completion is driven by:
      1. timer_end_epoch (primary) — session wall-clock time has expired
      2. LLM is_wrapping_up flag — LLM signals the interview is naturally complete
      3. SAFETY_MAX_TURNS (backstop) — hard cap to prevent runaway sessions
    """

    existing_turns = get_session_turns(session_id)
    turn_index = len(existing_turns)

    # Safety backstop — fires only if no timer is provided or timer logic fails
    if turn_index >= SAFETY_MAX_TURNS:
        _trigger_debrief(session_id)
        return {
            "interview_complete": True,
            "interviewer_response": "",
            "next_question": "",
            "scores": _default_scores(),
        }

    # Time-based completion (primary mechanism)
    if timer_end_epoch is not None:
        now_ms = int(time.time() * 1000)
        if now_ms >= timer_end_epoch:
            LOGGER.info(
                "[INTERVIEW] session=%s time expired (now=%d >= end=%d), completing.",
                session_id, now_ms, timer_end_epoch,
            )
            _trigger_debrief(session_id)
            return {
                "interview_complete": True,
                "interviewer_response": CLOSING_RESPONSE,
                "next_question": "",
                "scores": _default_scores(),
            }

    LOGGER.info("[INTERVIEW] session=%s turn=%s", session_id, turn_index + 1)

    hr_prompt = _get_hr_prompt(company=company, language_mode=language_mode)

    # Extract candidate name from cv_context if user_name not provided
    candidate_name = user_name or "the candidate"

    system_prompt = build_system_prompt(
        company=company,
        language_mode=language_mode,
        duration_mins=duration_mins,
        is_demo_mode=is_demo_mode,
        hr_persona=hr_prompt,
        cv_context=cv_context,
        user_name=candidate_name,
        target_role=target_role,
    )

    # Rebuild transcript from stored turns (backend-owned state)
    transcript = _rebuild_transcript(existing_turns)

    turn_prompt = _build_turn_prompt(user_message, turn_index)

    llm_response = call_llm(
        system_prompt=system_prompt,
        conversation=transcript,
        user_message=turn_prompt,
    )

    interviewer_response = str(llm_response.get("interviewer_response") or "").strip()
    next_question = str(llm_response.get("next_question") or "").strip()
    scores = _normalize_scores(llm_response.get("scores"))
    is_wrapping_up = bool(llm_response.get("is_wrapping_up", False))

    # Guard: if the LLM embedded the question inside interviewer_response,
    # clear interviewer_response so the candidate does not hear it twice.
    interviewer_response, next_question = _fix_duplicate_question(
        interviewer_response, next_question
    )

    # Additional guard: if fields are still near-identical (>0.8), remove next_question
    if _is_duplicate_question(interviewer_response, next_question):
        next_question = ""

    # Completion is driven by the LLM's wrapping-up signal
    interview_complete = is_wrapping_up

    if interview_complete:
        interviewer_response = CLOSING_RESPONSE
        next_question = ""

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
