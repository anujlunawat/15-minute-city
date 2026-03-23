"""
Here, we create two version
"""


import osmnx as ox
import networkx as nx
from networkx import MultiDiGraph
import geopandas as gpd
from geopandas import GeoDataFrame, GeoSeries
from shapely.geometry import MultiPoint, MultiPolygon, Polygon, LineString, MultiLineString, Point
from shapely import concave_hull
from pyproj import CRS
from pandas.api.types import is_integer_dtype
import constants as constants
from compute_accessibility import build_graph
from database import save_isochrones

# ===================================== EDGES METHOD ===========================================

def compute_isochrone_edges(G: MultiDiGraph, origins: GeoSeries):
    # edges method
    
    # Ensure graph is projected
    if not ox.projection.is_projected(G.graph['crs']):
        G = ox.project_graph(G)
    
    if not origins.crs.is_projected:
        origins = origins.to_crs(constants.projected_crs)

    origin_nodes = ox.distance.nearest_nodes(G, origins.x, origins.y)
    origin_nodes = list(set(origin_nodes))
    print(f"ORIGIN NODES: {len(origin_nodes)}")

    edges_gdf = ox.graph_to_gdfs(G, nodes=False)
    u_index = edges_gdf.index.get_level_values(0)
    v_index = edges_gdf.index.get_level_values(1)

    # coords = {}
    isochrone_polys = {}
    count = 0
    # node, here, is an int
    batch = []

    for node in origin_nodes:
        count += 1
        try:
            times = nx.single_source_dijkstra_path_length(G, node, weight='travel_time', cutoff=constants.MAX_ACCESS_TIME)
            # reachable_nodes =   [n for n, t in times.items() if t <=config.MAX_ACCESS_TIME]
            reachable_nodes = set(times.keys())
            if len(reachable_nodes) == 0: 
                isochrone_polys[node] = []
                continue

            # subgraph = G.subgraph(reachable_nodes)
            # we get multiple edges from this subgraph
            # edges = ox.graph_to_gdfs(subgraph, nodes=False)
            mask = u_index.isin(reachable_nodes)
            mask &= v_index.isin(reachable_nodes)
            subedges = edges_gdf.loc[mask]

            if subedges.empty:
                continue
            # edges.buffer(): widens the edges.
            buffered = subedges.buffer(25)  # 25 meters
            # we stitch the edges together to form an (isochrone) polygon
            isochrone_poly = buffered.union_all()  # type Polygon
            # isochrone_polys.append(isochrone_poly)
            isochrone_polys[node] = isochrone_poly
            batch.append({"origin_node": node, "geometry": isochrone_poly})

            try:
                if not len(batch) % 100: 
                    print(f"COUNT: {count}")
                    batch_gdf = gpd.GeoDataFrame(batch, crs=constants.projected_crs)
                    batch_gdf.to_file(constants.city_data_gpkg, layer="isochrones_edges_base",
                                driver="GPKG", mode="a")
                    batch = []  # clear batch
                    print("APPENDED TO FILE SUCCESSFULLY!")

            except Exception as e:
                with open("log.txt", "a") as f:
                    f.write(f"{count=}\tCOULDN'T APPEND TO FILE. ERROR:{e}",)
                print("COULDN'T APPEND TO FILE. ERROR:", e)

        except Exception as e:
            print("ERROR:", e)

    if batch:
        batch_gdf = gpd.GeoDataFrame(batch, crs=constants.projected_crs)
        batch_gdf.to_file(constants.city_data_gpkg, layer="isochrones_edges_base",
                    driver="GPKG", mode="a")
    return isochrone_polys


# ===================================== CONCAVE HULL METHOD ===========================================

