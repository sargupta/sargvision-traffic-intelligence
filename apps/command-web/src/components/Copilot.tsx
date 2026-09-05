"use client";

import type { Band, CopilotAnswer } from "@/lib/api";
import { BandTag } from "./Bits";

/** Suggested questions, grouped by what they reach — so an officer discovers the
 *  range, not just the one phrasing in the placeholder. Past and present both. */
export const SUGGESTIONS: { group: string; questions: string[] }[] = [
  {
    group: "Right now",
    questions: [
      "What should I be worried about right now?",
      "Which corridors are worst at the moment?",
      "Any incidents past their deadline?",
    ],
  },
  {
    group: "Typically",
    questions: [
      "When is travel usually worst on a weekday?",
      "Is now unusual for this hour?",
    ],
  },
  {
    group: "Verify & safety",
    questions: [
      "Did our deployments work today?",
      "Which junctions are dangerous, and is that where it's congested?",
    ],
  },
  { group: "Changes", questions: ["What changed in the last hour?"] },
];

type Row = Record<string, unknown>;
const n = (v: unknown) => (typeof v === "number" ? v : null);
const s = (v: unknown) => (typeof v === "string" ? v : "");
const rows = (v: unknown): Row[] => (Array.isArray(v) ? (v as Row[]).filter((r) => r && !("…" in r)) : []);

function Tiles({ items }: { items: [string, unknown][] }) {
  return (
    <dl className="flex flex-wrap gap-x-6 gap-y-2">
      {items.map(([k, v]) => (
        <div key={k}>
          <dt className="label">{k}</dt>
          <dd className="tnum text-[length:var(--text-lg)] font-semibold leading-none">{String(v ?? "—")}</dd>
        </div>
      ))}
    </dl>
  );
}

/** One tool's result, rendered as the widget that fits it. Defensive: an
 *  unexpected shape falls back to nothing rather than throwing. */
