from pydantic import BaseModel, Field
from datetime import datetime
from typing import Annotated

class leases_list_req(BaseModel):
  filter_email:             Annotated[str | None, Field(default=None)]
  filter_car_id:            Annotated[int | None, Field(default=None)]
  filter_time_from:         Annotated[datetime | None, Field(examples=["CET time"],    default=None)]
  filter_time_to:           Annotated[datetime | None, Field(examples=["CET time"],    default=None)]
  filter_active_leases:     Annotated[bool | None, Field(examples=["Active leases"],   default=None)]
  filter_inactive_leases:  Annotated[bool | None, Field(examples=["InActive leases"], default=None)]

class monthly_leases_req(BaseModel):
  month: Annotated[int, Field(description="Which month to filter leases by.")]

class cancel_lease_req(BaseModel):
  recipient: Annotated[str | None, Field(default=None, description="Whose lease to cancel, if not manager users email is utilized instead.")]
  car_name:  str
  car_id:    Annotated[int | None, Field(description="If ID is available use it before selecting with car name")]
  lease_id:  Annotated[int | None, Field(description="Needed to know for sure which lease to cancel")]

class lease_car_req(BaseModel):
  recipient:    Annotated[str | None, Field(default=None)]
  car_id:       int
  private_ride: bool
  private_trip: bool
  trip_participants: Annotated[list[str] | None, Field(examples=["['user@gamo.sk', 'user2@gamo.sk']"], default=None)]
  time_from:    Annotated[datetime | None, Field(examples=["CET time"],    default=None)]
  time_to:      Annotated[datetime | None, Field(examples=["CET time"],    default=None)]

class approve_pvr_req(BaseModel):
  approval:   bool
  request_id: int
  time_from:  Annotated[datetime | None, Field(examples=["CET time"],    default=None)]
  time_to:    Annotated[datetime | None, Field(examples=["CET time"],    default=None)]
  car_id:     int
  requester:  Annotated[str, Field(description="User who requested the private ride",  default=None)]

class return_car_req(BaseModel):
  lease_id:        int
  time_of_return:  Annotated[datetime | None, Field(examples=["CET time"],    default=None)]
  return_location: str
  damaged:         bool
  dirty_car:       bool
  interior_damage: bool
  exterior_damage: bool
  collision:       bool