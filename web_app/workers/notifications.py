import requests
from flask import session, jsonify


def notifications():
  headers = {'Authorization': 'Bearer ' + session.get('token'),
             'Content-Type': 'application/json'}
  url = 'https://icls.sosit-wh.net/notifications'

  try:
    r = requests.post(url=url, headers=headers)

    # Try to parse JSON safely
    try:
      response = r.json()
    except requests.JSONDecodeError:
      print('notifications.py')
      print(f"Response was not JSON. Status code: {r.status_code}")
      print(f"Response text: {r.text}")
      return jsonify({'error': 'Invalid JSON response from server', 'status_code': r.status_code}), 500
    return jsonify(response)

  except requests.RequestException as e:
    print(f"Request failed: {e}")
    return jsonify({'error': 'Failed to reach the server'}), 500
