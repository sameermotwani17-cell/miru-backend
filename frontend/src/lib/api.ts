import type {
  StartPayload,
  StartResponse,
  TurnResponse,
  InterviewTurnResponse,
  FullResults,
  RadarScores,
  FinalReport,
  Transcript,
} from "./types";

const DEFAULT_FETCH_TIMEOUT_MS = 20_000;

function normalizeCompanyForBackend(company: string): string {
  const raw = company.trim().toLowerCase();
  const map: Record<string, string> = {
    toyota: "toyota",
    rakuten: "rakuten",
    sony: "sony",
    softbank: "softbank",
    uniqlo: "uniqlo",
  };

  return map[raw] ?? raw;
}

const BASE =
  process.env.NEXT_PUBLIC_API_URL ?? "https://miru-backend-production.up.railway.app";

const API_URL =
  process.env.NEXT_PUBLIC_API_URL ||
  "https://miru-backend-production.up.railway.app";

class ApiError extends Error {
  constructor(
    public status: number,
    message: string
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function fetchWithTimeout(
  url: string,
  options: RequestInit,
  timeoutMs: number = DEFAULT_FETCH_TIMEOUT_MS
): Promise<Response> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    return await fetch(url, {
      ...options,
      signal: controller.signal,
    });
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") {
      throw new ApiError(408, "MIRU is thinking longer than expected...");
    }
    throw err;
  } finally {
    clearTimeout(timeoutId);
  }
}

async function request<T>(
  path: string,
  options?: RequestInit
): Promise<T> {
  const url = `${BASE}${path}`;
  const res = await fetchWithTimeout(url, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });

  if (!res.ok) {
    let message = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      message = body.detail ?? body.message ?? message;
    } catch {
      // ignore parse errors
    }
    throw new ApiError(res.status, message);
  }

  return res.json() as Promise<T>;
}

export async function startInterview(
  payload: StartPayload
): Promise<StartResponse> {
  return request<StartResponse>("/api/session/start", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function submitTurn(
  sessionId: string,
  answer: string,
  languageMode: string
): Promise<TurnResponse> {
  return request<TurnResponse>("/api/interview/turn", {
    method: "POST",
    body: JSON.stringify({
      session_id: sessionId,
      user_answer: answer,
      language_mode: languageMode,
    }),
  });
}

export async function sendInterviewTurn(
  userAnswer: string,
  sessionId: string,
  company: string,
  language: "en" | "jp",
  options?: { forceComplete?: boolean }
): Promise<InterviewTurnResponse> {
  const normalizedCompany = normalizeCompanyForBackend(company);
  const safeAnswer = userAnswer.trim().length === 0 ? "start" : userAnswer;

  for (let attempt = 1; attempt <= 2; attempt++) {
    console.log("Sending interview turn", {
      sessionId,
      company: normalizedCompany,
      attempt,
    });

    try {
      const response = await fetchWithTimeout(
        `${API_URL}/api/interview/turn`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            company: normalizedCompany,
            session_id: sessionId,
            user_answer: safeAnswer,
            voice_mode: true,
            ...(options?.forceComplete ? { force_complete: true } : {}),
          }),
        }
      );

      console.log("Response received", {
        sessionId,
        status: response.status,
        ok: response.ok,
        attempt,
      });

      if (!response.ok) {
        let messageText = `HTTP ${response.status}`;
        try {
          const body = await response.json();
          messageText = body.detail ?? body.message ?? messageText;
        } catch {
          // ignore parse errors
        }
        throw new ApiError(response.status, messageText);
      }

      return response.json() as Promise<InterviewTurnResponse>;
    } catch (err) {
      if (err instanceof ApiError && err.status === 408 && attempt === 1) {
        console.warn("Interview turn timed out; retrying once", { sessionId });
        continue;
      }
      throw err;
    }
  }

  throw new ApiError(408, "MIRU is thinking longer than expected...");
}

export async function getResults(sessionId: string): Promise<FullResults> {
  return request<FullResults>(`/api/interview/${sessionId}/results`);
}

export async function getRadar(sessionId: string): Promise<RadarScores> {
  return request<RadarScores>(`/api/interview/${sessionId}/radar`);
}

export async function getReport(sessionId: string): Promise<FinalReport> {
  return request<FinalReport>(`/api/interview/${sessionId}/report`);
}

export async function getFeedback(
  sessionId: string
): Promise<{ turns: import("./types").TurnFeedback[] }> {
  return request<{ turns: import("./types").TurnFeedback[] }>(
    `/api/interview/${sessionId}/feedback`
  );
}

export async function getTranscript(sessionId: string): Promise<Transcript> {
  return request<Transcript>(`/api/interview/${sessionId}/transcript`);
}
