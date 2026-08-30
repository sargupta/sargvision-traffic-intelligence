"use client";

import { useMemo } from "react";
import { RUN_COLOUR, type Board, type NetworkPayload } from "@/lib/api";

/** The network drawn from its own coordinates, with no basemap and no GPU.
 *
 *  Same geometry as the live map — the real carriageway from the route
 *  polyline, coloured by what was measured on each stretch — rendered as plain
 *  SVG. It exists because a control room screen must not go dark when a
 *  third-party map fails to paint, a GPU context is lost, or the room is on a
 *  machine that cannot run WebGL. It also prints, which the map does not.
 *
 *  This is not a placeholder. On a projector or in a briefing pack it is the
 *  better rendering: no basemap clutter, only the roads we actually measure.
 */
export function NetworkPlan({
  board,
  network,
  selected,
  onSelectIncident,
  className,
}: {
  board: Board | null;
  network: NetworkPayload | null;
  selected: string | null;
  onSelectIncident: (id: string) => void;
  className?: string;
}) {
  const model = useMemo(() => {
    if (!board || !network) return null;

    const pts: [number, number][] = [];
    board.corridors.forEach((c) => c.runs.forEach((r) => pts.push(...r.path)));
    network.junctions.forEach((j) => pts.push([j.lon, j.lat]));
    if (pts.length < 2) return null;

    const lons = pts.map((p) => p[0]);
    const lats = pts.map((p) => p[1]);
    const minLon = Math.min(...lons), maxLon = Math.max(...lons);
    const minLat = Math.min(...lats), maxLat = Math.max(...lats);

    // Equirectangular at this latitude keeps the city's shape honest; a raw
    // lat/lon stretch would squash Siliguri east-to-west by about 11%.
    const k = Math.cos((((minLat + maxLat) / 2) * Math.PI) / 180);
    const W = 1000;
    const spanX = (maxLon - minLon) * k;
    const spanY = maxLat - minLat;
    const H = Math.max(360, Math.min(900, (W * spanY) / (spanX || 1)));
    const pad = 34;

    const x = (lon: number) => pad + ((lon - minLon) * k / (spanX || 1)) * (W - pad * 2);
    const y = (lat: number) => H - pad - ((lat - minLat) / (spanY || 1)) * (H - pad * 2);

    return { W, H, x, y };
  }, [board, network]);

  if (!model || !board || !network) {
    return (
      <div className={`grid place-items-center rounded-lg border border-line bg-surface ${className ?? ""}`}>
        <p className="p-6 text-center text-[length:var(--text-sm)] text-ink-2">
          Waiting for the first readings.
        </p>
      </div>
    );
  }

  const { W, H, x, y } = model;
  const connected = new Set<string>();
  network.corridors.forEach((c) => {
    connected.add(c.from_junction);
    connected.add(c.to_junction);
  });

  return (
    <figure className={`overflow-hidden rounded-lg border border-line bg-surface ${className ?? ""}`}>
      <svg viewBox={`0 0 ${W} ${H}`} className="h-full w-full" role="img"
        aria-label="Siliguri road network, coloured by measured traffic speed">
        {/* Roads, drawn worst last so a jam is never hidden under a clear road. */}
        {(["NORMAL", "SLOW", "TRAFFIC_JAM"] as const).map((speed) =>
          board.corridors.flatMap((c) =>
            c.runs
              .filter((r) => r.speed === speed && r.path.length > 1)
              .map((r, i) => (
                <polyline
                  key={`${c.corridor_id}-${speed}-${i}`}
                  points={r.path.map(([lon, lat]) => `${x(lon).toFixed(1)},${y(lat).toFixed(1)}`).join(" ")}
                  fill="none"
                  stroke={`rgb(${RUN_COLOUR[speed].join(",")})`}
                  strokeWidth={speed === "TRAFFIC_JAM" ? 5 : speed === "SLOW" ? 4 : 2}
                  strokeOpacity={speed === "NORMAL" ? 0.5 : 0.95}
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <title>{`${c.name} · ${speed.replace("_", " ").toLowerCase()} · ${Math.round(r.length_m)} m`}</title>
                </polyline>
              )),
          ),
        )}

        {network.junctions
          .filter((j) => connected.has(j.junction_id))
          .map((j) => (
            <g key={j.junction_id}>
              <circle cx={x(j.lon)} cy={y(j.lat)} r={3.5} fill="#fff"
                stroke={j.pin_approximate ? "#98A2B3" : "#0A1628"}
                strokeWidth={j.pin_approximate ? 1.2 : 1.8}
                strokeDasharray={j.pin_approximate ? "2 2" : undefined}>
                <title>{j.pin_approximate ? `${j.name} — approximate location` : j.name}</title>
              </circle>
              <text x={x(j.lon)} y={y(j.lat) - 7} textAnchor="middle"
                style={{ fontSize: 10, fontWeight: 500, paintOrder: "stroke", stroke: "#fff", strokeWidth: 3 }}
                fill="#4A5568">
                {j.name}
              </text>
            </g>
          ))}

        {board.incidents.map((i) => {
          const on = selected === i.incident_id;
          const colour = i.priority === "P1" ? "#B32318" : "#B54708";
          return (
            <g key={i.incident_id} onClick={() => onSelectIncident(i.incident_id)} style={{ cursor: "pointer" }}>
              <circle cx={x(i.lon)} cy={y(i.lat)} r={on ? 15 : 12} fill={colour} fillOpacity={0.16}
                stroke={colour} strokeWidth={on ? 2.5 : 1.8} />
              <circle cx={x(i.lon)} cy={y(i.lat)} r={3} fill={colour} />
              <title>{`${i.title} — ${i.location_name}`}</title>
            </g>
          );
        })}
      </svg>
    </figure>
  );
}
