"use client";

import { Section } from "./Section";
import { Reveal } from "./Reveal";
import { Figure } from "./Figure";
import { findings } from "@/lib/data";
import { useInView } from "@/lib/useInView";

const f = findings.f1_ceiling;

const pct = (v: number) => (v / f.reference_speed_kmh) * 100;

/** The whole argument in one bar. The eye should reach the conclusion before
 *  the caption does: the copper band is small, the hatched band is not. */
function SpeedBar() {
  const { ref, hidden } = useInView<HTMLDivElement>(0.4);
  const observed = pct(f.observed_speed_kmh);
  const congestion = pct(f.congestion_gap_kmh);
  const structural = pct(f.structural_gap_kmh);

  const grow = (width: number, delay: number) => ({
    width: hidden ? "0%" : `${width}%`,
    transition: `width 1.05s cubic-bezier(0.22, 1, 0.36, 1) ${delay}s`,
  });

  return (
    <div ref={ref} className="mt-16">
      <div className="flex h-20 w-full overflow-hidden rounded-[2px] sm:h-24">
        <div
          style={grow(observed, 0)}
          className="relative flex shrink-0 items-center overflow-hidden bg-ink-600 pl-4 sm:pl-6"
        >
          <span className="whitespace-nowrap font-mono text-[length:var(--text-micro)] uppercase tracking-[0.14em] text-paper-40">
            What Siliguri gets
          </span>
        </div>

        <div
          style={grow(congestion, 0.4)}
          className="shrink-0 bg-copper"
          title={`Congestion costs ${f.congestion_gap_kmh} km/h`}
        />

        <div
          style={grow(structural, 0.62)}
          className="shrink-0 overflow-hidden border-y border-r border-dashed border-rule-lit"
          title={`The roads themselves cost ${f.structural_gap_kmh} km/h`}
        >
          <div
            aria-hidden
            className="h-full w-full"
            style={{
              backgroundImage:
                "repeating-linear-gradient(-45deg, var(--color-rule-lit) 0 1px, transparent 1px 9px)",
              opacity: 0.75,
            }}
          />
        </div>
      </div>

      {/* Scale — direct labels, no legend. */}
      <div className="relative mt-3 h-16">
        {(
          [
            [0, `${0}`],
            [f.observed_speed_kmh, `${f.observed_speed_kmh}`],
            [f.freeflow_speed_kmh, `${f.freeflow_speed_kmh}`],
            [f.reference_speed_kmh, `${f.reference_speed_kmh}`],
          ] as const
        ).map(([value, label], i) => (
          <div
            key={label}
            className="absolute top-0 flex flex-col items-start"
            style={{ left: `${pct(value as number)}%` }}
          >
            <span aria-hidden className="block h-2.5 w-px bg-rule-lit" />
            <span
              className={`mt-2 whitespace-nowrap font-mono text-[length:var(--text-micro)] tnum ${
                i === 1 ? "text-paper" : "text-paper-40"
              } ${i === 0 ? "" : i === 3 ? "-translate-x-full" : "-translate-x-1/2"}`}
            >
              {label}
            </span>
          </div>
        ))}
        <span className="absolute right-0 top-9 font-mono text-[length:var(--text-micro)] uppercase tracking-[0.14em] text-paper-40">
          km/h
        </span>
      </div>

      {/* The two gaps, named. */}
      <div className="mt-10 grid gap-8 sm:grid-cols-2">
        <div className="border-t border-copper pt-5">
          <p className="font-display text-[length:var(--text-h3)] font-light tnum text-copper-lit">
            +{f.congestion_gap_kmh} <span className="font-sans text-[0.42em] tracking-[0.06em] text-paper-40">km/h</span>
          </p>
          <p className="mt-3 text-[length:var(--text-base)] leading-snug text-paper-70">
            available from clearing congestion entirely — every signal perfect, every
            encroachment gone, no vehicle ever waiting.
          </p>
        </div>
        <div className="border-t border-rule-lit pt-5">
          <p className="font-display text-[length:var(--text-h3)] font-light tnum text-paper">
            +{f.structural_gap_kmh} <span className="font-sans text-[0.42em] tracking-[0.06em] text-paper-40">km/h</span>
          </p>
          <p className="mt-3 text-[length:var(--text-base)] leading-snug text-paper-70">
            available only from the roads themselves — width, alignment, junction
            geometry, level crossings, the number of ways across the river.
          </p>
        </div>
      </div>
    </div>
  );
}

