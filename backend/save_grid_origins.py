"""
1. Create a gdf of the city (`config.CITY`). Change its crs to projected crs. This is `boundary`, which gives us boundary of the entire city.
2. The next step is to create square grids of equal sizes covering the entire city. For this:
    a. We find the total_bounds of the boundary. This means, we create the minimum size rectangle that can contain the entire boundary i.e every geometry (point, polygon etc). By this, we access the
        xmin → smallest X coordinate (left edge)
        ymin → smallest Y coordinate (bottom edge)
        xmax → largest X coordinate (right edge)
        ymax → largest Y coordinate (top edge)
    of the boundary's total_bounds.
    b. prep(city_poly) prepares the geometry so that repeated spatial operations like intersects() are much faster when applied many times (as in the grid generation loop).
    c. we have defined the size of each cell (`config.GRID_CELL_SIZE`). define a variable `grid_cells` and assign it to an empty list.
    d. Then we iterate 2 nested for loops over the X and Y coordinates of the bounding box.For each (x, y) pair, a square polygon is created using shapely.geometry.box() with size cell_size.
    e. Now, since we had created a rectangle (total_bounds) for the boundary, and actually we are creating cells in spaces of the rectangle, we have to check if the cells intersects with the boundary (var: `city_prepared`).
    To understand this, let's take an example:
        - We have the boundary of a city and it looks like a triangle; the base is broad and the top is narrow.
        - When we create a rectangle arounds it, it should cover the entire boundary. Hence, there will be lots of space left at the top and, maybe, little at the bottom.
        - Now, when we create cells to cover this rectangle, we need to check if the cell is not in the the spaces of the rectangle and actually a part of the boundary.
        - Here we check if the grid cell intersects the city boundary. This includes cells that partially overlap the city. For a stricter grid, we could instead check if the city contains the entire cell.
3. After appending all the required cells in the list (`grid_cells`), we create a GeoDataFrame for it. It enables spatial operations and eases data manipulation. 
4. Since the cells are Polygons, we need a represntative Point for each cell.These points will act as origin locations for further spatial analysis. For this, we find the centroid of all the Polygon geometries. (Note: alternatively, we could use `grid.representative_point() instead of centroid).
5. We, then save this gdf in a GeoPackage file (.gpkg) for GIS compatibility and a Feather (.feather) file for fast loading in Python workflows.
"""



import osmnx as ox
import geopandas as gpd
from geopandas import GeoDataFrame, GeoSeries
from shapely.prepared import prep
import shapely
import time
from pyproj import CRS
import numpy as np
import backend.constants as constants


def create_gdf(place: str) -> GeoDataFrame:
    """
    Takes a place string and returns its boundary GeoDataFrame in projected crs.

    Args:
        place (str): place (city in our case) to get boundary of

    Returns:
        GeoDataFrame: boundary of the input place in projected crs
    """    
    boundary = ox.geocode_to_gdf(place)
    return boundary.to_crs(crs=constants.projected_crs)


# ========================================= APPROACH 1 =======================================

def create_grids(boundary: GeoDataFrame) -> tuple[GeoDataFrame]:
    """
    1. Takes an input boundary
    2. Encloses it in minimim rectangle that can contain all the nodes and edges in it
    3. creates grids in this rectangle starting from the top left to the bottom right (i.e fills it with rectangles)
    4. then checks the grids that INTERSECT with the boundary. stores these grids in `grid_cells` var. create a gdf from it (var `grid`)
    5. make a copy of grid. after this, in grid, convert the geometry of each cell to a point represented by the cells centre (centroid)
    6. saves it in geopackage (.gpkg) and feather (.feather) files
    7. return the earlier copy of grid and grid (i.e the cells` geometries and their centroids in 2 different gdfs)  
    A detailed explanation is provided at the start of this file
    - Note: there are 2 other functions for grids and centroids creation. What makes this function different?
        - create_grids2: uses np.arange() that takes float as an input and can return floats as well. but this function uses range() which which takes an int val and return ints. so, there may be some difference in the grid creation and thereafter, but it does not have a significant impact on the overall process (of grids creation and centroid calc).
        - create_grids3: works with a different approach. it reates all the grids in the bounding rectangle and stores in a gdf. then it calculates the overlay of the cells' geometries with the boundary. this means, the cells that are completely in the boundary are considered and the cells which are, let's say 20%, in the boundary, their 20% geometry that lies in the boundary is considered and added the rest is not added. This is a more precise approach but any one the 3 functions work, without giving any major difference in the outputs.
    Args:
        boundary (GeoDataFrame): boundary to create grids on

    Returns:
        tuple[GeoDataFrame]: (gdf having cell boundaries(Polygon) geometry, gdf having cell centroids(Point) geometry)
    """    

    # checking if boundary is projected. if not, make it
    if not CRS(boundary.crs).is_projected:
        boundary = boundary.to_crs(constants.projected_crs)
        
    xmin, ymin, xmax, ymax = boundary.total_bounds
    city_poly = boundary.geometry.iloc[0]  # this gives use the Polygon of the boundary
    city_prepared = prep(city_poly)  # preprocesses a geometry so repeated spatial checks (like contains or intersects) against it run much faster.

    cell_size = constants.GRID_CELL_SIZE
    grid_cells = []

    for x in range(int(xmin), int(xmax), cell_size):
        for y in range(int(ymin), int(ymax), cell_size):
            cell = shapely.geometry.box(x, y, x+cell_size, y+cell_size)

            # since the bounding box (xmin, xmax, ymin, ymax) could be greater than the city boundary, we have to check if the cell really intersects the city for is just lying in the bounding area away from the actual city boundary.
            if city_prepared.intersects(cell):
                grid_cells.append(cell)

    # we need a gdf for getting the centroids
    grid = GeoDataFrame(geometry=grid_cells, crs=boundary.crs)  #boundary.crs: projected
    
    centroids = grid.copy(deep=True)
    centroids["geometry"] = centroids.centroid

    return grid.to_crs(constants.geographic_crs), centroids  # grid_gdf, centroids_gdf


