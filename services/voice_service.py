import base64
import logging
import os
import sys

# elevenlabs is installed to C:\el due to Windows Long Path constraints.
# Remove any stale partial install from sys.modules before inserting the correct path.
for _mod in list(sys.modules):
    if _mod == "elevenlabs" or _mod.startswith("elevenlabs."):
        del sys.modules[_mod]
if "C:\\el" not in sys.path:
    sys.path.insert(0, "C:\\el")

from elevenlabs.client import ElevenLabs

LOGGER = logging.getLogger(__name__)

_client = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))
VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID")


def generate_voice(text: str) -> str:
    """Generate TTS audio via ElevenLabs and return base64-encoded MP3.

    Returns an empty string if the API call fails so callers can degrade
    gracefully without crashing the interview pipeline.
    """
    if not text:
        return ""
    try:
        audio_chunks = _client.text_to_speech.convert(
            voice_id=VOICE_ID,
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
