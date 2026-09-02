"use client";

import { useEffect, useMemo, useState } from "react";
import { Chrome } from "@/components/Chrome";
import { Approximate, BandTag } from "@/components/Bits";
import { getNetwork, useBoard, type Junction, type NetworkPayload } from "@/lib/api";

const PRESSURE: Record<string, { label: string; fg: string; tint: string; mark: string }> = {
  OVER_CAPACITY:   { label: "Over capacity",  fg: "var(--color-sev)",  tint: "var(--color-sev-tint)",  mark: "■" },
  NEAR_CAPACITY:   { label: "Near capacity",  fg: "var(--color-high)", tint: "var(--color-high-tint)", mark: "▲" },
  WITHIN_CAPACITY: { label: "Within capacity", fg: "var(--color-ok)",  tint: "var(--color-ok-tint)",   mark: "–" },
};

/** Junctions with a documented safety signal. From Roy, Mohammadi & Roy,
 *  Geographies 6(2):55 (2026) — accident density and trend, 2021–23.
 *  Held here rather than in the API because it is reference material about the
 *  city, not something the live system measures. */
const SAFETY: Record<string, { note: string; severity: "HIGH" | "WATCH" }> = {
  J_VENUS_MORE: {
    note: "Highest accident density in the city — 14.21/km², and intensifying.",
    severity: "HIGH",
  },
  J_DARJEELING_MORE: {
    note: "Evening accident leader, 16.13% of the evening period's incidents.",
    severity: "HIGH",
  },
  J_CHAMPASARI_MORE: { note: "Secondary accident hotspot.", severity: "WATCH" },
};

