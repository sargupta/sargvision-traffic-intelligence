import type { Metadata, Viewport } from "next";
import { Inter, IBM_Plex_Mono } from "next/font/google";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"], weight: ["400", "500", "600", "700"],
  variable: "--font-inter", display: "swap",
});
const mono = IBM_Plex_Mono({
  subsets: ["latin"], weight: ["400", "500", "600"],
  variable: "--font-plex-mono", display: "swap",
});

export const metadata: Metadata = {
  title: "Siliguri Traffic Command",
  description:
    "Live traffic conditions across Siliguri's junctions and corridors, with the choke points located and the incidents an officer is working on.",
};

export const viewport: Viewport = { themeColor: "#0A1628", width: "device-width", initialScale: 1 };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en-IN" className={`${inter.variable} ${mono.variable}`}>
      <body className="flex min-h-dvh flex-col">
        <a
          href="#main"
          className="sr-only focus:not-sr-only focus:fixed focus:left-3 focus:top-3 focus:z-50 focus:rounded focus:bg-navy focus:px-3 focus:py-2 focus:text-white"
        >
          Skip to the board
        </a>
        {children}
      </body>
    </html>
  );
}
