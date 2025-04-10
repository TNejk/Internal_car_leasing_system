import requests
from flask import session

def get_all_users(email,role):
  headers = {'Authorization': 'Bearer ' + session.get('token')}
  body = {'email': email, 'role': role}
  url = 'https://icls.sosit-wh.net/get_users'
  request = requests.get(url=url, headers=headers, json=body)
  response = request.json()['users']
  return response