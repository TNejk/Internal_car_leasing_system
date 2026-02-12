from sqlalchemy import Column, Integer, SmallInteger, String, Enum, Boolean, TIMESTAMP, ForeignKey, CheckConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..database import Base
from ..enums import UserRoles, NotificationTypes, TargetFunctions

class Notifications(Base):
  __tablename__ = 'notifications'

  id = Column(Integer, primary_key=True)
  title = Column(String(64), nullable=False)
  message = Column(String(255), ForeignKey('messages.id'), nullable=False)
  actor = Column(Integer, ForeignKey('users.id'), nullable=False)
  recipient_role = Column(Enum(UserRoles), nullable=False)
  type = Column(Enum(NotificationTypes), nullable=False)
  target_func = Column(Enum(TargetFunctions), nullable=False)
  created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
  expires_at = Column(TIMESTAMP, nullable=False)

  user = relationship('Users', back_populates='notification')
  recipients = relationship('NotificationsRecipients', back_populates='_notification')

class NotificationsRecipients(Base):
  __tablename__ = 'notifications_recipients'

  id = Column(Integer, primary_key=True)
  recipient = Column(Integer, ForeignKey('users.id'), nullable=False)
  notification = Column(Integer, ForeignKey('notifications.id'), nullable=False)
  read_at = Column(TIMESTAMP)
  is_read = Column(Boolean, nullable=False, default=False)

  _notification = relationship('Notifications', back_populates='recipients')
  user = relationship('Users', back_populates='notification_recipient')