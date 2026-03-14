import json
import os
from openai import OpenAI


def _get_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")
    return OpenAI(api_key=api_key)


def call_llm(system_prompt: str, conversation: list, user_message: str):
    client = _get_client()

    messages = [{"role": "system", "content": system_prompt}]
    for msg in conversation:
        messages.append(msg)
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
                        "scores": {
                            "type": "object",
                            "additionalProperties": False,
                            "properties": {
                                "communication": {
                                    "type": "integer",
                                    "minimum": 1,
                                    "maximum": 10
                                },
                                "clarity": {
                                    "type": "integer",
                                    "minimum": 1,
                                    "maximum": 10
                                },
                                "cultural_fit": {
                                    "type": "integer",
                                    "minimum": 1,
                                    "maximum": 10
                                },
                                "problem_solving": {
                                    "type": "integer",
                                    "minimum": 1,
                                    "maximum": 10
                                }
                            },
                            "required": [
                                "communication",
                                "clarity",
                                "cultural_fit",
                                "problem_solving"
                            ]
                        },
                        "is_wrapping_up": {
                            "type": "boolean"
                        }
                    },
                    "required": [
                        "interviewer_response",
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
            "scores": {
                "communication": 5,
                "clarity": 5,
                "cultural_fit": 5,
                "problem_solving": 5,
            },
            "is_wrapping_up": False,
        }
