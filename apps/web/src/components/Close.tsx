import { Reveal } from "./Reveal";
import { findings } from "@/lib/data";

const f1 = findings.f1_ceiling;

export function Close() {
  return (
    <footer className="border-t border-rule">
      <div className="mx-auto w-full max-w-[78rem] px-6 py-28 sm:px-10 md:py-36 lg:px-16">
        <Reveal>
          <p className="eyebrow">The question this page exists to ask</p>
          <h2 className="mt-9 max-w-[22ch] text-[length:var(--text-h2)]">
            Is any of this <span className="italic text-gold">useful</span> to you?
          </h2>
        </Reveal>

        <Reveal delay={0.1}>
          <div className="mt-10 grid gap-14 md:grid-cols-12">
            <div className="measure md:col-span-7">
              <p className="text-[length:var(--text-lead)] leading-[1.55] text-paper-70">
                We think Siliguri would benefit from keeping a structured memory of how it
                moves — so that a claim about traffic can be checked against
                {" "}{findings.meta.days} days of evidence instead of recollection. We think
                that; we have not established it.
              </p>
              <p className="mt-6 text-[length:var(--text-base)] leading-relaxed text-paper-40">
                So this is not a proposal, and there is nothing to approve. It is four
                findings and the working behind them, put in front of the people who would
                know whether they change anything. If they are things you already act on,
                the honest conclusion is that the intelligence layer we are proposing is not
                yet worth building here — and we would rather learn that from you now than
                after building it.
              </p>
            </div>

            <div className="md:col-span-5">
              <p className="font-mono text-[length:var(--text-micro)] uppercase tracking-[0.14em] text-paper-40">
                The four, in one line each
              </p>
              <ul className="mt-5 space-y-4">
                {[
                  `Congestion is ${f1.congestion_share_pct_low}–${f1.congestion_share_pct_high}% of the gap to a 30 km/h city. The road is the rest.`,
                  "There is no morning peak. There is a twelve-hour afternoon.",
                  `The weekend peaks at ${findings.f3_weekend.weekend_share_of_weekday_peak}% of the weekday. This is a trade city.`,
                  `Only ${findings.f4_reliability.overlap} of the ${findings.f4_reliability.top_n} least dependable corridors are among the slowest.`,
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
