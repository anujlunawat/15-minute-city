import osmnx as ox
import networkx as nx
from networkx import MultiDiGraph
import geopandas as gpd
import backend.constants as constants
from shapely.geometry import Point

tags = {
    "amenity": ["school", "pharmacy", "restaurant"],
    "shop": ["supermarket", "convenience"],
    "leisure": "park",
}


def get_node(G, lat, lon):
    node = ox.distance.nearest_nodes(G, X=lon, Y=lat)
    return node


def build_graph(fp) -> MultiDiGraph:
    return ox.load_graphml(fp)


def _get_tag_info(row) -> tuple[str, str]:
    for key in ("amenity", "shop", "leisure"):
        value = row.get(key)
        if isinstance(value, str) and value:
            return key, value
    return "other", "other"

    
def _get_point(geometry):
    if geometry is None or geometry.is_empty:
        return None
    if isinstance(geometry, Point):
        return geometry
    return geometry.representative_point()


def _distance_meters(origin_lat, origin_lon, lat, lon) -> float:
    return float(ox.distance.great_circle(origin_lat, origin_lon, lat, lon))


def _serialize_for_frontend(geodf, lat, lon):
    features = [
        {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [lon, lat]},
            "properties": {
                "kind": "origin",
                "group": "origin",
                "tag": "origin",
                "name": "Selected location",
                "distance_m": 0.0,
            },
        }
    ]

    for _, row in geodf.iterrows():
        point = _get_point(row.geometry)
        if point is None:
            continue

        group, tag_value = _get_tag_info(row)
        poi_lat = float(point.y)
        poi_lon = float(point.x)
        poi_name = row.get("name")
        if not isinstance(poi_name, str) or not poi_name.strip():
            poi_name = tag_value.replace("_", " ").title()

        features.append(
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [poi_lon, poi_lat]},
                "properties": {
                    "kind": "poi",
                    "group": group,
                    "tag": tag_value,
                    "name": poi_name,
                    "distance_m": round(
                        _distance_meters(lat, lon, poi_lat, poi_lon), 1
                    ),
                },
            }
        )

    return {"type": "FeatureCollection", "features": features}


def main(G, lat, lon):
    _ = G
    geodf = ox.features_from_point((lat, lon), dist=1000, tags=tags)
    return _serialize_for_frontend(geodf, lat, lon)
