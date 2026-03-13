import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from models.interview_turn import InterviewTurn


LOGGER = logging.getLogger(__name__)

_BASE_DIR = Path(__file__).resolve().parents[1]
_INTERVIEWS_DIR = _BASE_DIR / "data" / "interviews"


def _iso_now() -> str:
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"


def _safe_session_id(session_id: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_-]", "_", str(session_id))
    return cleaned or "default_session"


def _session_file_path(session_id: str) -> Path:
    return _INTERVIEWS_DIR / f"{_safe_session_id(session_id)}.json"


def _load_session_payload(session_id: str) -> Dict[str, Any]:
    file_path = _session_file_path(session_id)
    if not file_path.exists():
        return {"session_id": session_id, "turns": []}

    try:
        with file_path.open("r", encoding="utf-8") as file:
            payload = json.load(file)
        if not isinstance(payload, dict):
            return {"session_id": session_id, "turns": []}
        turns = payload.get("turns", [])
        if not isinstance(turns, list):
            turns = []
        return {
            "session_id": str(payload.get("session_id", session_id)),
            "turns": turns,
        }
    except Exception as exc:
        LOGGER.warning("Failed reading interview session file for '%s': %s", session_id, exc)
        return {"session_id": session_id, "turns": []}


def _write_session_payload(session_id: str, payload: Dict[str, Any]) -> bool:
    file_path = _session_file_path(session_id)
    try:
        _INTERVIEWS_DIR.mkdir(parents=True, exist_ok=True)
        with file_path.open("w", encoding="utf-8") as file:
            json.dump(payload, file, ensure_ascii=False, indent=2)
        return True
    except Exception as exc:
        LOGGER.warning("Failed writing interview session file for '%s': %s", session_id, exc)
        return False


def get_next_turn_index(session_id: str) -> int:
    turns = get_session_turns(session_id)
    return len(turns) + 1


def store_interview_turn(
    session_id: str,
    turn_index: int,
    question_id: str,
    question_category: str,
    question_prompt: str,
    user_answer: str,
    scores: dict,
) -> InterviewTurn:
    score_dict = scores if isinstance(scores, dict) else {}

    turn = InterviewTurn(
        session_id=session_id,
        turn_index=int(turn_index),
        question_id=str(question_id),
        question_category=str(question_category),
        question_prompt=str(question_prompt),
        user_answer=str(user_answer),
        jiko_pr=int(score_dict.get("jiko_pr", 5)),
        shibou_douki=int(score_dict.get("shibou_douki", 5)),
        kyouchousei=int(score_dict.get("kyouchousei", 5)),
        seichou_iyoku=int(score_dict.get("seichou_iyoku", 5)),
        bunka_tekigou=int(score_dict.get("bunka_tekigou", 5)),
        timestamp=_iso_now(),
    )

    payload = _load_session_payload(session_id)
    turns = payload.get("turns", [])

    turns.append(
        {
            "turn_index": turn.turn_index,
            "question_id": turn.question_id,
            "question_category": turn.question_category,
            "question_prompt": turn.question_prompt,
            "user_answer": turn.user_answer,
            "answer": turn.user_answer,
            "scores": {
                "jiko_pr": turn.jiko_pr,
                "shibou_douki": turn.shibou_douki,
                "kyouchousei": turn.kyouchousei,
                "seichou_iyoku": turn.seichou_iyoku,
                "bunka_tekigou": turn.bunka_tekigou,
            },
            "timestamp": turn.timestamp,
        }
    )

    payload["session_id"] = session_id
    payload["turns"] = turns
    _write_session_payload(session_id, payload)
    return turn


def get_session_turns(session_id: str) -> List[Dict[str, Any]]:
    payload = _load_session_payload(session_id)
    raw_turns = payload.get("turns", [])
    if not isinstance(raw_turns, list):
        return []

    def _turn_sort_key(item: Dict[str, Any]) -> int:
        try:
            return int(item.get("turn_index", 0))
        except Exception:
            return 0

    sorted_turns = sorted(raw_turns, key=_turn_sort_key)

    normalized: List[Dict[str, Any]] = []
    for turn in sorted_turns:
        if not isinstance(turn, dict):
            continue
        question_prompt = str(turn.get("question_prompt") or turn.get("question_text") or "")
        user_answer = str(turn.get("user_answer") or turn.get("answer") or "")
        scores = turn.get("scores", {})
        if not isinstance(scores, dict):
            scores = {}

        normalized.append(
            {
                "turn_index": int(turn.get("turn_index", 0) or 0),
                "question_id": str(turn.get("question_id", "")),
                "question_category": str(turn.get("question_category", "")),
                "question_prompt": question_prompt,
                "user_answer": user_answer,
                "answer": user_answer,
                "scores": {
                    "jiko_pr": int(scores.get("jiko_pr", 5)),
                    "shibou_douki": int(scores.get("shibou_douki", 5)),
                    "kyouchousei": int(scores.get("kyouchousei", 5)),
                    "seichou_iyoku": int(scores.get("seichou_iyoku", 5)),
                    "bunka_tekigou": int(scores.get("bunka_tekigou", 5)),
                },
                "timestamp": str(turn.get("timestamp", "")),
            }
        )

    return normalized


def clear_session_turns(session_id: str) -> None:
    file_path = _session_file_path(session_id)
    try:
        if file_path.exists():
            file_path.unlink()
    except Exception as exc:
        LOGGER.warning("Failed deleting interview session file for '%s': %s", session_id, exc)
