"use client";

import { useEffect, useRef, useState } from "react";
import { BAND_STROKE, LIGHT_MAP, loadMaps } from "@/lib/maps";
import type { Board, Junction, NetworkPayload } from "@/lib/api";

const KEY = process.env.NEXT_PUBLIC_MAPS_API_KEY ?? "";

/** The network, drawn as it is: junctions as named points, corridors as
 *  straight connectors between them, and choke points at their real
 *  coordinates on the road.
 *
 *  Corridors are drawn as plain lines rather than traced along the carriageway
 *  because the corridor is a relationship between two junctions, not a route.
 *  Choke points are the opposite — they come from Google's traffic on the
 *  actual polyline, so those ARE drawn where they are, and they are the only
 *  thing on this map claiming street-level precision.
 */
export function CommandMap({
  board,
  network,
  selected,
  onSelectIncident,
}: {
  board: Board | null;
  network: NetworkPayload | null;
  selected: string | null;
  onSelectIncident: (id: string) => void;
}) {
  const host = useRef<HTMLDivElement>(null);
  const map = useRef<google.maps.Map | null>(null);
  const drawn = useRef<google.maps.MVCObject[]>([]);
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");

  useEffect(() => {
    if (!KEY || !host.current || !network) return;
    let cancelled = false;
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
        // Fit to the junctions that carry corridors, not to every junction.
        // Bagdogra Airport sits 10 km west with no corridor of its own, and
        // including it dragged the bounds wide enough to squeeze the city an
        // officer actually works into the middle third of the map.
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
        setStatus("ready");
      })
      .catch(() => !cancelled && setStatus("error"));
    return () => {
      cancelled = true;
    };
  }, [network]);

  useEffect(() => {
    const gm = typeof window !== "undefined" ? window.google?.maps : undefined;
    if (!gm || !map.current || status !== "ready" || !network || !board) return;

    drawn.current.forEach((o) => (o as google.maps.Polyline).setMap?.(null));
    drawn.current = [];

    const junction = new Map<string, Junction>(network.junctions.map((j) => [j.junction_id, j]));
    const bandOf = new Map(board.corridors.map((c) => [c.corridor_id, c.band]));

    for (const c of network.corridors) {
      const a = junction.get(c.from_junction);
      const b = junction.get(c.to_junction);
      if (!a || !b) continue;
      const band = bandOf.get(c.corridor_id) ?? "UNKNOWN";
      const style = BAND_STROKE[band] ?? BAND_STROKE.UNKNOWN;
      const line = new gm.Polyline({
        path: [
          { lat: a.lat, lng: a.lon },
          { lat: b.lat, lng: b.lon },
        ],
        map: map.current,
        strokeColor: style.colour,
        strokeOpacity: band === "NORMAL" || band === "UNKNOWN" ? 0.4 : 0.9,
        strokeWeight: style.weight,
        zIndex: band === "NORMAL" || band === "UNKNOWN" ? 10 : 40,
      });
      drawn.current.push(line);
    }

    for (const j of network.junctions) {
      const marker = new gm.Marker({
        position: { lat: j.lat, lng: j.lon },
        map: map.current,
        title: j.pin_approximate ? `${j.name} — approximate location` : j.name,
        icon: {
          path: gm.SymbolPath.CIRCLE,
          scale: 4.5,
          fillColor: "#FFFFFF",
          fillOpacity: 1,
          strokeColor: j.pin_approximate ? "#98A2B3" : "#0A1628",
          strokeWeight: j.pin_approximate ? 1.5 : 2,
          // Push the label clear of the dot rather than printing it over the top.
          labelOrigin: new gm.Point(0, 2.6),
        },
        label: {
          text: j.name,
          color: "#4A5568",
          fontSize: "11px",
          fontWeight: "500",
          className: "map-label",
        },
        zIndex: 60,
      });
      drawn.current.push(marker);
    }

    // Choke points last, on top: these are the only marks on this map at
    // street-level precision, and they are what an officer is being sent to.
    for (const incident of board.incidents) {
      const isSelected = selected === incident.incident_id;
      const severe = incident.priority === "P1" || incident.priority === "P2";
      const ring = new gm.Marker({
        position: { lat: incident.lat, lng: incident.lon },
        map: map.current,
        title: `${incident.title} — ${incident.location_name}`,
        icon: {
          path: gm.SymbolPath.CIRCLE,
          scale: isSelected ? 13 : 10,
          fillColor: severe ? "#B32318" : "#B54708",
          fillOpacity: isSelected ? 0.32 : 0.18,
          strokeColor: severe ? "#B32318" : "#B54708",
          strokeWeight: isSelected ? 3 : 2,
        },
        zIndex: 90,
      });
      ring.addListener("click", () => onSelectIncident(incident.incident_id));
      drawn.current.push(ring);
    }
  }, [board, network, selected, status, onSelectIncident]);

  return (
    <div className="relative h-full w-full overflow-hidden rounded-lg border border-line bg-surface">
      <div ref={host} className="h-full w-full" role="application" aria-label="Siliguri traffic network" />

      {status !== "ready" && (
        <div className="absolute inset-0 grid place-items-center bg-raised p-6 text-center">
          <p className="max-w-[46ch] text-[length:var(--text-sm)] leading-relaxed text-ink-2">
            {status === "loading"
              ? "Loading the network map…"
              : "The map needs a Google Maps key. The board, the incident list and every action work without it."}
          </p>
        </div>
      )}

      <div className="pointer-events-none absolute bottom-3 left-3 rounded-md border border-line bg-surface/95 px-3 py-2 shadow-[var(--shadow-card)]">
        <p className="label mb-1.5">Corridor</p>
        <div className="flex flex-col gap-1">
          {(["SEVERE", "HIGH", "ELEVATED", "NORMAL"] as const).map((b) => (
            <span key={b} className="flex items-center gap-2 text-[length:var(--text-2xs)] text-ink-2">
              <span
                aria-hidden
                className="inline-block h-0.5 w-5 rounded"
                style={{ backgroundColor: BAND_STROKE[b].colour, height: BAND_STROKE[b].weight / 2 }}
              />
              {b === "SEVERE" ? "Severe" : b === "HIGH" ? "High" : b === "ELEVATED" ? "Elevated" : "Normal"}
            </span>
          ))}
          <span className="mt-1 flex items-center gap-2 border-t border-line pt-1.5 text-[length:var(--text-2xs)] text-ink-2">
            <span aria-hidden className="inline-block h-2.5 w-2.5 rounded-full border-2" style={{ borderColor: "#B32318", background: "#B3231830" }} />
            Choke point
          </span>
        </div>
      </div>
    </div>
  );
}
