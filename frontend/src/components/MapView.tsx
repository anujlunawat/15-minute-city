import {
  MapContainer,
  GeoJSON,
  TileLayer,
  CircleMarker,
  Popup,
} from "react-leaflet";
import "leaflet/dist/leaflet.css";
import { useEffect, useState } from "react";
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
  fetchPolygonAccessibility,
} from "../api/nodes";

interface MapViewProps {
  nodes: NodeData[];
}

// type PoiProperties = {
//   kind: "origin" | "poi";
//   group: string;
//   tag: string;
//   name: string;
//   distance_m: number;
// };

function MapView({ nodes }: MapViewProps) {
  const [data, setData] = useState<FeatureCollection<
    Polygon | MultiPolygon
  > | null>(null);
  // const [poiData, setPoiData] =
  //   useState<FeatureCollection<Point, PoiProperties> | null>(null);
  const [polygonData, setPolygonData] =
    useState<AccessibilityPolygonCollection | null>(null);

  useEffect(() => {
    async function loadPolygonData() {
      try {
        const data = await fetchPolygonAccessibility();
        setPolygonData(data);
      } catch (error) {
        console.error(error);
      }
    }
    loadPolygonData();
  }, []);

  const geojson: FeatureCollection<Point> = {
    type: "FeatureCollection",
    features: nodes.map((node) => ({
      type: "Feature",
      geometry: {
        type: "Point",
        coordinates: [node.lon, node.lat],
      },
      properties: {
        grocery_time: node.grocery_time,
        accessible: node.accessible,
      },
    })),
  };

  const pointToLayer = (feature: Feature<Point>, latlng: LatLng) => {
    const accessible = feature.properties?.accessible;

    console.log("latlng:", latlng);
    return L.circleMarker(latlng, {
      radius: 4,
      color: accessible ? "green" : "red",
      fillOpacity: 0.8,
    });
  };

  const onEachFeature = (feature: Feature<Point>, layer: Layer) => {
    if (feature.properties && "bindPopup" in layer) {
      (layer as L.CircleMarker).bindPopup(
        `Grocery Time: ${feature.properties.grocery_time} sec`,
      );
    }
  };

  // const colorByGroup: Record<string, string> = {
  //   origin: "red",
  //   amenity: "#1d4ed8",
  //   shop: "#15803d",
  //   leisure: "#ea580c",
  //   other: "#4b5563",
  // };

  // const poiPointToLayer = (
  //   feature: Feature<Point, PoiProperties>,
  //   latlng: LatLng
  // ) => {
  //   const group = feature.properties?.group ?? "other";
  //   const kind = feature.properties?.kind;
  //   const color = colorByGroup[group] ?? colorByGroup.other;

  //   return L.circleMarker(latlng, {
  //     radius: kind === "origin" ? 8 : 5,
  //     color,
  //     fillColor: color,
  //     fillOpacity: 0.9,
  //     weight: kind === "origin" ? 3 : 2,
  //   });
  // };

  // const onEachPoiFeature = (
  //   feature: Feature<Point, PoiProperties>,
  //   layer: Layer
  // ) => {
  //   if (!feature.properties || !("bindTooltip" in layer)) {
  //     return;
  //   }
  //   const { kind, name, tag, distance_m } = feature.properties;
  //   const label =
  //     kind === "origin"
  //       ? name
  //       : `${name} (${tag.replace("_", " ")}) - ${distance_m} m`;

  //   (layer as L.CircleMarker).bindTooltip(label, {
  //     sticky: true,
  //     direction: "top",
  //   });
  // };

  const handleClick = async (lat: number, lng: number) => {
    console.log("Clicked at:", lat, lng);

    const response = await fetch("http://localhost:8000/isochrone", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ lat, lng }),
    });
    if (!response.ok) {
      throw new Error("Failed to fetch POIs");
    }
    const data = await response.json();
    setData(data);
    // setPoiData(data);
  };

  useEffect(() => {
    console.log("DATA RECEIVED:", data);
  }, [data]);

  const polygonStyle = (
    feature?: Feature<Polygon | MultiPolygon, AccessibilityPolygonProperties>,
  ) => {
    const color = feature?.properties?.color ?? "#475569";
    return {
      color,
      fillColor: color,
      fillOpacity: 0.35,
      weight: 1.5,
    };
  };

  const onEachPolygonFeature = (
    feature: Feature<Polygon | MultiPolygon, AccessibilityPolygonProperties>,
    layer: Layer,
  ) => {
    if (!feature.properties || !("bindPopup" in layer)) {
      return;
    }

    // const { accessibility_percent, accessible_groups, missing_groups, group_counts } =
    //   feature.properties;

    // const accessibleLabel = accessible_groups.length
    //   ? accessible_groups.join(", ")
    //   : "none";
    // const missingLabel = missing_groups.length ? missing_groups.join(", ") : "none";
    // const countsLabel = Object.entries(group_counts)
    //   .map(([group, count]) => `${group}: ${count}`)
    //   .join("<br/>");

    // (layer as L.Path).bindPopup(
    //   `<b>Accessibility:</b> ${accessibility_percent}%<br/>
    //    <b>Available:</b> ${accessibleLabel}<br/>
    //    <b>Missing:</b> ${missingLabel}<br/>
    //    <b>POI counts:</b><br/>${countsLabel}`
    // );
  };

  return (
    <MapContainer
      center={[18.5308, 73.8475]}
      zoom={14}
      style={{ height: "100vh", width: "100%" }}
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />

      {polygonData && (
        <GeoJSON
          data={polygonData}
          style={polygonStyle}
          onEachFeature={onEachPolygonFeature}
        />
      )}

      {nodes.length > 0 && (
        <GeoJSON
          data={geojson}
          pointToLayer={pointToLayer}
          onEachFeature={onEachFeature}
        />
      )}

      {/* {poiData && (
        <GeoJSON
          data={poiData}
          pointToLayer={poiPointToLayer}
          onEachFeature={onEachPoiFeature}
        />
      )} */}

      {data && (
        <GeoJSON
          data={data}
          style={(feature?: Feature<Polygon | MultiPolygon>) => ({
            color: feature?.properties?.colour ?? "#64748b",
            fillColor: feature?.properties?.colour ?? "#64748b",
            fillOpacity: 0.5,
            weight: 1,
          })}
        />
      )}

      {data &&
        data.features
          .filter((feature) => feature.properties)
          .map((feature, index) => (
            <CircleMarker
              key={index}
              center={[feature.properties!.lat, feature.properties!.lon]}
            >
              <Popup>Origin Node {index + 1}</Popup>
            </CircleMarker>
          ))}

      <MapClickHandler onClick={handleClick} />
    </MapContainer>
  );
}

export default MapView;
