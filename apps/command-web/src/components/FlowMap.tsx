"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { GoogleMapsOverlay } from "@deck.gl/google-maps";
import { PathLayer, ScatterplotLayer } from "@deck.gl/layers";
import { TripsLayer } from "@deck.gl/geo-layers";
import { LIGHT_MAP, loadMaps } from "@/lib/maps";
import { RUN_COLOUR, type Board, type NetworkPayload } from "@/lib/api";

const KEY = process.env.NEXT_PUBLIC_MAPS_API_KEY ?? "";

/** The network as it actually is.
 *
 *  Every line here is the carriageway Google routed over, decoded from the
 *  response polyline and split at each change of traffic classification. There
 *  are no straight lines between dots on this map — those described a
 *  relationship, and what an officer needs is the road.
 *
 *  The animation is not decoration. Trails move along each stretch at a rate
 *  proportional to the speed measured on it, so a jam reads as stalled traffic
 *  before anyone has looked at a number. Where a corridor has no reading the
 *  road is drawn but nothing moves on it, which is the honest rendering of
 *  "we have not asked recently" — distinct from "clear".
 */

const TRAIL_LENGTH = 260;
const LOOP_MS = 12_000;

interface Trip {
  path: [number, number][];
  timestamps: number[];
  colour: [number, number, number];
}

