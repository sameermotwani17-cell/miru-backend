"""
Tests for the MIRU adaptive interview engine.

Run with: pytest tests/test_interview_engine.py -v
"""
import sys
import os
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
        "communication": 7,
        "clarity": 6,
        "cultural_fit": 5,
        "problem_solving": 6,
    },
    "is_wrapping_up": False,
}


def _mock_llm(response: Dict[str, Any] = None):
    """Return a patch object that replaces call_llm with a mock."""
    return patch(
        "services.interview_engine.call_llm",
        return_value=response or VALID_LLM_RESPONSE,
    )


def _mock_store(existing_turns: List[Dict] = None):
    """Patch get_session_turns and store_interview_turn."""
    return (
        patch("services.interview_engine.get_session_turns", return_value=existing_turns or []),
        patch("services.interview_engine.store_interview_turn", return_value=MagicMock()),
    )


def _mock_results():
    """Patch get_interview_results / save_interview_results."""
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
                conversation_history=[],
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
                conversation_history=[],
                session_id="test_session_002",
            )

        scores = result["scores"]
        assert isinstance(scores, dict)
        for dim in ("communication", "clarity", "cultural_fit", "problem_solving"):
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
                conversation_history=[],
                session_id="test_session_003",
            )

        assert result["interview_complete"] is False


# ---------------------------------------------------------------------------
# Test 2: messages sent to LLM always contain role/content
# ---------------------------------------------------------------------------

class TestLLMMessageIntegrity:

    def test_malformed_history_filtered_out(self):
        """Malformed messages (missing role/content) must not reach call_llm."""
        from services.interview_engine import run_interview_turn

        malformed_history = [
            {"role": "user", "content": "valid message"},
            {"content": "no role here"},          # missing role
            {"role": "assistant"},                 # missing content
            {"role": "invalid_role", "content": "bad role"},
            None,                                  # not a dict
            "just a string",                       # not a dict
        ]

        captured_calls: List[Dict] = []

        def fake_llm(system_prompt, conversation, user_message):
            captured_calls.append({"conversation": list(conversation)})
            return VALID_LLM_RESPONSE

        p_turns, p_store = _mock_store()
        p_res_get, p_res_save = _mock_results()

        with patch("services.interview_engine.call_llm", side_effect=fake_llm), \
             p_turns, p_store, p_res_get, p_res_save:
            run_interview_turn(
                company="rakuten",
                language_mode="en",
                duration_mins=15,
                is_demo_mode=False,
                user_message="My answer.",
                conversation_history=malformed_history,
                session_id="test_session_004",
            )

        assert captured_calls, "LLM must have been called"
        sent_conversation = captured_calls[0]["conversation"]

        valid_roles = {"system", "user", "assistant"}
        for msg in sent_conversation:
            assert isinstance(msg, dict), f"Non-dict message reached LLM: {msg}"
            assert "role" in msg, f"Message missing 'role': {msg}"
            assert "content" in msg, f"Message missing 'content': {msg}"
            assert msg["role"] in valid_roles, f"Invalid role '{msg['role']}' reached LLM"
            assert msg["content"], f"Empty content reached LLM: {msg}"

    def test_valid_history_passes_through(self):
        """Valid history messages must reach call_llm unchanged."""
        from services.interview_engine import run_interview_turn

        valid_history = [
            {"role": "assistant", "content": "Hello, please introduce yourself."},
            {"role": "user", "content": "I am a software engineer."},
        ]

        captured_calls: List[Dict] = []

        def fake_llm(system_prompt, conversation, user_message):
            captured_calls.append({"conversation": list(conversation)})
            return VALID_LLM_RESPONSE

        p_turns, p_store = _mock_store()
        p_res_get, p_res_save = _mock_results()

        with patch("services.interview_engine.call_llm", side_effect=fake_llm), \
             p_turns, p_store, p_res_get, p_res_save:
            run_interview_turn(
                company="rakuten",
                language_mode="en",
                duration_mins=15,
                is_demo_mode=False,
                user_message="Follow-up answer.",
                conversation_history=valid_history,
                session_id="test_session_005",
            )

        sent_conversation = captured_calls[0]["conversation"]
        # Both valid history messages should appear in the conversation
        roles_contents = [(m["role"], m["content"]) for m in sent_conversation]
        assert ("assistant", "Hello, please introduce yourself.") in roles_contents
        assert ("user", "I am a software engineer.") in roles_contents


