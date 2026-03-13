from typing import Dict, Optional

from models.session import SessionState
from store.interview_results import clear_interview_results
from store.interview_turns import clear_session_turns


sessions: Dict[str, SessionState] = {}


def create_session(state: SessionState) -> None:
    sessions[state.session_id] = state


def get_session(session_id: str) -> Optional[SessionState]:
    return sessions.get(session_id)


def delete_session(session_id: str) -> None:
    sessions.pop(session_id, None)
    clear_session_turns(session_id)
    clear_interview_results(session_id)