function Estimators() {
  return (
    <Reveal className="mt-16">
      <p className="font-mono text-[length:var(--text-micro)] uppercase tracking-[0.14em] text-paper-40">
        The same question, computed three ways
      </p>
      <table className="mt-5 w-full border-collapse text-[length:var(--text-caption)]">
        <thead>
          <tr className="border-b border-rule text-left">
            <th scope="col" className="py-3 pr-4 font-medium text-paper-40">Aggregation</th>
            <th scope="col" className="py-3 pr-4 text-right font-medium text-paper-40">Observed</th>
            <th scope="col" className="py-3 pr-4 text-right font-medium text-paper-40">Free-flow</th>
            <th scope="col" className="py-3 text-right font-medium text-paper-40">Congestion&rsquo;s share</th>
          </tr>
        </thead>
        <tbody className="font-mono tnum">
          {f.estimators.map((e) => (
            <tr key={e.method} className="border-b border-rule/60">
              <td className="py-3 pr-4 font-sans text-paper-70">{e.method}</td>
              <td className="py-3 pr-4 text-right text-paper-70">{e.observed.toFixed(2)}</td>
              <td className="py-3 pr-4 text-right text-paper-70">{e.freeflow.toFixed(2)}</td>
              <td className="py-3 text-right text-paper">{e.share_pct.toFixed(1)}%</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="mt-5 measure text-[length:var(--text-caption)] leading-relaxed text-paper-40">
        Three defensible ways to aggregate the same observations land between{" "}
        {f.estimators.reduce((a, b) => (a.share_pct < b.share_pct ? a : b)).share_pct.toFixed(1)}% and{" "}
        {f.estimators.reduce((a, b) => (a.share_pct > b.share_pct ? a : b)).share_pct.toFixed(1)}%. We
        publish the range rather than pick the flattering end of it.
      </p>
    </Reveal>
  );
}

export function Ceiling() {
  return (
    <Section
      id="ceiling"
      index="01"
      eyebrow="The ceiling"
      claim={
        <>
          Siliguri is slow even when the traffic is{" "}
          <span className="italic text-gold">gone</span>.
        </>
      }
      standfirst={
        <>
          The median journey in this sample moves at {f.observed_speed_kmh} km/h. Google&rsquo;s
          modelled free-flow speed for the same journeys — the road with no other traffic on
          it — is {f.freeflow_speed_kmh} km/h. The distance between those two numbers is
          everything congestion costs Siliguri. It is {f.congestion_gap_kmh} km/h.
        </>
      }
    >
      <Reveal delay={0.1}>
        <SpeedBar />
      </Reveal>

      <div className="mt-20 grid gap-14 md:grid-cols-12 md:items-start">
        <Reveal className="md:col-span-5">
          <Figure
            value={`${f.congestion_share_pct_low}–${f.congestion_share_pct_high}`}
            unit="%"
            tone="gold"
            size="large"
            label="of the gap between Siliguri today and a 30 km/h city is congestion. The rest is the road."
            sample={`n = ${f.n.toLocaleString("en-US")}`}
            definition="The share of the shortfall to a 30 km/h reference speed that could be recovered by removing congestion alone, given as the range across three aggregation methods."
            source="Akbar, Couture, Duranton & Storeygard (AER 2023); Zenodo 10.5281/zenodo.10499064, CC BY 4.0. Google Maps Directions responses collected by the authors, 2019."
            derivation="(free-flow speed − observed speed) ÷ (30 − observed speed), computed separately as a median of per-observation speeds, a distance-weighted aggregate, and a mean of per-observation speeds."
            limitation="Free-flow is Google's modelled value, not an observed empty-road speed — TTI falls below 1.0 overnight, which is physically impossible, so the modelled baseline is optimistic. 30 km/h is a reference line, not a target anyone has adopted. Always quote this as a range."
          />
        </Reveal>

        <Reveal delay={0.12} className="md:col-span-7">
          <div className="border-l border-copper/45 pl-7">
            <p className="text-[length:var(--text-h4)] font-display font-light leading-snug text-paper">
              This reorders the budget.
            </p>
            <p className="mt-5 text-[length:var(--text-base)] leading-relaxed text-paper-70">
              Signal retiming, lane discipline, enforcement and parking control all compete
              for the same {f.congestion_gap_kmh} km/h. They are worth doing, and they are
              cheap, and they will not make Siliguri a 30 km/h city — because roughly four
              fifths of that shortfall was never traffic in the first place.
            </p>
            <p className="mt-5 text-[length:var(--text-base)] leading-relaxed text-paper-70">
              An operations plan that promises to fix Siliguri&rsquo;s travel times through
              traffic management is promising something the data says is not available. A
              plan that says <span className="text-paper">&ldquo;we will take most of the
              {" "}{f.congestion_gap_kmh} km/h that congestion holds, and the rest needs
              capacity&rdquo;</span> is promising something achievable — and it tells the
              engineering department that the larger share of the problem is theirs.
            </p>
          </div>
        </Reveal>
      </div>

      <Estimators />
    </Section>
  );
}
