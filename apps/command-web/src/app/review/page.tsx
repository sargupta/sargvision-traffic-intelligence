"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { Chrome } from "@/components/Chrome";
import { ConditionTag, Empty } from "@/components/Bits";
import { getReview, useBoard, type BoardItem, type BoardReview } from "@/lib/api";

const URGENCY: Record<BoardItem["urgency"], { label: string; fg: string; tint: string }> = {
  NOW: { label: "Now", fg: "var(--color-sev)", tint: "var(--color-sev-tint)" },
  THIS_SHIFT: { label: "This shift", fg: "var(--color-high)", tint: "var(--color-high-tint)" },
  ADVISORY: { label: "Advisory", fg: "var(--color-none)", tint: "var(--color-none-tint)" },
};

function BoardCard({ item }: { item: BoardItem }) {
  const [open, setOpen] = useState(false);
  const u = URGENCY[item.urgency];
  const spd = item.live.speed_kmh;
  return (
    <li className="card overflow-hidden border-l-[3px]" style={{ borderLeftColor: u.fg }}>
      <div className="p-3.5">
        <div className="flex flex-wrap items-center gap-2">
          <span
            className="rounded px-2 py-0.5 text-[length:var(--text-2xs)] font-semibold"
            style={{ color: u.fg, backgroundColor: u.tint }}
          >
            {u.label}
          </span>
          <span className="text-[length:var(--text-md)] font-semibold">{item.junction}</span>
          {item.live.condition ? <ConditionTag condition={item.live.condition as never} /> : null}
          <span className="tnum text-[length:var(--text-sm)] text-ink-3">
            {spd != null ? `${spd.toFixed(0)} km/h` : "—"}
            {item.live.loaded_corridor ? ` · ${item.live.loaded_corridor}` : ""}
          </span>
          {item.live.has_choke_point ? (
            <span
              className="rounded px-1.5 py-0.5 text-[length:var(--text-2xs)] font-semibold"
              style={{ color: "var(--color-sev)", backgroundColor: "var(--color-sev-tint)" }}
            >
              located block
            </span>
          ) : null}
        </div>

        {/* The move — the thing to do now. */}
        <p className="mt-2 text-[length:var(--text-md)] font-semibold leading-snug">{item.move}</p>
        <p className="mt-1 text-[length:var(--text-sm)] leading-relaxed text-ink-2">
          {item.where_when}
        </p>

        {/* The seat — the honest 'expert chair': a real discipline + a grade. */}
        <div className="mt-2 flex flex-wrap items-center gap-2">
          <span className="label">Seat</span>
          <span className="text-[length:var(--text-sm)] font-medium text-ink">{item.seat}</span>
          <span
            className="rounded bg-sunken px-1.5 py-0.5 text-[length:var(--text-2xs)] font-semibold text-ink-2"
            title="Evidence grade: A peer-reviewed independent … E projection-as-result"
          >
            grade {item.grade}
          </span>
        </div>

        {/* The AI council's per-item note, when the council is on. */}
        {item.expert_note ? (
          <p
            className="mt-2.5 rounded-md border-l-2 bg-sunken px-3 py-2 text-[length:var(--text-sm)] leading-relaxed text-ink-2"
            style={{ borderLeftColor: "var(--color-copper)" }}
          >
            <span className="label" style={{ color: "var(--color-copper)" }}>
              Council
            </span>{" "}
            {item.expert_note}
          </p>
        ) : null}

        <button
          type="button"
          onClick={() => setOpen(!open)}
          aria-expanded={open}
          className="mt-2.5 text-[length:var(--text-sm)] font-medium text-ink-2 underline decoration-line-firm underline-offset-2 hover:text-ink no-print"
        >
          {open ? "Hide the working" : "Why this, and how to check it"}
        </button>

        {open ? (
          <div className="mt-2.5 space-y-2.5 border-t border-line pt-2.5">
            <div>
              <p className="label">Because</p>
              <p className="mt-1 text-[length:var(--text-sm)] leading-relaxed text-ink-2">
                {item.rationale}
              </p>
            </div>
            <div>
              <p className="label">Measure it</p>
              <p className="mt-1 text-[length:var(--text-sm)] leading-relaxed text-ink-2">
                {item.measure}
              </p>
              <p className="mt-1 text-[length:var(--text-sm)] leading-relaxed text-ink-3">
                Expected: {item.expected}
              </p>
            </div>
            <div>
              <p className="label">What it must not claim</p>
              <p
                className="mt-1 text-[length:var(--text-sm)] leading-relaxed"
                style={{ color: "var(--color-copper)" }}
              >
                {item.do_not_claim}
              </p>
              <p className="mt-1 text-[length:var(--text-sm)] leading-relaxed text-ink-3">
                {item.caveat}
              </p>
            </div>
            <div>
              <p className="label">Grounded in</p>
              <p className="mt-1 text-[length:var(--text-2xs)] leading-relaxed text-ink-3">
                {item.source}
              </p>
            </div>
          </div>
        ) : null}
      </div>
    </li>
  );
}

