import { textToSpeech } from "@/lib/api";

let currentAudio: HTMLAudioElement | null = null;

function stopCurrent(): void {
  if (currentAudio) {
    currentAudio.pause();
    currentAudio = null;
  }
}

function playAudioUrl(audioUrl: string): Promise<void> {
  const audio = new Audio(audioUrl);
  currentAudio = audio;

  return new Promise<void>((resolve) => {
    const finish = () => {
      URL.revokeObjectURL(audioUrl);
      currentAudio = null;
      resolve();
    };
    audio.onended = finish;
    audio.onerror = finish;
    audio.play().catch(() => resolve());
  });
}

/**
 * Speak text through the backend's TTS endpoint.
 *
 * This used to call api.elevenlabs.io directly from the browser using
 * NEXT_PUBLIC_ELEVENLABS_API_KEY. Anything prefixed NEXT_PUBLIC_ is inlined
 * into the client bundle and served to every visitor, so that key was
 * readable by anyone who opened devtools. The key now lives only on the
 * backend.
 */
export async function speak(text: string): Promise<void> {
  if (typeof window === "undefined") return;

  stopCurrent();
  if (!text?.trim()) return;

  try {
    const base64 = await textToSpeech(text);
    if (!base64) return;
    await playBase64Audio(base64);
  } catch (err) {
    console.error("TTS failed", err);
  }
}

export function stopSpeech(): void {
  stopCurrent();
}

export async function playBase64Audio(base64: string): Promise<void> {
  if (typeof window === "undefined" || !base64?.trim()) return;

  stopCurrent();

  const byteChars = atob(base64);
  const bytes = new Uint8Array(byteChars.length);
  for (let i = 0; i < byteChars.length; i++) {
    bytes[i] = byteChars.charCodeAt(i);
  }
  const blob = new Blob([bytes], { type: "audio/mpeg" });
  await playAudioUrl(URL.createObjectURL(blob));
}
