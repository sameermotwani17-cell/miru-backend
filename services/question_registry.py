from typing import Dict, Optional


QUESTIONS = {
    "Q_STD_01": {
        "category": "intro",
        "prompt": "Please introduce yourself.",
    },
    "Q_STD_02": {
        "category": "motivation",
        "prompt": "Why are you interested in working at this company?",
    },
    "Q_BEHAVIOR_01": {
        "category": "behavior",
        "prompt": "Tell me about a time you faced a difficult challenge.",
    },
    "Q_TEAM_01": {
        "category": "teamwork",
        "prompt": "Describe a situation where you had to work closely with others.",
    },
    "Q_FAILURE_01": {
        "category": "self_reflection",
        "prompt": "Tell me about a failure and what you learned from it.",
    },
    "Q_CLOSING_01": {
        "category": "closing",
        "prompt": "Do you have any final thoughts about why you would be a good fit?",
    },
}


INTERVIEW_FLOW = [
    "Q_STD_01",
    "Q_STD_02",
    "Q_BEHAVIOR_01",
    "Q_TEAM_01",
    "Q_FAILURE_01",
    "Q_CLOSING_01",
]


def get_next_question(turn_index: int) -> Optional[Dict[str, str]]:
    if turn_index >= len(INTERVIEW_FLOW):
        return None

    question_id = INTERVIEW_FLOW[turn_index]
    question = QUESTIONS[question_id]

    return {
        "question_id": question_id,
        "category": question["category"],
        "prompt": question["prompt"],
    }
