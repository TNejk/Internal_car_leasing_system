from sqlalchemy import Column, Integer, String, Enum, Boolean, TIMESTAMP, ForeignKey
from sqlalchemy import func
from sqlalchemy.orm import relationship
from ..database import Base
from ..enums import UserRoles

class Users(Base):
	__tablename__ = 'users'

	id = Column(Integer, primary_key=True)
	email = Column(String(64), unique=True, nullable=False)
	password = Column(String(255), nullable=False)
	role = Column(Enum(UserRoles), default='user', nullable=False)
	name = Column(String(64), default='unnamed_user', nullable=False)
	created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
	is_deleted = Column(Boolean, default=False, nullable=False)

	change_logs = relationship('UsersChangeLog', back_populates='user')
	change_logs_cars = relationship('CarsChangeLog', back_populates='user')
	leases = relationship('Leases', back_populates='user')
	change_logs_leases = relationship('LeasesChangeLog', back_populates='user')
	lease_requests = relationship('LeaseRequests', back_populates='user')
	trips = relationship('Trips', back_populates='user')
	trip_participant = relationship('TripsParticipants', back_populates='user')
	trip_invite = relationship('TripsInvites', back_populates='user')
	trip_join_request = relationship('TripsJoinRequests', back_populates='user')
	notifications = relationship('Notifications', back_populates='user')
	notification_recipient = relationship('NotificationsRecipients', back_populates='user')

class UsersChangeLog(Base):
	__tablename__ = 'users_change_log'

	id = Column(Integer, primary_key=True)
	id_user = Column(Integer, ForeignKey('users.id'), nullable=False)
	changed_by = Column(Integer, ForeignKey('users.id'), nullable=False)
	changed_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
	note = Column(String(255), nullable=False)

	user = relationship('Users', back_populates='change_logs')
