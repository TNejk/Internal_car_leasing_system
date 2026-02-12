from sqlalchemy import Column, Integer, Numeric, String, Enum, Boolean, TIMESTAMP, ForeignKey, CheckConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..database import Base
from ..enums import TripsStatuses, TripsInviteStatus


class Trips(Base):
	__tablename__ = 'trips'

	id = Column(Integer, primary_key=True)
	trip_name = Column(String(128), nullable=False)
	id_lease = Column(Integer, ForeignKey('leases.id'), nullable=False)
	id_car = Column(Integer, ForeignKey('cars.id'), nullable=False)
	creator = Column(Integer, ForeignKey('users.id'), nullable=False)
	is_public = Column(Boolean, default=True, nullable=False)
	status = Column(Enum(TripsStatuses), default='scheduled', nullable=False)
	free_seats = Column(Integer, nullable=False)
	destination_name = Column(String(255), nullable=False)
	destination_lat = Column(Numeric(9,6), nullable=False)
	destination_lon = Column(Numeric(9,6), nullable=False)
	created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)

	lease = relationship('Leases', back_populates='trip')
	user = relationship('Users', back_populates='trips')
	car = relationship('Cars', back_populates='trips')

	participants = relationship('TripsParticipants', back_populates='trip')
	invites = relationship('TripsInvites', back_populates='trip')
	requests = relationship('TripsJoinRequests', back_populates='trip')

	__table_args__ = (
		CheckConstraint('free_seats>=0', name='trips_free_seats_check'),
	)

class TripsParticipants(Base):
	__tablename__ = 'trips_participants'

	id = Column(Integer, primary_key=True)
	id_trip = Column(Integer, ForeignKey('trips.id'), nullable=False)
	id_user = Column(Integer, ForeignKey('users.id'), nullable=False)
	seat_number = Column(Integer, nullable=False)
	trip_finished = Column(Boolean, default=False, nullable=False)

	trip = relationship('Trips', back_populates=False)
	user = relationship('Users', back_populates=False)

class TripsInvites(Base):
	__tablename__ = 'trips_invites'

	id = Column(Integer, primary_key=True)
	id_trip = Column(Integer, ForeignKey('trips.id'), nullable=False)
	id_user = Column(Integer, ForeignKey('users.id'), nullable=False)
	status = Column(Enum(TripsInviteStatus), default='pending', nullable=False)

	trip = relationship('Trips', back_populates='invites')
	user = relationship('Users', back_populates='invite')

class TripsJoinRequests(Base):
	__tablename__ = 'trips_join_requests'

	id = Column(Integer, primary_key=True)
	id_trip = Column(Integer, ForeignKey('trips.id'), nullable=False)
	id_user = Column(Integer, ForeignKey('users.id'), nullable=False)
	status = Column(Enum(TripsInviteStatus), default='pending', nullable=False)

	trip = relationship('Trips', back_populates='requests')
	user = relationship('users', back_populates='request')
