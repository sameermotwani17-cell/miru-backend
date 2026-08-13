import base64
import logging
import os

LOGGER = logging.getLogger(__name__)

# Default matches the voice the frontend previously hardcoded, so behaviour is
# unchanged if ELEVENLABS_VOICE_ID is not set.
_DEFAULT_VOICE_ID = "EbuvaInXUGWtpYRUnKLQ"

_client = None


def _get_client():
    """Build the ElevenLabs client lazily.

    Reading the key at import time meant a missing ELEVENLABS_API_KEY baked a
    dead client into the module for the life of the process.
    """
    global _client
    if _client is None:
        from elevenlabs.client import ElevenLabs

        _client = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))
    return _client


def _voice_id() -> str:
    return os.getenv("ELEVENLABS_VOICE_ID") or _DEFAULT_VOICE_ID


def generate_voice(text: str) -> str:
    """Generate TTS audio via ElevenLabs and return base64-encoded MP3.

    Returns an empty string if the API call fails so callers can degrade
    gracefully without crashing the interview pipeline.
    """
    if not text:
        return ""
    if not os.getenv("ELEVENLABS_API_KEY"):
        LOGGER.warning("[VOICE] ELEVENLABS_API_KEY not set — skipping TTS")
        return ""
    try:
        audio_chunks = _get_client().text_to_speech.convert(
            voice_id=_voice_id(),
            model_id="eleven_multilingual_v2",
            text=text,
            voice_settings={
                "stability": 0.65,
                "similarity_boost": 0.85,
            },
        )
        audio_bytes = b"".join(audio_chunks)
        return base64.b64encode(audio_bytes).decode("utf-8")
    except Exception as exc:
        LOGGER.warning("[VOICE] ElevenLabs TTS failed: %s", exc)
        return ""
