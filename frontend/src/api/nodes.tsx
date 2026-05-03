import { type NodeData } from "../types/Node";
import type { FeatureCollection, MultiPolygon, Point, Polygon } from "geojson";

const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000";

export async function fetchNodes(): Promise<NodeData[]> {
  const response = await fetch(`${API_BASE}/nodes`);
  if (!response.ok) {
    throw new Error("Failed to fetch nodes");
  }
  return response.json();
}

export type AccessibilityPolygonProperties = {
  polygon_id: number;
  origin_lat: number;
  origin_lon: number;
  accessible_groups: string[];
  missing_groups: string[];
  group_counts: Record<string, number>;
  accessibility_score: number;
  accessibility_percent: number;
  color: string;
};

export type AccessibilityPolygonCollection = FeatureCollection<
  Polygon | MultiPolygon,
  AccessibilityPolygonProperties
>;

export async function fetchPolygonAccessibility(): Promise<AccessibilityPolygonCollection> {
  const response = await fetch(`${API_BASE}/polygon-accessibility`);
  if (!response.ok) {
    throw new Error("Failed to fetch polygon accessibility");
  }
  return response.json();
}

// ── POI types ──────────────────────────────────────────────────

export type PoiProperties = {
  poi_id: number;
  name: string;
  category: string;
  subtype: string;
  address: string;
};

export type PoiFeatureCollection = FeatureCollection<Point, PoiProperties>;

export async function fetchPoisForIsochrone(
  originNode: number
): Promise<PoiFeatureCollection> {
  const response = await fetch(`${API_BASE}/isochrone-pois/${originNode}`);
  if (!response.ok) {
    throw new Error("Failed to fetch POIs for isochrone");
  }
  return response.json();
}

// ── POI category colours ──────────────────────────────────────

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
