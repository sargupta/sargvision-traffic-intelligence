"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Chrome } from "@/components/Chrome";
import { Approximate, BandTag, Empty } from "@/components/Bits";
import {
  getCityProfile, getCorridor, getCorridorHistory, useBoard,
  type CityProfile, type CorridorDetail, type CorridorHistory,
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

/** The colour a congestion index earns, on the same bands the board uses. */
function bandColour(v: number | null | undefined): string {
  if (v == null) return "var(--color-line)";
  if (v >= 1.75) return "var(--color-sev)";
  if (v >= 1.45) return "var(--color-high, var(--color-sev))";
  if (v >= 1.25) return "var(--color-elev)";
  return "var(--color-ok)";
}

/** This corridor's OWN learned shape of the day: the median line with the p85
 *  band behind it, built live from our readings. The honest counterpart to the
 *  city curve — specific to this corridor, and labelled with how much it rests
 *  on so a thin baseline is never mistaken for a firm one. */
function OwnDayShape({ typical, liveIndex, liveHour }: {
  typical: NonNullable<CorridorHistory["typical_today"]>;
  liveIndex: number | null;
  liveHour: number | null;
}) {
  const W = 900, H = 200;
  const M = { top: 16, right: 16, bottom: 30, left: 42 };
  const PW = W - M.left - M.right, PH = H - M.top - M.bottom;
  const LO = 0.85, HI = 2.0;
  const x = (h: number) => M.left + (h / 23) * PW;
  const y = (v: number) => M.top + PH - ((Math.min(Math.max(v, LO), HI) - LO) / (HI - LO)) * PH;
  const seen = typical.hours.filter((h) => h.n > 0 && h.p50 != null);
  const p50Line = seen.map((h) => `${x(h.hour).toFixed(1)},${y(h.p50!).toFixed(1)}`).join(" L");
  const bandArea = seen.length
    ? `M${seen.map((h) => `${x(h.hour).toFixed(1)},${y(h.p85 ?? h.p50!).toFixed(1)}`).join(" L")} L${seen.map((h) => `${x(h.hour).toFixed(1)},${y(h.p50!).toFixed(1)}`).reverse().join(" L")} Z`
    : "";
  return (
    <div className="overflow-x-auto">
      <svg viewBox={`0 0 ${W} ${H}`} className="h-auto w-full min-w-[38rem]" role="img"
        aria-label="This corridor's own typical index by hour, learned live">
        {[1.0, 1.25, 1.5, 1.75].map((v) => (
          <g key={v}>
            <line x1={M.left} x2={W - M.right} y1={y(v)} y2={y(v)}
              stroke={v === 1.0 ? "var(--color-line-firm)" : "var(--color-line)"}
              strokeDasharray={v === 1.0 ? "4 4" : undefined} />
            <text x={M.left - 8} y={y(v) + 4} textAnchor="end" className="fill-[var(--color-ink-3)]" style={{ fontSize: 11 }}>{v.toFixed(2)}</text>
          </g>
        ))}
        {[0, 6, 12, 18, 23].map((h) => (
          <text key={h} x={x(h)} y={M.top + PH + 20} textAnchor={h === 0 ? "start" : h === 23 ? "end" : "middle"}
            className="fill-[var(--color-ink-3)]" style={{ fontSize: 11 }}>{String(h).padStart(2, "0")}:00</text>
        ))}
        {bandArea && <path d={bandArea} fill="var(--color-navy)" opacity={0.1} />}
        {seen.length > 1 && <path d={`M${p50Line}`} fill="none" stroke="var(--color-navy)" strokeWidth={1.75} />}
        {seen.map((h) => (
          <circle key={h.hour} cx={x(h.hour)} cy={y(h.p50!)} r={2} fill="var(--color-navy)" />
        ))}
        {liveIndex != null && liveHour != null && (
          <circle cx={x(liveHour)} cy={y(liveIndex)} r={4.5} fill={bandColour(liveIndex)}
            stroke="var(--color-surface)" strokeWidth={1.5} />
        )}
      </svg>
    </div>
  );
}

/** The historical timeline the officer asked to see: one bar per day, its height
 *  the day's peak index, coloured on the board's bands. Coarse by design — a
 *  daily rollup, not a reconstructable series. */
function DailyTimeline({ days }: { days: NonNullable<CorridorHistory["timeline"]>["days"] }) {
  const shown = days.slice(-30);
  const max = Math.max(...shown.map((d) => d.peak ?? 0), 1.75);
  return (
    <div>
      <div className="flex items-end gap-[2px]" style={{ height: 60 }} aria-hidden>
        {shown.map((d) => (
          <div key={d.date} title={`${d.date} — peak ${d.peak?.toFixed(2) ?? "—"}, mean ${d.mean?.toFixed(2) ?? "—"}, ${d.hours_congested}h congested`}
            style={{ flex: 1, height: `${Math.max(6, ((d.peak ?? 0) / max) * 100)}%`, background: bandColour(d.peak), borderRadius: 1, opacity: 0.9 }} />
        ))}
      </div>
      <div className="mt-1 flex justify-between text-[length:var(--text-2xs)] text-ink-3">
        <span>{shown[0]?.date ?? ""}</span>
        <span>peak index per day · last {shown.length}d</span>
        <span>{shown[shown.length - 1]?.date ?? ""}</span>
      </div>
    </div>
  );
}

function LearnedHistory({ history }: { history: CorridorHistory }) {
  const vb = history.vs_baseline;
  const worse = vb?.verdict === "worse than typical";
  const better = vb?.verdict === "better than typical";
  const typical = history.typical_today;
  const observations = typical?.observations ?? 0;
  const tr = history.trend;
  const fc = history.forecast;
  return (
    <div className="flex flex-col gap-4">
      {/* Verdict: is now unusual for this corridor, at this hour? */}
      {vb && (
        <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
          {history.live_index != null && (
            <span className="tnum text-[length:var(--text-lg)] font-semibold">{history.live_index.toFixed(2)}</span>
          )}
          <span className="rounded px-2 py-0.5 text-[length:var(--text-sm)] font-semibold"
            style={{ background: "var(--color-sunken)", color: worse ? "var(--color-sev)" : better ? "var(--color-navy)" : "var(--color-ink-2)" }}>
            {vb.verdict}
          </span>
          {vb.baseline && vb.when && (
            <span className="text-[length:var(--text-sm)] text-ink-2">
              typical for {vb.when.weekday} {vb.when.hour}:00 is {vb.baseline.p50?.toFixed(2) ?? "—"} (p85 {vb.baseline.p85?.toFixed(2) ?? "—"}, {vb.baseline.n} readings)
            </span>
          )}
        </div>
      )}

      {/* This corridor's own shape of the day. */}
      {typical && observations > 0 ? (
        <div>
          <OwnDayShape typical={typical} liveIndex={history.live_index} liveHour={vb?.when?.hour ?? null} />
          <p className="mt-1.5 text-[length:var(--text-2xs)] leading-relaxed text-ink-3">
            This corridor&rsquo;s own median (line) and p85 (band) by hour on a {typical.weekday}, learned from{" "}
            {typical.observations} readings. {observations < 50 ? "Still thin — it sharpens as we keep observing. " : ""}
            The dot is now.
          </p>
        </div>
      ) : (
        <p className="text-[length:var(--text-sm)] leading-relaxed text-ink-2">
          The corridor memory has just started for this segment. Its own baseline appears here as the
          system observes it across the week — no raw travel time is stored, only the derived shape.
        </p>
      )}

      {/* The daily historical timeline. */}
      {history.timeline && history.timeline.days.length > 0 && (
        <div>
          <p className="label mb-1.5">Day by day</p>
          <DailyTimeline days={history.timeline.days} />
        </div>
      )}

      {/* Trend and the next-hours baseline expectation. */}
      <div className="grid gap-3 sm:grid-cols-2">
        {tr && tr.direction && (
          <div className="rounded-md border border-line bg-surface p-2.5">
            <p className="label">Recent trend</p>
            <p className="mt-0.5 text-[length:var(--text-sm)]">
              <span className="font-semibold" style={{ color: tr.direction === "worsening" ? "var(--color-sev)" : "var(--color-ink)" }}>{tr.direction}</span>
              {tr.drift != null && <span className="text-ink-2"> · {tr.drift > 0 ? "+" : ""}{tr.drift.toFixed(2)} over {tr.days_observed}d</span>}
            </p>
          </div>
        )}
        {fc && fc.steps.some((s) => s.expected != null) && (
          <div className="rounded-md border border-line bg-surface p-2.5">
            <p className="label">Typically, next hours</p>
            <div className="mt-1 flex gap-3">
              {fc.steps.map((st, i) => (
                <span key={i} className="text-[length:var(--text-sm)]">
                  <span className="text-ink-3">{st.hour}:00</span>{" "}
                  <span className="tnum font-semibold">{st.expected != null ? st.expected.toFixed(2) : "—"}</span>
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
      <p className="text-[length:var(--text-2xs)] leading-relaxed text-ink-3">{history.source}</p>
    </div>
  );
}

function CorridorView() {
  const params = useSearchParams();
  const id = params.get("id");
  const { board, connected } = useBoard();
  const [detail, setDetail] = useState<CorridorDetail | null>(null);
  const [profile, setProfile] = useState<CityProfile | null>(null);
  const [history, setHistory] = useState<CorridorHistory | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getCityProfile().then(setProfile).catch(() => setProfile(null));
  }, []);

  useEffect(() => {
    if (!id) return;
    const load = () => {
      getCorridor(id).then(setDetail).catch((e) => setError(String(e)));
      getCorridorHistory(id).then(setHistory).catch(() => setHistory(null));
    };
    load();
    const t = setInterval(load, 60_000);
    return () => clearInterval(t);
  }, [id]);

  const row = board?.corridors.find((c) => c.corridor_id === id);

  return (
    <>
      <Chrome at={board?.at} connected={connected} cycle={board?.cycle} officer="Duty Officer" pollSeconds={board?.poll_seconds} dataState={board?.data_state} readAgeSeconds={board?.feed?.read_age_seconds} />
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
              <h2 className="text-[length:var(--text-md)] font-semibold">Is this normal for this corridor?</h2>
              <p className="mt-1.5 max-w-[80ch] text-[length:var(--text-sm)] leading-relaxed text-ink-2">
                The system now keeps this corridor&rsquo;s own memory — how its congestion index sits by
                weekday and hour — so it can say whether right now is unusual <em>for this corridor</em>,
                not just for the city. It stores only that derived shape and a coarse day-by-day rollup;
                no raw travel time is kept, exactly as Google&rsquo;s terms require.
              </p>
              <div className="mt-4">
                {history ? (
                  <LearnedHistory history={history} />
                ) : (
                  <p className="text-[length:var(--text-sm)] text-ink-3">Loading this corridor&rsquo;s history…</p>
                )}
              </div>
            </section>

            <section className="card mt-4 p-4">
              <h2 className="text-[length:var(--text-md)] font-semibold">
                The city&rsquo;s shape of a weekday <span className="font-normal text-ink-3">· 2019 study, context only</span>
              </h2>
              <p className="mt-1.5 max-w-[80ch] text-[length:var(--text-sm)] leading-relaxed text-ink-2">
                For comparison, the city&rsquo;s general weekday shape from the 2019 study, with every reading
                this system has taken of this corridor drawn on the same axis. Seven years old and city-wide —
                treat the points as observations, not as a pattern.
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
