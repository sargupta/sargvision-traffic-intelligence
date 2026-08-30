import type { Metadata, Viewport } from "next";
import { Newsreader, Inter, IBM_Plex_Mono } from "next/font/google";
import "./globals.css";

const newsreader = Newsreader({
  subsets: ["latin"],
  weight: ["300", "400", "500"],
  style: ["normal", "italic"],
  variable: "--font-newsreader",
  display: "swap",
});

const inter = Inter({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-inter",
  display: "swap",
});

const plexMono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "500"],
  variable: "--font-plex-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "How Siliguri Moves",
  description:
    "Four structural findings about travel time in Siliguri, drawn from 101,418 valid primary-route observations recorded between June and November 2019. Published by SARGVISION Intelligence Pvt. Ltd.",
  authors: [{ name: "SARGVISION Intelligence Pvt. Ltd." }],
  openGraph: {
    title: "How Siliguri Moves",
    description:
      "Congestion is roughly a fifth of the gap between Siliguri's traffic and a 30 km/h city. Four findings from 101,418 observations.",
    type: "article",
  },
};

export const viewport: Viewport = {
  themeColor: "#0A1628",
  colorScheme: "dark",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en-IN" className={`${newsreader.variable} ${inter.variable} ${plexMono.variable}`}>
      <body>
        <a
          href="#findings"
          className="sr-only focus:not-sr-only focus:fixed focus:top-4 focus:left-4 focus:z-50 focus:bg-ink-700 focus:px-4 focus:py-2 focus:text-paper"
        >
          Skip to the findings
        </a>
        {children}
      </body>
    </html>
  );
}
