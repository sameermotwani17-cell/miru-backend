"use client";

import { motion } from "framer-motion";
import Link from "next/link";
import MiruLogo from "@/components/MiruLogo";

const FEATURES = [
  {
    icon: "🎙",
    title: "Interview Simulation",
    body: "Voice-driven mock interviews in Japanese or English, powered by an AI trained on Japanese HR patterns.",
  },
  {
    icon: "📊",
    title: "Cultural Scoring",
    body: "Silently scored on 5 dimensions: wa, loyalty, humility, kaizen, and cultural fit. Invisible signals made visible.",
  },
  {
    icon: "📋",
    title: "HR Debrief",
    body: "What the interviewer was actually thinking. Radar chart, answer rewrites, and company-specific flags.",
  },
];

const COMPANIES = [
  { name: "Toyota", jp: "トヨタ" },
  { name: "Rakuten", jp: "楽天" },
  { name: "Sony", jp: "ソニー" },
  { name: "SoftBank", jp: "ソフトバンク" },
  { name: "Uniqlo", jp: "ユニクロ" },
];

const container = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.08, delayChildren: 0.2 },
  },
};

const EASE = [0.16, 1, 0.3, 1] as [number, number, number, number];

const item = {
  hidden: { opacity: 0, y: 20 },
  show: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.5, ease: EASE },
  },
};

