"use client";

import { useState, useEffect, useRef, useReducer, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useRouter } from "next/navigation";
import MiruLogo from "@/components/MiruLogo";
import HRAvatar from "@/components/HRAvatar";
import VoiceInput from "@/components/VoiceInput";
import { session } from "@/lib/session";
import { speakAndWait, stopSpeech, playBase64Audio } from "@/lib/tts";
import { sendInterviewTurn } from "@/lib/api";
import {
  startSpeechRecognition,
  type SpeechRecognitionInstance,
} from "@/lib/voice";
import {
  type InterviewScores,
} from "@/lib/types";
import { normalizeScores } from "@/lib/resultsNormalizer";
import { DIMENSION_LABELS } from "@/lib/types";
import ErrorBoundary from "@/components/ErrorBoundary";

type MachineStatus =
  | "IDLE"
  | "STARTING"
  | "QUESTION"
  | "LISTENING"
  | "TRANSCRIBING"
  | "WAITING_RESPONSE"
  | "WRAP_UP"
  | "COMPLETED"
  | "ERROR";

type ChatMessage = {
  role: "user" | "agent";
  text: string;
};

type MachineState = {
  status: MachineStatus;
  sessionId: string;
  company: string;
  languageMode: string;
  messages: ChatMessage[];
  latestScores: InterviewScores | null;
  error: string;
  turnCount: number;
};

type MachineAction =
  | { type: "SET_CONTEXT"; sessionId: string; company: string; languageMode: string }
  | { type: "STARTING" }
  | { type: "APPEND_MESSAGE"; role: "agent" | "user"; text: string }
  | { type: "QUESTION_READY"; agentText: string; scores?: InterviewScores; isFirst: boolean }
  | { type: "LISTENING" }
  | { type: "TRANSCRIBING" }
  | { type: "WAITING_RESPONSE"; userText: string; appendUser: boolean }
  | { type: "WRAP_UP" }
  | { type: "COMPLETED" }
  | { type: "ERROR"; error: string }
  | { type: "RETRY_FROM_ERROR" }
  | { type: "BACK_TO_QUESTION" };

const initialMachineState: MachineState = {
  status: "IDLE",
  sessionId: "",
  company: "rakuten",
  languageMode: "en",
  messages: [],
  latestScores: null,
  error: "",
  turnCount: 0,
};

const RETRY_BASE_DELAY_MS = 450;
const WRAP_UP_SECONDS = 20;
// Silence timeout passed to voice recognition (ms)
const SILENCE_TIMEOUT_MS = 2500;

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function interviewReducer(state: MachineState, action: MachineAction): MachineState {
  switch (action.type) {
    case "SET_CONTEXT":
      return {
        ...state,
        sessionId: action.sessionId,
        company: action.company,
        languageMode: action.languageMode,
      };
    case "STARTING":
      return {
        ...state,
        status: "STARTING",
        error: "",
      };
    case "APPEND_MESSAGE":
      return {
        ...state,
        messages: [...state.messages, { role: action.role, text: action.text }],
      };
    case "QUESTION_READY":
      return {
        ...state,
        status: "QUESTION",
        error: "",
        latestScores: action.scores ?? state.latestScores,
        messages: action.isFirst
          ? [{ role: "agent", text: action.agentText }]
          : [...state.messages, { role: "agent", text: action.agentText }],
      };
    case "LISTENING":
      return {
        ...state,
        status: "LISTENING",
        error: "",
      };
    case "TRANSCRIBING":
      return {
        ...state,
        status: "TRANSCRIBING",
        error: "",
      };
    case "WAITING_RESPONSE":
      return {
        ...state,
        status: "WAITING_RESPONSE",
        error: "",
        turnCount: action.appendUser ? state.turnCount + 1 : state.turnCount,
        messages: action.appendUser
          ? [...state.messages, { role: "user", text: action.userText }]
          : state.messages,
      };
    case "WRAP_UP":
      return {
        ...state,
        status: "WRAP_UP",
      };
    case "COMPLETED":
      return {
        ...state,
        status: "COMPLETED",
      };
    case "ERROR":
      return {
        ...state,
        status: "ERROR",
        error: action.error,
      };
    case "RETRY_FROM_ERROR":
      return {
        ...state,
        status: state.messages.length ? "QUESTION" : "STARTING",
        error: "",
      };
    case "BACK_TO_QUESTION":
      return {
        ...state,
        status: "QUESTION",
        error: "",
      };
    default:
      return state;
  }
}

