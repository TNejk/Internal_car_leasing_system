import requests
from flask import session, jsonify


def delete_car(data):
  headers = {'Authorization': 'Bearer ' + session.get('token')}
  url = 'https://icls.sosit-wh.net/decommision_car'
  request = requests.post(url=url, headers=headers, json=data)
  response = request.json()
  return jsonify(response)