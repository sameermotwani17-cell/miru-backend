import { speak as elevenSpeak, stopSpeech as elevenStop, playBase64Audio as elevenPlayBase64 } from "@/services/voice";

export { elevenStop as stopSpeech };
export { elevenPlayBase64 as playBase64Audio };

export async function speakAndWait(texts: string | string[], _lang?: string): Promise<void> {
  const list = (Array.isArray(texts) ? texts : [texts]).filter((t) => Boolean(t?.trim()));
  if (!list.length) return;
  await elevenSpeak(list.join(" "));
}

export function speak(texts: string | string[], _lang?: string): void {
  void speakAndWait(texts);
}
