CREATE TYPE lease_status AS ENUM ('created', 'scheduled', 'active', 'late', 'unconfirmed', 'returned', 'canceled', 'missing', 'aborted');
CREATE TYPE regions AS ENUM('local', 'global');
CREATE TYPE request_statuses AS ENUM ( 'pending',  'approved',  'rejected',  'cancelled');
CREATE TYPE car_types AS ENUM('personal', 'cargo');
CREATE TYPE gearbox_types AS ENUM('manual','automatic');
CREATE TYPE fuel_types AS ENUM('benzine','naft','diesel','electric');
CREATE TYPE car_status AS ENUM('available','away','unavailable','decommissioned');
CREATE TYPE user_roles AS ENUM('user','manager','admin','system');
CREATE TYPE notification_types AS ENUM('info','warning','danger','success');
CREATE TYPE trips_statuses AS ENUM('scheduled','ongoing','ended', 'canceled');
CREATE TYPE trip_invite_statuses AS ENUM('pending','accepted','rejected','expired');
CREATE TYPE target_functions AS ENUM('lease','trips','reservations','requests','reports');

CREATE TABLE users (
  id BIGSERIAL PRIMARY KEY,
  email VARCHAR(64) NOT NULL UNIQUE,
  password VARCHAR(255) NOT NULL,
  role user_roles NOT NULL DEFAULT 'user',
  name VARCHAR(64) NOT NULL DEFAULT 'unnamed_user',
  created_at TIMESTAMP NOT NULL DEFAULT now(),
  is_deleted BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE users_change_log (
  id BIGSERIAL PRIMARY KEY,
  id_user INT NOT NULL REFERENCES users(id),
  changed_by INT NOT NULL REFERENCES users(id),
  changed_at TIMESTAMP NOT NULL DEFAULT now(),
  note VARCHAR(255) NOT NULL
);

CREATE TABLE cars (
  id BIGSERIAL PRIMARY KEY,
  plate_number VARCHAR(7) UNIQUE NOT NULL,
  name VARCHAR(32) NOT NULL DEFAULT 'unnamed_car',
  category car_types NOT NULL,
  gearbox_type gearbox_types NOT NULL,
  fuel_type fuel_types NOT NULL,
  region regions NOT NULL,
  status car_status NOT NULL DEFAULT 'available',
  seats SMALLINT NOT NULL CHECK (seats > 0),
  usage_metric SMALLINT NOT NULL DEFAULT 1,
  img_url VARCHAR(255) NOT NULL DEFAULT 'https://fl.gamo.sosit-wh.net/placeholder_car.png',
  created_at TIMESTAMP NOT NULL DEFAULT now(),
  is_deleted BOOLEAN NOT NULL DEFAULT false
);

CREATE TABLE cars_change_log (
  id BIGSERIAL PRIMARY KEY,
  id_car INT NOT NULL REFERENCES cars(id),
  changed_by INT NOT NULL REFERENCES users(id),
  changed_at TIMESTAMP NOT NULL DEFAULT now(),
  note VARCHAR(255) NOT NULL
);

CREATE TABLE leases (
  id BIGSERIAL PRIMARY KEY,
  status lease_status NOT NULL DEFAULT 'created',
  create_time TIMESTAMP NOT NULL DEFAULT now(),
  scheduled_time TIMESTAMP,
  start_time TIMESTAMP NOT NULL,
  end_time TIMESTAMP NOT NULL,
  u_return_time TIMESTAMP,
  return_time TIMESTAMP,
  missing_time TIMESTAMP,
  canceled_time TIMESTAMP,
  aborted_time TIMESTAMP,
  id_car INT NOT NULL REFERENCES cars(id),
  id_user INT NOT NULL REFERENCES users(id),
  private BOOLEAN NOT NULL DEFAULT FALSE,
  note VARCHAR(255),
  region_tag regions NOT NULL,
  is_damaged BOOLEAN NOT NULL DEFAULT FALSE,
  dirty BOOLEAN NOT NULL DEFAULT FALSE,
  exterior_damage BOOLEAN NOT NULL DEFAULT FALSE,
  interior_damage BOOLEAN NOT NULL DEFAULT FALSE,
  collision BOOLEAN NOT NULL DEFAULT FALSE,
  status_updated_at TIMESTAMP,
  last_changed_by INT REFERENCES users(id)
);

CREATE TABLE lease_change_log (
  id BIGSERIAL PRIMARY KEY,
  id_lease INT REFERENCES leases(id),
  changed_by INT NOT NULL REFERENCES users(id),
  changed_at TIMESTAMP NOT NULL DEFAULT now(),
  previous_status lease_status NOT NULL,
  new_status lease_status NOT NULL,
  note VARCHAR(255)
);

CREATE TABLE lease_requests (
  id BIGSERIAL PRIMARY KEY,
  start_time TIMESTAMP NOT NULL,
  end_time TIMESTAMP NOT NULL,
  status request_statuses NOT NULL DEFAULT 'pending',
  id_car INT NOT NULL REFERENCES cars(id),
  id_user INT NOT NULL REFERENCES users(id)
);

CREATE TABLE trips (
  id BIGSERIAL PRIMARY KEY,
  trip_name VARCHAR(128) NOT NULL,
  id_lease INT NOT NULL REFERENCES leases(id),
  id_car INT NOT NULL REFERENCES cars(id),
  creator INT NOT NULL REFERENCES users(id),
  is_public BOOLEAN  NOT NULL DEFAULT true,
  status trips_statuses NOT NULL DEFAULT 'scheduled',
  free_seats INT NOT NULL CHECK (free_seats >= 0),
  destination_name VARCHAR(255) NOT NULL,
  destiantion_lat DECIMAL(9,6) NOT NULL,
  destination_lon DECIMAL(9,6) NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE trips_participants (
  id BIGSERIAL PRIMARY KEY,
  id_trip INT NOT NULL REFERENCES trips(id),
  id_user INT NOT NULL REFERENCES users(id),
  seat_number INT NOT NULL,
  trip_finished BOOLEAN NOT NULL DEFAULT false
);

CREATE TABLE trips_invites (
  id BIGSERIAL PRIMARY KEY,
  id_trip INT NOT NULL REFERENCES trips(id),
  id_user INT NOT NULL REFERENCES users(id),
  status trip_invite_statuses NOT NULL DEFAULT 'pending'
);

CREATE TABLE trips_join_requests (
  id BIGSERIAL PRIMARY KEY,
  id_trip INT NOT NULL REFERENCES trips(id),
  id_user INT NOT NULL REFERENCES users(id),
  status trip_invite_statuses NOT NULL DEFAULT 'pending'
);

CREATE TABLE notifications (
  id BIGSERIAL PRIMARY KEY,
  title VARCHAR(64) NOT NULL,
  message VARCHAR(255) NOT NULL,
  actor INT NOT NULL REFERENCES users(id),
  recipient_role user_roles NOT NULL,
  type notification_types NOT NULL,
  target_func target_functions NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT now(),
  expires_at TIMESTAMP
);

CREATE TABLE notifications_recipients (
  id BIGSERIAL PRIMARY KEY,
  recipient INT NOT NULL REFERENCES users(id),
  notification INT NOT NULL REFERENCES notifications(id),
  read_at TIMESTAMP,
  is_read BOOLEAN NOT NULL DEFAULT false
);












CREATE INDEX idx_users_role_deleted ON users(is_deleted, role);
CREATE INDEX idx_cars_multi ON cars(is_deleted, status, category, gearbox_type, region);
CREATE INDEX idx_cars_emanuel ON cars(is_deleted, status);
CREATE INDEX idx_leases_id_car ON leases(id_car);
CREATE INDEX idx_leases_id_user ON leases(id_user);
CREATE INDEX idx_leases_status ON leases(status);
CREATE INDEX idx_lease_change_log_id_lease ON lease_change_log(id_lease);
CREATE INDEX idx_lease_change_log_changed_by ON lease_change_log(changed_by);
CREATE INDEX idx_cars_change_log_id_car ON cars_change_log(id_car);
CREATE INDEX idx_cars_change_log_changed_by ON cars_change_log(changed_by);
CREATE INDEX idx_users_change_log_id_user ON users_change_log(id_user);
CREATE INDEX idx_users_change_log_changed_by ON users_change_log(changed_by);
CREATE INDEX idx_trips_is_public_status ON trips(is_public, status);
CREATE INDEX idx_trips_participants_trip_finished_id_trip ON trips_participants(trip_finished, id_trip);
CREATE INDEX idx_lease_requests_status ON lease_requests(status);
CREATE INDEX idx_notifications_recipients_read_recipient ON notifications_recipients(is_read, recipient);
CREATE INDEX idx_trips_invites_id_user ON trips_invites(id_user);
CREATE INDEX idx_trips_join_requests_status_id_trip ON trips_join_requests(status, id_trip);