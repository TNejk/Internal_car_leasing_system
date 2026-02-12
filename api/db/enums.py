# enums.py
from enum import Enum

class LeaseStatus(Enum):
	created = 'created'
	scheduled = 'scheduled'
	active = 'active'
	late = 'late'
	undonfirmed = 'unconfirmed'
	returned = 'returned'
	canceled = 'canceled'
	missing = 'missing'
	aborted = 'aborted'

class Regions(Enum):
	local = 'local'
	_global = 'global'

class RequestStatus(Enum):
	pending = 'pending'
	approved = 'approved'
	rejected = 'rejected'
	canceled = 'cancelled'

class CarTypes(Enum):
	personal = 'personal'
	cargo = 'cargo'

class GearboxTypes(Enum):
	manual = 'manual'
	automatic = 'automatic'

class FuelTypes(Enum):
	benzine = 'benzine'
	naft = 'naft'
	diesel = 'diesel'
	electric = 'electric'

class CarStatus(Enum):
	available = 'available'
	away = 'away'
	unavailable = 'unavailable'
	decommissioned = 'decommissioned'

class UserRoles(Enum):
	user = 'user'
	manager = 'manager'
	admin = 'admin'
	system = 'system'

class NotificationTypes(Enum):
	info = 'info'
	warning = 'warning'
	danger = 'danger'
	success = 'success'

class TripsStatuses(Enum):
	scheduled = 'scheduled'
	ongoing = 'ongoing'
	ended = 'ended'
	canceled = 'canceled'

class TripsInviteStatus(Enum):
	pending = 'pending'
	accepted = 'accepted'
	rejected = 'rejected'
	expired = 'expired'

class TargetFunctions(Enum):
	lease = 'lease'
	trips = 'trips'
	reservations = 'reservations'
	requests = 'requests'
	reports = 'reports'
