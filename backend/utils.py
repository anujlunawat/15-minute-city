import fiona
import pyogrio
import backend.constants as constants
from geopandas import GeoDataFrame

def remove_gpkg_layer(gpkg: str, layer: str):
    l = len(pyogrio.list_layers(gpkg))

    fiona.remove(
        path_or_collection=gpkg,
        layer=layer,
        driver="GPKG",
    )

    if l < len(pyogrio.list_layers(gpkg)):
        print("Layer: {} removed from GeoPackage: {} successfully!".format(layer, gpkg))
    else:
        print("Could not remove layer: {} from GeoPackage: {}".format(layer, gpkg))


def list_layers(gpkg: str):
    return pyogrio.list_layers(gpkg)


def save_gpkg_layer(filename: str, layer: str, gdf: GeoDataFrame):
    gdf.to_file(filename=constants.gpkg_folder / filename, layer=layer, driver="GPKG")
    return constants.gpkg_folder / filename


def save_feather_file(filename:str, gdf: GeoDataFrame):
    gdf.to_feather(filename=constants.feather_folder / filename, index = False)
    return constants.feather_folder / filename


if __name__ == "__main__":
    pass