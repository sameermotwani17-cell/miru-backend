"""Quick smoke test for the ElevenLabs voice service."""
import os
import sys

# Ensure project root is on the path when run directly
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from services.voice_service import generate_voice

TEST_TEXT = "Welcome to your interview. Please introduce yourself."

if __name__ == "__main__":
    print("Testing ElevenLabs voice service...")
    api_key = os.getenv("ELEVENLABS_API_KEY", "")
    voice_id = os.getenv("ELEVENLABS_VOICE_ID", "")
    print(f"  ELEVENLABS_API_KEY : {'SET (sk_***)' if api_key.startswith('sk_') else 'MISSING'}")
    print(f"  ELEVENLABS_VOICE_ID: {'SET' if voice_id else 'MISSING'}")

    result = generate_voice(TEST_TEXT)
    if result:
        print(f"  Audio generated successfully — base64 length: {len(result)} chars")
        print("PASS: ElevenLabs TTS is working.")
    else:
        print("FAIL: No audio returned. Check API key and voice ID in .env.")
        sys.exit(1)
