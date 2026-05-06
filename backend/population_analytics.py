import geopandas as gpd
import pandas as pd
import shapely.wkt
import sys
from pathlib import Path

# Add backend to path so we can import db
sys.path.insert(0, "d:/15-min-city-2/backend")
import db
import constants

def run_analysis():
    print("Fetching isochrones from DuckDB...")
    conn = db.get_conn()
    iso_rows = conn.execute("SELECT score, ST_AsText(geom) FROM isochrones").fetchall()
    
    polys = [shapely.wkt.loads(r[1]) for r in iso_rows]
    scores = [r[0] for r in iso_rows]
    
    iso_gdf = gpd.GeoDataFrame({"score": scores, "geometry": polys}, crs=constants.geographic_crs)
    print(f"Loaded {len(iso_gdf)} isochrones.")

    print("Loading population data...")
    pop_path = Path("d:/15-min-city-2/files/pune_population.gpkg")
    pop_gdf = gpd.read_file(pop_path)
    print(f"Loaded {len(pop_gdf)} population hexes.")

    print("Reprojecting...")
    pop_gdf = pop_gdf.to_crs(iso_gdf.crs)
    
    # We want population hexagons as points (centroids) to make intersections cleaner
    # and faster, since hexes are small (400m)
    pop_gdf["geometry"] = pop_gdf.geometry.centroid

    print("Running spatial join (this may take a minute)...")
    joined = gpd.sjoin(pop_gdf, iso_gdf, how="left", predicate="within")

    print("Aggregating results...")
    # A point might fall into multiple overlapping isochrones. We want the best score.
    joined_max = joined.groupby(joined.index).agg({
        'population': 'first',
        'score': 'max'
    })

    # Population outside all isochrones defaults to 0 (car dependent)
    joined_max['score'] = joined_max['score'].fillna(0)

    score_dist = joined_max.groupby('score')['population'].sum()
    total_pop = score_dist.sum()

    print("\n" + "="*45)
    print("  POPULATION-BASED WALKABILITY DISTRIBUTION  ")
    print("="*45)
    for s in range(6, -1, -1):
        pop = score_dist.get(s, 0)
        pct = (pop / total_pop) * 100
        print(f"Score {s}: {pct:5.1f}% | {pop:10,.0f} people")
    print("="*45)
    print(f"Total Analyzed Population: {total_pop:,.0f}")

if __name__ == '__main__':
    run_analysis()
