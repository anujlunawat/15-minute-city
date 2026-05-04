import {
  MapContainer,
  GeoJSON,
  TileLayer,
  CircleMarker,
  Popup,
  Tooltip,
  useMap,
} from "react-leaflet";
import "leaflet/dist/leaflet.css";
import { useEffect, useRef, useState } from "react";
import { type NodeData } from "../types/Node";
import L, { LatLng, Layer } from "leaflet";
import type {
  Feature,
  FeatureCollection,
  MultiPolygon,
  Point,
  Polygon,
} from "geojson";
import MapClickHandler from "./MapClickHandler.tsx";
import {
  type AccessibilityPolygonCollection,
  type AccessibilityPolygonProperties,
  type PoiFeatureCollection,
  type PoiProperties,
  type PoiSummary,
  fetchPolygonAccessibility,
  fetchPoisForIsochrone,
  fetchPoiSummary,
  POI_COLORS,
  SCORE_LABELS,
} from "../api/nodes";

// ── Types ──────────────────────────────────────────────────────────────────────
interface MapViewProps {
  nodes: NodeData[];
  onResult: (result: IsochroneResult | null) => void;
  onLoading: (loading: boolean) => void;
  onSummary: (summary: PoiSummary | null) => void;
  activeCategories: Set<string>;
  heatmapOpacity: number;
  flyToTarget: { lat: number; lon: number } | null;
}

export interface IsochroneResult {
  origin_node: number;
  lat: number;
  lon: number;
  score: number;
  colour: string;
  distance_m: number;
}

// ── Haversine (client-side walk time) ─────────────────────────────────────────
function haversineM(lat1: number, lon1: number, lat2: number, lon2: number) {
  const R = 6_371_000;
  const toRad = (x: number) => (x * Math.PI) / 180;
  const dLat = toRad(lat2 - lat1);
  const dLon = toRad(lon2 - lon1);
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLon / 2) ** 2;
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

// ── Fly-to isochrone result ────────────────────────────────────────────────────
function FlyTo({ lat, lon }: { lat: number; lon: number }) {
  const map = useMap();
  useEffect(() => {
    map.flyTo([lat, lon], map.getZoom(), { animate: true, duration: 0.8 });
  }, [lat, lon, map]);
  return null;
}

// ── Fly-to search result (zooms to z15) ───────────────────────────────────────
function FlyToTarget({ target }: { target: { lat: number; lon: number } | null }) {
  const map = useMap();
  useEffect(() => {
    if (target) map.flyTo([target.lat, target.lon], 15, { animate: true, duration: 1.2 });
  }, [target, map]);
  return null;
}