export function FlowMap({
  board,
  network,
  selected,
  onSelectIncident,
  animate,
  onUnavailable,
}: {
  board: Board | null;
  network: NetworkPayload | null;
  selected: string | null;
  onSelectIncident: (id: string) => void;
  animate: boolean;
  onUnavailable?: () => void;
}) {
  const host = useRef<HTMLDivElement>(null);
  const map = useRef<google.maps.Map | null>(null);
  const overlay = useRef<GoogleMapsOverlay | null>(null);
  const frame = useRef<number>(0);
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
  const [clock, setClock] = useState(0);
  const [hover, setHover] = useState<{ x: number; y: number; text: string } | null>(null);

  // ── the road, split by what was measured on each part of it ──────────────
  const paths = useMemo(() => {
    if (!board) return [];
    return board.corridors.flatMap((c) =>
      c.runs.map((r) => ({
        path: r.path,
        colour: RUN_COLOUR[r.speed],
        // A jam is drawn thicker: it is both worse and, being shorter, easier
        // to miss at this zoom.
        width: r.speed === "TRAFFIC_JAM" ? 9 : r.speed === "SLOW" ? 7 : 4,
        corridor: c.corridor_id,
        label: `${c.name} · ${r.speed.replace("_", " ").toLowerCase()} · ${Math.round(r.length_m)} m`,
      })),
    );
  }, [board]);

  // ── trails, moving at the speed actually measured ────────────────────────
  const trips = useMemo<Trip[]>(() => {
    if (!board) return [];
    const out: Trip[] = [];
    for (const c of board.corridors) {
      if (c.speed_kmh == null || c.runs.length === 0) continue;
      // Normalise so a 40 km/h road crosses the loop once and slower roads
      // proportionally less. The eye reads relative pace, which is the point.
      const pace = Math.max(0.08, Math.min(1, c.speed_kmh / 40));
      for (const r of c.runs) {
        if (r.path.length < 2) continue;
        const span = LOOP_MS / pace;
        const step = span / (r.path.length - 1);
        out.push({
          path: r.path,
          timestamps: r.path.map((_, i) => i * step),
          colour: RUN_COLOUR[r.speed],
        });
      }
    }
    return out;
  }, [board]);

  const loopEnd = useMemo(
    () => Math.max(LOOP_MS, ...trips.map((t) => t.timestamps[t.timestamps.length - 1] ?? 0)),
    [trips],
  );

  useEffect(() => {
    // Honour the operating system before the checkbox. An officer who has
    // asked for reduced motion is sitting in front of this for eight hours.
    const reduced =
      typeof window !== "undefined" &&
      window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
    if (!animate || reduced) return;
    let raf = 0;
    const tick = () => {
      frame.current = (frame.current + 16) % loopEnd;
      setClock(frame.current);
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [animate, loopEnd]);

  useEffect(() => {
    if (!KEY) {
      setStatus("error");
      onUnavailable?.();
      return;
    }
    if (!host.current || !network) return;
    let cancelled = false;

    // The only signal Google gives for a rejected key. Without it the map
    // renders Google's own error dialog inside our frame, under our legend and
    // our "N stretches measured" count, and the app reports itself healthy.
    (window as unknown as Record<string, unknown>).gm_authFailure = () => {
      setStatus("error");
      onUnavailable?.();
    };

    // And a key can be valid while tiles never arrive. If nothing has painted
    // by then, treat the basemap as unavailable rather than showing an empty
    // frame that looks like clear roads.
    const watchdog = window.setTimeout(() => {
      if (!host.current?.querySelector("canvas, img")) {
        setStatus("error");
        onUnavailable?.();
      }
    }, 8000);
    loadMaps(KEY)
      .then((gm) => {
        if (cancelled || !host.current) return;
        map.current = new gm.Map(host.current, {
          center: { lat: 26.7145, lng: 88.4215 },
          zoom: 13,
          styles: LIGHT_MAP,
          disableDefaultUI: true,
          zoomControl: true,
          gestureHandling: "greedy",
          backgroundColor: "#F6F7F9",
          clickableIcons: false,
        });
        const connected = new Set<string>();
        network.corridors.forEach((c) => {
          connected.add(c.from_junction);
          connected.add(c.to_junction);
        });
        const bounds = new gm.LatLngBounds();
        network.junctions
          .filter((j) => connected.has(j.junction_id))
          .forEach((j) => bounds.extend({ lat: j.lat, lng: j.lon }));
        map.current.fitBounds(bounds, { top: 48, right: 48, bottom: 48, left: 48 });

        overlay.current = new GoogleMapsOverlay({
          onHover: (info) => {
            const o = info.object as { label?: string; name?: string } | null;
            setHover(o && info.x != null
              ? { x: info.x, y: info.y, text: o.label ?? o.name ?? "" }
              : null);
          },
        });
        overlay.current.setMap(map.current);
        setStatus("ready");
      })
      .catch(() => {
        if (cancelled) return;
        setStatus("error");
        onUnavailable?.();
      });
    return () => {
      cancelled = true;
      window.clearTimeout(watchdog);
      overlay.current?.finalize();
    };
  }, [network, onUnavailable]);

  useEffect(() => {
    if (!overlay.current || status !== "ready" || !board) return;

    const incidents = board.incidents.map((i) => ({
      position: [i.lon, i.lat] as [number, number],
      id: i.incident_id,
      priority: i.priority,
      name: `${i.title} — ${i.location_name}`,
    }));

    // A slow, shallow pulse. Fast blinking on an operations screen is an
    // accessibility hazard and reads as an emergency even when nothing is.
    const pulse = 1 + 0.16 * Math.sin((clock / loopEnd) * Math.PI * 4);

    overlay.current.setProps({
      layers: [
        new PathLayer({
          id: "carriageway",
          data: paths,
          getPath: (d: (typeof paths)[number]) => d.path,
          getColor: (d: (typeof paths)[number]) => d.colour,
          getWidth: (d: (typeof paths)[number]) => d.width,
          widthUnits: "pixels",
          widthMinPixels: 3,
          capRounded: true,
          jointRounded: true,
          opacity: 0.85,
          pickable: true,
        }),
        animate &&
          clock > 0 &&
          new TripsLayer({
            id: "flow",
            data: trips,
            getPath: (d: Trip) => d.path,
            getTimestamps: (d: Trip) => d.timestamps,
            getColor: (d: Trip) => d.colour,
            currentTime: clock,
            trailLength: TRAIL_LENGTH,
            widthMinPixels: 2.5,
            capRounded: true,
            jointRounded: true,
            opacity: 0.95,
          }),
        new ScatterplotLayer({
          id: "incidents",
          data: incidents,
          getPosition: (d: (typeof incidents)[number]) => d.position,
          getRadius: (d: (typeof incidents)[number]) =>
            (d.priority === "P1" ? 150 : 110) * (selected === d.id ? 1.35 : pulse),
          getFillColor: (d: (typeof incidents)[number]) =>
            d.priority === "P1" ? [179, 35, 24, 70] : [181, 71, 8, 60],
          getLineColor: (d: (typeof incidents)[number]) =>
            d.priority === "P1" ? [179, 35, 24, 255] : [181, 71, 8, 255],
          getLineWidth: 2.5,
          lineWidthUnits: "pixels",
          stroked: true,
          filled: true,
          radiusUnits: "meters",
          radiusMinPixels: 9,
          pickable: true,
          onClick: (info) => {
            const o = info.object as { id?: string } | undefined;
            if (o?.id) onSelectIncident(o.id);
          },
          updateTriggers: { getRadius: [pulse, selected] },
        }),
      ].filter(Boolean) as never[],
    });
  }, [board, paths, trips, clock, selected, status, animate, loopEnd, onSelectIncident]);

  return (
    <div className="relative h-full w-full overflow-hidden rounded-lg border border-line bg-surface">
      <div ref={host} className="h-full w-full" role="application" aria-label="Siliguri live traffic" />

      {status !== "ready" && (
        <div className="absolute inset-0 grid place-items-center bg-raised p-6 text-center">
          <p className="max-w-[46ch] text-[length:var(--text-sm)] leading-relaxed text-ink-2">
            {status === "loading"
              ? "Loading the live network…"
              : "The map needs a Google Maps key. Every figure, incident and action works without it."}
          </p>
        </div>
      )}

      {hover && (
        <div
          className="pointer-events-none absolute z-10 rounded border border-line bg-surface px-2 py-1 text-[length:var(--text-2xs)] shadow-[var(--shadow-card)]"
          style={{ left: hover.x + 12, top: hover.y + 12 }}
        >
          {hover.text}
        </div>
      )}

      {status === "ready" && (
      <div className="pointer-events-none absolute bottom-3 left-3 rounded-md border border-line bg-surface/95 px-3 py-2 shadow-[var(--shadow-card)]">
        <p className="label mb-1.5">Measured on the road</p>
        <div className="flex flex-col gap-1">
          {(
            [
              ["NORMAL", "Moving"],
              ["SLOW", "Slow"],
              ["TRAFFIC_JAM", "Stopped"],
            ] as const
          ).map(([k, label]) => (
            <span key={k} className="flex items-center gap-2 text-[length:var(--text-2xs)] text-ink-2">
              <span
                aria-hidden
                className="inline-block h-1 w-5 rounded"
                style={{ background: `rgb(${RUN_COLOUR[k].join(",")})`, height: k === "NORMAL" ? 2 : 4 }}
              />
              {label}
            </span>
          ))}
        </div>
      </div>
      )}
    </div>
  );
}
