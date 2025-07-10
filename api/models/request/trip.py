from pydantic import BaseModel

class trip_join_request_req(BaseModel):
  trip_id: int


class trip_invite_response_req(BaseModel):
  invite_id: int
  accepted: bool


class trip_join_response_req(BaseModel):
  request_id: int
  approved: bool