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
