import requests
import os
import jwt
from flask import session, jsonify

API_SECRET = os.getenv('API_SECRET_KEY')

def sign_in_api_call(email, password):
    payload = {"username": email, "password": password}
    try:
        response = requests.post(
            url='https://icls.sosit-wh.net/v2/auth/login',
            data=payload
        )
        if response.status_code == 500:
            return {'error': 'danger', 'msg': 'Nastala serverová chyba, kontaktujre prosím administrátora!', 'status_code': response.status_code}
        if response.status_code == 401:
            return {'error': 'warning', 'msg': 'Neplatné meno alebo heslo!', 'status_code': response.status_code}

        resp = response.json()
        raw_token = jwt.decode(resp['token'], API_SECRET, algorithms=['HS256'])

        session['email'] = email
        session['name'] = raw_token['name']
        session['token'] = resp['token']
        session['role'] = raw_token['role']
        session.permanent = True

        return {'error': 'success', 'msg': 'Prihlásenie bolo úspešné!', 'status_code': response.status_code}

    except requests.exceptions.RequestException as e:
        return {'error': 'danger', 'msg': e, 'status_code': 500}
