"""
DuckDB spatial database layer for the 15-Minute City Auditor.

Tables:
  - nodes:       node_id, lat, lon, grocery_time, accessible
  - pois:        poi_id, name, category, subtype, lat, lon, address, geom (POINT)
  - isochrones:  origin_node, lat, lon, score, colour, geom (POLYGON)

Requires: duckdb >= 1.1.0 with the spatial extension.
"""

import json
import duckdb
import backend.constants as constants

# ── Persistent read-only connection (opened once at API startup) ───────────────
_persistent_conn: duckdb.DuckDBPyConnection | None = None


def init_persistent_conn() -> None:
    """Open the singleton read-only connection. Called once at app startup."""
    global _persistent_conn
    _persistent_conn = duckdb.connect(str(constants.DUCKDB_PATH), read_only=True)
    _persistent_conn.load_extension("spatial")


def close_persistent_conn() -> None:
    """Close the singleton connection. Called at app shutdown."""
    global _persistent_conn
    if _persistent_conn is not None:
        _persistent_conn.close()
        _persistent_conn = None


def get_conn() -> duckdb.DuckDBPyConnection:
    """
    Return the persistent read-only connection (safe while API is running).
    Falls back to creating a new one if not yet initialised.
    Callers must NOT call .close() on this connection.
    """
    if _persistent_conn is not None:
        return _persistent_conn
    # Fallback (e.g. when called from a script, not from the API)
    conn = duckdb.connect(str(constants.DUCKDB_PATH), read_only=True)
    conn.load_extension("spatial")
    return conn


def get_write_conn() -> duckdb.DuckDBPyConnection:
    """
    Return a read-write DuckDB connection.
    IMPORTANT: The API server must NOT be running when this is used,
    as DuckDB only allows one writer at a time.
    Callers MUST call .close() when done.
    """
    conn = duckdb.connect(str(constants.DUCKDB_PATH), read_only=False)
    conn.install_extension("spatial")
    conn.load_extension("spatial")
    return conn


# ── Schema init ────────────────────────────────────────────────────────────────


