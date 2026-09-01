"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
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

const MIN_ZOOM = 1;
const MAX_ZOOM = 8;

// Roughly the width of a character at the label's base size, in viewBox units.
// Used to reserve space before the browser has measured anything, because
// decluttering has to happen during render.
const CHAR_W = 5.4;
const LINE_H = 12;

interface Placed {
  id: string;
  name: string;
  cx: number;
  cy: number;
  tx: number;
  ty: number;
  anchor: "start" | "end";
  approximate: boolean;
}

interface Box {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
}

const overlaps = (a: Box, b: Box) =>
  a.x1 < b.x2 && a.x2 > b.x1 && a.y1 < b.y2 && a.y2 > b.y1;

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
  const svgRef = useRef<SVGSVGElement | null>(null);
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const drag = useRef<{ x: number; y: number; panX: number; panY: number } | null>(null);
  const [dragging, setDragging] = useState(false);

  const model = useMemo(() => {
    if (!board || !network) return null;

    // Only the junctions that carry corridors. Bagdogra Airport is 10 km west
    // with no corridor of its own, and including it stretched the bounds far
    // enough to squeeze the city an officer works into the right-hand third of
    // the canvas, leaving a third of the primary screen blank.
    const connected = new Set<string>();
    network.corridors.forEach((c) => {
      connected.add(c.from_junction);
      connected.add(c.to_junction);
    });

    const pts: [number, number][] = [];
    board.corridors.forEach((c) => c.runs.forEach((r) => pts.push(...r.path)));
    network.junctions
      .filter((j) => connected.has(j.junction_id))
      .forEach((j) => pts.push([j.lon, j.lat]));
    if (pts.length < 2) return null;

    const lons = pts.map((p) => p[0]);
    const lats = pts.map((p) => p[1]);
    const minLon = Math.min(...lons);
    const maxLon = Math.max(...lons);
    const minLat = Math.min(...lats);
    const maxLat = Math.max(...lats);

    // Equirectangular at this latitude keeps the city's shape honest; a raw
    // lat/lon stretch would squash Siliguri east-to-west by about 11%.
    const k = Math.cos((((minLat + maxLat) / 2) * Math.PI) / 180);
    const W = 1000;
    const spanX = (maxLon - minLon) * k;
    const spanY = maxLat - minLat;
    const H = Math.max(360, Math.min(900, (W * spanY) / (spanX || 1)));
    const pad = 44;
    const padRight = 150;

    const x = (lon: number) =>
      pad + (((lon - minLon) * k) / (spanX || 1)) * (W - pad - padRight);
    const y = (lat: number) => H - pad - ((lat - minLat) / (spanY || 1)) * (H - pad * 2);

    return { W, H, x, y, midLon: (minLon + maxLon) / 2, connected };
  }, [board, network]);

  /** Which labels can be drawn without colliding, at the current zoom.
   *
   *  Six junctions — Mahananda Bridge, Pani Tanki More, Air View More, Sevoke
   *  More, Venus More, Court More — sit inside about 800 m of each other, which
   *  is precisely where incidents happen. Drawing all of them produced an
   *  unreadable stack, and dropping the overlap silently would hide the busiest
   *  part of the city.
   *
   *  So labels are placed greedily in order of what an officer needs first: a
   *  junction carrying an incident, then one whose position we are confident
   *  of, then the rest. Each tries right of its node, then left, then above,
   *  then below, and is skipped only if all four collide. Because the boxes are
   *  measured in screen space, zooming in makes room and more names appear —
   *  which is what the zoom is for.
   */
  const labels = useMemo(() => {
    if (!model || !network || !board) return { placed: [] as Placed[], hidden: 0 };

    const { x, y, midLon, connected } = model;
    const withIncident = new Set(board.incidents.flatMap((i) => i.junctions));

    const candidates = network.junctions
      .filter((j) => connected.has(j.junction_id))
      .map((j) => ({
        j,
        rank:
          (withIncident.has(j.junction_id) ? 0 : 10) +
          (j.pin_approximate ? 2 : 0) +
          (j.name.length > 18 ? 1 : 0),
      }))
      .sort((a, b) => a.rank - b.rank || a.j.name.localeCompare(b.j.name));

    // Label geometry is constant on screen, so in viewBox units it shrinks as
    // the view zooms in. That is what frees space for more names.
    const w = (name: string) => (name.length * CHAR_W) / zoom;
    const h = LINE_H / zoom;
    const gap = 7 / zoom;
    const nodeR = 4 / zoom;

    const taken: Box[] = [];
    const placed: Placed[] = [];
    let hidden = 0;

    for (const { j } of candidates) {
      const cx = x(j.lon);
      const cy = y(j.lat);
      const width = w(j.name);

      // Reserve the node itself so a label never sits on another junction.
      taken.push({ x1: cx - nodeR, y1: cy - nodeR, x2: cx + nodeR, y2: cy + nodeR });

      const preferRight = j.lon <= midLon;
      const options: { tx: number; ty: number; anchor: "start" | "end"; box: Box }[] = [
        {
          tx: cx + gap,
          ty: cy + h * 0.33,
          anchor: "start",
          box: { x1: cx + gap, y1: cy - h * 0.6, x2: cx + gap + width, y2: cy + h * 0.5 },
        },
        {
          tx: cx - gap,
          ty: cy + h * 0.33,
          anchor: "end",
          box: { x1: cx - gap - width, y1: cy - h * 0.6, x2: cx - gap, y2: cy + h * 0.5 },
        },
        {
          tx: cx,
          ty: cy - gap,
          anchor: "start",
          box: { x1: cx - width / 2, y1: cy - gap - h, x2: cx + width / 2, y2: cy - gap },
        },
        {
          tx: cx,
          ty: cy + gap + h * 0.75,
          anchor: "start",
          box: { x1: cx - width / 2, y1: cy + gap, x2: cx + width / 2, y2: cy + gap + h },
        },
      ];
      if (!preferRight) options.unshift(options.splice(1, 1)[0]);

      const fits = options.find((o) => !taken.some((t) => overlaps(o.box, t)));
      if (!fits) {
        hidden += 1;
        continue;
      }
      taken.push(fits.box);
      placed.push({
        id: j.junction_id,
        name: j.name,
        cx,
        cy,
        tx: fits.tx,
        ty: fits.ty,
        anchor: fits.anchor,
        approximate: j.pin_approximate,
      });
    }

    return { placed, hidden };
  }, [model, network, board, zoom]);

  const reset = useCallback(() => {
    setZoom(1);
    setPan({ x: 0, y: 0 });
  }, []);

  // Zoom toward the pointer rather than the centre, so an officer can push into
  // the dense middle of the city without chasing it back into view.
  const onWheel = useCallback(
    (e: React.WheelEvent<SVGSVGElement>) => {
      if (!model || !svgRef.current) return;
      e.preventDefault();
      const rect = svgRef.current.getBoundingClientRect();
      const px = ((e.clientX - rect.left) / rect.width) * model.W;
      const py = ((e.clientY - rect.top) / rect.height) * model.H;

      // Both values are computed here and set separately. Calling setPan from
      // inside the setZoom updater looked tidier and was wrong: a state updater
      // must be pure, React runs it twice under StrictMode, and rapid wheel
      // events lost all but one step because of it.
      const next = Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, zoom * (e.deltaY < 0 ? 1.18 : 1 / 1.18)));
      if (next === zoom) return;
      const ratio = next / zoom;
      setZoom(next);
      setPan(
        next === MIN_ZOOM
          ? { x: 0, y: 0 }
          : { x: px - (px - pan.x) * ratio, y: py - (py - pan.y) * ratio },
      );
    },
    [model, zoom, pan],
  );

  const onPointerDown = (e: React.PointerEvent<SVGSVGElement>) => {
    if (zoom === MIN_ZOOM) return;
    (e.target as Element).setPointerCapture?.(e.pointerId);
    drag.current = { x: e.clientX, y: e.clientY, panX: pan.x, panY: pan.y };
    setDragging(true);
  };

  const onPointerMove = (e: React.PointerEvent<SVGSVGElement>) => {
    if (!drag.current || !model || !svgRef.current) return;
    const rect = svgRef.current.getBoundingClientRect();
    const dx = ((e.clientX - drag.current.x) / rect.width) * model.W;
    const dy = ((e.clientY - drag.current.y) / rect.height) * model.H;
    setPan({ x: drag.current.panX + dx, y: drag.current.panY + dy });
  };

  const endDrag = () => {
    drag.current = null;
    setDragging(false);
  };

  // Keyboard is the control room's real input on a bad day.
  useEffect(() => {
    const el = svgRef.current;
    if (!el) return;
    const onKey = (e: KeyboardEvent) => {
      const step = 40;
      if (e.key === "+" || e.key === "=") setZoom((z) => Math.min(MAX_ZOOM, z * 1.25));
      else if (e.key === "-") setZoom((z) => Math.max(MIN_ZOOM, z / 1.25));
      else if (e.key === "0" || e.key === "Escape") reset();
      else if (e.key === "ArrowLeft") setPan((p) => ({ ...p, x: p.x + step }));
      else if (e.key === "ArrowRight") setPan((p) => ({ ...p, x: p.x - step }));
      else if (e.key === "ArrowUp") setPan((p) => ({ ...p, y: p.y + step }));
      else if (e.key === "ArrowDown") setPan((p) => ({ ...p, y: p.y - step }));
      else return;
      e.preventDefault();
    };
    el.addEventListener("keydown", onKey);
    return () => el.removeEventListener("keydown", onKey);
  }, [reset]);

  if (!model || !board || !network) {
    return (
      <div
        className={`grid place-items-center rounded-lg border border-line bg-surface ${className ?? ""}`}
      >
        <p className="p-6 text-center text-[length:var(--text-sm)] text-ink-2">
          Waiting for the first readings.
        </p>
      </div>
    );
  }

  const { W, H, x, y, connected } = model;
  const approximate = network.junctions.filter(
    (j) => connected.has(j.junction_id) && j.pin_approximate,
  ).length;
  const s = zoom; // stroke and radius divisors, so weight stays constant on screen

  return (
    <figure
      className={`relative overflow-hidden rounded-lg border border-line bg-surface ${className ?? ""}`}
    >
      <svg
        ref={svgRef}
        viewBox={`0 0 ${W} ${H}`}
        className="h-full w-full touch-none focus:outline-none"
        style={{ cursor: zoom > 1 ? (dragging ? "grabbing" : "grab") : "default" }}
        role="img"
        tabIndex={0}
        aria-label={
          `Siliguri road network, coloured by measured traffic speed. ` +
          `${labels.placed.length} junctions labelled. ` +
          `Scroll or press plus and minus to zoom, arrow keys to pan, zero to reset.`
        }
        onWheel={onWheel}
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={endDrag}
        onPointerLeave={endDrag}
      >
        <g transform={`translate(${pan.x} ${pan.y}) scale(${zoom})`}>
          {/* Roads, drawn worst last so a jam is never hidden under a clear road. */}
          {(["NORMAL", "SLOW", "TRAFFIC_JAM"] as const).map((speed) =>
            board.corridors.flatMap((c) =>
              c.runs
                .filter((r) => r.speed === speed && r.path.length > 1)
                .map((r, i) => (
                  <polyline
                    key={`${c.corridor_id}-${speed}-${i}`}
                    points={r.path
                      .map(([lon, lat]) => `${x(lon).toFixed(1)},${y(lat).toFixed(1)}`)
                      .join(" ")}
                    fill="none"
                    stroke={`rgb(${RUN_COLOUR[speed].join(",")})`}
                    strokeWidth={
                      (speed === "TRAFFIC_JAM" ? 5.5 : speed === "SLOW" ? 4 : 1.5) / s
                    }
                    strokeOpacity={speed === "NORMAL" ? 0.28 : 0.95}
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
              <circle
                key={j.junction_id}
                cx={x(j.lon)}
                cy={y(j.lat)}
                r={3.5 / s}
                fill="#fff"
                stroke={j.pin_approximate ? "#98A2B3" : "#0A1628"}
                strokeWidth={(j.pin_approximate ? 1.2 : 1.8) / s}
                strokeDasharray={j.pin_approximate ? `${2 / s} ${2 / s}` : undefined}
              >
                <title>{j.pin_approximate ? `${j.name} — approximate location` : j.name}</title>
              </circle>
            ))}

          {labels.placed.map((l) => (
            <text
              key={l.id}
              x={l.tx}
              y={l.ty}
              textAnchor={l.anchor}
              style={{
                fontSize: 10.5 / s,
                fontWeight: 500,
                paintOrder: "stroke",
                stroke: "#fff",
                strokeWidth: 3.5 / s,
              }}
              fill={l.approximate ? "#7A8598" : "#39424F"}
            >
              {l.name}
            </text>
          ))}

          {board.incidents.map((i) => {
            const on = selected === i.incident_id;
            const colour = i.priority === "P1" ? "#B32318" : "#B54708";
            return (
              <g
                key={i.incident_id}
                onClick={() => onSelectIncident(i.incident_id)}
                style={{ cursor: "pointer" }}
              >
                <circle
                  cx={x(i.lon)}
                  cy={y(i.lat)}
                  r={(on ? 15 : 12) / s}
                  fill={colour}
                  fillOpacity={0.16}
                  stroke={colour}
                  strokeWidth={(on ? 2.5 : 1.8) / s}
                />
                <circle cx={x(i.lon)} cy={y(i.lat)} r={3 / s} fill={colour} />
                <title>{`${i.title} — ${i.location_name}`}</title>
              </g>
            );
          })}
        </g>
      </svg>

      {/* Bottom right, clear of the view toggle the board overlays at top right,
          and clear of the legend at bottom left. Zoom state is stated rather
          than implied: an officer who has pushed into one corner must be able
          to see that they have, and get back. */}
      <div className="absolute bottom-3 right-3 flex items-center gap-1 rounded-md border border-line bg-surface/95 p-1 shadow-[var(--shadow-card)] no-print">
        <button
          type="button"
          onClick={() => setZoom((z) => Math.max(MIN_ZOOM, z / 1.4))}
          disabled={zoom <= MIN_ZOOM}
          aria-label="Zoom out"
          className="h-7 w-7 rounded text-[length:var(--text-md)] leading-none text-ink-2 hover:bg-sunken disabled:opacity-30"
        >
          −
        </button>
        <span className="tnum w-10 text-center text-[length:var(--text-2xs)] text-ink-3">
          {zoom.toFixed(1)}×
        </span>
        <button
          type="button"
          onClick={() => setZoom((z) => Math.min(MAX_ZOOM, z * 1.4))}
          disabled={zoom >= MAX_ZOOM}
          aria-label="Zoom in"
          className="h-7 w-7 rounded text-[length:var(--text-md)] leading-none text-ink-2 hover:bg-sunken disabled:opacity-30"
        >
          +
        </button>
        {zoom > MIN_ZOOM && (
          <button
            type="button"
            onClick={reset}
            className="ml-1 rounded px-2 py-1 text-[length:var(--text-2xs)] text-ink-2 hover:bg-sunken"
          >
            Reset
          </button>
        )}
      </div>

      <div className="pointer-events-none absolute bottom-3 left-3 rounded-md border border-line bg-surface/95 px-3 py-2 shadow-[var(--shadow-card)]">
        <p className="label mb-1.5">Measured on the road</p>
        <div className="flex flex-col gap-1">
          {(
            [
              ["NORMAL", "Moving", 1.5, 0.28],
              ["SLOW", "Slow", 4, 0.95],
              ["TRAFFIC_JAM", "Stopped", 5.5, 0.95],
            ] as const
          ).map(([k, label, weight, opacity]) => (
            <span
              key={k}
              className="flex items-center gap-2 text-[length:var(--text-2xs)] text-ink-2"
            >
              <span
                aria-hidden
                className="inline-block w-5 rounded"
                style={{
                  background: `rgb(${RUN_COLOUR[k].join(",")})`,
                  height: weight,
                  opacity,
                }}
              />
              {label}
            </span>
          ))}
          {approximate > 0 && (
            <span className="mt-1 flex items-center gap-2 border-t border-line pt-1.5 text-[length:var(--text-2xs)] text-ink-2">
              <span
                aria-hidden
                className="inline-block h-2.5 w-2.5 rounded-full border border-dashed"
                style={{ borderColor: "#98A2B3" }}
              />
              {approximate} junction{approximate === 1 ? "" : "s"} located approximately
            </span>
          )}
          {labels.hidden > 0 && (
            <span className="text-[length:var(--text-2xs)] text-ink-3">
              {labels.hidden} name{labels.hidden === 1 ? "" : "s"} hidden — zoom in to read them
            </span>
          )}
        </div>
      </div>
    </figure>
  );
}
