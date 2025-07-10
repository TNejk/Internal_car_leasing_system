from pydantic import BaseModel

class read_notification_req(BaseModel):
  notification_id: int
