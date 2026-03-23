import osmnx as ox
import geopandas as gpd
from geopandas import GeoDataFrame
import pandas as pd
import backend.constants as constants

# POIS
pois = {
    "grocery": {
        "shop": ["supermarket", "convenience"]
    },

    "healthcare": {
        "amenity": ["hospital", "clinic", "doctors"]
    },

    "pharmacy": {
        "amenity": "pharmacy"
    },

    "school": {
        "amenity": "school"
    },

    "park": {
        "leisure": "park"
    },

    "public_transport": {
        "highway": "bus_stop",
        "railway": ["station", "halt"]
    }
}

def save_pois() -> GeoDataFrame:
    # the saved file is in PROJECTED crs  
    all_pois = []

    for key, value in pois.items():
        print(f"Fetching values for {key}...")
        gdf = ox.features_from_place(constants.CITY, tags=value)
        print(f"Fetched values for {key} successfully.")
        print("Converting crs")
        # ================================================
        gdf = gdf.to_crs(constants.projected_crs) # projected crs
        # ================================================
        gdf = gdf[gdf.geometry.type.isin(["Point", "Polygon", "MultiPolygon"])]
        # gdf["geometry"] = gdf.geometry.representative_point()
        gdf["geometry"] = gdf.geometry.centroid
        gdf["category"] = key
        all_pois.append(gdf)

    print("FINALLY DONE!!!")
    print("Converting to GDF")
    final_pois = gpd.GeoDataFrame(
        pd.concat(all_pois, ignore_index=True),
        crs=all_pois[0].crs
    )

    final_pois.to_file(constants.city_data_gpkg, layer="pois", driver="GPKG")
    print("Saved file successfully: {}".format(constants.city_data_gpkg))
    return final_pois
    
if __name__ == "__main__":
    # final_pois = save_pois()
    pass