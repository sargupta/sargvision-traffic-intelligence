"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { Chrome } from "@/components/Chrome";
import { Empty } from "@/components/Bits";
import {
  endDeployment,
  getDeployments,
  getRoster,
  startDeployment,
  useBoard,
  type Deployment,
  type DeploymentEffect,
  type Officer,
} from "@/lib/api";

/** The colour a verdict earns. Improving-and-beating-usual is the strong green;
 *  worse is red; the honest in-betweens are neutral. */
function verdictStyle(e: DeploymentEffect): { fg: string; label: string } {
  if (e.verdict.includes("beat this road")) return { fg: "var(--color-ok)", label: e.verdict };
  if (e.verdict.startsWith("worse")) return { fg: "var(--color-sev)", label: e.verdict };
  if (e.verdict.startsWith("improved")) return { fg: "var(--color-ok)", label: e.verdict };
  return { fg: "var(--color-ink-2)", label: e.verdict };
}

function DeltaSpeed({ e }: { e: DeploymentEffect }) {
  if (e.before_speed_kmh == null || e.during_speed_kmh == null) {
    return <span className="text-ink-3">measuring…</span>;
  }
  const up = (e.delta_speed_kmh ?? 0) > 0;
  const flat = Math.abs(e.delta_speed_kmh ?? 0) < 1;
  return (
    <span className="tnum whitespace-nowrap">
      <span className="font-semibold">{e.before_speed_kmh.toFixed(0)}</span>
      <span className="text-ink-3"> → </span>
      <span className="font-semibold">{e.during_speed_kmh.toFixed(0)} km/h</span>
      {!flat && e.delta_speed_kmh != null && (
        <span
          className="ml-2 font-semibold"
          style={{ color: up ? "var(--color-ok)" : "var(--color-sev)" }}
        >
          {up ? "↑" : "↓"} {Math.abs(e.delta_speed_kmh).toFixed(0)}
        </span>
      )}
    </span>
  );
}

function DeploymentCard({ d, onEnd }: { d: Deployment; onEnd: (id: string) => void }) {
  const e = d.effect;
  const v = verdictStyle(e);
  return (
    <li className="card p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-[length:var(--text-md)] font-semibold">{e.location}</p>
          <p className="mt-0.5 text-[length:var(--text-sm)] text-ink-2">
            {e.unit} · {e.purpose}
          </p>
        </div>
        <div className="text-right">
          <span
            className="rounded px-2 py-0.5 text-[length:var(--text-sm)] font-semibold"
            style={{ backgroundColor: "var(--color-sunken)", color: v.fg }}
          >
            {v.label}
          </span>
          <p className="mt-1 text-[length:var(--text-2xs)] text-ink-3">
            {e.active ? "on the ground" : "ended"} · {e.minutes_posted.toFixed(0)} min · confidence {e.confidence}
          </p>
        </div>
      </div>

      <dl className="mt-3 grid gap-3 sm:grid-cols-3">
        <div>
          <dt className="label">Speed, before → during</dt>
          <dd className="mt-0.5 text-[length:var(--text-md)]"><DeltaSpeed e={e} /></dd>
        </div>
        <div>
          <dt className="label">vs this road&rsquo;s usual</dt>
          <dd className="mt-0.5 text-[length:var(--text-sm)] text-ink-2">
            {e.vs_typical ?? "no baseline yet"}
          </dd>
        </div>
        <div>
          <dt className="label">Readings</dt>
          <dd className="tnum mt-0.5 text-[length:var(--text-sm)] text-ink-2">
            {e.samples.before} before · {e.samples.during} during
          </dd>
        </div>
      </dl>

      <p className="mt-3 rounded bg-sunken px-2.5 py-2 text-[length:var(--text-2xs)] leading-relaxed text-ink-3">
        <span className="label" style={{ color: "var(--color-copper)" }}>What this does and doesn&rsquo;t show</span>{" "}
        {e.limitation}
      </p>

      {e.active && (
        <div className="mt-3 flex justify-end">
          <button
            type="button"
            onClick={() => onEnd(d.deployment_id)}
            className="rounded border border-line-firm bg-surface px-3 py-1.5 text-[length:var(--text-sm)] font-medium text-ink-2 hover:bg-sunken"
          >
            End posting
          </button>
        </div>
      )}
    </li>
  );
}

