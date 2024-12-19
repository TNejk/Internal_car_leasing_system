import os, requests, hashlib
from flask import session, render_template

def sign_in_api(username, password, SALT):
    payload = {"username": username, "password": password}
    try:
        response = requests.post(
            url='https://icls.sosit-wh.net/login',
            json=payload
        )
        response = response.json()
        print(response)
        if response is None:
            return render_template('signs/sign_out.html', data='Niekde sa stala chyba!')
        if 'type' in response:
            if response['type'] == 0:
                return render_template('signs/sign_in.html', data='Chýba meno alebo heslo!')
            elif response['type'] == 1:
                return render_template('signs/sign_in.html', data='Nesprávne meno alebo heslo!')
        salted = SALT + SALT + SALT + SALT + SALT + SALT + SALT + SALT + SALT + password + SALT + SALT + SALT + SALT + SALT
        hashed = hashlib.sha256(salted.encode()).hexdigest()
        session['username'] = username
        session['password'] = hashed
        session['token'] = response['access_token']
        session['role'] = response['role']
        session.permanent = True

    except requests.exceptions.RequestException as e:
        print("An error occurred while making the request:", e)
        return None
