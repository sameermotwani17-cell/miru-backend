let currentAudio: HTMLAudioElement | null = null;

export async function speak(text: string): Promise<void> {
  if (typeof window === "undefined") return;

  // Stop any currently playing audio
  if (currentAudio) {
    currentAudio.pause();
    currentAudio = null;
  }

  if (!text?.trim()) return;

  const apiKey = process.env.NEXT_PUBLIC_ELEVENLABS_API_KEY;
  if (!apiKey) {
    console.error("ElevenLabs TTS failed: NEXT_PUBLIC_ELEVENLABS_API_KEY is not set");
    return;
  }

  const response = await fetch(
    "https://api.elevenlabs.io/v1/text-to-speech/EbuvaInXUGWtpYRUnKLQ",
    {
      method: "POST",
      headers: {
        "xi-api-key": apiKey,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        text,
        model_id: "eleven_multilingual_v2",
        voice_settings: {
          stability: 0.4,
          similarity_boost: 0.8,
        },
      }),
    }
  );

  if (!response.ok) {
    console.error("ElevenLabs TTS failed", response.status);
    return;
  }

  const audioBlob = await response.blob();
  const audioUrl = URL.createObjectURL(audioBlob);
  const audio = new Audio(audioUrl);
  currentAudio = audio;

  await new Promise<void>((resolve) => {
    audio.onended = () => {
      URL.revokeObjectURL(audioUrl);
      currentAudio = null;
      resolve();
    };
    audio.onerror = () => {
      URL.revokeObjectURL(audioUrl);
      currentAudio = null;
      resolve();
    };
    audio.play().catch(() => resolve());
  });
}

export function stopSpeech(): void {
  if (currentAudio) {
    currentAudio.pause();
    currentAudio = null;
  }
}

export async function playBase64Audio(base64: string): Promise<void> {
  if (typeof window === "undefined" || !base64?.trim()) return;

  if (currentAudio) {
    currentAudio.pause();
    currentAudio = null;
  }

  const byteChars = atob(base64);
  const bytes = new Uint8Array(byteChars.length);
  for (let i = 0; i < byteChars.length; i++) {
    bytes[i] = byteChars.charCodeAt(i);
  }
  const blob = new Blob([bytes], { type: "audio/mpeg" });
  const audioUrl = URL.createObjectURL(blob);
  const audio = new Audio(audioUrl);
  currentAudio = audio;

  await new Promise<void>((resolve) => {
    audio.onended = () => {
      URL.revokeObjectURL(audioUrl);
      currentAudio = null;
      resolve();
    };
    audio.onerror = () => {
      URL.revokeObjectURL(audioUrl);
      currentAudio = null;
      resolve();
    };
    audio.play().catch(() => resolve());
  });
}
