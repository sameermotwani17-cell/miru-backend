"""
Tests for the MIRU adaptive interview engine.

Run with: pytest tests/test_interview_engine.py -v
"""
import sys
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

        existing_turns = [{"turn_index": i, "interviewer_response": "", "user_answer": "answer"} for i in range(MAX_TURNS)]

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
                session_id="test_session_010",
            )

        assert result.get("interview_complete") is True

    def test_last_turn_sets_interview_complete(self):
        """The turn that hits MAX_TURNS should mark interview_complete = True."""
        from services.interview_engine import run_interview_turn, MAX_TURNS, CLOSING_RESPONSE

        existing_turns = [
            {"turn_index": i, "interviewer_response": "Good.", "user_answer": "answer"}
            for i in range(MAX_TURNS - 1)
        ]

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
                session_id="test_session_011",
            )

        assert result.get("interview_complete") is True
        assert result.get("next_question") == CLOSING_RESPONSE

    def test_max_turns_constant_is_10(self):
        from services.interview_engine import MAX_TURNS
        assert MAX_TURNS == 10
