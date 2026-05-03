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
  fetchPolygonAccessibility,
  fetchPoisForIsochrone,
  POI_COLORS,
} from "../api/nodes";

// ── Types ──────────────────────────────────────────────────────────
interface MapViewProps {
  nodes: NodeData[];
  onResult: (result: IsochroneResult | null) => void;
  onLoading: (loading: boolean) => void;
}

export interface IsochroneResult {
  origin_node: number;
  lat: number;
  lon: number;
  score: number;
  colour: string;
  distance_m: number;
}

// Score label helper
const SCORE_LABELS: Record<number, string> = {
  0: "No walkable amenities",
  1: "Very poor walkability",
  2: "Poor walkability",
  3: "Below average",
  4: "Average walkability",
  5: "Good walkability",
  6: "Excellent — true 15-min city",
};

// ── Fly-to helper ──────────────────────────────────────────────────
function FlyTo({ lat, lon }: { lat: number; lon: number }) {
  const map = useMap();
  useEffect(() => {
    map.flyTo([lat, lon], map.getZoom(), { animate: true, duration: 0.8 });
  }, [lat, lon, map]);
  return null;
}

// ── Component ──────────────────────────────────────────────────────
function MapView({ nodes, onResult, onLoading }: MapViewProps) {
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
    async function loadPolygonData() {
      try {
        const data = await fetchPolygonAccessibility();
        setPolygonData(data);
      } catch (error) {
        console.error("Failed to load polygon accessibility:", error);
      }
    }
    loadPolygonData();
  }, []);

  // ── Map click handler ────────────────────────────────────────────
  const handleClick = async (lat: number, lng: number) => {
    setClickMarker({ lat, lng });
    onLoading(true);
    onResult(null);
    setIsoData(null);
    setPoiData(null);

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

        // Fetch POIs inside this isochrone
        try {
          const pois = await fetchPoisForIsochrone(props.origin_node);
          poiKey.current += 1;
          setPoiData(pois);
        } catch (poiErr) {
          console.error("Failed to fetch POIs:", poiErr);
        }
      }
    } catch (err) {
      console.error("Isochrone fetch failed:", err);
      onResult(null);
    } finally {
      onLoading(false);
    }
  };

  // ── Styles ────────────────────────────────────────────────────────
  const polygonStyle = (
    feature?: Feature<Polygon | MultiPolygon, AccessibilityPolygonProperties>
  ) => {
    const color = feature?.properties?.color ?? "#475569";
    return { color, fillColor: color, fillOpacity: 0.3, weight: 1 };
  };

  const isoStyle = (feature?: Feature<Polygon | MultiPolygon>) => {
    const colour = feature?.properties?.colour ?? "#58a6ff";
    return {
      color: colour,
      fillColor: colour,
      fillOpacity: 0.45,
      weight: 2.5,
    };
  };

  // ── GeoJSON node layer (subtle background dots) ───────────────────
  const pointToLayer = (_feature: Feature, latlng: LatLng) =>
    L.circleMarker(latlng, {
      radius: 3,
      color: "#58a6ff",
      fillColor: "#58a6ff",
      fillOpacity: 0.5,
      weight: 0,
    });

  // ── Popup for clicked isochrone ───────────────────────────────────
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

  return (
    <MapContainer
      center={[18.5308, 73.8475]}
      zoom={14}
      style={{ height: "100vh", width: "100%" }}
      zoomControl={true}
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />

      {/* Background accessibility layer */}
      {polygonData && (
        <GeoJSON data={polygonData} style={polygonStyle} />
      )}

      {/* Background node dots */}
      {nodes.length > 0 && nodes.length < 2000 && (
        <GeoJSON
          data={{
            type: "FeatureCollection" as const,
            features: nodes.map((n) => ({
              type: "Feature" as const,
              geometry: {
                type: "Point" as const,
                coordinates: [n.lon, n.lat],
              },
              properties: n,
            })),
          }}
          pointToLayer={pointToLayer}
        />
      )}

      {/* Clicked isochrone polygon */}
      {isoData && (
        <GeoJSON
          key={geoJsonKey.current}
          data={isoData}
          style={isoStyle}
          onEachFeature={onEachIsoFeature}
        />
      )}

      {/* POI markers inside isochrone */}
      {poiData &&
        poiData.features.map((feature) => {
          const props = feature.properties as PoiProperties;
          const [lon, lat] = feature.geometry.coordinates;
          const color = POI_COLORS[props.category] ?? POI_COLORS.other;
          const subtypeLabel = props.subtype
            .replace(/_/g, " ")
            .replace(/\b\w/g, (c) => c.toUpperCase());

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
              </Tooltip>
              <Popup>
                <div className="poi-popup">
                  <div className="poi-popup-header">
                    <div
                      className="poi-popup-dot"
                      style={{ background: color }}
                    />
                    <div>
                      <div className="poi-popup-name">{props.name}</div>
                      <div className="poi-popup-cat">
                        {props.category} · {subtypeLabel}
                      </div>
                    </div>
                  </div>
                  {props.address && (
                    <div className="poi-popup-address">📍 {props.address}</div>
                  )}
                </div>
              </Popup>
            </CircleMarker>
          );
        })}

      {/* Pulse marker at click point */}
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

      {/* Fly to result */}
      {isoResult && <FlyTo lat={isoResult.lat} lon={isoResult.lon} />}

      <MapClickHandler onClick={handleClick} />
    </MapContainer>
  );
}

export { SCORE_LABELS };
export default MapView;
