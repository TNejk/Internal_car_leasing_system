from pydantic import BaseModel, Field
from typing import Optional, Annotated
from datetime import datetime

class CarCreationReq(BaseModel):
  car_name: Annotated[str, Field(max_length=30, min_length=4)]
  car_type: Annotated[str, Field(examples=["personal", "cargo"])]
  spz: Annotated[str, Field(min_length=7)]
  gas_type: Annotated[str, Field(examples=['benzine', 'naft', 'diesel', 'electric'])]
  drive_type: Annotated[str, Field(examples=["manual", "automatic"])]
  car_image: Annotated[str, Field(description=".jpg or .png only")]


class CarEditingReq(BaseModel):
  car_id: int
  car_name: Annotated[str | None, Field(default=None)]
  car_type: Annotated[str | None, Field(default=None, examples=["personal", "cargo"])]
  car_status: Annotated[
    str | None, Field(default=None, examples=['available', 'away', 'unavailable', 'decommissioned'])]
  spz: Annotated[str | None, Field(default=None, min_length=7)]
  gas_type: Annotated[str | None, Field(default=None, examples=['benzine', 'naft', 'diesel', 'electric'])]
  drive_type: Annotated[str | None, Field(default=None, examples=['manual', 'automatic'])]
  car_image: Annotated[str | None, Field(default=None)]


class CarDeletionReq(BaseModel):
  car_id: int


class CarDecommissionReq(BaseModel):
  car_id: int
  time_from: Annotated[datetime, Field(examples=["YYYY DD-MM hh:mm:ss"], description="CET time when the car was decommisoned.")]
  time_to: Annotated[datetime, Field(examples=["YYYY DD-MM hh:mm:ss"], description="CET time when the car will be active again.")]


class CarActivationReq(BaseModel):
  car_id: int
  car_id: Annotated[int | None, Field(description="If ID is available use it before selecting with car name")]


class CarInformationReq(BaseModel):
  car_id: int
