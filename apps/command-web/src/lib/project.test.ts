import { describe, expect, it } from "vitest";
import { project } from "./project";

/** The real bounding box of the connected junctions, from
 *  data/curated/junctions.json: 4.81 km east-west by 7.30 km north-south. */
const SILIGURI: [number, number][] = [
  [88.408939, 26.684225],
  [88.457352, 26.750220],
];

const DEG = Math.PI / 180;
const M_PER_DEG_LAT = 110_574;

/** Ground distance in metres, equirectangular at Siliguri's latitude. */
function metres(a: [number, number], b: [number, number]): number {
  const k = Math.cos(26.717 * DEG);
  return Math.hypot((b[0] - a[0]) * k * M_PER_DEG_LAT, (b[1] - a[1]) * M_PER_DEG_LAT);
}

describe("project", () => {
  it("uses one scale for both axes, so distance on the plan is true", () => {
    // The defect this file exists for. Fitted into a landscape box, the old
    // code drew east-west about 1.5x longer per kilometre than north-south.
    const p = project(SILIGURI, { w: 969, h: 742 })!;
    const [W, S] = [SILIGURI[0], SILIGURI[1]];

    const ew: [number, number] = [S[0], W[1]]; // same latitude, other longitude
    const ns: [number, number] = [W[0], S[1]]; // same longitude, other latitude

    const ewPx = Math.hypot(p.x(ew[0]) - p.x(W[0]), p.y(ew[1]) - p.y(W[1]));
    const nsPx = Math.hypot(p.x(ns[0]) - p.x(W[0]), p.y(ns[1]) - p.y(W[1]));

    const ewScale = ewPx / metres(W, ew);
    const nsScale = nsPx / metres(W, ns);

    expect(ewScale / nsScale).toBeCloseTo(1, 2);
  });

  it("keeps one metres-per-pixel across every pair of points", () => {
    const p = project(SILIGURI, { w: 969, h: 742 })!;
    const pts: [number, number][] = [
      [88.4287, 26.7132], // Siliguri Junction
      [88.4326, 26.7096], // Mahananda Bridge
      [88.4341, 26.7042], // Venus More
      [88.4189, 26.7285], // Darjeeling More
      [88.4498, 26.7002], // Wall Ford Bypass
    ];
    const ratios: number[] = [];
    for (let i = 0; i < pts.length; i++) {
      for (let j = i + 1; j < pts.length; j++) {
        const px = Math.hypot(p.x(pts[j][0]) - p.x(pts[i][0]), p.y(pts[j][1]) - p.y(pts[i][1]));
        ratios.push(px / metres(pts[i], pts[j]));
      }
    }
    const mean = ratios.reduce((a, b) => a + b, 0) / ratios.length;
    for (const r of ratios) expect(Math.abs(r - mean) / mean).toBeLessThan
      (0.02);
  });

  it("puts north at the top", () => {
    const p = project(SILIGURI, { w: 969, h: 742 })!;
    expect(p.y(26.750220)).toBeLessThan(p.y(26.684225));
  });

  it("puts east to the right", () => {
    const p = project(SILIGURI, { w: 969, h: 742 })!;
    expect(p.x(88.457352)).toBeGreaterThan(p.x(88.408939));
  });

  it("draws the whole city inside the box, with the label gutter clear", () => {
    const box = { w: 969, h: 742 };
    const p = project(SILIGURI, box)!;
    for (const [lon, lat] of SILIGURI) {
      expect(p.x(lon)).toBeGreaterThanOrEqual(0);
      expect(p.x(lon)).toBeLessThanOrEqual(box.w - 92); // room kept for labels
      expect(p.y(lat)).toBeGreaterThanOrEqual(0);
      expect(p.y(lat)).toBeLessThanOrEqual(box.h);
    }
  });

  it("corrects for longitude converging at this latitude", () => {
    // Without the cosine the city is squashed east-west by about 11%.
    const p = project(SILIGURI, { w: 969, h: 742 })!;
    const oneDegLonPx = p.x(89.408939) - p.x(88.408939);
    const oneDegLatPx = p.y(25.684225) - p.y(26.684225);
    expect(oneDegLonPx / oneDegLatPx).toBeCloseTo(Math.cos(26.717 * (Math.PI / 180)), 2);
  });

  it("survives a box it cannot draw in", () => {
    expect(project(SILIGURI, { w: 0, h: 0 })).toBeNull();
    expect(project(SILIGURI, { w: 969, h: 10 })).toBeNull();
  });

  it("survives a degenerate point set", () => {
    expect(project([[88.42, 26.71]], { w: 969, h: 742 })).toBeNull();
    // Two identical points have no span; it must not divide by zero.
    const p = project(
      [
        [88.42, 26.71],
        [88.42, 26.71],
      ],
      { w: 969, h: 742 },
    );
    expect(Number.isFinite(p!.x(88.42))).toBe(true);
    expect(Number.isFinite(p!.y(26.71))).toBe(true);
  });

  it("reports a metres-per-pixel a scale bar could use", () => {
    const p = project(SILIGURI, { w: 969, h: 742 })!;
    // The city is ~7.3 km tall in ~718 px of usable height.
    expect(p.metresPerPixel).toBeGreaterThan(8);
    expect(p.metresPerPixel).toBeLessThan(14);
  });

  it("stays uniform in a portrait box as well as a landscape one", () => {
    for (const box of [
      { w: 969, h: 742 },
      { w: 400, h: 900 },
      { w: 1400, h: 500 },
      { w: 355, h: 468 },
    ]) {
      const p = project(SILIGURI, box)!;
      const a: [number, number] = [88.408939, 26.684225];
      const ew: [number, number] = [88.457352, 26.684225];
      const ns: [number, number] = [88.408939, 26.750220];
      const ewScale =
        Math.hypot(p.x(ew[0]) - p.x(a[0]), p.y(ew[1]) - p.y(a[1])) / metres(a, ew);
      const nsScale =
        Math.hypot(p.x(ns[0]) - p.x(a[0]), p.y(ns[1]) - p.y(a[1])) / metres(a, ns);
      expect(ewScale / nsScale, `box ${box.w}x${box.h}`).toBeCloseTo(1, 2);
    }
  });
});
