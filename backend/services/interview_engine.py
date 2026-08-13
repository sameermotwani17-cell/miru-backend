import difflib
import logging
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from prompts.system_prompt import build_system_prompt
from services.debrief_engine import generate_interview_debrief
from services.llm_client import call_llm
from services.score_dimensions import SCORE_DIMENSIONS, DEFAULT_SCORES
from store.interview_results import (
    get_interview_results,
    set_interview_results_processing,
)
from store.interview_turns import get_session_turns, store_interview_turn


LOGGER = logging.getLogger(__name__)

# Safety backstop — prevents runaway sessions if timer_end_epoch is not set.
# Primary completion signal is time-based (timer_end_epoch).
SAFETY_MAX_TURNS = 30
MAX_TURNS = 10
DEFAULT_MAX_QUESTIONS = 12
LLM_TIMEOUT_SECONDS = 25

PROMPT_DIR = Path(__file__).resolve().parents[1] / "prompts"
INTERVIEWER_PROMPT_DIR = PROMPT_DIR / "interviewer"

_SUPPORTED_COMPANIES = ("rakuten", "toyota", "softbank", "sony", "uniqlo")

CLOSING_RESPONSE = "Thank you for your time today. That concludes the interview."
FALLBACK_QUESTION = "Thank you. Let's continue with the next question. Could you share a concrete example from your recent work?"


def _parse_iso_timestamp_to_ms(timestamp: str) -> Optional[int]:
    text = str(timestamp or "").strip()
    if not text:
        return None
    try:
        # Stored timestamps use UTC with trailing Z.
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return int(dt.timestamp() * 1000)
    except ValueError:
        return None


def _coerce_max_questions(max_questions: Optional[int]) -> int:
    try:
        value = int(max_questions) if max_questions is not None else DEFAULT_MAX_QUESTIONS
    except (TypeError, ValueError):
        value = DEFAULT_MAX_QUESTIONS
    return max(1, min(SAFETY_MAX_TURNS, value))


def _elapsed_time_reached(
    duration_mins: int,
    existing_turns: List[Dict[str, Any]],
    timer_end_epoch: Optional[int],
) -> bool:
    now_ms = int(time.time() * 1000)

    # Primary mechanism: trusted timer from session state.
    if timer_end_epoch is not None:
        return now_ms >= int(timer_end_epoch)

    # Fallback mechanism: derive elapsed wall-clock from first stored turn timestamp.
    if duration_mins <= 0 or not existing_turns:
        return False

    first_turn_ts = _parse_iso_timestamp_to_ms(existing_turns[0].get("timestamp", ""))
    if first_turn_ts is None:
        return False

    elapsed_ms = now_ms - first_turn_ts
    return elapsed_ms >= int(duration_mins) * 60 * 1000


def _finalize_interview_response(session_id: str, turn_number: int, scores: Dict[str, int]) -> Dict[str, Any]:
    """Return a completion response and ensure debrief is triggered for ALL completion paths."""
    # Mark results as in-progress so polling can detect completion immediately.
    try:
        set_interview_results_processing(session_id)
    except Exception as exc:
        LOGGER.warning("[INTERVIEW] set_interview_results_processing failed for %s: %s", session_id, exc)

    # Trigger debrief inline — covers force_complete, max_turns, and time-based paths
    # that bypass the LLM is_wrapping_up code block.
    try:
        from services.debrief_engine import generate_interview_debrief
        LOGGER.info("[INTERVIEW] Generating debrief for session %s (finalize path)", session_id)
        generate_interview_debrief(session_id)
    except Exception as exc:
        LOGGER.exception("[INTERVIEW] Inline debrief failed for session %s: %s", session_id, exc)

    return {
        "interview_complete": True,
        "debrief_ready": True,
        "interviewer_response": CLOSING_RESPONSE,
        "next_question": None,
        "scores": scores,
        "question_id": f"Q_LLM_{turn_number:02d}",
        "is_wrapping_up": True,
        "session_id": session_id,
        "turn": turn_number,
    }


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
    return dict(DEFAULT_SCORES)


