from sqlalchemy import Column, Integer, SmallInteger, String, Enum, Boolean, TIMESTAMP, ForeignKey, CheckConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..database import Base
from ..enums import CarTypes, GearboxTypes, FuelTypes, Regions, CarStatus

class Cars(Base):
	__tablename__ = 'cars'

	id = Column(Integer, primary_key=True)
	plate_number = Column(String(7), unique=True, nullable=False)
	name = Column(String(32), default='unnamed_car', nullable=False)
	category = Column(Enum(CarTypes), nullable=False)
	gearbox_type = Column(Enum(GearboxTypes), nullable=False)
	fuel_type = Column(Enum(FuelTypes), nullable=False)
	region = Column(Enum(Regions), nullable=False)
	status = Column(Enum(CarStatus), default='available', nullable=False)
	seats = Column(SmallInteger, nullable=False)
	usage_metric = Column(SmallInteger, default=1, nullable=False)
	img_url = Column(String(255), default='https://fl.gamo.sosit-wh.net/placeholder_car.png')
	created_at = Column(TIMESTAMP, server_default=func.now())
	is_deleted = Column(Boolean, default=False, nullable=False)

	change_logs = relationship('CarsChangeLog', back_populates='car')
	leases = relationship('Leases', back_populates='car')
	lease_request = relationship('LeaseRequests', back_populates='car')
	trips = relationship('Trips', back_populates='car')

	__table_args__ = (
		CheckConstraint('seats>0', name='cars_seats_check'),
	)

class CarsChangeLog(Base):
	__tablename__ = 'cars_change_log'

	id = Column(Integer, primary_key=True)
	id_car = Column(Integer, ForeignKey('cars.id'), nullable=False)
	changed_by = Column(Integer, ForeignKey('users.id'), nullable=False)
	changed_at = Column(TIMESTAMP, server_default=func.now())
	note = Column(String(255), nullable=False)

	car = relationship('Cars', back_populates='change_logs')
	user = relationship('Users', back_populates='change_logs_cars')
