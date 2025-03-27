import requests
from flask import session

def request_all_car_data(*location):
  headers = {'Authorization': 'Bearer ' + session.get('token')}
  url = 'https://icls.sosit-wh.net/get_car_list' if location is None else f'https://icls.sosit-wh.net/get_car_list?location={location}'
  request = requests.get(url=url, headers=headers)
  response = request.json()['cars']
  return response 