# ========================================= APPROACH 2 =======================================

def create_grids2(boundary):
    # checking if boundary is projected. if not, make it
    if not CRS(boundary.crs).is_projected:
        boundary = boundary.to_crs(constants.projected_crs)
    
    xmin, ymin, xmax, ymax = boundary.total_bounds
    city_poly = boundary.geometry.iloc[0]  # this gives use the Polygon of the boundary
    city_prepared = prep(city_poly)  # preprocesses a geometry so repeated spatial checks (like contains or intersects) against it run much faster.
    cell_size = constants.GRID_CELL_SIZE
    # since arange works with floats, it can have very light difference in results from the range used in create_grids
    xs = np.arange(xmin, xmax, cell_size)
    ys = np.arange(ymin, ymax, cell_size)

    cells = [
        cell
        for x in xs
        for y in ys
        if city_prepared.intersects(cell := shapely.box(x, y, x+cell_size, y+cell_size))
    ]

    grid = GeoDataFrame(geometry=cells, crs=boundary.crs)  #boundary.crs: projected

    centroids = grid.copy(deep=True)
    centroids["geometry"] = centroids.centroid

    return grid.to_crs(constants.geographic_crs), centroids  # grid cells, centroids



# ========================================= APPROACH 3 =======================================

def create_grids3(boundary):
    # checking if boundary is projected. if not, make it
    if not CRS(boundary.crs).is_projected:
        boundary = boundary.to_crs(constants.projected_crs)
    
    xmin, ymin, xmax, ymax = boundary.total_bounds
    # city_poly = boundary.geometry.iloc[0]  # this gives use the Polygon of the boundary
    # city_prepared = prep(city_poly)  # preprocesses a geometry so repeated spatial checks (like contains or intersects) against it run much faster.
    cell_size = constants.GRID_CELL_SIZE
    xs = np.arange(xmin, xmax, cell_size)
    ys = np.arange(ymin, ymax, cell_size)

    grid = gpd.GeoDataFrame(
        geometry=[shapely.box(x, y, x+cell_size, y+cell_size) for x in xs for y in ys],
        crs=boundary.crs
    )

    grid = gpd.overlay(grid, boundary, how="intersection")

    centroids = grid.copy(deep=True)
    centroids["geometry"] = centroids.centroid

    return grid.to_crs(constants.geographic_crs), centroids


if __name__ == "__main__":
    boundary = create_gdf(constants.CITY)  # projected

    #  Approach 1
    start_time_1 = time.time()
    grid_gdf, centroids_gdf = create_grids(boundary)
    time_1 = time.time() - start_time_1

    # save geo package file
    gpkg_path = constants.gpkg_folder / "grid.gpkg"
    grid_gdf.to_file(filename=gpkg_path, driver="GPKG", layer="grid_appr1")
    print(f"Saved file: {gpkg_path}")

    # save feather file
    grid_gdf.to_feather(constants.feather_folder / "grid" / "grid_appr1.feather", index=False)
    print("Saved file: {}".format("grid_appr1.feather"))
    

    print(f"FINISHED APPROACH 1:\n{len(grid_gdf) = }\n{CRS(grid_gdf.crs).to_epsg() = }\n\n")

    
    # Approach 2
    start_time_2 = time.time()
    grid_gdf, centroids_gdf = create_grids2(boundary)
    time_2 = time.time() - start_time_2

    # save geo package file
    gpkg_path = constants.gpkg_folder / "grid.gpkg"
    grid_gdf.to_file(filename=gpkg_path, driver="GPKG", layer="grid_appr2")
    print(f"Saved file: {gpkg_path}")

    # save feather file
    grid_gdf.to_feather(constants.feather_folder / "grid" /"grid_appr2.feather", index=False)
    print("Saved file: {}".format("grid_appr2.feather"))

    print(f"FINISHED APPROACH 2:\n{len(grid_gdf) = }\n{CRS(grid_gdf.crs).to_epsg() = }\n\n")


    # Approach 3
    start_time_3 = time.time()
    grid_gdf, centroids_gdf = create_grids3(boundary)
    time_3 = time.time() - start_time_3

    # save geo package file
    gpkg_path = constants.gpkg_folder / "grid.gpkg"
    grid_gdf.to_file(filename=gpkg_path, driver="GPKG", layer="grid_appr3", overwrite=True, mode='w')
    print(f"Saved file: {gpkg_path}")

    # save feather file
    grid_gdf.to_feather(constants.feather_folder / "grid" /"grid_appr3.feather", index=False)
    print("Saved file: {}".format("grid_appr3.feather"))

    print(f"FINISHED APPROACH 3:\n{len(grid_gdf) = }\n{CRS(grid_gdf.crs).to_epsg() = }\n\n")

    # Print timing results
    print("="*50)
    print("TIMING RESULTS")
    print("="*50)
    print(f"Approach 1: {time_1:.4f} seconds")
    print(f"Approach 2: {time_2:.4f} seconds")
    print(f"Approach 3: {time_3:.4f} seconds")
    print("="*50)

