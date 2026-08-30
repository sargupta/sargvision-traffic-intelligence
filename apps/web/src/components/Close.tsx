import { Reveal } from "./Reveal";
import { findings, clock, num } from "@/lib/data";

const f1 = findings.f1_ceiling;
const f2 = findings.f2_shape;
const f3 = findings.f3_weekend;
const f4 = findings.f4_reliability;

/** Four consequences, each tied to the finding it follows from. This section
 *  exists because the honest test of the page is not whether the analysis is
 *  interesting — it is whether a duty officer can name something they would
 *  do differently after reading it. */
const CONSEQUENCES: { finding: string; act: string; body: string }[] = [
  {
    finding: "01 · The ceiling",
    act: "Split the target before the budget is written.",
    body: `Traffic management is bidding for ${f1.congestion_gap_kmh} km/h and capacity is bidding for ${f1.structural_gap_kmh}. Any programme that promises to fix Siliguri's travel times through enforcement and signals alone is bidding for the smaller share and will be judged on the larger one.`,
  },
  {
    finding: "02 · The shape of the day",
    act: `Staff the afternoon, not the ${clock(9)} peak.`,
    body: `The heaviest ${f2.summary.plateau_hours} hours run ${clock(f2.summary.plateau_start)} to ${clock(f2.summary.plateau_end + 1)} continuously. A roster built around two commuter spikes puts its thinnest cover across the middle of the day, which is when this city is actually slowest.`,
  },
  {
    finding: "03 · The week that isn't a week",
    act: "Aim demand measures at freight, not offices.",
    body: `Weekend traffic runs at ${f3.weekend_share_of_weekday_peak}% of weekday intensity. Staggered office hours and school-timing changes act on the part of the load that already disappears on Sunday and barely changes anything. Loading windows, market access and through-movement act on the part that does not.`,
  },
  {
    finding: "04 · Dependability",
    act: "Keep two lists, and work them differently.",
    body: `Only ${f4.overlap} of the ${f4.top_n} least dependable corridors are among the slowest. Reliably slow is a capacity problem and belongs to engineering. Usually fine and occasionally terrible is an operations problem, and it is the one that never appears on a live map.`,
  },
];

export function Close() {
  return (
    <footer className="border-t border-rule">
      <div className="mx-auto w-full max-w-[78rem] px-6 py-28 sm:px-10 md:py-36 lg:px-16">
        <Reveal>
          <p className="eyebrow">What follows from it</p>
          <h2 className="mt-9 max-w-[24ch] text-[length:var(--text-h2)]">
            Four things Siliguri could do differently on{" "}
            <span className="italic text-gold">Monday</span>.
          </h2>
          <p className="mt-8 measure text-[length:var(--text-lead)] leading-[1.55] text-paper-70">
            An analysis that ends in a chart has not finished. Each of the four findings
            changes a decision that is being made anyway — where staff go, what a scheme is
            expected to deliver, which list a corridor belongs on.
          </p>
        </Reveal>

        <ol className="mt-20 grid gap-x-16 gap-y-14 md:grid-cols-2">
          {CONSEQUENCES.map((c, i) => (
            <Reveal key={c.act} delay={i * 0.06} as="li">
              <div className="border-t border-copper/50 pt-6">
                <p className="font-mono text-[length:var(--text-micro)] uppercase tracking-[0.14em] text-copper-lit">
                  {c.finding}
                </p>
                <p className="mt-5 font-display text-[length:var(--text-h4)] font-light leading-snug text-paper">
                  {c.act}
                </p>
                <p className="mt-4 text-[length:var(--text-base)] leading-relaxed text-paper-70">
                  {c.body}
                </p>
              </div>
            </Reveal>
          ))}
        </ol>

        <Reveal delay={0.1}>
          <div className="mt-28 grid gap-14 md:grid-cols-12">
            <div className="md:col-span-7">
              <p className="font-display text-[length:var(--text-h3)] font-light leading-snug text-paper">
                What we are doing next, either way.
              </p>
              <p className="mt-6 measure text-[length:var(--text-base)] leading-relaxed text-paper-70">
                Three things, none of which require anyone&rsquo;s permission. Attach real
                corridor names, so a finding can be argued about in the language the city
                uses rather than in grid references. Extend the same method to current
                observations, so the structure above can be tested against the Siliguri of
                today instead of the Siliguri of 2019. And keep the result, so that next
                year there is something to compare against — which is the whole of what we
                mean by a city&rsquo;s memory of how it moves.
              </p>
              <p className="mt-6 measure text-[length:var(--text-base)] leading-relaxed text-paper-40">
                Whether Siliguri needs that memory is a hypothesis, and we have said so
                throughout. The way to settle it is not to argue about the idea. It is to
                put findings like these in front of the people who run the roads and find
                out which ones are wrong.
              </p>
            </div>

            <div className="md:col-span-5">
              <div className="panel p-7">
                <p className="font-mono text-[length:var(--text-micro)] uppercase tracking-[0.14em] text-copper-lit">
                  The four, in one line each
                </p>
                <ul className="mt-6 space-y-4">
                  {[
                    `Congestion is ${f1.congestion_share_pct_low}–${f1.congestion_share_pct_high}% of the gap to a 30 km/h city. The road is the rest.`,
                    `No morning peak — a ${f2.summary.plateau_hours}-hour afternoon instead.`,
                    `The weekend runs at ${f3.weekend_share_of_weekday_peak}% of the weekday. This is a trade city.`,
                    `Unreliable and slow are different lists: ${f4.overlap} of ${f4.top_n} overlap.`,
                  ].map((line, i) => (
                    <li key={i} className="flex gap-4 border-t border-rule pt-4">
                      <span className="font-mono text-[length:var(--text-micro)] tnum text-copper">
                        0{i + 1}
                      </span>
                      <span className="text-[length:var(--text-caption)] leading-relaxed text-paper-70">
                        {line}
                      </span>
                    </li>
                  ))}
                </ul>
                <p className="mt-7 border-t border-rule pt-5 text-[length:var(--text-caption)] leading-relaxed text-paper-40">
                  Every figure above is computed from {num(findings.meta.n)} valid
                  primary-route observations and carries its own derivation and limits.
                  Where we are silent, we are uninformed.
                </p>
              </div>
            </div>
          </div>
        </Reveal>

        <Reveal delay={0.16}>
          <div className="mt-24 flex flex-wrap items-end justify-between gap-8 border-t border-rule pt-8">
            <div>
              <p className="font-display text-[length:var(--text-h4)] font-light text-paper">
                SARGVISION Intelligence Pvt. Ltd.
              </p>
              <p className="mt-2 text-[length:var(--text-caption)] text-paper-40">
                Traffic Intelligence · Siliguri · self-published, not commissioned
              </p>
            </div>
            <p className="font-mono text-[length:var(--text-micro)] uppercase tracking-[0.14em] text-paper-40">
              Historical replay · {findings.meta.window_start} → {findings.meta.window_end}
            </p>
          </div>
        </Reveal>
      </div>
    </footer>
  );
}
