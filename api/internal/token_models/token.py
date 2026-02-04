from pydantic import BaseModel, Field
from typing import Annotated

class Token(BaseModel):
  access_token: str
  token_type: str


class TokenData(BaseModel):
  email: str
  role: Annotated[str, Field(examples=["manager", "user", "admin"])]

  # class Config:
  #   from_attributes = True  # Allows conversion from SQLAlchemy model