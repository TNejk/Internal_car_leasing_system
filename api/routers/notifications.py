from fastapi import APIRouter, Depends
from typing import Annotated
import api_models.default as modef
import api_models.request as moreq
from internal.dependencies import get_current_user

router = APIRouter(prefix="/v2/notifications", tags=["notifications"])

@router.get("/get", response_model=list[dict])
async def get_notifications(current_user: Annotated[modef.User, Depends(get_current_user)]):
  """Get user notifications"""
  pass


@router.post("/mark-as-read", response_model=modef.DefaultResponse)
async def mark_notification_as_read(request: moreq.NotificationRead,
                                    current_user: Annotated[modef.User, Depends(get_current_user)]):
  """Mark a notification as read"""
  pass

