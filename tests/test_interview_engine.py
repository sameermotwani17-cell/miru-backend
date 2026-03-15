"""
Tests for the MIRU adaptive interview engine.

Run with: pytest tests/test_interview_engine.py -v
"""
import sys
import time
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pytest

# Ensure the miru-backend package root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

VALID_LLM_RESPONSE = {
    "interviewer_response": "Thank you for that introduction.",
    "next_question": "Could you tell me about a time you faced a difficult challenge?",
    "scores": {
        "wa_teamwork": 7,
        "loyalty_commitment": 6,
        "humility": 5,
        "kaizen_growth": 6,
        "cultural_fit": 5,
    },
    "is_wrapping_up": False,
}


def _mock_llm(response: Dict[str, Any] = None):
    return patch(
        "services.interview_engine.call_llm",
        return_value=response or VALID_LLM_RESPONSE,
    )


def _mock_store(existing_turns: List[Dict] = None):
    return (
        patch("services.interview_engine.get_session_turns", return_value=existing_turns or []),
        patch("services.interview_engine.store_interview_turn", return_value=MagicMock()),
    )


def _mock_results():
    return (
        patch("services.interview_engine.get_interview_results", return_value=None),
        patch("services.interview_engine.save_interview_results"),
    )


# ---------------------------------------------------------------------------
# Test 1: run_interview_turn returns valid structure
# ---------------------------------------------------------------------------

class TestRunInterviewTurnStructure:

    def test_returns_required_keys(self):
        from services.interview_engine import run_interview_turn

        p_turns, p_store = _mock_store()
        p_res_get, p_res_save = _mock_results()

        with _mock_llm(), p_turns, p_store, p_res_get, p_res_save:
            result = run_interview_turn(
                company="rakuten",
                language_mode="en",
                duration_mins=15,
                is_demo_mode=False,
                user_message="Hello, I am Sameer.",
                session_id="test_session_001",
            )

        assert isinstance(result, dict), "Result must be a dict"
        for key in ("interviewer_response", "next_question", "scores", "interview_complete", "turn"):
            assert key in result, f"Missing key: {key}"

    def test_scores_contain_all_dimensions(self):
        from services.interview_engine import run_interview_turn

        p_turns, p_store = _mock_store()
        p_res_get, p_res_save = _mock_results()

        with _mock_llm(), p_turns, p_store, p_res_get, p_res_save:
            result = run_interview_turn(
                company="rakuten",
                language_mode="en",
                duration_mins=15,
                is_demo_mode=False,
                user_message="My name is Sameer.",
                session_id="test_session_002",
            )

        scores = result["scores"]
        assert isinstance(scores, dict)
        for dim in ("wa_teamwork", "loyalty_commitment", "humility", "kaizen_growth", "cultural_fit"):
            assert dim in scores, f"Missing score dimension: {dim}"
            assert 1 <= scores[dim] <= 10, f"Score out of range for {dim}: {scores[dim]}"

    def test_interview_not_complete_on_first_turn(self):
        from services.interview_engine import run_interview_turn

        p_turns, p_store = _mock_store()
        p_res_get, p_res_save = _mock_results()

        with _mock_llm(), p_turns, p_store, p_res_get, p_res_save:
            result = run_interview_turn(
                company="rakuten",
                language_mode="en",
                duration_mins=15,
                is_demo_mode=False,
                user_message="Hello.",
                session_id="test_session_003",
            )

        assert result["interview_complete"] is False


# ---------------------------------------------------------------------------
# Test 2: messages sent to LLM always contain valid role/content
# ---------------------------------------------------------------------------

