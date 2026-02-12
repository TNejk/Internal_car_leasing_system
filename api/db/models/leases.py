from sqlalchemy import Column, Integer, SmallInteger, String, Enum, Boolean, TIMESTAMP, ForeignKey, CheckConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..database import Base
from ..enums import Regions, LeaseStatus, RequestStatus

class Leases(Base):
	__tablename__ = 'leases'
	id = Column(Integer, primary_key=True)
	status = Column(Enum(LeaseStatus), default='created', nullable=False)
	create_time = Column(TIMESTAMP, server_default=func.now(), nullable=False)
	scheduled_time = Column(TIMESTAMP)
	start_time = Column(TIMESTAMP, nullable=False)
	end_time = Column(TIMESTAMP, nullable=False)
	u_return_time = Column(TIMESTAMP)
	return_time = Column(TIMESTAMP)
	missing_time = Column(TIMESTAMP)
	canceled_time = Column(TIMESTAMP)
	aborted_time = Column(TIMESTAMP)
	id_car = Column(Integer, ForeignKey('cars.id'), nullable=False)
	id_user = Column(Integer, ForeignKey('users.id'), nullable=False)
	private = Column(Boolean, default=False, nullable=False)
	note = Column(String(255))
	region_tag = Column(Enum(Regions), nullable=False)
	is_damaged = Column(Boolean, default=False, nullable=False)
	dirty = Column(Boolean, default=False, nullable=False)
	exterior_damage = Column(Boolean, default=False, nullable=False)
	interior_damage = Column(Boolean, default=False, nullable=False)
	collision = Column(Boolean, default=False, nullable=False)
	status_updated_at = Column(TIMESTAMP)
	last_changed_by = Column(Integer, ForeignKey('users.id'))

	user = relationship('Users', back_populates='leases')
	car = relationship('Cars', back_populates='leases')

	trip = relationship('Trips', back_populates='lease', uselist=False)

	change_logs = relationship('LeaseChangeLog', back_populates='lease')

class LeaseRequests(Base):
	__tablename__ = 'lease_requests'

	id = Column(Integer, primary_key=True)
	start_time = Column(TIMESTAMP, nullable=False)
	end_time = Column(TIMESTAMP, nullable=False)
	status = Column(Enum(RequestStatus), default='pending', nullable=False)
	id_car = Column(Integer, ForeignKey('cars.id'), nullable=False)
	id_user = Column(Integer, ForeignKey('users.id'), nullable=False)

	car = relationship('Cars', back_populates='lease_request')
	user = relationship('Users', back_populates='lease_requests')

class LeaseChangeLog(Base):
	__tablename__ = 'lease_change_log'

	id = Column(Integer, primary_key=True)
	id_lease = Column(Integer, ForeignKey('leases.id'), nullable=False)
	changed_by = Column(Integer, ForeignKey('users.id'), nullable=False)
	changed_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
	previous_status = Column(Enum(LeaseStatus), nullable=False)
	new_status = Column(Enum(LeaseStatus), nullable=False)
	note = Column(String(255))

	lease = relationship('Leases', back_populates='change_logs')
	user = relationship('Users', back_populates='change_logs_leases')
