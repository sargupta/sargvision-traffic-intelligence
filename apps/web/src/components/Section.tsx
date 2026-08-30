import type { ReactNode } from "react";
import { Reveal } from "./Reveal";

/** Sections carry an index and a claim, not a topic. Reading only the claims
 *  top to bottom should reproduce the argument — the newspaper standfirst test. */
export function Section({
  index,
  eyebrow,
  claim,
  standfirst,
  children,
  well = false,
  id,
}: {
  index: string;
  eyebrow: string;
  claim: ReactNode;
  standfirst?: ReactNode;
  children: ReactNode;
  well?: boolean;
  id?: string;
}) {
  return (
    <section
      id={id}
      className={well ? "bg-abyss" : undefined}
      aria-labelledby={id ? `${id}-claim` : undefined}
    >
      <div className="mx-auto w-full max-w-[78rem] px-6 py-24 sm:px-10 md:py-32 lg:px-16">
        <Reveal>
          <div className="flex items-baseline gap-5">
            <span className="font-mono text-[length:var(--text-micro)] tracking-[0.18em] text-copper">
              {index}
            </span>
            <span className="eyebrow">{eyebrow}</span>
          </div>
          <hr className="mt-4 border-0 border-t border-rule" />
        </Reveal>

        <Reveal delay={0.08}>
          <h2
            id={id ? `${id}-claim` : undefined}
            className="mt-10 max-w-[19ch] text-[length:var(--text-h2)]"
          >
            {claim}
          </h2>
        </Reveal>

        {standfirst && (
          <Reveal delay={0.14}>
            <div className="mt-7 measure text-[length:var(--text-lead)] leading-[1.55] text-paper-70">
              {standfirst}
            </div>
          </Reveal>
        )}

        {children}
      </div>
    </section>
  );
}
