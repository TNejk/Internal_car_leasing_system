import os, sys, requests
from functools import wraps
from flask import session, redirect, url_for

def revoke_token():
  def decorator(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
      if 'token' in session:
        response = requests.post(
          url='https://icls.sosit-wh.net/revoke_token',
          headers={'Authorization': f'Bearer {session["token"]}'},)
        session.pop('token', None)
        session.pop('username', None)
        session.pop('password', None)
        session.pop('role', None)
        session.pop('notifications', None)
        return redirect('/sign-in')

      return func(*args, **kwargs)
    return wrapper
  return decorator