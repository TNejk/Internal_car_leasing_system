
from firebase_admin import messaging
from typing import Optional, List
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
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
                             target_func: TargetFunctions = TargetFunctions.requests,
                             expires_at: Optional[datetime] = None) -> bool:
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
            target_func=target_func,
            expires_at=expires_at or (datetime.now() + timedelta(days=30))  # Default 30 days expiry
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
                             target_func: TargetFunctions = TargetFunctions.requests,
                             expires_at: Optional[datetime] = None) -> bool:
    """Send both database and Firebase notification to all users with a specific role."""
    try:
        # Create database notification for role
        notification = model.Notifications(
            title=title,
            message=message,
            actor=actor_user_id,
            recipient_role=target_role,
            type=notification_type,
            target_func=target_func,
            expires_at=expires_at or (datetime.now() + timedelta(days=30))  # Default 30 days expiry
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
                           target_func: TargetFunctions = TargetFunctions.requests,
                           expires_at: Optional[datetime] = None) -> bool:
    """Send system-wide notification to all users."""
    try:
        # Create database notification for system
        notification = model.Notifications(
            title=title,
            message=message,
            actor=actor_user_id,
            recipient_role=UserRoles.user,  # Default role, but this will be ignored for system notifications
            type=notification_type,
            target_func=target_func,
            expires_at=expires_at or (datetime.now() + timedelta(days=30))  # Default 30 days expiry
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

# Convenience helper functions for common notification scenarios
def notify_lease_cancelled(db: Session, current_user_id: int, recipient_email: str, car_name: str) -> bool:
    """Send notification when a lease is cancelled by manager/admin."""
    return send_notification_to_user(
        db=db,
        title="Vaša rezervácia bola zrušená!",
        message=f"Rezervácia pre auto: {car_name} bola zrušená.",
        target_user_email=recipient_email,
        actor_user_id=current_user_id,
        notification_type=NotificationTypes.warning,
        target_func=TargetFunctions.lease
    )

def notify_private_ride_request(db: Session, current_user_id: int, user_email: str, car_name: str, 
                               time_from: str, time_to: str) -> bool:
    """Send notification to managers about private ride request."""
    return send_notification_to_role(
        db=db,
        title="Žiadosť o súkromnu jazdu!",
        message=f"Email: {user_email}\nAuto: {car_name}\nOd: {time_from}\nDo: {time_to}",
        target_role=UserRoles.manager,
        actor_user_id=current_user_id,
        notification_type=NotificationTypes.info,
        target_func=TargetFunctions.requests
    )

def notify_lease_approved(db: Session, current_user_id: int, recipient_email: str, car_name: str) -> bool:
    """Send notification when a private lease request is approved."""
    return send_notification_to_user(
        db=db,
        title="Vaša rezervácia bola prijatá!",
        message=f"Súkromná rezervácia auta: {car_name} bola schválená.",
        target_user_email=recipient_email,
        actor_user_id=current_user_id,
        notification_type=NotificationTypes.success,
        target_func=TargetFunctions.requests
    )

def notify_lease_rejected(db: Session, current_user_id: int, recipient_email: str, car_name: str) -> bool:
    """Send notification when a private lease request is rejected."""
    return send_notification_to_user(
        db=db,
        title="Súkromná rezervácia nebola prijatá!",
        message=f"Súkromná rezervácia auta: {car_name} bola odmietnutá.",
        target_user_email=recipient_email,
        actor_user_id=current_user_id,
        notification_type=NotificationTypes.warning,
        target_func=TargetFunctions.requests
    )

def notify_car_damage(db: Session, current_user_id: int, user_email: str, car_name: str) -> bool:
    """Send notification to managers about car damage."""
    return send_notification_to_role(
        db=db,
        title="Poškodenie auta!",
        message=f"Email: {user_email}\nAuto: {car_name}\nVrátil auto s poškodením!",
        target_role=UserRoles.manager,
        actor_user_id=current_user_id,
        notification_type=NotificationTypes.danger,
        target_func=TargetFunctions.lease
    )

def notify_new_reservation(db: Session, current_user_id: int, recipient_email: str, car_name: str,
                          time_from: str, time_to: str) -> bool:
    """Send notification to managers about new car reservation."""
    return send_notification_to_role(
        db=db,
        title=f"Nová rezervácia auta: {car_name}!",
        message=f"Email: {recipient_email}\nOd: {time_from}\nDo: {time_to}",
        target_role=UserRoles.manager,
        actor_user_id=current_user_id,
        notification_type=NotificationTypes.info,
        target_func=TargetFunctions.reservations
    )

def notify_trip_cancelled(db: Session, current_user_id: int, trip_name: str, car_name: str) -> bool:
    """Send system notification when a trip is cancelled."""
    return send_system_notification(
        db=db,
        title="Cestovná rezervácia zrušená!",
        message=f"Cesta '{trip_name}' pre auto {car_name} bola zrušená.",
        actor_user_id=current_user_id,
        notification_type=NotificationTypes.warning,
        target_func=TargetFunctions.trips
    )

def notify_car_decommissioned(db: Session, current_user_id: int, car_name: str) -> bool:
    """Send system notification when a car is decommissioned."""
    return send_system_notification(
        db=db,
        title=f"Auto: {car_name}, bolo deaktivované!",
        message="Skontrolujte si prosím vaše rezervácie.",
        actor_user_id=current_user_id,
        notification_type=NotificationTypes.warning,
        target_func=TargetFunctions.reservations
    )

def notify_car_activated(db: Session, current_user_id: int, car_name: str) -> bool:
    """Send system notification when a car is activated/reactivated."""
    return send_system_notification(
        db=db,
        title=f"Auto {car_name} je k dispozíci!",
        message="Je možné znova auto rezervovať v aplikácií.",
        actor_user_id=current_user_id,
        notification_type=NotificationTypes.success,
        target_func=TargetFunctions.reservations
    )