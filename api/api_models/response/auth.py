from pydantic import BaseModel, Field
from typing import Annotated

class LoginResponse(BaseModel):
  token: str
  email: str
  role: Annotated[str, Field(examples=["manager", "user", "admin"])]
