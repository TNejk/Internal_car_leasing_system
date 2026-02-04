from pydantic import BaseModel, Field
from typing import Annotated

class LoginResponse(BaseModel):
  token: str
