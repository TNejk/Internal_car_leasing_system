from flask import session
import requests

def request_monthly_leases(month):
  headers = {'Authorization': 'Bearer ' + session.get('token')}
  body = {'month': month, 'role': session.get('role')}
  url = 'https://icls.sosit-wh.net/get_monthly_leases'
  request = requests.post(url=url, headers=headers, json=body)
  response = request.json()
  # data = []
  # for lease in response:
  #   row = {'title': lease[3], 'start': lease[0], 'end': lease[1], 'extendedProps': {'car_id': lease[2]}}
  #   data.append(row)
  return response