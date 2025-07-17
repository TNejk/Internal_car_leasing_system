import hashlib
import os
import requests
from flask import session, jsonify

SALT = os.getenv('SALT')

def sign_in_api_call(username, password):
    payload = {"username": username, "password": password}
    try:
        response = requests.post(
            url='https://icls.sosit-wh.net/v2/auth/login',
            json=payload
        )
        response = response.json()


        salted = SALT + password + SALT
        hashed = hashlib.sha256(salted.encode()).hexdigest()
        session['email'] = username
        session['name'] = 'unnamed_user'
        session['password'] = hashed
        session['token'] = response['access_token']
        session['role'] = response['role']
        session.permanent = True

        return True

    except requests.exceptions.RequestException as e:
        return jsonify({'error': 'An error occurred while making the request', 'msg': e, 'status_code': 500}), 500
