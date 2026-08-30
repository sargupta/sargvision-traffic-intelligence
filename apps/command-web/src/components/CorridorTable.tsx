"use client";

import Link from "next/link";
import { useState } from "react";
import type { Band, CorridorRow } from "@/lib/api";
import { BandTag, TravelTime, Trend, Approximate } from "./Bits";

type SortKey = "band" | "excess" | "name" | "held";

const BAND_ORDER: Record<Band, number> = {
  SEVERE: 0, HIGH: 1, ELEVATED: 2, NORMAL: 3, UNKNOWN: 4,
};

/** Every corridor, always. The incident list is what needs action; this is what
 *  is true — an officer asked "what about Hill Cart Road" must be able to
 *  answer without waiting for it to become a problem. */
export function CorridorTable({ corridors }: { corridors: CorridorRow[] }) {
  const [sort, setSort] = useState<SortKey>("band");
  const [onlyProblems, setOnlyProblems] = useState(false);

  const rows = [...corridors]
    .filter((c) => (onlyProblems ? c.band !== "NORMAL" && c.band !== "UNKNOWN" : true))
    .sort((a, b) => {
      switch (sort) {
        case "excess":
          return (b.excess_minutes ?? -99) - (a.excess_minutes ?? -99);
        case "name":
          return a.name.localeCompare(b.name);
        case "held":
          return b.held_minutes - a.held_minutes;
        default:
          return BAND_ORDER[a.band] - BAND_ORDER[b.band] || (b.excess_minutes ?? 0) - (a.excess_minutes ?? 0);
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
        <label className="flex cursor-pointer items-center gap-2 text-[length:var(--text-sm)] text-ink-2 no-print">
          <input
            type="checkbox"
            checked={onlyProblems}
            onChange={(e) => setOnlyProblems(e.target.checked)}
            className="h-3.5 w-3.5 accent-[var(--color-navy)]"
          />
          Only above normal
        </label>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full min-w-[54rem] border-collapse text-[length:var(--text-sm)]">
          <thead className="sticky top-0 bg-raised text-[length:var(--text-2xs)] uppercase tracking-[0.05em]">
            <tr className="border-b border-line">
              {head("band", "Status")}
              {head("name", "Corridor")}
              <th scope="col" className="px-3 py-2 text-left font-semibold text-ink-3">Road</th>
              <th scope="col" className="px-3 py-2 text-right font-semibold text-ink-3">Travel time</th>
              {head("held", "Trend", "right")}
              <th scope="col" className="px-3 py-2 text-right font-semibold text-ink-3">Chokes</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((c) => (
              <tr key={c.corridor_id} className="border-b border-line/70 last:border-0 hover:bg-raised">
                <td className="px-3 py-2"><BandTag band={c.band} /></td>
                <td className="px-3 py-2">
                  <Link href={`/corridor?id=${c.corridor_id}`} className="font-medium underline decoration-line-firm underline-offset-2 hover:decoration-ink">
                    {c.name}
                  </Link>
                  {c.approximate_location && <span className="ml-1.5"><Approximate /></span>}
                </td>
                <td className="max-w-[16rem] truncate px-3 py-2 text-ink-2" title={c.roads}>{c.roads || "—"}</td>
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
        Travel time is now against Google&rsquo;s modelled typical time for the same route. It is not a
        measured free-flow speed and can read faster than typical. Corridors marked approximate have a
        junction pin matched to a road rather than the junction itself.
      </p>
    </section>
  );
}
