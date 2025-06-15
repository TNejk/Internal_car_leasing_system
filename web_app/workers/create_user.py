import requests
from flask import session, jsonify


def create_user(data):
  headers = {'Authorization': 'Bearer ' + session.get('token')}
  url = 'https://icls.sosit-wh.net/register'
  request = requests.post(url=url, headers=headers, json=data)
  response = request.json()
  return jsonify(response)