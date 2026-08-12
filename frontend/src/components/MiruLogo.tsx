"use client";

import { motion } from "framer-motion";

type LogoSize = "sm" | "md" | "lg";

const SIZE_MAP: Record<LogoSize, { icon: number; roman: number; jp: number }> =
  {
    sm: { icon: 24, roman: 14, jp: 10 },
    md: { icon: 40, roman: 20, jp: 13 },
    lg: { icon: 80, roman: 36, jp: 22 },
  };

interface MiruLogoProps {
  size?: LogoSize;
  animated?: boolean;
  className?: string;
}

export default function MiruLogo({
  size = "md",
  animated = false,
  className = "",
}: MiruLogoProps) {
  const { icon, roman, jp } = SIZE_MAP[size];

  return (
    <div
      className={`flex items-center gap-3 ${className}`}
      style={{ userSelect: "none" }}
    >
      {/* Icon */}
      <svg
        width={icon}
        height={icon}
        viewBox="0 0 80 80"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        style={{ flexShrink: 0 }}
      >
        {/* Outer radar ring - animated rotation */}
        <motion.circle
          cx="40"
          cy="40"
          r="36"
          stroke="var(--accent-secondary)"
          strokeWidth="1"
          strokeDasharray="6 4"
          fill="none"
          animate={animated ? { rotate: 360 } : undefined}
          transition={
            animated
              ? { duration: 20, repeat: Infinity, ease: "linear" }
              : undefined
          }
          style={{ transformOrigin: "40px 40px" }}
        />

        {/* Middle ring - counter rotation */}
        <motion.circle
          cx="40"
          cy="40"
          r="28"
          stroke="var(--accent-primary)"
          strokeWidth="1.5"
          fill="none"
          opacity="0.6"
          animate={animated ? { rotate: -360 } : undefined}
          transition={
            animated
              ? { duration: 15, repeat: Infinity, ease: "linear" }
              : undefined
          }
          style={{ transformOrigin: "40px 40px" }}
        />

        {/* Core glow */}
        <circle
          cx="40"
          cy="40"
          r="20"
          fill="url(#coreGrad)"
          opacity="0.9"
        />

        {/* Eye shape */}
        <ellipse
          cx="40"
          cy="40"
          rx="14"
          ry="9"
          stroke="var(--accent-secondary)"
          strokeWidth="1.5"
          fill="none"
        />

        {/* Iris */}
        <circle cx="40" cy="40" r="5" fill="var(--accent-primary)" />

        {/* Pupil */}
        <circle cx="40" cy="40" r="2.5" fill="var(--bg-void)" />

        {/* Iris ring */}
        <motion.circle
          cx="40"
          cy="40"
          r="5"
          stroke="var(--accent-secondary)"
          strokeWidth="1"
          fill="none"
          opacity="0.8"
          animate={animated ? { scale: [1, 1.3, 1] } : undefined}
          transition={
            animated
              ? { duration: 2.5, repeat: Infinity, ease: "easeInOut" }
              : undefined
          }
          style={{ transformOrigin: "40px 40px" }}
        />

        {/* Radar sweep lines */}
        <line
          x1="40"
          y1="14"
          x2="40"
          y2="20"
          stroke="var(--accent-primary)"
          strokeWidth="1.5"
          opacity="0.4"
        />
        <line
          x1="40"
          y1="60"
          x2="40"
          y2="66"
          stroke="var(--accent-primary)"
          strokeWidth="1.5"
          opacity="0.4"
        />
        <line
          x1="14"
          y1="40"
          x2="20"
          y2="40"
          stroke="var(--accent-primary)"
          strokeWidth="1.5"
          opacity="0.4"
        />
        <line
          x1="60"
          y1="40"
          x2="66"
          y2="40"
          stroke="var(--accent-primary)"
          strokeWidth="1.5"
          opacity="0.4"
        />

        <defs>
          <radialGradient id="coreGrad" cx="40%" cy="35%" r="55%">
            <stop offset="0%" stopColor="var(--accent-primary)" stopOpacity="0.3" />
            <stop offset="100%" stopColor="var(--bg-void)" stopOpacity="0.9" />
          </radialGradient>
        </defs>
      </svg>

      {/* Wordmark */}
      <div className="flex flex-col leading-none">
        <span
          style={{
            fontFamily: "var(--font-japanese), sans-serif",
            fontSize: jp,
            color: "var(--accent-secondary)",
            letterSpacing: "0.08em",
            lineHeight: 1,
          }}
        >
          ミル
        </span>
        <span
          style={{
            fontFamily: "var(--font-display), sans-serif",
            fontSize: roman,
            fontWeight: 700,
            color: "var(--text-primary)",
            letterSpacing: "0.12em",
            lineHeight: 1.1,
          }}
        >
          MIRU
        </span>
      </div>
    </div>
  );
}
