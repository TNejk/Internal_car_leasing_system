from pydantic import BaseModel, Field
from typing import Annotated

class UserEdit(BaseModel):
  email: Annotated[str | None, Field(min_length=9)]  # @gamo.sk = 8 char
  password: Annotated[str | None, Field(default=None)]
  role: Annotated[str | None, Field(default=None)]
  name: Annotated[str | None, Field(default=None)]

class UserDelete(BaseModel):
  user_id: int