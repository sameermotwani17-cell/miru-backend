"use client";

import { useCallback, useEffect, useState } from "react";
import { motion } from "framer-motion";
import { useRouter } from "next/navigation";
import MiruLogo from "@/components/MiruLogo";
import MiruRadarChart from "@/components/MiruRadarChart";
import ScoreBar from "@/components/ScoreBar";
import { session } from "@/lib/session";
import type { FullResults, FeedbackObject, RadarScores, TranscriptTurn } from "@/lib/types";
import { DIMENSION_LABELS } from "@/lib/types";
import { normalizeScores } from "@/lib/resultsNormalizer";
import { getSessionId } from "@/lib/getSessionId";

type DebriefApiResponse = Partial<FullResults> & {
  status?: string;
  scores?: Partial<RadarScores>;
  turn_feedback?: unknown[] | Record<string, unknown>;
};

type CoachingTurn = {
  questionId: string;
  question: string;
  answer: string;
  score: number;
  feedback: string;
  better_example: string | null;
};

// Increased polling window to allow LLM evaluation to complete (up to 45 s)
const POLL_ATTEMPTS = 30;
const POLL_DELAY_MS = 1500;

function isReadyResponse(data: DebriefApiResponse | null): boolean {
  if (!data) return false;
  // Explicit ready status
  if (typeof data.status === "string" && data.status.toLowerCase() === "ready") {
    return true;
  }
  // Accept valid results even if status is missing or different
  // Accepts both array and object-map shapes (mirrors normalizeCoachingTurns)
  const tfLen = Array.isArray(data.turn_feedback)
    ? data.turn_feedback.length
    : Object.keys(data.turn_feedback ?? {}).length;
  const hasTurnFeedback = tfLen > 0;
  const hasScores =
    !!(data.radar_scores ?? data.scores);
  return hasTurnFeedback || hasScores;
}

function SectionHeader({ label, title }: { label: string; title: string }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
      style={{ marginBottom: 32 }}
    >
      <p
        style={{
          fontSize: 11,
          color: "var(--text-page-accent)",
          letterSpacing: "0.14em",
          fontFamily: "var(--font-body)",
          marginBottom: 6,
          fontWeight: 600,
        }}
      >
        {label}
      </p>
      <h2
        style={{
          fontFamily: "var(--font-display)",
          fontSize: "clamp(22px, 4vw, 32px)",
          fontWeight: 700,
          color: "var(--text-page-heading)",
          lineHeight: 1.2,
        }}
      >
        {title}
      </h2>
    </motion.div>
  );
}

function getLowestDimension(scores: RadarScores): keyof RadarScores {
  return (Object.keys(scores) as (keyof RadarScores)[]).reduce((a, b) =>
    Number(scores[a] ?? 0) < Number(scores[b] ?? 0) ? a : b
  );
}

function getAvgScore(scores: RadarScores): number {
  const vals = Object.values(scores).map((v) => Number(v ?? 0));
  if (!vals.length) return 0;
  return vals.reduce((a, b) => a + b, 0) / vals.length;
}

function getScoreColor(score: number): string {
  if (score >= 7) return "var(--accent-green)";
  if (score >= 4) return "var(--accent-gold)";
  return "var(--accent-warm)";
}

function toNumber(value: unknown): number | null {
  const n = typeof value === "number" ? value : Number(value);
  return Number.isFinite(n) ? n : null;
}

function avgFromScores(scores: unknown): number | undefined {
  if (!scores || typeof scores !== "object") return undefined;
  const values = Object.values(scores as Record<string, unknown>)
    .map((v) => toNumber(v))
    .filter((v): v is number => v !== null);
  if (!values.length) return undefined;
  return values.reduce((a, b) => a + b, 0) / values.length;
}

// ── Normalization helpers ────────────────────────────────────────────────────

/**
 * Remaps per-turn `evaluation` → `scores` so that normalizeScores (which only
 * reads `.scores`) can compute the radar chart when the backend stores dimension
 * scores under `evaluation` instead of `scores`.
 */
