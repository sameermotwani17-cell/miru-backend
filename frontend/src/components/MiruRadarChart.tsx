"use client";

import {
  Radar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  ResponsiveContainer,
  Tooltip,
} from "recharts";
import type { RadarScores } from "@/lib/types";
import { DIMENSION_LABELS } from "@/lib/types";

interface MiruRadarChartProps {
  scores: RadarScores;
}

const IDEAL_SCORES: RadarScores = {
  wa_teamwork: 9,
  loyalty_commitment: 9,
  humility: 8,
  kaizen_growth: 8,
  cultural_fit: 9,
};

export default function MiruRadarChart({ scores }: MiruRadarChartProps) {
  const data = (Object.keys(scores) as (keyof RadarScores)[]).map((key) => ({
    dimension: DIMENSION_LABELS[key],
    candidate: Number(scores[key] ?? 0),
    ideal: IDEAL_SCORES[key],
    fullMark: 10,
  }));

  return (
    <div>
      <p
        style={{
          fontFamily: "var(--font-display)",
          fontSize: 15,
          fontWeight: 700,
          color: "var(--text-primary)",
          marginBottom: 12,
          textAlign: "center",
        }}
      >
        Japanese Hiring Signal Profile
      </p>

      <div
        style={{
          display: "flex",
          justifyContent: "center",
          gap: 16,
          marginBottom: 8,
          flexWrap: "wrap",
        }}
      >
        <span style={{ fontFamily: "var(--font-body)", fontSize: 12, color: "#4a6a8a" }}>
          <span style={{ color: "#0d3a5f", marginRight: 6 }}>●</span>
          Ideal Japanese Candidate
        </span>
        <span style={{ fontFamily: "var(--font-body)", fontSize: 12, color: "#4a6a8a" }}>
          <span style={{ color: "#1ca2a2", marginRight: 6 }}>●</span>
          Your Interview Signals
        </span>
      </div>

      <ResponsiveContainer width="100%" height={320}>
        <RadarChart data={data} margin={{ top: 20, right: 30, bottom: 20, left: 30 }}>
          <PolarGrid gridType="polygon" stroke="rgba(40,131,186,0.15)" />
          <PolarAngleAxis
            dataKey="dimension"
            tick={{
              fill: "#4a6a8a",
              fontSize: 11,
              fontFamily: "var(--font-body)",
            }}
          />
          <Tooltip
            formatter={(value, name) => {
              const numeric = typeof value === "number" ? value : Number(value);
              const formattedValue = Number.isFinite(numeric) ? numeric.toFixed(1) : "-";
              const label = String(name) === "candidate" ? "Your Score" : "Ideal Score";
              return [formattedValue, label];
            }}
            labelFormatter={(label) => `Dimension: ${String(label ?? "")}`}
            contentStyle={{
              background: "rgba(255,255,255,0.97)",
              border: "1px solid rgba(40,131,186,0.2)",
              borderRadius: 8,
              color: "#0d3a5f",
              fontFamily: "var(--font-body)",
              boxShadow: "0 4px 16px rgba(13,58,95,0.1)",
            }}
          />
          <Radar
            name="Ideal Japanese Candidate"
            dataKey="ideal"
            stroke="#0d3a5f"
            fill="#0d3a5f"
            fillOpacity={0.08}
            dot={false}
          />
          <Radar
            name="Your Interview Signals"
            dataKey="candidate"
            stroke="#1ca2a2"
            fill="#1ca2a2"
            fillOpacity={0.45}
            dot={{
              r: 4,
              fill: "#1ca2a2",
              strokeWidth: 0,
            }}
          />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
}
