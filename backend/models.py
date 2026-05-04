from pydantic import BaseModel
from typing import List, Union

class ClickPoint(BaseModel):
    lat: float
    lng: float

class Origins(BaseModel):
    lat: float
    lon: float