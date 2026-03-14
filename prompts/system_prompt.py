from prompts.hr_personality import HR_PERSONA
from prompts.companies.toyota import TOYOTA_PROFILE
from prompts.companies.rakuten import RAKUTEN_PROFILE
from prompts.companies.sony import SONY_PROFILE
from prompts.companies.softbank import SOFTBANK_PROFILE
from prompts.companies.uniqlo import UNIQLO_PROFILE

COMPANY_PROFILES = {
    "toyota": TOYOTA_PROFILE,
    "rakuten": RAKUTEN_PROFILE,
    "sony": SONY_PROFILE,
    "softbank": SOFTBANK_PROFILE,
    "uniqlo": UNIQLO_PROFILE,
}

def build_system_prompt(
    company: str,
    language_mode: str,
    duration_mins: int,
    is_demo_mode: bool,
    cv_context: str | None = None,
    user_name: str = "",
    target_role: str = "",
    hr_persona: str | None = None,
) -> str:
    """
    Assemble the full MIRU system prompt by stacking:
    1) Layer 1 — core HR persona
    2) Layer 2 — company-specific profile
    3) Layer 3 — candidate and session context
    4) Layer 4 — output schema / format instructions
    """

    company_profile = COMPANY_PROFILES.get(company, TOYOTA_PROFILE)

    layer_3 = f"""
Candidate name: {user_name or "Not provided"}
Target role: {target_role or "Not provided"}
Language mode: {language_mode}
Interview duration (minutes): {duration_mins}
Demo mode: {"yes" if is_demo_mode else "no"}
CV context:
{cv_context or "Not provided"}
""".strip()

    prompt = "\n\n".join(
        [
            "LAYER 1 — HR PERSONA",
            (hr_persona or HR_PERSONA).strip(),
            "LAYER 2 — COMPANY PROFILE",
            company_profile.strip(),
            "LAYER 3 — CANDIDATE & SESSION CONTEXT",
            layer_3,
            "LAYER 4 — OUTPUT FORMAT",
            (
                "Return only valid JSON (no markdown, no extra text) in this exact shape:\n"
                "{\n"
                "  \"response\": \"<next interview question>\",\n"
                "  \"scores\": {\n"
                "    \"jiko_pr\": <int 1-10>,\n"
                "    \"shibou_douki\": <int 1-10>,\n"
                "    \"kyouchousei\": <int 1-10>,\n"
                "    \"seichou_iyoku\": <int 1-10>,\n"
                "    \"bunka_tekigou\": <int 1-10>\n"
                "  },\n"
                "  \"is_wrapping_up\": <boolean>\n"
                "}\n"
                "You are a strict Japanese corporate interviewer evaluating a candidate.\n"
                "Use a conservative scale and evaluate only from the candidate's latest answer.\n"
                "Evaluate clarity and structure independent of language; the answer may be in English or Japanese.\n"
                "Scoring bands:\n"
                "1-2: serious concern\n"
                "3-4: weak answer\n"
                "5-6: acceptable but average\n"
                "7-8: strong answer\n"
                "9: exceptional answer\n"
                "10: almost never used\n"
                "Most candidates should score between 4 and 6.\n"
                "Do not give high scores unless the answer clearly demonstrates strong alignment with Japanese workplace values: teamwork harmony, humility, willingness to support group decisions, and continuous improvement mindset.\n"
                "Answers emphasizing individualism or challenging hierarchy should lower kyouchousei and bunka_tekigou.\n"
                "Calibration examples for kyouchousei:\n"
                "Weak: 'I prefer working independently and usually push my own ideas.' -> 2-3\n"
                "Average: 'I work well with teams and communicate openly.' -> 5-6\n"
                "Strong: 'I support team consensus even if my initial idea differs.' -> 7-8\n"
                "If kyouchousei <= 3, reduce bunka_tekigou by 1-2 points."
            ),
        ]
    )

    return prompt