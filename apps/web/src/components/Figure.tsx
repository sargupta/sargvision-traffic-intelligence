"use client";

import { useState } from "react";

/** The Metric contract from `packages/contracts/metric.py`, rendered.
 *
 *  The Python dataclass refuses to construct without definition, source,
 *  derivation and limitation. This component refuses to display without them
 *  either — that symmetry is the point. A figure on this page is never bare.
 */
export interface FigureProps {
  value: string;
  unit?: string;
  label: string;
  definition: string;
  source: string;
  derivation: string;
  limitation: string;
  sample?: string;
  tone?: "paper" | "gold" | "copper";
  size?: "hero" | "large" | "inline";
}

const TONE = {
  paper: "text-paper",
  gold: "text-gold",
  copper: "text-copper-lit",
} as const;

const SIZE = {
  hero: "text-[length:var(--text-mega)]",
  large: "text-[length:var(--text-h1)]",
  inline: "text-[length:var(--text-h2)]",
} as const;

export function Figure({
  value,
  unit,
  label,
  definition,
  source,
  derivation,
  limitation,
  sample,
  tone = "paper",
  size = "large",
}: FigureProps) {
  const [open, setOpen] = useState(false);

  return (
    <figure className="relative">
      <div
        className={`font-display font-light leading-[0.82] tnum ${TONE[tone]} ${SIZE[size]}`}
      >
        {value}
        {unit && (
          <span className="ml-[0.12em] align-baseline font-sans text-[0.24em] font-medium tracking-[0.06em] text-paper-40">
            {unit}
          </span>
        )}
      </div>

      <figcaption className="mt-5 max-w-[34ch]">
        <p className="text-[length:var(--text-base)] leading-snug text-paper-70">{label}</p>

        <div className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-1">
          {sample && (
            <span className="font-mono text-[length:var(--text-micro)] tracking-[0.08em] text-paper-40">
              {sample}
            </span>
          )}
          <button
            type="button"
            onClick={() => setOpen((v) => !v)}
            aria-expanded={open}
            className="group inline-flex items-center gap-1.5 font-mono text-[length:var(--text-micro)] uppercase tracking-[0.14em] text-copper-lit transition-colors hover:text-gold"
          >
            <span
              aria-hidden
              className={`inline-block h-px w-4 bg-current transition-transform duration-200 ${open ? "scale-x-100" : "scale-x-50"}`}
            />
            {open ? "Hide basis" : "How this is derived"}
          </button>
        </div>

        {open && (
          <dl className="mt-4 space-y-3 border-l border-copper/45 pl-4 text-[length:var(--text-caption)] leading-relaxed">
            {(
              [
                ["Definition", definition],
                ["Source", source],
                ["Derivation", derivation],
                ["Limitation", limitation],
              ] as const
            ).map(([term, body]) => (
              <div key={term}>
                <dt className="font-mono text-[length:var(--text-micro)] uppercase tracking-[0.14em] text-paper-40">
                  {term}
                </dt>
                <dd className={term === "Limitation" ? "mt-1 text-copper-lit" : "mt-1 text-paper-70"}>
                  {body}
                </dd>
              </div>
            ))}
          </dl>
        )}
      </figcaption>
    </figure>
  );
}
