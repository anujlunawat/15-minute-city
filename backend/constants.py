CENTER_POINT = (18.4655, 73.8547)  # Shivajinagar (lat, lon)
RADIUS_METERS = 1000
WALKING_SPEED = 1.4  # meters per second (5kmph)
MAX_ACCESS_TIME = 900  # 15 minutes in seconds
GRID_CELL_SIZE = 250
CITY = "Pune, Maharashtra"

# crs: Coordinate Reference System
# everything in files is projected
# everything in db should be geographic

# UTM: Universal Transverse Mercator
# flattened region
# Units = meters
# high local accuracy
projected_crs="EPSG:32643"

# curved earth
# Units = degrees
geographic_crs="EPSG:4326"

from pathlib import Path
BASE_FOLDER = Path(__file__).resolve().parent.parent 
FILES_FOLDER = BASE_FOLDER / "files"
DB_NAME = "accessibility.db"
DB_PATH = BASE_FOLDER / "backend" / DB_NAME

DUCKDB_NAME = "accessibility.duckdb"
DUCKDB_PATH = BASE_FOLDER / "backend" / DUCKDB_NAME

feather_folder = FILES_FOLDER / "feather_files"
feather_folder.mkdir(exist_ok=True)

_city_data_gpkg_filename = "city_data.gpkg"
_isochrones_gpkg_filename = "isochrones.gpkg"
city_data_gpkg = FILES_FOLDER / _city_data_gpkg_filename  # entire fp with the file name
isochones_gpkg = FILES_FOLDER / _isochrones_gpkg_filename

gpkg_folder = FILES_FOLDER / "gpkg"
grid_gpkg = gpkg_folder / "grid.gpkg"



