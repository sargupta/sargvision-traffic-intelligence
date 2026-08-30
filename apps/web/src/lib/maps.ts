/** Midnight Executive, translated into a Google Maps style array.
 *  The basemap is deliberately quiet: it is context for the arcs, never the
 *  subject. Road colours are flattened so no one can read congestion into them. */
export const MAP_STYLE: google.maps.MapTypeStyle[] = [
  { elementType: "geometry", stylers: [{ color: "#0A1628" }] },
  { elementType: "labels.icon", stylers: [{ visibility: "off" }] },
  { elementType: "labels.text.fill", stylers: [{ color: "#93A0B2" }] },
  { elementType: "labels.text.stroke", stylers: [{ color: "#060E1A" }, { weight: 3 }] },
  { featureType: "administrative", elementType: "geometry.stroke", stylers: [{ color: "#22334C" }] },
  { featureType: "administrative.land_parcel", stylers: [{ visibility: "off" }] },
  { featureType: "landscape", elementType: "geometry", stylers: [{ color: "#0C1B30" }] },
  { featureType: "poi", stylers: [{ visibility: "off" }] },
  { featureType: "poi.park", elementType: "geometry", stylers: [{ color: "#101F35" }] },
  { featureType: "road", elementType: "geometry", stylers: [{ color: "#16273F" }] },
  { featureType: "road", elementType: "geometry.stroke", stylers: [{ visibility: "off" }] },
  { featureType: "road", elementType: "labels", stylers: [{ visibility: "off" }] },
  { featureType: "road.arterial", elementType: "geometry", stylers: [{ color: "#1A2E4A" }] },
  { featureType: "road.highway", elementType: "geometry", stylers: [{ color: "#20374F" }] },
  { featureType: "transit", stylers: [{ visibility: "off" }] },
  { featureType: "water", elementType: "geometry", stylers: [{ color: "#071120" }] },
  { featureType: "water", elementType: "labels.text.fill", stylers: [{ color: "#33486A" }] },
];

let loader: Promise<typeof google.maps> | null = null;

declare global {
  interface Window {
    __sargMapsReady?: () => void;
  }
}

/** Load the Maps JS API.
 *
 *  This uses the `callback` parameter rather than `loading=async`. The async
 *  bootstrap resolves its script `onload` before `google.maps.importLibrary`
 *  is attached, so awaiting the load event and then calling importLibrary is a
 *  race that loses often enough to matter. `callback` fires only once every
 *  constructor is on `google.maps`, which is exactly the guarantee we need.
 */
export function loadMaps(key: string): Promise<typeof google.maps> {
  if (loader) return loader;

  loader = new Promise((resolve, reject) => {
    if (typeof window === "undefined") return reject(new Error("no window"));
    if (window.google?.maps?.Map) return resolve(window.google.maps);

    const timeout = window.setTimeout(
      () => reject(new Error("Google Maps timed out")),
      15000,
    );

    window.__sargMapsReady = () => {
      window.clearTimeout(timeout);
      resolve(window.google.maps);
    };

    const script = document.createElement("script");
    script.src =
      `https://maps.googleapis.com/maps/api/js?key=${encodeURIComponent(key)}` +
      `&v=weekly&callback=__sargMapsReady`;
    script.async = true;
    script.onerror = () => {
      window.clearTimeout(timeout);
      reject(new Error("Google Maps failed to load"));
    };
    document.head.appendChild(script);
  });

  return loader;
}

/** A quadratic bezier between two points, bulged perpendicular to the chord.
 *
 *  This is the design constraint made geometric. The observations carry an
 *  origin and a destination and no route in between, so the line we draw must
 *  not resemble a route. A visible arc that plainly ignores the street grid is
 *  the honest rendering — see docs/design/ui-ux.md §0.1.
 */
export function arcPath(
  from: [number, number],
  to: [number, number],
  bulge = 0.22,
  steps = 44,
): google.maps.LatLngLiteral[] {
  const [lat0, lng0] = from;
  const [lat2, lng2] = to;
  const mx = (lat0 + lat2) / 2;
  const my = (lng0 + lng2) / 2;
  const dx = lat2 - lat0;
  const dy = lng2 - lng0;
  // Perpendicular offset, scaled by chord length so short hops bulge less.
  const cx = mx - dy * bulge;
  const cy = my + dx * bulge;

  const out: google.maps.LatLngLiteral[] = [];
  for (let i = 0; i <= steps; i++) {
    const t = i / steps;
    const u = 1 - t;
    out.push({
      lat: u * u * lat0 + 2 * u * t * cx + t * t * lat2,
      lng: u * u * lng0 + 2 * u * t * cy + t * t * lng2,
    });
  }
  return out;
}

/** ink-600 → signal, through copper. Used for buffer; reversed for speed. */
export function ramp(t: number): string {
  const stops: [number, [number, number, number]][] = [
    [0, [22, 39, 63]],
    [0.45, [184, 115, 51]],
    [1, [194, 90, 74]],
  ];
  const c = Math.max(0, Math.min(1, t));
  for (let i = 0; i < stops.length - 1; i++) {
    const [p0, a] = stops[i];
    const [p1, b] = stops[i + 1];
    if (c >= p0 && c <= p1) {
      const k = (c - p0) / (p1 - p0);
      const m = a.map((v, j) => Math.round(v + (b[j] - v) * k));
      return `rgb(${m[0]},${m[1]},${m[2]})`;
    }
  }
  return "rgb(194,90,74)";
}
