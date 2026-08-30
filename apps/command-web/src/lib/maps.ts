"use client";

/** A quiet light basemap.
 *
 *  The map is context for the network drawn on top of it, never the subject.
 *  Road colour in particular is flattened: Google's own traffic tints would
 *  compete with — and contradict — the bands we compute, and two disagreeing
 *  reds on one screen is worse than no map at all.
 */
export const LIGHT_MAP: google.maps.MapTypeStyle[] = [
  { elementType: "geometry", stylers: [{ color: "#F6F7F9" }] },
  { elementType: "labels.icon", stylers: [{ visibility: "off" }] },
  { elementType: "labels.text.fill", stylers: [{ color: "#6B7688" }] },
  { elementType: "labels.text.stroke", stylers: [{ color: "#FFFFFF" }, { weight: 3 }] },
  { featureType: "administrative", elementType: "geometry.stroke", stylers: [{ color: "#D9DEE6" }] },
  { featureType: "administrative.land_parcel", stylers: [{ visibility: "off" }] },
  { featureType: "landscape", elementType: "geometry", stylers: [{ color: "#F1F3F6" }] },
  { featureType: "poi", stylers: [{ visibility: "off" }] },
  { featureType: "poi.park", elementType: "geometry", stylers: [{ color: "#E8EFE9" }] },
  { featureType: "road", elementType: "geometry", stylers: [{ color: "#FFFFFF" }] },
  { featureType: "road", elementType: "geometry.stroke", stylers: [{ color: "#E4E8EE" }] },
  { featureType: "road.arterial", elementType: "geometry", stylers: [{ color: "#FFFFFF" }] },
  { featureType: "road.highway", elementType: "geometry", stylers: [{ color: "#FDFDFE" }] },
  { featureType: "road.highway", elementType: "geometry.stroke", stylers: [{ color: "#DCE2EA" }] },
  { featureType: "road", elementType: "labels.text.fill", stylers: [{ color: "#8A94A6" }] },
  { featureType: "transit", stylers: [{ visibility: "off" }] },
  { featureType: "water", elementType: "geometry", stylers: [{ color: "#DDE7F0" }] },
  { featureType: "water", elementType: "labels.text.fill", stylers: [{ color: "#9AAABE" }] },
];

let loader: Promise<typeof google.maps> | null = null;

declare global {
  interface Window {
    __commandMapsReady?: () => void;
  }
}

/** Loads via `callback` rather than `loading=async`.
 *  The async bootstrap resolves its script onload before importLibrary is
 *  attached, which is a race that loses often enough to break the map. */
export function loadMaps(key: string): Promise<typeof google.maps> {
  if (loader) return loader;
  loader = new Promise((resolve, reject) => {
    if (typeof window === "undefined") return reject(new Error("no window"));
    if (window.google?.maps?.Map) return resolve(window.google.maps);

    const timer = window.setTimeout(() => reject(new Error("Google Maps timed out")), 15000);
    window.__commandMapsReady = () => {
      window.clearTimeout(timer);
      resolve(window.google.maps);
    };
    const s = document.createElement("script");
    s.src =
      `https://maps.googleapis.com/maps/api/js?key=${encodeURIComponent(key)}` +
      `&v=weekly&callback=__commandMapsReady&language=en-IN&region=IN`;
    s.async = true;
    s.onerror = () => {
      window.clearTimeout(timer);
      reject(new Error("Google Maps failed to load"));
    };
    document.head.appendChild(s);
  });
  return loader;
}

export const BAND_STROKE: Record<string, { colour: string; weight: number }> = {
  SEVERE:   { colour: "#B32318", weight: 6 },
  HIGH:     { colour: "#B54708", weight: 5 },
  ELEVATED: { colour: "#B8860B", weight: 4 },
  NORMAL:   { colour: "#7C8698", weight: 2.5 },
  UNKNOWN:  { colour: "#C9D0DA", weight: 2 },
};
