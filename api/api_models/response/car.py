from pydantic import BaseModel, Field
from typing import Annotated
from datetime import datetime
from db.enums import GearboxTypes, FuelTypes, CarTypes

class CarListContent(BaseModel):
  car_id: int
  car_name: str
  car_status: Annotated[str, Field(examples=['available', 'away', 'unavailable', 'decommissioned'])]
  spz: Annotated[str | None, Field(default=None, min_length=7)]
  image_url: str


class CarListResponse(BaseModel):
  car_list: list[CarListContent]


class CarInfoResponse(BaseModel):
  """ Every information about the requested car. """
  car_id: int
  spz: Annotated[str, Field(min_length=7)]
  car_type: Annotated[str, Field(examples=['personal', 'cargo'])]
  gearbox_type: Annotated[str, Field(examples=['manual', 'automatic'])]
  fuel_type: Annotated[str, Field(examples=['benzine', 'naft', 'diesel', 'electric'])]
  region: Annotated[str, Field(examples=['local', 'global'])]
  car_status: Annotated[str, Field(examples=['available', 'away', 'unavailable', 'decommissioned'])]
  seats: Annotated[int, Field(ge=2)]
  type: CarTypes
  usage_metric: int
  image_url: str
  decommission_time: Annotated[datetime | None, Field(examples=["CET time"], default=None,
                                                      description="Unless the car is decommissioned this will be None")]
  allowed_hours: Annotated[list[list], Field(examples=["[[YYYY.MM.DD HH:MM:SS, YYYY.MM.DD HH:MM:SS]]"],
                                             description="A list containing starting and ending times of leases bound to this car.")]

class CarInfoListResponse(BaseModel):
  car_list: list[CarInfoResponse]