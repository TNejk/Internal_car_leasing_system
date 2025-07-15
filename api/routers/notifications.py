from fastapi import APIRouter, Depends, HTTPException, status
from typing import Annotated
from sqlalchemy.orm import Session
import api_models.default as modef
import api_models.request as moreq  
import api_models.response as mores
from internal.dependencies import get_current_user, connect_to_db
import db.models as model
from datetime import datetime

router = APIRouter(prefix="/v2/notifications", tags=["notifications"])

@router.get("/get", response_model=mores.NotificationListResponse)
async def get_notifications(current_user: Annotated[modef.User, Depends(get_current_user)],
                            db: Session = Depends(connect_to_db)):
  """Get user notifications based on their role and individual assignments"""
  try:
    user_db = db.query(model.Users.id, model.Users.role).filter(
      model.Users.email == current_user.email
    ).first()
    
    # Get notifications for user's role and individual notifications
    # Use a subquery to check if user has a recipient record
    notifications_query = db.query(
      model.Notifications,
      model.NotificationsRecipients.is_read,
      model.NotificationsRecipients.read_at
    ).outerjoin(
      model.NotificationsRecipients,
      (model.Notifications.id == model.NotificationsRecipients.notification) & 
      (model.NotificationsRecipients.recipient == user_db.id)
    ).filter(
      # Either role-based notification or individual recipient
      (model.Notifications.recipient_role == user_db.role) |
      (model.NotificationsRecipients.recipient == user_db.id)
    ).filter(
      (model.Notifications.expires_at.is_(None)) |
      (model.Notifications.expires_at > datetime.now())
    )
    
    # match notification with user id and get actor email
    notifications_with_actors = notifications_query.join(
      model.Users, model.Notifications.actor == model.Users.id
    ).add_columns(model.Users.email.label('actor_email')).all()
    
    notification_list = []
    unread_count = 0
    
    for notification, is_read, read_at, actor_email in notifications_with_actors:
  
      is_notification_read = is_read if is_read is not None else False
      notification_read_at = read_at if read_at is not None else None
      
      if not is_notification_read:
        unread_count += 1
        
      notification_list.append(
        mores.NotificationResponse(
          notification_id=notification.id,
          title=notification.title,
          message=notification.message,
          actor_email=actor_email,
          notification_type=notification.type.value,
          target_function=notification.target_func.value,
          created_at=notification.created_at,
          expires_at=notification.expires_at,
          is_read=is_notification_read,
          read_at=notification_read_at
        )
      )
    
    # Sort by created_at descending (newest first)
    notification_list.sort(key=lambda x: x.created_at, reverse=True)
    
    return mores.NotificationListResponse(
      notifications=notification_list,
      unread_count=unread_count
    )
    
  except HTTPException:
    raise
  except Exception as e:
    raise HTTPException(
      status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
      detail=f"Error retrieving notifications: {str(e)}"
    )


@router.post("/mark-as-read", response_model=modef.DefaultResponse)
async def mark_notification_as_read(request: moreq.NotificationRead,
                                    current_user: Annotated[modef.User, Depends(get_current_user)],
                                    db: Session = Depends(connect_to_db)):
  """Mark a notification as read for the current user"""
  try:
    user_db = db.query(model.Users.id, model.Users.role).filter(
      model.Users.email == current_user.email
    ).first()
    

    notification = db.query(model.Notifications).filter(
      model.Notifications.id == request.notification_id
    ).filter(
  
      (model.Notifications.recipient_role == user_db.role) |
      (model.Notifications.id.in_(
        db.query(model.NotificationsRecipients.notification).filter(
          model.NotificationsRecipients.recipient == user_db.id
        )
      ))
    ).first()
    
    if not notification:
      raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Notification not found or access denied"
      )
    
    # Check if recipient record already exists
    recipient_record = db.query(model.NotificationsRecipients).filter(
      model.NotificationsRecipients.notification == request.notification_id,
      model.NotificationsRecipients.recipient == user_db.id
    ).first()
    
    current_time = datetime.now()
    
    if recipient_record:
      if not recipient_record.is_read:
        recipient_record.is_read = True
        recipient_record.read_at = current_time
      else:
        return modef.DefaultResponse(
          status=True,
          msg="Notification already marked as read"
        )
    else:
 
      new_recipient = model.NotificationsRecipients(
        notification=request.notification_id,
        recipient=user_db.id,
        is_read=True,
        read_at=current_time
      )
      db.add(new_recipient)
    
    db.commit()
    
    return modef.DefaultResponse(
      status=True,
      msg="Notification marked as read successfully"
    )
    
  except HTTPException:
    raise
  except Exception as e:
    db.rollback()
    raise HTTPException(
      status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
      detail=f"Error marking notification as read: {str(e)}"
    )

