"use client";

import { motion } from "framer-motion";

type AvatarState = "idle" | "listening" | "processing" | "speaking";

interface HRAvatarProps {
  state: AvatarState;
}

const STATE_CONFIG: Record<
  AvatarState,
  { outerColor: string; coreColor: string; pulseScale: number[] }
> = {
  idle: {
    outerColor: "var(--accent-primary)",
    coreColor: "rgba(108,99,255,0.6)",
    pulseScale: [1, 1.03, 1],
  },
  listening: {
    outerColor: "var(--accent-warm)",
    coreColor: "rgba(255,107,107,0.6)",
    pulseScale: [1, 1.08, 1],
  },
  processing: {
    outerColor: "var(--accent-gold)",
    coreColor: "rgba(255,179,71,0.6)",
    pulseScale: [1, 1.04, 0.97, 1],
  },
  speaking: {
    outerColor: "var(--accent-secondary)",
    coreColor: "rgba(0,212,255,0.6)",
    pulseScale: [1, 1.06, 1],
  },
};

export default function HRAvatar({ state }: HRAvatarProps) {
  const cfg = STATE_CONFIG[state];

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        position: "relative",
        width: 240,
        height: 240,
      }}
    >
      {/* Outermost ring — dashed, slow clockwise */}
      <motion.div
        animate={{ rotate: 360 }}
        transition={{ duration: 20, repeat: Infinity, ease: "linear" }}
        style={{
          position: "absolute",
          width: 220,
          height: 220,
          borderRadius: "50%",
          border: `1.5px dashed ${cfg.outerColor}`,
          opacity: 0.7,
        }}
      />

      {/* Middle ring — solid, counter-clockwise */}
      <motion.div
        animate={{ rotate: -360 }}
        transition={{ duration: 15, repeat: Infinity, ease: "linear" }}
        style={{
          position: "absolute",
          width: 170,
          height: 170,
          borderRadius: "50%",
          border: `1.5px solid ${cfg.outerColor}`,
          opacity: 0.8,
        }}
      />

      {/* Inner ring — pulses */}
      <motion.div
        animate={{ scale: cfg.pulseScale, opacity: [0.6, 0.9, 0.6] }}
        transition={{
          duration: state === "processing" ? 0.8 : 2.5,
          repeat: Infinity,
          ease: "easeInOut",
        }}
        style={{
          position: "absolute",
          width: 120,
          height: 120,
          borderRadius: "50%",
          border: `1.5px solid ${cfg.outerColor}`,
          opacity: 0.6,
        }}
      />

      {/* Core sphere */}
      <motion.div
        animate={{
          scale: state === "speaking" ? [1, 1.05, 1] : [1, 1.02, 1],
          boxShadow:
            state === "speaking"
              ? [
                  `0 0 40px ${cfg.coreColor}, 0 0 80px ${cfg.coreColor}, 0 0 120px ${cfg.coreColor}`,
                  `0 0 60px ${cfg.coreColor}, 0 0 100px ${cfg.coreColor}, 0 0 160px ${cfg.coreColor}`,
                  `0 0 40px ${cfg.coreColor}, 0 0 80px ${cfg.coreColor}, 0 0 120px ${cfg.coreColor}`,
                ]
              : [
                  `0 0 30px ${cfg.coreColor}, 0 0 60px ${cfg.coreColor}`,
                  `0 0 45px ${cfg.coreColor}, 0 0 80px ${cfg.coreColor}`,
                  `0 0 30px ${cfg.coreColor}, 0 0 60px ${cfg.coreColor}`,
                ],
        }}
        transition={{
          duration: state === "speaking" ? 0.8 : 3,
          repeat: Infinity,
          ease: "easeInOut",
        }}
        style={{
          width: 80,
          height: 80,
          borderRadius: "50%",
          background: `radial-gradient(circle at 40% 35%, ${cfg.outerColor}, rgba(5,5,8,0.9))`,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        {/* Eye motif */}
        <svg width="36" height="24" viewBox="0 0 36 24" fill="none">
          <ellipse
            cx="18"
            cy="12"
            rx="14"
            ry="9"
            stroke="rgba(255,255,255,0.7)"
            strokeWidth="1.5"
          />
          <motion.circle
            cx="18"
            cy="12"
            r="5"
            fill="rgba(255,255,255,0.9)"
            animate={{ r: state === "speaking" ? [5, 6, 5] : [5, 5.5, 5] }}
            transition={{ duration: 1.5, repeat: Infinity, ease: "easeInOut" }}
          />
          <circle cx="18" cy="12" r="2.5" fill="rgba(5,5,8,0.9)" />
        </svg>
      </motion.div>

      {/* State label */}
      <motion.p
        key={state}
        initial={{ opacity: 0, y: 4 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -4 }}
        style={{
          position: "absolute",
          bottom: -8,
          fontFamily: "var(--font-body)",
          fontSize: 11,
          color: "#8888aa",
          letterSpacing: "0.1em",
          textTransform: "uppercase",
        }}
      >
        {state === "idle" && "Standby"}
        {state === "listening" && "Recording…"}
        {state === "processing" && "Thinking…"}
        {state === "speaking" && "Speaking"}
      </motion.p>
    </div>
  );
}