export default function ReviewPage() {
  const { board, connected } = useBoard();
  const [rev, setRev] = useState<BoardReview | null>(null);

  const load = useCallback(() => {
    getReview()
      .then(setRev)
      .catch(() => setRev(null));
  }, []);
  useEffect(() => {
    load();
    const t = setInterval(load, 60_000);
    return () => clearInterval(t);
  }, [load]);

  const byCouncil = rev?.generated_by === "adk-council";

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
          <h1 className="text-[length:var(--text-xl)] font-semibold">The review board</h1>
          <Link href="/" className="text-[length:var(--text-sm)] text-ink-2 underline">
            ← Board
          </Link>
        </div>
        <p className="mt-1 max-w-[74ch] text-[length:var(--text-sm)] leading-relaxed text-ink-2">
          A standing panel of the traffic-engineering canon — not invented experts, the disciplines
          and published standards a graduate programme is built from — reading the live situation and
          issuing the immediate move for each junction that warrants one now. Every move names the
          seat it comes from and the standard behind it, what to measure, and what it must not claim.
        </p>

        {rev ? (
          <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-[length:var(--text-2xs)]">
            <span
              className="rounded-full px-2 py-0.5 font-semibold"
              style={
                byCouncil
                  ? { color: "var(--color-copper)", backgroundColor: "var(--color-none-tint)" }
                  : { color: "var(--color-ink-2)", backgroundColor: "var(--color-sunken)" }
              }
              title={rev.council_status ?? ""}
            >
              {byCouncil ? "AI council · Google ADK on Vertex" : "Grounded engine"}
            </span>
            {rev.seats_consulted?.length ? (
              <span className="text-ink-3">
                Seats in play: {rev.seats_consulted.join(" · ")}
              </span>
            ) : null}
          </div>
        ) : null}

        {/* The AI council's cross-item read — the judgement a checklist cannot give. */}
        {rev?.synthesis ? (
          <section
            className="mt-4 rounded-lg border border-line bg-surface p-4"
            style={{ borderLeftWidth: 3, borderLeftColor: "var(--color-copper)" }}
          >
            <p className="label" style={{ color: "var(--color-copper)" }}>
              The board&rsquo;s read this shift
            </p>
            <p className="mt-1.5 text-[length:var(--text-md)] leading-relaxed text-ink">
              {rev.synthesis}
            </p>
          </section>
        ) : null}

        <section className="mt-5">
          {rev == null ? (
            <p className="text-[length:var(--text-sm)] text-ink-3">Loading…</p>
          ) : rev.count === 0 ? (
            <Empty
              title="The board recommends no move right now."
              detail={
                rev.stand_down ??
                "No located block, no junction slow-and-worse-than-usual without cover, no safety junction in its risk window."
              }
            />
          ) : (
            <ul className="flex flex-col gap-2.5">
              {rev.items.map((it) => (
                <BoardCard key={`${it.junction}-${it.move}`} item={it} />
              ))}
            </ul>
          )}
        </section>

        {rev ? (
          <div className="mt-6 space-y-2 border-t border-line pt-3 text-[length:var(--text-2xs)] leading-relaxed text-ink-3">
            <p>
              <span className="label">Doctrine</span> {rev.doctrine}
            </p>
            <p>
              <span className="label">Probe</span> {rev.probe_caveat}
            </p>
          </div>
        ) : null}
      </main>
    </>
  );
}