class TestLLMMessageIntegrity:

    def test_transcript_built_from_stored_turns(self):
        """LLM conversation must be rebuilt from stored turns, not client input."""
        from services.interview_engine import run_interview_turn

        stored_turns = [
            {
                "turn_index": 1,
                "interviewer_response": "Welcome to the interview.",
                "user_answer": "I am a software engineer.",
                "scores": {},
            }
        ]

        captured_calls: List[Dict] = []

        def fake_llm(system_prompt, conversation, user_message):
            captured_calls.append({"conversation": list(conversation)})
            return VALID_LLM_RESPONSE

        p_turns, p_store = _mock_store(existing_turns=stored_turns)
        p_res_get, p_res_save = _mock_results()

        with patch("services.interview_engine.call_llm", side_effect=fake_llm), \
             p_turns, p_store, p_res_get, p_res_save:
            run_interview_turn(
                company="rakuten",
                language_mode="en",
                duration_mins=15,
                is_demo_mode=False,
                user_message="My follow-up answer.",
                session_id="test_session_004",
            )

        assert captured_calls, "LLM must have been called"
        sent_conversation = captured_calls[0]["conversation"]

        # Stored turn content must appear in the conversation sent to LLM
        roles_contents = [(m["role"], m["content"]) for m in sent_conversation]
        assert ("assistant", "Welcome to the interview.") in roles_contents
        assert ("user", "I am a software engineer.") in roles_contents

    def test_all_messages_have_valid_role_and_content(self):
        """Every message sent to call_llm must have a valid role and non-empty content."""
        from services.interview_engine import run_interview_turn

        stored_turns = [
            {
                "turn_index": 1,
                "interviewer_response": "Hello, please introduce yourself.",
                "user_answer": "I am Sameer from Liberia.",
                "scores": {},
            }
        ]

        captured_calls: List[Dict] = []

        def fake_llm(system_prompt, conversation, user_message):
            captured_calls.append({"conversation": list(conversation)})
            return VALID_LLM_RESPONSE

        p_turns, p_store = _mock_store(existing_turns=stored_turns)
        p_res_get, p_res_save = _mock_results()

        with patch("services.interview_engine.call_llm", side_effect=fake_llm), \
             p_turns, p_store, p_res_get, p_res_save:
            run_interview_turn(
                company="rakuten",
                language_mode="en",
                duration_mins=15,
                is_demo_mode=False,
                user_message="I enjoy collaborative work.",
                session_id="test_session_005",
            )

        assert captured_calls, "LLM must have been called"
        valid_roles = {"system", "user", "assistant"}
        for msg in captured_calls[0]["conversation"]:
            assert isinstance(msg, dict), f"Non-dict message sent to LLM: {msg}"
            assert "role" in msg, f"Message missing 'role': {msg}"
            assert "content" in msg, f"Message missing 'content': {msg}"
            assert msg["role"] in valid_roles, f"Invalid role '{msg['role']}'"
            assert msg["content"], f"Empty content in message: {msg}"

    def test_empty_stored_turns_sends_no_history(self):
        """On the very first turn, conversation passed to LLM must be empty."""
        from services.interview_engine import run_interview_turn

        captured_calls: List[Dict] = []

        def fake_llm(system_prompt, conversation, user_message):
            captured_calls.append({"conversation": list(conversation)})
            return VALID_LLM_RESPONSE

        p_turns, p_store = _mock_store(existing_turns=[])
        p_res_get, p_res_save = _mock_results()

        with patch("services.interview_engine.call_llm", side_effect=fake_llm), \
             p_turns, p_store, p_res_get, p_res_save:
            run_interview_turn(
                company="rakuten",
                language_mode="en",
                duration_mins=15,
                is_demo_mode=False,
                user_message="Hello.",
                session_id="test_session_006",
            )

        assert captured_calls, "LLM must have been called"
        assert captured_calls[0]["conversation"] == [], "No history on first turn"


# ---------------------------------------------------------------------------
# Test 3: transcript is rebuilt correctly from stored turns
# ---------------------------------------------------------------------------

