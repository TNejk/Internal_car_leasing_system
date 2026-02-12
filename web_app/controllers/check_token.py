import requests
from functools import wraps
from flask import session, redirect
from workers import sign_in_api_call

def check_token():
  def decorator(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
      # if 'token' not in session:
      #   return redirect('/sign-in')
      #
      # response = requests.post(
      #   url='https://icls.sosit-wh.net/check_token',
      #   headers={'Authorization': f'Bearer {session["token"]}'},
      # )
      #
      # if response.status_code != 200 or response.json().get('msg') != 'success':
      #   # Try to refresh token
      #   result = sign_in_api_call(session.get('username'), session.get('password'))
      #   if result != 'success':  # If login fails, redirect
      #     return redirect('/sign-in')
      #   if result == 'Nesprávne meno alebo heslo!':
      #     return redirect('/sign-in')
      #
      #
      # # If token is valid (or refreshed successfully), proceed to the original function
      return func(*args, **kwargs)
    return wrapper
  return decorator
