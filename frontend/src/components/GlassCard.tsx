import { ReactNode } from "react";

interface GlassCardProps {
  children: ReactNode;
  className?: string;
  style?: React.CSSProperties;
  padding?: number | string;
}

export default function GlassCard({
  children,
  className = "",
  style = {},
  padding = 24,
}: GlassCardProps) {
  return (
    <div
      className={`glass-card ${className}`}
      style={{ padding, ...style }}
    >
      {children}
    </div>
  );
}
