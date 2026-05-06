import geopandas as gpd
from pathlib import Path
import os
import sys

def process():
    root = Path("d:/15-min-city-2/files")
    kontur_path = root / "kontur_population_IN_20231101.gpkg"
    boundary_path = root / "files/pune_boundary.geojson"
    output_path = root / "files/pune_population.gpkg"

    if output_path.exists():
        print("Pune population file already exists. Skipping clipping.")
        return

    print("Loading Pune boundary...")
    boundary_gdf = gpd.read_file(boundary_path)
    # Kontur is usually EPSG:3857, let's load boundary and project it to match
    print("Loading Kontur India population (using bbox to save RAM)...")
    
    # We don't know kontur crs beforehand, let's read one row to check
    sample = gpd.read_file(kontur_path, rows=1)
    target_crs = sample.crs
    
    boundary_gdf = boundary_gdf.to_crs(target_crs)
    bbox = tuple(boundary_gdf.total_bounds)
    
    pop_gdf = gpd.read_file(kontur_path, bbox=bbox)
    
    print("Clipping exactly to boundary...")
    pune_pop = pop_gdf.clip(boundary_gdf)
    
    print(f"Total Pune Population Extracted: {pune_pop['population'].sum():,}")
    
    print("Saving to pune_population.gpkg...")
    pune_pop.to_file(output_path, driver="GPKG")
    print("Done!")

if __name__ == '__main__':
    process()