export default function LandingPage() {
  return (
    <motion.main
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
      className="page-light"
      style={{ minHeight: "100vh", overflowX: "hidden" }}
    >
      {/* Nav */}
      <nav
        className="dark-surface"
        style={{
          position: "fixed",
          top: 0,
          left: 0,
          right: 0,
          zIndex: 50,
          padding: "16px 40px",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          borderBottom: "1px solid rgba(13,58,95,0.25)",
          background: "#0d3a5f",
        }}
      >
        <MiruLogo size="sm" animated />
        <Link href="/onboarding">
          <motion.button
            whileHover={{ scale: 1.03 }}
            whileTap={{ scale: 0.97 }}
            style={{
              padding: "8px 22px",
              borderRadius: 8,
              border: "1px solid rgba(255,255,255,0.3)",
              background: "rgba(255,255,255,0.1)",
              color: "#ffffff",
              fontFamily: "var(--font-body)",
              fontSize: 14,
              cursor: "pointer",
              letterSpacing: "0.06em",
              fontWeight: 600,
            }}
          >
            Start Interview
          </motion.button>
        </Link>
      </nav>

      {/* Hero */}
      <section
        style={{
          minHeight: "100vh",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          textAlign: "center",
          padding: "120px 24px 80px",
        }}
      >
        <motion.div variants={container} initial="hidden" animate="show">
          {/* Tag */}
          <motion.div variants={item}>
            <span
              style={{
                display: "inline-block",
                padding: "6px 16px",
                borderRadius: 999,
                border: "1px solid rgba(40,131,186,0.3)",
                color: "#2883ba",
                fontSize: 12,
                letterSpacing: "0.12em",
                fontFamily: "var(--font-body)",
                marginBottom: 32,
                background: "rgba(40,131,186,0.08)",
              }}
            >
              <span style={{ fontFamily: "var(--font-japanese)" }}>
                日本語面接対策
              </span>
              {" · "}AI Interview Coach
            </span>
          </motion.div>

          {/* Headline */}
          <motion.h1
            variants={item}
            style={{
              fontFamily: "var(--font-display)",
              fontSize: "clamp(36px, 6vw, 72px)",
              fontWeight: 700,
              lineHeight: 1.1,
              letterSpacing: "-0.02em",
              color: "var(--text-page-heading)",
              maxWidth: 800,
              margin: "0 auto 20px",
            }}
          >
            The AI that thinks like a{" "}
            <span
              style={{
                background: "linear-gradient(135deg, #0d3a5f, #2883ba)",
                WebkitBackgroundClip: "text",
                WebkitTextFillColor: "transparent",
              }}
            >
              Japanese HR manager
            </span>
            .
          </motion.h1>

          {/* Subhead */}
          <motion.p
            variants={item}
            style={{
              fontFamily: "var(--font-body)",
              fontSize: "clamp(16px, 2.5vw, 20px)",
              color: "var(--text-page-body)",
              maxWidth: 600,
              margin: "0 auto 48px",
              lineHeight: 1.6,
            }}
          >
            Foreigners don&apos;t fail Japanese interviews because of language.
            They fail because of invisible cultural signals.{" "}
            <span style={{ color: "var(--text-page-heading)", fontWeight: 600 }}>
              MIRU makes them visible.
            </span>
          </motion.p>

          {/* CTA */}
          <motion.div variants={item}>
            <Link href="/onboarding">
              <motion.button
                whileHover={{ scale: 1.04, boxShadow: "0 0 32px rgba(40,131,186,0.4)" }}
                whileTap={{ scale: 0.96 }}
                style={{
                  padding: "16px 40px",
                  borderRadius: 12,
                  background: "#2883ba",
                  border: "none",
                  color: "#fff",
                  fontFamily: "var(--font-body)",
                  fontSize: 16,
                  fontWeight: 600,
                  cursor: "pointer",
                  letterSpacing: "0.04em",
                  boxShadow: "0 4px 20px rgba(40,131,186,0.3)",
                }}
              >
                Start Your Interview →
              </motion.button>
            </Link>
          </motion.div>
        </motion.div>
      </section>

      {/* Features */}
      <section
        style={{
          padding: "80px 24px",
          maxWidth: 1100,
          margin: "0 auto",
        }}
      >
        <motion.h2
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
          style={{
            textAlign: "center",
            fontFamily: "var(--font-display)",
            fontSize: "clamp(24px, 4vw, 40px)",
            fontWeight: 700,
            color: "var(--text-page-heading)",
            marginBottom: 60,
          }}
        >
          What MIRU does
        </motion.h2>

        <motion.div
          variants={container}
          initial="hidden"
          whileInView="show"
          viewport={{ once: true }}
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
            gap: 24,
          }}
        >
          {FEATURES.map((f) => (
            <motion.div
              key={f.title}
              variants={item}
              className="glass-card glass-card-hover"
              style={{ padding: 32 }}
            >
              <div style={{ fontSize: 36, marginBottom: 16 }}>{f.icon}</div>
              <h3
                style={{
                  fontFamily: "var(--font-display)",
                  fontSize: 20,
                  fontWeight: 600,
                  color: "var(--text-primary)",
                  marginBottom: 12,
                }}
              >
                {f.title}
              </h3>
              <p
                style={{
                  fontFamily: "var(--font-body)",
                  fontSize: 15,
                  color: "var(--text-secondary)",
                  lineHeight: 1.6,
                }}
              >
                {f.body}
              </p>
            </motion.div>
          ))}
        </motion.div>
      </section>

      {/* Companies */}
      <section
        style={{
          padding: "60px 24px 100px",
          textAlign: "center",
        }}
      >
        <motion.p
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          style={{
            fontFamily: "var(--font-body)",
            fontSize: 13,
            color: "var(--text-page-muted)",
            letterSpacing: "0.12em",
            textTransform: "uppercase",
            marginBottom: 32,
          }}
        >
          Practice for top Japanese companies
        </motion.p>

        <motion.div
          variants={container}
          initial="hidden"
          whileInView="show"
          viewport={{ once: true }}
          style={{
            display: "flex",
            flexWrap: "wrap",
            justifyContent: "center",
            gap: 16,
          }}
        >
          {COMPANIES.map((c) => (
            <motion.div
              key={c.name}
              variants={item}
              style={{
                padding: "10px 24px",
                borderRadius: 8,
                border: "1px solid rgba(13,58,95,0.14)",
                background: "rgba(255,255,255,0.75)",
                backdropFilter: "blur(4px)",
                display: "flex",
                alignItems: "center",
                gap: 8,
                boxShadow: "0 1px 6px rgba(13,58,95,0.06)",
              }}
            >
              <span
                style={{
                  fontFamily: "var(--font-japanese)",
                  fontSize: 12,
                  color: "#1ca2a2",
                }}
              >
                {c.jp}
              </span>
              <span
                style={{
                  fontFamily: "var(--font-body)",
                  fontSize: 14,
                  fontWeight: 600,
                  color: "#0d3a5f",
                }}
              >
                {c.name}
              </span>
            </motion.div>
          ))}
        </motion.div>
      </section>

      {/* Bottom CTA */}
      <section
        style={{
          padding: "80px 24px",
          textAlign: "center",
          borderTop: "1px solid rgba(13,58,95,0.1)",
        }}
      >
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5 }}
        >
          <p
            style={{
              fontFamily: "var(--font-japanese)",
              fontSize: 14,
              color: "#1ca2a2",
              marginBottom: 16,
            }}
          >
            準備はいいですか？
          </p>
          <p
            style={{
              fontFamily: "var(--font-body)",
              fontSize: 16,
              color: "#333333",
              marginBottom: 32,
            }}
          >
            Ready to see what a Japanese HR manager sees?
          </p>
          <Link href="/onboarding">
            <motion.button
              whileHover={{ scale: 1.04, boxShadow: "0 0 24px rgba(40,131,186,0.25)" }}
              whileTap={{ scale: 0.96 }}
              style={{
                padding: "14px 36px",
                borderRadius: 10,
                border: "none",
                background: "#0d3a5f",
                color: "#ffffff",
                fontFamily: "var(--font-body)",
                fontSize: 15,
                fontWeight: 700,
                cursor: "pointer",
                boxShadow: "0 4px 16px rgba(13,58,95,0.2)",
              }}
            >
              Begin Interview →
            </motion.button>
          </Link>
        </motion.div>
      </section>
    </motion.main>
  );
}
