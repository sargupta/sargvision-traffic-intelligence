import { describe, expect, it } from "vitest";
import type { Incident, Officer } from "./api";
import {
  isDestructive,
  matchIncidents,
  startsWithVerb,
  matchOfficers,
  parseCommand,
  type ParseContext,
} from "./intent";

// ── fixtures ────────────────────────────────────────────────────────────────
function incident(over: Partial<Incident> = {}): Incident {
  return {
    incident_id: "INC-VENUS",
    kind: "CHOKE_POINT",
    priority: "P2",
    state: "DETECTED",
    title: "Slow traffic on NH10 near Venus More",
    detail: "",
    location_name: "NH10, near Venus More",
    lat: 26.7,
    lon: 88.4,
    corridors: ["C_X__VENUS_MORE"],
    junctions: ["J_VENUS_MORE"],
    detected_at: "2026-08-30T18:00:00",
    age_minutes: 12,
    owner: null,
    is_open: true,
    needs_attention: true,
    evidence: {},
    limitation: "",
    assignments: [],
    notes: [],
    history: [],
    next_actions: ["ACKNOWLEDGED", "STOOD_DOWN", "LAPSED"],
    ...over,
  } as Incident;
}

const ROSTER: Officer[] = [
  { officer_id: "DO-1", name: "Duty Officer", rank: "Inspector", role: "DUTY_OFFICER", unit: "Control Room", on_duty: true },
  { officer_id: "TG-2", name: "SI Barman", rank: "Sub-Inspector", role: "FIELD", unit: "Traffic Guard 2", on_duty: true },
  { officer_id: "TG-3", name: "ASI Roy", rank: "ASI", role: "FIELD", unit: "Traffic Guard 3", on_duty: true },
  { officer_id: "PCR-1", name: "Mobile Patrol 1", rank: "Unit", role: "PATROL", unit: "PCR 1", on_duty: true },
];

function ctx(incidents: Incident[], source: ParseContext["source"] = "chat"): ParseContext {
  return { incidents, roster: ROSTER, source };
}

// ── entity grounding ──────────────────────────────────────────────────────
describe("matchOfficers — enum-constrained", () => {
  it("resolves 'guard 2' to TG-2", () => {
    expect(matchOfficers("send guard 2", ROSTER).map((o) => o.officer_id)).toEqual(["TG-2"]);
  });
  it("resolves a name", () => {
    expect(matchOfficers("assign to barman", ROSTER)[0].officer_id).toBe("TG-2");
  });
  it("resolves 'pcr 1' / 'patrol 1'", () => {
    expect(matchOfficers("pcr 1", ROSTER)[0].officer_id).toBe("PCR-1");
    expect(matchOfficers("mobile patrol 1", ROSTER)[0].officer_id).toBe("PCR-1");
  });
  it("never returns the duty officer as a dispatch target", () => {
    expect(matchOfficers("duty officer", ROSTER)).toEqual([]);
  });
  it("returns nothing for an officer not on the roster (cannot mint)", () => {
    expect(matchOfficers("send constable singh", ROSTER)).toEqual([]);
  });
});

describe("matchIncidents — enum-constrained", () => {
  const list = [
    incident({ incident_id: "INC-VENUS", title: "Slow near Venus More", location_name: "NH10, near Venus More", junctions: ["J_VENUS_MORE"] }),
    incident({ incident_id: "INC-SEVOKE", title: "Slow near Court More", location_name: "Sevoke Road, near Court More", junctions: ["J_COURT_MORE"] }),
  ];
  it("matches a junction phrase to the right incident", () => {
    expect(matchIncidents("resolve venus more", list).map((i) => i.incident_id)).toEqual(["INC-VENUS"]);
  });
  it("returns nothing for an unknown place", () => {
    expect(matchIncidents("resolve airport road", list)).toEqual([]);
  });
  it("ignores closed incidents", () => {
    const closed = [incident({ is_open: false })];
    expect(matchIncidents("venus more", closed)).toEqual([]);
  });
});

