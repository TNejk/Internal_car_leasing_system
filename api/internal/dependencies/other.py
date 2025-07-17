from sqlalchemy.orm import Session
import db.models as model
from datetime import timedelta

USER_ROLES = [
  "user",
  "manager",
  "admin",
  "system"
]

def admin_or_manager(role: str):
  if role == "manager" or role == "admin":
    return True
  return False

def check_roles(user, roles: list):
  if user.role not in roles:
    raise HTTPException(
      status_code=status.HTTP_401_UNAUTHORIZED,
      detail="Unauthorized access. Admin role required.",
      headers={"WWW-Authenticate": "Bearer"}
    )


def calculate_usage_metric(car_id: int, db: Session) -> int:
  """Calculate usage metric for a car based on recent lease history"""
  try:
    latest_lease = db.query(model.Leases).filter(
      model.Leases.id_car == car_id
    ).order_by(model.Leases.id.desc()).first()
    
    if not latest_lease:
      return 1
    
    two_weeks_ago = latest_lease.start_time - timedelta(days=14)
    
    recent_leases = db.query(model.Leases).filter(
      model.Leases.id_car == car_id,
      model.Leases.start_time >= two_weeks_ago,
      model.Leases.return_time.isnot(None)
    ).all()
    
    total_hours = 0.0
    num_leases = len(recent_leases)
    
    for lease in recent_leases:
      if lease.return_time and lease.start_time:
        duration = lease.return_time - lease.start_time
        total_hours += duration.total_seconds() / 3600
    
    if num_leases <= 2 or total_hours <= 48.0:
      return 1
    elif 3 <= num_leases <= 4 or total_hours <= 72.0:
      return 2
    elif 5 <= num_leases <= 7 or total_hours <= 144.0:
      return 3
    elif 8 <= num_leases <= 11 or total_hours <= 288.0:
      return 4
    else:
      return 5
      
  except Exception:
    return 1
