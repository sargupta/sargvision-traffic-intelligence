"use client";

import { useState } from "react";
import { ACTION_PATH, act, type Incident, type Recommendation } from "@/lib/api";

const URGENCY: Record<Recommendation["urgency"], { label: string; fg: string; tint: string }> = {
  NOW: { label: "Now", fg: "var(--color-sev)", tint: "var(--color-sev-tint)" },
  THIS_SHIFT: { label: "This shift", fg: "var(--color-high)", tint: "var(--color-high-tint)" },
  ADVISORY: { label: "Advisory", fg: "var(--color-none)", tint: "var(--color-none-tint)" },
};

const KIND: Record<Recommendation["kind"], string> = {
  POST: "Post an officer",
  DIVERT: "Divert",
  ESCALATE: "Escalate",
  WATCH: "Watch",
  STAND_DOWN: "No action",
};

/** Suggestions, with their working shown.
 *
 *  "Because" and "cannot know" are not decoration. A recommendation an officer
 *  cannot audit is one they stop reading by the second week, and the fastest
 *  way to lose a control room is to be confidently wrong once about something
 *  they could not check.
 */
/** Which open incidents a recommendation is actually about.
 *
 *  `Recommendation` carries corridors and junctions, not incident ids, so the
 *  link has to be made here. Matching on either is deliberate: a choke point
 *  sits on a corridor, but the advice that escalates it names the junction.
 */
function related(r: Recommendation, incidents: Incident[]): Incident[] {
  const corridors = new Set(r.corridors);
  const junctions = new Set(r.junctions);
  return incidents.filter(
    (i) =>
      i.is_open &&
      (i.corridors.some((c) => corridors.has(c)) || i.junctions.some((j) => junctions.has(j))),
  );
}

export function Advice({
  items,
  incidents = [],
  officer,
  onSelectIncident,
  onChanged,
}: {
  items: Recommendation[];
  incidents?: Incident[];
  officer?: string;
  onSelectIncident?: (id: string) => void;
  onChanged?: (updated: Incident) => void;
}) {
  // Collapsed by default. Auto-expanding the first card spent ~300px of a
  // 768px screen explaining a recommendation before the officer had seen the
  // queue it refers to.
  const [open, setOpen] = useState<number | null>(null);
  const [busy, setBusy] = useState<number | null>(null);
  const [failed, setFailed] = useState<string | null>(null);

  if (items.length === 0) return null;

  function reveal(id: string) {
    onSelectIncident?.(id);
    document
      .getElementById(`incident-${id}`)
      ?.scrollIntoView({ behavior: "smooth", block: "center" });
  }

  async function acknowledgeAll(index: number, targets: Incident[]) {
    if (!officer) return;
    setBusy(index);
    setFailed(null);
    try {
      for (const t of targets) {
        onChanged?.(await act(t.incident_id, ACTION_PATH.ACKNOWLEDGED, { by: officer }));
      }
    } catch (e) {
      setFailed(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(null);
    }
  }

  return (
    <section aria-labelledby="advice-heading">
      <h2 id="advice-heading" className="mb-2.5 flex items-baseline gap-2 text-[length:var(--text-md)] font-semibold">
        What to do
        <span className="tnum text-[length:var(--text-sm)] font-normal text-ink-3">{items.length}</span>
      </h2>

      <ul className="flex flex-col gap-2.5">
        {items.map((r, i) => {
          const u = URGENCY[r.urgency];
          const expanded = open === i;
          const hits = related(r, incidents);
          const unowned = hits.filter((h) => !h.owner && h.next_actions.includes("ACKNOWLEDGED"));
          return (
            <li
              key={`${r.kind}-${i}`}
              data-band={r.urgency}
              className="card overflow-hidden border-l-[3px]"
              style={{ borderLeftColor: u.fg }}
            >
              <div className="p-3.5">
                <div className="flex flex-wrap items-center gap-2">
                  <span
                    className="rounded px-2 py-0.5 text-[length:var(--text-2xs)] font-semibold"
                    style={{ color: u.fg, backgroundColor: u.tint }}
                  >
                    {u.label}
                  </span>
                  <span className="label">{KIND[r.kind]}</span>
                </div>

                <p className="mt-2 text-[length:var(--text-md)] font-semibold leading-snug">
                  {r.headline}
                </p>
                <p className="mt-1.5 text-[length:var(--text-sm)] leading-relaxed text-ink-2">
                  {r.detail}
                </p>

                {/* ── what the officer can do about it ───────────────────
                     A recommendation with no control is a paragraph. These
                     act on the incidents the advice is derived from, so the
                     officer never has to find them by hand. */}
                <div className="mt-3 flex flex-wrap items-center gap-2 no-print">
                  {unowned.length > 0 && officer && (
                    <button
                      type="button"
                      disabled={busy !== null}
                      onClick={(e) => {
                        e.stopPropagation();
                        acknowledgeAll(i, unowned);
                      }}
                      className="rounded bg-navy px-2.5 py-1.5 text-[length:var(--text-sm)] font-medium text-white transition-colors hover:bg-navy-2 disabled:opacity-40"
                    >
                      {busy === i
                        ? "Working…"
                        : unowned.length === 1
                          ? "Acknowledge it"
                          : `Acknowledge all ${unowned.length}`}
                    </button>
                  )}

                  {hits.length > 0 && (
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        reveal(hits[0].incident_id);
                      }}
                      className="rounded border border-line-firm bg-surface px-2.5 py-1.5 text-[length:var(--text-sm)] font-medium text-ink-2 transition-colors hover:bg-sunken"
                    >
                      {hits.length === 1
                        ? "Open the incident"
                        : `Open ${hits.length} incidents`}
                    </button>
                  )}

                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      setOpen(expanded ? null : i);
                    }}
                    aria-expanded={expanded}
                    className="text-[length:var(--text-sm)] font-medium text-ink-2 underline decoration-line-firm underline-offset-2 hover:text-ink"
                  >
                    {expanded ? "Hide the working" : "Why this?"}
                  </button>
                </div>

                {failed && busy === null && (
                  <p className="mt-2 text-[length:var(--text-sm)]" style={{ color: "var(--color-sev)" }}>
                    {failed}
                  </p>
                )}

                {expanded && (
                  <div className="mt-2.5 border-t border-line pt-2.5">
                    <p className="label">Because</p>
                    <ul className="mt-1.5 space-y-1">
                      {r.because.filter(Boolean).map((b, k) => (
                        <li key={k} className="flex gap-2 text-[length:var(--text-sm)] leading-snug text-ink-2">
                          <span aria-hidden className="text-ink-3">·</span>
                          <span>{b}</span>
                        </li>
                      ))}
                    </ul>
                    <p className="label mt-3">What this cannot tell you</p>
                    <p
                      className="mt-1 text-[length:var(--text-sm)] leading-relaxed"
                      style={{ color: "var(--color-copper)" }}
                    >
                      {r.cannot_know}
                    </p>
                  </div>
                )}
              </div>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
