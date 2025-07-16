from pydantic import BaseModel, Field
from datetime import datetime
from typing import Annotated

class LeaseList(BaseModel):
  filter_email:             Annotated[str | None, Field(default=None)]
  filter_car_id:            Annotated[int | None, Field(default=None)]
  filter_time_from:         Annotated[datetime | None, Field(examples=["CET time"],    default=None)]
  filter_time_to:           Annotated[datetime | None, Field(examples=["CET time"],    default=None)]
  filter_active_leases:     Annotated[bool | None, Field(examples=["Active leases"],   default=None)]
  filter_inactive_leases:  Annotated[bool | None, Field(examples=["InActive leases"], default=None)]

class LeaseMonthly(BaseModel):
  month: Annotated[int, Field(description="Which month to filter leases by.")]

class LeaseCancel(BaseModel):
  car_id: int
  lease_id:  int
  recipient: Annotated[str | None, Field(default=None, description="Whose lease to cancel, if not manager users email is utilized instead.")]

class LeaseCar(BaseModel):
  recipient:    Annotated[str | None, Field(default=None)]
  car_id:       int
  private_ride: bool
  private_trip: bool
  trip_participants: Annotated[list[str] | None, Field(examples=["['user@gamo.sk', 'user2@gamo.sk']"], default=None)]
  time_from:    Annotated[datetime | None, Field(examples=["YYYY.MM.DD hh:mm:dd"],    default=None)]
  time_to:      Annotated[datetime | None, Field(examples=["YYYY.MM.DD hh:mm:dd"],    default=None)]

class LeasePrivateApprove(BaseModel):
  approval:   bool
  request_id: int
  car_id:     int
  requester:  Annotated[str, Field(description="User who requested the private ride",  default=None)]

class LeaseFinish(BaseModel):
  lease_id:        int
  time_of_return:  Annotated[datetime | None, Field(examples=["YYYY.MM.DD hh:mm:dd"],    default=None)]
  return_location: str
  damaged:         bool
  dirty_car:       bool
  interior_damage: bool
  exterior_damage: bool
  collision:       bool