"use client";

import { useEffect, useRef } from "react";

interface Particle {
  x: number;
  y: number;
  vx: number;
  vy: number;
  size: number;
  colorIndex: number;
  opacity: number;
}

// Light theme — subtle on warm canvas
const LIGHT_COLORS = [
  "40, 131, 186",   // secondary blue
  "28, 162, 162",   // accent teal
  "13, 58, 95",     // primary dark blue
  "100, 160, 205",  // soft blue
];

// Dark theme — visible on void canvas
const DARK_COLORS = [
  "40, 131, 186",   // secondary blue
  "28, 162, 162",   // accent teal
  "13, 58, 95",     // primary dark (subtle)
  "0, 180, 220",    // cyan
];

const LIGHT_BG = "#faf0e0";
const DARK_BG  = "#050508";
const PARTICLE_COUNT = 120;

interface BokehBlob {
  color: string;
  size: number;
  top: string;
  left: string;
  duration: number;
  delay: number;
  animation: string;
}

const BOKEH_BLOBS: BokehBlob[] = [
  { color: "rgba(40, 131, 186, 0.07)", size: 380, top: "5%",  left: "10%", duration: 28, delay: 0,   animation: "bokeh-drift-1" },
  { color: "rgba(28, 162, 162, 0.06)", size: 320, top: "60%", left: "75%", duration: 34, delay: -8,  animation: "bokeh-drift-2" },
  { color: "rgba(13, 58, 95, 0.05)",   size: 420, top: "30%", left: "55%", duration: 40, delay: -14, animation: "bokeh-drift-3" },
  { color: "rgba(40, 131, 186, 0.05)", size: 280, top: "75%", left: "20%", duration: 24, delay: -5,  animation: "bokeh-drift-4" },
  { color: "rgba(28, 162, 162, 0.04)", size: 350, top: "15%", left: "80%", duration: 38, delay: -20, animation: "bokeh-drift-5" },
  { color: "rgba(13, 58, 95, 0.04)",   size: 300, top: "50%", left: "5%",  duration: 30, delay: -10, animation: "bokeh-drift-6" },
];

// Dark bokeh — more saturated, visible against void
const DARK_BOKEH_BLOBS: BokehBlob[] = [
  { color: "rgba(40, 131, 186, 0.14)", size: 400, top: "5%",  left: "10%", duration: 28, delay: 0,   animation: "bokeh-drift-1" },
  { color: "rgba(28, 162, 162, 0.11)", size: 340, top: "60%", left: "75%", duration: 34, delay: -8,  animation: "bokeh-drift-2" },
  { color: "rgba(40, 131, 186, 0.09)", size: 460, top: "30%", left: "55%", duration: 40, delay: -14, animation: "bokeh-drift-3" },
  { color: "rgba(28, 162, 162, 0.08)", size: 300, top: "75%", left: "20%", duration: 24, delay: -5,  animation: "bokeh-drift-4" },
  { color: "rgba(40, 131, 186, 0.10)", size: 380, top: "15%", left: "80%", duration: 38, delay: -20, animation: "bokeh-drift-5" },
  { color: "rgba(28, 162, 162, 0.07)", size: 320, top: "50%", left: "5%",  duration: 30, delay: -10, animation: "bokeh-drift-6" },
];

interface ParticleBackgroundProps {
  theme?: "light" | "dark";
}

