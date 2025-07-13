from pydantic import BaseModel, Field
from typing import Annotated
from datetime import datetime
from ..default.default import Trip

class TripList(BaseModel):
  trips: list[Trip]


class TripJoinRequest(BaseModel):
  request_id: int
  trip_id: int
  user_email: str
  status: Annotated[str, Field(examples=['pending', 'accepted', 'rejected'])]
  requested_at: Annotated[datetime, Field(examples=["CET time"])]


class TripJoinRequestListResponse(BaseModel):
  join_requests: list[TripJoinRequest]


class TripInvite(BaseModel):
  invite_id: int
  trip_id: int
  user_email: str
  status: Annotated[str, Field(examples=['pending', 'accepted', 'rejected'])]
  invited_at: Annotated[datetime, Field(examples=["CET time"])]


class TripInviteListResponse(BaseModel):
  invites: list[TripInvite]
