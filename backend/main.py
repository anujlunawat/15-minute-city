from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from contextlib import asynccontextmanager
import json

import database
import functionality
import backend.compute_accessibility as calc_accessbility
import backend.constants as constants
from models import ClickPoint


# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     # startup
#     print("Building graph...")
#     G = compute.build_graph()

#     print("Finding grocery nodes...")
#     grocery_nodes = compute.get_grocery_nodes(G)

#     print("Computing accessibility...")
#     results = compute.compute_accessibility(G, grocery_nodes)

#     print("Saving to DB...")
#     database.init_db()
#     database.save_nodes(results)

#     print("Startup computation complete.")

#     yield

    # shutdown

# with open(config.FILES_FOLDER / "isochrones_concave_hull.json") as f:
#     isochrones_json = json.load(f)

app = FastAPI()
# app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/nodes")
def get_nodes():
    return database.fetch_nodes()


@app.get("/polygon-accessibility")
def get_polygon_accessibility():
    output_file = calc_accessbility.ACCESSIBILITY_OUTPUT
    if not output_file.exists():
        return {"type": "FeatureCollection", "features": []}
    return json.loads(output_file.read_text(encoding="utf-8"))


@app.get("/")
def hey():
    print("hey there. connected already huh.")


@app.post("/isochrone")
async def compute_isochrone(point: ClickPoint):
    iso_gdf = database.fetch_isochrones()
    
    print("DONE")
    return JSONResponse(content=iso_gdf.__geo_interface__)