// ── full parse ────────────────────────────────────────────────────────────
describe("parseCommand", () => {
  it("parses acknowledge on a single named incident", () => {
    const r = parseCommand("acknowledge venus more", ctx([incident()]));
    expect(r.kind).toBe("ready");
    if (r.kind === "ready") {
      expect(r.intent.action).toBe("acknowledge");
      expect(r.intent.incidentId).toBe("INC-VENUS");
      expect(r.confirm).toBe(false);
    }
  });

  it("a bare verb is unambiguous when only one incident is open", () => {
    const r = parseCommand("resolve it", ctx([incident({ next_actions: ["RESOLVED", "CLEARING"], state: "ON_SCENE" })]));
    expect(r.kind).toBe("ready");
    if (r.kind === "ready") expect(r.intent.action).toBe("resolve");
  });

  it("asks which incident when several are open and none named", () => {
    const r = parseCommand("acknowledge", ctx([incident({ incident_id: "A" }), incident({ incident_id: "B" })]));
    expect(r.kind).toBe("need");
    if (r.kind === "need") expect(r.field).toBe("incident");
  });

  it("assign needs an officer, then completes", () => {
    const ack = incident({ state: "ACKNOWLEDGED", next_actions: ["ASSIGNED", "STOOD_DOWN"] });
    const need = parseCommand("assign venus more", ctx([ack]));
    expect(need.kind).toBe("need");
    const ok = parseCommand("assign venus more to guard 2", ctx([ack]));
    expect(ok.kind).toBe("ready");
    if (ok.kind === "ready") {
      expect(ok.intent.action).toBe("assign");
      expect(ok.intent.to).toBe("SI Barman");
      expect(ok.intent.unit).toBe("Traffic Guard 2");
    }
  });

  it("resolve is destructive and must be confirmed", () => {
    const r = parseCommand("resolve venus more", ctx([incident({ state: "ON_SCENE", next_actions: ["RESOLVED", "CLEARING"] })]));
    expect(r.kind).toBe("ready");
    if (r.kind === "ready") {
      expect(r.confirm).toBe(true);
      expect(r.readback.toLowerCase()).toContain("resolve");
    }
  });

  it("rejects an illegal transition with a helpful reason", () => {
    // DETECTED cannot go straight to RESOLVED
    const r = parseCommand("resolve venus more", ctx([incident({ state: "DETECTED", next_actions: ["ACKNOWLEDGED", "STOOD_DOWN"] })]));
    expect(r.kind).toBe("unknown");
    if (r.kind === "unknown") expect(r.reason.toLowerCase()).toContain("acknowledge");
  });

  it("stand down needs a reason", () => {
    const need = parseCommand("stand down venus more", ctx([incident()]));
    expect(need.kind).toBe("need");
    const ok = parseCommand("stand down venus more local officer says clear", ctx([incident()]));
    expect(ok.kind).toBe("ready");
    if (ok.kind === "ready") {
      expect(ok.intent.text).toBeTruthy();
      expect(ok.confirm).toBe(true);
    }
  });

  it("asks again when the officer is not named specifically enough", () => {
    const ack = incident({ state: "ACKNOWLEDGED", next_actions: ["ASSIGNED", "STOOD_DOWN"] });
    // "traffic guard" with no number resolves to nobody specific → ask
    const r = parseCommand("assign venus more to traffic guard", ctx([ack]));
    expect(["disambiguate", "need"]).toContain(r.kind);
  });

  it("returns unknown for a non-command", () => {
    expect(parseCommand("what is the weather", ctx([incident()])).kind).toBe("unknown");
  });

  it("a click-source ready intent has full confidence", () => {
    const r = parseCommand("acknowledge venus more", ctx([incident()], "click"));
    if (r.kind === "ready") expect(r.intent.confidence).toBe(1);
  });
});

describe("startsWithVerb — lets a fresh command escape a pending question", () => {
  it("is true for a command", () => {
    expect(startsWithVerb("acknowledge thana more")).toBe(true);
    expect(startsWithVerb("resolve it")).toBe(true);
  });
  it("is false for a bare slot reply", () => {
    expect(startsWithVerb("guard 2")).toBe(false);
    expect(startsWithVerb("venus more")).toBe(false);
  });
});

describe("isDestructive", () => {
  it("gates only the irreversible verbs", () => {
    expect(isDestructive("resolve")).toBe(true);
    expect(isDestructive("stand-down")).toBe(true);
    expect(isDestructive("close")).toBe(true);
    expect(isDestructive("acknowledge")).toBe(false);
    expect(isDestructive("assign")).toBe(false);
    expect(isDestructive("on-scene")).toBe(false);
  });
});
