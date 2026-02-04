from datetime import datetime, timedelta, timezone
import pytz

def convert_to_datetime(string):
  try:
    # Parse string, handling timezone if present
    dt_obj = datetime.strptime(string, "%Y-%m-%d %H:%M:%S")
    return dt_obj
  except:  #? Ok now bear with me, it may look stupid, be stupid and make me look stupid, but it works :) Did i mention how much i hate dates
    try:
      dt_obj = datetime.strptime(string, "%Y-%m-%d %H:%M")
      return dt_obj
    except ValueError as e:
      raise ValueError(f"Invalid datetime format: {string}") from e


def ten_minute_tolerance(a_timeof, today):
  """ Gives user 10 minutes of leaniency to lease a car before a lease from the past error. """
  timeof = convert_to_datetime(string=a_timeof)
  diff = today - timeof
  if (diff.total_seconds() / 60) >= 10:
    return True


def get_sk_date():
  bratislava_tz = pytz.timezone('Europe/Bratislava')
  # Ensure the datetime is in UTC before converting
  dt_obj = datetime.now()
  utc_time = dt_obj.replace(tzinfo=pytz.utc) if dt_obj.tzinfo is None else dt_obj.astimezone(pytz.utc)
  bratislava_time = utc_time.astimezone(bratislava_tz)  # Convert to Bratislava timezone
  return bratislava_time