class TestTranscriptRebuild:

    def test_rebuild_transcript_order(self):
        """_rebuild_transcript must interleave assistant/user messages correctly."""
        from services.interview_engine import _rebuild_transcript

        turns = [
            {
                "interviewer_response": "Hello, welcome.",
                "user_answer": "Hi, I am Sameer.",
            },
            {
                "interviewer_response": "Thank you for that.",
                "user_answer": "I worked at a startup.",
            },
        ]

        transcript = _rebuild_transcript(turns)

        assert transcript[0] == {"role": "assistant", "content": "Hello, welcome."}
        assert transcript[1] == {"role": "user", "content": "Hi, I am Sameer."}
        assert transcript[2] == {"role": "assistant", "content": "Thank you for that."}
        assert transcript[3] == {"role": "user", "content": "I worked at a startup."}

    def test_rebuild_transcript_skips_empty_fields(self):
        """Turns with empty interviewer_response or user_answer are skipped."""
        from services.interview_engine import _rebuild_transcript

        turns = [
            {"interviewer_response": "", "user_answer": "I am Sameer."},
            {"interviewer_response": "Good answer.", "user_answer": ""},
        ]

        transcript = _rebuild_transcript(turns)

        contents = [m["content"] for m in transcript]
        assert "I am Sameer." in contents
        assert "Good answer." in contents
        assert "" not in contents

    def test_rebuild_transcript_empty_turns(self):
        """Empty turn list must produce empty transcript."""
        from services.interview_engine import _rebuild_transcript

        assert _rebuild_transcript([]) == []

    def test_transcript_grows_after_each_turn(self):
        """After a turn, the stored turn count must increase by 1."""
        from services.interview_engine import run_interview_turn

        stored_call_count = {"count": 0}
        original_store = MagicMock()

        def fake_store(**kwargs):
            stored_call_count["count"] += 1
            return original_store

        p_turns, _ = _mock_store(existing_turns=[])
        p_res_get, p_res_save = _mock_results()

        with _mock_llm(), p_turns, \
             patch("services.interview_engine.store_interview_turn", side_effect=fake_store), \
             p_res_get, p_res_save:
            run_interview_turn(
                company="rakuten",
                language_mode="en",
                duration_mins=15,
                is_demo_mode=False,
                user_message="Hello, my name is Sameer.",
                session_id="test_session_007",
            )

        assert stored_call_count["count"] == 1, "store_interview_turn must be called once per turn"


# ---------------------------------------------------------------------------
# Test 4: results endpoint returns expected JSON
# ---------------------------------------------------------------------------

class TestResultsEndpoint:

    def test_results_returns_required_fields(self):
        from api.interview_results import _build_results_response

        mock_turns = [
            {
                "turn_index": 1,
                "question_id": "Q_LLM_01",
                "question_category": "adaptive",
                "question_prompt": "Please introduce yourself.",
                "interviewer_response": "Hello, welcome to the interview.",
                "user_answer": "I am a software engineer.",
                "answer": "I am a software engineer.",
                "scores": {"wa_teamwork": 7, "loyalty_commitment": 6, "humility": 5, "kaizen_growth": 6, "cultural_fit": 5},
                "timestamp": "2026-01-01T00:00:00Z",
            }
        ]

        mock_results = {
            "overall_scores": {"wa_teamwork": 7.0, "loyalty_commitment": 6.0, "humility": 5.0, "kaizen_growth": 6.0, "cultural_fit": 5.0},
            "final_report": {
                "overall_summary": "Good candidate.",
                "strengths": ["Shows team-first thinking"],
                "improvement_areas": ["Needs stronger loyalty signals"],
                "recommended_focus": "Practice framing answers around group outcomes.",
            },
            "turn_feedback": [],
        }

        with patch("api.interview_results.get_session_turns", return_value=mock_turns), \
             patch("api.interview_results.get_interview_results", return_value=mock_results):
            response = _build_results_response("test_session_008")

        assert "scores" in response
        assert "transcript" in response
        assert "feedback" in response

        scores = response["scores"]
        for dim in ("wa_teamwork", "loyalty_commitment", "humility", "kaizen_growth", "cultural_fit"):
            assert dim in scores

        feedback = response["feedback"]
        assert "strengths" in feedback
        assert "areas_for_improvement" in feedback
        assert "summary" in feedback

    def test_results_transcript_has_roles(self):
        from api.interview_results import _build_results_response

        mock_turns = [
            {
                "turn_index": 1,
                "question_id": "Q_LLM_01",
                "question_category": "adaptive",
                "question_prompt": "Tell me about yourself.",
                "interviewer_response": "Welcome to the interview.",
                "user_answer": "I am Sameer.",
                "answer": "I am Sameer.",
                "scores": {"wa_teamwork": 6, "loyalty_commitment": 6, "humility": 5, "kaizen_growth": 5, "cultural_fit": 5},
                "timestamp": "2026-01-01T00:00:00Z",
            }
        ]

        with patch("api.interview_results.get_session_turns", return_value=mock_turns), \
             patch("api.interview_results.get_interview_results", return_value=None):
            response = _build_results_response("test_session_009")

        transcript = response["transcript"]
        assert isinstance(transcript, list)
        assert len(transcript) > 0

        valid_roles = {"user", "assistant"}
        for msg in transcript:
            assert isinstance(msg, dict)
            assert msg.get("role") in valid_roles
            assert msg.get("content")

    def test_missing_session_returns_error(self):
        from api.interview_results import _build_results_response

        with patch("api.interview_results.get_session_turns", return_value=[]), \
             patch("api.interview_results.get_interview_results", return_value=None):
            response = _build_results_response("nonexistent_session")

        assert "error" in response
        assert "not found" in response["error"].lower()


