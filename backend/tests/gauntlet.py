#!/usr/bin/env python3
"""MIRU gauntlet — run the README's documented lifecycle end to end.

The README makes a specific set of promises about how the frontend drives the
backend. This harness turns each of those promises into an assertion and runs
them in a loop against a live server until they all pass or the round budget
is exhausted, so "the README is accurate" becomes something you can check
rather than something you hope.

Usage
-----
  # against a locally booted server, no API keys required
  MIRU_STUB_LLM=1 python tests/gauntlet.py --spawn

  # against a deployment
  python tests/gauntlet.py --base-url https://miru-api.vercel.app

Exit code is 0 only when every check passes.
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

BACKEND_DIR = Path(__file__).resolve().parents[1]

RADAR_DIMENSIONS = [
    "wa_teamwork",
    "loyalty_commitment",
    "humility",
    "kaizen_growth",
    "cultural_fit",
]

GREEN, RED, YELLOW, DIM, RESET = (
    "\033[32m",
    "\033[31m",
    "\033[33m",
    "\033[2m",
    "\033[0m",
)


class CheckFailure(Exception):
    """A README promise the server did not keep."""


class Gauntlet:
    def __init__(self, base_url: str, timeout: float = 90.0, verbose: bool = False):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.verbose = verbose
        self.passed: List[str] = []
        self.failed: List[Tuple[str, str]] = []
        self.notes: List[str] = []

    # ── transport ────────────────────────────────────────────────────────
    def request(
        self, method: str, path: str, body: Optional[Dict[str, Any]] = None
    ) -> Tuple[int, Any]:
        url = f"{self.base_url}{path}"
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(
            url,
            data=data,
            method=method,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                raw = resp.read().decode()
                status = resp.status
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode()
            status = exc.code
        except urllib.error.URLError as exc:
            raise CheckFailure(f"{method} {path} — connection failed: {exc.reason}")

        try:
            return status, json.loads(raw) if raw else None
        except json.JSONDecodeError:
            return status, raw

    # ── assertions ───────────────────────────────────────────────────────
    def check(self, name: str, fn: Callable[[], None]) -> bool:
        try:
            fn()
        except CheckFailure as exc:
            self.failed.append((name, str(exc)))
            print(f"  {RED}✗{RESET} {name}\n      {RED}{exc}{RESET}")
            return False
        except Exception as exc:  # noqa: BLE001
            self.failed.append((name, f"{type(exc).__name__}: {exc}"))
            print(f"  {RED}✗{RESET} {name}\n      {RED}{type(exc).__name__}: {exc}{RESET}")
            return False
        self.passed.append(name)
        print(f"  {GREEN}✓{RESET} {name}")
        return True

    def note(self, message: str) -> None:
        self.notes.append(message)
        print(f"  {YELLOW}!{RESET} {message}")

    @staticmethod
    def expect(condition: bool, message: str) -> None:
        if not condition:
            raise CheckFailure(message)

    @staticmethod
    def expect_keys(payload: Any, keys: List[str], where: str) -> None:
        if not isinstance(payload, dict):
            raise CheckFailure(f"{where}: expected an object, got {type(payload).__name__}")
        missing = [k for k in keys if k not in payload]
        if missing:
            raise CheckFailure(
                f"{where}: missing key(s) {missing}; got {sorted(payload.keys())}"
            )

    def expect_radar(self, payload: Any, where: str) -> None:
        self.expect_keys(payload, RADAR_DIMENSIONS, where)
        for dim in RADAR_DIMENSIONS:
            value = payload[dim]
            if not isinstance(value, (int, float)):
                raise CheckFailure(f"{where}: {dim} is {type(value).__name__}, expected a number")
            if not 0 <= float(value) <= 10:
                raise CheckFailure(f"{where}: {dim}={value} outside the documented 0-10 range")

    # ── the lifecycle ────────────────────────────────────────────────────
    def run(self) -> bool:
        print(f"\n{DIM}Target: {self.base_url}{RESET}\n")

        print("Environment")
        health: Dict[str, Any] = {}

        def _health() -> None:
            status, body = self.request("GET", "/health")
            self.expect(status == 200, f"/health returned HTTP {status}")
            self.expect_keys(body, ["ok", "database"], "/health")
            health.update(body)

        if not self.check("GET /health responds", _health):
            return False

        db = health.get("database", {})
        if db.get("alive"):
            print(f"  {GREEN}✓{RESET} database reachable")
        else:
            self.note(f"database NOT reachable — {db.get('detail')}")
            self.note("results will be memory-only and will not survive a cold start")
        if not health.get("openai_key_set"):
            self.note("OPENAI_API_KEY not set — interview quality is stubbed/fallback")
        if not health.get("elevenlabs_key_set"):
            self.note("ELEVENLABS_API_KEY not set — voice_audio will be empty")

        print("\nStep 1 — POST /api/session/start")
        session_id = ""
        timer_end = 0

        def _start() -> None:
            nonlocal session_id, timer_end
            status, body = self.request(
                "POST",
                "/api/session/start",
                {
                    "user_name": "Gauntlet Candidate",
                    "target_role": "Product Manager",
                    "company": "rakuten",
                    "language_mode": "en",
                    "duration_mins": 3,
                    "cv_context": "Five years of product management in fintech.",
                },
            )
            self.expect(status == 200, f"expected HTTP 200, got {status}: {body}")
            self.expect_keys(body, ["session_id", "timer_end_epoch"], "session/start")
            session_id = str(body["session_id"])
            timer_end = int(body["timer_end_epoch"])
            self.expect(len(session_id) > 0, "session_id is empty")
            self.expect(
                timer_end > int(time.time() * 1000),
                "timer_end_epoch is in the past — the interview timer would expire instantly",
            )

        if not self.check("returns session_id and a future timer_end_epoch", _start):
            return False

        print("\nStep 2 — POST /api/interview/turn (README: frontend loops this)")
        turns_done = 0
        interview_complete = False
        debrief_ready = False

        def _turn_shape() -> None:
            nonlocal turns_done, interview_complete, debrief_ready
            status, body = self.request(
                "POST",
                "/api/interview/turn",
                {
                    "session_id": session_id,
                    "user_answer": "I led a cross-functional team to cut onboarding time by 30%.",
                    "company": "rakuten",
                    "voice_mode": False,
                },
            )
            self.expect(status == 200, f"expected HTTP 200, got {status}: {body}")
            # Contract consumed by frontend/src/lib/types.ts InterviewTurnResponse
            self.expect_keys(
                body,
                ["interviewer_response", "next_question", "scores", "interview_complete"],
                "interview/turn",
            )
            self.expect_radar(body["scores"], "interview/turn scores")
            turns_done += 1
            interview_complete = bool(body.get("interview_complete"))
            debrief_ready = bool(body.get("debrief_ready"))

        if not self.check("turn response matches InterviewTurnResponse", _turn_shape):
            return False

        def _session_persists() -> None:
            status, body = self.request("GET", f"/api/session/{session_id}/state")
            self.expect(status == 200, f"expected HTTP 200, got {status}: {body}")
            self.expect_keys(
                body, ["turn_count", "scores", "time_remaining_ms"], "session/state"
            )
            self.expect(
                int(body["turn_count"]) >= 1,
                f"turn_count is {body['turn_count']} after {turns_done} turn(s) — "
                "session state is not persisting across requests",
            )

        self.check("session state survives across requests", _session_persists)

        def _voice_mode() -> None:
            status, body = self.request(
                "POST",
                "/api/interview/turn",
                {
                    "session_id": session_id,
                    "user_answer": "I prefer to build consensus before proposing a change.",
                    "company": "rakuten",
                    "voice_mode": True,
                },
            )
            self.expect(status == 200, f"expected HTTP 200, got {status}: {body}")
            self.expect("tts_text" in body, "voice_mode=true did not return tts_text")
            if not body.get("voice_audio"):
                self.note("voice_mode=true returned no voice_audio (ElevenLabs unavailable)")

        self.check("voice_mode returns tts_text", _voice_mode)
        turns_done += 1

        print("\nStep 3 — drive to completion")

        def _complete() -> None:
            nonlocal interview_complete, debrief_ready
            deadline = time.time() + self.timeout
            attempts = 0
            while not interview_complete and time.time() < deadline and attempts < 12:
                attempts += 1
                force = attempts >= 3
                status, body = self.request(
                    "POST",
                    "/api/interview/turn",
                    {
                        "session_id": session_id,
                        "user_answer": "I take ownership of mistakes and share credit for wins.",
                        "company": "rakuten",
                        "voice_mode": False,
                        **({"force_complete": True} if force else {}),
                    },
                )
                self.expect(status == 200, f"expected HTTP 200, got {status}: {body}")
                interview_complete = bool(body.get("interview_complete"))
                debrief_ready = bool(body.get("debrief_ready"))
            self.expect(
                interview_complete,
                f"interview never reported interview_complete after {attempts} turns "
                "(force_complete included) — the frontend would never leave the interview screen",
            )

        if not self.check("interview reaches interview_complete", _complete):
            return False

        if not debrief_ready:
            self.note(
                "interview_complete=true but debrief_ready falsy — README step 3 "
                "says the frontend navigates on both flags"
            )

        print("\nStep 4 — GET /api/interview/results (README: poll until ready)")

        def _poll_results() -> None:
            deadline = time.time() + self.timeout
            last: Any = None
            while time.time() < deadline:
                status, body = self.request(
                    "GET", f"/api/interview/results?session_id={session_id}"
                )
                self.expect(status == 200, f"expected HTTP 200, got {status}: {body}")
                last = body
                if isinstance(body, dict) and body.get("status") == "ready":
                    return
                time.sleep(2)
            raise CheckFailure(
                f"results never reached status='ready' within {self.timeout:.0f}s; last={last}"
            )

        results_ok = self.check("results reach status='ready'", _poll_results)

        print("\nStep 5 — debrief payload the UI renders")

        def _full_results() -> None:
            status, body = self.request("GET", f"/api/interview/{session_id}/results")
            self.expect(status == 200, f"expected HTTP 200, got {status}: {body}")
            # Contract consumed by frontend/src/lib/types.ts FullResults
            self.expect_keys(
                body,
                ["radar_scores", "transcript", "feedback", "hiring_signal"],
                "interview/{id}/results",
            )
            self.expect_radar(body["radar_scores"], "results radar_scores")
            self.expect(
                isinstance(body["transcript"], list),
                f"transcript is {type(body['transcript']).__name__}, expected a list",
            )

        def _radar() -> None:
            status, body = self.request("GET", f"/api/interview/{session_id}/radar")
            self.expect(status == 200, f"expected HTTP 200, got {status}: {body}")
            payload = body.get("radar_scores", body) if isinstance(body, dict) else body
            self.expect_radar(payload, "interview/{id}/radar")

        def _report() -> None:
            status, body = self.request("GET", f"/api/interview/{session_id}/report")
            self.expect(status == 200, f"expected HTTP 200, got {status}: {body}")
            # Contract consumed by frontend/src/lib/types.ts FinalReport
            self.expect_keys(
                body,
                ["overall_summary", "strengths", "improvement_areas"],
                "interview/{id}/report",
            )
            self.expect(
                isinstance(body["strengths"], list),
                "report.strengths must be a list for the UI to map over it",
            )

        def _feedback() -> None:
            status, body = self.request("GET", f"/api/interview/{session_id}/feedback")
            self.expect(status == 200, f"expected HTTP 200, got {status}: {body}")
            self.expect_keys(body, ["turns"], "interview/{id}/feedback")
            self.expect(
                isinstance(body["turns"], list),
                "feedback.turns must be a list",
            )

        def _transcript() -> None:
            status, body = self.request("GET", f"/api/interview/{session_id}/transcript")
            self.expect(status == 200, f"expected HTTP 200, got {status}: {body}")
            self.expect(
                isinstance(body, dict) and "turns" in body,
                f"transcript must be an object with 'turns'; got {body}",
            )

        if results_ok:
            self.check("GET /{id}/results matches FullResults", _full_results)
            self.check("GET /{id}/radar returns 5 valid dimensions", _radar)
            self.check("GET /{id}/report matches FinalReport", _report)
            self.check("GET /{id}/feedback returns turns[]", _feedback)
            self.check("GET /{id}/transcript returns turns[]", _transcript)

        print("\nStep 6 — cleanup")

        def _delete() -> None:
            status, body = self.request("DELETE", f"/api/session/{session_id}")
            self.expect(status == 200, f"expected HTTP 200, got {status}: {body}")
            status, _ = self.request("GET", f"/api/session/{session_id}/state")
            self.expect(
                status == 404,
                f"deleted session still resolves (HTTP {status}) — delete did not purge state",
            )

        self.check("DELETE /api/session/{id} purges the session", _delete)

        return not self.failed


def wait_for_server(base_url: str, timeout: float = 45.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"{base_url}/health", timeout=3) as resp:
                if resp.status == 200:
                    return True
        except Exception:  # noqa: BLE001
            time.sleep(0.5)
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the MIRU README gauntlet.")
    parser.add_argument(
        "--base-url",
        default=os.getenv("MIRU_BASE_URL", "http://127.0.0.1:8000"),
        help="Server to test (default: %(default)s)",
    )
    parser.add_argument(
        "--spawn",
        action="store_true",
        help="Boot a local uvicorn server for the duration of the run",
    )
    parser.add_argument(
        "--rounds",
        type=int,
        default=3,
        help="Maximum attempts before giving up (default: %(default)s)",
    )
    parser.add_argument("--timeout", type=float, default=90.0)
    args = parser.parse_args()

    server: Optional[subprocess.Popen] = None
    base_url = args.base_url

    if args.spawn:
        base_url = "http://127.0.0.1:8000"
        print(f"{DIM}Booting uvicorn on {base_url}…{RESET}")
        server = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "main:app", "--port", "8000", "--log-level", "warning"],
            cwd=str(BACKEND_DIR),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            preexec_fn=os.setsid if hasattr(os, "setsid") else None,
        )
        if not wait_for_server(base_url):
            print(f"{RED}Server failed to start.{RESET}")
            if server.stdout:
                print(server.stdout.read()[:4000])
            server.kill()
            return 1

    try:
        for round_number in range(1, args.rounds + 1):
            print(f"\n{'═' * 62}\n  MIRU GAUNTLET — round {round_number}/{args.rounds}\n{'═' * 62}")
            gauntlet = Gauntlet(base_url, timeout=args.timeout)
            ok = gauntlet.run()

            print(f"\n{'─' * 62}")
            print(
                f"  {GREEN}{len(gauntlet.passed)} passed{RESET}   "
                f"{RED}{len(gauntlet.failed)} failed{RESET}   "
                f"{YELLOW}{len(gauntlet.notes)} warning(s){RESET}"
            )
            if gauntlet.notes:
                print("\n  Warnings:")
                for note in gauntlet.notes:
                    print(f"    {YELLOW}!{RESET} {note}")
            if gauntlet.failed:
                print("\n  Failures:")
                for name, detail in gauntlet.failed:
                    print(f"    {RED}✗{RESET} {name}: {detail}")
            print(f"{'─' * 62}")

            if ok:
                print(f"\n{GREEN}GAUNTLET PASSED{RESET} — every README lifecycle claim holds.\n")
                return 0
            if round_number < args.rounds:
                backoff = 2 ** round_number
                print(f"\n{YELLOW}Retrying in {backoff}s…{RESET}")
                time.sleep(backoff)

        print(f"\n{RED}GAUNTLET FAILED{RESET} after {args.rounds} round(s).\n")
        return 1
    finally:
        if server is not None:
            try:
                if hasattr(os, "killpg"):
                    os.killpg(os.getpgid(server.pid), signal.SIGTERM)
                else:
                    server.terminate()
                server.wait(timeout=10)
            except Exception:  # noqa: BLE001
                server.kill()


if __name__ == "__main__":
    sys.exit(main())
