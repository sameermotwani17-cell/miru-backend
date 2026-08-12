"use client";

import { motion, AnimatePresence } from "framer-motion";
import { useEffect, useRef } from "react";

interface VoiceInputProps {
  isRecording: boolean;
  transcript: string;
  onStartRecording: () => void;
  onStopRecording: () => void;
  disabled?: boolean;
  statusText?: string;
}

export default function VoiceInput({
  isRecording,
  transcript,
  onStartRecording,
  onStopRecording,
  disabled = false,
  statusText,
}: VoiceInputProps) {
  const barsRef = useRef<number[]>(Array.from({ length: 20 }, () => 0.2));
  const animRef = useRef<number>(0);
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    if (!isRecording) {
      cancelAnimationFrame(animRef.current);
      return;
    }

    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const animate = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      barsRef.current = barsRef.current.map((v) =>
        Math.max(0.05, Math.min(1, v + (Math.random() - 0.5) * 0.25))
      );

      const barW = 3;
      const gap = 4;
      const total = barsRef.current.length * (barW + gap);
      const startX = (canvas.width - total) / 2;

      barsRef.current.forEach((h, i) => {
        const barH = h * canvas.height;
        const x = startX + i * (barW + gap);
        const y = (canvas.height - barH) / 2;
        const alpha = 0.5 + h * 0.5;
        ctx.fillStyle = `rgba(255,107,107,${alpha})`;
        ctx.beginPath();
        ctx.roundRect(x, y, barW, barH, 2);
        ctx.fill();
      });

      animRef.current = requestAnimationFrame(animate);
    };

    animRef.current = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(animRef.current);
  }, [isRecording]);

  const handleClick = () => {
    if (disabled) return;
    if (isRecording) {
      onStopRecording();
    } else {
      onStartRecording();
    }
  };

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: 16,
      }}
    >
      {/* Waveform */}
      <AnimatePresence>
        {isRecording && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 50 }}
            exit={{ opacity: 0, height: 0 }}
            style={{ width: 200 }}
          >
            <canvas
              ref={canvasRef}
              width={200}
              height={50}
              style={{ borderRadius: 8 }}
            />
          </motion.div>
        )}
      </AnimatePresence>

      {/* Transcript display */}
      <AnimatePresence>
        {transcript && !isRecording && (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            style={{
              maxWidth: 500,
              padding: "12px 18px",
              borderRadius: 12,
              border: "1px solid var(--border-subtle)",
              background: "rgba(13,13,20,0.8)",
              fontFamily: "var(--font-body)",
              fontSize: 14,
              color: "var(--text-secondary)",
              lineHeight: 1.5,
              textAlign: "center",
            }}
          >
            <span style={{ color: "var(--text-dim)", fontSize: 11, display: "block", marginBottom: 6, letterSpacing: "0.08em" }}>
              YOU SAID
            </span>
            {transcript}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Mic button */}
      <motion.button
        onClick={handleClick}
        disabled={disabled}
        whileHover={disabled ? {} : { scale: 1.06 }}
        whileTap={disabled ? {} : { scale: 0.94 }}
        animate={
          isRecording
            ? { boxShadow: ["0 0 20px rgba(255,107,107,0.4)", "0 0 40px rgba(255,107,107,0.6)", "0 0 20px rgba(255,107,107,0.4)"] }
            : { boxShadow: "0 0 20px rgba(108,99,255,0.2)" }
        }
        transition={
          isRecording
            ? { duration: 1, repeat: Infinity, ease: "easeInOut" }
            : {}
        }
        style={{
          width: 72,
          height: 72,
          borderRadius: "50%",
          border: isRecording
            ? "2px solid var(--accent-warm)"
            : "2px solid var(--border-active)",
          background: isRecording
            ? "rgba(255,107,107,0.15)"
            : "rgba(108,99,255,0.1)",
          cursor: disabled ? "not-allowed" : "pointer",
          opacity: disabled ? 0.4 : 1,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        {isRecording ? (
          // Stop icon
          <div
            style={{
              width: 22,
              height: 22,
              borderRadius: 4,
              background: "var(--accent-warm)",
            }}
          />
        ) : (
          // Mic icon
          <svg width="26" height="26" viewBox="0 0 24 24" fill="none">
            <rect
              x="9"
              y="2"
              width="6"
              height="12"
              rx="3"
              fill="var(--accent-primary)"
            />
            <path
              d="M5 10a7 7 0 0 0 14 0"
              stroke="var(--accent-primary)"
              strokeWidth="1.5"
              strokeLinecap="round"
            />
            <line
              x1="12"
              y1="17"
              x2="12"
              y2="21"
              stroke="var(--accent-primary)"
              strokeWidth="1.5"
              strokeLinecap="round"
            />
            <line
              x1="9"
              y1="21"
              x2="15"
              y2="21"
              stroke="var(--accent-primary)"
              strokeWidth="1.5"
              strokeLinecap="round"
            />
          </svg>
        )}
      </motion.button>

      <p
        style={{
          fontFamily: "var(--font-body)",
          fontSize: 12,
          color: "var(--text-dim)",
          letterSpacing: "0.06em",
        }}
      >
        {statusText ??
          (disabled
            ? "Please wait..."
            : isRecording
            ? "Tap to stop recording"
            : "Tap to speak")}
      </p>
    </div>
  );
}
