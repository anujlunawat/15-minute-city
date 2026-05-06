import geopandas as gpd
import pandas as pd
import shapely.wkt
import sys
from pathlib import Path

# Add backend to path so we can import db
sys.path.insert(0, "d:/15-min-city-2/backend")
import db
import constants

def precompute_population():
    print("Fetching isochrones from DuckDB...")
    conn = db.get_conn()
    iso_rows = conn.execute("SELECT origin_node, ST_AsText(geom) FROM isochrones").fetchall()
    conn.close()
    
    nodes = [r[0] for r in iso_rows]
    polys = [shapely.wkt.loads(r[1]) for r in iso_rows]
    
    iso_gdf = gpd.GeoDataFrame({"origin_node": nodes, "geometry": polys}, crs=constants.geographic_crs)
    print(f"Loaded {len(iso_gdf)} isochrones.")

    pop_path = Path("d:/15-min-city-2/backend/pune_population.gpkg")
    print(f"Loading population from {pop_path}...")
    pop_gdf = gpd.read_file(pop_path)
    
    print("Reprojecting to UTM (EPSG:32643) for precise meter-level area calculations...")
    utm_crs = "EPSG:32643" # Pune is in UTM Zone 43N
    iso_gdf_utm = iso_gdf.to_crs(utm_crs)
    pop_gdf_utm = pop_gdf.to_crs(utm_crs)
    
    # Calculate the exact total area of each population hexagon
    pop_gdf_utm['hex_area'] = pop_gdf_utm.geometry.area

    print("Finding intersecting pairs using spatial index...")
    # 'intersects' finds any overlap, rather than just center points
    joined = gpd.sjoin(pop_gdf_utm, iso_gdf_utm, how="inner", predicate="intersects")
    
    print("Calculating exact proportional overlaps (this will take a minute)...")
    # For every pair, calculate exactly how much the isochrone covers the hexagon
    # We must ensure both are GeoSeries with identical indices for vectorized operations
    left_geoms = joined.geometry
    right_geoms_array = iso_gdf_utm.loc[joined['index_right']].geometry.values
    right_geoms = gpd.GeoSeries(right_geoms_array, index=left_geoms.index, crs=utm_crs)
    
    # Calculate the actual area of the overlap
    intersection_areas = left_geoms.intersection(right_geoms).area
    
    # Multiply the population by the percentage of the hexagon covered
    joined['proportional_pop'] = joined['population'] * (intersection_areas / joined['hex_area'])
    
    print("Aggregating exact population per node...")
    pop_per_node = joined.groupby('origin_node')['proportional_pop'].sum().round().astype(int).reset_index()
    pop_per_node.rename(columns={'proportional_pop': 'population'}, inplace=True)

    print("Writing to DuckDB...")
    # NOTE: This requires a write connection, so the Docker container MUST be stopped.
    import duckdb
    conn = duckdb.connect("d:/15-min-city-2/backend/accessibility_temp.duckdb", read_only=False)
    
    print("Adding population column to isochrones table...")
    try:
        conn.execute("ALTER TABLE isochrones ADD COLUMN IF NOT EXISTS population INTEGER")
    except Exception as e:
        print(f"Column might exist: {e}")
    
    print("Updating database...")
    # Load pandas dataframe to duckdb via temp table
    conn.execute("CREATE TEMP TABLE pop_update AS SELECT * FROM pop_per_node")
    conn.execute('''
        UPDATE isochrones 
        SET population = pop_update.population 
        FROM pop_update 
        WHERE isochrones.origin_node = pop_update.origin_node
    ''')
    
    # Fill remaining with 0
    conn.execute("UPDATE isochrones SET population = 0 WHERE population IS NULL")
    
    conn.close()
    print("Done! All populations precomputed and saved.")

if __name__ == '__main__':
    import warnings
    warnings.filterwarnings("ignore")
    precompute_population()
