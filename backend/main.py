from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from shapely import wkt as shapely_wkt

import math

import backend.db as duckdb_layer
import backend.constants as constants
from backend.models import ClickPoint


# ── Helpers ────────────────────────────────────────────────────────────────────

def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Accurate haversine distance in metres."""
    R = 6_371_000
    φ1, φ2 = math.radians(lat1), math.radians(lat2)
    dφ = math.radians(lat2 - lat1)
    dλ = math.radians(lon2 - lon1)
    a = math.sin(dφ / 2) ** 2 + math.cos(φ1) * math.cos(φ2) * math.sin(dλ / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# ── App lifecycle ──────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Open one persistent read-only DuckDB connection for the life of the server."""
    duckdb_layer.init_persistent_conn()
    yield
    duckdb_layer.close_persistent_conn()


app = FastAPI(
    title="15-Minute City Auditor",
    description="Pune walkability explorer API",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Endpoints ──────────────────────────────────────────────────────────────────

@app.get("/")
def health():
    return {"status": "connected", "version": "2.0.0"}


@app.get("/nodes")
def get_nodes():
    try:
        return duckdb_layer.fetch_nodes()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database error: {e}")


@app.get("/polygon-accessibility")
def get_polygon_accessibility():
    """
    Return all isochrone polygons as a GeoJSON FeatureCollection.
    Fetched from DuckDB — no file I/O on every request.
    """
    try:
        return duckdb_layer.fetch_all_isochrones_geojson()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database error: {e}")


@app.post("/isochrone")
async def get_nearest_isochrone(point: ClickPoint):
    """
    Given a clicked lat/lng, find the closest pre-computed isochrone polygon
    using DuckDB ST_Distance. Returns a GeoJSON FeatureCollection.
    """
    try:
        iso = duckdb_layer.fetch_nearest_isochrone(point.lat, point.lng)
        if iso is None:
            return JSONResponse(content={"type": "FeatureCollection", "features": []})

        polygon = shapely_wkt.loads(iso["wkt"])
        distance_m = round(_haversine_m(point.lat, point.lng, iso["lat"], iso["lon"]), 1)

        feature = {
            "type": "Feature",
            "geometry": polygon.__geo_interface__,
            "properties": {
                "origin_node": int(iso["origin_node"]),
                "lat": float(iso["lat"]),
                "lon": float(iso["lon"]),
                "score": int(iso["score"]) if iso["score"] is not None else 0,
                "colour": str(iso["colour"]) if iso["colour"] else "#94a3b8",
                "distance_m": distance_m,
            },
        }
        return JSONResponse(content={"type": "FeatureCollection", "features": [feature]})
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database error: {e}")


@app.get("/isochrone-pois/{origin_node}")
async def get_pois_for_isochrone(origin_node: int):
    """
    Return all POIs inside the isochrone polygon as a GeoJSON FeatureCollection.
    Uses DuckDB ST_Within.
    """
    try:
        iso = duckdb_layer.fetch_isochrone_by_node(origin_node)
        if iso is None:
            return JSONResponse(content={"type": "FeatureCollection", "features": []})

        pois = duckdb_layer.fetch_pois_in_polygon(iso["wkt"])
        features = [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [poi["lon"], poi["lat"]]},
                "properties": {
                    "poi_id": poi["poi_id"],
                    "name": poi["name"],
                    "category": poi["category"],
                    "subtype": poi["subtype"],
                    "address": poi["address"],
                },
            }
            for poi in pois
        ]
        return JSONResponse(content={"type": "FeatureCollection", "features": features})
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database error: {e}")


@app.get("/isochrone-pois/{origin_node}/summary")
async def get_poi_summary(origin_node: int):
    """
    Return POI count per category for a given isochrone — no coordinates.
    e.g. {"grocery": 3, "park": 1, "total": 4}
    """
    try:
        summary = duckdb_layer.fetch_poi_summary_for_node(origin_node)
        return JSONResponse(content=summary)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database error: {e}")
