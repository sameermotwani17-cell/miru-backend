import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional


LOGGER = logging.getLogger(__name__)

_results_store: Dict[str, Dict[str, Any]] = {}

_BASE_DIR = Path(__file__).resolve().parents[1]
_RESULTS_DIR = _BASE_DIR / "data" / "results"


def save_interview_results(session_id: str, results: Dict[str, Any]) -> None:
    sid = str(session_id)
    _results_store[sid] = dict(results)

    try:
        _RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        file_path = _RESULTS_DIR / f"{sid}.json"
        with file_path.open("w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
    except Exception as exc:
        LOGGER.warning("[RESULTS] Failed to persist results to disk for session %s: %s", sid, exc)


def get_interview_results(session_id: str) -> Optional[Dict[str, Any]]:
    sid = str(session_id)

    # Fast path: in-memory
    cached = _results_store.get(sid)
    if isinstance(cached, dict):
        return dict(cached)

    # Slow path: load from disk
    file_path = _RESULTS_DIR / f"{sid}.json"
    if file_path.exists():
        try:
            with file_path.open("r", encoding="utf-8") as f:
                loaded = json.load(f)
            if isinstance(loaded, dict):
                _results_store[sid] = loaded
                return dict(loaded)
        except Exception as exc:
            LOGGER.warning("[RESULTS] Failed to load results from disk for session %s: %s", sid, exc)

    return None


def clear_interview_results(session_id: str) -> None:
    sid = str(session_id)
    _results_store.pop(sid, None)

    file_path = _RESULTS_DIR / f"{sid}.json"
    try:
        if file_path.exists():
            file_path.unlink()
    except Exception as exc:
        LOGGER.warning("[RESULTS] Failed to delete results file for session %s: %s", sid, exc)
