from pydantic import BaseModel

class NotificationRead(BaseModel):
  notification_id: int

class NotificationGet(BaseModel):
  user_id: int