import type { Metadata } from "next";
import { Sora, Space_Grotesk, Noto_Sans_JP } from "next/font/google";
import "./globals.css";
import ThemeAwareBackground from "@/components/ThemeAwareBackground";

const sora = Sora({
  subsets: ["latin"],
  variable: "--font-sora",
  display: "swap",
});

const spaceGrotesk = Space_Grotesk({
  subsets: ["latin"],
  variable: "--font-space-grotesk",
  display: "swap",
});

const notoJP = Noto_Sans_JP({
  subsets: ["latin"],
  variable: "--font-noto-jp",
  display: "swap",
  weight: ["400", "500", "700"],
});

export const metadata: Metadata = {
  title: "MIRU — Japanese HR Interview Simulator",
  description:
    "The AI that thinks like a Japanese HR manager. Practice your interview and understand the invisible cultural signals that matter.",
  icons: {
    icon: "/favicon.ico",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${sora.variable} ${spaceGrotesk.variable} ${notoJP.variable}`}
    >
      <body className="antialiased">
        <ThemeAwareBackground />
        <div style={{ position: "relative", zIndex: 1 }}>{children}</div>
      </body>
    </html>
  );
}
