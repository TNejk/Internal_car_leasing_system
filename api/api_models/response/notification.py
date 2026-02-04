from pydantic import BaseModel, Field
from typing import Annotated, Optional
from datetime import datetime

class NotificationResponse(BaseModel):
  notification_id: int
  title: str
  message: str
  actor_email: str
  notification_type: Annotated[str, Field(examples=["info", "warning", "danger", "success"])]
  target_function: Annotated[str, Field(examples=["lease", "trips", "reservations", "requests", "reports"])]
  created_at: Annotated[datetime, Field(examples=["CET time"])]
  expires_at: Optional[datetime] = None
  is_read: bool
  read_at: Optional[datetime] = None

class NotificationListResponse(BaseModel):
  notifications: list[NotificationResponse]
  unread_count: int 