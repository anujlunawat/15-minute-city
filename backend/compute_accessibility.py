import geopandas as gpd
import pandas as pd
from geopandas import GeoDataFrame, GeoSeries
import shapely
from shapely.geometry import Point
from shapely.prepared import prep
import osmnx as ox
import networkx as nx
from networkx import MultiDiGraph
import json
from pathlib import Path
from pyproj import CRS
import backend.constants as constants
import database

ESSENTIAL_POIS = {
    "grocery": {"shop": ["supermarket", "convenience"]},
    "healthcare": {"amenity": ["hospital", "clinic", "doctors"]},
    "pharmacy": {"amenity": "pharmacy"},
    "school": {"amenity": "school"},
    "park": {"leisure": "park"},
    "public_transport": {"highway": "bus_stop", "railway": ["station", "halt"]},
}

ACCESSIBILITY_COLOR_SCALE = [
    (0, "#a50026"),
    (1, "#d73027"), 
    (2, "#f46d43"),
    (3, "#fdae61"),
    (4, "#fee08b"),
    (5, "#66bd63"),
    (6, "#1a9850"),
]


def build_graph(fp) -> MultiDiGraph:
    G = ox.load_graphml(fp)

    for u, v, k, data in G.edges(data=True, keys=True):
        data["travel_time"] = data["length"] / constants.WALKING_SPEED

    return G


def _as_list(value):
    if isinstance(value, list):
        return value
    return [value]


def _write_geojson(output_path: Path, payload: dict) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload), encoding="utf-8")


def _build_category_table(joined: GeoDataFrame):
    category_table = (
    joined.groupby(["origin_node", "category"])
    .size()
    .unstack(fill_value=0)
)

    category_table["score"] = (category_table > 0).sum(axis=1)
    category_table = category_table.reset_index()
    return category_table


def _access_colour(score):
    for s, clr in ACCESSIBILITY_COLOR_SCALE:
        if score == s:
            return clr
        
    return "#ffffff"


def build_polygon_accessibility(
    isochrone_gdf: GeoDataFrame,
    pois_gdf: GeoDataFrame,
    # origins: GeoSeries
):
    # sjoin in GeoPandas only requires that both GeoDataFrames have the same CRS. It does not care which CRS it is, as long as they match.
    try:
        assert CRS(isochrone_gdf.crs) == CRS(pois_gdf.crs)
        
        joined: GeoDataFrame = gpd.sjoin(
            isochrone_gdf,
            pois_gdf,
            how="left",
            predicate="contains" 
        )
        
        category_table: pd.DataFrame = _build_category_table(joined)

        isochrone_final = isochrone_gdf.merge(
            category_table[["origin_node", "score"]],
            on="origin_node",
            how="left"
        ).fillna(0)

        isochrone_final["score"] = isochrone_final["score"].astype("Int64")
        isochrone_final["colour"] = isochrone_final["score"].apply(lambda s: _access_colour(s))
        # assert isinstance(isochrone_final, GeoDataFrame)
        isochrone_final.to_file(filename=constants.isochones_gpkg, layer="isochrones_final", driver="GPKG")

        isochrone_json = isochrone_final.iloc[:500, :].to_json()
        isochrone_json = json.loads(isochrone_json)
        _write_geojson(constants.FILES_FOLDER / "isochrone_final.json", isochrone_json)
        # database.save_isochrones(isochrone_json)


    except Exception as e:
        print("ERROR:", e)




if __name__ == "__main__":
    # origins_gdf = GeoDataFrame.from_file(filename=config.gpkg_fp, layer="origins")
    # G_latlon = build_graph(config.FILES_FOLDER / "pune_walk.graphml")
    # G_proj = ox.project_graph(G_latlon, to_crs=config.projected_crs) 

    # origins_proj: GeoSeries = origins_gdf.geometry


    # Create empty GeoDataFrame with correct schema
    # empty_gdf = gpd.GeoDataFrame(
    #     {
    #         "origin_node": [],
    #         "geometry": []
    #     },
    #     geometry="geometry",
    #     crs=config.projected_crs
    # )

    # # Save once to create the layer
    # empty_gdf.to_file(
    #     config.gpkg_fp,
    #     layer="isochrones",
    #     driver="GPKG",
    #     mode="w"
    # )

    # isochrone_polys = calc_isochrone_from_origin(G_proj, origins_proj)
        # creates a geodf with 2 cols: origin_node and its geometry
    # isochrone_gdf:GeoDataFrame = GeoDataFrame.from_dict(
    #     isochrone_polys,
    #     orient="index",
    #     columns=["geometry"],
    #     crs=config.projected_crs
    # ).reset_index().rename(columns={"index": "origin_node"})

    # isochrone_gdf.to_file(filename=config.gpkg_fp, layer="isochrones")


    # isochrone_polys is projected
    # isochrone_gdf_proj: GeoDataFrame = GeoDataFrame.from_file(filename=config.gpkg_fp, layer="isochrones")
    # isochrone_gdf_proj: GeoDataFrame = GeoDataFrame.from_file(filename=config.city_data_gpkg, layer="isochrones_concave_hull")
    # print(isochrone_gdf_proj.crs)
    # isochrone_gdf_proj['origin_node'] = isochrone_gdf_proj['origin_node'].astype('Int64')  # convert the node IDs to int (rn, they were floats)
    # isochrone_gdf_latlon = isochrone_gdf_proj.to_crs(config.geographic_crs)

    # pois_gdf_proj = GeoDataFrame.from_file(filename=config.city_data_gpkg, layer="pois").to_crs(config.projected_crs)
    # pois_gdf_latlon = pois_gdf_proj.to_crs(config.geographic_crs)

    # # origins_latlon: GeoSeries = origins_proj.to_crs(config.geographic_crs)

    # build_polygon_accessibility(
    #     isochrone_gdf=isochrone_gdf_latlon,
    #     pois_gdf=pois_gdf_latlon,
    #     # origins=origins_latlon
    # )


    # geographic crs
    isochrone_gdf_geog: GeoDataFrame = GeoDataFrame.from_file(filename=constants.gpkg_folder / "gpkg" / "isochrones.gpkg", layer="isochrones_polygons_origin")
    print(isochrone_gdf_geog.crs)
    # isochrone_gdf_proj['origin_node'] = isochrone_gdf_proj['origin_node'].astype('Int64')  # convert the node IDs to int (rn, they were floats)

    pois_gdf_proj = GeoDataFrame.from_file(filename=constants.city_data_gpkg, layer="pois")
    print(pois_gdf_proj.crs)
    pois_gdf_latlon = pois_gdf_proj.to_crs(constants.geographic_crs)

    # origins_latlon: GeoSeries = origins_proj.to_crs(config.geographic_crs)

    build_polygon_accessibility(
        isochrone_gdf=isochrone_gdf_geog,
        pois_gdf=pois_gdf_latlon,
        # origins=origins_latlon
    )




    # print("FETCHING ESSENTIAL POIS")
    # all_pois = fetch_essential_pois(config.CITY, target_crs=iso_gdf.crs)
    # print("BUILDING POLYGON ACCESSIBILITY GEOJSON")
    # polygon_accessibility_geojson = build_polygon_accessibility_geojson(
    #     iso_gdf=iso_gdf,
    #     origins=origins,
    #     all_pois=all_pois,
    # )
    # print(
    #     f"Saved {len(polygon_accessibility_geojson['features'])} polygon features to "
    #     f"{ACCESSIBILITY_OUTPUT}"
    # )
