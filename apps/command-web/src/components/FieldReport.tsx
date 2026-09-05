"use client";

import { useEffect, useMemo, useState } from "react";
import {
  ActionError,
  getNetwork,
  raiseFieldReport,
  type Incident,
  type Junction,
  type Priority,
} from "@/lib/api";

/** What a guard can report from the junction — the other half of the field job.
 *  Big targets, preset causes, one screen. The cause list matches the on-scene
 *  taxonomy so a report and a resolution speak the same vocabulary. */
const CAUSES = [
  "Accident",
  "Vehicle breakdown",
  "Signal not working",
  "Waterlogging",
  "Encroachment / parking",
  "Procession or event",
  "Road works",
  "Heavy volume",
] as const;

const BIG = "min-h-[44px] rounded-lg px-4 py-3 text-[length:var(--text-md)] font-semibold";

export function FieldReport({
  me,
  onRaised,
  onClose,
}: {
  me: string;
  onRaised: (incident: Incident) => void;
  onClose: () => void;
}) {
  const [junctions, setJunctions] = useState<Junction[]>([]);
  const [junctionId, setJunctionId] = useState("");
  const [cause, setCause] = useState<string>("");
  const [note, setNote] = useState("");
  const [urgent, setUrgent] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [needsToken, setNeedsToken] = useState(false);

  useEffect(() => {
    getNetwork()
      .then((n) => setJunctions([...n.junctions].sort((a, b) => a.name.localeCompare(b.name))))
      .catch(() => setJunctions([]));
  }, []);

  const canSubmit = useMemo(() => junctionId && cause && !busy, [junctionId, cause, busy]);

  async function submit() {
    if (!canSubmit) return;
    setBusy(true);
    setError(null);
    try {
      // An accident defaults to P1; everything else the officer chose to flag
      // urgent, else P2. A breakdown blocking a lane matters, but an accident
      // is the one that must jump the queue by default.
      const priority: Priority = cause === "Accident" || urgent ? "P1" : "P2";
      const inc = await raiseFieldReport({
        by: me,
        junction_id: junctionId,
        cause,
        note: note.trim() || undefined,
        priority,
      });
      onRaised(inc);
    } catch (e) {
      if (e instanceof ActionError) {
        setError(e.human);
        setNeedsToken(e.status === 401 || e.status === 503);
      } else {
        setError(e instanceof Error ? e.message : String(e));
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="rounded-lg border border-line-firm bg-surface p-3.5">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-[length:var(--text-md)] font-semibold">Report a problem</h2>
        <button type="button" onClick={onClose} className="text-[length:var(--text-sm)] text-ink-2 underline">
          Cancel
        </button>
      </div>

      {error && (
        <p className="mb-3 rounded-lg bg-sev-tint px-3 py-2.5 text-[length:var(--text-sm)]" style={{ color: "var(--color-sev)" }}>
          {error}
          {needsToken && " Unlock recording on this phone first (from the board)."}
        </p>
      )}

      <label className="label mb-1.5 block" htmlFor="fr-junction">Where</label>
      <select
        id="fr-junction"
        value={junctionId}
        onChange={(e) => setJunctionId(e.target.value)}
        className={`${BIG} mb-3 w-full border border-line-firm bg-surface`}
      >
        <option value="">Choose the junction…</option>
        {junctions.map((j) => (
          <option key={j.junction_id} value={j.junction_id}>{j.name}</option>
        ))}
      </select>

      <p className="label mb-1.5">What</p>
      <div className="mb-3 grid grid-cols-2 gap-2">
        {CAUSES.map((c) => (
          <button
            key={c}
            type="button"
            onClick={() => setCause(c)}
            aria-pressed={cause === c}
            className={`min-h-[44px] rounded-lg border px-3 py-2 text-left text-[length:var(--text-sm)] font-medium ${
              cause === c ? "border-navy bg-navy text-white" : "border-line-firm bg-surface"
            }`}
          >
            {c}
          </button>
        ))}
      </div>

      <label className="label mb-1.5 block" htmlFor="fr-note">Anything to add (optional)</label>
      <input
        id="fr-note"
        value={note}
        onChange={(e) => setNote(e.target.value)}
        placeholder="e.g. blocking both lanes"
        className={`${BIG} mb-3 w-full border border-line-firm bg-surface`}
      />

      {cause !== "Accident" && (
        <label className="mb-3 flex cursor-pointer items-center gap-2 text-[length:var(--text-sm)]">
          <input type="checkbox" checked={urgent} onChange={(e) => setUrgent(e.target.checked)} className="h-4 w-4 accent-[var(--color-navy)]" />
          Mark urgent (act now)
        </label>
      )}
      {cause === "Accident" && (
        <p className="mb-3 text-[length:var(--text-2xs)]" style={{ color: "var(--color-sev)" }}>
          An accident is raised as act-now.
        </p>
      )}

      <button
        type="button"
        disabled={!canSubmit}
        onClick={submit}
        className={`${BIG} w-full bg-navy text-white disabled:opacity-40`}
      >
        {busy ? "Reporting…" : "Report — I'm on scene"}
      </button>
    </section>
  );
}