# ---------------------------------------------------------------------------
# Test 5: time-based completion and safety backstop
# ---------------------------------------------------------------------------

class TestTimedCompletion:

    def test_time_expired_returns_interview_complete(self):
        """When timer_end_epoch is in the past, interview_complete must be True."""
        from services.interview_engine import run_interview_turn, CLOSING_RESPONSE

        past_epoch_ms = int(time.time() * 1000) - 5000  # 5 seconds ago

        p_res_get, p_res_save = _mock_results()

        with patch("services.interview_engine.get_session_turns", return_value=[]), \
             patch("services.interview_engine.store_interview_turn"), \
             patch("services.interview_engine.generate_interview_debrief", return_value={"overall_scores": {}, "turn_evaluations": []}), \
             patch("services.interview_engine.generate_full_feedback_package", return_value={}), \
             p_res_get, p_res_save:
            result = run_interview_turn(
                company="rakuten",
                language_mode="en",
                duration_mins=15,
                is_demo_mode=False,
                user_message="One more answer.",
                session_id="test_session_010",
                timer_end_epoch=past_epoch_ms,
            )

        assert result.get("interview_complete") is True
        assert result.get("interviewer_response") == CLOSING_RESPONSE

    def test_time_not_expired_continues_interview(self):
        """When timer_end_epoch is in the future, interview must continue."""
        from services.interview_engine import run_interview_turn

        future_epoch_ms = int(time.time() * 1000) + 600_000  # 10 minutes from now

        p_turns, p_store = _mock_store()
        p_res_get, p_res_save = _mock_results()

        with _mock_llm(), p_turns, p_store, p_res_get, p_res_save:
            result = run_interview_turn(
                company="rakuten",
                language_mode="en",
                duration_mins=15,
                is_demo_mode=False,
                user_message="My answer.",
                session_id="test_session_011",
                timer_end_epoch=future_epoch_ms,
            )

        assert result.get("interview_complete") is False

    def test_llm_wrapping_up_completes_interview(self):
        """When LLM signals is_wrapping_up=True, interview_complete must be True."""
        from services.interview_engine import run_interview_turn, CLOSING_RESPONSE

        wrapping_up_response = {**VALID_LLM_RESPONSE, "is_wrapping_up": True}

        p_turns, p_store = _mock_store()
        p_res_get, p_res_save = _mock_results()

        with patch("services.interview_engine.call_llm", return_value=wrapping_up_response), \
             p_turns, p_store, \
             patch("services.interview_engine.generate_interview_debrief", return_value={"overall_scores": {}, "turn_evaluations": []}), \
             patch("services.interview_engine.generate_full_feedback_package", return_value={}), \
             p_res_get, p_res_save:
            result = run_interview_turn(
                company="rakuten",
                language_mode="en",
                duration_mins=15,
                is_demo_mode=False,
                user_message="Final answer.",
                session_id="test_session_012",
            )

        assert result.get("interview_complete") is True
        assert result.get("interviewer_response") == CLOSING_RESPONSE
        assert result.get("next_question") == ""

    def test_safety_max_turns_backstop(self):
        """When turn count reaches SAFETY_MAX_TURNS, interview must complete regardless of time."""
        from services.interview_engine import run_interview_turn, SAFETY_MAX_TURNS

        existing_turns = [
            {"turn_index": i, "interviewer_response": "", "user_answer": "answer"}
            for i in range(SAFETY_MAX_TURNS)
        ]

        p_res_get, p_res_save = _mock_results()

        with patch("services.interview_engine.get_session_turns", return_value=existing_turns), \
             patch("services.interview_engine.store_interview_turn"), \
             patch("services.interview_engine.generate_interview_debrief", return_value={"overall_scores": {}, "turn_evaluations": []}), \
             patch("services.interview_engine.generate_full_feedback_package", return_value={}), \
             p_res_get, p_res_save:
            result = run_interview_turn(
                company="rakuten",
                language_mode="en",
                duration_mins=30,
                is_demo_mode=False,
                user_message="Still going.",
                session_id="test_session_013",
                timer_end_epoch=int(time.time() * 1000) + 600_000,  # timer not yet expired
            )

        assert result.get("interview_complete") is True

    def test_safety_max_turns_constant(self):
        from services.interview_engine import SAFETY_MAX_TURNS
        assert SAFETY_MAX_TURNS == 30

    def test_debrief_triggered_on_time_expiry(self):
        """When time expires, run_interview_turn returns interview_complete=True.
        Debrief is scheduled asynchronously by the route handler via BackgroundTasks;
        this test verifies _trigger_debrief calls generate_interview_debrief when invoked."""
        from services.interview_engine import _trigger_debrief

        mock_debrief = patch(
            "services.interview_engine.generate_interview_debrief",
            return_value={"overall_scores": {}, "turn_evaluations": []},
        )
        mock_feedback = patch(
            "services.interview_engine.generate_full_feedback_package",
            return_value={},
        )

        with patch("services.interview_engine.get_session_turns", return_value=[{"question_id": "Q1", "question_category": "adaptive", "question_prompt": "Intro?", "user_answer": "Hello"}]), \
             patch("services.interview_engine.get_interview_results", return_value=None), \
             patch("services.interview_engine.save_interview_results"), \
             mock_debrief as m_debrief, mock_feedback:
            _trigger_debrief("test_session_014")

        m_debrief.assert_called_once()


