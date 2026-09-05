"use client";

import { useEffect, useState } from "react";
import { Chrome } from "@/components/Chrome";
import { BandTag, EscalationChip, PriorityTag } from "@/components/Bits";
import { getHandover, minutes, STATE_LABEL, useBoard, type HandoverPayload, type HandoverSummary } from "@/lib/api";

function Group({
  title,
  detail,
  items,
  emphasis = false,
}: {
  title: string;
  detail: string;
  items: HandoverSummary[];
  emphasis?: boolean;
}) {
  return (
    <section className="mb-6 break-inside-avoid">
      <h2 className="flex items-baseline gap-2 text-[length:var(--text-md)] font-semibold">
        {title}
        <span className="tnum text-[length:var(--text-sm)] font-normal text-ink-3">{items.length}</span>
      </h2>
      <p className="mt-0.5 max-w-[74ch] text-[length:var(--text-sm)] text-ink-2">{detail}</p>

      {items.length === 0 ? (
        <p className="mt-2 rounded border border-dashed border-line-firm px-3 py-2.5 text-[length:var(--text-sm)] text-ink-3">
          None.
        </p>
      ) : (
        <ul className="mt-2.5 space-y-2">
          {items.map((i) => (
            <li
              key={i.incident_id}
              data-band={i.priority}
              className={`rounded border border-line bg-surface p-3 ${emphasis ? "border-l-[3px]" : ""}`}
              style={emphasis ? { borderLeftColor: "var(--color-sev)" } : undefined}
            >
              <div className="flex flex-wrap items-center gap-2">
                <PriorityTag priority={i.priority} />
                <span className="rounded bg-sunken px-2 py-0.5 text-[length:var(--text-2xs)] font-medium text-ink-2">
                  {STATE_LABEL[i.state]}
                </span>
                <span className="tnum text-[length:var(--text-2xs)] text-ink-3">
                  {minutes(i.age_minutes)} old
                </span>
                <EscalationChip escalation={i.escalation} />
                <span className="tnum ml-auto font-mono text-[length:var(--text-2xs)] text-ink-3">
                  {i.incident_id}
                </span>
              </div>
              <p className="mt-1.5 text-[length:var(--text-base)] font-medium leading-snug">{i.title}</p>
              <p className="text-[length:var(--text-sm)] text-ink-2">{i.location_name}</p>
              {i.owner && (
                <p className="mt-1 text-[length:var(--text-sm)] text-ink-2">
                  With <strong className="font-semibold text-ink">{i.owner}</strong>
                </p>
              )}
              {i.notes.length > 0 && (
                <ul className="mt-2 space-y-1 border-l-2 border-line pl-2.5">
                  {i.notes.map((n, k) => (
                    <li key={k} className="text-[length:var(--text-sm)] leading-snug">
                      <span className="label mr-1.5">{n.kind}</span>
                      <span className="text-ink-2">{n.text}</span>
                      <span className="ml-1.5 text-[length:var(--text-2xs)] text-ink-3">— {n.author}</span>
                    </li>
                  ))}
                </ul>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

export default function Handover() {
  const { board, connected } = useBoard();
  const [data, setData] = useState<HandoverPayload | null>(null);
  const [hours, setHours] = useState(8);
  const [outgoing, setOutgoing] = useState("");
  const [incoming, setIncoming] = useState("");

  useEffect(() => {
    getHandover(hours).then(setData).catch(() => setData(null));
  }, [hours]);

  const lapse = data?.alerting_quality.lapse_rate ?? 0;

  return (
    <>
      <Chrome at={board?.at} connected={connected} cycle={board?.cycle} officer="Duty Officer" pollSeconds={board?.poll_seconds} />

      <main id="main" className="mx-auto w-full max-w-[62rem] px-4 py-5 lg:px-6">
        <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
          <div>
            <h1 className="text-[length:var(--text-xl)] font-semibold">Shift handover</h1>
            <p className="mt-1 max-w-[74ch] text-[length:var(--text-sm)] leading-relaxed text-ink-2">
              What the next shift inherits and what this one did. Meant to be read, saved and
              printed — this page is a record, not a dashboard.
            </p>
          </div>
          <div className="flex items-center gap-2 no-print">
            <label className="label" htmlFor="hours">Window</label>
            <select
              id="hours"
              value={hours}
              onChange={(e) => setHours(Number(e.target.value))}
              className="rounded border border-line-firm bg-surface px-2.5 py-1.5 text-[length:var(--text-sm)]"
            >
              {[4, 8, 12, 24].map((h) => (
                <option key={h} value={h}>{h} hours</option>
              ))}
            </select>
            <button
              type="button"
              onClick={() => window.print()}
              className="rounded bg-navy px-3 py-1.5 text-[length:var(--text-sm)] font-medium text-white"
            >
              Print
            </button>
          </div>
        </div>

        {data && (
          <>
            {/* SITUATION — the thirty-second read the incoming officer needs
                before anything else. */}
            <section className="card mb-4 border-l-[3px] px-5 py-4" style={{ borderLeftColor: "var(--color-navy)" }}>
              <p className="label">Situation at handover</p>
              <p className="mt-1.5 text-[length:var(--text-lg)] font-semibold leading-snug">
                {data.situation.assessment}
              </p>
              <dl className="mt-3 flex flex-wrap gap-x-8 gap-y-2">
                {(
                  [
                    ["Open", data.situation.open],
                    ["Unowned", data.situation.unowned],
                    ["Past deadline", data.situation.overdue],
                    ["Raised this window", data.situation.raised_in_window],
                    ["Elevated now", data.situation.elevated_now],
                  ] as const
                ).map(([k, v]) => (
                  <div key={k}>
                    <dt className="label">{k}</dt>
                    <dd
                      className="tnum text-[length:var(--text-xl)] font-semibold leading-none"
                      style={{ color: k === "Past deadline" && v > 0 ? "var(--color-sev)" : k === "Unowned" && v > 0 ? "var(--color-high)" : undefined }}
                    >
                      {v}
                    </dd>
                  </div>
                ))}
              </dl>
            </section>

            {/* WATCH — what is live on the road right now; the abnormal-conditions
                line of a control-room turnover. */}
            {data.watch.length > 0 && (
              <section className="card mb-4 px-5 py-4 break-inside-avoid">
                <h2 className="text-[length:var(--text-md)] font-semibold">Watch this shift</h2>
                <p className="mt-0.5 text-[length:var(--text-sm)] text-ink-2">
                  Corridors above their typical travel time at handover, worst first.
                </p>
                <ul className="mt-2.5 flex flex-wrap gap-2">
                  {data.watch.map((w) => (
                    <li key={w.name} className="flex items-center gap-2 rounded border border-line bg-surface px-2.5 py-1.5 text-[length:var(--text-sm)]">
                      <BandTag band={w.band} />
                      <span className="font-medium">{w.name}</span>
                      {w.index != null && <span className="tnum text-[length:var(--text-2xs)] text-ink-3">{w.index}×</span>}
                    </li>
                  ))}
                </ul>
              </section>
            )}

            <div className="card mb-6 px-4 py-3">
              <div className="flex flex-wrap items-baseline gap-x-8 gap-y-2">
                <p className="text-[length:var(--text-sm)] text-ink-2">
                  <span className="label mr-2">Period</span>
                  <span className="tnum">{data.from.replace("T", " ")} → {data.to.replace("T", " ")}</span>
                </p>
                <p className="text-[length:var(--text-sm)] text-ink-2">
                  <span className="label mr-2">Raised</span>
                  <span className="tnum font-semibold text-ink">{data.raised}</span>
                </p>
                <p className="text-[length:var(--text-sm)] text-ink-2">
                  <span className="label mr-2">Cleared on their own</span>
                  <span
                    className="tnum font-semibold"
                    style={{ color: lapse > 0.4 ? "var(--color-high)" : "var(--color-ink)" }}
                  >
                    {Math.round(lapse * 100)}%
                  </span>
                </p>
              </div>
              {lapse > 0.4 && (
                <p className="mt-2 rounded bg-high-tint px-3 py-2 text-[length:var(--text-sm)] leading-relaxed" style={{ color: "var(--color-high)" }}>
                  More than two in five conditions cleared before anyone acted. That is the system
                  raising things that did not need an officer, and the thresholds should be reviewed.
                </p>
              )}
            </div>

            <Group
              title="Needs an owner"
              detail="Open, and nobody has taken responsibility. Deal with these first."
              items={data.handing_over.needs_an_owner}
              emphasis
            />
            <Group
              title="In hand"
              detail="Open, with an officer assigned. Confirm they are still on it."
              items={data.handing_over.in_hand}
            />

            <div className="page-break" />

            <Group
              title="Closed this period"
              detail="Acted on and resolved, with the outcome recorded."
              items={data.this_shift.closed}
            />
            <Group
              title="No action needed"
              detail="An officer looked and judged no deployment necessary. A decision, and recorded as one."
              items={data.this_shift.stood_down}
            />
            <Group
              title="Cleared on their own"
              detail={data.alerting_quality.note}
              items={data.this_shift.lapsed}
            />

            {/* SIGN-OFF — a handover transfers responsibility, so it is signed.
                The names are for the printed record; nothing is submitted. */}
            <section className="mt-6 break-inside-avoid rounded-lg border border-line-firm p-4">
              <h2 className="text-[length:var(--text-md)] font-semibold">Sign-off</h2>
              <p className="mt-0.5 text-[length:var(--text-sm)] text-ink-2">
                Responsibility passes when both officers have read the above. Enter names for the
                printed record.
              </p>
              <div className="mt-3 grid gap-3 sm:grid-cols-2">
                {(
                  [
                    ["Handed over by", outgoing, setOutgoing],
                    ["Received by", incoming, setIncoming],
                  ] as const
                ).map(([label, value, setter]) => (
                  <label key={label} className="block">
                    <span className="label">{label}</span>
                    <input
                      value={value}
                      onChange={(e) => setter(e.target.value)}
                      placeholder="Name and rank"
                      className="mt-1 w-full rounded border border-line-firm bg-surface px-3 py-2 text-[length:var(--text-sm)]"
                    />
                  </label>
                ))}
              </div>
              <p className="mt-3 text-[length:var(--text-2xs)] text-ink-3">
                Prepared {new Date().toLocaleString("en-IN")} · covers the {data.window_hours}-hour window ending{" "}
                {data.to.replace("T", " ")}.
              </p>
            </section>

            <footer className="mt-8 border-t border-line pt-4 text-[length:var(--text-2xs)] leading-relaxed text-ink-3">
              <p>
                Siliguri Traffic Command · SARGVISION Intelligence Pvt. Ltd. · generated{" "}
                {new Date().toLocaleString("en-IN")}
              </p>
              <p className="mt-1">
                Conditions are derived from Google Maps travel-time data. The system reports where
                traffic is slow and by how much; it does not establish a cause. Any cause recorded
                above was entered by the named officer.
              </p>
            </footer>
          </>
        )}
      </main>
    </>
  );
}