function remapEvaluationToScores(data: DebriefApiResponse): DebriefApiResponse {
  const rawTurns = Array.isArray(data.turn_feedback)
    ? data.turn_feedback
    : Object.values(data.turn_feedback ?? {});

  if (!rawTurns.length) return data;

  const remapped = rawTurns.map((item) => {
    const t = (item ?? {}) as Record<string, unknown>;
    // Only remap when `scores` is absent and `evaluation` is a plain object
    if (!t.scores && t.evaluation && typeof t.evaluation === "object" && !Array.isArray(t.evaluation)) {
      return { ...t, scores: t.evaluation };
    }
    return t;
  });

  return { ...data, turn_feedback: remapped };
}

function normalizeCoachingTurns(raw: DebriefApiResponse): CoachingTurn[] {
  console.log("turn_feedback raw:", raw.turn_feedback);

  // STEP 1 — normalise array vs object-map shape
  const turns = Array.isArray(raw.turn_feedback)
    ? raw.turn_feedback
    : Object.values(raw.turn_feedback || {});

  if (turns.length) {
    console.log("first turn keys:", Object.keys(turns[0] as object));
    return turns.map((item, index) => {
      const turn = (item ?? {}) as Record<string, unknown>;

      // STEP 2 — score: explicit fields → averaged scores obj → averaged evaluation obj
      const explicitScore =
        toNumber(turn.score) ??
        toNumber(turn.final_score) ??
        toNumber(turn.overall_score);
      const computedScore =
        explicitScore ??
        avgFromScores(turn.scores) ??
        avgFromScores(turn.evaluation);

      // STEP 2 — question: multiple alias keys, category as last resort
      const question =
        String(
          turn.question ??
          turn.prompt ??
          turn.question_text ??
          turn.question_prompt ??
          turn.question_category ??
          ""
        ) || "Interview Question";   // STEP 3 fallback

      // STEP 2 — answer: multiple alias keys
      // Return "" when absent so the display renders the "No speech detected" fallback
      const answer = String(
        turn.answer ??
        turn.user_answer ??
        turn.candidate_answer ??
        ""
      );                             // STEP 3: display uses || "No speech detected"

      // STEP 2 — feedback: explicit field → coaching alias → evaluation notes
      const feedback = String(
        turn.feedback ??
        turn.coaching_feedback ??
        (turn.evaluation as Record<string, unknown> | undefined)?.notes ??
        "No feedback available."     // STEP 3 fallback
      );

      // STEP 2 — better example: multiple alias keys
      // rewrite_example is the raw backend field name from feedback_engine
      const betterExample =
        turn.better_example ??
        turn.rewrite_example ??
        turn.rewrite ??
        turn.improved_answer ??
        null;
      const better_example = betterExample !== null ? String(betterExample) : null;

      return {
        questionId: String(turn.question_id ?? `q${index + 1}`),
        question,
        answer,
        score: Math.max(0, Math.min(10, computedScore || 0)),
        feedback,
        better_example,
      };
    });
  }

  const transcriptTurns: TranscriptTurn[] = Array.isArray(raw.transcript)
    ? (raw.transcript as TranscriptTurn[])
    : [];

  const interviewerTurns = transcriptTurns.filter((t) => t.role === "interviewer");
  const candidateTurns = transcriptTurns.filter((t) => t.role === "candidate");

  return interviewerTurns.map((turn, index) => ({
    questionId: `q${index + 1}`,
    question: turn.text,
    answer: candidateTurns[index]?.text ?? "No answer captured",
    score: 0,
    feedback: "No feedback available.",
    better_example: null,
  }));
}