# ---------------------------------------------------------------------------
# Test 6: duplicate-question guard (_fix_duplicate_question)
# ---------------------------------------------------------------------------

class TestFixDuplicateQuestion:
    """Unit tests for the post-LLM duplicate-question sanitiser."""

    # ------------------------------------------------------------------
    # Direct unit tests of the helper
    # ------------------------------------------------------------------

    def test_identical_strings_clears_response(self):
        """Exact duplicates must clear interviewer_response."""
        from services.interview_engine import _fix_duplicate_question

        resp, q = _fix_duplicate_question(
            "Please introduce yourself.",
            "Please introduce yourself.",
        )
        assert resp == "", "interviewer_response must be cleared on duplicate"
        assert q == "Please introduce yourself."

    def test_highly_similar_strings_clears_response(self):
        """Near-identical paraphrases above the threshold must clear interviewer_response."""
        from services.interview_engine import _fix_duplicate_question

        resp, q = _fix_duplicate_question(
            "Could you introduce yourself?",
            "Could you please introduce yourself?",
        )
        assert resp == "", "Similar question in response must be cleared"
        assert "introduce yourself" in q.lower()

    def test_no_question_mark_in_response_leaves_unchanged(self):
        """If interviewer_response has no '?', nothing should change."""
        from services.interview_engine import _fix_duplicate_question

        original_resp = "Hello Sameer, it's great to meet you today."
        original_q = "Could you introduce yourself and walk me through your background?"

        resp, q = _fix_duplicate_question(original_resp, original_q)

        assert resp == original_resp
        assert q == original_q

    def test_unrelated_question_in_response_leaves_unchanged(self):
        """A '?' in response that is unrelated to next_question must not be cleared."""
        from services.interview_engine import _fix_duplicate_question

        resp = "You mentioned working at a startup — that sounds exciting, right?"
        q = "Can you describe a time you had to meet a tight deadline?"

        result_resp, result_q = _fix_duplicate_question(resp, q)

        assert result_resp == resp, "Unrelated response must not be cleared"
        assert result_q == q

    def test_empty_next_question_leaves_response_unchanged(self):
        """When next_question is empty, response must not be touched."""
        from services.interview_engine import _fix_duplicate_question

        resp = "Please introduce yourself?"
        resp_out, q_out = _fix_duplicate_question(resp, "")

        assert resp_out == resp
        assert q_out == ""

    def test_empty_both_fields_no_error(self):
        """Both fields empty must return both empty without raising."""
        from services.interview_engine import _fix_duplicate_question

        resp, q = _fix_duplicate_question("", "")
        assert resp == ""
        assert q == ""

    # ------------------------------------------------------------------
    # Integration tests via run_interview_turn
    # ------------------------------------------------------------------

    def test_run_turn_clears_duplicate_response(self):
        """run_interview_turn must strip a duplicate question from interviewer_response."""
        from services.interview_engine import run_interview_turn

        duplicate_llm_response = {
            "interviewer_response": "Please introduce yourself.",
            "next_question": "Please introduce yourself.",
            "scores": {
                "wa_teamwork": 5,
                "loyalty_commitment": 5,
                "humility": 5,
                "kaizen_growth": 5,
                "cultural_fit": 5,
            },
            "is_wrapping_up": False,
        }

        p_turns, p_store = _mock_store(existing_turns=[])
        p_res_get, p_res_save = _mock_results()

        with _mock_llm(response=duplicate_llm_response), p_turns, p_store, p_res_get, p_res_save:
            result = run_interview_turn(
                company="rakuten",
                language_mode="en",
                duration_mins=15,
                is_demo_mode=False,
                user_message="Hi, I am Sameer.",
                session_id="test_session_dup_01",
            )

        assert result["interviewer_response"] == "", (
            "interviewer_response must be cleared when it duplicates next_question"
        )
        assert result["next_question"] == "Please introduce yourself."

    def test_run_turn_preserves_clean_response(self):
        """run_interview_turn must NOT alter a well-formed, non-duplicate response."""
        from services.interview_engine import run_interview_turn

        clean_llm_response = {
            "interviewer_response": "Hello Sameer, it's great to meet you today.",
            "next_question": "Could you walk me through your professional background?",
            "scores": {
                "wa_teamwork": 7,
                "loyalty_commitment": 6,
                "humility": 5,
                "kaizen_growth": 6,
                "cultural_fit": 5,
            },
            "is_wrapping_up": False,
        }

        p_turns, p_store = _mock_store(existing_turns=[])
        p_res_get, p_res_save = _mock_results()

        with _mock_llm(response=clean_llm_response), p_turns, p_store, p_res_get, p_res_save:
            result = run_interview_turn(
                company="rakuten",
                language_mode="en",
                duration_mins=15,
                is_demo_mode=False,
                user_message="Hi, I am Sameer.",
                session_id="test_session_dup_02",
            )

        assert result["interviewer_response"] == "Hello Sameer, it's great to meet you today."
        assert result["next_question"] == "Could you walk me through your professional background?"
