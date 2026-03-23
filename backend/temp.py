import osmnx as ox
import networkx as nx
from networkx import MultiDiGraph
import geopandas as gpd
from geopandas import GeoDataFrame
import constants


def nearest_node(G: MultiDiGraph, lat, lon):
    node = ox.distance.nearest_nodes(G, X=lon, y=lat)

    isochrones = gpd.read_feather(constants.feather_folder / "isochrones_polygons_final.feather")
    if node in isochrones["origin_node"]:
        print()