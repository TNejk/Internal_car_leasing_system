from pydantic import BaseModel, Field
from typing import Annotated
from datetime import datetime

class ErrorResponse(BaseModel):
  status: bool
  msg: str

class DefaultResponse(BaseModel):
  status: bool
  msg: Annotated[str | None, Field(default=None)]

class User(BaseModel):
  email: str
  role: Annotated[str, Field(examples=["manager", "user", "admin", "system"])]
  name: str  # This maps to name in the database
  disabled: bool  # This maps to is_deleted in the database

class Trip(BaseModel):
  trip_id: int
  trip_name: str
  creator_email: str
  car_name: str
  is_public: bool
  status: Annotated[str, Field(examples=['scheduled', 'active', 'completed', 'cancelled'])]
  free_seats: int
  destination_name: str
  destination_lat: float
  destination_lon: float
  created_at: Annotated[datetime, Field(examples=["CET time"])]

class Lease(BaseModel):
  lease_id: int
  lease_status: Annotated[str | None, Field(
    examples=['created', 'scheduled', 'active', 'late', 'unconfirmed', 'returned', 'canceled', 'missing', 'aborted'],
    default=None)]
  creation_time: Annotated[datetime | None, Field(examples=["CET time"], default=None)]
  starting_time: Annotated[datetime | None, Field(examples=["CET time"], default=None)]
  ending_time: Annotated[datetime | None, Field(examples=["CET time"], default=None)]
  approved_return_time: Annotated[datetime | None, Field(examples=["CET time"], default=None)]
  missing_time: Annotated[datetime | None, Field(examples=["CET time"], default=None)]
  cancelled_time: Annotated[datetime | None, Field(examples=["CET time"], default=None)]
  aborted_time: Annotated[datetime | None, Field(examples=["CET time"], default=None)]
  driver_email: str
  car_name: str
  status_updated_at: Annotated[datetime | None, Field(examples=["CET time"], default=None)]
  last_changed_by: str
  region_tag: Annotated[str, Field(examples=['local', 'global'])]


class Car(BaseModel):
  car_id: int
  plate_number: str
  name: str
  category: str
  gearbox_type: str
  fuel_type: str
  region: str
  status: str
  seats: int
  usage_metric: int
  img_url: str
  created_at: datetime
  is_deleted: bool

  class Config:
    from_attributes = True