from functools import wraps
from flask import abort, session

def require_role(*roles):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if 'role' not in session or session['role'] not in roles:
                abort(403)
            return func(*args, **kwargs)
        return wrapper
    return decorator