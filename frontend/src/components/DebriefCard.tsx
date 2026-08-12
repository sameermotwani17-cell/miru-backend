"use client";

import { motion } from "framer-motion";
import type { TurnFeedback } from "@/lib/types";
import { DIMENSION_LABELS } from "@/lib/types";

interface DebriefCardProps {
  turn: TurnFeedback;
  index: number;
}

function getScoreColor(score: number): string {
  if (score >= 7) return "var(--accent-green)";
  if (score >= 4) return "var(--accent-gold)";
  return "var(--accent-warm)";
}

export default function DebriefCard({ turn, index }: DebriefCardProps) {
  const avgScore =
    Object.values(turn.scores).reduce((a, b) => a + b, 0) /
    Object.values(turn.scores).length;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-60px" }}
      transition={{
        duration: 0.5,
        delay: index * 0.05,
        ease: [0.16, 1, 0.3, 1],
      }}
      className="glass-card"
      style={{ padding: "28px 28px" }}
    >
      {/* Question number + score */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
          marginBottom: 16,
        }}
      >
        <span
          style={{
            fontFamily: "var(--font-body)",
            fontSize: 11,
            color: "var(--text-dim)",
            letterSpacing: "0.1em",
          }}
        >
          QUESTION {index + 1}
        </span>
        <span
          style={{
            fontFamily: "var(--font-display)",
            fontSize: 14,
            fontWeight: 700,
            color: getScoreColor(avgScore),
          }}
        >
          avg {avgScore.toFixed(1)}
        </span>
      </div>

      {/* Question */}
      <p
        style={{
          fontFamily: "var(--font-display)",
          fontSize: 16,
          fontWeight: 600,
          color: "var(--text-primary)",
          marginBottom: 12,
          lineHeight: 1.4,
        }}
      >
        {turn.question}
      </p>

      {/* Answer */}
      <div
        style={{
          padding: "12px 14px",
          borderRadius: 8,
          background: "rgba(255,255,255,0.02)",
          border: "1px solid var(--border-subtle)",
          marginBottom: 16,
        }}
      >
        <p
          style={{
            fontSize: 11,
            color: "var(--text-dim)",
            letterSpacing: "0.08em",
            marginBottom: 6,
            fontFamily: "var(--font-body)",
          }}
        >
          YOU SAID
        </p>
        <p
          style={{
            fontFamily: "var(--font-body)",
            fontSize: 13,
            color: "var(--text-secondary)",
            lineHeight: 1.6,
          }}
        >
          {turn.answer}
        </p>
      </div>

      {/* HR Internal Reaction */}
      <div
        style={{
          padding: "14px 16px",
          borderRadius: 8,
          background: "rgba(255,179,71,0.04)",
          border: "1px solid rgba(255,179,71,0.2)",
          marginBottom: 16,
        }}
      >
        <p
          style={{
            fontSize: 11,
            color: "var(--accent-gold)",
            letterSpacing: "0.08em",
            marginBottom: 6,
            fontFamily: "var(--font-body)",
            fontWeight: 600,
          }}
        >
          HR INTERNAL REACTION
        </p>
        <p
          style={{
            fontFamily: "var(--font-body)",
            fontSize: 13,
            color: "var(--text-primary)",
            lineHeight: 1.6,
          }}
        >
          {typeof turn.feedback === "string"
            ? turn.feedback || "—"
            : turn.feedback && typeof turn.feedback === "object"
            ? (turn.feedback as { summary?: string }).summary ??
              (turn.feedback as { strengths?: string }).strengths ??
              "—"
            : "—"}
        </p>
      </div>

      {/* Scores mini-grid */}
      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          gap: 8,
        }}
      >
        {(Object.keys(turn.scores) as (keyof typeof turn.scores)[]).map(
          (key) => (
            <div
              key={key}
              style={{
                padding: "5px 10px",
                borderRadius: 6,
                background: "rgba(13,13,20,0.8)",
                border: "1px solid var(--border-subtle)",
                display: "flex",
                gap: 6,
                alignItems: "center",
              }}
            >
              <span
                style={{
                  fontFamily: "var(--font-body)",
                  fontSize: 10,
                  color: "var(--text-dim)",
                }}
              >
                {DIMENSION_LABELS[key].split("・")[0]}
              </span>
              <span
                style={{
                  fontFamily: "var(--font-display)",
                  fontSize: 12,
                  fontWeight: 700,
                  color: getScoreColor(Number(turn.scores[key] ?? 0)),
                }}
              >
                {Number(turn.scores[key] ?? 0).toFixed(1)}
              </span>
            </div>
          )
        )}
      </div>
    </motion.div>
  );
}
