"use client";

import { Section } from "./Section";
import { Reveal } from "./Reveal";
import { Figure } from "./Figure";
import { findings, num } from "@/lib/data";

const f = findings.f4_reliability;

const W = 1000;
const H = 330;
const M = { top: 26, right: 26, bottom: 54, left: 26 };
const PW = W - M.left - M.right;

const LO = 0;
const HI = 42;
const BIN = 1.5;
const R = 5.2;

const x = (v: number) => M.left + ((v - LO) / (HI - LO)) * PW;

/** One dot, one corridor. Stacked into 1.5-point bins, so the silhouette is the
 *  real distribution rather than a smoothed curve that hides how few there are. */
function DotPlot() {
  const bins = new Map<number, typeof f.corridors>();
  for (const c of [...f.corridors].sort((a, b) => a.buffer_pct - b.buffer_pct)) {
    const k = Math.floor(c.buffer_pct / BIN);
    bins.set(k, [...(bins.get(k) ?? []), c]);
  }

  const baseline = H - M.bottom;
  const cutoff = f.corridors
    .map((c) => c.buffer_pct)
    .sort((a, b) => b - a)[Math.floor(f.corridors.length * 0.1)];
  const markedCount = f.corridors.filter((c) => c.buffer_pct >= cutoff).length;

  return (
    <figure className="mt-14">
      <div className="-mx-6 overflow-x-auto px-6 sm:mx-0 sm:px-0">
        <svg
          viewBox={`0 0 ${W} ${H}`}
          className="h-auto w-full min-w-[640px]"
          role="img"
          aria-label={`Distribution of buffer time across ${f.unit_count} corridors, from ${f.best}% to ${f.worst}%, median ${f.median}%. Each dot is one corridor.`}
        >
          <line x1={M.left} x2={W - M.right} y1={baseline + 1} y2={baseline + 1} stroke="var(--color-rule)" />

          {[0, 10, 20, 30, 40].map((t) => (
            <g key={t}>
              <line x1={x(t)} x2={x(t)} y1={baseline + 1} y2={baseline + 8} stroke="var(--color-rule-lit)" />
              <text
                x={x(t)}
                y={baseline + 26}
                textAnchor="middle"
                className="fill-paper-40"
                style={{ fontSize: 12.5, fontVariantNumeric: "tabular-nums" }}
              >
                {t}%
              </text>
            </g>
          ))}
          <text
            x={W - M.right}
            y={baseline + 45}
            textAnchor="end"
            className="fill-paper-40 font-mono"
            style={{ fontSize: 11.5, letterSpacing: "0.12em" }}
          >
            EXTRA TIME TO BUDGET FOR A 9-IN-10 ON-TIME ARRIVAL
          </text>

          {/* Median marker, drawn under the dots. */}
          <line
            x1={x(f.median)}
            x2={x(f.median)}
            y1={M.top - 4}
            y2={baseline}
            stroke="var(--color-paper-40)"
            strokeDasharray="3 4"
            opacity="0.65"
          />
          <text x={x(f.median)} y={M.top - 10} textAnchor="middle" className="fill-paper-40 font-mono" style={{ fontSize: 11.5, letterSpacing: "0.1em" }}>
            MEDIAN {f.median}%
          </text>

          {[...bins.entries()].map(([k, list]) =>
            list.map((c, i) => (
              <circle
                key={c.id}
                cx={x(k * BIN + BIN / 2)}
                cy={baseline - R - i * (R * 2 + 1.6)}
                r={R}
                fill={c.buffer_pct >= cutoff ? "var(--color-signal)" : "var(--color-ink-600)"}
                stroke={c.buffer_pct >= cutoff ? "var(--color-signal)" : "var(--color-rule-lit)"}
                strokeWidth="1"
              >
                <title>{`${c.buffer_pct}% buffer · ${c.speed} km/h · n = ${c.n}`}</title>
              </circle>
            )),
          )}

          {/* The two ends, named on the chart itself. */}
          <g>
            <line x1={x(f.best)} x2={x(f.best)} y1={baseline - 22} y2={baseline - 54} stroke="var(--color-gold)" strokeOpacity="0.5" />
            <text x={x(f.best)} y={baseline - 62} textAnchor="middle" className="fill-paper" style={{ fontSize: 13.5 }}>
              most dependable · {f.best}%
            </text>
          </g>
          <g>
            <line x1={x(f.worst)} x2={x(f.worst)} y1={baseline - 22} y2={baseline - 54} stroke="var(--color-signal)" strokeOpacity="0.6" />
            <text x={x(f.worst)} y={baseline - 62} textAnchor="middle" className="fill-paper" style={{ fontSize: 13.5 }}>
              least dependable · {f.worst}%
            </text>
          </g>
        </svg>
      </div>
      <figcaption className="mt-5 measure text-[length:var(--text-caption)] leading-relaxed text-paper-40">
        Each dot is one of {f.unit_count} corridors carrying at least {f.min_sample}{" "}
        observations. Position is the buffer: the extra time, over the typical journey, you
        must allow to arrive on time nine trips in ten. The {markedCount} least
        dependable are marked. Corridors are ~2 km grid-cell pairs, not named roads —
        see the limits below.
      </figcaption>
    </figure>
  );
}

