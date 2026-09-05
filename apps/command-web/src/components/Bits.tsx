"use client";

import { BAND, PRIORITY, type Band, type Escalation, type Priority } from "@/lib/api";

/** A band, shown three ways at once — colour, word and mark — so it survives a
 *  monochrome print and colour vision deficiency. */
export function BandTag({ band, size = "sm" }: { band: Band; size?: "sm" | "md" }) {
  const b = BAND[band];
  return (
    <span
      data-band={band}
      className={`inline-flex items-center gap-1.5 rounded border-l-[3px] font-semibold ${
        size === "md" ? "px-2.5 py-1 text-[length:var(--text-sm)]" : "px-2 py-0.5 text-[length:var(--text-2xs)]"
      }`}
      style={{ color: b.fg, backgroundColor: b.tint, borderColor: b.fg }}
    >
      <span aria-hidden>{b.mark}</span>
      {b.label}
    </span>
  );
}

export function PriorityTag({ priority }: { priority: Priority }) {
  const p = PRIORITY[priority];
  return (
    <span
      data-band={priority}
      className="inline-flex items-center gap-1.5 rounded border-l-[3px] px-2 py-0.5 text-[length:var(--text-2xs)] font-semibold"
      style={{ color: p.fg, backgroundColor: p.tint, borderColor: p.fg }}
    >
      <span className="tnum">{priority}</span>
      <span className="font-medium opacity-80">{p.label}</span>
    </span>
  );
}

/** The index is a ratio against a modelled typical time, so it is always shown
 *  as the two times it came from. A bare "1.59" means nothing to an officer;
 *  "8 min, usually 5" means everything. */
export function TravelTime({
  now,
  typical,
  excess,
}: {
  now: number | null;
  typical: number | null;
  excess: number | null;
}) {
  if (now === null || typical === null) {
    return <span className="text-ink-3">no reading</span>;
  }
  const late = (excess ?? 0) >= 0.5;
  return (
    <span className="tnum whitespace-nowrap">
      <strong className="font-semibold">{now.toFixed(0)} min</strong>
      <span className="text-ink-3"> · usually {typical.toFixed(0)}</span>
      {late && (
        <span className="ml-1.5 font-semibold" style={{ color: "var(--color-high)" }}>
          +{excess!.toFixed(0)}
        </span>
      )}
    </span>
  );
}

export function Trend({ value }: { value: number | null }) {
  if (value === null) return <span className="text-ink-3">—</span>;
  const rising = value > 0.02;
  const falling = value < -0.02;
  const colour = rising ? "var(--color-sev)" : falling ? "var(--color-ok)" : "var(--color-ink-3)";
  return (
    <span className="tnum inline-flex items-center gap-1 whitespace-nowrap" style={{ color: colour }}>
      <span aria-hidden>{rising ? "↑" : falling ? "↓" : "→"}</span>
      <span className="sr-only">{rising ? "worsening" : falling ? "improving" : "steady"}</span>
      {Math.abs(value) >= 0.005 ? `${value > 0 ? "+" : ""}${(value * 100).toFixed(0)}%` : "steady"}
    </span>
  );
}

/** Absence of evidence, rendered. An officer must be able to tell "nothing is
 *  wrong here" from "we cannot see here". */
export function Approximate({ what = "location" }: { what?: string }) {
  return (
    <span
      className="inline-flex items-center gap-1 rounded bg-none-tint px-1.5 py-0.5 text-[length:var(--text-2xs)] font-medium"
      style={{ color: "var(--color-none)" }}
      title="This point was matched to a road or locality rather than the junction itself"
    >
      <span aria-hidden>◌</span> approximate {what}
    </span>
  );
}

export function Empty({ title, detail }: { title: string; detail: string }) {
  return (
    <div className="rounded-lg border border-dashed border-line-firm bg-raised px-6 py-10 text-center">
      <p className="text-[length:var(--text-md)] font-semibold">{title}</p>
      <p className="mx-auto mt-2 max-w-[52ch] text-[length:var(--text-sm)] leading-relaxed text-ink-2">
        {detail}
      </p>
    </div>
  );
}

/** How long an incident has been waiting for its next human step, and whether
 *  that is now too long. The colour and word both carry it, and an overdue item
 *  reads the same in a monochrome briefing pack. Renders nothing while there is
 *  no clock (on scene, or terminal) or while it is comfortably on time. */
export function EscalationChip({ escalation }: { escalation?: Escalation }) {
  if (!escalation || escalation.clock === null || escalation.level === "ok") return null;

  const need = escalation.clock === "owner" ? "for an officer" : "to reach scene";
  if (escalation.level === "overdue") {
    return (
      <span
        className="inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[length:var(--text-2xs)] font-semibold"
        style={{ color: "var(--color-sev)", backgroundColor: "var(--color-sev-tint)" }}
        title={`Waiting ${escalation.waiting_minutes} min ${need}; limit ${escalation.limit_minutes} min`}
      >
        <span aria-hidden>▲</span>
        {escalation.minutes_over < 1
          ? "Overdue"
          : `Overdue ${Math.round(escalation.minutes_over)}m`}
      </span>
    );
  }
  // due soon
  const left = Math.max(0, (escalation.limit_minutes ?? 0) - escalation.waiting_minutes);
  return (
    <span
      className="inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[length:var(--text-2xs)] font-medium"
      style={{ color: "var(--color-high)", backgroundColor: "var(--color-high-tint)" }}
      title={`${need}`}
    >
      Due {left < 1 ? "now" : `${Math.round(left)}m`}
    </span>
  );
}