def _normalize_scores(raw_scores: Any) -> Dict[str, int]:
    if not isinstance(raw_scores, dict):
        return _default_scores()

    normalized: Dict[str, int] = {}
    for key in SCORE_DIMENSIONS:
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

    Each turn contributes up to three messages in order:
      1. assistant: question_prompt  — the question that was asked to the candidate
      2. user:      user_answer      — the candidate's response
      3. assistant: interviewer_response — the interviewer's acknowledgment

    Including question_prompt gives the LLM full recall of every question
    already asked, which prevents repeated questions across turns.
    """
    transcript: List[Dict[str, str]] = []
    for turn in existing_turns:
        question = turn.get("question_prompt") or ""
        if question:
            transcript.append({"role": "assistant", "content": question})

        user_answer = turn.get("user_answer") or turn.get("answer") or ""
        if user_answer:
            transcript.append({"role": "user", "content": user_answer})

        ack = turn.get("interviewer_response") or ""
        if ack:
            transcript.append({"role": "assistant", "content": ack})

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


_DUPLICATE_SIMILARITY_THRESHOLD = 0.75


def _is_duplicate_question(new_question: str, existing_turns: List[Dict[str, Any]]) -> bool:
    """
    Return True if new_question is sufficiently similar to any question_prompt
    already stored in existing_turns (threshold: 0.75).

    This gives the LLM a hard backstop: even if it lacks context about prior
    questions, the engine will catch and replace near-duplicate questions before
    they reach the candidate.
    """
    if not new_question:
        return False
    q_norm = new_question.lower().strip()
    for turn in existing_turns:
        prev_q = turn.get("question_prompt") or ""
        if not prev_q:
            continue
        similarity = difflib.SequenceMatcher(None, q_norm, prev_q.lower().strip()).ratio()
        if similarity >= _DUPLICATE_SIMILARITY_THRESHOLD:
            return True
    return False


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


def _calculate_hiring_signal(scores: Dict[str, Any]) -> str:
    avg = sum(float(scores.get(d, 0)) for d in SCORE_DIMENSIONS) / len(SCORE_DIMENSIONS)
    if avg >= 7.5:
        return "Strong Hire"
    if avg >= 6:
        return "Hire"
    if avg >= 4.5:
        return "Borderline"
    return "No Hire"


def _build_qa_transcript(turns: List[Dict[str, Any]], turn_feedback: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
    feedback_by_qid: Dict[str, Dict[str, Any]] = {}
    for item in turn_feedback or []:
        if not isinstance(item, dict):
            continue
        qid = str(item.get("question_id", "")).strip()
        if qid:
            feedback_by_qid[qid] = item

    transcript: List[Dict[str, Any]] = []
    for turn in turns:
        qid = str(turn.get("question_id", "")).strip()
        coaching = feedback_by_qid.get(qid, {})
        transcript.append(
            {
                "question": str(turn.get("question") or turn.get("question_prompt") or ""),
                "answer": str(turn.get("user_answer") or turn.get("answer") or ""),
                "score": float(turn.get("score", 5.0) or 5.0),
                "feedback": str(turn.get("feedback") or coaching.get("feedback") or ""),
                "better_example": str(turn.get("better_example") or coaching.get("rewrite_example") or ""),
            }
        )
    return transcript


def _call_llm_with_timeout(
    session_id: str,
    system_prompt: str,
    conversation: List[Dict[str, str]],
    user_message: str,
) -> Dict[str, Any]:
    executor = ThreadPoolExecutor(max_workers=1)
    try:
        future = executor.submit(
            call_llm,
            system_prompt,
            conversation,
            user_message,
        )
        result = future.result(timeout=LLM_TIMEOUT_SECONDS)
        executor.shutdown(wait=False, cancel_futures=True)

        if isinstance(result, dict):
            return result

        LOGGER.warning("[INTERVIEW] LLM returned non-dict payload for session %s", session_id)
    except FutureTimeoutError:
        future.cancel()
        executor.shutdown(wait=False, cancel_futures=True)
        LOGGER.warning("LLM response timeout for session %s", session_id)
    except Exception as exc:
        executor.shutdown(wait=False, cancel_futures=True)
        LOGGER.warning("[INTERVIEW] LLM call failed for session %s: %s", session_id, exc)

    # Always return a safe fallback so run_interview_turn never blocks indefinitely.
    return {
        "interviewer_response": FALLBACK_QUESTION,
        "next_question": FALLBACK_QUESTION,
        "scores": dict(DEFAULT_SCORES),
        "is_wrapping_up": False,
        "_fallback": True,
    }


def _trigger_debrief(session_id: str) -> None:
    """Trigger debrief generation for a session. Safe to call multiple times."""
    existing = get_interview_results(session_id)
    if existing is not None and existing.get("status") == "ready":
        return
    try:
        generate_interview_debrief(session_id)
    except Exception as exc:
        LOGGER.exception("[DEBRIEF] _trigger_debrief failed for session %s: %s", session_id, exc)


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
    max_questions: Optional[int] = None,
    force_complete: bool = False,
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

    Debrief is triggered inline when interview_complete is True, and also
    scheduled as a BackgroundTask by api/interview_routes.py as a fallback.
    """

    existing_turns = get_session_turns(session_id)
    turn_index = len(existing_turns)
    max_questions_limit = _coerce_max_questions(max_questions)

    # The question the user is answering now is the one stored as question_prompt on the previous turn.
    # question_prompt always holds the next_question generated in that turn — i.e. what was asked to the user.
    current_question = existing_turns[-1].get("question_prompt", "") if existing_turns else ""

    if force_complete:
        turn_number = turn_index + 1
        scores = _default_scores()
        question_id = f"Q_LLM_{turn_number:02d}"
        try:
            store_interview_turn(
                session_id=session_id,
                turn_index=turn_number,
                question_id=question_id,
                question_category="adaptive",
                question_prompt="",
                question=current_question,
                answer=user_message,
                interviewer_response=CLOSING_RESPONSE,
                scores=scores,
                score=5.0,
                feedback="",
                better_example="",
            )
        except Exception as exc:
            LOGGER.warning("[INTERVIEW] Failed to persist force-complete turn: %s", exc)
        # Persist processing state immediately so result polling can observe completion in progress.
        set_interview_results_processing(session_id)
        return _finalize_interview_response(session_id=session_id, turn_number=turn_number, scores=scores)

    # Hard stop once completion/debrief is already in-flight or ready.
    existing_results = get_interview_results(session_id)
    if isinstance(existing_results, dict) and existing_results.get("status") in {"processing", "ready"}:
        return _finalize_interview_response(
            session_id=session_id,
            turn_number=max(turn_index, 1),
            scores=_default_scores(),
        )

    # Additional hard cap to prevent runaway loops if timer/front-end flow fails.
    if turn_index >= MAX_TURNS:
        turn_number = turn_index + 1
        scores = _default_scores()
        question_id = f"Q_LLM_{turn_number:02d}"
        try:
            store_interview_turn(
                session_id=session_id,
                turn_index=turn_number,
                question_id=question_id,
                question_category="adaptive",
                question_prompt="",
                question=current_question,
                answer=user_message,
                interviewer_response=CLOSING_RESPONSE,
                scores=scores,
                score=5.0,
                feedback="",
                better_example="",
            )
        except Exception as exc:
            LOGGER.warning("[INTERVIEW] Failed to persist max-turn completion turn: %s", exc)
        return _finalize_interview_response(session_id=session_id, turn_number=turn_number, scores=scores)

    # Max-questions completion gate (deterministic and LLM-independent).
    if turn_index + 1 >= max_questions_limit:
        turn_number = turn_index + 1
        scores = _default_scores()
        question_id = f"Q_LLM_{turn_number:02d}"
        try:
            store_interview_turn(
                session_id=session_id,
                turn_index=turn_number,
                question_id=question_id,
                question_category="adaptive",
                question_prompt="",
                question=current_question,
                answer=user_message,
                interviewer_response=CLOSING_RESPONSE,
                scores=scores,
                score=5.0,
                feedback="",
                better_example="",
            )
        except Exception as exc:
            LOGGER.warning("[INTERVIEW] Failed to persist completion turn: %s", exc)
        return _finalize_interview_response(session_id=session_id, turn_number=turn_number, scores=scores)

    # Safety backstop — fires only if no timer is provided or timer logic fails
    if turn_index >= SAFETY_MAX_TURNS:
        return _finalize_interview_response(
            session_id=session_id,
            turn_number=turn_index,
            scores=_default_scores(),
        )

    # Time-based completion (primary mechanism)
    if _elapsed_time_reached(duration_mins=duration_mins, existing_turns=existing_turns, timer_end_epoch=timer_end_epoch):
        LOGGER.info("[INTERVIEW] session=%s elapsed time reached, completing.", session_id)
        turn_number = turn_index + 1
        scores = _default_scores()
        question_id = f"Q_LLM_{turn_number:02d}"
        try:
            store_interview_turn(
                session_id=session_id,
                turn_index=turn_number,
                question_id=question_id,
                question_category="adaptive",
                question_prompt="",
                question=current_question,
                answer=user_message,
                interviewer_response=CLOSING_RESPONSE,
                scores=scores,
                score=5.0,
                feedback="",
                better_example="",
            )
        except Exception as exc:
            LOGGER.warning("[INTERVIEW] Failed to persist completion turn: %s", exc)
        return _finalize_interview_response(session_id=session_id, turn_number=turn_number, scores=scores)

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

    llm_response = _call_llm_with_timeout(
        session_id=session_id,
        system_prompt=system_prompt,
        conversation=transcript,
        user_message=turn_prompt,
    )

    interviewer_response = str(llm_response.get("interviewer_response") or "").strip()
    next_question = str(llm_response.get("next_question") or "").strip()
    scores = _normalize_scores(llm_response.get("scores"))
    is_wrapping_up = bool(llm_response.get("is_wrapping_up", False))
    is_fallback_response = bool(llm_response.get("_fallback", False))

    if not is_fallback_response:
        # Guard: if the LLM embedded the question inside interviewer_response,
        # clear interviewer_response so the candidate does not hear it twice.
        interviewer_response, next_question = _fix_duplicate_question(
            interviewer_response, next_question
        )

        # Guard: if next_question repeats any question already asked this session,
        # replace it with the fallback so the candidate never hears the same
        # question twice. Uses 0.75 similarity against all stored question_prompts.
        if _is_duplicate_question(next_question, existing_turns):
            LOGGER.warning(
                "[INTERVIEW] Duplicate question detected and replaced for session %s: %s",
                session_id,
                next_question,
            )
            next_question = FALLBACK_QUESTION

    # Completion is driven by the LLM's wrapping-up signal
    interview_complete = is_wrapping_up

    if interview_complete:
        LOGGER.info("Interview complete for session %s", session_id)
        interviewer_response = CLOSING_RESPONSE
        next_question = None
        set_interview_results_processing(session_id)

    turn_number = turn_index + 1
    question_id = f"Q_LLM_{turn_number:02d}"

    try:
        store_interview_turn(
            session_id=session_id,
            turn_index=turn_number,
            question_id=question_id,
            question_category="adaptive",
            question_prompt=next_question or "",
            question=current_question,
            answer=user_message,
            interviewer_response=interviewer_response,
            scores=scores,
            score=round(sum(float(scores.get(dim, 5)) for dim in SCORE_DIMENSIONS) / len(SCORE_DIMENSIONS), 2),
            feedback="",
            better_example="",
        )
    except Exception as exc:
        LOGGER.warning("[INTERVIEW] Failed to persist turn: %s", exc)

    # Post-LLM timer check: catches cases where the timer expired during the LLM call.
    # Without this, the turn returns interview_complete=False even though time is up,
    # and the frontend never navigates to the debrief screen.
    if not interview_complete and _elapsed_time_reached(
        duration_mins=duration_mins,
        existing_turns=existing_turns,
        timer_end_epoch=timer_end_epoch,
    ):
        LOGGER.info("[INTERVIEW] session=%s timer expired during LLM call, finalizing", session_id)
        return _finalize_interview_response(session_id=session_id, turn_number=turn_number, scores=scores)

    if interview_complete:
        try:
            from services.debrief_engine import generate_interview_debrief
            LOGGER.info("Generating interview debrief for session %s", session_id)
            generate_interview_debrief(session_id)
        except Exception as exc:
            LOGGER.exception("Debrief generation failed for session %s", session_id)

    return {
        "next_question": next_question,
        "interviewer_response": interviewer_response,
        "interview_complete": interview_complete,
        "debrief_ready": interview_complete,
        "question_id": question_id,
        "scores": scores,
        "is_wrapping_up": is_wrapping_up,
        "session_id": session_id,
        "turn": turn_number,
    }