export function Reliability() {
  return (
    <Section
      id="reliability"
      index="04"
      eyebrow="Dependability"
      claim={
        <>
          The corridors you cannot rely on are{" "}
          <span className="italic text-gold">not</span> the ones that are slow.
        </>
      }
      standfirst={
        <>
          Average speed tells you where Siliguri is congested. It does not tell you where
          Siliguri is <span className="text-paper">unpredictable</span> — and those turn out
          to be largely different places. Of the {f.top_n} corridors with the worst
          buffer, only {f.overlap} appear among the {f.top_n} slowest.
        </>
      }
    >
      <Reveal delay={0.1}>
        <DotPlot />
      </Reveal>

      <div className="mt-20 grid gap-14 md:grid-cols-12 md:items-start">
        <Reveal className="md:col-span-5">
          <Figure
            value={`${f.overlap} of ${f.top_n}`}
            tone="gold"
            size="large"
            label={`worst-for-reliability corridors are also among the slowest. Rank correlation between buffer and speed is ${f.rho_buffer_speed} — weak.`}
            sample={`${f.unit_count} corridors · n ≥ ${f.min_sample} each`}
            definition="Overlap between the 15 corridors with the highest buffer time and the 15 corridors with the lowest median speed, plus the Spearman rank correlation between the two measures."
            source="Akbar, Couture, Duranton & Storeygard (AER 2023); Zenodo 10.5281/zenodo.10499064, CC BY 4.0."
            derivation="Buffer = (90th percentile − 50th percentile) of travel time per kilometre, divided by the 50th percentile, per ~2 km grid-cell pair with at least 200 observations. Ranked against median observed speed for the same pairs."
            limitation="118 corridors out of 507 clear the 200-observation floor; the rest are unmeasured, not reliable. Corridors are grid-cell pairs and carry no road name. A 2019 window cannot describe today."
          />
        </Reveal>

        <Reveal delay={0.12} className="md:col-span-7">
          <div className="border-l border-copper/45 pl-7">
            <p className="font-display text-[length:var(--text-h4)] font-light leading-snug text-paper">
              Two different lists, two different jobs.
            </p>
            <p className="mt-5 text-[length:var(--text-base)] leading-relaxed text-paper-70">
              A corridor that is reliably slow is a capacity problem: it behaves the same
              way every day, and the fix is physical. A corridor that is usually fine and
              occasionally terrible is an operations problem: something intermittent is
              happening on it — a market spilling out, a crossing, unloading, a
              bottleneck that only binds sometimes.
            </p>
            <p className="mt-5 text-[length:var(--text-base)] leading-relaxed text-paper-70">
              The spread across the city is {f.spread_multiple}×: the least dependable
              corridor demands {f.worst}% extra time where the most dependable demands{" "}
              {f.best}%. Nothing in a live traffic map distinguishes these, because a live
              map only ever shows today. Separating them needs history, which is the one
              thing a live map does not keep.
            </p>
            <p className="mt-6 font-mono text-[length:var(--text-caption)] leading-relaxed text-paper-40">
              This is the finding we think is genuinely new to the room, and the one we
              would most like to be argued with about.
            </p>
          </div>
        </Reveal>
      </div>
    </Section>
  );
}
