"use client";

import { useEffect, useRef, useState } from "react";
import { arcPath, loadMaps, MAP_STYLE } from "@/lib/maps";
import { API, STATUS_COLOUR, type MovementLive, type View } from "@/lib/live";

const KEY = process.env.NEXT_PUBLIC_MAPS_API_KEY ?? "";

interface RegistryEntry {
  movement_id: string;
  name: string;
  origin_lat: number;
  origin_lon: number;
  dest_lat: number;
  dest_lon: number;
  origin_zone: string;
  dest_zone: string;
  origin_name: string;
  dest_name: string;
  priority: string;
}

/** The map is an analytical canvas, not a picture.
 *
 *  Arcs are drawn between zone centroids and bulged off the chord, because the
 *  observations carry an origin and a destination and no route between them —
 *  the same constraint that governs every map in this product. Colour is the
 *  movement's current deviation from its own baseline, so what the eye is
 *  reading is "unusual for here", not "slow".
 *
 *  A `view` from the copilot or a finding dims everything outside its focus,
 *  which is how the interface reorganises itself around an investigation.
 */
export function LiveMap({
  movements,
  view,
  onSelect,
  selected,
}: {
  movements: MovementLive[];
  view: View | null;
  onSelect: (movementId: string) => void;
  selected: string | null;
}) {
  const host = useRef<HTMLDivElement>(null);
  const map = useRef<google.maps.Map | null>(null);
  const arcs = useRef<Map<string, google.maps.Polyline>>(new Map());
  const markers = useRef<google.maps.Marker[]>([]);
  const [registry, setRegistry] = useState<RegistryEntry[]>([]);
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");

  useEffect(() => {
    fetch(`${API}/api/registry`)
      .then((r) => r.json())
      .then((d) => setRegistry(d.movements))
      .catch(() => setStatus("error"));
  }, []);

  useEffect(() => {
    if (!KEY || !host.current || registry.length === 0) return;
    let cancelled = false;

    loadMaps(KEY)
      .then((gm) => {
        if (cancelled || !host.current) return;
        map.current = new gm.Map(host.current, {
          center: { lat: 26.7145, lng: 88.4215 },
          zoom: 12,
          maxZoom: 15,
          styles: MAP_STYLE,
          disableDefaultUI: true,
          zoomControl: true,
          gestureHandling: "greedy",
          backgroundColor: "#0A1628",
          clickableIcons: false,
        });

        const bounds = new gm.LatLngBounds();
        const zones = new Map<string, { lat: number; lng: number; name: string }>();
        for (const r of registry) {
          zones.set(r.origin_zone, { lat: r.origin_lat, lng: r.origin_lon, name: r.origin_name });
          zones.set(r.dest_zone, { lat: r.dest_lat, lng: r.dest_lon, name: r.dest_name });
          bounds.extend({ lat: r.origin_lat, lng: r.origin_lon });
          bounds.extend({ lat: r.dest_lat, lng: r.dest_lon });
        }
        map.current.fitBounds(bounds, { top: 60, right: 60, bottom: 60, left: 60 });

        for (const [id, z] of zones) {
          markers.current.push(
            new gm.Marker({
              position: { lat: z.lat, lng: z.lng },
              map: map.current,
              title: z.name,
              icon: {
                path: gm.SymbolPath.CIRCLE,
                scale: 5,
                fillColor: "#F5F1E8",
                fillOpacity: 0.9,
                strokeColor: "#0A1628",
                strokeWeight: 2,
              },
              label: {
                text: z.name,
                color: "#B4BECD",
                fontSize: "11px",
                fontFamily: "IBM Plex Mono, monospace",
                className: "translate-y-5",
              },
              zIndex: 500,
            }),
          );
          void id;
        }
        setStatus("ready");
      })
      .catch(() => !cancelled && setStatus("error"));

    return () => {
      cancelled = true;
    };
  }, [registry]);

  useEffect(() => {
    const gm = typeof window !== "undefined" ? window.google?.maps : undefined;
    if (!gm || !map.current || status !== "ready") return;

    const byId = new Map(registry.map((r) => [r.movement_id, r]));
    const focus = view?.focus_movements ?? [];
    const focusZones = view?.focus_zones ?? [];
    const dimming = focus.length > 0 || focusZones.length > 0;

    for (const m of movements) {
      const geo = byId.get(m.movement_id);
      if (!geo || geo.origin_zone === geo.dest_zone) continue;

      const inFocus =
        !dimming ||
        focus.includes(m.movement_id) ||
        focusZones.includes(geo.origin_zone) ||
        focusZones.includes(geo.dest_zone);
      const isSelected = selected === m.movement_id;
      // An operations display has to be readable at a glance from across a
      // room. Normal is deliberately quiet and elevated is deliberately loud —
      // rendering them at similar weight makes the map decorative rather than
      // useful, which is the failure mode of most traffic dashboards.
      const calm = m.status === "NORMAL" || m.status === "UNKNOWN";
      const colour = STATUS_COLOUR[m.status];
      const weight = calm ? 1.2 : m.status === "MODERATE" ? 3 : 4.5;
      const baseOpacity = calm ? 0.3 : 0.95;

      let line = arcs.current.get(m.movement_id);
      if (!line) {
        line = new gm.Polyline({
          path: arcPath([geo.origin_lat, geo.origin_lon], [geo.dest_lat, geo.dest_lon], 0.18),
          map: map.current,
          geodesic: false,
        });
        line.addListener("click", () => onSelect(m.movement_id));
        arcs.current.set(m.movement_id, line);
      }

      line.setOptions({
        strokeColor: colour,
        strokeOpacity: inFocus ? (isSelected ? 1 : baseOpacity) : 0.08,
        strokeWeight: isSelected ? weight + 2 : weight,
        zIndex: isSelected ? 300 : inFocus ? 200 : 50,
      });
    }
  }, [movements, view, selected, registry, status, onSelect]);

  return (
    <div className="relative h-full w-full">
      <div ref={host} className="h-full w-full bg-abyss" role="application" aria-label="Siliguri live mobility map" />
      {status !== "ready" && (
        <div className="absolute inset-0 grid place-items-center bg-abyss/90 p-8 text-center">
          <p className="measure-tight text-[length:var(--text-caption)] leading-relaxed text-paper-40">
            {status === "loading"
              ? "Loading the mobility canvas…"
              : "The map needs a Google Maps key. The intelligence feed and copilot work without it."}
          </p>
        </div>
      )}
      {view && (view.focus_movements?.length || view.focus_zones?.length) ? (
        <div className="pointer-events-none absolute left-4 top-4 panel px-3 py-2">
          <p className="font-mono text-[length:var(--text-micro)] uppercase tracking-[0.14em] text-copper-lit">
            Focused view · {view.encode ?? "deviation"}
          </p>
        </div>
      ) : null}
    </div>
  );
}
