import requests
from flask import session

def get_all_cars(email,role):
  headers = {'Authorization': 'Bearer ' + session.get('token')}
  body = {'email': email, 'role': role}
  url = 'https://icls.sosit-wh.net/get_car_names'
  request = requests.post(url=url, headers=headers, json=body)
  response = request.json()['cars']
  return response