function renderFeedback(fb: string | FeedbackObject | null | undefined) {
  if (!fb) {
    return (
      <p
        style={{
          fontFamily: "var(--font-body)",
          fontSize: 14,
          color: "var(--text-page-body)",
          lineHeight: 1.7,
        }}
      >
        No feedback available for this session.
      </p>
    );
  }

  if (typeof fb === "string") {
    return (
      <p
        style={{
          fontFamily: "var(--font-body)",
          fontSize: 14,
          color: "var(--text-page-body)",
          lineHeight: 1.7,
        }}
      >
        {fb}
      </p>
    );
  }

  const subsectionLabel = (text: string, color: string) => (
    <p
      style={{
        fontSize: 11,
        color,
        letterSpacing: "0.1em",
        fontFamily: "var(--font-body)",
        fontWeight: 600,
        marginBottom: 6,
        textTransform: "uppercase" as const,
      }}
    >
      {text}
    </p>
  );

  const bodyText = (text: string) => (
    <p
      style={{
        fontFamily: "var(--font-body)",
        fontSize: 14,
        color: "var(--text-page-body)",
        lineHeight: 1.7,
        marginBottom: 0,
      }}
    >
      {text}
    </p>
  );

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
      {fb.summary && (
        <div>
          {subsectionLabel("Summary", "var(--accent-gold)")}
          {bodyText(fb.summary)}
        </div>
      )}
      {fb.strengths && (
        <div>
          {subsectionLabel("Strengths", "var(--accent-green)")}
          {bodyText(fb.strengths)}
        </div>
      )}
      {fb.areas_for_improvement && (
        <div>
          {subsectionLabel("Areas for Improvement", "var(--accent-warm)")}
          {bodyText(fb.areas_for_improvement)}
        </div>
      )}
      {!fb.summary && !fb.strengths && !fb.areas_for_improvement && (
        <p
          style={{
            fontFamily: "var(--font-body)",
            fontSize: 14,
            color: "var(--text-page-body)",
            lineHeight: 1.7,
          }}
        >
          No feedback available for this session.
        </p>
      )}
    </div>
  );
}

