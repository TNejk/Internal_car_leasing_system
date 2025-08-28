from pydantic import BaseModel, Field
from datetime import datetime
from typing import Annotated
from ..default import Lease

class Location(BaseModel):
    id: int
    name: str
    street: str
    number: str
    psc: str
    city: str
    country: str
    lat: int
    lon: int
    p_spots: int
    free_p_spots: int 

class LocationResponse(BaseModel):
    locations: list[Location]