import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "SARGVISION Traffic Intelligence · Siliguri",
  description:
    "Real-time urban mobility intelligence for Siliguri: live conditions compared against historical baselines, with the findings the engine considers worth attention.",
};

export default function ConsoleLayout({ children }: { children: React.ReactNode }) {
  return children;
}
