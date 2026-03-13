import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import json
import logging
import random
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from data_loader import load_questions, load_rubric, load_company_weights
from services.answer_analyzer import evaluate_answer
from services.dimensions import normalize_dimension
from services.interview_engine import next_question, start_interview
from services.scoring_engine import compute_cultural_fit_score

DURATION_SECONDS = 20 * 60
QUESTIONS_PER_INTERVIEW = 10

LOG_DIR = Path("tests/logs")
ERROR_LOG_PATH = LOG_DIR / "stress_errors.log"
RESULT_LOG_PATH = LOG_DIR / "stress_results.log"

LOGGER = logging.getLogger(__name__)

VALID_DIMENSIONS = {"wa", "kaizen", "loyalty", "humility", "kuuki"}

TEST_ANSWERS = [
    "I collaborate with the team, listen carefully, and support group goals.",
    "I continuously improve processes, ask for feedback, and apply lessons learned.",
    "I respect senior members, adapt communication, and help build team trust.",
    "I value long-term contribution and align my growth with company objectives.",
    "During conflict, I seek shared understanding and solutions that benefit everyone.",
]


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _write_log(path: Path, payload: Dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")


def _build_error_entry(
    interview_number: int,
    question: str,
    dimension: str,
    score: Optional[float],
    final_cultural_fit_score: Optional[float],
    error_message: str,
) -> Dict[str, Any]:
    return {
        "timestamp": _now_iso(),
        "interview_number": interview_number,
        "question": question,
        "dimension": dimension,
        "score": score,
        "final_cultural_fit_score": final_cultural_fit_score,
        "error_message": error_message,
    }


def _validate_question_repeat(question: str, seen_questions: set[str]) -> None:
    if question in seen_questions:
        raise ValueError("Duplicate question detected in one interview")
    seen_questions.add(question)


def _error_category(exc: Exception) -> str:
    if isinstance(exc, KeyError):
        return "KeyError"
    if isinstance(exc, IndexError):
        return "IndexError"
    if isinstance(exc, TypeError):
        return "TypeError"
    if isinstance(exc, ValueError):
        return "ValueError"
    return "Other"


def _increment_error_counter(error_counter: Dict[str, int], exc: Exception) -> None:
    category = _error_category(exc)
    error_counter[category] = error_counter.get(category, 0) + 1


def _run_single_interview(
    interview_number: int,
    company: str,
    error_counter: Dict[str, int],
) -> Tuple[Optional[float], int]:
    error_count = 0
    session: Dict[str, Any] = {"company": company}
    seen_questions: set[str] = set()
    dimension_to_scores: Dict[str, List[float]] = {}
    pending_success_rows: List[Dict[str, Any]] = []

    intro = start_interview(company)
    pending_success_rows.append(
        {
            "timestamp": _now_iso(),
            "interview_number": interview_number,
            "question": str(intro.get("question", "")),
            "dimension": str(intro.get("dimension", "")),
            "score": None,
            "final_cultural_fit_score": None,
            "error_message": "",
        }
    )

    for _ in range(QUESTIONS_PER_INTERVIEW):
        current_question = ""
        current_dimension = ""

        try:
            q = next_question(session)
            if not q or not q.get("question"):
                break

            current_question = str(q.get("question", ""))
            current_dimension = str(q.get("dimension", ""))

            if not current_dimension:
                raise ValueError("Missing dimension in question payload")

            _validate_question_repeat(current_question, seen_questions)

            answer = random.choice(TEST_ANSWERS)

            if current_dimension == "introduction":
                pending_success_rows.append(
                    {
                        "timestamp": _now_iso(),
                        "interview_number": interview_number,
                        "question": current_question,
                        "dimension": current_dimension,
                        "score": None,
                        "final_cultural_fit_score": None,
                        "error_message": "",
                    }
                )
                continue

            try:
                current_dimension = normalize_dimension(current_dimension)
            except ValueError as exc:
                LOGGER.warning(str(exc))
                _write_log(
                    ERROR_LOG_PATH,
                    _build_error_entry(
                        interview_number=interview_number,
                        question=current_question,
                        dimension=current_dimension,
                        score=None,
                        final_cultural_fit_score=None,
                        error_message=f"WARNING: {exc}",
                    ),
                )
                continue

            if current_dimension not in VALID_DIMENSIONS:
                LOGGER.warning("Unexpected normalized dimension: %s", current_dimension)
                continue

            result = evaluate_answer(current_question, current_dimension, answer)
            if result is None:
                raise ValueError("evaluate_answer returned None for non-introduction dimension")

            result_dimension = str(result.get("dimension", ""))
            score = float(result.get("score"))

            if not result_dimension:
                raise ValueError("Missing dimension in evaluation result")
            if not (1.0 <= score <= 4.0):
                raise ValueError(f"Score out of range: {score}")

            dimension_to_scores.setdefault(result_dimension, []).append(score)

            pending_success_rows.append(
                {
                    "timestamp": _now_iso(),
                    "interview_number": interview_number,
                    "question": current_question,
                    "dimension": result_dimension,
                    "score": score,
                    "final_cultural_fit_score": None,
                    "error_message": "",
                }
            )

        except Exception as exc:
            error_count += 1
            _increment_error_counter(error_counter, exc)
            _write_log(
                ERROR_LOG_PATH,
                _build_error_entry(
                    interview_number=interview_number,
                    question=current_question,
                    dimension=current_dimension,
                    score=None,
                    final_cultural_fit_score=None,
                    error_message=f"{type(exc).__name__}: {exc}",
                ),
            )
            # Continue running even if one question fails.
            continue

    avg_scores: Dict[str, float] = {}
    for dim, values in dimension_to_scores.items():
        if values:
            avg_scores[dim] = sum(values) / len(values)

    final_score_value: Optional[float] = None
    try:
        final_result = compute_cultural_fit_score(company, avg_scores)
        final_score_value = float(final_result.get("cultural_fit_score", 0.0))

        if not (0.0 <= final_score_value <= 100.0):
            raise ValueError(f"cultural_fit_score out of range: {final_score_value}")

    except Exception as exc:
        error_count += 1
        _increment_error_counter(error_counter, exc)
        _write_log(
            ERROR_LOG_PATH,
            _build_error_entry(
                interview_number=interview_number,
                question="",
                dimension="",
                score=None,
                final_cultural_fit_score=final_score_value,
                error_message=f"{type(exc).__name__}: {exc}",
            ),
        )

    for row in pending_success_rows:
        row["final_cultural_fit_score"] = final_score_value
        _write_log(RESULT_LOG_PATH, row)

    return final_score_value, error_count


def run_stress_test() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    companies = sorted(load_company_weights().keys())
    if not companies:
        raise RuntimeError("No companies found in company_weights.json")

    start_time = time.monotonic()
    interview_number = 0
    total_errors = 0
    final_scores: List[float] = []
    error_counter: Dict[str, int] = {
        "KeyError": 0,
        "IndexError": 0,
        "TypeError": 0,
        "ValueError": 0,
        "Other": 0,
    }

    while (time.monotonic() - start_time) < DURATION_SECONDS:
        interview_number += 1
        company = random.choice(companies)

        try:
            final_score, interview_errors = _run_single_interview(
                interview_number,
                company,
                error_counter,
            )
            total_errors += interview_errors
            if final_score is not None:
                final_scores.append(final_score)

        except Exception as exc:
            total_errors += 1
            _increment_error_counter(error_counter, exc)
            _write_log(
                ERROR_LOG_PATH,
                _build_error_entry(
                    interview_number=interview_number,
                    question="",
                    dimension="",
                    score=None,
                    final_cultural_fit_score=None,
                    error_message=f"{type(exc).__name__}: Interview-level crash: {exc}",
                ),
            )

        if interview_number % 100 == 0:
            print("Progress:")
            print(f"interviews={interview_number}")
            print(f"errors={total_errors}")
            print(f"KeyError={error_counter['KeyError']}")
            print(f"IndexError={error_counter['IndexError']}")
            print(f"TypeError={error_counter['TypeError']}")
            print(f"ValueError={error_counter['ValueError']}")
            print(f"Other={error_counter['Other']}")

    average_cultural_fit_score = (
        sum(final_scores) / len(final_scores) if final_scores else 0.0
    )

    print("\nFINAL SUMMARY")
    print(f"total_interviews_run: {interview_number}")
    print(f"total_errors: {total_errors}")
    print(f"average_cultural_fit_score: {round(average_cultural_fit_score, 2)}")


if __name__ == "__main__":
    run_stress_test()
