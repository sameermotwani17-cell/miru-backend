from typing import Any, Dict, Optional


_results_store: Dict[str, Dict[str, Any]] = {}


def save_interview_results(session_id: str, results: Dict[str, Any]) -> None:
    _results_store[str(session_id)] = dict(results)


def get_interview_results(session_id: str) -> Optional[Dict[str, Any]]:
    cached = _results_store.get(str(session_id))
    return dict(cached) if isinstance(cached, dict) else None


def clear_interview_results(session_id: str) -> None:
    _results_store.pop(str(session_id), None)
