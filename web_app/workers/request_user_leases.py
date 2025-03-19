import requests
from flask import session

def request_user_leases(email,role,filters):
  headers = {'Authorization': 'Bearer ' + session.get('token')}
  body = {'email': filters.email, 'role': role, 'car_name': filters.car_name, 'timeof': filters.timeof, 'timeto': filters.timeto}
  url = 'https://icls.sosit-wh.net/get_leases'
  request = requests.post(url=url, headers=headers, json=body)
  response = request.json()
  return response