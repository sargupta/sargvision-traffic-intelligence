"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { Chrome } from "@/components/Chrome";
import { ConditionTag, Empty } from "@/components/Bits";
import { getCoverage, useBoard, type Coverage } from "@/lib/api";

function UnwatchedRow({ c }: { c: Coverage["unwatched_slow"]["corridors"][number] }) {
  return (
    <li className="flex flex-wrap items-center gap-x-3 gap-y-1 rounded-md border border-line bg-surface px-3 py-2">
      <ConditionTag condition={c.condition} />
      <span className="tnum text-[length:var(--text-sm)] font-semibold">
        {c.speed_kmh != null ? `${c.speed_kmh.toFixed(0)} km/h` : "—"}
      </span>
      <Link href={`/corridor?id=${c.corridor_id}`} className="text-[length:var(--text-sm)] font-medium underline decoration-line-firm underline-offset-2 hover:decoration-ink">
        {c.name}
      </Link>
      {c.held_minutes != null && c.held_minutes > 0 ? (
        <span className="text-[length:var(--text-2xs)] text-ink-3">held {Math.round(c.held_minutes)}m</span>
      ) : null}
      <Link
        href="/verify"
        className="ml-auto rounded border border-line-firm bg-surface px-2.5 py-1 text-[length:var(--text-2xs)] font-medium text-ink-2 hover:bg-sunken no-print"
      >
        Post an officer →
      </Link>
    </li>
  );
}

export default function CoveragePage() {
  const { board, connected } = useBoard();
  const [cov, setCov] = useState<Coverage | null>(null);

  const load = useCallback(() => {
    getCoverage().then(setCov).catch(() => setCov(null));
  }, []);
  useEffect(() => {
    load();
    const t = setInterval(load, 60_000);
    return () => clearInterval(t);
  }, [load]);

  const unwatched = cov?.unwatched_slow;

  return (
    <>
      <Chrome
        at={board?.at}
        connected={connected}
        cycle={board?.cycle}
        officer="Duty Officer"
        pollSeconds={board?.poll_seconds}
        dataState={board?.data_state}
        readAgeSeconds={board?.feed?.read_age_seconds}
      />
      <main id="main" className="mx-auto w-full max-w-[68rem] px-4 py-5 lg:px-6">
        <div className="flex items-baseline justify-between">
          <h1 className="text-[length:var(--text-xl)] font-semibold">What nobody&rsquo;s on</h1>
          <Link href="/" className="text-[length:var(--text-sm)] text-ink-2 underline">← Board</Link>
        </div>
        <p className="mt-1 max-w-[74ch] text-[length:var(--text-sm)] leading-relaxed text-ink-2">
          The value isn&rsquo;t mirroring the junctions officers already man — it&rsquo;s the roads
          they don&rsquo;t. Below: the corridors slow right now with no officer posted (the Ghogomali
          pattern), and — because we deliberately don&rsquo;t watch every road — the significant roads
          we don&rsquo;t instrument at all, and why.
        </p>

        {/* Slow now, nobody on it. */}
        <section className="mt-5">
          <h2 className="text-[length:var(--text-md)] font-semibold">
            Slow now, no officer on it
            {unwatched ? (
              <span className="ml-2 text-[length:var(--text-sm)] font-normal text-ink-3">
                · {unwatched.acute} acute · {unwatched.chronic} chronic
              </span>
            ) : null}
          </h2>
          {unwatched && unwatched.count === 0 ? (
            <div className="mt-2">
              <Empty title="Every slow corridor has an officer on it." detail="Nothing is crawling without a posting right now. This is a result, not an empty screen." />
            </div>
          ) : unwatched ? (
            <ul className="mt-2 flex flex-col gap-1.5">
              {unwatched.corridors.map((c) => <UnwatchedRow key={c.corridor_id} c={c} />)}
            </ul>
          ) : (
            <p className="mt-2 text-[length:var(--text-sm)] text-ink-3">Loading…</p>
          )}
          {unwatched ? (
            <p className="mt-2 text-[length:var(--text-2xs)] leading-relaxed text-ink-3">{unwatched.note}</p>
          ) : null}
        </section>

        {/* The coverage boundary. */}
        <section className="mt-7">
          <h2 className="text-[length:var(--text-md)] font-semibold">
            Roads we don&rsquo;t watch at all
            {cov ? (
              <span className="ml-2 text-[length:var(--text-sm)] font-normal text-ink-3">
                · watching {cov.summary.corridors_instrumented} corridors / {cov.summary.junctions_instrumented} junctions
              </span>
            ) : null}
          </h2>
          {cov ? (
            <p className="mt-1 max-w-[74ch] text-[length:var(--text-2xs)] leading-relaxed text-ink-3">{cov.summary.note}</p>
          ) : null}
          <ul className="mt-3 flex flex-col gap-2">
            {(cov?.gaps ?? []).map((g) => (
              <li key={g.name} className="card p-3">
                <div className="flex flex-wrap items-baseline gap-x-2 gap-y-1">
                  <span className="text-[length:var(--text-sm)] font-semibold">{g.name}</span>
                  <span className="rounded bg-sunken px-1.5 py-0.5 text-[length:var(--text-2xs)] text-ink-3">{g.kind}</span>
                  <span
                    className="rounded bg-sunken px-1.5 py-0.5 text-[length:var(--text-2xs)] font-semibold text-ink-2"
                    title="Evidence grade of the significance: A peer-reviewed … D press"
                  >
                    grade {g.grade}
                  </span>
                </div>
                <p className="mt-1 text-[length:var(--text-sm)] leading-relaxed text-ink-2">{g.significance}</p>
                <p className="mt-0.5 text-[length:var(--text-2xs)] text-ink-3">
                  <span className="label">Source</span> {g.evidence} · <span className="label">Not watched because</span> {g.why_not_watched}
                </p>
              </li>
            ))}
          </ul>
        </section>
      </main>
    </>
  );
}
