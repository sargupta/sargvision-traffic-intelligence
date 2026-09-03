/** Putting a city on a rectangle, honestly.
 *
 *  This lives on its own because it is the code that was wrong, and wrong in
 *  the way that matters: the plan drew Siliguri about 1.5x longer per kilometre
 *  east-west than north-south, directly under a comment claiming it kept the
 *  city's shape. A duty officer reads "which of these is nearer" straight off
 *  the map, so a projection that lies about distance produces wrong decisions
 *  and looks fine doing it.
 *
 *  The cause was a fixed 1000x900 viewBox. Siliguri is portrait — the connected
 *  junctions span 4.81 km east-west by 7.30 km north-south — so a landscape box
 *  forced a choice between distorting and letterboxing, and the code took the
 *  distortion by normalising each axis to its own span. One scale for both axes
 *  is the fix, and being a pure function of the points and the box is what
 *  makes it checkable.
 */

export interface Box {
  /** Width of the host element, in CSS pixels. */
  w: number;
  /** Height of the host element, in CSS pixels. */
  h: number;
}

export interface Projection {
  x: (lon: number) => number;
  y: (lat: number) => number;
  /** Pixels per corrected degree, shared by both axes. */
  scale: number;
  /** Metres per pixel at this latitude — what a scale bar would show. */
  metresPerPixel: number;
  midLon: number;
}

/** Room kept clear on the right for labels, which are drawn outward from their
 *  node. A layout margin, not a projection term: both axes still share one
 *  scale, so the city keeps its shape. */
export const LABEL_GUTTER = 92;
export const INSET = 12;

const DEG = Math.PI / 180;
/** Metres per degree of latitude. Close enough at city scale. */
const M_PER_DEG_LAT = 110_574;

export function project(points: readonly [number, number][], box: Box): Projection | null {
  if (points.length < 2 || box.w < 40 || box.h < 40) return null;

  let minLon = Infinity;
  let maxLon = -Infinity;
  let minLat = Infinity;
  let maxLat = -Infinity;
  for (const [lon, lat] of points) {
    if (lon < minLon) minLon = lon;
    if (lon > maxLon) maxLon = lon;
    if (lat < minLat) minLat = lat;
    if (lat > maxLat) maxLat = lat;
  }

  // Equirectangular at this latitude. Without the cosine a raw lat/lon stretch
  // squashes Siliguri east-to-west by about 11%.
  const k = Math.cos(((minLat + maxLat) / 2) * DEG);
  const spanX = (maxLon - minLon) * k || 1e-9;
  const spanY = maxLat - minLat || 1e-9;

  const availW = Math.max(40, box.w - INSET - LABEL_GUTTER);
  const availH = Math.max(40, box.h - INSET * 2);

  // ONE scale factor, for both axes. Everything above is bookkeeping; this is
  // the line that has to stay true.
  const scale = Math.min(availW / spanX, availH / spanY);
  const ox = INSET + (availW - spanX * scale) / 2;
  const oy = INSET + (availH - spanY * scale) / 2;

  return {
    x: (lon: number) => ox + (lon - minLon) * k * scale,
    y: (lat: number) => oy + (maxLat - lat) * scale, // north up
    scale,
    metresPerPixel: M_PER_DEG_LAT / scale,
    midLon: (minLon + maxLon) / 2,
  };
}
