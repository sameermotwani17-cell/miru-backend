import type { FullResults } from "./types";

const KEYS = {
  SESSION_ID: "saiko_session_id",
  COMPANY: "saiko_company",
  LANGUAGE_MODE: "saiko_language_mode",
  CV_TEXT: "saiko_cv_text",
  INTERVIEW_STARTED: "saiko_interview_started",
  INTERVIEW_COMPLETE: "saiko_interview_complete",
  QUESTION_COUNT: "saiko_question_count",
  QUESTION_COUNT_TARGET: "saiko_question_count_target",
  DURATION_MODE: "saiko_duration_mode",
  CANDIDATE_NAME: "saiko_candidate_name",
  TARGET_ROLE: "saiko_target_role",
  RESULTS: "saiko_results",
} as const;

function safe<T>(fn: () => T): T | null {
  if (typeof window === "undefined") return null;
  try {
    return fn();
  } catch {
    return null;
  }
}

export const session = {
  getSessionId: () => safe(() => sessionStorage.getItem(KEYS.SESSION_ID)),
  setSessionId: (v: string) =>
    safe(() => sessionStorage.setItem(KEYS.SESSION_ID, v)),

  getCompany: () => safe(() => sessionStorage.getItem(KEYS.COMPANY)),
  setCompany: (v: string) =>
    safe(() => sessionStorage.setItem(KEYS.COMPANY, v)),
  removeCompany: () => safe(() => sessionStorage.removeItem(KEYS.COMPANY)),

  getLanguageMode: () => safe(() => sessionStorage.getItem(KEYS.LANGUAGE_MODE)),
  setLanguageMode: (v: string) =>
    safe(() => sessionStorage.setItem(KEYS.LANGUAGE_MODE, v)),

  getCvText: () => safe(() => sessionStorage.getItem(KEYS.CV_TEXT)),
  setCvText: (v: string) =>
    safe(() => sessionStorage.setItem(KEYS.CV_TEXT, v)),

  getDurationMode: () => safe(() => sessionStorage.getItem(KEYS.DURATION_MODE)),
  setDurationMode: (v: string) =>
    safe(() => sessionStorage.setItem(KEYS.DURATION_MODE, v)),

  getInterviewStarted: () =>
    safe(() => sessionStorage.getItem(KEYS.INTERVIEW_STARTED) === "true"),
  setInterviewStarted: (v: boolean) =>
    safe(() => sessionStorage.setItem(KEYS.INTERVIEW_STARTED, String(v))),

  getInterviewComplete: () =>
    safe(() => sessionStorage.getItem(KEYS.INTERVIEW_COMPLETE) === "true"),
  setInterviewComplete: (v: boolean) =>
    safe(() => sessionStorage.setItem(KEYS.INTERVIEW_COMPLETE, String(v))),

  getQuestionCount: () =>
    safe(() => {
      const v = sessionStorage.getItem(KEYS.QUESTION_COUNT);
      return v ? parseInt(v, 10) : null;
    }),
  setQuestionCount: (v: number) =>
    safe(() => sessionStorage.setItem(KEYS.QUESTION_COUNT, String(v))),

  getQuestionCountTarget: (): number | null =>
    safe(() => {
      const v = sessionStorage.getItem(KEYS.QUESTION_COUNT_TARGET);
      return v ? parseInt(v, 10) : null;
    }),
  setQuestionCountTarget: (v: number | null) =>
    safe(() => {
      if (v === null) sessionStorage.removeItem(KEYS.QUESTION_COUNT_TARGET);
      else sessionStorage.setItem(KEYS.QUESTION_COUNT_TARGET, String(v));
    }),

  getCandidateName: () =>
    safe(() => sessionStorage.getItem(KEYS.CANDIDATE_NAME)),
  setCandidateName: (v: string) =>
    safe(() => sessionStorage.setItem(KEYS.CANDIDATE_NAME, v)),

  getTargetRole: () => safe(() => sessionStorage.getItem(KEYS.TARGET_ROLE)),
  setTargetRole: (v: string) =>
    safe(() => sessionStorage.setItem(KEYS.TARGET_ROLE, v)),

  getResults: (): FullResults | null =>
    safe(() => {
      const raw = sessionStorage.getItem(KEYS.RESULTS);
      return raw ? (JSON.parse(raw) as FullResults) : null;
    }),
  setResults: (v: FullResults) =>
    safe(() => sessionStorage.setItem(KEYS.RESULTS, JSON.stringify(v))),

  clear: () =>
    safe(() => {
      Object.values(KEYS).forEach((k) => sessionStorage.removeItem(k));
    }),

  clearForNewSession: () =>
    safe(() => {
      sessionStorage.clear();
    }),
};
