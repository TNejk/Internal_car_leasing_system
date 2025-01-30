import os, sys, requests, json
sys.path.append('./workers')
from functools import wraps
from flask import abort, session, render_template
from sign_in_api import sign_in_api

SALT = os.getenv('SALT')
SALT = '%2b%12%4/ZiN3Ga8VQjxm9.K2V3/.'

def check_token():
  def decorator(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
      response = requests.post(
        url='https://icls.sosit-wh.net/check_token',
        headers={'Authorization': f'Bearer {session["token"]}'},
      )
      print(response.json())
      if response.json()['msg'] != 'succesful':
        sign_in_api(session['username'],session['password'], SALT)
      return func(*args, **kwargs)
    return wrapper
  return decorator