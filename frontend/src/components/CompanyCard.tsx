"use client";

import { useState } from "react";
import Image from "next/image";
import { motion } from "framer-motion";

interface CompanyCardProps {
  id: string;
  name: string;
  label: string;
  descriptor: string;
  accent: string;
  bg: string;
  selected: boolean;
  onSelect: () => void;
}

export default function CompanyCard({
  id,
  name,
  label,
  descriptor,
  accent,
  bg,
  selected,
  onSelect,
}: CompanyCardProps) {
  const [logoError, setLogoError] = useState(false);

  return (
    <motion.button
      onClick={onSelect}
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
      animate={
        selected
          ? { scale: 1.02 }
          : { scale: 1 }
      }
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "flex-start",
        padding: "24px 20px",
        borderRadius: 14,
        border: selected
          ? `1.5px solid ${accent}`
          : "1px solid rgba(40,131,186,0.15)",
        background: selected ? bg : "#ffffff",
        boxShadow: selected
          ? `0 0 20px ${accent}30`
          : "0 1px 8px rgba(13,58,95,0.06)",
        cursor: "pointer",
        textAlign: "left",
        transition: "border-color 0.2s, box-shadow 0.2s, background 0.2s",
        width: "100%",
      }}
    >
      {/* Logo / Monogram */}
      <div
        style={{
          width: 44,
          height: 44,
          borderRadius: 10,
          background: selected ? `${accent}20` : "rgba(40,131,186,0.06)",
          border: `1px solid ${selected ? accent : "rgba(40,131,186,0.12)"}`,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          marginBottom: 16,
          overflow: "hidden",
          fontSize: 18,
          fontFamily: "var(--font-japanese)",
          color: selected ? accent : "#4a6a8a",
          fontWeight: 700,
          transition: "all 0.2s",
        }}
      >
        {!logoError ? (
          <Image
            src={`/logos/${id}.png`}
            alt={name}
            width={40}
            height={40}
            style={{ objectFit: "contain", borderRadius: 8 }}
            onError={() => setLogoError(true)}
          />
        ) : (
          label.charAt(0)
        )}
      </div>

      {/* Name */}
      <div style={{ marginBottom: 6 }}>
        <span
          style={{
            fontFamily: "var(--font-display)",
            fontSize: 16,
            fontWeight: 700,
            color: "#0d3a5f",
          }}
        >
          {name}
        </span>
        <span
          style={{
            fontFamily: "var(--font-japanese)",
            fontSize: 11,
            color: "var(--text-secondary)",
            marginLeft: 8,
          }}
        >
          {label}
        </span>
      </div>

      {/* Descriptor */}
      <p
        style={{
          fontFamily: "var(--font-body)",
          fontSize: 12,
          color: selected ? "#4a6a8a" : "#8899aa",
          lineHeight: 1.4,
          transition: "color 0.2s",
        }}
      >
        {descriptor}
      </p>

      {/* Selected indicator */}
      {selected && (
        <motion.div
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          style={{
            position: "absolute" as const,
            top: 12,
            right: 12,
            width: 20,
            height: 20,
            borderRadius: "50%",
            background: accent,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <svg width="10" height="8" viewBox="0 0 10 8" fill="none">
            <path
              d="M1 4L3.5 6.5L9 1"
              stroke="white"
              strokeWidth="1.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </motion.div>
      )}
    </motion.button>
  );
}
