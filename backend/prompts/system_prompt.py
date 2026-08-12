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
{cv_section}
Name instruction: {"If the candidate name is known, address them naturally at appropriate moments (for example: Hello " + user_name + "). Do not overuse the name." if user_name else "Candidate name is not known; do not guess or use a placeholder name."}""".strip()

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
                "    \"wa_teamwork\": <int 1-10>,\n"
                "    \"loyalty_commitment\": <int 1-10>,\n"
                "    \"humility\": <int 1-10>,\n"
                "    \"kaizen_growth\": <int 1-10>,\n"
                "    \"cultural_fit\": <int 1-10>\n"
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
                "   - Vary the type: behavioral, situational, motivational, or values-based.\n"
                "   - Never repeat a question already asked in the conversation history.\n\n"
                "CRITICAL: The two fields serve different purposes and must never overlap.\n"
                "  WRONG → interviewer_response: \"Could you tell me about yourself?\"\n"
                "           next_question:        \"Could you tell me about yourself?\"\n"
                "  RIGHT → interviewer_response: \"Hello Sameer, it's great to meet you.\"\n"
                "           next_question:        \"Could you walk me through your background?\"\n\n"
                "3. 'is_wrapping_up': Set to true only when the interview has covered enough ground "
                "and should conclude naturally.\n\n"
                "SCORING DIMENSIONS (score each 1-10 in the scores JSON object):\n"
                "- wa_teamwork: Does the answer prioritise group harmony? Does it avoid dominant \"I\" framing?\n"
                "  High score = team-first language, references to group outcomes.\n"
                "  Low score = individualistic framing, \"I achieved\", \"I decided alone\".\n\n"
                "- loyalty_commitment: Does the answer signal long-term intent?\n"
                "  High score = language of commitment, contributing to company mission long-term.\n"
                "  Low score = job-hopping signals, \"stepping stone\", \"looking for new challenges\".\n\n"
                "- humility: Is self-presentation appropriately humble for Japanese context?\n"
                "  High score = achievements framed with credit to team/circumstances, correct modesty markers.\n"
                "  Low score = \"I am the best\", \"I am confident I can\", over-selling without qualification.\n\n"
                "- kaizen_growth: Is growth framed as improvement within the company's framework?\n"
                "  High score = \"I want to develop within [company]'s methods\", \"contribute to continuous improvement\".\n"
                "  Low score = \"I eventually want to start my own company\", \"I want to expand my personal skills\".\n\n"
                "- cultural_fit: Does the candidate show awareness of Japanese business culture?\n"
                "  High score = references to company values, keigo-aware phrasing, process respect.\n"
                "  Low score = casual language, ignoring hierarchy, asking about work-life balance too early.\n\n"
                "SCORING GUIDANCE:\n"
                "- Be conservative. Most foreign candidates score 4-6 on most dimensions.\n"
                "- A score of 8+ requires explicit, specific evidence in the answer.\n"
                "- A score of 1-2 means the answer actively damaged this dimension.\n"
                "- Score based on how a Japanese HR manager at the target company would actually react.\n"
                "- Evaluate only from the candidate's latest answer."
            ),
        ]
    )

    return prompt