// ── MapView ────────────────────────────────────────────────────────────────────
function MapView({
  nodes,
  onResult,
  onLoading,
  onSummary,
  activeCategories,
  heatmapOpacity,
  flyToTarget,
}: MapViewProps) {
  const [isoData, setIsoData] = useState<FeatureCollection<
    Polygon | MultiPolygon
  > | null>(null);
  const [polygonData, setPolygonData] =
    useState<AccessibilityPolygonCollection | null>(null);
  const [poiData, setPoiData] = useState<PoiFeatureCollection | null>(null);
  const [clickMarker, setClickMarker] = useState<{
    lat: number;
    lng: number;
  } | null>(null);

  const geoJsonKey = useRef(0);
  const poiKey = useRef(0);

  // Load background accessibility polygons on mount
  useEffect(() => {
    fetchPolygonAccessibility()
      .then(setPolygonData)
      .catch((e) => console.error("Failed to load polygon accessibility:", e));
  }, []);

  // ── Map click ────────────────────────────────────────────────────────────────
  const handleClick = async (lat: number, lng: number) => {
    setClickMarker({ lat, lng });
    onLoading(true);
    onResult(null);
    onSummary(null);
    setIsoData(null);
    setPoiData(null);

    // Update URL hash for shareability
    window.location.hash = `${lat.toFixed(5)},${lng.toFixed(5)}`;

    try {
      const response = await fetch("http://localhost:8000/isochrone", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ lat, lng }),
      });
      if (!response.ok) throw new Error("Backend error");

      const data: FeatureCollection<Polygon | MultiPolygon> =
        await response.json();
      geoJsonKey.current += 1;
      setIsoData(data);

      if (data.features.length > 0) {
        const props = data.features[0].properties as IsochroneResult;
        onResult(props);

        // Fetch POIs and summary in parallel
        const [pois, summary] = await Promise.all([
          fetchPoisForIsochrone(props.origin_node).catch(() => null),
          fetchPoiSummary(props.origin_node).catch(() => null),
        ]);
        if (pois) { poiKey.current += 1; setPoiData(pois); }
        if (summary) onSummary(summary);
      }
    } catch (err) {
      console.error("Isochrone fetch failed:", err);
      onResult(null);
    } finally {
      onLoading(false);
    }
  };

  // ── Styles ───────────────────────────────────────────────────────────────────
  const polygonStyle = (
    feature?: Feature<Polygon | MultiPolygon, AccessibilityPolygonProperties>
  ) => {
    const color = feature?.properties?.color ?? "#475569";
    return { color, fillColor: color, fillOpacity: heatmapOpacity, weight: 1 };
  };

  const isoStyle = (feature?: Feature<Polygon | MultiPolygon>) => {
    const colour = feature?.properties?.colour ?? "#58a6ff";
    return { color: colour, fillColor: colour, fillOpacity: 0.45, weight: 2.5 };
  };

  const pointToLayer = (_feature: Feature, latlng: LatLng) =>
    L.circleMarker(latlng, {
      radius: 3,
      color: "#58a6ff",
      fillColor: "#58a6ff",
      fillOpacity: 0.5,
      weight: 0,
    });

  const onEachIsoFeature = (
    feature: Feature<Polygon | MultiPolygon>,
    layer: Layer
  ) => {
    if (!feature.properties) return;
    const { score, colour, distance_m, origin_node } =
      feature.properties as IsochroneResult;
    const label = SCORE_LABELS[score] ?? "Unknown";
    (layer as L.Path).bindPopup(
      `<div class="popup-score-row">
        <div class="popup-dot" style="background:${colour}"></div>
        <b style="color:${colour}">Score ${score}/6</b>
      </div>
      <div class="popup-label">${label}</div>
      <div style="margin-top:6px; display:flex; gap:8px; flex-wrap:wrap;">
        <span class="meta-chip">Node <span>${origin_node}</span></span>
        <span class="meta-chip">~<span>${Math.round(distance_m)} m</span> away</span>
      </div>`,
      { maxWidth: 240 }
    );
  };

  const isoResult = isoData?.features[0]?.properties as
    | IsochroneResult
    | undefined;

  // ── Render ───────────────────────────────────────────────────────────────────
  return (
    <MapContainer
      center={[18.5308, 73.8475]}
      zoom={14}
      style={{ height: "100vh", width: "100%" }}
      zoomControl={true}
    >
      <TileLayer
        attribution="&copy; OpenStreetMap contributors"
        url="https://{s}.tile.openstreetmap.fr/hot/{z}/{x}/{y}.png"
      />

      {/* Heatmap layer — key={heatmapOpacity} forces re-render when opacity changes.
           Uncomment the block below to enable the background accessibility heatmap. */}
      {/* polygonData && (
        <GeoJSON key={heatmapOpacity} data={polygonData} style={polygonStyle} />
      ) */}

      {nodes.length > 0 && nodes.length < 2000 && (
        <GeoJSON
          data={{
            type: "FeatureCollection" as const,
            features: nodes.map((n) => ({
              type: "Feature" as const,
              geometry: { type: "Point" as const, coordinates: [n.lon, n.lat] },
              properties: n,
            })),
          }}
          pointToLayer={pointToLayer}
        />
      )}

      {isoData && (
        <GeoJSON
          key={geoJsonKey.current}
          data={isoData}
          style={isoStyle}
          onEachFeature={onEachIsoFeature}
        />
      )}

      {/* POI markers — filtered by activeCategories */}
      {poiData &&
        poiData.features
          .filter((f) => activeCategories.has((f.properties as PoiProperties).category))
          .map((feature) => {
            const props = feature.properties as PoiProperties;
            const [lon, lat] = feature.geometry.coordinates;
            const color = POI_COLORS[props.category] ?? POI_COLORS.other;
            const subtypeLabel = props.subtype
              .replace(/_/g, " ")
              .replace(/\b\w/g, (c) => c.toUpperCase());

            // Walk time from isochrone origin
            let walkLabel = "";
            if (isoResult) {
              const distM = haversineM(isoResult.lat, isoResult.lon, lat, lon);
              const walkSec = distM / 1.4;
              walkLabel =
                walkSec < 60
                  ? `~${Math.round(walkSec)}s walk`
                  : `~${Math.round(walkSec / 60)} min walk`;
            }

            const gmapsUrl = `https://www.google.com/maps/search/?api=1&query=${lat},${lon}`;

            return (
              <CircleMarker
                key={`poi-${props.poi_id}`}
                center={[lat, lon]}
                radius={6}
                pathOptions={{
                  color: "#161b22",
                  fillColor: color,
                  fillOpacity: 0.9,
                  weight: 1.5,
                }}
              >
                <Tooltip
                  direction="top"
                  offset={[0, -8]}
                  className="poi-tooltip"
                  sticky
                >
                  <span className="poi-tooltip-name">{props.name}</span>
                  <span className="poi-tooltip-sub">{subtypeLabel}</span>
                  {walkLabel && (
                    <span className="poi-tooltip-walk">{walkLabel}</span>
                  )}
                </Tooltip>
                <Popup>
                  <div className="poi-popup">
                    <div className="poi-popup-header">
                      <div className="poi-popup-dot" style={{ background: color }} />
                      <div>
                        <div className="poi-popup-name">{props.name}</div>
                        <div className="poi-popup-cat">
                          {props.category} · {subtypeLabel}
                        </div>
                      </div>
                    </div>
                    {walkLabel && (
                      <div className="poi-popup-walk">🚶 {walkLabel}</div>
                    )}
                    {props.address && (
                      <div className="poi-popup-address">📍 {props.address}</div>
                    )}
                    <a
                      className="poi-gmaps-btn"
                      href={gmapsUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      Open in Google Maps ↗
                    </a>
                  </div>
                </Popup>
              </CircleMarker>
            );
          })}

      {clickMarker && (
        <CircleMarker
          center={[clickMarker.lat, clickMarker.lng]}
          radius={7}
          pathOptions={{
            color: "#58a6ff",
            fillColor: "#58a6ff",
            fillOpacity: 0.9,
            weight: 2,
          }}
        >
          <Popup>
            <span style={{ fontSize: 12, color: "#8b949e" }}>
              {clickMarker.lat.toFixed(5)}, {clickMarker.lng.toFixed(5)}
            </span>
          </Popup>
        </CircleMarker>
      )}

      {isoResult && <FlyTo lat={isoResult.lat} lon={isoResult.lon} />}
      <FlyToTarget target={flyToTarget} />
      <MapClickHandler onClick={handleClick} />
    </MapContainer>
  );
}

export default MapView;
