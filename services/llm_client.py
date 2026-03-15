import json
import os
from openai import OpenAI

from services.score_dimensions import DEFAULT_SCORES


def _get_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")
    return OpenAI(api_key=api_key)


_VALID_ROLES = {"system", "user", "assistant"}


def call_llm(system_prompt: str, conversation: list, user_message: str):
    client = _get_client()

    messages = [{"role": "system", "content": system_prompt}]
    for msg in conversation:
        if not isinstance(msg, dict):
            continue
        role = msg.get("role")
        content = msg.get("content")
        if role not in _VALID_ROLES or content is None:
            continue
        messages.append({"role": role, "content": str(content)})
    messages.append({"role": "user", "content": user_message})

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0.3,
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "miru_interview_turn",
                "strict": True,
                "schema": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "interviewer_response": {
                            "type": "string"
                        },
                        "next_question": {
                            "type": "string"
                        },
                        "scores": {
                            "type": "object",
                            "additionalProperties": False,
                            "properties": {
                                "wa_teamwork": {
                                    "type": "integer",
                                    "minimum": 1,
                                    "maximum": 10
                                },
                                "loyalty_commitment": {
                                    "type": "integer",
                                    "minimum": 1,
                                    "maximum": 10
                                },
                                "humility": {
                                    "type": "integer",
                                    "minimum": 1,
                                    "maximum": 10
                                },
                                "kaizen_growth": {
                                    "type": "integer",
                                    "minimum": 1,
                                    "maximum": 10
                                },
                                "cultural_fit": {
                                    "type": "integer",
                                    "minimum": 1,
                                    "maximum": 10
                                }
                            },
                            "required": [
                                "wa_teamwork",
                                "loyalty_commitment",
                                "humility",
                                "kaizen_growth",
                                "cultural_fit"
                            ]
                        },
                        "is_wrapping_up": {
                            "type": "boolean"
                        }
                    },
                    "required": [
                        "interviewer_response",
                        "next_question",
                        "scores",
                        "is_wrapping_up"
                    ]
                }
            }
        }
    )

    raw_text = response.choices[0].message.content

    try:
        parsed = json.loads(raw_text)
        return parsed
    except Exception:
        return {
            "interviewer_response": raw_text,
            "next_question": "",
            "scores": dict(DEFAULT_SCORES),
            "is_wrapping_up": False,
        }
