"use client";

import { useState } from "react";
import {
  ACTION_LABEL, ACTION_PATH, STATE_LABEL, act, minutes,
  type Incident, type Officer,
} from "@/lib/api";
import { Approximate, PriorityTag } from "./Bits";

/** One incident, with everything needed to act on it without leaving the board.
 *
 *  Two actions that are not "fix it" sit alongside the rest on purpose:
 *  standing down (an officer judged no deployment needed) and closing with an
 *  outcome. A system that only lets you record success gets worked around, and
 *  then the record is worth nothing.
 */
export function IncidentCard({
  incident,
  roster,
  officer,
  onChanged,
  selected,
  onSelect,
  compact = false,
}: {
  incident: Incident;
  roster: Officer[];
  officer: string;
  onChanged: (updated: Incident) => void;
  selected?: boolean;
  onSelect?: () => void;
  compact?: boolean;
}) {
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [prompt, setPrompt] = useState<null | "ASSIGNED" | "STOOD_DOWN" | "CLOSED" | "NOTE">(null);
  const [text, setText] = useState("");
  const [assignee, setAssignee] = useState("");

  const evidence = incident.evidence as Record<string, number | string | null>;

  async function run(action: string, body: Record<string, string | undefined>) {
    setBusy(action);
    setError(null);
    try {
      onChanged(await act(incident.incident_id, action, { by: officer, ...body }));
      setPrompt(null);
      setText("");
      setAssignee("");
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(null);
    }
  }

  function trigger(next: string) {
    if (next === "ASSIGNED") return setPrompt("ASSIGNED");
    if (next === "STOOD_DOWN") return setPrompt("STOOD_DOWN");
    if (next === "CLOSED") return setPrompt("CLOSED");
    if (next === "LAPSED") return; // the system does this, not an officer
    run(ACTION_PATH[next], {});
  }

  const onDuty = roster.filter((o) => o.on_duty && o.role !== "DUTY_OFFICER");

  // The action bar sits below the evidence, which on a 768px screen is off the
  // bottom of the card. Whatever the single most useful next step is, it also
  // appears in the header, where the officer's eye already is.
  const HOISTED = ["ACKNOWLEDGED", "ASSIGNED", "ON_SCENE", "RESOLVED"];
  const primary = HOISTED.find((a) => incident.next_actions.includes(a));

  return (
    <article
      id={`incident-${incident.incident_id}`}
      data-band={incident.priority}
      onClick={onSelect}
      className={`card overflow-hidden border-l-[3px] transition-shadow ${
        selected ? "shadow-[var(--shadow-float)]" : ""
      } ${onSelect ? "cursor-pointer" : ""}`}
      style={{
        borderLeftColor:
          incident.priority === "P1" ? "var(--color-sev)"
          : incident.priority === "P2" ? "var(--color-high)"
          : incident.priority === "P3" ? "var(--color-elev)"
          : "var(--color-none)",
      }}
    >
      <div className="p-4">
        <div className="flex flex-wrap items-center gap-2">
          <PriorityTag priority={incident.priority} />
          <span className="rounded bg-sunken px-2 py-0.5 text-[length:var(--text-2xs)] font-medium text-ink-2">
            {STATE_LABEL[incident.state]}
          </span>
          {incident.owner && (
            <span className="text-[length:var(--text-2xs)] text-ink-2">
              with <strong className="font-semibold text-ink">{incident.owner}</strong>
            </span>
          )}
          <span className="tnum ml-auto text-[length:var(--text-2xs)] text-ink-3">
            {minutes(incident.age_minutes)} old
          </span>
          {primary && (
            <button
              type="button"
              disabled={busy !== null}
              onClick={(e) => {
                e.stopPropagation();
                trigger(primary);
              }}
              className="rounded bg-navy px-2.5 py-1 text-[length:var(--text-2xs)] font-semibold text-white transition-colors hover:bg-navy-2 disabled:opacity-40 no-print"
            >
              {ACTION_LABEL[primary]}
            </button>
          )}
        </div>

        <h3 className="mt-2.5 text-[length:var(--text-md)] font-semibold leading-snug">
          {incident.title}
        </h3>

        <p className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-[length:var(--text-sm)] text-ink-2">
          <span className="font-medium text-ink">{incident.location_name}</span>
          {String(evidence.junction_pin) === "ROAD_ONLY" && <Approximate what="junction" />}
        </p>

        <p className="mt-2 text-[length:var(--text-sm)] leading-relaxed text-ink-2">{incident.detail}</p>

        {!compact && (
          <dl className="mt-3 grid grid-cols-2 gap-x-4 gap-y-2 rounded-md bg-sunken px-3 py-2.5 sm:grid-cols-4">
            {(
              [
                ["Affected", evidence.length_m != null ? `${evidence.length_m} m` : "—"],
                ["Of corridor", evidence.share_of_corridor != null ? `${Math.round(Number(evidence.share_of_corridor) * 100)}%` : "—"],
                ["Seen from", `${evidence.corroborating_corridors ?? "—"} corridor${Number(evidence.corroborating_corridors) === 1 ? "" : "s"}`],
                ["Slowest route", evidence.worst_index != null ? `${Number(evidence.worst_index).toFixed(2)}×` : "—"],
              ] as const
            ).map(([k, v]) => (
              <div key={k}>
                <dt className="label">{k}</dt>
                <dd className="tnum mt-0.5 text-[length:var(--text-sm)] font-semibold">{v}</dd>
              </div>
            ))}
          </dl>
        )}

        {incident.notes.length > 0 && (
          <ul className="mt-3 space-y-1.5 border-l-2 border-line pl-3">
            {incident.notes.slice(-3).map((n, i) => (
              <li key={i} className="text-[length:var(--text-sm)] leading-snug">
                <span className="label mr-1.5">{n.kind}</span>
                <span className="text-ink-2">{n.text}</span>
                <span className="ml-1.5 text-[length:var(--text-2xs)] text-ink-3">— {n.author}</span>
              </li>
            ))}
          </ul>
        )}

        <p className="mt-3 text-[length:var(--text-2xs)] leading-relaxed text-ink-3">
          {incident.limitation}
        </p>
      </div>

      {/* ── actions ─────────────────────────────────────────────────────── */}
      <div className="border-t border-line bg-raised px-4 py-3 no-print" onClick={(e) => e.stopPropagation()}>
        {error && (
          <p className="mb-2 rounded bg-sev-tint px-2.5 py-1.5 text-[length:var(--text-sm)]" style={{ color: "var(--color-sev)" }}>
            {error}
          </p>
        )}

        {prompt === "ASSIGNED" && (
          <div className="mb-2 flex flex-wrap items-center gap-2">
            <select
              value={assignee}
              onChange={(e) => setAssignee(e.target.value)}
              className="min-w-[13rem] rounded border border-line-firm bg-surface px-2.5 py-1.5 text-[length:var(--text-sm)]"
            >
              <option value="">Choose an officer…</option>
              {onDuty.map((o) => (
                <option key={o.officer_id} value={o.name}>
                  {o.name} — {o.unit}
                </option>
              ))}
            </select>
            <button
              type="button"
              disabled={!assignee || busy !== null}
              onClick={() => run("assign", { to: assignee, unit: onDuty.find((o) => o.name === assignee)?.unit })}
              className="rounded bg-navy px-3 py-1.5 text-[length:var(--text-sm)] font-medium text-white disabled:opacity-40"
            >
              Assign
            </button>
            <button type="button" onClick={() => setPrompt(null)} className="text-[length:var(--text-sm)] text-ink-2 underline">
              Cancel
            </button>
          </div>
        )}

        {(prompt === "STOOD_DOWN" || prompt === "CLOSED" || prompt === "NOTE") && (
          <div className="mb-2 flex flex-wrap items-center gap-2">
            <input
              autoFocus
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder={
                prompt === "STOOD_DOWN" ? "Why no action is needed"
                : prompt === "CLOSED" ? "What was done and the outcome"
                : "What you found"
              }
              className="min-w-[16rem] flex-1 rounded border border-line-firm bg-surface px-2.5 py-1.5 text-[length:var(--text-sm)]"
            />
            <button
              type="button"
              disabled={!text.trim() || busy !== null}
              onClick={() =>
                run(
                  prompt === "STOOD_DOWN" ? "stand-down" : prompt === "CLOSED" ? "close" : "note",
                  prompt === "NOTE" ? { text, kind: "CAUSE" } : { text },
                )
              }
              className="rounded bg-navy px-3 py-1.5 text-[length:var(--text-sm)] font-medium text-white disabled:opacity-40"
            >
              {prompt === "NOTE" ? "Add" : "Confirm"}
            </button>
            <button type="button" onClick={() => setPrompt(null)} className="text-[length:var(--text-sm)] text-ink-2 underline">
              Cancel
            </button>
          </div>
        )}

        <div className="flex flex-wrap items-center gap-1.5">
          {incident.next_actions
            .filter((a) => a !== "LAPSED")
            .map((a) => {
              const primary = a === "ACKNOWLEDGED" || a === "ASSIGNED" || a === "RESOLVED";
              return (
                <button
                  key={a}
                  type="button"
                  disabled={busy !== null}
                  onClick={() => trigger(a)}
                  className={`rounded px-2.5 py-1.5 text-[length:var(--text-sm)] font-medium transition-colors disabled:opacity-40 ${
                    primary
                      ? "bg-navy text-white hover:bg-navy-2"
                      : "border border-line-firm bg-surface text-ink-2 hover:bg-sunken"
                  }`}
                >
                  {ACTION_LABEL[a] ?? a}
                </button>
              );
            })}
          <button
            type="button"
            onClick={() => setPrompt("NOTE")}
            className="rounded border border-line-firm bg-surface px-2.5 py-1.5 text-[length:var(--text-sm)] font-medium text-ink-2 hover:bg-sunken"
          >
            Record cause
          </button>
        </div>
      </div>
    </article>
  );
}
