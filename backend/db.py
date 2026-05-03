"""
DuckDB spatial database layer for POIs and isochrones.

Tables:
  - pois:        poi_id, name, category, subtype, lat, lon, address, geometry (POINT)
  - isochrones:  origin_node, lat, lon, score, colour, geometry (POLYGON)

Requires: duckdb >= 1.1.0 with the spatial extension.
"""

import duckdb
from pathlib import Path
from shapely.geometry import mapping
import backend.constants as constants


def get_conn() -> duckdb.DuckDBPyConnection:
    """Return a DuckDB connection with spatial loaded."""
    conn = duckdb.connect(str(constants.DUCKDB_PATH))
    conn.install_extension("spatial")
    conn.load_extension("spatial")
    return conn


def init_db():
    """Create tables if they don't exist."""
    conn = get_conn()

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
    """Create sequence + tables idempotently."""
    conn = get_conn()
    # Create the sequence if it doesn't exist
    try:
        conn.execute("CREATE SEQUENCE poi_seq START 1")
    except duckdb.CatalogException:
        pass  # already exists

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


# ── Insert helpers ──────────────────────────────────────────────


def insert_pois(rows: list[dict]):
    """
    Insert POI rows into DuckDB.

    Each row dict must have:
        name, category, subtype, lat, lon, address, wkt
    where wkt is the WKT string of the point geometry.
    """
    _safe_init()
    conn = get_conn()

    conn.execute("DELETE FROM pois")

    # Stage: insert into a temp table with wkt as TEXT, then convert
    conn.execute("""
        CREATE OR REPLACE TEMP TABLE _pois_stage (
            name      TEXT,
            category  TEXT,
            subtype   TEXT,
            lat       DOUBLE,
            lon       DOUBLE,
            address   TEXT,
            wkt       TEXT
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

    # Reset the sequence so IDs start fresh
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
    """
    Insert isochrone rows into DuckDB.

    Each row dict must have:
        origin_node, lat, lon, score, colour, wkt
    """
    _safe_init()
    conn = get_conn()

    conn.execute("DELETE FROM isochrones")

    conn.execute("""
        CREATE OR REPLACE TEMP TABLE _iso_stage (
            origin_node  BIGINT,
            lat          DOUBLE,
            lon          DOUBLE,
            score        INTEGER,
            colour       TEXT,
            wkt          TEXT
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


# ── Query helpers ───────────────────────────────────────────────


def fetch_pois_in_polygon(polygon_wkt: str) -> list[dict]:
    """
    Return all POIs whose point geometry falls inside the given polygon WKT.
    Uses DuckDB spatial ST_Within for fast R-tree filtering.
    """
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

    conn.close()

    return [
        {
            "poi_id": r[0],
            "name": r[1],
            "category": r[2],
            "subtype": r[3],
            "lat": r[4],
            "lon": r[5],
            "address": r[6],
        }
        for r in results
    ]


def fetch_isochrone_by_node(origin_node: int) -> dict | None:
    """Fetch a single isochrone row by origin_node."""
    conn = get_conn()

    row = conn.execute(
        """
        SELECT origin_node, lat, lon, score, colour, ST_AsText(geom) as wkt
        FROM isochrones
        WHERE origin_node = ?
        """,
        [origin_node],
    ).fetchone()

    conn.close()

    if row is None:
        return None

    return {
        "origin_node": row[0],
        "lat": row[1],
        "lon": row[2],
        "score": row[3],
        "colour": row[4],
        "wkt": row[5],
    }


def fetch_nearest_isochrone(lat: float, lon: float) -> dict | None:
    """Find the nearest isochrone to a given lat/lon using haversine in SQL."""
    conn = get_conn()

    row = conn.execute(
        """
        SELECT origin_node, lat, lon, score, colour,
               ST_AsText(geom) as wkt,
               ST_Distance(
                   ST_Point(lon, lat),
                   ST_Point(?, ?)
               ) AS dist
        FROM isochrones
        ORDER BY dist ASC
        LIMIT 1
        """,
        [lon, lat],
    ).fetchone()

    conn.close()

    if row is None:
        return None

    return {
        "origin_node": row[0],
        "lat": row[1],
        "lon": row[2],
        "score": row[3],
        "colour": row[4],
        "wkt": row[5],
        "distance_deg": row[6],
    }


# ── CLI ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    _safe_init()
    conn = get_conn()
    pois_count = conn.execute("SELECT count(*) FROM pois").fetchone()[0]
    iso_count = conn.execute("SELECT count(*) FROM isochrones").fetchone()[0]
    conn.close()
    print(f"DuckDB ready at {constants.DUCKDB_PATH}")
    print(f"  pois:       {pois_count} rows")
    print(f"  isochrones: {iso_count} rows")
