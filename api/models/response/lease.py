from pydantic import BaseModel, Field
from datetime import datetime
from typing import Annotated
from ..default.lease import Lease

class LeaseList(BaseModel):
  active_leases: Lease

class LeaseCancel(BaseModel):
  cancelled: bool

class LeaseMonthly(BaseModel):
  start_of_lease: Annotated[datetime | None, Field(examples=["CET time"], default=None)]
  end_of_lease: Annotated[datetime | None, Field(examples=["CET time"], default=None)]
  time_of_return: Annotated[datetime | None, Field(examples=["CET time"], default=None)]
  lease_status: Annotated[str | None, Field(
    examples=['created', 'scheduled', 'active', 'late', 'unconfirmed', 'returned', 'canceled', 'missing', 'aborted'],
    default=None)]
  car_name: str
  driver_email: str
  note: Annotated[str, Field(max_length=250)]

class LeaseStart(BaseModel):
  status: bool
  private: bool
  msg: Annotated[str | None, Field(default=None)]

class LeaseRequest(BaseModel):
  request_id: int
  starting_time: Annotated[datetime | None, Field(examples=["CET time"], default=None)]
  ending_time: Annotated[datetime | None, Field(examples=["CET time"], default=None)]
  request_status: Annotated[str, Field(examples=['pending', 'approved', 'rejected', 'cancelled'])]
  car_name: str
  spz: Annotated[str | None, Field(default=None, min_length=7)]
  driver_email: str
  image_url: str

class LeaseRequestList(BaseModel):
  active_requests: list[LeaseRequest]