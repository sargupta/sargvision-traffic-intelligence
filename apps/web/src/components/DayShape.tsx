"use client";

import { Section } from "./Section";
import { Reveal } from "./Reveal";
import { Figure } from "./Figure";
import { TtiChart } from "./TtiChart";
import { findings, clock, num } from "@/lib/data";

const f = findings.f2_shape;
const at = (h: number) => f.hours.find((p) => p.hour === h)!;

const morning = at(8);
const noon = at(12);
const peak = at(f.summary.peak_hour);

export function DayShape() {
  return (
    <Section
      id="shape"
      index="02"
      eyebrow="The shape of the day"
      claim={
        <>
          There is no morning rush hour. There is a{" "}
          <span className="italic text-gold">twelve-hour afternoon</span>.
        </>
      }
      standfirst={
        <>
          At {clock(8)} — the hour every city plans around — Siliguri is running within{" "}
          {((morning.tti - 1) * 100).toFixed(1)}% of free-flow. Congestion arrives late,
          settles in around {clock(f.summary.plateau_start)}, and does not leave until{" "}
          {clock(f.summary.plateau_end + 1)}. Midday is not a lull. Midday is the peak,
          near enough.
        </>
      }
    >
      <Reveal delay={0.1}>
        <TtiChart
          ariaLabel={`Median travel time index by hour on weekdays in Siliguri. Near free-flow until ${clock(9)}, rising to a plateau from ${clock(f.summary.plateau_start)} to ${clock(f.summary.plateau_end)}, peaking at ${clock(peak.hour)} at ${peak.tti}.`}
          band={[f.summary.plateau_start, f.summary.plateau_end]}
          bandLabel={`${f.summary.plateau_hours} congested hours`}
          series={[
            {
              points: f.hours,
              colour: "var(--color-copper)",
              label: "WEEKDAY",
              fill: true,
            },
          ]}
          annotations={[
            {
              hour: 8,
              tti: morning.tti,
              title: `${clock(8)} — the rush hour that isn't`,
              detail: `TTI ${morning.tti.toFixed(3)} · ${morning.speed} km/h · n = ${num(morning.n)}`,
              side: "right",
              dy: -44,
            },
            {
              hour: 12,
              tti: noon.tti,
              title: "Midday, not a lull",
              detail: `TTI ${noon.tti.toFixed(3)} · n = ${num(noon.n)}`,
              side: "left",
              dy: -52,
            },
            {
              hour: peak.hour,
              tti: peak.tti,
              title: `${clock(peak.hour)} — the day's worst`,
              detail: `TTI ${peak.tti.toFixed(3)} · ${peak.speed} km/h · n = ${num(peak.n)}`,
              side: "left",
              dy: -30,
            },
          ]}
          caption={`Travel Time Index is observed travel time divided by Google's modelled free-flow time for the same journey; 1.20 means a trip takes 20% longer than an empty road would allow. Weekday medians, Monday to Friday, ${num(f.summary.n)} observations. Hours with fewer than ${findings.meta.min_bin} observations are not plotted.`}
        />
      </Reveal>

      <div className="mt-20 grid gap-14 md:grid-cols-12 md:items-start">
        <Reveal className="md:col-span-5">
          <Figure
            value={f.summary.plateau_hours.toString()}
            unit="hours"
            tone="gold"
            size="large"
            label={`of the weekday sit at or above 10% over free-flow — a continuous block from ${clock(f.summary.plateau_start)} to ${clock(f.summary.plateau_end + 1)}, not two commuter spikes.`}
            sample={`n = ${num(f.summary.n)} weekday observations`}
            definition="Count of hours whose median Travel Time Index is at least 1.10, on weekdays."
            source="Akbar, Couture, Duranton & Storeygard (AER 2023); Zenodo 10.5281/zenodo.10499064, CC BY 4.0."
            derivation="Median TTI computed per hour across all weekday observations, then counted where the median is ≥ 1.10. Hours with fewer than 30 observations are excluded."
            limitation="The 1.10 cut is our choice, not a standard. A different cut moves the count. The shape of the curve — flat morning, long afternoon — does not depend on where the line is drawn."
          />
        </Reveal>

        <Reveal delay={0.12} className="md:col-span-7">
          <div className="border-l border-copper/45 pl-7">
            <p className="font-display text-[length:var(--text-h4)] font-light leading-snug text-paper">
              You already know this. That is not the problem.
            </p>
            <p className="mt-5 text-[length:var(--text-base)] leading-relaxed text-paper-70">
              Any officer who has worked a shift in Siliguri could have told us the
              afternoon is worse than the morning. Experience is not the gap here.
              Evidence is. There is a difference between a duty officer knowing it and a
              budget proposal being able to <span className="text-paper">prove</span> it
              across {num(findings.meta.days)} days and {num(f.summary.n)} observations.
            </p>
            <p className="mt-5 text-[length:var(--text-base)] leading-relaxed text-paper-70">
              The practical consequence is about where staff and attention go. A deployment
              built around two commuter peaks is built around a pattern this city does not
              have. The demand here is continuous, and it is heaviest when most planning
              assumes a lull.
            </p>
          </div>
        </Reveal>
      </div>
    </Section>
  );
}
