from pydantic import BaseModel, Field
from typing import Annotated

class RegisterRequest(BaseModel):
  email: Annotated[str, Field(min_length=9)]
  password: Annotated[str, Field(min_length=15)]
  role: Annotated[str, Field(examples=["manager", "user", "admin", "system"])]
  name: Annotated[str, Field(min_length=4)]

class LoginRequest(BaseModel):
  email: str
  password: str