def init_db():
    """Create tables if they don't exist (requires write access)."""
    conn = get_write_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS pois (
            poi_id    INTEGER PRIMARY KEY DEFAULT(nextval('poi_seq')),
            name      TEXT,
            category  TEXT,
            subtype   TEXT,
            lat       DOUBLE,
            lon       DOUBLE,
            address   TEXT,
            geom      GEOMETRY
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS isochrones (
            origin_node  BIGINT PRIMARY KEY,
            lat          DOUBLE,
            lon          DOUBLE,
            score        INTEGER,
            colour       TEXT,
            geom         GEOMETRY
        )
    """)
    conn.close()


def _safe_init():
    """Create sequence + tables + indexes idempotently (requires write access)."""
    conn = get_write_conn()

    try:
        conn.execute("CREATE SEQUENCE poi_seq START 1")
    except duckdb.CatalogException:
        pass  # already exists

    conn.execute("""
        CREATE TABLE IF NOT EXISTS nodes (
            node_id      BIGINT PRIMARY KEY,
            lat          DOUBLE,
            lon          DOUBLE,
            grocery_time DOUBLE,
            accessible   BOOLEAN
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS pois (
            poi_id    INTEGER PRIMARY KEY DEFAULT(nextval('poi_seq')),
            name      TEXT,
            category  TEXT,
            subtype   TEXT,
            lat       DOUBLE,
            lon       DOUBLE,
            address   TEXT,
            geom      GEOMETRY
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS isochrones (
            origin_node  BIGINT PRIMARY KEY,
            lat          DOUBLE,
            lon          DOUBLE,
            score        INTEGER,
            colour       TEXT,
            geom         GEOMETRY
        )
    """)

    # Indexes
    conn.execute("CREATE INDEX IF NOT EXISTS idx_pois_category ON pois (category)")
    try:
        conn.execute("CREATE INDEX IF NOT EXISTS idx_pois_geom ON pois USING RTREE (geom)")
    except Exception:
        pass  # spatial extension may not support RTREE in this build
    try:
        conn.execute("CREATE INDEX IF NOT EXISTS idx_iso_geom ON isochrones USING RTREE (geom)")
    except Exception:
        pass

    conn.close()


# ── Nodes ──────────────────────────────────────────────────────────────────────


def insert_nodes(rows: list[dict]) -> int:
    """Insert walking-network node rows. Each row: node_id, lat, lon, grocery_time, accessible."""
    _safe_init()
    conn = get_write_conn()
    conn.execute("DELETE FROM nodes")
    conn.executemany(
        "INSERT INTO nodes (node_id, lat, lon, grocery_time, accessible) VALUES (?, ?, ?, ?, ?)",
        [
            (int(r["node_id"]), float(r["lat"]), float(r["lon"]),
             float(r["grocery_time"]), bool(r["accessible"]))
            for r in rows
        ],
    )
    count = conn.execute("SELECT count(*) FROM nodes").fetchone()[0]
    conn.close()
    return count


def fetch_nodes() -> list[dict]:
    """Return all walking-network nodes. Returns [] if table doesn't exist yet."""
    conn = get_conn()
    try:
        results = conn.execute(
            "SELECT lat, lon, grocery_time, accessible FROM nodes"
        ).fetchall()
        return [
            {"lat": r[0], "lon": r[1], "grocery_time": r[2], "accessible": bool(r[3])}
            for r in results
        ]
    except Exception:
        return []


# ── Insert helpers ─────────────────────────────────────────────────────────────


def insert_pois(rows: list[dict]):
    """Insert POI rows. Each row: name, category, subtype, lat, lon, address, wkt."""
    _safe_init()
    conn = get_write_conn()
    conn.execute("DELETE FROM pois")
    conn.execute("""
        CREATE OR REPLACE TEMP TABLE _pois_stage (
            name TEXT, category TEXT, subtype TEXT,
            lat DOUBLE, lon DOUBLE, address TEXT, wkt TEXT
        )
    """)
    conn.executemany(
        "INSERT INTO _pois_stage VALUES (?, ?, ?, ?, ?, ?, ?)",
        [
            (
                str(r["name"]) if r["name"] else "",
                str(r["category"]),
                str(r["subtype"]),
                float(r["lat"]),
                float(r["lon"]),
                str(r["address"]) if r["address"] else "",
                str(r["wkt"]),
            )
            for r in rows
        ],
    )
    try:
        conn.execute("DROP SEQUENCE poi_seq")
        conn.execute("CREATE SEQUENCE poi_seq START 1")
    except Exception:
        pass
    conn.execute("""
        INSERT INTO pois (poi_id, name, category, subtype, lat, lon, address, geom)
        SELECT nextval('poi_seq'), name, category, subtype, lat, lon, address,
               ST_GeomFromText(wkt)
        FROM _pois_stage
    """)
    conn.execute("DROP TABLE _pois_stage")
    count = conn.execute("SELECT count(*) FROM pois").fetchone()[0]
    conn.close()
    return count


def insert_isochrones(rows: list[dict]):
    """Insert isochrone rows. Each row: origin_node, lat, lon, score, colour, wkt."""
    _safe_init()
    conn = get_write_conn()
    conn.execute("DELETE FROM isochrones")
    conn.execute("""
        CREATE OR REPLACE TEMP TABLE _iso_stage (
            origin_node BIGINT, lat DOUBLE, lon DOUBLE,
            score INTEGER, colour TEXT, wkt TEXT
        )
    """)
    conn.executemany(
        "INSERT INTO _iso_stage VALUES (?, ?, ?, ?, ?, ?)",
        [
            (
                int(r["origin_node"]),
                float(r["lat"]),
                float(r["lon"]),
                int(r["score"]) if r["score"] is not None else 0,
                str(r["colour"]) if r["colour"] else "#94a3b8",
                str(r["wkt"]),
            )
            for r in rows
        ],
    )
    conn.execute("""
        INSERT INTO isochrones (origin_node, lat, lon, score, colour, geom)
        SELECT origin_node, lat, lon, score, colour, ST_GeomFromText(wkt)
        FROM _iso_stage
    """)
    conn.execute("DROP TABLE _iso_stage")
    count = conn.execute("SELECT count(*) FROM isochrones").fetchone()[0]
    conn.close()
    return count


# ── Query helpers ──────────────────────────────────────────────────────────────


def fetch_all_isochrones_geojson() -> dict:
    """
    Return all isochrones as a GeoJSON FeatureCollection for the background heatmap.
    Uses the DB — no file reads.
    """
    conn = get_conn()
    results = conn.execute("""
        SELECT origin_node, lat, lon, score, colour, ST_AsGeoJSON(geom) as geojson
        FROM isochrones
        ORDER BY score ASC
    """).fetchall()

    features = []
    for r in results:
        geom_json = json.loads(r[5]) if r[5] else None
        if geom_json is None:
            continue
        features.append({
            "type": "Feature",
            "geometry": geom_json,
            "properties": {
                "origin_node": r[0],
                "lat": r[1],
                "lon": r[2],
                "score": r[3],
                "color": r[4],   # frontend uses 'color' key for polygon styling
                "colour": r[4],
            },
        })
    return {"type": "FeatureCollection", "features": features}


def fetch_pois_in_polygon(polygon_wkt: str) -> list[dict]:
    """Return all POIs inside a polygon using ST_Within."""
    conn = get_conn()
    results = conn.execute(
        """
        SELECT poi_id, name, category, subtype, lat, lon, address
        FROM pois
        WHERE ST_Within(geom, ST_GeomFromText(?))
        ORDER BY category, name
        """,
        [polygon_wkt],
    ).fetchall()
    return [
        {
            "poi_id": r[0], "name": r[1], "category": r[2],
            "subtype": r[3], "lat": r[4], "lon": r[5], "address": r[6],
        }
        for r in results
    ]


def fetch_poi_summary_for_node(origin_node: int) -> dict:
    """
    Return count of POIs per category for a given isochrone (no coordinates).
    Returns e.g. {"grocery": 3, "park": 1, "total": 4}
    """
    conn = get_conn()
    iso = conn.execute(
        "SELECT ST_AsText(geom) FROM isochrones WHERE origin_node = ?",
        [origin_node],
    ).fetchone()
    if iso is None:
        return {"total": 0}

    results = conn.execute(
        """
        SELECT category, count(*) as cnt
        FROM pois
        WHERE ST_Within(geom, ST_GeomFromText(?))
        GROUP BY category
        ORDER BY category
        """,
        [iso[0]],
    ).fetchall()

    summary = {r[0]: r[1] for r in results}
    summary["total"] = sum(summary.values())
    return summary


def fetch_isochrone_by_node(origin_node: int) -> dict | None:
    """Fetch a single isochrone row by origin_node."""
    conn = get_conn()
    row = conn.execute(
        """
        SELECT origin_node, lat, lon, score, colour, ST_AsText(geom) as wkt
        FROM isochrones WHERE origin_node = ?
        """,
        [origin_node],
    ).fetchone()
    if row is None:
        return None
    return {
        "origin_node": row[0], "lat": row[1], "lon": row[2],
        "score": row[3], "colour": row[4], "wkt": row[5],
    }


def fetch_nearest_isochrone(lat: float, lon: float) -> dict | None:
    """Find the nearest isochrone centroid to a given lat/lon via ST_Distance."""
    conn = get_conn()
    row = conn.execute(
        """
        SELECT origin_node, lat, lon, score, colour,
               ST_AsText(geom) as wkt,
               ST_Distance(ST_Point(lon, lat), ST_Point(?, ?)) AS dist
        FROM isochrones
        ORDER BY dist ASC
        LIMIT 1
        """,
        [lon, lat],
    ).fetchone()
    if row is None:
        return None
    return {
        "origin_node": row[0], "lat": row[1], "lon": row[2],
        "score": row[3], "colour": row[4], "wkt": row[5],
        "distance_deg": row[6],
    }


# ── CLI ────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    _safe_init()
    conn = get_write_conn()
    pois_count = conn.execute("SELECT count(*) FROM pois").fetchone()[0]
    iso_count = conn.execute("SELECT count(*) FROM isochrones").fetchone()[0]
    conn.close()
    print(f"DuckDB ready at {constants.DUCKDB_PATH}")
    print(f"  pois:       {pois_count} rows")
    print(f"  isochrones: {iso_count} rows")
