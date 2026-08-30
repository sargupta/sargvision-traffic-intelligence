"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Chrome } from "@/components/Chrome";
import { Approximate, BandTag, Empty } from "@/components/Bits";
import {
  getCityProfile, getCorridor, useBoard,
  type CityProfile, type CorridorDetail,
} from "@/lib/api";

/** The shape of a normal weekday across Siliguri, from the 2019 study, with
 *  today's readings for this corridor drawn on the same axis.
 *
 *  These are deliberately different marks. The city profile is a broad, muted
 *  band — it is seven-year-old, city-wide structure and is only here to say
 *  "this is roughly when the city is busy". Today's readings are points,
 *  because that is what they are: a handful of observations since the system
 *  started, not a pattern. Drawing them as a confident line would claim a
 *  recurrence we have no right to assert.
 */
function DayShape({
  profile,
  readings,
}: {
  profile: CityProfile | null;
  readings: CorridorDetail["readings"];
}) {
  const W = 900;
  const H = 220;
  const M = { top: 18, right: 16, bottom: 34, left: 42 };
  const PW = W - M.left - M.right;
  const PH = H - M.top - M.bottom;
  const LO = 0.85;
  const HI = 1.75;

  const x = (h: number) => M.left + (h / 24) * PW;
  const y = (v: number) => M.top + PH - ((Math.min(Math.max(v, LO), HI) - LO) / (HI - LO)) * PH;

  const band = profile?.hours ?? [];
  const area = band.length
    ? `M${band.map((h) => `${x(h.hour).toFixed(1)},${y(h.index).toFixed(1)}`).join(" L")} L${x(24)},${M.top + PH} L${x(0)},${M.top + PH} Z`
    : "";

  const points = readings
    .map((r) => ({ hour: Number(r.at.slice(11, 13)) + Number(r.at.slice(14, 16)) / 60, index: r.index }))
    .filter((p) => Number.isFinite(p.hour));

  return (
    <figure>
      <div className="overflow-x-auto">
        <svg viewBox={`0 0 ${W} ${H}`} className="h-auto w-full min-w-[38rem]" role="img"
          aria-label="City-wide shape of a normal weekday, with today's readings for this corridor">
          {[1.0, 1.25, 1.5].map((v) => (
            <g key={v}>
              <line x1={M.left} x2={W - M.right} y1={y(v)} y2={y(v)}
                stroke={v === 1.0 ? "var(--color-line-firm)" : "var(--color-line)"}
                strokeDasharray={v === 1.0 ? "4 4" : undefined} />
              <text x={M.left - 8} y={y(v) + 4} textAnchor="end" className="fill-[var(--color-ink-3)]" style={{ fontSize: 11 }}>
                {v.toFixed(2)}
              </text>
            </g>
          ))}
          {[0, 6, 12, 18, 24].map((h) => (
            <text key={h} x={x(h)} y={M.top + PH + 22} textAnchor={h === 0 ? "start" : h === 24 ? "end" : "middle"}
              className="fill-[var(--color-ink-3)]" style={{ fontSize: 11 }}>
              {String(h % 24).padStart(2, "0")}:00
            </text>
          ))}

          {area && <path d={area} fill="var(--color-sunken)" />}
          {band.length > 0 && (
            <path d={`M${band.map((h) => `${x(h.hour).toFixed(1)},${y(h.index).toFixed(1)}`).join(" L")}`}
              fill="none" stroke="var(--color-line-firm)" strokeWidth={1.5} />
          )}

          {points.map((p, i) => (
            <circle key={i} cx={x(p.hour)} cy={y(p.index)} r={3.5}
              fill={p.index >= 1.45 ? "var(--color-sev)" : p.index >= 1.25 ? "var(--color-elev)" : "var(--color-ok)"} />
          ))}
        </svg>
      </div>
      <figcaption className="mt-2 text-[length:var(--text-2xs)] leading-relaxed text-ink-3">
        <span className="inline-block h-2 w-4 align-middle" style={{ background: "var(--color-sunken)", border: "1px solid var(--color-line-firm)" }} />{" "}
        City-wide shape of a normal weekday, 2019 study — context only, and not specific to this
        corridor. <span aria-hidden>●</span> This corridor&rsquo;s readings since the system started.
      </figcaption>
    </figure>
  );
}

