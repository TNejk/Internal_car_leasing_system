from pydantic import BaseModel, Field
from typing import Annotated
from ..default.user import User

class UserList(BaseModel):
  users: Annotated[[User] | None, Field(default=None, examples=["{email: user@gamo.sk, role: manager}"])]

class UserInfoResponse(BaseModel):
  user_id: int
  username: str
  email: str
  role: Annotated[str, Field(examples=["manager", "user", "admin", "system"])]
