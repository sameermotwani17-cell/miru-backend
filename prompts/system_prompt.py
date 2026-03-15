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
    3) Layer 3 — candidate and session context (including CV)
    4) Layer 4 — output schema / format instructions
    """

    company_profile = COMPANY_PROFILES.get(company, TOYOTA_PROFILE)

    cv_section = f"Candidate CV:\n{cv_context}" if cv_context else "Candidate CV: Not provided"

    layer_3 = f"""Candidate name: {user_name or "Not provided"}
Target role: {target_role or "Not provided"}
Language mode: {language_mode}
Interview duration (minutes): {duration_mins}
Demo mode: {"yes" if is_demo_mode else "no"}
{cv_section}""".strip()

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
                "  \"interviewer_response\": \"<commentary only — NO question, NO question mark>\",\n"
                "  \"next_question\": \"<the single question to ask the candidate>\",\n"
                "  \"scores\": {\n"
                "    \"communication\": <int 1-10>,\n"
                "    \"clarity\": <int 1-10>,\n"
                "    \"cultural_fit\": <int 1-10>,\n"
                "    \"problem_solving\": <int 1-10>\n"
                "  },\n"
                "  \"is_wrapping_up\": <boolean>\n"
                "}\n\n"
                "STRICT FIELD RULES — follow these exactly, every turn:\n\n"
                "1. 'interviewer_response' — COMMENTARY ONLY.\n"
                "   - Must NOT contain a question mark (?).\n"
                "   - Must NOT ask any question, directly or indirectly.\n"
                "   - Must NOT repeat or paraphrase what will appear in 'next_question'.\n"
                "   - Write 1-3 sentences that react naturally to what the candidate just said.\n"
                "   - Reference a specific detail from their answer.\n"
                "   - Do not use hollow filler like 'I see', 'Interesting', or 'Great'.\n"
                "   - On the very first turn, greet the candidate warmly by name — nothing more.\n"
                "     Example: \"Hello Sameer, it's great to meet you today.\"\n\n"
                "2. 'next_question' — THE QUESTION.\n"
                "   - Must contain exactly one focused question ending with a question mark (?).\n"
                "   - On the very first turn, ask the candidate to introduce themselves.\n"
                "     Example: \"Could you please introduce yourself and walk me through your background?\"\n"
                "   - On subsequent turns, ask one follow-up question that builds on their answer.\n"
                "   - Vary the type: behavioral, situational, motivational, or technical.\n"
                "   - Never repeat a question already asked in the conversation history.\n\n"
                "CRITICAL: The two fields serve different purposes and must never overlap.\n"
                "  WRONG → interviewer_response: \"Could you tell me about yourself?\"\n"
                "           next_question:        \"Could you tell me about yourself?\"\n"
                "  RIGHT → interviewer_response: \"Hello Sameer, it's great to meet you.\"\n"
                "           next_question:        \"Could you walk me through your background?\"\n\n"
                "3. 'is_wrapping_up': Set to true only when the interview has covered enough ground "
                "and should conclude naturally.\n\n"
                "Scoring bands (1-10):\n"
                "1-2: serious concern\n"
                "3-4: weak answer\n"
                "5-6: acceptable but average\n"
                "7-8: strong answer\n"
                "9-10: exceptional (rare)\n\n"
                "Score definitions:\n"
                "- communication: how clearly and confidently they expressed themselves\n"
                "- clarity: how well-structured and concise their answer was\n"
                "- cultural_fit: alignment with the company's values and working style\n"
                "- problem_solving: evidence of analytical thinking and handling challenges\n\n"
                "Evaluate only from the candidate's latest answer. Be conservative — most candidates score 4-6."
            ),
        ]
    )

    return prompt
