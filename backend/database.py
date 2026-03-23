import sqlite3
import pandas as pd
from geopandas import GeoSeries, GeoDataFrame
from pyproj import CRS
from shapely import wkb
import backend.constants as constants


def establish_conn(db):
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    return conn, cursor

def init_db():
    conn, cursor = establish_conn(constants.DB_NAME)

    cursor.execute("DROP TABLE IF EXISTS nodes")
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS nodes (
        node_id INTEGER PRIMARY KEY,
        lat REAL,
        lon REAL,
        grocery_time REAL,
        accessible INTEGER
    )                   
""")
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS origins (
        id INTEGER AUTO INCREMENT PRIMARY KEY,
        lat DECIMAL NOT NULL,               
        lon DECIMAL NOT NULL
    )
""")
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS all_isochrones (
        id INTEGER AUTO INCREMENT PRIMARY KEY,
        geojson TEXT
    )
    """)

    # cursor.execute("DELETE FROM isochrones")
    # individual isochrones
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS isochrones (
        origin_node INTEGER PRIMARY KEY,
        lat REAL,
        lon REAL,
        score INT,
        colour TEXT,
        geometry BLOB
    )
""")
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS pois (
        poi_id INTEGER PRIMARY KEY,
        name TEXT,
        category TEXT,
        geometry BLOB               
    )
""")
    

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS isochrone_pois (
    origin_node INTEGER,
    poi_id INTEGER,
    distance REAL DEFAULT NULL,
                   
    PRIMARY KEY (origin_node, poi_id),
                   
    FOREIGN KEY (origin_node) REFERENCES isochrones(origin_node),
    FOREIGN KEY (poi_id) REFERENCES pois(poi_id)
    )
""")
    
    
    # create indexes
    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_ip_origin
    ON isochrone_pois(origin_node);
    """)

    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_ip_poi
    ON isochrone_pois(poi_id);
    """)

    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_poi_category
    ON pois(category);
    """)

    
    conn.commit()
    conn.close()


def save_isochrones(isochrone_gdf_latlon: GeoDataFrame):
    # WE CAN'T CHECK FOR CRS OFTHIS GDF SINCE THE GEOMETRY HAS BEEN CHANGED (to well-known binary i.e. wkb) 
    # assert CRS(isochrone_gdf_latlon) == CRS(config.geographic_crs)
    try:
        # isochrone_gdf_latlon = isochrone_gdf_latlon.convert_dtypes()

        if CRS(isochrone_gdf_latlon.crs).is_projected:
            isochrone_gdf_latlon = isochrone_gdf_latlon.to_crs(crs=constants.geographic_crs)

        isochrone_gdf_latlon["geometry"] = isochrone_gdf_latlon.geometry.to_wkb()
    except Exception as e:
        print("ERROR:", e)

    
    conn, cursor = establish_conn(constants.DB_PATH)

    isochrone_gdf_latlon.to_sql(
        name="isochrones",
        con=conn,
        if_exists="append",
        index=False
    )

    conn.commit()
    conn.close()


def save_origins(origins: GeoSeries):
    conn, cursor = establish_conn(constants.DB_PATH)

    df = pd.DataFrame({
    "lat": origins.y,
    "lon": origins.x
    })

    df.to_sql(
        name="origins",
        con=conn,
        if_exists="append",
        index=False,  # index=False part controls whether Pandas writes the DataFrame index as a column into the database.
        chunksize=300,
        method="multi"  # writes multiple values in a single INSERT command
    )


def save_nodes(data):
    conn, cursor = establish_conn(constants.DB_PATH)

    cursor.execute("DELETE FROM nodes")

    for row in data:
        accessible = 1 if row["grocery_time"] <= constants.MAX_ACCESS_TIME else 0

        cursor.execute("""
    INSERT INTO nodes (node_id, lat, lon, grocery_time, accessible)
    VALUES (?, ?, ?, ?, ?)
""",(
    row["node_id"],
    row["lat"],
    row["lon"],
    row["grocery_time"],
    accessible
))
    
    conn.commit()
    conn.close()



def fetch_nodes():
    conn, cursor = establish_conn(constants.DB_PATH)
    cursor.execute("SELECT lat, lon, grocery_time, accessible FROM nodes")

    rows = cursor.fetchall()
    conn.close()

    return [
        {
            "lat": r[0],
            "lon": r[1],
            "grocery_time": r[2],
            "accessible": bool(r[3])
        }
        for r in rows
    ]


def fetch_isochrones():
    conn, cursor = establish_conn(constants.DB_PATH)

    df = pd.read_sql("""
    SELECT origin_node, lat, lon, score, geometry, colour
    FROM isochrones
    LIMIT 500
    """, conn)

    df["geometry"] = df["geometry"].apply(wkb.loads)

    iso_gdf = GeoDataFrame(df, geometry="geometry", crs=constants.geographic_crs)

    conn.close()
    
    return iso_gdf


if __name__ == "__main__":
    init_db()