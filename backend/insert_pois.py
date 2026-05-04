"""
Read POIs and isochrones from .gpkg files and insert into DuckDB.

Usage:
    python -m backend.insert_pois          # insert both POIs and isochrones
    python -m backend.insert_pois --pois   # insert only POIs
    python -m backend.insert_pois --iso    # insert only isochrones
"""

import sys
import geopandas as gpd
from geopandas import GeoDataFrame
from pyproj import CRS
import backend.constants as constants
import backend.db as db


# ── POI category / subtype resolution ───────────────────────────

CATEGORY_MAP = {
    "grocery":          {"shop": ["supermarket", "convenience"]},
    "healthcare":       {"amenity": ["hospital", "clinic", "doctors"]},
    "pharmacy":         {"amenity": ["pharmacy"]},
    "school":           {"amenity": ["school"]},
    "park":             {"leisure": ["park"]},
    "public_transport": {"highway": ["bus_stop"], "railway": ["station", "halt"]},
}


def _resolve_category_subtype(row) -> tuple[str, str]:
    """
    Given a GeoDataFrame row, figure out (category, subtype)
    by checking the OSM tag columns.
    """
    for category, tag_dict in CATEGORY_MAP.items():
        for tag_col, allowed_values in tag_dict.items():
            val = row.get(tag_col)
            if isinstance(val, str) and val in allowed_values:
                return category, val
    return "other", "other"


def _resolve_subtype_from_category(row, category: str) -> str:
    """Fallback subtype resolution when category is already known."""
    tag_dict = CATEGORY_MAP.get(category, {})
    for tag_col, allowed_values in tag_dict.items():
        val = row.get(tag_col)
        if isinstance(val, str) and val in allowed_values:
            return val
    return category


def _get_address(row) -> str:
    """Build a single address string from addr:* columns."""
    parts = []
    for col in ("addr:housename", "addr:housenumber", "addr:street", "addr:city"):
        val = row.get(col)
        if isinstance(val, str) and val.strip():
            parts.append(val.strip())
    return ", ".join(parts) if parts else ""


def _get_name(row, subtype: str) -> str:
    """Get the best name for a POI."""
    name = row.get("name")
    if isinstance(name, str) and name.strip():
        return name.strip()
    name_en = row.get("name:en")
    if isinstance(name_en, str) and name_en.strip():
        return name_en.strip()
    return subtype.replace("_", " ").title()


# ── Insert POIs ─────────────────────────────────────────────────

def load_and_insert_pois():
    """
    Read from files/pois(representative_points).gpkg → insert to DuckDB.
    The file may be in projected CRS, so we convert to geographic.
    """
    gpkg_path = constants.FILES_FOLDER / "pois(representative_points).gpkg"

    print(f"Reading POIs from {gpkg_path} ...")
    gdf: GeoDataFrame = gpd.read_file(gpkg_path)
    print(f"  Loaded {len(gdf)} raw rows, CRS = {gdf.crs}")

    # Ensure geographic CRS (lat/lon)
    if CRS(gdf.crs).is_projected:
        print("  Converting from projected to geographic CRS ...")
        gdf = gdf.to_crs(constants.geographic_crs)

    # Ensure all geometries are points (use centroid if not)
    non_point = ~gdf.geometry.type.isin(["Point"])
    if non_point.any():
        print(f"  Converting {non_point.sum()} non-point geometries to centroids ...")
        gdf.loc[non_point, "geometry"] = gdf.loc[non_point].geometry.centroid

    # Build insert rows
    rows = []
    skipped = 0
    for _, row in gdf.iterrows():
        geom = row.geometry
        if geom is None or geom.is_empty:
            skipped += 1
            continue

        category, subtype = _resolve_category_subtype(row)
        if category == "other":
            # The gpkg may already have a 'category' column from save_pois.py
            cat = row.get("category")
            if isinstance(cat, str) and cat.strip():
                category = cat.strip()
                subtype = _resolve_subtype_from_category(row, category)

        name = _get_name(row, subtype)
        address = _get_address(row)

        rows.append({
            "name": name,
            "category": category,
            "subtype": subtype,
            "lat": float(geom.y),
            "lon": float(geom.x),
            "address": address,
            "wkt": geom.wkt,
        })

    print(f"  Prepared {len(rows)} POI rows ({skipped} skipped)")
    count = db.insert_pois(rows)
    print(f"  ✓ Inserted {count} POIs into DuckDB")
    return count


# ── Insert isochrones ──────────────────────────────────────────

def load_and_insert_isochrones():
    """
    Read isochrones from files/gpkg/isochrones.gpkg
    layer="isochrones_polygons_final" (geographic CRS) → insert to DuckDB.
    """
    gpkg_path = constants.FILES_FOLDER / "gpkg" / "isochrones.gpkg"
    layer = "isochrones_polygons_final"

    print(f"Reading isochrones from {gpkg_path} layer={layer} ...")
    iso_gdf: GeoDataFrame = gpd.read_file(gpkg_path, layer=layer)
    print(f"  Loaded {len(iso_gdf)} rows, CRS = {iso_gdf.crs}")

    if iso_gdf.empty:
        print("  ⚠ No isochrones found. Skipping.")
        return 0

    # Ensure geographic CRS
    if CRS(iso_gdf.crs).is_projected:
        print("  Converting to geographic CRS ...")
        iso_gdf = iso_gdf.to_crs(constants.geographic_crs)

    # Check what columns exist
    print(f"  Columns: {list(iso_gdf.columns)}")

    rows = []
    for _, row in iso_gdf.iterrows():
        geom = row.geometry
        if geom is None or geom.is_empty:
            continue

        # Try to get lat/lon from columns or from geometry centroid
        lat = row.get("lat")
        lon = row.get("lon")
        if lat is None or lon is None:
            centroid = geom.centroid
            lat = float(centroid.y)
            lon = float(centroid.x)

        rows.append({
            "origin_node": int(row["origin_node"]),
            "lat": float(lat),
            "lon": float(lon),
            "score": int(row["score"]) if row.get("score") is not None else 0,
            "colour": str(row["colour"]) if row.get("colour") else "#94a3b8",
            "wkt": geom.wkt,
        })

    print(f"  Prepared {len(rows)} isochrone rows")
    count = db.insert_isochrones(rows)
    print(f"  ✓ Inserted {count} isochrones into DuckDB")
    return count


# ── CLI ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    args = sys.argv[1:]

    if not args or "--pois" in args:
        load_and_insert_pois()

    if not args or "--iso" in args:
        load_and_insert_isochrones()

    # Show summary
    conn = db.get_conn()
    pois_n = conn.execute("SELECT count(*) FROM pois").fetchone()[0]
    iso_n = conn.execute("SELECT count(*) FROM isochrones").fetchone()[0]
    conn.close()
    print(f"\nDuckDB summary ({constants.DUCKDB_PATH}):")
    print(f"  pois:       {pois_n}")
    print(f"  isochrones: {iso_n}")