function ToolWidget({ tool, result }: { tool: string; result: Row }) {
  switch (tool) {
    case "get_current_state":
      return (
        <Tiles
          items={[
            ["Open", result.open_incidents],
            ["Unowned", result.unowned],
            ["Overdue", result.overdue],
            ["Corridors elevated", result.corridors_above_typical],
            ["Data age", result.poll_age_minutes != null ? `${result.poll_age_minutes}m` : "—"],
          ]}
        />
      );

    case "data_confidence":
      return (
        <Tiles
          items={[
            ["Coverage", result.coverage_pct != null ? `${result.coverage_pct}%` : "—"],
            ["Observed", `${result.corridors_observed ?? "—"}/${result.corridors_total ?? "—"}`],
            ["Cycles", result.cycles_run],
            ["Data age", result.poll_age_minutes != null ? `${result.poll_age_minutes}m` : "—"],
          ]}
        />
      );

    case "verification_summary":
      return (
        <Tiles
          items={[
            ["Resolved", result.resolved],
            ["Improved while owned", result.showed_improvement_while_owned],
            ["Median clear", result.median_minutes_to_clear != null ? `${result.median_minutes_to_clear}m` : "—"],
            ["Window", result.window_hours != null ? `${result.window_hours}h` : "—"],
          ]}
        />
      );

    case "corridors_above_typical": {
      const rs = rows(result.shown);
      if (!rs.length) return <p className="text-[length:var(--text-sm)] text-ink-3">Nothing above typical.</p>;
      return (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[30rem] text-[length:var(--text-sm)]">
            <thead className="text-[length:var(--text-2xs)] uppercase tracking-[0.05em] text-ink-3">
              <tr>
                <th className="py-1 text-left font-semibold">Corridor</th>
                <th className="py-1 text-left font-semibold">Band</th>
                <th className="py-1 text-right font-semibold">Index</th>
                <th className="py-1 text-right font-semibold">Excess</th>
                <th className="py-1 text-right font-semibold">Held</th>
              </tr>
            </thead>
            <tbody>
              {rs.map((r, i) => (
                <tr key={i} className="border-t border-line">
                  <td className="py-1 pr-2 font-medium">{s(r.name)}</td>
                  <td className="py-1"><BandTag band={s(r.band) as Band} /></td>
                  <td className="tnum py-1 text-right">{n(r.index) != null ? (r.index as number).toFixed(2) : "—"}</td>
                  <td className="tnum py-1 text-right">{n(r.excess_minutes) != null ? `${r.excess_minutes}m` : "—"}</td>
                  <td className="tnum py-1 text-right text-ink-3">{n(r.held_minutes) != null ? `${r.held_minutes}m` : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );
    }

    case "list_incidents": {
      const rs = rows(result.incidents);
      if (!rs.length) return <p className="text-[length:var(--text-sm)] text-ink-3">No incidents.</p>;
      return (
        <ul className="flex flex-col gap-1">
          {rs.map((r, i) => (
            <li key={i} className="flex items-center gap-2 text-[length:var(--text-sm)]">
              <span className="tnum rounded bg-sunken px-1.5 py-0.5 text-[length:var(--text-2xs)] font-semibold">{s(r.priority)}</span>
              <span className="font-medium">{s(r.location)}</span>
              <span className="text-[length:var(--text-2xs)] text-ink-3">{s(r.state).toLowerCase().replace("_", " ")}</span>
              {r.overdue ? <span className="text-[length:var(--text-2xs)] font-semibold" style={{ color: "var(--color-sev)" }}>overdue</span> : null}
            </li>
          ))}
        </ul>
      );
    }

    case "recent_changes": {
      const rs = rows(result.changes);
      if (!rs.length) return <p className="text-[length:var(--text-sm)] text-ink-3">Nothing changed in the window.</p>;
      return (
        <ul className="flex flex-col gap-1">
          {rs.map((r, i) => (
            <li key={i} className="flex items-center gap-2 text-[length:var(--text-sm)]">
              <span className="tnum text-[length:var(--text-2xs)] text-ink-3">{s(r.at).slice(11, 16)}</span>
              <span className="font-medium">{s(r.location)}</span>
              <span className="text-[length:var(--text-2xs)] text-ink-3">{s(r.from).toLowerCase()} → {s(r.to).toLowerCase()}</span>
            </li>
          ))}
        </ul>
      );
    }

    case "junction_reference": {
      const rs = rows(result.junctions).filter((r) => r.safety || r.congestion_pressure === "OVER_CAPACITY");
      const show = rs.length ? rs : rows(result.junctions).slice(0, 6);
      return (
        <ul className="flex flex-col gap-1.5">
          {show.map((r, i) => (
            <li key={i} className="text-[length:var(--text-sm)]">
              <span className="font-medium">{s(r.junction)}</span>
              {r.congestion_pressure ? (
                <span className="ml-2 text-[length:var(--text-2xs)] text-ink-3">{s(r.congestion_pressure).toLowerCase().replace(/_/g, " ")}</span>
              ) : null}
              {r.safety ? <span className="ml-2 text-[length:var(--text-2xs)]" style={{ color: "var(--color-sev)" }}>{s(r.safety)}</span> : null}
            </li>
          ))}
        </ul>
      );
    }

    case "historical_day_shape": {
      const hrs = rows(result.hours);
      if (!hrs.length) return null;
      const max = Math.max(...hrs.map((h) => n(h.index) ?? 0), 1);
      return (
        <div>
          <div className="flex items-end gap-[3px]" style={{ height: 48 }} aria-hidden>
            {hrs.map((h, i) => {
              const idx = n(h.index) ?? 0;
              return (
                <div
                  key={i}
                  title={`${h.hour}:00 — index ${idx}`}
                  style={{
                    flex: 1,
                    height: `${Math.max(6, (idx / max) * 100)}%`,
                    background: h.congested ? "var(--color-high)" : "var(--color-navy)",
                    opacity: h.congested ? 0.95 : 0.35,
                    borderRadius: 1,
                  }}
                />
              );
            })}
          </div>
          <p className="mt-1 text-[length:var(--text-2xs)] text-ink-3">
            Typical {s(result.day_type).toLowerCase()} by hour (0–23), 2019 city-wide. Worst:{" "}
            {rows(result.worst_hours).map((w) => `${w.hour}:00`).join(", ")}.
          </p>
        </div>
      );
    }

    default:
      return null;
  }
}

const TOOL_LABEL: Record<string, string> = {
  get_current_state: "Board now",
  data_confidence: "Data coverage",
  verification_summary: "Deployment effect",
  corridors_above_typical: "Corridors above typical",
  list_incidents: "Incidents",
  recent_changes: "Recent changes",
  junction_reference: "Junctions",
  historical_day_shape: "Typical day (2019)",
};

export function CopilotResult({
  answer,
  onDismiss,
  onFocusIncident,
}: {
  answer: CopilotAnswer;
  onDismiss: () => void;
  onFocusIncident?: (id: string) => void;
}) {
  const sections: [string, string, boolean][] = [
    ["Comparison", answer.comparison, false],
    ["Interpretation", answer.interpretation, false],
    ["Limitation", answer.limitation, true],
    ["Next step", answer.next_step, false],
  ];
  return (
    <div className="mt-2.5 rounded-lg border border-line bg-raised p-3.5">
      <div className="flex items-center justify-between">
        <span className="label">Copilot</span>
        <button type="button" onClick={onDismiss} className="text-[length:var(--text-2xs)] text-ink-3 underline">
          Dismiss
        </button>
      </div>

      {/* Observation leads, as a statement. */}
      <p className="mt-1.5 text-[length:var(--text-md)] font-medium leading-snug text-ink">
        {answer.observation}
      </p>

      {/* The figures behind it, as widgets. */}
      {answer.data?.length > 0 && (
        <div className="mt-3 flex flex-col gap-3">
          {answer.data.map((d, i) => (
            <div key={i} className="rounded-md border border-line bg-surface p-2.5">
              <p className="label mb-1.5">{TOOL_LABEL[d.tool] ?? d.tool}</p>
              <ToolWidget tool={d.tool} result={d.result} />
            </div>
          ))}
        </div>
      )}

      {/* The reasoning, structured. */}
      <dl className="mt-3 grid gap-2.5 sm:grid-cols-2">
        {sections.map(([k, v, accent]) => (
          <div key={k} className={accent ? "sm:col-span-2 rounded-md bg-sunken px-2.5 py-2" : ""}>
            <dt className="label" style={accent ? { color: "var(--color-copper)" } : undefined}>{k}</dt>
            <dd className="text-[length:var(--text-sm)] leading-relaxed text-ink-2">{v}</dd>
          </div>
        ))}
      </dl>

      {answer.focus_incident && onFocusIncident && (
        <button
          type="button"
          onClick={() => onFocusIncident(answer.focus_incident!)}
          className="mt-2.5 rounded border border-line-firm bg-surface px-2.5 py-1.5 text-[length:var(--text-sm)] font-medium text-ink-2 hover:bg-sunken"
        >
          Show the incident
        </button>
      )}

      <p className="mt-2.5 border-t border-line pt-2 text-[length:var(--text-2xs)] text-ink-3">
        {answer.degraded ? "Answered from the board — the model is offline. " : ""}
        From: {answer.tools_called.join(", ")}
      </p>
    </div>
  );
}
