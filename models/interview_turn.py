from dataclasses import dataclass


@dataclass
class InterviewTurn:
    session_id: str
    turn_index: int
    question_id: str
    question_category: str
    question_prompt: str
    user_answer: str
    jiko_pr: int
    shibou_douki: int
    kyouchousei: int
    seichou_iyoku: int
    bunka_tekigou: int
    timestamp: str
