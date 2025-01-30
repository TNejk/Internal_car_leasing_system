import requests
from flask import session

def request_user_leases(email,role):
  headers = {'Authorization': 'Bearer ' + session.get('token')}
  body = {'email': email, 'role': role}
  url = 'https://icls.sosit-wh.net/get_leases'
  request = requests.post(url=url, headers=headers, json=body)
  response = request.json()['active_leases']
  return response