function InterviewPage() {
  const router = useRouter();
  const [machine, dispatch] = useReducer(interviewReducer, initialMachineState);

  const [transcript, setTranscript] = useState("");
  const [lastTranscript, setLastTranscript] = useState("");
  const [timerSeconds, setTimerSeconds] = useState(0);
  const [timerMaxSecs, setTimerMaxSecs] = useState(0);
  const [durationId, setDurationId] = useState("");

  const currentQuestionIdRef = useRef<string>("");
  const currentQuestionTextRef = useRef<string>("");

  const transcriptRef = useRef("");
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const recognitionRef = useRef<SpeechRecognitionInstance | null>(null);
  const submitTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const transcriptPreviewTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const chatContainerRef = useRef<HTMLDivElement | null>(null);
  const chatBottomRef = useRef<HTMLDivElement | null>(null);

  const [interviewComplete, setInterviewComplete] = useState(false);

  const startedRef = useRef(false);
  const completingRef = useRef(false);
  const interviewCompleteRef = useRef(false);
  const wrapUpTriggeredRef = useRef(false);
  const requestInFlightRef = useRef(false);
  const restartRecordingAfterSilenceRef = useRef(false);
  const silenceRetriesRef = useRef(0);
  const pendingRequestRef = useRef<{ kind: "start" | "answer"; answer: string } | null>(null);
  // Synchronous boolean — set true when recording starts, false as soon as onEnd fires.
  // Avoids the async-useEffect lag of statusRef.
  const isListeningRef = useRef(false);

  // Stable refs that always point to the latest callback versions.
  // Used inside recognition event closures to avoid stale-closure bugs.
  const executeAnswerTurnRef = useRef<(answer: string, appendUser: boolean) => Promise<void>>(
    async () => {}
  );
  const startRecordingRef = useRef<() => void>(() => {});

  // Scroll to bottom whenever messages change or status changes
  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [machine.messages, machine.status]);

  const sendTurnWithRetry = useCallback(
    async (userAnswer: string, options?: { forceComplete?: boolean }) => {
      const maxAttempts = 3;
      let lastError: unknown = null;

      const language = machine.languageMode === "jp" ? "jp" : "en";

      for (let attempt = 1; attempt <= maxAttempts; attempt++) {
        try {
          return await sendInterviewTurn(
            userAnswer,
            machine.sessionId,
            machine.company,
            language,
            options
          );
        } catch (err) {
          lastError = err;
          if (attempt === maxAttempts) {
            break;
          }
          const jitter = Math.floor(Math.random() * 120);
          const delay = RETRY_BASE_DELAY_MS * 2 ** (attempt - 1) + jitter;
          await sleep(delay);
        }
      }

      throw lastError instanceof Error
        ? lastError
        : new Error("Turn request failed after retries.");
    },
    [machine.sessionId, machine.company, machine.languageMode]
  );

  const finalizeInterview = useCallback(async () => {
    if (completingRef.current || interviewCompleteRef.current || !machine.sessionId) {
      return;
    }

    completingRef.current = true;
    wrapUpTriggeredRef.current = true;
    isListeningRef.current = false;
    dispatch({ type: "WRAP_UP" });
    stopSpeech();

    if (recognitionRef.current) {
      recognitionRef.current.stop();
      recognitionRef.current = null;
    }

    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }

    if (requestInFlightRef.current) {
      const waitStartedAt = Date.now();
      while (requestInFlightRef.current && Date.now() - waitStartedAt < 3000) {
        await sleep(100);
      }
    }

    requestInFlightRef.current = true;
    pendingRequestRef.current = null;
    const ttsLang = machine.languageMode === "jp" ? "ja-JP" : "en-US";

    try {
      const res = await sendTurnWithRetry("[Timer wrap-up]", { forceComplete: true });
      const sid = machine.sessionId;

      if (
        res.interview_complete === true &&
        res.debrief_ready === true &&
        res.next_question === null
      ) {
        interviewCompleteRef.current = true;
        setInterviewComplete(true);
        session.setInterviewComplete(true);

        const closingLine = `Thank you for your time today. That concludes the interview. We appreciate your interest in ${machine.company || "the company"}.`;
        dispatch({ type: "APPEND_MESSAGE", role: "agent", text: closingLine });
        dispatch({ type: "COMPLETED" });
        await speakAndWait(closingLine, ttsLang);
        stopSpeech();
        router.push(`/debrief?session_id=${sid}`);
        return;
      }

      dispatch({
        type: "ERROR",
        error: "Interview wrap-up is still processing. Please wait and retry.",
      });
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Failed to finalize interview.";
      dispatch({ type: "ERROR", error: msg });
    } finally {
      requestInFlightRef.current = false;
      completingRef.current = false;
    }
  }, [machine.sessionId, machine.languageMode, machine.company, router, sendTurnWithRetry]);

  const executeStartTurn = useCallback(async () => {
    if (
      requestInFlightRef.current ||
      startedRef.current ||
      interviewCompleteRef.current ||
      wrapUpTriggeredRef.current ||
      !machine.sessionId
    ) {
      return;
    }

    startedRef.current = true;
    requestInFlightRef.current = true;
    pendingRequestRef.current = { kind: "start", answer: "start" };
    dispatch({ type: "STARTING" });

    const ttsLang = machine.languageMode === "jp" ? "ja-JP" : "en-US";

    try {
      const res = await sendTurnWithRetry("start");
      const sid = machine.sessionId;
      if (
        res.interview_complete === true &&
        res.debrief_ready === true &&
        res.next_question === null
      ) {
        if (!sid) {
          console.error("Missing session_id — cannot redirect to debrief");
          return;
        }
        interviewCompleteRef.current = true;
        setInterviewComplete(true);
        if (timerRef.current) {
          clearInterval(timerRef.current);
          timerRef.current = null;
        }
        if (res.interviewer_response) {
          dispatch({ type: "APPEND_MESSAGE", role: "agent", text: res.interviewer_response.trim() });
        }
        dispatch({ type: "COMPLETED" });
        stopSpeech();
        // give backend time to finalize result generation
        await new Promise(resolve => setTimeout(resolve, 2000));
        router.push(`/debrief?session_id=${sid}`);
        return;
      }

      const agentReply = res.interviewer_response?.trim() ?? "";
      const nextQuestion = res.next_question?.trim() || "Please introduce yourself.";
      currentQuestionIdRef.current = res.question_id ?? "q1";
      currentQuestionTextRef.current = nextQuestion;
      if (agentReply) {
        dispatch({ type: "APPEND_MESSAGE", role: "agent", text: agentReply });
        await sleep(400);
      }

      dispatch({
        type: "QUESTION_READY",
        agentText: nextQuestion,
        scores: res.scores,
        isFirst: !agentReply,
      });

      console.log("VOICE: TTS starting (first question)");
      if (res.voice_audio) {
        await playBase64Audio(res.voice_audio);
      } else {
        await speakAndWait(res.tts_text ?? [agentReply, nextQuestion].filter(Boolean), ttsLang);
      }
      console.log("VOICE: TTS done — auto-starting mic");

      if (!wrapUpTriggeredRef.current && !interviewCompleteRef.current) {
        startRecordingRef.current();
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Failed to start interview.";
      dispatch({ type: "ERROR", error: msg });
      startedRef.current = false;
    } finally {
      requestInFlightRef.current = false;
    }
  }, [machine.sessionId, machine.languageMode, sendTurnWithRetry, router]);

  const executeAnswerTurn = useCallback(
    async (answer: string, appendUser: boolean) => {
      if (
        requestInFlightRef.current ||
        interviewCompleteRef.current ||
        wrapUpTriggeredRef.current ||
        !machine.sessionId ||
        machine.status === "WRAP_UP" ||
        machine.status === "COMPLETED"
      ) {
        return;
      }

      const safeAnswer = answer.trim();
      if (!safeAnswer) {
        console.warn("VOICE: empty answer — restarting recording");
        restartRecordingAfterSilenceRef.current = true;
        dispatch({ type: "BACK_TO_QUESTION" });
        return;
      }

      console.log("VOICE: submitting answer");
      requestInFlightRef.current = true;
      pendingRequestRef.current = { kind: "answer", answer: safeAnswer };

      if (appendUser) {
        setLastTranscript(safeAnswer);
        if (transcriptPreviewTimeoutRef.current) {
          clearTimeout(transcriptPreviewTimeoutRef.current);
        }
        transcriptPreviewTimeoutRef.current = setTimeout(() => {
          setLastTranscript("");
        }, 2800);
      }

      dispatch({ type: "WAITING_RESPONSE", userText: safeAnswer, appendUser });

      const ttsLang = machine.languageMode === "jp" ? "ja-JP" : "en-US";

      try {
        const res = await sendTurnWithRetry(safeAnswer);
        const sid = machine.sessionId;
        if (
          res.interview_complete === true &&
          res.debrief_ready === true &&
          res.next_question === null
        ) {
          if (!sid) {
            console.error("Missing session_id — cannot redirect to debrief");
            return;
          }
          interviewCompleteRef.current = true;
          setInterviewComplete(true);
          if (timerRef.current) {
            clearInterval(timerRef.current);
            timerRef.current = null;
          }
          if (res.interviewer_response) {
            dispatch({ type: "APPEND_MESSAGE", role: "agent", text: res.interviewer_response.trim() });
          }
          session.setInterviewComplete(true);
          dispatch({ type: "COMPLETED" });
          stopSpeech();
          // give backend time to finalize result generation
          await new Promise(resolve => setTimeout(resolve, 2000));
          router.push(`/debrief?session_id=${sid}`);
          return;
        }

        if (wrapUpTriggeredRef.current) {
          return;
        }

        const agentReply = res.interviewer_response?.trim() ?? "";
        const nextQuestion = res.next_question?.trim() || "Please continue.";

        console.log("VOICE: next question received");
        currentQuestionIdRef.current = res.question_id ?? `q${machine.turnCount + 1}`;
        currentQuestionTextRef.current = nextQuestion;

        if (agentReply) {
          dispatch({ type: "APPEND_MESSAGE", role: "agent", text: agentReply });
          await sleep(400);
        }

        dispatch({
          type: "QUESTION_READY",
          agentText: nextQuestion,
          scores: res.scores,
          isFirst: false,
        });

        setTranscript("");
        transcriptRef.current = "";

        console.log("VOICE: TTS starting");
        if (res.voice_audio) {
          await playBase64Audio(res.voice_audio);
        } else {
          await speakAndWait(res.tts_text ?? [agentReply, nextQuestion].filter(Boolean), ttsLang);
        }
        console.log("VOICE: TTS done — auto-starting mic");

        if (!wrapUpTriggeredRef.current && !interviewCompleteRef.current) {
          startRecordingRef.current();
        }
      } catch (err) {
        const msg = err instanceof Error ? err.message : "Temporary network issue. Please try again.";
        dispatch({ type: "ERROR", error: msg });
      } finally {
        requestInFlightRef.current = false;
      }
    },
    [machine.sessionId, machine.status, machine.languageMode, machine.turnCount, sendTurnWithRetry, router]
  );

  // Keep stable refs in sync with the latest callback versions.
  useEffect(() => {
    executeAnswerTurnRef.current = executeAnswerTurn;
  }, [executeAnswerTurn]);

  useEffect(() => {
    if (machine.status === "IDLE" && machine.sessionId) {
      void executeStartTurn();
    }
  }, [machine.status, machine.sessionId, executeStartTurn]);

  useEffect(() => {
    if (
      timerMaxSecs > 0 &&
      timerSeconds <= WRAP_UP_SECONDS &&
      !wrapUpTriggeredRef.current &&
      !interviewCompleteRef.current &&
      machine.status !== "COMPLETED"
    ) {
      void finalizeInterview();
    }
  }, [timerSeconds, timerMaxSecs, machine.status, finalizeInterview]);

  const startRecording = useCallback(() => {
    if (machine.status !== "QUESTION" || wrapUpTriggeredRef.current) {
      return;
    }

    console.log("VOICE: listening");
    setTranscript("");
    transcriptRef.current = "";
    isListeningRef.current = true;
    dispatch({ type: "LISTENING" });

    const recognition = startSpeechRecognition(
      (text) => {
        setTranscript(text);
        transcriptRef.current = text;
      },
      {
        lang: machine.languageMode === "jp" ? "ja-JP" : "en-US",
        silenceTimeoutMs: SILENCE_TIMEOUT_MS,
        onError: (message) => {
          // Only surface errors that aren't caused by an expected stop
          if (isListeningRef.current) {
            dispatch({ type: "ERROR", error: message });
          }
        },
        onEnd: () => {
          // Use isListeningRef (synchronous) — avoids the async useEffect lag of statusRef
          if (!isListeningRef.current) return;
          isListeningRef.current = false;

          console.log("VOICE: recognition ended");

          if (wrapUpTriggeredRef.current || interviewCompleteRef.current) return;

          const answer = transcriptRef.current.trim();
          if (!answer) {
            console.warn("VOICE: no transcript captured — restarting");
            silenceRetriesRef.current += 1;
            if (silenceRetriesRef.current > 2) {
              console.warn("VOICE: silence retry limit reached — returning to question");
              silenceRetriesRef.current = 0;
              dispatch({ type: "BACK_TO_QUESTION" });
              return;
            }
            restartRecordingAfterSilenceRef.current = true;
            dispatch({ type: "BACK_TO_QUESTION" });
            return;
          }

          if (requestInFlightRef.current) {
            console.warn("VOICE: request already in flight — skipping duplicate submission");
            return;
          }

          silenceRetriesRef.current = 0;
          dispatch({ type: "TRANSCRIBING" });
          // Call via ref so we always invoke the latest closure — no setTimeout needed
          void executeAnswerTurnRef.current(answer, true);
        },
      }
    );

    if (!recognition) {
      isListeningRef.current = false;
      return;
    }

    recognitionRef.current = recognition;
  }, [machine.status, machine.languageMode]);

  // Keep startRecordingRef in sync
  useEffect(() => {
    startRecordingRef.current = startRecording;
  }, [startRecording]);

  const stopRecordingFull = useCallback(() => {
    if (wrapUpTriggeredRef.current) {
      return;
    }

    isListeningRef.current = false;
    if (recognitionRef.current) {
      recognitionRef.current.stop();
      recognitionRef.current = null;
    }
  }, []);

  // Auto-restart recording after a no-speech silence
  useEffect(() => {
    if (machine.status === "QUESTION" && restartRecordingAfterSilenceRef.current) {
      restartRecordingAfterSilenceRef.current = false;
      const timer = setTimeout(() => startRecording(), 600);
      return () => clearTimeout(timer);
    }
  }, [machine.status, startRecording]);

  const retryFailedRequest = useCallback(() => {
    if (wrapUpTriggeredRef.current) {
      return;
    }

    const pending = pendingRequestRef.current;
    if (!pending || requestInFlightRef.current) {
      return;
    }

    dispatch({ type: "RETRY_FROM_ERROR" });

    if (pending.kind === "start") {
      startedRef.current = false;
      void executeStartTurn();
      return;
    }

    void executeAnswerTurnRef.current(pending.answer, false);
  }, [executeStartTurn]);

  useEffect(() => {
    let id = session.getSessionId();
    const company = session.getCompany() ?? "rakuten";
    const languageMode = session.getLanguageMode() ?? "en";
    const durId = session.getDurationMode() ?? "demo";

    if (!id) {
      id = crypto.randomUUID();
      session.setSessionId(id);
    }

    if (!session.getCompany()) {
      session.setCompany(company);
    }

    dispatch({
      type: "SET_CONTEXT",
      sessionId: id,
      company,
      languageMode,
    });

    setDurationId(durId);

    const maxSecs =
      durId === "demo" ? 180 :
      durId === "10min" ? 600 :
      durId === "15min" ? 900 :
      durId === "30min" ? 1800 :
      durId === "60min" ? 3600 : 0;

    setTimerMaxSecs(maxSecs);

    if (maxSecs > 0) {
      setTimerSeconds(maxSecs);
      timerRef.current = setInterval(() => {
        setTimerSeconds((s) => Math.max(0, s - 1));
      }, 1000);
    } else {
      setTimerSeconds(0);
      timerRef.current = setInterval(() => {
        setTimerSeconds((s) => s + 1);
      }, 1000);
    }

    return () => {
      if (submitTimeoutRef.current) clearTimeout(submitTimeoutRef.current);
      if (transcriptPreviewTimeoutRef.current) clearTimeout(transcriptPreviewTimeoutRef.current);
      if (timerRef.current) clearInterval(timerRef.current);
      if (recognitionRef.current) recognitionRef.current.stop();
      stopSpeech();
    };
  }, []);

  const formatTime = (s: number) => {
    const m = Math.floor(s / 60);
    const sec = s % 60;
    return `${String(m).padStart(2, "0")}:${String(sec).padStart(2, "0")}`;
  };

  const isTimerWarning = timerMaxSecs > 0 && timerSeconds <= 60 && timerSeconds > 0;
  const isTimerCritical = timerMaxSecs > 0 && timerSeconds <= 20 && timerSeconds > 0;

  const isThinking = machine.status === "STARTING" || machine.status === "WAITING_RESPONSE";
  const inputDisabled =
    machine.status === "STARTING" ||
    machine.status === "TRANSCRIBING" ||
    machine.status === "WAITING_RESPONSE" ||
    machine.status === "WRAP_UP" ||
    machine.status === "COMPLETED";

  const avatarState =
    machine.status === "LISTENING"
      ? "listening"
      : machine.status === "TRANSCRIBING" || machine.status === "WAITING_RESPONSE" || machine.status === "STARTING"
      ? "processing"
      : machine.status === "QUESTION"
      ? "speaking"
      : "idle";

  const statusText =
    machine.status === "LISTENING"
      ? "Listening..."
      : machine.status === "TRANSCRIBING"
      ? "Transcribing..."
      : machine.status === "WAITING_RESPONSE" || machine.status === "STARTING"
      ? "MIRU is thinking..."
      : "Tap mic and speak";

  const normalizedLatestScores = machine.latestScores
    ? normalizeScores({ scores: machine.latestScores })
    : null;

  return (
    <div
      className="page-dark"
      style={{
        height: "100vh",
        display: "flex",
        flexDirection: "column",
        position: "relative",
        backgroundColor: "#050508",
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "18px 32px",
          borderBottom: "1px solid var(--border-subtle)",
          background: "rgba(5,5,8,0.85)",
          backdropFilter: "blur(20px)",
          flexShrink: 0,
          zIndex: 10,
        }}
      >
        <MiruLogo size="sm" />

        <div style={{ display: "flex", alignItems: "center", gap: 20 }}>
          <span
            style={{
              fontFamily: "var(--font-body)",
              fontSize: 13,
              color: "#8888aa",
            }}
          >
            {machine.company}
          </span>

          <span
            style={{
              fontFamily: "var(--font-body)",
              fontSize: 13,
              color: "var(--accent-primary)",
              fontWeight: 600,
            }}
          >
            Turns: {machine.turnCount}
          </span>

          <span
            style={{
              fontFamily: "var(--font-body)",
              fontSize: 14,
              color: isTimerCritical
                ? "#ef4444"
                : isTimerWarning
                ? "#ffb347"
                : "var(--text-secondary)",
              fontVariantNumeric: "tabular-nums",
              fontWeight: isTimerWarning ? 700 : 400,
              transition: "color 0.3s",
            }}
          >
            {timerMaxSecs > 0 ? "Time left: " : "Elapsed: "}
            {formatTime(timerSeconds)}
          </span>

          {durationId === "demo" && (
            <span
              style={{
                padding: "4px 10px",
                borderRadius: 6,
                background: "rgba(255,179,71,0.15)",
                border: "1px solid rgba(255,179,71,0.3)",
                color: "var(--accent-gold)",
                fontSize: 11,
                fontFamily: "var(--font-body)",
                fontWeight: 600,
                letterSpacing: "0.08em",
              }}
            >
              DEMO
            </span>
          )}
        </div>
      </div>

      <div
        style={{
          flex: 1,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "24px",
          maxWidth: 760,
          margin: "0 auto",
          width: "100%",
          gap: 14,
        }}
      >
        <HRAvatar state={avatarState} />

        <p
          style={{
            fontFamily: "var(--font-body)",
            fontSize: 13,
            color: "#a8a9c7",
            letterSpacing: "0.06em",
            textTransform: "uppercase",
          }}
        >
          {statusText}
        </p>

        <div
          ref={chatContainerRef}
          className="glass-card"
          style={{
            width: "100%",
            height: "70vh",
            overflowY: "auto",
            padding: "16px",
            borderRadius: 14,
            border: "1px solid var(--border-subtle)",
            display: "flex",
            flexDirection: "column",
            gap: 10,
          }}
        >
          {(machine.messages ?? []).map((m, idx) => (
            <div
              key={`${m.role}-${idx}`}
              style={{
                alignSelf: m.role === "user" ? "flex-end" : "flex-start",
                maxWidth: "80%",
                padding: "10px 14px",
                borderRadius: 12,
                background:
                  m.role === "user"
                    ? "rgba(40,131,186,0.22)"
                    : "rgba(255,255,255,0.06)",
                border:
                  m.role === "user"
                    ? "1px solid rgba(40,131,186,0.4)"
                    : "1px solid rgba(255,255,255,0.1)",
                color: "#f0f0ff",
                fontFamily: "var(--font-body)",
                fontSize: 14,
                lineHeight: 1.5,
              }}
            >
              <div
                style={{
                  fontSize: 11,
                  letterSpacing: "0.08em",
                  color: "#9fa0c3",
                  marginBottom: 4,
                }}
              >
                {m.role === "user" ? "YOU" : "MIRU"}
              </div>
              {m.text}
            </div>
          ))}

          {isThinking && (
            <div
              style={{
                alignSelf: "flex-start",
                maxWidth: "70%",
                padding: "10px 14px",
                borderRadius: 12,
                background: "rgba(255,255,255,0.04)",
                border: "1px solid rgba(255,255,255,0.1)",
                color: "#a8a9c7",
                fontFamily: "var(--font-body)",
                fontSize: 13,
              }}
            >
              MIRU is thinking...
            </div>
          )}

          <div ref={chatBottomRef} />
        </div>

        {lastTranscript && (
          <div
            className="glass-card"
            style={{
              width: "100%",
              padding: "10px 12px",
              borderRadius: 10,
              border: "1px solid rgba(255,255,255,0.12)",
              color: "#c8c9e6",
              fontFamily: "var(--font-body)",
              fontSize: 13,
            }}
          >
            <span style={{ color: "#9fa0c3", marginRight: 8 }}>You said:</span>
            &quot;{lastTranscript}&quot;
          </div>
        )}

        {normalizedLatestScores && (
          <div
            className="glass-card"
            style={{
              width: "100%",
              padding: "12px 14px",
              borderRadius: 12,
              border: "1px solid var(--border-subtle)",
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))",
              gap: 10,
              fontFamily: "var(--font-body)",
              fontSize: 13,
              color: "#c8c9e6",
            }}
          >
            <div>{DIMENSION_LABELS.wa_teamwork}: {normalizedLatestScores.wa_teamwork.toFixed(1)}</div>
            <div>{DIMENSION_LABELS.loyalty_commitment}: {normalizedLatestScores.loyalty_commitment.toFixed(1)}</div>
            <div>{DIMENSION_LABELS.humility}: {normalizedLatestScores.humility.toFixed(1)}</div>
            <div>{DIMENSION_LABELS.kaizen_growth}: {normalizedLatestScores.kaizen_growth.toFixed(1)}</div>
            <div>{DIMENSION_LABELS.cultural_fit}: {normalizedLatestScores.cultural_fit.toFixed(1)}</div>
          </div>
        )}

        <AnimatePresence>
          {machine.status === "ERROR" && machine.error && (
            <motion.div
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className="glass-card"
              style={{
                padding: "12px 18px",
                borderColor: "rgba(255,107,107,0.3)",
                color: "var(--accent-warm)",
                fontSize: 13,
                fontFamily: "var(--font-body)",
                maxWidth: 620,
                textAlign: "center",
                display: "flex",
                flexDirection: "column",
                gap: 10,
              }}
            >
              <span>{machine.error}</span>
              <button
                onClick={retryFailedRequest}
                style={{
                  alignSelf: "center",
                  padding: "8px 14px",
                  borderRadius: 8,
                  border: "1px solid rgba(255,255,255,0.2)",
                  background: "rgba(255,255,255,0.08)",
                  color: "#f0f0ff",
                  fontSize: 12,
                  fontFamily: "var(--font-body)",
                  cursor: "pointer",
                }}
              >
                Retry Request
              </button>
            </motion.div>
          )}
        </AnimatePresence>

        <VoiceInput
          isRecording={machine.status === "LISTENING"}
          transcript={transcript}
          onStartRecording={startRecording}
          onStopRecording={stopRecordingFull}
          disabled={inputDisabled}
          statusText={
            machine.status === "LISTENING"
              ? "Tap to stop · hold mic close"
              : machine.status === "TRANSCRIBING"
              ? "Processing your answer..."
              : machine.status === "WAITING_RESPONSE" || machine.status === "STARTING"
              ? "MIRU is speaking..."
              : machine.status === "COMPLETED"
              ? "Interview complete"
              : inputDisabled
              ? "Please wait..."
              : "Tap mic to answer"
          }
        />
      </div>

    </div>
  );
}

export default function InterviewPageWithBoundary() {
  return (
    <ErrorBoundary>
      <InterviewPage />
    </ErrorBoundary>
  );
}
