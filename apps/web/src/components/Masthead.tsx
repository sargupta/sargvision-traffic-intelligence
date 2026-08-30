"use client";

import { findings, num } from "@/lib/data";

const { meta, f2_shape } = findings;

/** The hero's only ornament is the city's own 24-hour congestion curve, drawn
 *  at low opacity. It is real data, not decoration invented to fill space —
 *  and it previews the finding that section 02 makes explicitly. */
function SignatureCurve() {
  const hours = f2_shape.hours;
  const W = 1200;
  const H = 200;
  const lo = 0.9;
  const hi = 1.3;
  const x = (h: number) => (h / 23) * W;
  const y = (t: number) => H - ((t - lo) / (hi - lo)) * H;

  const d = hours
    .map((p, i) => `${i === 0 ? "M" : "L"}${x(p.hour).toFixed(1)},${y(p.tti).toFixed(1)}`)
    .join(" ");

  return (
    <svg
      className="pointer-events-none absolute inset-x-0 bottom-0 h-[38vh] w-full"
      viewBox={`0 0 ${W} ${H}`}
      preserveAspectRatio="none"
      aria-hidden="true"
      focusable="false"
    >
      <defs>
        <linearGradient id="sig-fade" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="var(--color-copper)" stopOpacity="0.16" />
          <stop offset="100%" stopColor="var(--color-copper)" stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={`${d} L${W},${H} L0,${H} Z`} fill="url(#sig-fade)" />
      <path
        d={d}
        fill="none"
        stroke="var(--color-copper)"
        strokeOpacity="0.5"
        strokeWidth="1.25"
        vectorEffect="non-scaling-stroke"
        className="stroke-draw"
        style={{ ["--len" as string]: "2400" }}
      />
    </svg>
  );
}

export function Masthead() {
  return (
    <header className="relative isolate overflow-hidden">
      {/* Design principle 5 — replay mode is stated, never implied. */}
      <div className="sticky top-0 z-40 border-b border-copper/35 bg-abyss/92 backdrop-blur-sm">
        <div className="mx-auto flex w-full max-w-[78rem] flex-wrap items-center gap-x-4 gap-y-1 px-6 py-2.5 sm:px-10 lg:px-16">
          <span
            aria-hidden
            className="h-1.5 w-1.5 shrink-0 rounded-full bg-copper"
          />
          <span className="font-mono text-[length:var(--text-micro)] uppercase tracking-[0.16em] text-copper-lit">
            Historical replay
          </span>
          <span className="font-mono text-[length:var(--text-micro)] tracking-[0.04em] text-paper-40">
            {meta.window_start} → {meta.window_end} · this page shows nothing that is happening now
          </span>
        </div>
      </div>

      <SignatureCurve />

      <div className="relative mx-auto w-full max-w-[78rem] px-6 pb-32 pt-24 sm:px-10 md:pb-44 md:pt-36 lg:px-16">
        <p className="eyebrow enter" style={{ ["--enter-delay" as string]: "0.05s" }}>
          SARGVISION Intelligence Pvt. Ltd. · Traffic Intelligence
        </p>

        <h1
          className="enter enter-rise mt-7 text-[length:var(--text-h1)] font-light leading-[0.92] tracking-[-0.03em]"
          style={{ ["--enter-delay" as string]: "0.14s" }}
        >
          How Siliguri
          <br />
          <span className="italic text-gold">moves</span>
        </h1>

        <div className="enter mt-12 grid gap-12 md:grid-cols-12" style={{ ["--enter-delay" as string]: "0.4s" }}>
          <div className="measure md:col-span-7">
            <p className="text-[length:var(--text-lead)] leading-[1.55] text-paper-70">
              Four findings about travel time in Siliguri, read out of{" "}
              <span className="text-paper">{meta.canonical_sample}</span> recorded across{" "}
              {meta.days} days in 2019.
            </p>
            <p className="mt-6 text-[length:var(--text-base)] leading-relaxed text-paper-40">
              We did not survey anyone, install anything, or ask the Commissionerate for
              access. Everything here comes from a published academic dataset and our own
              analysis of it. We are showing this first because the useful question is not
              whether we can build a traffic system — it is whether what the data already
              says is worth knowing.
            </p>
          </div>

          <dl className="grid grid-cols-2 gap-x-8 gap-y-7 self-end md:col-span-5 md:grid-cols-2">
            {[
              ["Observations", num(meta.n)],
              ["Distinct trips", num(meta.trips)],
              ["Days observed", num(meta.days)],
              ["Live feeds", "None"],
            ].map(([term, value]) => (
              <div key={term} className="border-t border-rule pt-4">
                <dt className="font-mono text-[length:var(--text-micro)] uppercase tracking-[0.14em] text-paper-40">
                  {term}
                </dt>
                <dd className="mt-2 font-display text-[length:var(--text-h4)] font-light tnum text-paper">
                  {value}
                </dd>
              </div>
            ))}
          </dl>
        </div>
      </div>
    </header>
  );
}
