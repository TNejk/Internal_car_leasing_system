import requests
from flask import session, jsonify

def request_user_leases(role,filters):
  headers = {'Authorization': 'Bearer ' + session.get('token')}
  body = {'role': role,
          'email': filters.get('email','') if session.get('role') == 'manager' else session.get('email',''),
          'car_name': filters.get('car_name',''),
          'timeof': filters.get('timeof',''),
          'timeto': filters.get('timeto',''),
          'status': filters.get('status',''),}
  url = 'https://icls.sosit-wh.net/get_leases'
  request = requests.post(url=url, headers=headers, json=body)
  response = request.json()['active_leases']
  return response