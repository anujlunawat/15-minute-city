from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

import json
import math

import backend.database as database
import backend.db as duckdb_layer
import backend.constants as constants
from backend.models import ClickPoint


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/nodes")
def get_nodes():
    return database.fetch_nodes()


@app.get("/polygon-accessibility")
def get_polygon_accessibility():
    output_file = constants.FILES_FOLDER / "isochrone_final.json"
    if not output_file.exists():
        return {"type": "FeatureCollection", "features": []}
    return json.loads(output_file.read_text(encoding="utf-8"))


@app.get("/")
def hey():
    return {"status": "connected"}


@app.post("/isochrone")
async def get_nearest_isochrone(point: ClickPoint):
    """
    Given a clicked lat/lng, find the closest pre-computed isochrone polygon
    and return it as a GeoJSON FeatureCollection with colour and score.
    """
    iso_gdf = database.fetch_isochrones()

    if iso_gdf.empty:
        return JSONResponse(content={"type": "FeatureCollection", "features": []})

    def haversine(lat1, lon1, lat2, lon2):
        R = 6_371_000  # metres
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlam = math.radians(lon2 - lon1)
        a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    iso_gdf = iso_gdf.dropna(subset=["lat", "lon", "geometry"])

    distances = iso_gdf.apply(
        lambda row: haversine(point.lat, point.lng, row["lat"], row["lon"]),
        axis=1,
    )

    closest_idx = distances.idxmin()
    closest_row = iso_gdf.loc[closest_idx]

    feature = {
        "type": "Feature",
        "geometry": closest_row.geometry.__geo_interface__,
        "properties": {
            "origin_node": int(closest_row["origin_node"]),
            "lat": float(closest_row["lat"]),
            "lon": float(closest_row["lon"]),
            "score": int(closest_row["score"]) if closest_row["score"] is not None else 0,
            "colour": str(closest_row["colour"]) if closest_row["colour"] else "#94a3b8",
            "distance_m": round(distances[closest_idx], 1),
        },
    }

    geojson = {"type": "FeatureCollection", "features": [feature]}
    return JSONResponse(content=geojson)


@app.get("/isochrone-pois/{origin_node}")
async def get_pois_for_isochrone(origin_node: int):
    """
    Given an origin_node, look up its isochrone polygon in DuckDB,
    then use ST_Within to find all POIs inside that polygon.
    Returns a GeoJSON FeatureCollection of POI points.
    """
    # Get the isochrone polygon from DuckDB
    iso = duckdb_layer.fetch_isochrone_by_node(origin_node)

    if iso is None:
        return JSONResponse(content={"type": "FeatureCollection", "features": []})

    polygon_wkt = iso["wkt"]

    # Query DuckDB for POIs inside this polygon
    pois = duckdb_layer.fetch_pois_in_polygon(polygon_wkt)

    features = []
    for poi in pois:
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [poi["lon"], poi["lat"]],
            },
            "properties": {
                "poi_id": poi["poi_id"],
                "name": poi["name"],
                "category": poi["category"],
                "subtype": poi["subtype"],
                "address": poi["address"],
            },
        })

    geojson = {"type": "FeatureCollection", "features": features}
    return JSONResponse(content=geojson)