export default function NetworkPage() {
  const { board, connected } = useBoard();
  const [network, setNetwork] = useState<NetworkPayload | null>(null);
  const [sort, setSort] = useState<"pressure" | "name" | "safety">("pressure");

  useEffect(() => {
    getNetwork().then(setNetwork).catch(() => setNetwork(null));
  }, []);

  const bandOf = useMemo(
    () => new Map((board?.corridors ?? []).map((c) => [c.corridor_id, c.band])),
    [board],
  );

  const junctions = useMemo(() => {
    const list = [...(network?.junctions ?? [])];
    const rank = { OVER_CAPACITY: 0, NEAR_CAPACITY: 1, WITHIN_CAPACITY: 2 };
    return list.sort((a, b) => {
      if (sort === "name") return a.name.localeCompare(b.name);
      if (sort === "safety") {
        const s = (j: Junction) => (SAFETY[j.junction_id]?.severity === "HIGH" ? 0 : SAFETY[j.junction_id] ? 1 : 2);
        return s(a) - s(b) || a.name.localeCompare(b.name);
      }
      const ap = a.congestion_pressure ? rank[a.congestion_pressure] : 3;
      const bp = b.congestion_pressure ? rank[b.congestion_pressure] : 3;
      return ap - bp || (b.vc_ratio ?? 0) - (a.vc_ratio ?? 0);
    });
  }, [network, sort]);

  return (
    <>
      <Chrome at={board?.at} connected={connected} cycle={board?.cycle} officer="Duty Officer" pollSeconds={board?.poll_seconds} />

      <main id="main" className="mx-auto w-full max-w-[100rem] px-4 py-5 lg:px-6">
        <header className="mb-5">
          <h1 className="text-[length:var(--text-xl)] font-semibold">Network reference</h1>
          <p className="mt-1.5 max-w-[76ch] text-[length:var(--text-sm)] leading-relaxed text-ink-2">
            The junctions and corridors this system watches, with what is known about each from
            survey and study. This is background an officer can rely on between incidents — it does
            not change through the day.
          </p>
        </header>

        {/* The distinction the whole product turns on. */}
        <section className="card mb-5 border-l-[3px] p-4" style={{ borderLeftColor: "var(--color-copper)" }}>
          <h2 className="text-[length:var(--text-md)] font-semibold">
            Congestion and danger are in different places
          </h2>
          <p className="mt-1.5 max-w-[86ch] text-[length:var(--text-sm)] leading-relaxed text-ink-2">
            Venus More carries the highest accident density in Siliguri and one of its lowest
            volume-to-capacity ratios. Jalpai More is the reverse: the most over-capacity junction in
            the 2011 survey, with no accident signal in the 2026 study. A single severity score would
            rank both of them wrongly, so this system never computes one. Congestion is measured
            live; the safety column below is study evidence and is not something we observe.
          </p>
        </section>

        <div className="mb-3 flex flex-wrap items-center gap-2">
          <span className="label">Sort by</span>
          {(
            [
              ["pressure", "Capacity pressure"],
              ["safety", "Safety signal"],
              ["name", "Name"],
            ] as const
          ).map(([k, label]) => (
            <button
              key={k}
              type="button"
              onClick={() => setSort(k)}
              className={`rounded border px-2.5 py-1 text-[length:var(--text-sm)] transition-colors ${
                sort === k
                  ? "border-navy bg-navy text-white"
                  : "border-line-firm bg-surface text-ink-2 hover:bg-sunken"
              }`}
            >
              {label}
            </button>
          ))}
        </div>

        <section className="card overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[62rem] border-collapse text-[length:var(--text-sm)]">
              <thead className="bg-raised text-[length:var(--text-2xs)] uppercase tracking-[0.05em] text-ink-3">
                <tr className="border-b border-line">
                  <th scope="col" className="px-3 py-2 text-left font-semibold">Junction</th>
                  <th scope="col" className="px-3 py-2 text-left font-semibold">Control</th>
                  <th scope="col" className="px-3 py-2 text-right font-semibold">V/C 2011</th>
                  <th scope="col" className="px-3 py-2 text-left font-semibold">Capacity pressure</th>
                  <th scope="col" className="px-3 py-2 text-left font-semibold">Safety signal (study)</th>
                  <th scope="col" className="px-3 py-2 text-right font-semibold">Corridors</th>
                </tr>
              </thead>
              <tbody>
                {junctions.map((j) => {
                  const pressure = j.congestion_pressure ? PRESSURE[j.congestion_pressure] : null;
                  const safety = SAFETY[j.junction_id];
                  const corridors = (network?.corridors ?? []).filter(
                    (c) => c.from_junction === j.junction_id || c.to_junction === j.junction_id,
                  );
                  const live = corridors
                    .map((c) => bandOf.get(c.corridor_id))
                    .filter((b) => b && b !== "NORMAL" && b !== "UNKNOWN");
                  return (
                    <tr key={j.junction_id} className="border-b border-line/70 last:border-0 hover:bg-raised">
                      <td className="px-3 py-2.5">
                        <span className="font-medium">{j.name}</span>
                        {j.pin_approximate && <span className="ml-1.5"><Approximate /></span>}
                      </td>
                      <td className="px-3 py-2.5 text-ink-2">
                        {j.control.replace(/_/g, " ").toLowerCase()}
                      </td>
                      <td className="tnum px-3 py-2.5 text-right">
                        {j.vc_ratio !== null ? j.vc_ratio.toFixed(2) : <span className="text-ink-3">not surveyed</span>}
                      </td>
                      <td className="px-3 py-2.5">
                        {pressure ? (
                          <span
                            data-band={j.congestion_pressure}
                            className="inline-flex items-center gap-1.5 rounded border-l-[3px] px-2 py-0.5 text-[length:var(--text-2xs)] font-semibold"
                            style={{ color: pressure.fg, backgroundColor: pressure.tint, borderColor: pressure.fg }}
                          >
                            <span aria-hidden>{pressure.mark}</span>
                            {pressure.label}
                          </span>
                        ) : (
                          <span className="text-[length:var(--text-2xs)] text-ink-3">no survey</span>
                        )}
                      </td>
                      <td className="max-w-[26rem] px-3 py-2.5">
                        {safety ? (
                          <span
                            className="text-[length:var(--text-sm)] leading-snug"
                            style={{ color: safety.severity === "HIGH" ? "var(--color-sev)" : "var(--color-elev)" }}
                          >
                            {safety.note}
                          </span>
                        ) : (
                          <span className="text-[length:var(--text-2xs)] text-ink-3">
                            not identified in the study
                          </span>
                        )}
                      </td>
                      <td className="px-3 py-2.5 text-right">
                        <span className="tnum">{corridors.length}</span>
                        {live.length > 0 && (
                          <span className="ml-2 inline-block align-middle">
                            <BandTag band={live[0]!} />
                          </span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          <div className="border-t border-line bg-raised px-4 py-3 text-[length:var(--text-2xs)] leading-relaxed text-ink-3">
            <p>
              <strong className="text-ink-2">V/C 2011</strong> is the volume-to-capacity ratio of the
              junction&rsquo;s major arm from the Comprehensive Mobility Plan 2011, published in the
              Siliguri CDP 2041. It describes designed capacity against measured volume fifteen years
              ago and is structural context, not today&rsquo;s traffic.
            </p>
            <p className="mt-1.5">
              <strong className="text-ink-2">Safety signal</strong> is from Roy, Mohammadi &amp; Roy,{" "}
              <em>Geographies</em> 6(2):55 (2026), covering 2021–23. This system does not observe
              accidents and cannot detect one.
            </p>
            <p className="mt-1.5">
              <strong className="text-ink-2">Approximate</strong> means the junction was matched to a
              road or locality rather than to the junction itself. Its marker on the map is
              indicative only.
            </p>
          </div>
        </section>
      </main>
    </>
  );
}
