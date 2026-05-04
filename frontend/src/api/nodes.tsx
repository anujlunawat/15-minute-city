import { type NodeData } from "../types/Node";
import type { FeatureCollection, MultiPolygon, Point, Polygon } from "geojson";

const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000";

// ── Score labels ───────────────────────────────────────────────────────────────
export const SCORE_LABELS: Record<number, string> = {
  0: "No walkable amenities",
  1: "Very poor walkability",
  2: "Poor walkability",
  3: "Below average",
  4: "Average walkability",
  5: "Good walkability",
  6: "Excellent — true 15-min city",
};

// ── POI constants ──────────────────────────────────────────────────────────────
export const CATEGORIES = [
  "grocery",
  "healthcare",
  "pharmacy",
  "school",
  "park",
  "public_transport",
] as const;

export type Category = (typeof CATEGORIES)[number];

export const POI_COLORS: Record<string, string> = {
  grocery: "#22c55e",
  healthcare: "#ef4444",
  pharmacy: "#a855f7",
  school: "#f59e0b",
  park: "#10b981",
  public_transport: "#3b82f6",
  other: "#6b7280",
};

export const POI_LABELS: Record<string, string> = {
  grocery: "Grocery",
  healthcare: "Healthcare",
  pharmacy: "Pharmacy",
  school: "School",
  park: "Park",
  public_transport: "Transit",
};

// ── API types ──────────────────────────────────────────────────────────────────
export type AccessibilityPolygonProperties = {
  origin_node: number;
  score: number;
  color: string;
  colour: string;
};

export type AccessibilityPolygonCollection = FeatureCollection<
  Polygon | MultiPolygon,
  AccessibilityPolygonProperties
>;

export type PoiProperties = {
  poi_id: number;
  name: string;
  category: string;
  subtype: string;
  address: string;
};

export type PoiFeatureCollection = FeatureCollection<Point, PoiProperties>;

export type PoiSummary = Partial<Record<string, number>> & { total?: number };

// ── Fetch functions ────────────────────────────────────────────────────────────
export async function fetchNodes(): Promise<NodeData[]> {
  const r = await fetch(`${API_BASE}/nodes`);
  if (!r.ok) throw new Error("Failed to fetch nodes");
  return r.json();
}

export async function fetchPolygonAccessibility(): Promise<AccessibilityPolygonCollection> {
  const r = await fetch(`${API_BASE}/polygon-accessibility`);
  if (!r.ok) throw new Error("Failed to fetch polygon accessibility");
  return r.json();
}

export async function fetchPoisForIsochrone(
  originNode: number
): Promise<PoiFeatureCollection> {
  const r = await fetch(`${API_BASE}/isochrone-pois/${originNode}`);
  if (!r.ok) throw new Error("Failed to fetch POIs for isochrone");
  return r.json();
}

export async function fetchPoiSummary(originNode: number): Promise<PoiSummary> {
  const r = await fetch(`${API_BASE}/isochrone-pois/${originNode}/summary`);
  if (!r.ok) throw new Error("Failed to fetch POI summary");
  return r.json();
}

export async function geocodeAddress(
  query: string
): Promise<{ lat: number; lon: number; display_name: string }[]> {
  const params = new URLSearchParams({
    q: query,
    format: "json",
    limit: "5",
    countrycodes: "in",
  });
  const r = await fetch(
    `https://nominatim.openstreetmap.org/search?${params}`,
    { headers: { "Accept-Language": "en" } }
  );
  if (!r.ok) throw new Error("Geocode failed");
  const data = await r.json();
  return data.map((d: { lat: string; lon: string; display_name: string }) => ({
    lat: parseFloat(d.lat),
    lon: parseFloat(d.lon),
    display_name: d.display_name,
  }));
}
