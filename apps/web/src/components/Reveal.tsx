"use client";

import type { ReactNode } from "react";
import { useInView } from "@/lib/useInView";

const EASE = "cubic-bezier(0.22, 1, 0.36, 1)";

export function Reveal({
  children,
  delay = 0,
  className,
  as: Tag = "div",
}: {
  children: ReactNode;
  delay?: number;
  className?: string;
  as?: "div" | "section" | "li" | "figure";
}) {
  const { ref, hidden } = useInView<HTMLDivElement>();

  return (
    <Tag
      ref={ref as never}
      className={className}
      style={{
        opacity: hidden ? 0 : 1,
        // Under prefers-reduced-motion the translate is neutralised in CSS
        // (see globals.css) and only the opacity change survives.
        transform: hidden ? "translateY(18px)" : "none",
        transition: `opacity 0.85s ${EASE} ${delay}s, transform 0.85s ${EASE} ${delay}s`,
        willChange: hidden ? "opacity, transform" : undefined,
      }}
    >
      {children}
    </Tag>
  );
}
