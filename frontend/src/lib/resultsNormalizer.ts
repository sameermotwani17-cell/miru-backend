import type { RadarScores } from "./types";

const RADAR_KEYS: (keyof RadarScores)[] = [
  "wa_teamwork",
  "loyalty_commitment",
  "humility",
  "kaizen_growth",
  "cultural_fit",
];

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function normalizeScores(data: any): RadarScores {
  const raw = data?.radar_scores ?? data?.scores ?? {};

  const topLevel: RadarScores = {
    wa_teamwork: Number(raw.wa_teamwork ?? 0),
    loyalty_commitment: Number(raw.loyalty_commitment ?? 0),
    humility: Number(raw.humility ?? 0),
    kaizen_growth: Number(raw.kaizen_growth ?? 0),
    cultural_fit: Number(raw.cultural_fit ?? 0),
  };

  // If all top-level scores are zero, try averaging from turn_feedback[].scores
  const hasScores = RADAR_KEYS.some((k) => topLevel[k] > 0);
  if (!hasScores && Array.isArray(data?.turn_feedback) && data.turn_feedback.length > 0) {
    const averaged = { ...topLevel };
    for (const key of RADAR_KEYS) {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const vals = (data.turn_feedback as any[])
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        .map((t: any) => Number(t?.scores?.[key] ?? 0))
        .filter((v: number) => v > 0);
      averaged[key] = vals.length
        ? vals.reduce((a: number, b: number) => a + b, 0) / vals.length
        : 0;
    }
    return averaged;
  }

  return topLevel;
}
