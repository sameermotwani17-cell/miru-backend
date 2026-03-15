#!/usr/bin/env python3
"""
MIRU Hackathon Pipeline Simulation Test
Simulates a full interview from session start → turn loop → debrief retrieval.
Run from the miru-backend root:
    python tests/simulate_hackathon_test.py
"""

import json
import sys
import time
import uuid
import urllib.request
import urllib.error

BASE = "http://localhost:8000"
SESSION_ID = "hackathon_test_" + uuid.uuid4().hex[:8]
COMPANY = "toyota"
LANGUAGE_MODE = "en"
DURATION_MINS = 3

ANSWERS = [
    "Hello, my name is Sameer and I am excited to interview today.",
    "I worked on an AI waste sorting project with my team.",
    "A challenge we faced was coordinating data collection across the group.",
    "I learned the importance of teamwork and continuous iteration.",
    "I want to grow with a company long term and contribute to its mission.",
]

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
RESET = "\033[0m"
BOLD = "\033[1m"


def ok(msg):
    print(f"  {GREEN}✓{RESET} {msg}")


def fail(msg):
    print(f"  {RED}✗ {msg}{RESET}")


def warn(msg):
    print(f"  {YELLOW}⚠ {msg}{RESET}")


def section(title):
    print(f"\n{BOLD}{CYAN}{'─' * 60}{RESET}")
    print(f"{BOLD}{CYAN}  {title}{RESET}")
    print(f"{BOLD}{CYAN}{'─' * 60}{RESET}")


def post(path, body):
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        f"{BASE}{path}",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())
    except Exception as exc:
        return 0, {"error": str(exc)}


def get(path):
    req = urllib.request.Request(f"{BASE}{path}", method="GET")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())
    except Exception as exc:
        return 0, {"error": str(exc)}


def check_turn_response(resp, turn_num):
    required = ["interview_complete", "interviewer_response", "next_question", "question_id", "scores"]
    missing = [f for f in required if f not in resp]
    if missing:
        fail(f"Turn {turn_num}: missing fields: {missing}")
        return False

    scores = resp.get("scores", {})
    score_dims = ["wa_teamwork", "loyalty_commitment", "humility", "kaizen_growth", "cultural_fit"]
    missing_dims = [d for d in score_dims if d not in scores]
    if missing_dims:
        warn(f"Turn {turn_num}: scores missing dims: {missing_dims}")
    else:
        ok(f"Turn {turn_num}: all score dimensions present")

    ok(f"Turn {turn_num}: all required fields present")
    ok(f"Turn {turn_num}: interview_complete={resp['interview_complete']}")
    if resp.get("next_question"):
        print(f"    next_question: {resp['next_question'][:80]}...")
    return True


# ── STEP 1: Session Start ────────────────────────────────────────────────────
section("STEP 1 — Session Start")

status, resp = post("/api/session/start", {
    "user_name": "Sameer",
    "target_role": "Software Engineer",
    "company": COMPANY,
    "language_mode": LANGUAGE_MODE,
    "duration_mins": DURATION_MINS,
    "cv_context": None,
})

if status == 200 and "session_id" in resp:
    session_id = resp["session_id"]
    ok(f"Session created: {session_id}")
    ok(f"timer_end_epoch: {resp.get('timer_end_epoch')}")
else:
    warn(f"Session start returned {status} — using hardcoded test ID: {SESSION_ID}")
    session_id = SESSION_ID


# ── STEP 2: Interview Turn Loop ──────────────────────────────────────────────
section("STEP 2 — Interview Turn Loop")

interview_complete = False
turn_num = 0

# First turn: "start" message to kick off the interview
print(f"\n  [Turn 0 — start]")
status, resp = post("/api/interview/turn", {
    "session_id": session_id,
    "company": COMPANY,
    "user_answer": "start",
})

if status != 200:
    fail(f"Start turn failed: HTTP {status} — {resp}")
    sys.exit(1)

check_turn_response(resp, 0)

if resp.get("interview_complete") and resp.get("next_question") is None:
    warn("Interview completed immediately on start turn — possible logic issue")
    interview_complete = True

# Answer turns
for i, answer in enumerate(ANSWERS):
    if interview_complete:
        break

    turn_num = i + 1
    print(f"\n  [Turn {turn_num}]  answer: \"{answer[:60]}...\"")
    status, resp = post("/api/interview/turn", {
        "session_id": session_id,
        "company": COMPANY,
        "user_answer": answer,
    })

    if status != 200:
        fail(f"Turn {turn_num} failed: HTTP {status} — {resp}")
        sys.exit(1)

    ok(f"Turn {turn_num}: HTTP {status}")
    check_turn_response(resp, turn_num)

    if resp.get("interview_complete") and resp.get("next_question") is None:
        ok(f"Turn {turn_num}: interview_complete=True received ✓")
        interview_complete = True
        break

    time.sleep(0.3)  # brief pause between turns


