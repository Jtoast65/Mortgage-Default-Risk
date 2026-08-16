import type { Metadata } from "next";
import { Inter, IBM_Plex_Mono } from "next/font/google";
import "./globals.css";

const sans = Inter({ subsets: ["latin"], variable: "--font-sans", display: "swap" });
const mono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Mortgage Default Risk — Calibrated PD",
  description:
    "Calibrated probability of default on US mortgages. Drag an approval cutoff and watch approval rate trade against expected loss in dollars.",
  metadataBase: new URL("https://mortgage-default-risk.vercel.app"),
  openGraph: {
    title: "Mortgage Default Risk — Calibrated PD",
    description:
      "At a 4% PD cutoff the model approves 94% of applications and cuts expected loss ~$480K per $1B vs a FICO×LTV scorecard.",
    url: "https://mortgage-default-risk.vercel.app",
    type: "website",
  },
  twitter: { card: "summary_large_image" },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className={`${sans.variable} ${mono.variable}`}>{children}</body>
    </html>
  );
}
