"use client";

import { SIGNAL_LABEL, STATUS_COLOUR, hhmm, type Finding } from "@/lib/live";

/** The feed decides what deserves attention; the user does not have to know
 *  where to look. Order is the engine's priority score — severity, persistence,
 *  confidence and breadth multiplied — not recency. */
export function Feed({
  findings,
  onInvestigate,
  activeId,
}: {
  findings: Finding[];
  onInvestigate: (f: Finding) => void;
  activeId: string | null;
}) {
  if (findings.length === 0) {
    return (
      <div className="border-t border-rule px-5 py-8">
        <p className="font-display text-[length:var(--text-h4)] font-light leading-snug text-paper">
          Nothing is above expected.
        </p>
        <p className="mt-3 text-[length:var(--text-caption)] leading-relaxed text-paper-40">
          The engine is comparing every monitored movement against its own baseline for this
          hour and this day type, and none of them has crossed a threshold. This is a result,
          not an empty screen.
        </p>
      </div>
    );
  }

  return (
    <ul className="divide-y divide-rule">
      {findings.map((f) => {
        const active = activeId === f.id;
        return (
          <li key={f.id}>
            <button
              type="button"
              onClick={() => onInvestigate(f)}
              aria-current={active ? "true" : undefined}
              className={`block w-full px-5 py-4 text-left transition-colors ${
                active ? "bg-ink-700" : "hover:bg-ink-700/60"
              }`}
            >
              <div className="flex items-center gap-2.5">
                <span
                  aria-hidden
                  className="h-2 w-2 shrink-0 rounded-full"
                  style={{ backgroundColor: STATUS_COLOUR[f.severity] }}
                />
                <span className="font-mono text-[length:var(--text-micro)] tnum text-paper-40">
                  {hhmm(f.detected_at)}
                </span>
                <span className="font-mono text-[length:var(--text-micro)] uppercase tracking-[0.12em] text-copper-lit">
                  {SIGNAL_LABEL[f.signal]}
                </span>
                {f.state === "RESOLVED" && (
                  <span className="font-mono text-[length:var(--text-micro)] uppercase tracking-[0.12em] text-paper-40">
                    resolved
                  </span>
                )}
                <span className="ml-auto font-mono text-[length:var(--text-micro)] tnum text-paper-40">
                  p {f.priority.toFixed(2)}
                </span>
              </div>

              <p className="mt-2 text-[length:var(--text-base)] leading-snug text-paper">{f.title}</p>
              <p className="mt-1.5 text-[length:var(--text-caption)] leading-relaxed text-paper-70">
                {f.claim}
              </p>

              <div className="mt-2.5 flex flex-wrap items-center gap-x-4 gap-y-1 font-mono text-[length:var(--text-micro)] tnum text-paper-40">
                <span>{f.confidence.toLowerCase()} confidence</span>
                {f.persistence_minutes > 0 && <span>held {f.persistence_minutes.toFixed(0)} min</span>}
                <span>
                  {f.movements.length} movement{f.movements.length === 1 ? "" : "s"}
                </span>
                {f.components.length > 0 && <span>absorbs {f.components.length}</span>}
              </div>
            </button>
          </li>
        );
      })}
    </ul>
  );
}
