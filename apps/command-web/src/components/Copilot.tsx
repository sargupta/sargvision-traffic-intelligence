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
      "Is Court More → Venus More unusual for this hour?",
      "Is the Sevoke More → Air View More corridor trending worse?",
    ],
  },
  {
    group: "What can we try",
    questions: [
      "What interventions can we test at the worst junction?",
      "What can we try to fix Sevoke More?",
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

    case "suggest_interventions": {
      const iv = rows(result.interventions);
      if (!iv.length) return <p className="text-[length:var(--text-sm)] text-ink-3">{s(result.error) || "No candidate interventions."}</p>;
      const p = (result.profile ?? {}) as Row;
      return (
        <div className="flex flex-col gap-2">
          <p className="text-[length:var(--text-2xs)] text-ink-3">
            {s(result.junction)}
            {p.live_worst_band ? <> · now <span className="font-medium">{s(p.live_worst_band).toLowerCase()}</span></> : null}
            {n(p.live_worst_index) != null ? <> (index {(p.live_worst_index as number).toFixed(2)})</> : null}
            {p.safety ? <span className="ml-1.5" style={{ color: "var(--color-sev)" }}>· {s(p.safety)}</span> : null}
          </p>
          <ol className="flex flex-col gap-2">
            {iv.map((r, i) => (
              <li key={i} className="rounded-md border border-line bg-surface p-2.5">
                <div className="flex items-baseline gap-1.5">
                  <span className="tnum text-[length:var(--text-2xs)] font-semibold text-ink-3">{i + 1}</span>
                  <p className="text-[length:var(--text-sm)] font-semibold leading-snug text-ink">{s(r.action)}</p>
                </div>
                <dl className="mt-1.5 grid gap-x-4 gap-y-1 sm:grid-cols-2">
                  {([
                    ["Why", r.rationale],
                    ["Where / when", r.where_when],
                    ["We measure", r.measure],
                    ["If it worked", r.expected],
                  ] as [string, unknown][]).map(([k, v]) =>
                    s(v) ? (
                      <div key={k}>
                        <dt className="label">{k}</dt>
                        <dd className="text-[length:var(--text-2xs)] leading-relaxed text-ink-2">{s(v)}</dd>
                      </div>
                    ) : null,
                  )}
                </dl>
                {r.caveat ? (
                  <p className="mt-1.5 rounded bg-sunken px-2 py-1 text-[length:var(--text-2xs)] leading-relaxed text-ink-3">
                    <span className="label" style={{ color: "var(--color-copper)" }}>Risk</span> {s(r.caveat)}
                  </p>
                ) : null}
              </li>
            ))}
          </ol>
          <p className="text-[length:var(--text-2xs)] leading-relaxed text-ink-3">{s(result.basis)}</p>
        </div>
      );
    }

    case "deployment_effects": {
      const ds = rows(result.deployments);
      if (!ds.length) return <p className="text-[length:var(--text-sm)] text-ink-3">No postings logged yet.</p>;
      return (
        <ul className="flex flex-col gap-2">
          {ds.map((d, i) => {
            const bs = n(d.before_speed_kmh);
            const ds2 = n(d.during_speed_kmh);
            const verdict = s(d.verdict);
            const good = verdict.includes("beat this road") || verdict.startsWith("improved");
            const bad = verdict.startsWith("worse");
            return (
              <li key={i} className="rounded-md border border-line bg-surface p-2.5">
                <div className="flex flex-wrap items-baseline justify-between gap-2">
                  <span className="text-[length:var(--text-sm)] font-semibold">{s(d.location)}</span>
                  <span
                    className="text-[length:var(--text-2xs)] font-semibold"
                    style={{ color: good ? "var(--color-ok)" : bad ? "var(--color-sev)" : "var(--color-ink-2)" }}
                  >
                    {verdict}
                  </span>
                </div>
                <p className="mt-0.5 text-[length:var(--text-2xs)] text-ink-3">
                  {s(d.unit)} · {s(d.purpose)}{d.active ? " · on the ground" : ""}
                </p>
                {bs != null && ds2 != null && (
                  <p className="tnum mt-1 text-[length:var(--text-sm)]">
                    {bs.toFixed(0)} → {ds2.toFixed(0)} km/h
                    {s(d.vs_typical) ? <span className="ml-2 text-[length:var(--text-2xs)] text-ink-3">({s(d.vs_typical)})</span> : null}
                  </p>
                )}
              </li>
            );
          })}
        </ul>
      );
    }

    case "corridor_history": {
      if (result.error) return <p className="text-[length:var(--text-sm)] text-ink-3">{s(result.error)}</p>;
      const vb = (result.vs_baseline ?? {}) as Row;
      const tr = (result.trend ?? {}) as Row;
      const verdict = s(vb.verdict);
      const worse = verdict === "worse than typical";
      const better = verdict === "better than typical";
      return (
        <div className="flex flex-col gap-2">
          <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
            <span className="text-[length:var(--text-sm)] font-semibold">{s(result.corridor)}</span>
            {n(result.live_index) != null ? (
              <span className="tnum text-[length:var(--text-sm)]">now {(result.live_index as number).toFixed(2)}</span>
            ) : null}
            {verdict ? (
              <span
                className="rounded px-1.5 py-0.5 text-[length:var(--text-2xs)] font-semibold"
                style={{
                  background: worse ? "var(--color-sev-weak, var(--color-sunken))" : "var(--color-sunken)",
                  color: worse ? "var(--color-sev)" : better ? "var(--color-navy)" : "var(--color-ink-2)",
                }}
              >
                {verdict}
              </span>
            ) : null}
          </div>
          {vb.baseline ? (
            <p className="text-[length:var(--text-2xs)] text-ink-3">
              Typical for {s((vb.when as Row)?.weekday)} {n((vb.when as Row)?.hour)}:00 —{" "}
              p50 {n((vb.baseline as Row).p50)?.toFixed?.(2) ?? "—"}, p85 {n((vb.baseline as Row).p85)?.toFixed?.(2) ?? "—"}{" "}
              ({n((vb.baseline as Row).n)} readings)
            </p>
          ) : null}
          {tr.direction ? (
            <p className="text-[length:var(--text-2xs)] text-ink-3">
              Recent trend: <span className="font-medium">{s(tr.direction)}</span>
              {n(tr.drift) != null ? <> ({(tr.drift as number) > 0 ? "+" : ""}{(tr.drift as number).toFixed(2)} index over {n(tr.days)}d)</> : null}
            </p>
          ) : null}
          {s(vb.caveat) ? <p className="text-[length:var(--text-2xs)] leading-relaxed text-ink-3">{s(vb.caveat)}</p> : null}
        </div>
      );
    }

    case "corridor_forecast": {
      if (result.error) return <p className="text-[length:var(--text-sm)] text-ink-3">{s(result.error)}</p>;
      const steps = rows(result.steps);
      if (!steps.length) return null;
      return (
        <div className="flex flex-col gap-1.5">
          <div className="flex gap-2">
            {steps.map((st, i) => (
              <div key={i} className="flex-1 rounded-md border border-line bg-surface px-2 py-1.5 text-center">
                <div className="label">{s(st.weekday)} {n(st.hour)}:00</div>
                <div className="tnum text-[length:var(--text-lg)] font-semibold leading-none">
                  {n(st.expected) != null ? (st.expected as number).toFixed(2) : "—"}
                </div>
                {Array.isArray(st.band) && n(st.band[1]) != null ? (
                  <div className="tnum text-[length:var(--text-2xs)] text-ink-3">to {(st.band[1] as number).toFixed(2)}</div>
                ) : null}
              </div>
            ))}
          </div>
          <p className="text-[length:var(--text-2xs)] leading-relaxed text-ink-3">{s(result.caveat)}</p>
        </div>
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
  suggest_interventions: "Interventions to test",
  corridor_history: "This corridor's own history",
  corridor_forecast: "Next few hours (baseline)",
  deployment_effects: "Did the postings work",
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

      {/* Where the figures actually come from — a citation, not just the tool. */}
      {answer.sources?.length > 0 && (
        <div className="mt-2.5 border-t border-line pt-2">
          <p className="label mb-1">Sources</p>
          <ul className="flex flex-col gap-1">
            {answer.sources.map((src, i) => (
              <li key={i} className="flex gap-1.5 text-[length:var(--text-2xs)] leading-relaxed text-ink-3">
                <span aria-hidden>·</span>
                <span>{src}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      <p className="mt-2 text-[length:var(--text-2xs)] text-ink-3">
        {answer.degraded ? "Answered from the board — the model is offline. " : ""}
        Computed by: {answer.tools_called.join(", ")}
      </p>
    </div>
  );
}