function CorridorView() {
  const params = useSearchParams();
  const id = params.get("id");
  const { board, connected } = useBoard();
  const [detail, setDetail] = useState<CorridorDetail | null>(null);
  const [profile, setProfile] = useState<CityProfile | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getCityProfile().then(setProfile).catch(() => setProfile(null));
  }, []);

  useEffect(() => {
    if (!id) return;
    const load = () => getCorridor(id).then(setDetail).catch((e) => setError(String(e)));
    load();
    const t = setInterval(load, 60_000);
    return () => clearInterval(t);
  }, [id]);

  const row = board?.corridors.find((c) => c.corridor_id === id);

  return (
    <>
      <Chrome at={board?.at} connected={connected} cycle={board?.cycle} officer="Duty Officer" />
      <main id="main" className="mx-auto w-full max-w-[74rem] px-4 py-5 lg:px-6">
        <Link href="/" className="text-[length:var(--text-sm)] text-ink-2 underline">← Board</Link>

        {!id && <div className="mt-4"><Empty title="No corridor chosen." detail="Open a corridor from the board." /></div>}
        {error && <p className="mt-4 rounded bg-sev-tint px-3 py-2 text-[length:var(--text-sm)]" style={{ color: "var(--color-sev)" }}>{error}</p>}

        {detail && (
          <>
            <header className="mt-3 flex flex-wrap items-start justify-between gap-4">
              <div>
                <h1 className="text-[length:var(--text-xl)] font-semibold">{detail.name}</h1>
                <p className="mt-1 flex flex-wrap items-center gap-2 text-[length:var(--text-sm)] text-ink-2">
                  {row?.roads || "—"}
                  {detail.approximate_location && <Approximate />}
                </p>
              </div>
              <BandTag band={detail.band} size="md" />
            </header>

            <section className="card mt-4 grid grid-cols-2 gap-4 p-4 sm:grid-cols-4">
              {(
                [
                  ["Now", row?.duration_minutes != null ? `${row.duration_minutes} min` : "—"],
                  ["Usually", row?.typical_minutes != null ? `${row.typical_minutes} min` : "—"],
                  ["Difference", row?.excess_minutes != null ? `${row.excess_minutes > 0 ? "+" : ""}${row.excess_minutes} min` : "—"],
                  ["Held", row ? `${Math.round(row.held_minutes)} min` : "—"],
                ] as const
              ).map(([k, v]) => (
                <div key={k}>
                  <p className="label">{k}</p>
                  <p className="tnum mt-1 text-[length:var(--text-2xl)] font-semibold leading-none">{v}</p>
                </div>
              ))}
            </section>

            <section className="card mt-4 p-4">
              <h2 className="text-[length:var(--text-md)] font-semibold">When does this happen?</h2>
              <p className="mt-1.5 max-w-[80ch] text-[length:var(--text-sm)] leading-relaxed text-ink-2">
                Honestly: we cannot yet say for this corridor. Establishing that a delay recurs every
                Tuesday evening needs months of retained travel times, and Google&rsquo;s terms permit us
                to keep coordinates only. What follows is the city&rsquo;s general shape of a weekday from
                the 2019 study, and every reading this system has taken of this corridor since it
                started. Treat the points as observations, not as a pattern.
              </p>
              <div className="mt-4">
                <DayShape profile={profile} readings={detail.readings} />
              </div>
            </section>

            {row && row.choke_points.length > 0 && (
              <section className="card mt-4 p-4">
                <h2 className="text-[length:var(--text-md)] font-semibold">
                  Where on this corridor <span className="font-normal text-ink-3">· {row.choke_points.length}</span>
                </h2>
                <ul className="mt-3 space-y-2">
                  {row.choke_points.map((c, i) => (
                    <li key={i} className="flex flex-wrap items-center gap-x-4 gap-y-1 rounded border border-line bg-raised px-3 py-2.5">
                      <span className="font-semibold" style={{ color: c.severity === "TRAFFIC_JAM" ? "var(--color-sev)" : "var(--color-elev)" }}>
                        {c.severity === "TRAFFIC_JAM" ? "Stopped" : "Slow"}
                      </span>
                      <span className="tnum text-[length:var(--text-sm)]">{Math.round(c.length_m)} m</span>
                      <span className="tnum text-[length:var(--text-sm)] text-ink-2">
                        {Math.round(c.share_of_corridor * 100)}% of the corridor
                      </span>
                      <a
                        className="ml-auto text-[length:var(--text-sm)] underline"
                        href={`https://www.google.com/maps/search/?api=1&query=${c.midpoint[0]},${c.midpoint[1]}`}
                        target="_blank" rel="noreferrer"
                      >
                        Open location
                      </a>
                    </li>
                  ))}
                </ul>
              </section>
            )}

            <p className="mt-4 text-[length:var(--text-2xs)] leading-relaxed text-ink-3">{detail.note}</p>
          </>
        )}
      </main>
    </>
  );
}

export default function CorridorPage() {
  return (
    <Suspense fallback={null}>
      <CorridorView />
    </Suspense>
  );
}
