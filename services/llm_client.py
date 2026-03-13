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
                        "response": {
                            "type": "string"
                        },
                        "scores": {
                            "type": "object",
                            "additionalProperties": False,
                            "properties": {
                                "jiko_pr": {
                                    "type": "integer",
                                    "minimum": 1,
                                    "maximum": 10
                                },
                                "shibou_douki": {
                                    "type": "integer",
                                    "minimum": 1,
                                    "maximum": 10
                                },
                                "kyouchousei": {
                                    "type": "integer",
                                    "minimum": 1,
                                    "maximum": 10
                                },
                                "seichou_iyoku": {
                                    "type": "integer",
                                    "minimum": 1,
                                    "maximum": 10
                                },
                                "bunka_tekigou": {
                                    "type": "integer",
                                    "minimum": 1,
                                    "maximum": 10
                                }
                            },
                            "required": [
                                "jiko_pr",
                                "shibou_douki",
                                "kyouchousei",
                                "seichou_iyoku",
                                "bunka_tekigou"
                            ]
                        },
                        "is_wrapping_up": {
                            "type": "boolean"
                        }
                    },
                    "required": [
                        "response",
                        "scores",
                        "is_wrapping_up"
                    ]
                }
            }
        }
    )

    raw_text = response.choices[0].message.content

    print("RAW LLM RESPONSE:")
    print(raw_text)

    try:
        parsed = json.loads(raw_text)
        return parsed
    except Exception:
        return {
            "agent_text": raw_text,
            "scores": {
                "jiko_pr": 5,
                "shibou_douki": 5,
                "kyouchousei": 5,
                "seichou_iyoku": 5,
                "bunka_tekigou": 5
            },
            "is_wrapping_up": False,
            "question_id": "Q_FALLBACK"
        }