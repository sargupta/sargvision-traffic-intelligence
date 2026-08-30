"use client";

import { Section } from "./Section";
import { Reveal } from "./Reveal";
import { Figure } from "./Figure";
import { TtiChart } from "./TtiChart";
import { findings, clock, num } from "@/lib/data";

const f = findings.f3_weekend;

export function WeekendMirror() {
  return (
    <Section
      id="weekend"
      index="03"
      eyebrow="The week that isn't a week"
      well
      claim={
        <>
          Saturday looks almost exactly like{" "}
          <span className="italic text-gold">Tuesday</span>.
        </>
      }
      standfirst={
        <>
          Weekend traffic peaks at the same hour as weekday traffic, at{" "}
          {f.weekend_share_of_weekday_peak}% of the same intensity. In a commuter city the
          weekend curve collapses. Here it barely moves — which says the traffic on
          Siliguri&rsquo;s roads is not mostly people going to work.
        </>
      }
    >
      <Reveal delay={0.1}>
        <TtiChart
          ariaLabel={`Median travel time index by hour, weekday against weekend. Both peak at ${clock(f.weekend_summary.peak_hour)}; the weekend peak of ${f.weekend_summary.peak_tti} is ${f.weekend_share_of_weekday_peak}% of the weekday peak of ${f.weekday_summary.peak_tti}.`}
          series={[
            { points: f.weekday, colour: "var(--color-copper)", label: "WEEKDAY", labelAt: 15, labelDy: -16 },
            { points: f.weekend, colour: "var(--color-sage)", label: "WEEKEND", dashed: true, labelAt: 15, labelDy: 24 },
          ]}
          annotations={[
            {
              hour: f.weekend_summary.peak_hour,
              tti: f.weekend_summary.peak_tti,
              title: `Both peak at ${clock(f.weekend_summary.peak_hour)}`,
              detail: `weekend ${f.weekend_summary.peak_tti} vs weekday ${f.weekday_summary.peak_tti}`,
              side: "left",
              dy: 44,
            },
          ]}
          caption={`Weekday medians from ${num(f.weekday_summary.n)} observations (Monday–Friday); weekend medians from ${num(f.weekend_summary.n)} observations (Saturday–Sunday). Same index, same method, same window.`}
        />
      </Reveal>

      <div className="mt-20 grid gap-14 md:grid-cols-12 md:items-start">
        <Reveal className="md:col-span-5">
          <Figure
            value={f.weekend_share_of_weekday_peak.toFixed(0)}
            unit="%"
            tone="gold"
            size="large"
            label="— the weekend peak as a share of the weekday peak. A commuter city would show something closer to sixty."
            sample={`n = ${num(f.weekend_summary.n)} weekend observations`}
            definition="Peak weekend median Travel Time Index divided by peak weekday median Travel Time Index, expressed as a percentage."
            source="Akbar, Couture, Duranton & Storeygard (AER 2023); Zenodo 10.5281/zenodo.10499064, CC BY 4.0."
            derivation="Median TTI per hour computed separately for Monday–Friday and Saturday–Sunday; the maximum of each series divided one by the other."
            limitation="One 2019 window of 143 days, covering monsoon into early winter. It does not include the Durga Puja to Kali Puja retail peak in full, and it cannot speak to any year since. The comparison to a 'commuter city' is our characterisation, not a measured benchmark."
          />
        </Reveal>

        <Reveal delay={0.12} className="md:col-span-7">
          <div className="border-l border-copper/45 pl-7">
            <p className="font-display text-[length:var(--text-h4)] font-light leading-snug text-paper">
              A trade city, not a commuter city.
            </p>
            <p className="mt-5 text-[length:var(--text-base)] leading-relaxed text-paper-70">
              Siliguri sits on the corridor that feeds the North-East, Nepal, Bhutan and the
              hills. What moves through it is freight, wholesale, retail, medical and
              transit traffic — and none of that observes a weekend. The curve is the
              signature of that role, visible in the data without anyone having to assert it.
            </p>
            <p className="mt-5 text-[length:var(--text-base)] leading-relaxed text-paper-70">
              This is the finding with the sharpest consequence for policy. Staggered office
              hours, school-timing changes, alternate-day schemes and every other
              office-peak intervention are aimed at a peak that is a small part of what is
              on the road here. Interventions that touch freight timing, loading and
              unloading windows, market access and through-movement are aimed at what is
              actually there.
            </p>
            <p className="mt-6 font-mono text-[length:var(--text-caption)] leading-relaxed text-paper-40">
              We can show the pattern. We cannot show the cause — this data has no vehicle
              classes and no trip purposes. Attributing it to freight is the reading we find
              most plausible, and it is the kind of claim a week of classified counts would
              settle properly.
            </p>
          </div>
        </Reveal>
      </div>
    </Section>
  );
}
