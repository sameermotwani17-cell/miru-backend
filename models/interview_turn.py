from dataclasses import dataclass


@dataclass
class InterviewTurn:
    session_id: str
    turn_index: int
    question_id: str
    question_category: str
    question_prompt: str
    user_answer: str
    communication: int
    clarity: int
    cultural_fit: int
    problem_solving: int
    timestamp: str