function PostForm({ onPosted }: { onPosted: () => void }) {
  const { board } = useBoard();
  const [roster, setRoster] = useState<Officer[]>([]);
  const [corridor, setCorridor] = useState("");
  const [unit, setUnit] = useState("");
  const [purpose, setPurpose] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    getRoster().then((r) => setRoster(r.officers)).catch(() => setRoster([]));
  }, []);

  // Offer the slow corridors first — those are where a posting is worth measuring.
  const corridors = (board?.corridors ?? [])
    .filter((c) => c.condition === "ACUTE" || c.condition === "CHRONIC")
    .concat((board?.corridors ?? []).filter((c) => c.condition !== "ACUTE" && c.condition !== "CHRONIC"));

  const submit = async () => {
    setErr(null);
    if (!corridor || !unit || purpose.trim().length < 2) {
      setErr("Choose a corridor and unit, and say the purpose.");
      return;
    }
    setBusy(true);
    try {
      // `by` is the console identity (shared-token mode names no person on its
      // own — same as field reports); a per-officer token overrides it server-side.
      await startDeployment({ corridor_ids: [corridor], unit, purpose: purpose.trim(), by: "DO-1" });
      setCorridor("");
      setUnit("");
      setPurpose("");
      onPosted();
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="card p-4">
      <h2 className="text-[length:var(--text-md)] font-semibold">Post an officer</h2>
      <p className="mt-1 max-w-[70ch] text-[length:var(--text-sm)] text-ink-2">
        Log a posting and the system measures the road&rsquo;s speed before and during, against the
        corridor&rsquo;s own usual for the hour. That before/after is the thing a roster and a radio cannot give.
      </p>
      <div className="mt-3 grid gap-3 sm:grid-cols-3">
        <label className="flex flex-col gap-1 text-[length:var(--text-sm)]">
          <span className="label">Corridor</span>
          <select
            value={corridor}
            onChange={(e) => setCorridor(e.target.value)}
            className="rounded border border-line-firm bg-surface px-2.5 py-1.5"
          >
            <option value="">Choose a road…</option>
            {corridors.map((c) => (
              <option key={c.corridor_id} value={c.corridor_id}>
                {c.name}
                {c.speed_kmh != null ? ` — ${c.speed_kmh.toFixed(0)} km/h` : ""}
                {c.condition ? ` (${c.condition.toLowerCase()})` : ""}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1 text-[length:var(--text-sm)]">
          <span className="label">Unit</span>
          <select
            value={unit}
            onChange={(e) => setUnit(e.target.value)}
            className="rounded border border-line-firm bg-surface px-2.5 py-1.5"
          >
            <option value="">Choose a unit…</option>
            {roster.map((o) => (
              <option key={o.officer_id} value={o.unit}>{o.unit}</option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1 text-[length:var(--text-sm)]">
          <span className="label">Purpose</span>
          <input
            value={purpose}
            onChange={(e) => setPurpose(e.target.value)}
            placeholder="manage the peak movement"
            className="rounded border border-line-firm bg-surface px-2.5 py-1.5"
          />
        </label>
      </div>
      {err && (
        <p className="mt-2 text-[length:var(--text-sm)]" style={{ color: "var(--color-sev)" }}>{err}</p>
      )}
      <div className="mt-3 flex justify-end">
        <button
          type="button"
          onClick={submit}
          disabled={busy}
          className="rounded bg-navy px-4 py-1.5 text-[length:var(--text-sm)] font-medium text-white hover:bg-navy-2 disabled:opacity-60"
        >
          {busy ? "Posting…" : "Post & start measuring"}
        </button>
      </div>
    </section>
  );
}

export default function VerifyPage() {
  const { board, connected } = useBoard();
  const [deps, setDeps] = useState<Deployment[] | null>(null);

  const load = useCallback(() => {
    getDeployments().then((r) => setDeps(r.deployments)).catch(() => setDeps([]));
  }, []);

  useEffect(() => {
    load();
    const t = setInterval(load, 60_000);
    return () => clearInterval(t);
  }, [load]);

  const onEnd = async (id: string) => {
    try {
      await endDeployment(id);
      load();
    } catch {
      /* the card stays; a failed end is visible by the posting remaining active */
    }
  };

  const active = (deps ?? []).filter((d) => d.effect.active);
  const past = (deps ?? []).filter((d) => !d.effect.active);

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
          <h1 className="text-[length:var(--text-xl)] font-semibold">Did it work?</h1>
          <Link href="/" className="text-[length:var(--text-sm)] text-ink-2 underline">← Board</Link>
        </div>
        <p className="mt-1 max-w-[74ch] text-[length:var(--text-sm)] leading-relaxed text-ink-2">
          Every posting, measured. The road&rsquo;s own speed before and during, compared against what that
          corridor usually does at this hour — so &ldquo;it helped&rdquo; is evidence, not a claim. This is
          the one thing traffic police cannot get from officers on the ground and a wireless set.
        </p>

        <div className="mt-4">
          <PostForm onPosted={load} />
        </div>

        <h2 className="mt-6 text-[length:var(--text-md)] font-semibold">
          On the ground now <span className="font-normal text-ink-3">· {active.length}</span>
        </h2>
        {active.length === 0 ? (
          <div className="mt-2">
            <Empty title="No postings being measured." detail="Post an officer above, and the before/after starts accruing on the next reading." />
          </div>
        ) : (
          <ul className="mt-2 flex flex-col gap-3">
            {active.map((d) => <DeploymentCard key={d.deployment_id} d={d} onEnd={onEnd} />)}
          </ul>
        )}

        {past.length > 0 && (
          <>
            <h2 className="mt-6 text-[length:var(--text-md)] font-semibold">
              Ended <span className="font-normal text-ink-3">· {past.length}</span>
            </h2>
            <ul className="mt-2 flex flex-col gap-3">
              {past.map((d) => <DeploymentCard key={d.deployment_id} d={d} onEnd={onEnd} />)}
            </ul>
          </>
        )}
      </main>
    </>
  );
}
