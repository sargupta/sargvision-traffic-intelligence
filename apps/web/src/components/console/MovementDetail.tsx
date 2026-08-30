"use client";

import { useEffect, useState } from "react";
import {
  movementContext,
  movementHistory,
  STATUS_COLOUR,
  STATUS_LABEL,
  type MovementLive,
} from "@/lib/live";

interface Reading {
  at: string;
  minutes: number;
  deviation_pct: number | null;
}

/** Current condition against the historical band — the comparison that turns
 *  "traffic is slow" into "this is unusual for here, at this hour". */
function Trace({ readings }: { readings: Reading[] }) {
  const pts = readings.filter((r) => r.deviation_pct !== null).slice(-40);
  if (pts.length < 2) {
    return (
      <p className="mt-3 font-mono text-[length:var(--text-micro)] text-paper-40">
        Not enough readings yet to draw a trend.
      </p>
    );
  }

  const W = 460;
  const H = 110;
  const lo = Math.min(-20, ...pts.map((p) => p.deviation_pct!));
  const hi = Math.max(60, ...pts.map((p) => p.deviation_pct!));
  const x = (i: number) => (i / (pts.length - 1)) * W;
  const y = (v: number) => H - ((v - lo) / (hi - lo)) * H;

  const d = pts.map((p, i) => `${i === 0 ? "M" : "L"}${x(i).toFixed(1)},${y(p.deviation_pct!).toFixed(1)}`).join(" ");

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="mt-4 h-auto w-full" role="img" aria-label="Recent deviation trend">
      {[0, 30, 45, 60].map((t) =>
        t >= lo && t <= hi ? (
          <g key={t}>
            <line
              x1={0}
              x2={W}
              y1={y(t)}
              y2={y(t)}
              stroke={t === 0 ? "var(--color-paper-40)" : "var(--color-rule)"}
              strokeDasharray={t === 0 ? "4 4" : "2 5"}
            />
            <text x={W} y={y(t) - 3} textAnchor="end" className="fill-paper-40" style={{ fontSize: 9 }}>
              {t === 0 ? "expected" : `+${t}%`}
            </text>
          </g>
        ) : null,
      )}
      <path d={d} fill="none" stroke="var(--color-copper)" strokeWidth={1.75} strokeLinejoin="round" />
      <circle cx={x(pts.length - 1)} cy={y(pts[pts.length - 1].deviation_pct!)} r={3.5} fill="var(--color-gold)" />
    </svg>
  );
}

export function MovementDetail({ movement }: { movement: MovementLive }) {
  const [readings, setReadings] = useState<Reading[]>([]);
  const [reliability, setReliability] = useState<{
    buffer_pct: number;
    reliability: string;
    sample_size: number;
  } | null>(null);
  const [baselineHour, setBaselineHour] = useState<{
    normal_low_minutes: number;
    normal_high_minutes: number;
    sample_size: number;
    confidence: string;
  } | null>(null);

  useEffect(() => {
    let live = true;
    movementHistory(movement.movement_id)
      .then((d) => live && setReadings(d.readings))
      .catch(() => live && setReadings([]));
    movementContext(movement.movement_id)
      .then((d) => {
        if (!live) return;
        setReliability(d.reliability);
        const hour = new Date().getHours();
        setBaselineHour(d.hours.find((h) => h.hour === hour) ?? d.hours[0] ?? null);
      })
      .catch(() => live && setReliability(null));
    return () => {
      live = false;
    };
  }, [movement.movement_id]);

  return (
    <div className="p-5">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="font-display text-[length:var(--text-h4)] font-light leading-snug text-paper">
            {movement.name}
          </p>
          <p className="mt-1.5 flex items-center gap-2 font-mono text-[length:var(--text-micro)] uppercase tracking-[0.12em]">
            <span aria-hidden className="h-2 w-2 rounded-full" style={{ backgroundColor: STATUS_COLOUR[movement.status] }} />
            <span style={{ color: STATUS_COLOUR[movement.status] }}>{STATUS_LABEL[movement.status]}</span>
            {movement.persistence_minutes > 0 && (
              <span className="text-paper-40">held {movement.persistence_minutes.toFixed(0)} min</span>
            )}
          </p>
        </div>
      </div>

      <dl className="mt-5 grid grid-cols-3 gap-4">
        {(
          [
            ["Now", movement.current_minutes !== null ? `${movement.current_minutes} min` : "—"],
            ["Expected", movement.expected_minutes !== null ? `${movement.expected_minutes} min` : "—"],
            [
              "Deviation",
              movement.deviation_pct !== null
                ? `${movement.deviation_pct > 0 ? "+" : ""}${movement.deviation_pct}%`
                : "—",
            ],
          ] as const
        ).map(([term, value]) => (
          <div key={term}>
            <dt className="font-mono text-[length:var(--text-micro)] uppercase tracking-[0.1em] text-paper-40">
              {term}
            </dt>
            <dd className="mt-1.5 font-display text-[length:var(--text-h4)] font-light tnum text-paper">
              {value}
            </dd>
          </div>
        ))}
      </dl>

      <Trace readings={readings} />

      <div className="mt-5 space-y-3 border-t border-rule pt-4">
        <p className="font-mono text-[length:var(--text-micro)] uppercase tracking-[0.14em] text-paper-40">
          Historical context · 2019 baseline
        </p>
        {baselineHour ? (
          <p className="text-[length:var(--text-caption)] leading-relaxed text-paper-70">
            Normally {baselineHour.normal_low_minutes}–{baselineHour.normal_high_minutes} minutes
            at this hour, from {baselineHour.sample_size.toLocaleString("en-US")} observations
            ({baselineHour.confidence.toLowerCase()} confidence).
          </p>
        ) : (
          <p className="text-[length:var(--text-caption)] leading-relaxed text-paper-40">
            No published baseline for this movement at this hour — below the 30-observation
            floor. The system can tell you the current travel time and not whether it is
            unusual.
          </p>
        )}
        {reliability && (
          <p className="text-[length:var(--text-caption)] leading-relaxed text-paper-70">
            Buffer {reliability.buffer_pct.toFixed(0)}% —{" "}
            {reliability.reliability.replace(/_/g, " ").toLowerCase()}, across{" "}
            {reliability.sample_size.toLocaleString("en-US")} observations.
          </p>
        )}
      </div>
    </div>
  );
}
