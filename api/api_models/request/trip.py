from pydantic import BaseModel

class TripJoinRequest(BaseModel):
  seat_number: int
  trip_id: int

class TripJoinResponse(BaseModel):
  request_id: int
  approved: bool

class TripInviteResponse(BaseModel):
  invite_id: int
  accepted: bool


