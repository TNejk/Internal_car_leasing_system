import os, requests, hashlib
from flask import session, render_template, jsonify


def sign_in_api(username, password, SALT):
    payload = {"username": username, "password": password}
    try:
        response = requests.post(
            url='https://icls.sosit-wh.net/login',
            json=payload
        )
        response = response.json()
        if response is None:
            return 'Niekde nastala chyba!'
        if 'type' in response:
            if response['type'] == 0:
                return 'Nesprávne meno alebo heslo!'
            elif response['type'] == 1:
                return 'Chýba meno alebo heslo!'
            else:
                return 'Niečo je zle!'

        salted = SALT + password + SALT
        hashed = hashlib.sha256(salted.encode()).hexdigest()
        session['username'] = username
        session['password'] = hashed
        session['token'] = response['access_token']
        session['role'] = response['role']
        session.permanent = True

        return 'success'

    except requests.exceptions.RequestException as e:
        print("An error occurred while making the request:", e)
        return None
