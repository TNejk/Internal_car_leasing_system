from pydantic import BaseModel
from typing import Annotated

class login_response(BaseModel):
  token: str
  role: Annotated[str, Field(examples=["manager", "user", "admin"])]
  email: str
