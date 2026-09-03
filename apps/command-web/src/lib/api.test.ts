import { beforeEach, describe, expect, it, vi } from "vitest";
import { ActionError, RUN_COLOUR, RUN_STYLE, act } from "./api";
import { clearToken, setToken } from "./auth";

/** Contrast against white, for the graphical-object floor of 3:1. */
function contrast([r, g, b]: [number, number, number]): number {
  const lin = (v: number) => {
    const c = v / 255;
    return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  };
  const L = 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b);
  return 1.05 / (L + 0.05);
}

/** Relative luminance, as a monochrome printer would flatten it. */
function grey([r, g, b]: [number, number, number]): number {
  const lin = (v: number) => {
    const c = v / 255;
    return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  };
  return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b);
}

describe("run-class encoding", () => {
  it("never distinguishes a class by colour alone", () => {
    // Slow and stopped were once 18 degrees apart in hue and read as one
    // colour on the map. Colour also fails anyone who cannot separate red
    // from amber, so weight and dash carry the same information.
    const widths = new Set(Object.values(RUN_STYLE).map((s) => s.width));
    expect(widths.size).toBe(3);
    expect(RUN_STYLE.SLOW.dash).toBeDefined();
    expect(RUN_STYLE.TRAFFIC_JAM.dash).toBeUndefined();
  });

  it("survives a monochrome printer", () => {
    // All three once fell within 2.2 grey points, so the briefing pack lost
    // the distinction entirely.
    const [ok, slow, jam] = [
      grey(RUN_COLOUR.NORMAL),
      grey(RUN_COLOUR.SLOW),
      grey(RUN_COLOUR.TRAFFIC_JAM),
    ];
    expect(Math.abs(slow - jam)).toBeGreaterThan(0.05);
    expect(Math.abs(ok - slow)).toBeGreaterThan(0.05);
  });

  it("clears the 3:1 contrast floor for graphical objects", () => {
    for (const [name, rgb] of Object.entries(RUN_COLOUR)) {
      expect(contrast(rgb), name).toBeGreaterThan(3);
    }
  });
});

describe("ActionError", () => {
  it("does not put the state machine's vocabulary in front of an officer", () => {
    const raw = "INC-1: cannot go ACKNOWLEDGED → ACKNOWLEDGED. Allowed: ASSIGNED";
    const e = new ActionError(409, raw);
    expect(e.human).not.toContain("ACKNOWLEDGED");
    expect(e.human).not.toContain("→");
    expect(e.detail).toBe(raw); // the exact reason is still kept for the record
  });

  it("knows a conflict means the officer's copy is stale", () => {
    expect(new ActionError(409, "x").stale).toBe(true);
    expect(new ActionError(400, "x").stale).toBe(false);
  });

  it("tells the officer where to unlock recording", () => {
    const e = new ActionError(401, "an officer token is required");
    expect(e.needsToken).toBe(true);
    expect(e.human).toMatch(/unlock/i);
  });

  it("says plainly that nothing was saved when recording is disabled", () => {
    expect(new ActionError(503, "disabled").human).toMatch(/nothing was saved/i);
  });

  it("passes a validation message through, because it names the missing field", () => {
    expect(new ActionError(400, "assign needs `to`").human).toBe("assign needs `to`");
  });
});

describe("act", () => {
  beforeEach(() => clearToken());

  it("sends the officer token when the console is unlocked", async () => {
    setToken("a-token");
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ incident_id: "INC-1" }), { status: 200 }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await act("INC-1", "acknowledge", { by: "DO-1" });

    const headers = fetchMock.mock.calls[0][1].headers as Record<string, string>;
    expect(headers.Authorization).toBe("Bearer a-token");
  });

  it("omits the header entirely when locked, rather than sending an empty one", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({}), { status: 200 }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await act("INC-1", "acknowledge", { by: "DO-1" });

    const headers = fetchMock.mock.calls[0][1].headers as Record<string, string>;
    expect(headers.Authorization).toBeUndefined();
  });

  it("raises a typed error carrying the status, not a bare string", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ detail: "already moved on" }), { status: 409 }),
      ),
    );
    await expect(act("INC-1", "acknowledge", { by: "DO-1" })).rejects.toMatchObject({
      status: 409,
      detail: "already moved on",
    });
  });

  it("still fails usefully when the body is not JSON at all", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response("<html>502</html>", { status: 502 })),
    );
    await expect(act("INC-1", "acknowledge", { by: "DO-1" })).rejects.toMatchObject({
      status: 502,
    });
  });
});
