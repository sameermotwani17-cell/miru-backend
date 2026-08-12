export interface SpeechRecognitionEventLike extends Event {
  results: {
    [index: number]: {
      [index: number]: {
        transcript: string;
      };
      isFinal: boolean;
      length: number;
    };
    length: number;
  };
}

export interface SpeechRecognitionErrorEventLike extends Event {
  error: string;
}

export interface SpeechRecognitionInstance extends EventTarget {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  start: () => void;
  stop: () => void;
  onstart: (() => void) | null;
  onresult: ((ev: SpeechRecognitionEventLike) => void) | null;
  onerror: ((ev: SpeechRecognitionErrorEventLike) => void) | null;
  onend: (() => void) | null;
}

type SpeechRecognitionCtor = new () => SpeechRecognitionInstance;

export interface StartSpeechRecognitionOptions {
  lang?: string;
  interimResults?: boolean;
  silenceTimeoutMs?: number;
  onError?: (message: string) => void;
  onEnd?: () => void;
}

// Silence must persist for this long before auto-stop.
const DEFAULT_SILENCE_TIMEOUT_MS = 2500;

// Minimum speech duration before silence can auto-end capture.
const MIN_SPEECH_DURATION_MS = 800;

// Hard cap — recording stops after this duration even if speech continues.
const MAX_SPEECH_DURATION_MS = 30000;

export function startSpeechRecognition(
  onResult: (text: string) => void,
  options: StartSpeechRecognitionOptions = {}
): SpeechRecognitionInstance | null {
  if (typeof window === "undefined") {
    return null;
  }

  const speechWindow = window as Window & {
    SpeechRecognition?: SpeechRecognitionCtor;
    webkitSpeechRecognition?: SpeechRecognitionCtor;
  };

  const SpeechRecognition =
    speechWindow.SpeechRecognition ?? speechWindow.webkitSpeechRecognition;

  if (!SpeechRecognition) {
    options.onError?.("Speech recognition not supported. Please use Chrome.");
    return null;
  }

  const recognition = new SpeechRecognition();
  recognition.lang = options.lang ?? "en-US";
  recognition.interimResults = options.interimResults ?? true;

  const silenceTimeoutMs = options.silenceTimeoutMs ?? DEFAULT_SILENCE_TIMEOUT_MS;
  let silenceTimer: ReturnType<typeof setTimeout> | null = null;
  let maxDurationTimer: ReturnType<typeof setTimeout> | null = null;
  let hasDetectedSpeech = false;
  let speechStartTime: number | null = null;

  const clearSilenceTimer = () => {
    if (!silenceTimer) return;
    clearTimeout(silenceTimer);
    silenceTimer = null;
  };

  const clearMaxDurationTimer = () => {
    if (!maxDurationTimer) return;
    clearTimeout(maxDurationTimer);
    maxDurationTimer = null;
  };

  const resetSilenceTimer = () => {
    if (!hasDetectedSpeech) return;
    clearSilenceTimer();

    const now = Date.now();
    const speechElapsed = speechStartTime !== null ? now - speechStartTime : 0;

    const effectiveTimeout =
      speechElapsed < MIN_SPEECH_DURATION_MS
        ? silenceTimeoutMs + (MIN_SPEECH_DURATION_MS - speechElapsed)
        : silenceTimeoutMs;

    silenceTimer = setTimeout(() => {
      console.log("VOICE: silence detected — stopping recognition");
      recognition.stop();
    }, effectiveTimeout);
  };

  recognition.onstart = () => {
    hasDetectedSpeech = false;
    speechStartTime = null;
    clearSilenceTimer();
    clearMaxDurationTimer();
    // Hard-stop after MAX_SPEECH_DURATION_MS regardless of silence state.
    maxDurationTimer = setTimeout(() => {
      console.log("VOICE: max duration reached — stopping recognition");
      recognition.stop();
    }, MAX_SPEECH_DURATION_MS);
    console.log("VOICE: listening");
  };

  recognition.onresult = (event: SpeechRecognitionEventLike) => {
    // Accumulate full transcript across ALL result segments (handles multi-part utterances)
    let fullText = "";
    for (let i = 0; i < event.results.length; i++) {
      fullText += event.results[i][0]?.transcript ?? "";
    }
    fullText = fullText.trim();

    if (fullText) {
      if (!hasDetectedSpeech) {
        hasDetectedSpeech = true;
        speechStartTime = Date.now();
        console.log("VOICE: speech detected");
      }
      onResult(fullText);
      resetSilenceTimer();
    }
  };

  recognition.onerror = (event: SpeechRecognitionErrorEventLike) => {
    clearSilenceTimer();
    clearMaxDurationTimer();
    if (event.error !== "aborted") {
      console.warn(`VOICE: recognition error — ${event.error}`);
      options.onError?.(`Recording error: ${event.error}`);
    }
  };

  recognition.onend = () => {
    clearSilenceTimer();
    clearMaxDurationTimer();
    console.log("VOICE: recognition ended");
    options.onEnd?.();
  };

  recognition.start();
  return recognition;
}
