from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class SessionState:
    session_id: str
    user_name: str
    target_role: str
    company: str
    language_mode: str
    duration_mins: int
    timer_end_epoch: int

    conversation_history: List[Any] = field(default_factory=list)
    turn_count: int = 0
    question_ids_used: List[str] = field(default_factory=list)

    running_scores: Dict[str, float] = field(
        default_factory=lambda: {
            "jiko_pr": 0.0,
            "shibou_douki": 0.0,
            "kyouchousei": 0.0,
            "seichou_iyoku": 0.0,
            "bunka_tekigou": 0.0,
        }
    )

    cv_context: Optional[str] = None

