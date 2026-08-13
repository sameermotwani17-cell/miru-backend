"use client";

import { motion } from "framer-motion";
import type { TurnFeedback } from "@/lib/types";

interface RewriteComparisonProps {
  turn: TurnFeedback;
  index: number;
}

export default function RewriteComparison({ turn, index }: RewriteComparisonProps) {
  const avgBefore =
    Object.values(turn.scores).reduce((a, b) => a + b, 0) /
    Object.values(turn.scores).length;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-60px" }}
      transition={{ duration: 0.5, delay: index * 0.05, ease: [0.16, 1, 0.3, 1] }}
    >
      <p
        style={{
          fontFamily: "var(--font-display)",
          fontSize: 14,
          fontWeight: 600,
          color: "var(--text-secondary)",
          marginBottom: 12,
        }}
      >
        Question {index + 1}:{" "}
        <span style={{ color: "var(--text-primary)", fontWeight: 400, fontSize: 13 }}>
          {turn.question}
        </span>
      </p>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: 16,
        }}
      >
        {/* Before */}
        <div
          style={{
            padding: "18px 20px",
            borderRadius: 12,
            border: "1px solid rgba(255,107,107,0.25)",
            background: "rgba(255,107,107,0.04)",
          }}
        >
          <p
            style={{
              fontSize: 10,
              color: "var(--accent-warm)",
              letterSpacing: "0.1em",
              fontFamily: "var(--font-body)",
              fontWeight: 600,
              marginBottom: 10,
            }}
          >
            WHAT YOU SAID
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

        {/* After */}
        <div
          style={{
            padding: "18px 20px",
            borderRadius: 12,
            border: "1px solid rgba(0,255,178,0.25)",
            background: "rgba(0,255,178,0.04)",
          }}
        >
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              marginBottom: 10,
            }}
          >
            <p
              style={{
                fontSize: 10,
                color: "var(--accent-green)",
                letterSpacing: "0.1em",
                fontFamily: "var(--font-body)",
                fontWeight: 600,
              }}
            >
              WHAT TO SAY INSTEAD
            </p>
            <span
              style={{
                fontSize: 10,
                color: "var(--accent-green)",
                fontFamily: "var(--font-body)",
                background: "rgba(0,255,178,0.1)",
                padding: "2px 8px",
                borderRadius: 4,
              }}
            >
              +{(10 - avgBefore).toFixed(1)} potential
            </span>
          </div>
          <p
            style={{
              fontFamily: "var(--font-body)",
              fontSize: 13,
              color: "var(--text-primary)",
              lineHeight: 1.6,
            }}
          >
            {turn.rewrite}
          </p>
        </div>
      </div>
    </motion.div>
  );
}
