"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  API, act, getRoster, minutes, STATE_LABEL,
  type Incident, type Officer,
} from "@/lib/api";

/** What a sergeant standing at a junction can use.
 *
 *  Designed against the reality rather than an ideal: a budget Android in
 *  sunlight, held in one hand, on a connection that may be 2G, with perhaps
 *  thirty seconds of attention between directing vehicles. So: targets at least
 *  44 px, preset reasons instead of typing, one screen per task, and the
 *  navigation handoff goes to the app they already use.
 */

const FOUND = [
  "Vehicle breakdown",
  "Road works",
  "Signal not working",
  "Encroachment / parking",
  "Procession or event",
  "Waterlogging",
  "Heavy volume only",
  "Nothing found",
];

const BIG = "min-h-[44px] rounded-lg px-4 py-3 text-[length:var(--text-md)] font-semibold";

export default function Field() {
  const [roster, setRoster] = useState<Officer[]>([]);
  const [me, setMe] = useState<string>("");
  const [items, setItems] = useState<Incident[]>([]);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [open, setOpen] = useState<string | null>(null);
  const [online, setOnline] = useState(true);

  useEffect(() => {
    getRoster().then((r) => {
      setRoster(r.officers);
      const saved = typeof window !== "undefined" ? localStorage.getItem("field-officer") : null;
      if (saved) setMe(saved);
    }).catch(() => setRoster([]));
  }, []);

  useEffect(() => {
    const on = () => setOnline(true);
    const off = () => setOnline(false);
    window.addEventListener("online", on);
    window.addEventListener("offline", off);
    setOnline(navigator.onLine);
    return () => {
      window.removeEventListener("online", on);
      window.removeEventListener("offline", off);
    };
  }, []);

  const load = useCallback(async () => {
    try {
      const r = await fetch(`${API}/api/incidents`);
      const d = await r.json();
      setItems(d.incidents ?? []);
      setError(null);
    } catch (e) {
      setError("Could not reach the control room. Showing what was last loaded.");
    }
  }, []);

  useEffect(() => {
    load();
    const t = setInterval(load, 30_000);
    return () => clearInterval(t);
  }, [load]);

  const mine = useMemo(() => items.filter((i) => i.owner === me && i.is_open), [items, me]);
  const unassigned = useMemo(() => items.filter((i) => !i.owner && i.is_open), [items, me]);

  async function run(incident: Incident, action: string, body: Record<string, string | undefined> = {}) {
    setBusy(incident.incident_id + action);
    setError(null);
    try {
      const updated = await act(incident.incident_id, action, { by: me, ...body });
      setItems((list) => list.map((i) => (i.incident_id === updated.incident_id ? updated : i)));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(null);
    }
  }

  if (!me) {
    return (
      <main className="mx-auto min-h-dvh w-full max-w-[34rem] px-4 py-8">
        <h1 className="text-[length:var(--text-xl)] font-semibold">Who is on duty?</h1>
        <p className="mt-1.5 text-[length:var(--text-sm)] text-ink-2">
          Choose your name once. It is remembered on this device.
        </p>
        <ul className="mt-5 space-y-2.5">
          {roster.filter((o) => o.role !== "DUTY_OFFICER").map((o) => (
            <li key={o.officer_id}>
              <button
                type="button"
                onClick={() => {
                  setMe(o.name);
                  localStorage.setItem("field-officer", o.name);
                }}
                className={`${BIG} w-full border border-line-firm bg-surface text-left`}
              >
                {o.name}
                <span className="block text-[length:var(--text-sm)] font-normal text-ink-2">
                  {o.rank} · {o.unit} {o.on_duty ? "" : "· off duty"}
                </span>
              </button>
            </li>
          ))}
        </ul>
      </main>
    );
  }

  return (
    <main className="mx-auto min-h-dvh w-full max-w-[34rem] px-3 pb-16 pt-3">
      <header className="mb-3 flex items-center justify-between gap-3">
        <div>
          <p className="text-[length:var(--text-md)] font-semibold">{me}</p>
          <p className="text-[length:var(--text-2xs)] text-ink-3">Siliguri Traffic Command</p>
        </div>
        <div className="flex items-center gap-2">
          {!online && (
            <span className="rounded bg-high-tint px-2 py-1 text-[length:var(--text-2xs)] font-semibold" style={{ color: "var(--color-high)" }}>
              Offline
            </span>
          )}
          <Link href="/" className="text-[length:var(--text-sm)] text-ink-2 underline">Board</Link>
        </div>
      </header>

      {error && (
        <p className="mb-3 rounded-lg bg-sev-tint px-3 py-2.5 text-[length:var(--text-sm)]" style={{ color: "var(--color-sev)" }}>
          {error}
        </p>
      )}

      <h2 className="label mb-2">Assigned to you · {mine.length}</h2>
      {mine.length === 0 ? (
        <p className="rounded-lg border border-dashed border-line-firm px-4 py-6 text-center text-[length:var(--text-sm)] text-ink-2">
          Nothing assigned to you right now.
        </p>
      ) : (
        <ul className="space-y-3">
          {mine.map((i) => {
            const expanded = open === i.incident_id;
            return (
              <li key={i.incident_id} className="card overflow-hidden border-l-[3px]" style={{ borderLeftColor: "var(--color-sev)" }}>
                <div className="p-3.5">
                  <div className="flex items-center gap-2">
                    <span className="rounded bg-sunken px-2 py-0.5 text-[length:var(--text-2xs)] font-semibold text-ink-2">
                      {STATE_LABEL[i.state]}
                    </span>
                    <span className="tnum ml-auto text-[length:var(--text-2xs)] text-ink-3">
                      {minutes(i.age_minutes)}
                    </span>
                  </div>
                  <p className="mt-2 text-[length:var(--text-lg)] font-semibold leading-snug">{i.title}</p>
                  <p className="mt-0.5 text-[length:var(--text-base)] text-ink-2">{i.location_name}</p>

                  <div className="mt-3 grid grid-cols-2 gap-2">
                    <a
                      href={`https://www.google.com/maps/dir/?api=1&destination=${i.lat},${i.lon}&travelmode=driving`}
                      target="_blank"
                      rel="noreferrer"
                      className={`${BIG} border border-line-firm bg-surface text-center`}
                    >
                      Navigate
                    </a>
                    {i.next_actions.includes("ON_SCENE") ? (
                      <button
                        type="button"
                        disabled={busy !== null}
                        onClick={() => run(i, "on-scene")}
                        className={`${BIG} bg-navy text-white disabled:opacity-40`}
                      >
                        I&rsquo;m on scene
                      </button>
                    ) : (
                      <button
                        type="button"
                        onClick={() => setOpen(expanded ? null : i.incident_id)}
                        className={`${BIG} bg-navy text-white`}
                      >
                        {expanded ? "Close" : "Report"}
                      </button>
                    )}
                  </div>

                  {expanded && (
                    <div className="mt-3 border-t border-line pt-3">
                      <p className="label mb-2">What did you find?</p>
                      <div className="grid grid-cols-2 gap-2">
                        {FOUND.map((f) => (
                          <button
                            key={f}
                            type="button"
                            disabled={busy !== null}
                            onClick={() => run(i, "note", { text: f, kind: "CAUSE" })}
                            className="min-h-[44px] rounded-lg border border-line-firm bg-surface px-3 py-2 text-left text-[length:var(--text-sm)] font-medium disabled:opacity-40"
                          >
                            {f}
                          </button>
                        ))}
                      </div>

                      {i.next_actions.includes("RESOLVED") && (
                        <button
                          type="button"
                          disabled={busy !== null}
                          onClick={() => run(i, "resolve")}
                          className={`${BIG} mt-3 w-full text-white disabled:opacity-40`}
                          style={{ backgroundColor: "var(--color-ok)" }}
                        >
                          Traffic is moving again
                        </button>
                      )}
                    </div>
                  )}

                  {i.notes.length > 0 && (
                    <ul className="mt-2.5 space-y-1 border-l-2 border-line pl-2.5">
                      {i.notes.slice(-2).map((n, k) => (
                        <li key={k} className="text-[length:var(--text-sm)] text-ink-2">{n.text}</li>
                      ))}
                    </ul>
                  )}
                </div>
              </li>
            );
          })}
        </ul>
      )}

      {unassigned.length > 0 && (
        <>
          <h2 className="label mb-2 mt-6">Waiting for an officer · {unassigned.length}</h2>
          <ul className="space-y-2.5">
            {unassigned.map((i) => (
              <li key={i.incident_id} className="card p-3.5">
                <p className="text-[length:var(--text-base)] font-semibold leading-snug">{i.title}</p>
                <p className="mt-0.5 text-[length:var(--text-sm)] text-ink-2">{i.location_name}</p>
                <button
                  type="button"
                  disabled={busy !== null}
                  onClick={() => run(i, "assign", { to: me, unit: roster.find((o) => o.name === me)?.unit })}
                  className={`${BIG} mt-2.5 w-full bg-navy text-white disabled:opacity-40`}
                >
                  I&rsquo;ll take this
                </button>
              </li>
            ))}
          </ul>
        </>
      )}
    </main>
  );
}
