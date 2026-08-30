"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { hhmm } from "@/lib/api";

const NAV = [
  { href: "/", label: "Board" },
  { href: "/network", label: "Network" },
  { href: "/handover", label: "Handover" },
  { href: "/field", label: "Field" },
];

/** Chrome carries three things an officer must never have to hunt for:
 *  whether the data is live, how old it is, and who they are signed in as. */
export function Chrome({
  at,
  connected,
  cycle,
  officer,
}: {
  at?: string;
  connected: boolean;
  cycle?: number;
  officer: string;
}) {
  const path = usePathname();

  return (
    <header className="sticky top-0 z-30 border-b border-line bg-navy text-white no-print">
      <div className="mx-auto flex w-full max-w-[130rem] flex-wrap items-center gap-x-6 gap-y-2 px-4 py-2.5 lg:px-6">
        <Link href="/" className="flex items-baseline gap-2.5">
          <span className="text-[length:var(--text-md)] font-semibold tracking-tight">
            Siliguri Traffic Command
          </span>
          <span className="text-[length:var(--text-2xs)] font-semibold uppercase tracking-[0.08em] text-white/55">
            SARGVISION
          </span>
        </Link>

        <nav aria-label="Sections" className="flex items-center gap-0.5">
          {NAV.map((n) => {
            const active = n.href === "/" ? path === "/" : path.startsWith(n.href);
            return (
              <Link
                key={n.href}
                href={n.href}
                aria-current={active ? "page" : undefined}
                className={`rounded px-2.5 py-1 text-[length:var(--text-sm)] transition-colors ${
                  active ? "bg-white/15 text-white" : "text-white/70 hover:bg-white/10 hover:text-white"
                }`}
              >
                {n.label}
              </Link>
            );
          })}
        </nav>

        <div className="ml-auto flex items-center gap-5">
          <span className="flex items-center gap-2" title={connected ? "Receiving updates" : "Not receiving updates — figures may be stale"}>
            <span
              aria-hidden
              className={`h-2 w-2 rounded-full ${connected ? "bg-emerald-400" : "bg-amber-400"}`}
            />
            <span className="text-[length:var(--text-2xs)] font-semibold uppercase tracking-[0.08em] text-white/80">
              {connected ? "Live" : "Not updating"}
            </span>
          </span>

          <span className="tnum text-[length:var(--text-sm)] text-white/75">
            {at ? hhmm(at) : "—"}
            {cycle !== undefined && <span className="ml-2 text-white/45">cycle {cycle}</span>}
          </span>

          <span className="hidden text-[length:var(--text-sm)] text-white/75 sm:inline">{officer}</span>
        </div>
      </div>
    </header>
  );
}
