"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Section } from "./Section";
import { Reveal } from "./Reveal";
import { findings, num, type Corridor } from "@/lib/data";
import { MAP_STYLE, arcPath, loadMaps, ramp } from "@/lib/maps";

const KEY = process.env.NEXT_PUBLIC_MAPS_API_KEY ?? "";
const { meta, f4_reliability: f4, coverage } = findings;
const GRID_1KM = 0.009;

type Encoding = "buffer" | "speed";

const BAND_STYLE: Record<string, { fill: number; stroke: string; dash: boolean }> = {
  HIGH: { fill: 0.16, stroke: "#7E9B78", dash: false },
  MODERATE: { fill: 0.1, stroke: "#5E7A63", dash: false },
  LOW: { fill: 0.05, stroke: "#3C5273", dash: false },
  INSUFFICIENT: { fill: 0, stroke: "#3C5273", dash: true },
};

export function EvidenceMap() {
  const host = useRef<HTMLDivElement>(null);
  const map = useRef<google.maps.Map | null>(null);
  const arcs = useRef<google.maps.Polyline[]>([]);
  const cells = useRef<google.maps.Rectangle[]>([]);

  const [encoding, setEncoding] = useState<Encoding>("buffer");
  const [showCoverage, setShowCoverage] = useState(true);
  const [selected, setSelected] = useState<Corridor | null>(null);
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");

  const value = useCallback(
    (c: Corridor) =>
      encoding === "buffer"
        ? (c.buffer_pct - f4.best) / (f4.worst - f4.best)
        : 1 - (c.speed - 14.7) / (23.9 - 14.7),
    [encoding],
  );

  useEffect(() => {
    if (!KEY) {
      setStatus("error");
      return;
    }
    let cancelled = false;

    loadMaps(KEY)
      .then((gm) => {
        if (cancelled || !host.current) return;

        map.current = new gm.Map(host.current, {
          center: { lat: meta.centre[0], lng: meta.centre[1] },
          zoom: 12,
          maxZoom: 15,
          styles: MAP_STYLE,
          disableDefaultUI: true,
          zoomControl: true,
          gestureHandling: "cooperative",
          backgroundColor: "#0A1628",
          clickableIcons: false,
        });

        // Frame the observed extent rather than trusting a fixed zoom, so the
        // evidence stays fully visible at any container width — a phone would
        // otherwise crop it.
        map.current.fitBounds(
          new gm.LatLngBounds(
            { lat: meta.bbox[0], lng: meta.bbox[1] },
            { lat: meta.bbox[2], lng: meta.bbox[3] },
          ),
          { top: 28, right: 28, bottom: 28, left: 28 },
        );

        // Evidence coverage, drawn first so arcs sit above it.
        for (const cell of coverage.cells) {
          const s = BAND_STYLE[cell.b];
          const rect = new gm.Rectangle({
            bounds: {
              south: cell.c[0] - GRID_1KM / 2,
              north: cell.c[0] + GRID_1KM / 2,
              west: cell.c[1] - GRID_1KM / 2,
              east: cell.c[1] + GRID_1KM / 2,
            },
            map: map.current,
            fillColor: s.stroke,
            fillOpacity: s.fill,
            strokeColor: s.stroke,
            strokeOpacity: s.dash ? 0.34 : 0.42,
            strokeWeight: 1,
            clickable: false,
            zIndex: 1,
          });
          cells.current.push(rect);
        }

        setStatus("ready");
      })
      .catch(() => {
        if (!cancelled) setStatus("error");
      });

    return () => {
      cancelled = true;
    };
  }, []);

  // Arcs are rebuilt when the encoding changes; the basemap is not touched.
  useEffect(() => {
    const gm = typeof window !== "undefined" ? window.google?.maps : undefined;
    if (!gm || !map.current || status !== "ready") return;

    for (const a of arcs.current) a.setMap(null);
    arcs.current = [];

    for (const c of f4.corridors) {
      const t = value(c);
      const line = new gm.Polyline({
        path: arcPath(c.origin, c.dest),
        map: map.current,
        geodesic: false,
        strokeOpacity: 0,
        zIndex: 10 + Math.round(t * 80),
        icons: [
          {
            icon: {
              path: "M 0,-0.6 0,0.6",
              strokeColor: ramp(t),
              strokeOpacity: 0.55 + t * 0.42,
              strokeWeight: 1.4 + t * 2.4,
              scale: 2.6,
            },
            offset: "0",
            repeat: "9px",
          },
        ],
      });
      line.addListener("click", () => setSelected(c));
      arcs.current.push(line);
    }
  }, [encoding, status, value]);

  useEffect(() => {
    for (const r of cells.current) r.setVisible(showCoverage);
  }, [showCoverage]);

  return (
    <Section
      id="map"
      index="05"
      eyebrow="Where the evidence is"
      claim={
        <>
          We will not colour a road we cannot{" "}
          <span className="italic text-gold">see</span>.
        </>
      }
      standfirst={
        <>
          These observations carry an origin and a destination and nothing in between — no
          route, no road names, no path. So the map draws arcs between areas, bulged
          deliberately away from the street grid, because a red line along Sevoke Road
          would assert something this data cannot establish. Every traffic map you have
          seen implies more precision than it has. This one states exactly what it knows.
        </>
      }
    >
      <Reveal delay={0.1} className="mt-14">
        <div className="flex flex-wrap items-center gap-x-8 gap-y-4 border-y border-rule py-4">
          <div role="group" aria-label="What the arcs encode" className="flex items-center gap-1">
            <span className="mr-3 font-mono text-[length:var(--text-micro)] uppercase tracking-[0.14em] text-paper-40">
              Arcs show
            </span>
            {(
              [
                ["buffer", "Unreliability"],
                ["speed", "Slowness"],
              ] as const
            ).map(([k, label]) => (
              <button
                key={k}
                type="button"
                onClick={() => setEncoding(k)}
                aria-pressed={encoding === k}
                className={`px-3 py-1.5 text-[length:var(--text-caption)] transition-colors ${
                  encoding === k
                    ? "border-b border-copper text-paper"
                    : "border-b border-transparent text-paper-40 hover:text-paper-70"
                }`}
              >
                {label}
              </button>
            ))}
          </div>

          <label className="flex cursor-pointer items-center gap-2.5 text-[length:var(--text-caption)] text-paper-70">
            <input
              type="checkbox"
              checked={showCoverage}
              onChange={(e) => setShowCoverage(e.target.checked)}
              className="h-3.5 w-3.5 accent-[var(--color-copper)]"
            />
            Show where we have evidence
          </label>
        </div>

        <div className="relative mt-6">
          <div
            ref={host}
            role="application"
            aria-label="Map of Siliguri showing observed corridors as arcs between areas, with evidence coverage"
            className="h-[62vh] max-h-[640px] min-h-[430px] w-full border border-rule bg-abyss"
          />

          {status !== "ready" && (
            <div className="absolute inset-0 grid place-items-center bg-abyss p-8 text-center">
              <p className="measure-tight text-[length:var(--text-caption)] leading-relaxed text-paper-40">
                {status === "loading"
                  ? "Loading the basemap…"
                  : "The map needs a Google Maps key to draw. Every finding on this page is independent of it — the numbers above come from the dataset, not from the map."}
              </p>
            </div>
          )}

          {selected && (
            <div className="absolute bottom-4 left-4 right-4 max-w-sm panel p-5 shadow-lift sm:right-auto">
              <div className="flex items-start justify-between gap-4">
                <p className="font-mono text-[length:var(--text-micro)] leading-relaxed tracking-[0.06em] text-copper-lit">
                  {selected.id}
                </p>
                <button
                  type="button"
                  onClick={() => setSelected(null)}
                  aria-label="Close corridor detail"
                  className="-mr-1 -mt-1 shrink-0 px-2 text-paper-40 transition-colors hover:text-paper"
                >
                  ×
                </button>
              </div>
              <dl className="mt-4 grid grid-cols-3 gap-4">
                {(
                  [
                    ["Buffer", `${selected.buffer_pct}%`],
                    ["Median", `${selected.speed} km/h`],
                    ["Sample", num(selected.n)],
                  ] as const
                ).map(([term, v]) => (
                  <div key={term}>
                    <dt className="font-mono text-[length:var(--text-micro)] uppercase tracking-[0.1em] text-paper-40">
                      {term}
                    </dt>
                    <dd className="mt-1.5 font-display text-[length:var(--text-h4)] font-light tnum text-paper">
                      {v}
                    </dd>
                  </div>
                ))}
              </dl>
              <p className="mt-4 border-t border-rule pt-3 text-[length:var(--text-caption)] leading-relaxed text-paper-40">
                A ~2 km grid-cell pair. The arc marks the two areas, not the road between
                them — which this data does not record.
              </p>
            </div>
          )}
        </div>
      </Reveal>

      <div className="mt-16 grid gap-14 md:grid-cols-12 md:items-start">
        <Reveal className="md:col-span-6">
          <p className="font-mono text-[length:var(--text-micro)] uppercase tracking-[0.14em] text-paper-40">
            Evidence coverage · {num(coverage.cell_count)} one-kilometre cells
          </p>
          <ul className="mt-5 space-y-0">
            {(
              [
                ["HIGH", "n ≥ 300", "confident"],
                ["MODERATE", "n 100–299", "usable"],
                ["LOW", "n 30–99", "read with caution"],
                ["INSUFFICIENT", "n < 30", "we cannot see here"],
              ] as const
            ).map(([band, range, gloss]) => {
              const count = coverage.summary[band] ?? 0;
              const s = BAND_STYLE[band];
              return (
                <li
                  key={band}
                  className="flex items-baseline gap-4 border-b border-rule/70 py-3.5"
                >
                  <span
                    aria-hidden
                    className="mt-1 h-3.5 w-3.5 shrink-0 border"
                    style={{
                      borderColor: s.stroke,
                      borderStyle: s.dash ? "dashed" : "solid",
                      backgroundColor: s.fill ? s.stroke : "transparent",
                      opacity: s.fill ? 0.28 + s.fill * 2.6 : 1,
                    }}
                  />
                  <span className="w-28 shrink-0 font-mono text-[length:var(--text-caption)] uppercase tracking-[0.08em] text-paper-70">
                    {band}
                  </span>
                  <span className="w-24 shrink-0 font-mono text-[length:var(--text-caption)] tnum text-paper-40">
                    {range}
                  </span>
                  <span className="flex-1 text-[length:var(--text-caption)] text-paper-40">{gloss}</span>
                  <span className="font-display text-[length:var(--text-h4)] font-light tnum text-paper">
                    {count}
                  </span>
                </li>
              );
            })}
          </ul>
        </Reveal>

        <Reveal delay={0.12} className="md:col-span-6">
          <div className="border-l border-copper/45 pl-7">
            <p className="font-display text-[length:var(--text-h4)] font-light leading-snug text-paper">
              &ldquo;Nothing is wrong here&rdquo; and &ldquo;we cannot see here&rdquo; look
              identical on every other map.
            </p>
            <p className="mt-5 text-[length:var(--text-base)] leading-relaxed text-paper-70">
              {coverage.summary.INSUFFICIENT} of the {coverage.cell_count} cells with any
              observation at all fall below the {meta.min_bin}-observation floor we publish
              at. On this map they are drawn as empty dashed outlines, and they stay empty.
              An officer looking at a quiet area needs to know which kind of quiet it is.
            </p>
            <p className="mt-5 text-[length:var(--text-base)] leading-relaxed text-paper-70">
              That floor costs us coverage. A twelve-observation threshold would let us
              colour far more of this map, and we would not defend a single figure it
              produced.
            </p>
          </div>
        </Reveal>
      </div>
    </Section>
  );
}
