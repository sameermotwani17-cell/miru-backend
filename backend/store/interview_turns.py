"""Interview turn persistence.

Turns used to be written to data/interviews/{session_id}.json. On Vercel the
deployment filesystem is read-only apart from /tmp, and /tmp is per-instance
and ephemeral, so file-backed turns would either fail to write or vanish
between requests. The transcript is the backend's single source of truth for
rebuilding conversation history (the anti-injection design in the README
depends on it), so it has to be durable: it lives in Postgres as one JSONB
document per session, preserving the exact shape the previous file format
used.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List

from models.interview_turn import InterviewTurn
from services.score_dimensions import SCORE_DIMENSIONS
from store.db import cursor, is_db_configured

LOGGER = logging.getLogger(__name__)

# Fallback only, so local runs work without a database.
_memory: Dict[str, List[Dict[str, Any]]] = {}


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace(
        "+00:00", "Z"
    )


def _read_turns(session_id: str) -> List[Dict[str, Any]]:
    sid = str(session_id)

    if is_db_configured():
        try:
            with cursor() as cur:
                cur.execute(
                    "SELECT turns FROM interview_turns WHERE session_id = %s", (sid,)
                )
                row = cur.fetchone()
            if row is not None:
                turns = row["turns"]
                if isinstance(turns, str):
                    turns = json.loads(turns)
                if isinstance(turns, list):
                    return turns
        except Exception as exc:  # noqa: BLE001
            LOGGER.error("[TURNS] DB read failed for %s: %s", sid, exc)

    return list(_memory.get(sid, []))


def _write_turns(session_id: str, turns: List[Dict[str, Any]]) -> None:
    sid = str(session_id)
    _memory[sid] = turns

    if not is_db_configured():
        return
    try:
        with cursor() as cur:
            cur.execute(
                "INSERT INTO interview_turns (session_id, turns) VALUES (%s, %s) "
                "ON CONFLICT (session_id) DO UPDATE SET turns = EXCLUDED.turns, "
                "updated_at = now()",
                (sid, json.dumps(turns, ensure_ascii=False)),
            )
    except Exception as exc:  # noqa: BLE001
        LOGGER.error("[TURNS] DB write failed for %s: %s", sid, exc)


def get_next_turn_index(session_id: str) -> int:
    return len(_read_turns(session_id)) + 1


def store_interview_turn(
    session_id: str,
    turn_index: int,
    question_id: str,
    question_category: str,
    question_prompt: str,
    answer: str,
    scores: dict,
    interviewer_response: str = "",
    question: str = "",
    score: float | None = None,
    feedback: str = "",
    better_example: str = "",
) -> InterviewTurn:
    score_dict = scores if isinstance(scores, dict) else {}
    if score is None:
        score_values = [
            float(score_dict.get(dim, 5))
            for dim in SCORE_DIMENSIONS
            if isinstance(score_dict.get(dim, 5), (int, float))
        ]
        score = round(sum(score_values) / len(score_values), 2) if score_values else 5.0

    turn = InterviewTurn(
        session_id=session_id,
        turn_index=int(turn_index),
        question_id=str(question_id),
        question_category=str(question_category),
        question_prompt=str(question_prompt),
        user_answer=str(answer),
        wa_teamwork=int(score_dict.get("wa_teamwork", 5)),
        loyalty_commitment=int(score_dict.get("loyalty_commitment", 5)),
        humility=int(score_dict.get("humility", 5)),
        kaizen_growth=int(score_dict.get("kaizen_growth", 5)),
        cultural_fit=int(score_dict.get("cultural_fit", 5)),
        timestamp=_iso_now(),
    )

    turns = _read_turns(session_id)
    turns.append(
        {
            "turn_index": turn.turn_index,
            "question_id": turn.question_id,
            "question_category": turn.question_category,
            "question_prompt": turn.question_prompt,
            "interviewer_response": str(interviewer_response),
            "question": str(question),
            "answer": turn.user_answer,
            "score": float(score),
            "feedback": str(feedback or ""),
            "better_example": str(better_example or ""),
            "scores": {
                "wa_teamwork": turn.wa_teamwork,
                "loyalty_commitment": turn.loyalty_commitment,
                "humility": turn.humility,
                "kaizen_growth": turn.kaizen_growth,
                "cultural_fit": turn.cultural_fit,
            },
            "timestamp": turn.timestamp,
        }
    )
    _write_turns(session_id, turns)
    return turn


def get_session_turns(session_id: str) -> List[Dict[str, Any]]:
    raw_turns = _read_turns(session_id)

    def _turn_sort_key(item: Dict[str, Any]) -> int:
        try:
            return int(item.get("turn_index", 0))
        except Exception:  # noqa: BLE001
            return 0

    sorted_turns = sorted(
        (t for t in raw_turns if isinstance(t, dict)), key=_turn_sort_key
    )

    normalized: List[Dict[str, Any]] = []
    for turn in sorted_turns:
        question_prompt = str(turn.get("question_prompt") or turn.get("question_text") or "")
        answer = str(turn.get("answer") or turn.get("user_answer") or "")
        scores = turn.get("scores", {})
        if not isinstance(scores, dict):
            scores = {}

        normalized.append(
            {
                "turn_index": int(turn.get("turn_index", 0) or 0),
                "question_id": str(turn.get("question_id", "")),
                "question_category": str(turn.get("question_category", "")),
                "question": str(turn.get("question", "")),
                "question_prompt": question_prompt,
                "interviewer_response": str(turn.get("interviewer_response", "")),
                "answer": answer,
                # Compatibility alias for older call sites still expecting user_answer.
                "user_answer": answer,
                "score": float(turn.get("score", 5.0) or 5.0),
                "feedback": str(turn.get("feedback", "")),
                "better_example": str(turn.get("better_example", "")),
                "scores": {
                    "wa_teamwork": int(scores.get("wa_teamwork", 5)),
                    "loyalty_commitment": int(scores.get("loyalty_commitment", 5)),
                    "humility": int(scores.get("humility", 5)),
                    "kaizen_growth": int(scores.get("kaizen_growth", 5)),
                    "cultural_fit": int(scores.get("cultural_fit", 5)),
                },
                "timestamp": str(turn.get("timestamp", "")),
            }
        )

    return normalized


def clear_session_turns(session_id: str) -> None:
    sid = str(session_id)
    _memory.pop(sid, None)

    if not is_db_configured():
        return
    try:
        with cursor() as cur:
            cur.execute("DELETE FROM interview_turns WHERE session_id = %s", (sid,))
    except Exception as exc:  # noqa: BLE001
        LOGGER.error("[TURNS] DB delete failed for %s: %s", sid, exc)
