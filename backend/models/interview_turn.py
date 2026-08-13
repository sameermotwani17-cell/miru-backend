from dataclasses import dataclass


@dataclass
class InterviewTurn:
    session_id: str
    turn_index: int
    question_id: str
    question_category: str
    question_prompt: str
    user_answer: str
    wa_teamwork: int
    loyalty_commitment: int
    humility: int
    kaizen_growth: int
    cultural_fit: int
    timestamp: str
