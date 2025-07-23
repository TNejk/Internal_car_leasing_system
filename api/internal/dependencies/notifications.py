
from firebase_admin import messaging
from typing import Optional, List
from sqlalchemy.orm import Session
from datetime import datetime
import db.models as model
from db.enums import UserRoles, NotificationTypes, TargetFunctions

def send_firebase_message_safe(message):
    """Send Firebase message with error handling."""
    try:
        messaging.send(message)
        return True
    except Exception as e:
        print(f"ERROR: Failed to send Firebase message: {e}")
        return False

def create_firebase_notification(title: str, body: str, topic: str) -> messaging.Message:
    """Create a Firebase notification message for a specific topic."""
    return messaging.Message(
        notification=messaging.Notification(
            title=title,
            body=body
        ),
        topic=topic
    )

def create_firebase_notification_for_email(title: str, body: str, email: str) -> messaging.Message:
    """Create a Firebase notification message for a specific user email."""
    # Convert email to valid topic name (Firebase topics can't contain @ or .)
    topic = email.replace("@", "_").replace(".", "_")
    return messaging.Message(
        notification=messaging.Notification(
            title=title,
            body=body
        ),
        topic=topic
    )

def send_notification_to_user(db: Session, title: str, message: str, 
                             target_user_email: str, actor_user_id: int,
                             notification_type: NotificationTypes = NotificationTypes.info,
                             target_func: TargetFunctions = TargetFunctions.general) -> bool:
    """Send both database and Firebase notification to a specific user."""
    try:
        # Get target user
        target_user = db.query(model.Users).filter(
            model.Users.email == target_user_email,
            model.Users.is_deleted == False
        ).first()
        
        if not target_user:
            print(f"WARNING: User {target_user_email} not found for notification")
            return False
        
        # Create database notification
        notification = model.Notifications(
            title=title,
            message=message,
            actor=actor_user_id,
            recipient_role=target_user.role,
            type=notification_type,
            target_func=target_func
        )
        db.add(notification)
        db.flush()
        
        # Create recipient record for specific user
        recipient_record = model.NotificationsRecipients(
            notification=notification.id,
            recipient=target_user.id,
            is_read=False
        )
        db.add(recipient_record)
        db.commit()
        
        # Send Firebase notification
        firebase_message = create_firebase_notification_for_email(title, message, target_user_email)
        firebase_success = send_firebase_message_safe(firebase_message)
        
        print(f"NOTIFICATION: Sent to {target_user_email} - DB: ✓, Firebase: {'✓' if firebase_success else '✗'}")
        return True
        
    except Exception as e:
        db.rollback()
        print(f"ERROR: Failed to send notification to {target_user_email}: {e}")
        return False

def send_notification_to_role(db: Session, title: str, message: str,
                             target_role: UserRoles, actor_user_id: int,
                             notification_type: NotificationTypes = NotificationTypes.info,
                             target_func: TargetFunctions = TargetFunctions.general) -> bool:
    """Send both database and Firebase notification to all users with a specific role."""
    try:
        # Create database notification for role
        notification = model.Notifications(
            title=title,
            message=message,
            actor=actor_user_id,
            recipient_role=target_role,
            type=notification_type,
            target_func=target_func
        )
        db.add(notification)
        db.commit()
        
        # Send Firebase notification to role topic
        firebase_message = create_firebase_notification(title, message, target_role.value)
        firebase_success = send_firebase_message_safe(firebase_message)
        
        print(f"NOTIFICATION: Sent to role {target_role.value} - DB: ✓, Firebase: {'✓' if firebase_success else '✗'}")
        return True
        
    except Exception as e:
        db.rollback()
        print(f"ERROR: Failed to send notification to role {target_role.value}: {e}")
        return False

def send_system_notification(db: Session, title: str, message: str, actor_user_id: int,
                           notification_type: NotificationTypes = NotificationTypes.info,
                           target_func: TargetFunctions = TargetFunctions.general) -> bool:
    """Send system-wide notification to all users."""
    try:
        # Create database notification for system
        notification = model.Notifications(
            title=title,
            message=message,
            actor=actor_user_id,
            recipient_role=UserRoles.user,  # Default role, but this will be ignored for system notifications
            type=notification_type,
            target_func=target_func
        )
        db.add(notification)
        db.flush()
        
        # Create recipient records for all active users
        active_users = db.query(model.Users).filter(
            model.Users.is_deleted == False
        ).all()
        
        for user in active_users:
            recipient_record = model.NotificationsRecipients(
                notification=notification.id,
                recipient=user.id,
                is_read=False
            )
            db.add(recipient_record)
        
        db.commit()
        
        # Send Firebase notification to system topic
        firebase_message = create_firebase_notification(title, message, "system")
        firebase_success = send_firebase_message_safe(firebase_message)
        
        print(f"NOTIFICATION: System notification sent - DB: ✓, Firebase: {'✓' if firebase_success else '✗'}")
        return True
        
    except Exception as e:
        db.rollback()
        print(f"ERROR: Failed to send system notification: {e}")
        return False