def compute_isochrone_polygons(G: MultiDiGraph, origins: GeoSeries):
    # the .gpkg file is saved in PROJECTED crs

    # Ensure graph is projected
    if not ox.projection.is_projected(G.graph['crs']):
        G = ox.project_graph(G) 

    origin_nodes = ox.distance.nearest_nodes(G, origins.x, origins.y)
    origin_nodes = list(set(origin_nodes))
    print(f"ORIGIN NODES: {len(origin_nodes)}")

    temp = gpd.GeoDataFrame(
        {"origin_node": []},          # attribute columns
        geometry=[],                  # geometry column
        crs=constants.projected_crs
    )

    temp.to_file(
        constants.FILES_FOLDER / "city_data.gpkg",
        layer="isochrones_polygons_base",
        driver="GPKG"
    )

    # coords = {}
    isochrone_polys = {}
    count = 0
    # node, here, is an int
    batch = []

    for node in origin_nodes:
        
        try:
            count += 1
            times = nx.single_source_dijkstra_path_length(G, node, weight='travel_time', cutoff=constants.MAX_ACCESS_TIME)

            reachable_nodes = set(times.keys())
            if len(reachable_nodes) == 0: 
                isochrone_polys[node] = []
                continue
            
            points = MultiPoint([
                        (G.nodes[n]["x"], G.nodes[n]["y"])
                        for n in reachable_nodes
                    ])
            
            hull = concave_hull(points, ratio=0.25, allow_holes=False)

            if isinstance(hull, Polygon):
                isochrone_poly = hull

            elif isinstance(hull, MultiPolygon):
                isochrone_poly = max(hull.geoms, key=lambda p: p.area)

            elif isinstance(hull, (LineString, MultiLineString, Point)):
                isochrone_poly = hull.buffer(25)

            else:
                print(f"UNEXPECTED GEOMETRY TYPE: {type(hull)}")
                continue

            isochrone_polys[node] = isochrone_poly
            batch.append({"origin_node": node, "geometry": isochrone_poly})

            try:
                if not len(batch) % 100: 
                    batch_gdf = gpd.GeoDataFrame(batch, crs=constants.projected_crs)
                    batch_gdf.to_file(constants.city_data_gpkg, layer="isochrones_polygons_base",
                                driver="GPKG", mode="a")
                    batch = []  # clear batch
                    print("APPENDED TO FILE SUCCESSFULLY! COUNT={}".format(count))

            except Exception as e:
                print("COULDN'T APPEND TO FILE. ERROR:", e)

        except Exception as e:
            print("ERROR:", e)

    if batch:
        batch_gdf = gpd.GeoDataFrame(batch, crs=constants.projected_crs)
        batch_gdf.to_file(constants.city_data_gpkg, layer="isochrones_polygons_base",
                    driver="GPKG", mode="a")
    return isochrone_polys


# ===================================== SAVE ISOCHRONES ===========================================

def _save_isochrones(G_geog: GeoDataFrame, isochrone_base_geog: GeoDataFrame, approach: str):
    # this function creates the origin stage of isochrones
    
    try:
        assert not ox.projection.is_projected(G_geog.graph['crs'])
        assert isochrone_base_geog.crs.is_geographic
        
        # if the origin_node col is not int, convert it to int
        if not is_integer_dtype(isochrone_base_geog["origin_node"]):
            isochrone_base_geog["origin_node"] = isochrone_base_geog["origin_node"].astype("int64")

        # calc the x and y coords for every node
        node_x = {n: data["x"] for n, data in G_geog.nodes(data=True)}  # lon
        node_y = {n: data["y"] for n, data in G_geog.nodes(data=True)}  # lat

        # store it in isochrone_gdf_geog
        isochrone_base_geog["lon"] = isochrone_base_geog["origin_node"].map(node_x)
        isochrone_base_geog["lat"] = isochrone_base_geog["origin_node"].map(node_y)

        # save to files
        layer = f"isochrones_{approach}_origin"
        isochrone_base_geog.to_file(filename=constants.gpkg_folder/"isochrones.gpkg", layer=layer, driver="GPKG")
        isochrone_base_geog.to_feather(constants.feather_folder /"isochrones" / f"{layer}.feather", index=False)
        
        # save_isochrones(isochrone_gdf_geog)
    
    except Exception as e:
        print("Error:", e)


if __name__ == '__main__':
    
    G_geog = build_graph(constants.FILES_FOLDER / "pune_walk_geographic.graphml")
    G_proj = ox.project_graph(G_geog, to_crs=constants.projected_crs) 

    # centroids are considered origins
    grid_fp = constants.feather_folder / "grid" / "grid_appr1.feather"
    grids_gdf = gpd.read_feather(grid_fp)
    if not grids_gdf.crs.is_projected:
        grids_gdf = grids_gdf.to_crs(crs=constants.projected_crs)

    origins_geog: GeoSeries = grids_gdf.centroid
    origins_proj: GeoSeries = origins_geog.to_crs(constants.projected_crs)

    isochrone_polys = compute_isochrone_edges(G_proj, origins_proj)
    isochrones_gdf:GeoDataFrame = GeoDataFrame.from_dict(
        isochrone_polys,
        orient="index",
        columns=["geometry"],
        crs=constants.projected_crs
    ).reset_index().rename(columns={"index": "origin_node"})

    isochrones_gdf = isochrones_gdf.to_crs(constants.geographic_crs)
    # isochrones_gdf.to_file(filename=config.gpkg_fp, layer="isochrones_concave_hull2")
    

    # G_geog = build_graph(config.FILES_FOLDER / "pune_walk_geographic.graphml")
    isochrones_edges_base_geog = GeoDataFrame.from_file(constants.gpkg_folder / "isochrones.gpkg", layer="isochrones_edges_base")
    isochrones_polygons_base_geog = GeoDataFrame.from_file(constants.gpkg_folder / "isochrones.gpkg", layer="isochrones_polygons_base")

    print(f"{isochrones_edges_base_geog.crs=}")
    print(f"{isochrones_polygons_base_geog.crs=}")

    _save_isochrones(G_geog, isochrones_edges_base_geog, "edges")
    _save_isochrones(G_geog, isochrones_polygons_base_geog, "polygons")

