"""
Pipeline debug script — runs a minimal 3-turn interview then fetches results
and prints every transcript entry so we can see question/answer alignment.
"""
import json
import logging
import sys
import uuid

# ── logging setup ──────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.DEBUG,
    format="%(levelname)s %(name)s — %(message)s",
    stream=sys.stdout,
)

# ── imports ────────────────────────────────────────────────────────────────
from services.interview_engine import run_interview_turn, _trigger_debrief
from api.interview_results import _build_results_response
from store.interview_turns import get_session_turns, clear_session_turns
from store.interview_results import clear_interview_results

SESSION_ID = f"debug_{uuid.uuid4().hex[:8]}"

TURNS = [
    "Hi, I am Samee.",
    "I have been working at a software company for three years, focusing on backend development.",
    "My greatest strength is my ability to collaborate closely with teammates.",
]

print("\n" + "=" * 60)
print(f"SESSION: {SESSION_ID}")
print("=" * 60)

# ── clear any stale state ──────────────────────────────────────────────────
clear_session_turns(SESSION_ID)

# ── run turns ─────────────────────────────────────────────────────────────
for i, msg in enumerate(TURNS):
    print(f"\n>>> TURN {i + 1}: user_message = {msg!r}")
    result = run_interview_turn(
        company="rakuten",
        language_mode="en",
        duration_mins=15,
        is_demo_mode=True,
        user_message=msg,
        session_id=SESSION_ID,
        max_questions=len(TURNS),
    )
    print(f"    interview_complete = {result.get('interview_complete')}")
    print(f"    next_question      = {result.get('next_question')!r}")

# ── inspect raw stored turns ───────────────────────────────────────────────
print("\n" + "=" * 60)
print("RAW STORED TURNS (from get_session_turns):")
print("=" * 60)
turns = get_session_turns(SESSION_ID)
for t in turns:
    print(json.dumps({
        "turn_index": t.get("turn_index"),
        "question":   t.get("question"),
        "answer":     t.get("answer"),
        "score":      t.get("score"),
        "feedback":   t.get("feedback"),
        "better_example": t.get("better_example"),
    }, ensure_ascii=False, indent=2))

# ── trigger debrief synchronously ─────────────────────────────────────────
print("\n" + "=" * 60)
print("TRIGGERING DEBRIEF...")
print("=" * 60)
_trigger_debrief(SESSION_ID)

# ── fetch results ──────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("RESULTS TRANSCRIPT (from _build_results_response):")
print("=" * 60)
try:
    response = _build_results_response(SESSION_ID)
    for entry in response.get("transcript", []):
        print(json.dumps(entry, ensure_ascii=False, indent=2))
    print("\nHiring signal:", response.get("hiring_signal"))
except KeyError as e:
    print(f"Results not ready: {e}")

# ── cleanup ────────────────────────────────────────────────────────────────
clear_session_turns(SESSION_ID)
