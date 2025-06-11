import requests
from flask import session, jsonify

def request_user_leases(role,filters):
  headers = {'Authorization': 'Bearer ' + session.get('token')}
  body = {'role': role,
          'email': filters.get('email','') if session.get('role') == 'manager' else session.get('email',''),
          'car_name': filters.get('car_name',''),
          'timeof': filters.get('timeof',''),
          'timeto': filters.get('timeto',''),
          'istrue': filters.get('istrue', True),
          'isfalse': filters.get('isfalse', True),}
  url = 'https://icls.sosit-wh.net/get_leases'
  request = requests.post(url=url, headers=headers, json=body)
  print(request.text)
  response = request.json()['active_leases']

  # Assuming time is comparable (like a datetime object or a timestamp)
  sorted_array = sorted(response, key=lambda x: x['time_from'], reverse=True)

  return sorted_array