export default function ParticleBackground({ theme = "light" }: ParticleBackgroundProps) {
  const canvasRef    = useRef<HTMLCanvasElement>(null);
  const mouseRef     = useRef({ x: 0, y: 0 });
  const particlesRef = useRef<Particle[]>([]);
  const rafRef       = useRef<number>(0);
  const themeRef     = useRef(theme);
  themeRef.current   = theme; // always latest without restarting loop

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const resize = () => {
      canvas.width  = window.innerWidth;
      canvas.height = window.innerHeight;
    };
    resize();

    const isDark = () => themeRef.current === "dark";

    // Initialise particles — dark gets higher base opacity
    particlesRef.current = Array.from({ length: PARTICLE_COUNT }, () => ({
      x:          Math.random() * canvas.width,
      y:          Math.random() * canvas.height,
      vx:         (Math.random() - 0.5) * 0.25,
      vy:         (Math.random() - 0.5) * 0.25,
      size:       Math.random() < 0.5 ? 2 : 3,
      colorIndex: Math.floor(Math.random() * 4),
      opacity:    Math.random() * 0.12 + 0.06, // 0.06 – 0.18 (scaled per theme in draw)
    }));

    const prefersReduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    const onMouseMove = (e: MouseEvent) => {
      mouseRef.current = { x: e.clientX, y: e.clientY };
    };
    window.addEventListener("mousemove", onMouseMove);
    window.addEventListener("resize", resize);

    let lastMouse = { x: 0, y: 0 };

    const draw = () => {
      if (!canvas || !ctx) return;

      const dark   = isDark();
      const BG     = dark ? DARK_BG  : LIGHT_BG;
      const COLORS = dark ? DARK_COLORS : LIGHT_COLORS;

      // Fill entire canvas each frame — this is the critical fix
      ctx.fillStyle = BG;
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      if (!prefersReduced) {
        const mx = mouseRef.current.x;
        const my = mouseRef.current.y;
        const dx = mx - lastMouse.x;
        const dy = my - lastMouse.y;
        lastMouse = { x: mx, y: my };

        for (const p of particlesRef.current) {
          p.x += p.vx + dx * 0.03;
          p.y += p.vy + dy * 0.03;

          if (p.x < 0) p.x += canvas.width;
          if (p.x > canvas.width)  p.x -= canvas.width;
          if (p.y < 0) p.y += canvas.height;
          if (p.y > canvas.height) p.y -= canvas.height;

          // Dark theme particles are more visible
          const opacityScale = dark ? 3.0 : 1.0;
          const color = COLORS[p.colorIndex];
          ctx.fillStyle = `rgba(${color}, ${Math.min(1, p.opacity * opacityScale)})`;
          ctx.fillRect(
            Math.round(p.x - p.size / 2),
            Math.round(p.y - p.size / 2),
            p.size,
            p.size
          );
        }
      }

      rafRef.current = requestAnimationFrame(draw);
    };

    rafRef.current = requestAnimationFrame(draw);

    return () => {
      cancelAnimationFrame(rafRef.current);
      window.removeEventListener("mousemove", onMouseMove);
      window.removeEventListener("resize", resize);
    };
  }, []); // intentionally no deps — themeRef.current is read live inside draw()

  const blobs = theme === "dark" ? DARK_BOKEH_BLOBS : BOKEH_BLOBS;

  return (
    <div
      className="particle-bg"
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 0,
        pointerEvents: "none",
        overflow: "hidden",
      }}
      aria-hidden="true"
    >
      <canvas
        ref={canvasRef}
        style={{
          position: "absolute",
          inset: 0,
          width: "100%",
          height: "100%",
        }}
      />

      {blobs.map((blob, i) => (
        <div
          key={i}
          style={{
            position: "absolute",
            top: blob.top,
            left: blob.left,
            width: blob.size,
            height: blob.size,
            borderRadius: "50%",
            background: `radial-gradient(circle, ${blob.color} 0%, transparent 70%)`,
            animation: `${blob.animation} ${blob.duration}s ${blob.delay}s ease-in-out infinite`,
            transform: "translate(-50%, -50%)",
            willChange: "transform",
          }}
        />
      ))}

      <svg
        style={{
          position: "absolute",
          inset: 0,
          width: "100%",
          height: "100%",
          opacity: 0.03,
          mixBlendMode: "multiply",
        }}
      >
        <filter id="grain">
          <feTurbulence type="fractalNoise" baseFrequency="0.65" numOctaves="3" stitchTiles="stitch" />
          <feColorMatrix type="saturate" values="0" />
        </filter>
        <rect width="100%" height="100%" filter="url(#grain)" />
      </svg>
    </div>
  );
}
