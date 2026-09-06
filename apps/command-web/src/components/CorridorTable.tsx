"use client";

import Link from "next/link";
import { useState } from "react";
import { CONDITION, type Condition, type CorridorRow } from "@/lib/api";
import { BandTag, ConditionTag, TravelTime, Trend, Approximate } from "./Bits";

type SortKey = "condition" | "speed" | "excess" | "name" | "held";

// Worst-first on the ABSOLUTE axis: a fresh jam, then a standing one, then
// early-warning, then clear. This is the order an officer triages in.
const CONDITION_ORDER: Record<Condition, number> = {
  ACUTE: 0, CHRONIC: 1, WATCH: 2, CLEAR: 3, UNKNOWN: 4,
};

const SLOW: Condition[] = ["ACUTE", "CHRONIC"];

/** Every corridor, always — now led by how slow it actually is, not just how
 *  unusual. The "vs usual" band is kept as a second column, because both
 *  questions matter: an officer asked "what about Hill Cart Road" wants the real
 *  speed first and the deviation second. */
export function CorridorTable({
  corridors,
  condition = null,
  onClearCondition,
}: {
  corridors: CorridorRow[];
  /** Set when the officer arrived here by clicking a figure in the summary. */
  condition?: Condition | null;
  onClearCondition?: () => void;
}) {
  const [sort, setSort] = useState<SortKey>("condition");
  const [onlySlow, setOnlySlow] = useState(false);

  const cond = (c: CorridorRow): Condition => c.condition ?? "UNKNOWN";

  const rows = [...corridors]
    .filter((c) => (condition ? cond(c) === condition : true))
    .filter((c) => (onlySlow ? SLOW.includes(cond(c)) : true))
    .sort((a, b) => {
      switch (sort) {
        case "speed":
          return (a.speed_kmh ?? 999) - (b.speed_kmh ?? 999);
        case "excess":
          return (b.excess_minutes ?? -99) - (a.excess_minutes ?? -99);
        case "name":
          return a.name.localeCompare(b.name);
        case "held":
          return b.held_minutes - a.held_minutes;
        default:
          return (
            CONDITION_ORDER[cond(a)] - CONDITION_ORDER[cond(b)] ||
            (a.speed_kmh ?? 999) - (b.speed_kmh ?? 999)
          );
      }
    });

  const head = (key: SortKey, label: string, align = "left") => (
    <th scope="col" className={`px-3 py-2 text-${align} font-semibold`}>
      <button
        type="button"
        onClick={() => setSort(key)}
        className={`inline-flex items-center gap-1 ${sort === key ? "text-ink" : "text-ink-3 hover:text-ink-2"}`}
      >
        {label}
        {sort === key && <span aria-hidden>↓</span>}
      </button>
    </th>
  );

  return (
    <section className="card overflow-hidden">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line px-4 py-3">
        <h2 className="text-[length:var(--text-md)] font-semibold">
          All corridors
          <span className="ml-2 tnum text-[length:var(--text-sm)] font-normal text-ink-3">
            {rows.length} of {corridors.length}
          </span>
        </h2>
        {condition && (
          <button
            type="button"
            onClick={onClearCondition}
            className="flex items-center gap-1.5 rounded-full border border-line-firm bg-sunken px-2.5 py-1 text-[length:var(--text-2xs)] font-medium text-ink-2 hover:bg-surface no-print"
          >
            {CONDITION[condition].label} only
            <span aria-hidden>&times;</span>
            <span className="sr-only">Clear the filter</span>
          </button>
        )}
        <label className="flex cursor-pointer items-center gap-2 text-[length:var(--text-sm)] text-ink-2 no-print">
          <input
            type="checkbox"
            checked={onlySlow}
            onChange={(e) => setOnlySlow(e.target.checked)}
            className="h-3.5 w-3.5 accent-[var(--color-navy)]"
          />
          Only slow
        </label>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full min-w-[58rem] border-collapse text-[length:var(--text-sm)]">
          <thead className="sticky top-0 bg-raised text-[length:var(--text-2xs)] uppercase tracking-[0.05em]">
            <tr className="border-b border-line">
              {head("condition", "Condition")}
              {head("speed", "Speed", "right")}
              {head("name", "Corridor")}
              <th scope="col" className="px-3 py-2 text-left font-semibold text-ink-3">vs usual</th>
              <th scope="col" className="px-3 py-2 text-right font-semibold text-ink-3">Travel time</th>
              {head("held", "Trend", "right")}
              <th scope="col" className="px-3 py-2 text-right font-semibold text-ink-3">Chokes</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((c) => (
              <tr key={c.corridor_id} className="border-b border-line/70 last:border-0 hover:bg-raised">
                <td className="px-3 py-2"><ConditionTag condition={cond(c)} /></td>
                <td className="tnum px-3 py-2 text-right whitespace-nowrap">
                  {c.speed_kmh != null ? (
                    <span
                      className="font-semibold"
                      style={{
                        color: SLOW.includes(cond(c)) ? CONDITION[cond(c)].fg : "var(--color-ink-2)",
                      }}
                    >
                      {c.speed_kmh.toFixed(0)} <span className="font-normal text-ink-3">km/h</span>
                    </span>
                  ) : (
                    <span className="text-ink-3">—</span>
                  )}
                </td>
                <td className="px-3 py-2">
                  <Link href={`/corridor?id=${c.corridor_id}`} className="font-medium underline decoration-line-firm underline-offset-2 hover:decoration-ink">
                    {c.name}
                  </Link>
                  {c.approximate_location && <span className="ml-1.5"><Approximate /></span>}
                </td>
                <td className="px-3 py-2"><BandTag band={c.band} /></td>
                <td className="px-3 py-2 text-right">
                  <TravelTime now={c.duration_minutes} typical={c.typical_minutes} excess={c.excess_minutes} />
                </td>
                <td className="px-3 py-2 text-right"><Trend value={c.trend_per_10min} /></td>
                <td className="tnum px-3 py-2 text-right">
                  {c.choke_points.length > 0 ? (
                    <span className="font-semibold" style={{ color: "var(--color-high)" }}>
                      {c.choke_points.length}
                    </span>
                  ) : (
                    <span className="text-ink-3">—</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <p className="border-t border-line bg-raised px-4 py-2.5 text-[length:var(--text-2xs)] leading-relaxed text-ink-3">
        <strong className="font-semibold text-ink-2">Condition</strong> is the absolute state: <em>acute</em> = slow and
        worse than usual (deploy); <em>chronic</em> = always slow here (structural, not a dispatch); <em>building</em> =
        moving but slower than usual. <strong className="font-semibold text-ink-2">Speed</strong> is measured on the road.
        <strong className="font-semibold text-ink-2"> vs usual</strong> compares against Google&rsquo;s modelled typical
        time and can read faster than typical — it is why a chronically slow road used to show green.
      </p>
    </section>
  );
}