# ── STEP 3/4: Completion Check ───────────────────────────────────────────────
section("STEP 3/4 — Completion Validation")

if interview_complete:
    ok("interview_complete = True confirmed")
else:
    warn("interview_complete never reached after all answers — sending force_complete")
    status, resp = post("/api/interview/turn", {
        "session_id": session_id,
        "company": COMPANY,
        "user_answer": "[force complete]",
        "force_complete": True,
    })
    if status == 200 and resp.get("interview_complete"):
        ok("force_complete worked — interview_complete = True")
    else:
        fail(f"force_complete failed: HTTP {status} — {resp}")


# ── STEP 5: Debrief Generation ───────────────────────────────────────────────
section("STEP 5 — Debrief / Results Check")

print(f"\n  Polling GET /api/interview/results?session_id={session_id}")
print("  (waiting up to 60 s for debrief generation)...")

results = None
for attempt in range(20):
    time.sleep(3)
    status, data = get(f"/api/interview/results?session_id={session_id}")
    if status == 200 and data.get("status") != "results_not_ready":
        results = data
        ok(f"Results ready after {(attempt + 1) * 3}s (attempt {attempt + 1})")
        break
    print(f"    attempt {attempt + 1}: status={status} response_status={data.get('status', '?')}")

if not results:
    fail("Results not available after 60s polling")
    sys.exit(1)


# ── STEP 6: DB Persistence / Results Fields ──────────────────────────────────
section("STEP 6 — Results Field Validation")

expected_fields = ["radar_scores", "turn_feedback", "feedback", "hiring_signal"]
for field in expected_fields:
    if field in results and results[field] is not None:
        ok(f"'{field}' present")
    else:
        fail(f"'{field}' missing or null")

radar = results.get("radar_scores", {})
score_dims = ["wa_teamwork", "loyalty_commitment", "humility", "kaizen_growth", "cultural_fit"]
for dim in score_dims:
    val = radar.get(dim)
    if val is not None:
        ok(f"  radar_scores.{dim} = {val}")
    else:
        fail(f"  radar_scores.{dim} missing")

turn_feedback = results.get("turn_feedback", [])
if isinstance(turn_feedback, list) and len(turn_feedback) > 0:
    ok(f"turn_feedback: {len(turn_feedback)} items")
    first = turn_feedback[0] if isinstance(turn_feedback[0], dict) else {}
    for key in ["question", "answer", "feedback", "better_example"]:
        if first.get(key):
            ok(f"  turn_feedback[0].{key} populated")
        else:
            fail(f"  turn_feedback[0].{key} EMPTY — coaching card will show fallback")
else:
    fail("turn_feedback is empty — coaching breakdown section will be hidden")

hiring_signal = results.get("hiring_signal", "")
if hiring_signal:
    ok(f"hiring_signal: '{hiring_signal}'")
else:
    warn("hiring_signal empty")


# ── STEP 7: Frontend Key Mapping ─────────────────────────────────────────────
section("STEP 7 — Frontend Compatibility Check")

# Check radar_scores vs scores
if "radar_scores" in results:
    ok("radar_scores key present (frontend reads radar_scores ?? scores)")
elif "scores" in results:
    warn("Only 'scores' present — frontend will fall back to scores key")
else:
    fail("Neither radar_scores nor scores present — radar chart will be empty")

# Check feedback structure
feedback = results.get("feedback")
if isinstance(feedback, dict):
    ok(f"feedback is dict with keys: {list(feedback.keys())}")
    for k in ["summary", "strengths", "areas_for_improvement"]:
        if feedback.get(k):
            ok(f"  feedback.{k} populated")
        else:
            warn(f"  feedback.{k} empty")
elif isinstance(feedback, str) and feedback:
    ok("feedback is string (will render as plain text)")
else:
    fail("feedback is empty — 'Interviewer Feedback' section will be blank")

# Check transcript format
transcript = results.get("transcript", [])
if transcript and isinstance(transcript, list):
    first_t = transcript[0] if isinstance(transcript[0], dict) else {}
    if "role" in first_t and "text" in first_t:
        ok("transcript has role/text format (TranscriptTurn)")
    elif "question" in first_t or "answer" in first_t:
        ok("transcript has question/answer format (coaching format)")
    else:
        warn(f"transcript[0] has unexpected keys: {list(first_t.keys())}")
else:
    warn("transcript empty")


# ── Summary ──────────────────────────────────────────────────────────────────
section("SUMMARY")
print(f"  session_id:    {session_id}")
print(f"  turns_sent:    {turn_num + 1}")
print(f"  completed:     {interview_complete}")
print(f"  hiring_signal: {results.get('hiring_signal', 'N/A')}")
radar = results.get("radar_scores", {})
if radar:
    avg = round(sum(radar.values()) / len(radar), 2)
    print(f"  avg_score:     {avg}/10")
print()
print(f"  {GREEN}{BOLD}Pipeline test complete.{RESET}")
print()
