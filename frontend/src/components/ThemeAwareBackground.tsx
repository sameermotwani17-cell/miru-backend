"use client";

import { usePathname } from "next/navigation";
import ParticleBackground from "./ParticleBackground";

/**
 * Reads the current route and tells ParticleBackground which theme to render.
 * /interview → dark canvas (#050508)
 * all other routes → light canvas (#F8F8FC)
 */
export default function ThemeAwareBackground() {
  const pathname = usePathname();
  const theme = pathname === "/interview" ? "dark" : "light";
  return <ParticleBackground theme={theme} />;
}
