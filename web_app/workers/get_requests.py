import requests
from flask import session, jsonify


def get_requests():
  headers = {'Authorization': 'Bearer ' + session.get('token')}
  url = 'https://icls.sosit-wh.net/get_requests'

  try:
    r = requests.post(url=url, headers=headers)

    # Try to parse JSON safely
    try:
      response = r.json()
    except requests.JSONDecodeError:
      print(f"Response was not JSON. Status code: {r.status_code}")
      print(f"Response text: {r.text}")
      return jsonify({'error': 'Invalid JSON response from server', 'status_code': r.status_code}), 500

    return jsonify(response)

  except requests.RequestException as e:
    print(f"Request failed: {e}")
    return jsonify({'error': 'Failed to reach the server'}), 500
