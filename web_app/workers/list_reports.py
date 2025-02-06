import requests
from flask import session

def list_reports(email,role):
  headers = {'Authorization': 'Bearer ' + session.get('token')}
  body = {'email': email, 'role': role}
  url = 'https://icls.sosit-wh.net/list_reports'
  request = requests.post(url=url, headers=headers, json=body)
  response = request.json()['reports']
  return response