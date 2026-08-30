"use client";

import { useState } from "react";
import type { Recommendation } from "@/lib/api";

const URGENCY: Record<Recommendation["urgency"], { label: string; fg: string; tint: string }> = {
  NOW: { label: "Now", fg: "var(--color-sev)", tint: "var(--color-sev-tint)" },
  THIS_SHIFT: { label: "This shift", fg: "var(--color-high)", tint: "var(--color-high-tint)" },
  ADVISORY: { label: "Advisory", fg: "var(--color-none)", tint: "var(--color-none-tint)" },
};

const KIND: Record<Recommendation["kind"], string> = {
  POST: "Post an officer",
  DIVERT: "Divert",
  ESCALATE: "Escalate",
  WATCH: "Watch",
  STAND_DOWN: "No action",
};

/** Suggestions, with their working shown.
 *
 *  "Because" and "cannot know" are not decoration. A recommendation an officer
 *  cannot audit is one they stop reading by the second week, and the fastest
 *  way to lose a control room is to be confidently wrong once about something
 *  they could not check.
 */
export function Advice({ items }: { items: Recommendation[] }) {
  const [open, setOpen] = useState<number | null>(0);

  if (items.length === 0) return null;

  return (
    <section aria-labelledby="advice-heading">
      <h2 id="advice-heading" className="mb-2.5 flex items-baseline gap-2 text-[length:var(--text-md)] font-semibold">
        What to do
        <span className="tnum text-[length:var(--text-sm)] font-normal text-ink-3">{items.length}</span>
      </h2>

      <ul className="flex flex-col gap-2.5">
        {items.map((r, i) => {
          const u = URGENCY[r.urgency];
          const expanded = open === i;
          return (
            <li
              key={`${r.kind}-${i}`}
              data-band={r.urgency}
              className="card overflow-hidden border-l-[3px]"
              style={{ borderLeftColor: u.fg }}
            >
              <div className="p-3.5">
                <div className="flex flex-wrap items-center gap-2">
                  <span
                    className="rounded px-2 py-0.5 text-[length:var(--text-2xs)] font-semibold"
                    style={{ color: u.fg, backgroundColor: u.tint }}
                  >
                    {u.label}
                  </span>
                  <span className="label">{KIND[r.kind]}</span>
                </div>

                <p className="mt-2 text-[length:var(--text-md)] font-semibold leading-snug">
                  {r.headline}
                </p>
                <p className="mt-1.5 text-[length:var(--text-sm)] leading-relaxed text-ink-2">
                  {r.detail}
                </p>

                <button
                  type="button"
                  onClick={() => setOpen(expanded ? null : i)}
                  aria-expanded={expanded}
                  className="mt-2.5 text-[length:var(--text-sm)] font-medium text-ink-2 underline decoration-line-firm underline-offset-2 hover:text-ink no-print"
                >
                  {expanded ? "Hide the working" : "Why this?"}
                </button>

                {expanded && (
                  <div className="mt-2.5 border-t border-line pt-2.5">
                    <p className="label">Because</p>
                    <ul className="mt-1.5 space-y-1">
                      {r.because.filter(Boolean).map((b, k) => (
                        <li key={k} className="flex gap-2 text-[length:var(--text-sm)] leading-snug text-ink-2">
                          <span aria-hidden className="text-ink-3">·</span>
                          <span>{b}</span>
                        </li>
                      ))}
                    </ul>
                    <p className="label mt-3">What this cannot tell you</p>
                    <p
                      className="mt-1 text-[length:var(--text-sm)] leading-relaxed"
                      style={{ color: "var(--color-copper)" }}
                    >
                      {r.cannot_know}
                    </p>
                  </div>
                )}
              </div>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
