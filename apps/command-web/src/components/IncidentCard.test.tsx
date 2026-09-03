import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { IncidentCard } from "./IncidentCard";
import type { Incident, Officer } from "@/lib/api";

const ROSTER: Officer[] = [
  { officer_id: "DO-1", name: "Duty Officer", rank: "Inspector", role: "DUTY_OFFICER", unit: "Control Room", on_duty: true },
  { officer_id: "TG-2", name: "Traffic Guard 2", rank: "Sub-Inspector", role: "FIELD", unit: "TG-2", on_duty: true },
];

function incident(over: Partial<Incident> = {}): Incident {
  return {
    incident_id: "INC-1",
    kind: "CHOKE_POINT",
    priority: "P2",
    state: "DETECTED",
    title: "Slow traffic on NH10 near Siliguri Junction",
    detail: "d",
    location_name: "NH10",
    lat: 26.72,
    lon: 88.41,
    corridors: ["C_A__B"],
    junctions: ["J_A"],
    detected_at: "2026-08-30T15:00:00",
    age_minutes: 34,
    owner: null,
    is_open: true,
    needs_attention: true,
    evidence: {},
    limitation: "unknown cause",
    assignments: [],
    notes: [],
    history: [],
    next_actions: ["ACKNOWLEDGED", "LAPSED", "STOOD_DOWN"],
    ...over,
  } as Incident;
}

const noop = () => {};

describe("IncidentCard", () => {
  it("offers the primary action in the header, not only at the foot of the card", async () => {
    // The bar exists below ~140 lines of evidence. At 1366x768 — the size the
    // control room runs — that put it off the bottom of the card, so the board
    // named an incident and hid the buttons on it.
    render(<IncidentCard incident={incident()} roster={ROSTER} officer="DO-1" onChanged={noop} />);
    const acknowledge = screen.getAllByRole("button", { name: "Acknowledge" });
    expect(acknowledge.length).toBe(2);
  });

  it("re-derives that action from the incident's own legal transitions", () => {
    render(
      <IncidentCard
        incident={incident({ state: "ACKNOWLEDGED", next_actions: ["ASSIGNED", "CLEARING"] })}
        roster={ROSTER}
        officer="DO-1"
        onChanged={noop}
      />,
    );
    expect(screen.getAllByRole("button", { name: "Assign" }).length).toBeGreaterThan(0);
    expect(screen.queryByRole("button", { name: "Acknowledge" })).toBeNull();
  });

  it("never offers to lapse an incident, because the system does that", () => {
    render(
      <IncidentCard
        incident={incident({ next_actions: ["ACKNOWLEDGED", "LAPSED"] })}
        roster={ROSTER}
        officer="DO-1"
        onChanged={noop}
      />,
    );
    expect(screen.queryByRole("button", { name: /cleared on its own/i })).toBeNull();
  });

  it("carries an anchor id, so advice can scroll to the incident it named", () => {
    const { container } = render(
      <IncidentCard incident={incident()} roster={ROSTER} officer="DO-1" onChanged={noop} />,
    );
    expect(container.querySelector("#incident-INC-1")).not.toBeNull();
  });

  it("acting does not also select the card underneath it", async () => {
    const onSelect = vi.fn();
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify(incident({ state: "ACKNOWLEDGED" })), { status: 200 }),
      ),
    );
    render(
      <IncidentCard
        incident={incident()}
        roster={ROSTER}
        officer="DO-1"
        onChanged={noop}
        onSelect={onSelect}
      />,
    );
    await userEvent.click(screen.getAllByRole("button", { name: "Acknowledge" })[0]);
    expect(onSelect).not.toHaveBeenCalled();
  });

  it("shows an officer-readable message when someone else got there first", async () => {
    const fresh = incident({ state: "ACKNOWLEDGED", next_actions: ["ASSIGNED"] });
    vi.stubGlobal(
      "fetch",
      vi.fn().mockImplementation((url: string, opts?: RequestInit) =>
        Promise.resolve(
          opts?.method === "POST"
            ? new Response(
                JSON.stringify({
                  detail: "INC-1: cannot go ACKNOWLEDGED → ACKNOWLEDGED. Allowed: ASSIGNED",
                }),
                { status: 409 },
              )
            : new Response(JSON.stringify(fresh), { status: 200 }),
        ),
      ),
    );
    const onChanged = vi.fn();
    render(
      <IncidentCard incident={incident()} roster={ROSTER} officer="DO-1" onChanged={onChanged} />,
    );

    await userEvent.click(screen.getAllByRole("button", { name: "Acknowledge" })[0]);

    // The state machine's wording must not reach the screen...
    await waitFor(() => expect(screen.getByText(/already moved this on/i)).toBeInTheDocument());
    expect(screen.queryByText(/cannot go ACKNOWLEDGED/)).toBeNull();
    // ...and the card must correct itself rather than leaving dead buttons.
    await waitFor(() => expect(onChanged).toHaveBeenCalledWith(fresh));
  });

  it("points the officer at the lock when recording is not unlocked", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ detail: "an officer token is required" }), { status: 401 }),
      ),
    );
    render(<IncidentCard incident={incident()} roster={ROSTER} officer="DO-1" onChanged={noop} />);
    await userEvent.click(screen.getAllByRole("button", { name: "Acknowledge" })[0]);
    await waitFor(() => expect(screen.getByText(/unlock/i)).toBeInTheDocument());
  });

  it("makes standing down ask for a reason before it will record one", async () => {
    render(
      <IncidentCard
        incident={incident({ next_actions: ["ACKNOWLEDGED", "STOOD_DOWN"] })}
        roster={ROSTER}
        officer="DO-1"
        onChanged={noop}
      />,
    );
    await userEvent.click(screen.getByRole("button", { name: /no action needed/i }));
    // A stand-down with no reason is the one outcome an audit cannot read.
    expect(screen.getByRole("button", { name: /confirm/i })).toBeDisabled();
  });
});
