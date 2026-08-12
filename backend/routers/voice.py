"""Server-side text-to-speech.

The frontend previously called ElevenLabs directly using
NEXT_PUBLIC_ELEVENLABS_API_KEY. Anything prefixed NEXT_PUBLIC_ is inlined
into the JavaScript bundle and served to every visitor, so that key was
readable by anyone who opened devtools. Proxying through the backend keeps
the credential server-side.
"""

from typing import Any, Dict

from fastapi import APIRouter, HTTPException

from services.voice_service import generate_voice

voice_router = APIRouter(prefix="/api/voice", tags=["voice"])


@voice_router.post("/tts")
async def text_to_speech(payload: Dict[str, Any]) -> Dict[str, str]:
    text = str(payload.get("text") or "").strip()
    if not text:
        raise HTTPException(status_code=422, detail="text is required")

    audio_b64 = generate_voice(text)
    if not audio_b64:
        raise HTTPException(status_code=503, detail="Voice generation unavailable")

    return {"audio_base64": audio_b64, "content_type": "audio/mpeg"}
