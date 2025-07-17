from pydantic import BaseModel, Field
from typing import Annotated
from api_models.default.default import User
from ..default import User

class UserList(BaseModel):
  users: Annotated[list[User] | None, Field(default=None, examples=["{email: user@gamo.sk, role: manager}"])]

class UserInfo(BaseModel):
  user_id: int
  username: str
  email: str
  role: Annotated[str, Field(examples=["manager", "user", "admin", "system"])]

class UserInfoListResponse(BaseModel):
  users: list[UserInfo]