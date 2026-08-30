import { Section } from "./Section";
import { Reveal } from "./Reveal";
import { findings, num } from "@/lib/data";

const { meta, coverage, f4_reliability: f4 } = findings;

const LIMITS: [string, string][] = [
  [
    "This is 2019, and it is not live",
    `The window runs ${meta.window_start} to ${meta.window_end} — ${meta.days} days, seven years ago. Siliguri has since gained vehicles, lost road space and changed its junctions. Nothing on this page describes today's traffic, and nothing here updates. Treat every finding as a statement about structure, which changes slowly, and not about conditions, which do not.`,
  ],
  [
    "The corridors have no names",
    `A corridor here is a pair of grid cells — ${f4.corridors[0].id} — covering roughly two kilometres. It is not Sevoke Road or Hill Cart Road, and we have deliberately not guessed. Attaching real road names needs either the Commissionerate's corridor definitions or a routed dataset, and guessing would put a real name on a claim the data cannot carry.`,
  ],
  [
    "Free-flow is modelled, not observed",
    "The comparison speed is Google's estimate of the same journey on an empty road, not a measurement of one. We know it is optimistic because the index falls below 1.0 overnight, which cannot physically happen. This is why the congestion share is published as a range and never as a single decimal.",
  ],
  [
    "Most of the city did not clear the sample floor",
    `${f4.unit_count} corridors of 507 carry the ${f4.min_sample} observations we require, and ${coverage.summary.INSUFFICIENT} of ${coverage.cell_count} observed cells fall under the ${meta.min_bin}-observation publishing floor. Where we are silent, we are uninformed — not reassuring.`,
  ],
  [
    "We cannot tell you why",
    "There are no vehicle classes, no trip purposes, no incident records and no signal timings in this dataset. Every causal reading on this page — freight, market access, through-movement — is our interpretation offered as such, and each one is the kind of claim a week of proper counts would settle.",
  ],
];

export function Limits() {
  return (
    <Section
      id="limits"
      index="06"
      eyebrow="What this is not"
      well
      claim={
        <>
          Everything above is <span className="italic text-gold">wrong</span> in at least
          five specific ways.
        </>
      }
      standfirst={
        <>
          A finding you cannot argue with is a finding nobody checked. These are the limits
          we know about, stated at the same size as the findings, because a page that
          buries them is asking to be believed rather than examined.
        </>
      }
    >
      <div className="mt-16 grid gap-x-16 gap-y-12 md:grid-cols-2">
        {LIMITS.map(([title, body], i) => (
          <Reveal key={title} delay={i * 0.05} className={i === 4 ? "md:col-span-2 md:max-w-[calc(50%-2rem)]" : ""}>
            <div className="border-t border-copper/50 pt-6">
              <p className="font-display text-[length:var(--text-h4)] font-light leading-snug text-paper">
                {title}
              </p>
              <p className="mt-4 text-[length:var(--text-base)] leading-relaxed text-paper-70">{body}</p>
            </div>
          </Reveal>
        ))}
      </div>

      <Reveal className="mt-28">
        <p className="font-mono text-[length:var(--text-micro)] uppercase tracking-[0.14em] text-paper-40">
          Where the numbers come from
        </p>
        <div className="mt-6 grid gap-12 md:grid-cols-12">
          <div className="md:col-span-7">
            <ol className="space-y-0">
              {(
                [
                  ["Published dataset", "Zenodo 10.5281/zenodo.10499064 · CC BY 4.0 · no login, no permission required"],
                  ["Paper", "Akbar, Couture, Duranton & Storeygard, “Mobility and Congestion in Urban India”, American Economic Review 113(4), 2023"],
                  ["City", "WUP_cities row 154 → India / Siliguri / citycode 21405"],
                  ["Trips", `14,612 Siliguri trip records joined against 21,657,714 observations`],
                  ["Raw join", "115,347 observations"],
                  ["Valid", "115,330 after removing non-positive times and distances"],
                  ["Published", `${num(meta.n)} valid primary-route observations · ${num(meta.trips)} distinct trips`],
                ] as const
              ).map(([step, detail], i) => (
                <li key={step} className="flex gap-6 border-b border-rule/70 py-4">
                  <span className="w-6 shrink-0 font-mono text-[length:var(--text-micro)] tnum text-copper">
                    {String(i + 1).padStart(2, "0")}
                  </span>
                  <div>
                    <p className="text-[length:var(--text-caption)] font-medium text-paper">{step}</p>
                    <p className="mt-1 text-[length:var(--text-caption)] leading-relaxed text-paper-40">{detail}</p>
                  </div>
                </li>
              ))}
            </ol>
            <p className="mt-6 measure text-[length:var(--text-caption)] leading-relaxed text-paper-40">
              Only primary routes are kept. One origin–destination query returns several
              alternatives; counting each as an independent observation would count the same
              query two or three times. The archive is 1.6 GB and was never downloaded whole
              — two members were pulled by HTTP range request.
            </p>
          </div>

          <div className="md:col-span-5">
            <div className="panel p-7">
              <p className="font-mono text-[length:var(--text-micro)] uppercase tracking-[0.14em] text-copper-lit">
                Built without asking anyone
              </p>
              <p className="mt-5 text-[length:var(--text-base)] leading-relaxed text-paper-70">
                No data was requested from the Commissionerate, no survey was run, no sensor
                was installed and no vendor was involved. A published dataset, our own
                analysis and Google Maps for geography.
              </p>
              <p className="mt-5 text-[length:var(--text-base)] leading-relaxed text-paper-70">
                We built it this way on purpose. Anything that needs permission first cannot
                be shown to the person whose permission it needs.
              </p>
              <hr className="my-7 border-0 border-t border-rule" />
              <p className="text-[length:var(--text-caption)] leading-relaxed text-paper-40">
                {meta.source}
              </p>
            </div>
          </div>
        </div>
      </Reveal>
    </Section>
  );
}