# ---------------------------------------------------------------------------
# Test 3: transcript grows correctly after each turn
# ---------------------------------------------------------------------------

class TestTranscriptGrowth:

    def test_conversation_history_grows_after_turn(self):
        from services.interview_engine import run_interview_turn

        conversation_history = []
        p_turns, p_store = _mock_store()
        p_res_get, p_res_save = _mock_results()

        with _mock_llm(), p_turns, p_store, p_res_get, p_res_save:
            run_interview_turn(
                company="rakuten",
                language_mode="en",
                duration_mins=15,
                is_demo_mode=False,
                user_message="Hello, my name is Sameer.",
                conversation_history=conversation_history,
                session_id="test_session_006",
            )

        # Must have: user message + interviewer_response + next_question
        assert len(conversation_history) >= 2, "Transcript must grow after each turn"
        roles = [m["role"] for m in conversation_history]
        assert "user" in roles
        assert "assistant" in roles

    def test_conversation_roles_are_valid(self):
        from services.interview_engine import run_interview_turn

        conversation_history = []
        p_turns, p_store = _mock_store()
        p_res_get, p_res_save = _mock_results()

        with _mock_llm(), p_turns, p_store, p_res_get, p_res_save:
            run_interview_turn(
                company="rakuten",
                language_mode="en",
                duration_mins=15,
                is_demo_mode=False,
                user_message="I enjoy collaborative environments.",
                conversation_history=conversation_history,
                session_id="test_session_007",
            )

        valid_roles = {"user", "assistant", "system"}
        for msg in conversation_history:
            assert isinstance(msg, dict)
            assert msg.get("role") in valid_roles
            assert msg.get("content")


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
                "scores": {"communication": 7, "clarity": 6, "cultural_fit": 5, "problem_solving": 6},
                "timestamp": "2026-01-01T00:00:00Z",
            }
        ]

        mock_results = {
            "overall_scores": {"communication": 7.0, "clarity": 6.0, "cultural_fit": 5.0, "problem_solving": 6.0},
            "final_report": {
                "overall_summary": "Good candidate.",
                "strengths": ["Clear communication"],
                "improvement_areas": ["Needs more concrete examples"],
                "recommended_focus": "Practice STAR method.",
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
        for dim in ("communication", "clarity", "cultural_fit", "problem_solving"):
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
                "scores": {"communication": 6, "clarity": 6, "cultural_fit": 5, "problem_solving": 5},
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
# Test 5: interview stops after MAX_TURNS
# ---------------------------------------------------------------------------

class TestMaxTurns:

    def test_interview_complete_at_max_turns(self):
        from services.interview_engine import run_interview_turn, MAX_TURNS

        # Simulate having already completed MAX_TURNS
        existing_turns = [{"turn_index": i} for i in range(MAX_TURNS)]

        p_res_get, p_res_save = _mock_results()

        with patch("services.interview_engine.get_session_turns", return_value=existing_turns), \
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
                conversation_history=[],
                session_id="test_session_010",
            )

        assert result.get("interview_complete") is True

    def test_last_turn_sets_interview_complete(self):
        """The turn that hits MAX_TURNS - 1 should mark interview_complete = True."""
        from services.interview_engine import run_interview_turn, MAX_TURNS, CLOSING_RESPONSE

        # One turn short of the limit
        existing_turns = [{"turn_index": i} for i in range(MAX_TURNS - 1)]

        llm_response = {**VALID_LLM_RESPONSE, "is_wrapping_up": False}

        p_res_get, p_res_save = _mock_results()

        with patch("services.interview_engine.call_llm", return_value=llm_response), \
             patch("services.interview_engine.get_session_turns", return_value=existing_turns), \
             patch("services.interview_engine.store_interview_turn"), \
             patch("services.interview_engine.generate_interview_debrief", return_value={"overall_scores": {}, "turn_evaluations": []}), \
             patch("services.interview_engine.generate_full_feedback_package", return_value={}), \
             p_res_get, p_res_save:
            result = run_interview_turn(
                company="rakuten",
                language_mode="en",
                duration_mins=15,
                is_demo_mode=False,
                user_message="Final answer.",
                conversation_history=[],
                session_id="test_session_011",
            )

        assert result.get("interview_complete") is True
        assert result.get("next_question") == CLOSING_RESPONSE

    def test_max_turns_constant_is_10(self):
        from services.interview_engine import MAX_TURNS
        assert MAX_TURNS == 10
