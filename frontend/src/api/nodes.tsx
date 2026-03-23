import { type NodeData } from "../types/Node";
import type { FeatureCollection, MultiPolygon, Polygon } from "geojson";

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