export default function DebriefContent() {
  const router = useRouter();
  const [results, setResults] = useState<FullResults | null>(null);
  const [coachingTurns, setCoachingTurns] = useState<CoachingTurn[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingMessage, setLoadingMessage] = useState("");
  const [error, setError] = useState("");

  const loadResults = useCallback(async () => {
    setLoading(true);
    setError("");
    setLoadingMessage("Analyzing interview results...");

    const id = getSessionId();
    if (!id) {
      setError("Session not found. Please start a new interview.");
      setLoading(false);
      return;
    }

    session.setSessionId(id);

    console.log("Fetching results for session:", id);

    try {
      let data: DebriefApiResponse | null = null;

      for (let attempt = 0; attempt < POLL_ATTEMPTS; attempt++) {
        console.log("Polling results attempt", attempt + 1);

        const res = await fetch(
          `/api/interview/results?session_id=${encodeURIComponent(id)}`
        ).catch(() => null);

        const parsed = res
          ? ((await res.json().catch(() => null)) as DebriefApiResponse | null)
          : null;

        console.log("Results received:", parsed);

        if (parsed && isReadyResponse(parsed)) {
          data = parsed;
          break;
        }

        if (attempt < POLL_ATTEMPTS - 1) {
          await new Promise((r) => setTimeout(r, POLL_DELAY_MS));
        }
      }

      if (!data) {
        setError("Unable to load interview results.");
        return;
      }

      // Remap evaluation→scores per turn so normalizeScores can average them
      // when the backend stores dimension scores under `evaluation` instead of `scores`.
      const dataForScores = remapEvaluationToScores(data);

      const normalized: FullResults = {
        radar_scores: normalizeScores(dataForScores),
        transcript: Array.isArray(data.transcript) ? data.transcript : [],
        feedback: data.feedback ?? "",
        hiring_signal: data.hiring_signal ?? "",
      };

      setResults(normalized);
      setCoachingTurns(normalizeCoachingTurns(data));
    } catch {
      setError("Unable to load interview results.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadResults();
  }, [loadResults]);

  const handlePracticeAgain = () => {
    session.clearForNewSession();
    router.push("/onboarding");
  };

  const handleDifferentCompany = () => {
    session.removeCompany();
    router.push("/onboarding");
  };

  if (loading) {
    return (
      <div
        style={{
          minHeight: "100vh",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          flexDirection: "column",
          gap: 20,
        }}
      >
        <motion.div
          animate={{ rotate: 360 }}
          transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
          style={{
            width: 40,
            height: 40,
            borderRadius: "50%",
            border: "2px solid rgba(40,131,186,0.15)",
            borderTopColor: "#2883ba",
          }}
        />
        <p
          style={{
            fontFamily: "var(--font-body)",
            color: "var(--text-page-body)",
            fontSize: 14,
          }}
        >
          {loadingMessage}
        </p>
      </div>
    );
  }

  if (error || !results) {
    return (
      <div
        style={{
          minHeight: "100vh",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          padding: 24,
        }}
      >
        <div
          className="glass-card"
          style={{
            padding: 32,
            maxWidth: 480,
            textAlign: "center",
          }}
        >
          <p
            style={{
              color: "var(--accent-warm)",
              fontFamily: "var(--font-body)",
              marginBottom: 16,
            }}
          >
            {error || "No results found."}
          </p>
          <div style={{ display: "flex", gap: 12, justifyContent: "center" }}>
            <button
              onClick={loadResults}
              style={{
                padding: "10px 24px",
                borderRadius: 8,
                border: "none",
                background: "#2883ba",
                color: "#ffffff",
                fontFamily: "var(--font-body)",
                cursor: "pointer",
                fontWeight: 600,
              }}
            >
              Retry
            </button>
            <button
              onClick={() => router.push("/")}
              style={{
                padding: "10px 24px",
                borderRadius: 8,
                border: "1px solid rgba(40,131,186,0.2)",
                background: "transparent",
                color: "#4a6a8a",
                fontFamily: "var(--font-body)",
                cursor: "pointer",
              }}
            >
              Return Home
            </button>
          </div>
        </div>
      </div>
    );
  }

  const safeScores = normalizeScores(results);
  const feedback = results.feedback ?? null;
  const hiringSignal = results.hiring_signal ?? "";

  const radarKeys = Object.keys(safeScores) as (keyof RadarScores)[];
  const lowestDim = radarKeys.length
    ? getLowestDimension(safeScores)
    : ("wa_teamwork" as keyof RadarScores);
  const avgScore = radarKeys.length ? getAvgScore(safeScores) : 0;
  const company = session.getCompany() ?? "";
  const sessionId = session.getSessionId() ?? "";
  const transcript = results.transcript ?? [];

  console.log("Transcript data:", transcript);

  return (
    <div className="page-light" style={{ minHeight: "100vh", paddingBottom: 120 }}>
      <div className="print-header">
        <h1>MIRU - Interview Report</h1>
        <p>
          Company: {company || "-"} · Date: {new Date().toLocaleDateString()} · Session: {sessionId.slice(0, 8)}
        </p>
      </div>

      <nav
        className="no-print dark-surface"
        style={{
          position: "sticky",
          top: 0,
          zIndex: 50,
          padding: "14px 32px",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          borderBottom: "1px solid rgba(13,58,95,0.3)",
          background: "#0d3a5f",
        }}
      >
        <MiruLogo size="sm" />
        <div style={{ display: "flex", gap: 12 }}>
          <button
            onClick={handleDifferentCompany}
            style={{
              padding: "8px 18px",
              borderRadius: 8,
              border: "1px solid rgba(255,255,255,0.2)",
              background: "transparent",
              color: "rgba(255,255,255,0.75)",
              fontFamily: "var(--font-body)",
              fontSize: 13,
              cursor: "pointer",
            }}
          >
            Try Different Company
          </button>
          <button
            onClick={handlePracticeAgain}
            style={{
              padding: "8px 18px",
              borderRadius: 8,
              border: "none",
              background: "rgba(255,255,255,0.15)",
              color: "#ffffff",
              fontFamily: "var(--font-body)",
              fontSize: 13,
              cursor: "pointer",
              fontWeight: 600,
            }}
          >
            Practice Again
          </button>
        </div>
      </nav>

      <div style={{ maxWidth: 900, margin: "0 auto", padding: "60px 24px 40px" }}>
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
          style={{ textAlign: "center", marginBottom: 72 }}
        >
          <p
            style={{
              fontFamily: "var(--font-japanese)",
              fontSize: 14,
              color: "var(--text-page-accent)",
              marginBottom: 16,
            }}
          >
            面接フィードバック
          </p>
          <h1
            style={{
              fontFamily: "var(--font-display)",
              fontSize: "clamp(32px, 6vw, 56px)",
              fontWeight: 700,
              color: "var(--text-page-heading)",
              marginBottom: 12,
            }}
          >
            Your Debrief
          </h1>
          <div
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 10,
              padding: "10px 24px",
              borderRadius: 999,
              border: `1px solid ${getScoreColor(avgScore)}40`,
              background: `${getScoreColor(avgScore)}0D`,
            }}
          >
            <span
              style={{
                fontFamily: "var(--font-display)",
                fontSize: 28,
                fontWeight: 800,
                color: getScoreColor(avgScore),
              }}
            >
              {avgScore.toFixed(1)}
            </span>
            <span
              style={{
                fontFamily: "var(--font-body)",
                fontSize: 13,
                color: "var(--text-page-body)",
              }}
            >
              / 10 overall
            </span>
          </div>
        </motion.div>

        <section style={{ marginBottom: 80 }}>
          <SectionHeader label="SECTION 01" title="Score Overview" />

          <div className="glass-card radar-chart-wrapper" style={{ padding: 32, marginBottom: 28 }}>
            <MiruRadarChart scores={safeScores} />
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {(Object.keys(safeScores) as (keyof RadarScores)[]).map((key, i) => (
              <ScoreBar
                key={key}
                label={DIMENSION_LABELS[key]}
                score={safeScores[key]}
                delay={i * 0.05}
                highlight={key === lowestDim}
              />
            ))}
          </div>
        </section>

        <section style={{ marginBottom: 80 }}>
          <SectionHeader label="SECTION 02" title="Interviewer Feedback" />

          <div className="glass-card" style={{ padding: "28px 32px", borderColor: "rgba(245,158,11,0.3)" }}>
            <p
              style={{
                fontSize: 11,
                color: "var(--accent-gold)",
                letterSpacing: "0.1em",
                fontFamily: "var(--font-body)",
                fontWeight: 600,
                marginBottom: 16,
              }}
            >
              OVERALL ASSESSMENT
            </p>
            {renderFeedback(feedback)}
          </div>
        </section>

        {coachingTurns.length > 0 && (
          <section style={{ marginBottom: 80 }}>
            <SectionHeader label="SECTION 03" title="Coaching Breakdown" />
            <p
              style={{
                fontFamily: "var(--font-body)",
                fontSize: 14,
                color: "var(--text-page-body)",
                marginBottom: 28,
                lineHeight: 1.6,
              }}
            >
              Question-by-question review with coaching guidance and example rewrites.
            </p>

            <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
              {coachingTurns.map((item, i) => (
                <motion.div
                  key={item.questionId}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true, margin: "-60px" }}
                  transition={{ duration: 0.5, delay: i * 0.05, ease: [0.16, 1, 0.3, 1] }}
                  className="debrief-card glass-card flex flex-col gap-4"
                  style={{ padding: "24px 24px", borderColor: "rgba(40,131,186,0.2)" }}
                >
                  <span
                    style={{
                      fontFamily: "var(--font-body)",
                      fontSize: 11,
                      color: "var(--text-dim)",
                      letterSpacing: "0.1em",
                      display: "block",
                    }}
                  >
                    QUESTION {i + 1}
                  </span>

                  <h3 style={{ fontFamily: "var(--font-body)", fontSize: 16, color: "#0d3a5f", fontWeight: 600 }}>Question</h3>
                  <p style={{ fontFamily: "var(--font-display)", fontSize: 16, color: "#0d3a5f", lineHeight: 1.5 }}>
                    {item.question}
                  </p>

                  <h4 style={{ fontFamily: "var(--font-body)", fontSize: 13, color: "var(--text-dim)" }}>Your Answer</h4>
                  <p style={{ fontFamily: "var(--font-body)", fontSize: 13, color: "var(--text-secondary)", lineHeight: 1.6 }}>
                    {item.answer || "No speech detected"}
                  </p>

                  <h4 style={{ fontFamily: "var(--font-body)", fontSize: 13, color: "var(--accent-gold)" }}>Score</h4>
                  <p className="text-xl font-bold text-yellow-400">{item.score.toFixed(1)}/10</p>

                  <h4 style={{ fontFamily: "var(--font-body)", fontSize: 13, color: "var(--accent-warm)" }}>Feedback</h4>
                  <p style={{ fontFamily: "var(--font-body)", fontSize: 13, color: "var(--text-page-body)", lineHeight: 1.6 }}>
                    {item.feedback}
                  </p>

                  <h4 style={{ fontFamily: "var(--font-body)", fontSize: 13, color: "var(--accent-green)" }}>
                    Better Answer Example
                  </h4>
                  <p style={{ fontFamily: "var(--font-body)", fontSize: 13, color: "var(--text-page-body)", lineHeight: 1.7 }}>
                    {item.better_example ?? "No coaching example available."}
                  </p>
                </motion.div>
              ))}
            </div>
          </section>
        )}

        <section style={{ marginBottom: 80 }}>
          <SectionHeader label="SECTION 04" title="Hiring Signal" />

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1.1fr", gap: 28, alignItems: "start" }}>
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 20 }}>
                <div
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: 8,
                    padding: "8px 18px",
                    borderRadius: 999,
                    border: `1px solid ${getScoreColor(avgScore)}50`,
                    background: `${getScoreColor(avgScore)}12`,
                  }}
                >
                  <span
                    style={{
                      fontFamily: "var(--font-display)",
                      fontSize: 22,
                      fontWeight: 800,
                      color: getScoreColor(avgScore),
                    }}
                  >
                    {avgScore.toFixed(1)}
                  </span>
                  <span
                    style={{
                      fontFamily: "var(--font-body)",
                      fontSize: 12,
                      color: "var(--text-page-muted)",
                    }}
                  >
                    / 10
                  </span>
                </div>
                <span
                  style={{
                    fontFamily: "var(--font-body)",
                    fontSize: 12,
                    color: "var(--text-page-muted)",
                    letterSpacing: "0.06em",
                    textTransform: "uppercase" as const,
                  }}
                >
                  Overall Score
                </span>
              </div>

              <div className="glass-card radar-chart-wrapper" style={{ padding: "16px 16px 8px", marginBottom: 20 }}>
                <div className="w-full h-[420px] flex items-center justify-center">
                  <div style={{ width: 420, height: 320 }}>
                    <MiruRadarChart scores={safeScores} />
                  </div>
                </div>
              </div>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
              <div className="glass-card" style={{ padding: "20px 22px", borderColor: "rgba(40,131,186,0.2)" }}>
                <p
                  style={{
                    fontSize: 10,
                    color: "#2883ba",
                    letterSpacing: "0.1em",
                    fontFamily: "var(--font-body)",
                    fontWeight: 700,
                    marginBottom: 10,
                  }}
                >
                  HIRING SIGNAL
                </p>
                <p
                  style={{
                    fontFamily: "var(--font-body)",
                    fontSize: 13,
                    color: "var(--text-secondary)",
                    lineHeight: 1.7,
                  }}
                >
                  {hiringSignal || "Assessment pending."}
                </p>
              </div>

              {company && (
                <div className="insight-card">
                  <span className="insight-label">{company.toUpperCase()} INTERVIEW</span>
                  <p className="insight-body">Session ID: {sessionId.slice(0, 8)}</p>
                </div>
              )}
            </div>
          </div>
        </section>
      </div>

      <div
        className="no-print"
        style={{
          position: "fixed",
          bottom: 32,
          right: 32,
          zIndex: 100,
          display: "flex",
          flexDirection: "column",
          gap: 10,
        }}
      >
        <motion.button
          onClick={() => window.print()}
          whileHover={{ scale: 1.04, boxShadow: "0 0 28px rgba(40,131,186,0.45)" }}
          whileTap={{ scale: 0.97 }}
          style={{
            padding: "13px 22px",
            borderRadius: 12,
            background: "#2883ba",
            border: "none",
            color: "#fff",
            fontFamily: "var(--font-body)",
            fontSize: 14,
            fontWeight: 700,
            cursor: "pointer",
            boxShadow: "0 4px 20px rgba(40,131,186,0.35)",
            letterSpacing: "0.02em",
          }}
        >
          Download Report
        </motion.button>
        <motion.button
          onClick={handlePracticeAgain}
          whileHover={{ scale: 1.03 }}
          whileTap={{ scale: 0.97 }}
          style={{
            padding: "11px 22px",
            borderRadius: 12,
            border: "1px solid rgba(13,58,95,0.2)",
            background: "rgba(255,255,255,0.92)",
            backdropFilter: "blur(8px)",
            color: "#0d3a5f",
            fontFamily: "var(--font-body)",
            fontSize: 13,
            fontWeight: 600,
            cursor: "pointer",
            boxShadow: "0 2px 12px rgba(13,58,95,0.1)",
          }}
        >
          Start Again
        </motion.button>
      </div>
    </div>
  );
}
