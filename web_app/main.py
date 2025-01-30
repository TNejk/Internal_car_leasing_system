import sys, os
sys.path.append('controllers')
sys.path.append('workers')
from flask import Flask, render_template, request, redirect, url_for, jsonify, session
from require_role import require_role
from request_all_car_data import request_all_car_data
from sign_in_api import sign_in_api
from check_token import check_token
from request_user_leases import request_user_leases

SECRET_KEY = os.getenv('SECRET_KEY')
SALT = os.getenv('SALT')
SALT = '%2b%12%4/ZiN3Ga8VQjxm9.K2V3/.'

app = Flask(__name__)
app.config['SECRET_KEY'] = '3ccef32a4991129e86b6f80611a3e1e5287475c27d7ab3a8e26d122862119c49'

@app.route('/')
def index():
  return redirect('/sign-in')

@app.route('/sign-in', methods=['GET','POST'])
def sign_in():
  if request.method == 'GET':
    return render_template('signs/sign_in.html')
  else:
    username = request.form['email']
    password = request.form['password']
    result = sign_in_api(username, password, SALT)
    if result == 'success':
      return redirect('/dashboard')
    else:
      return render_template('signs/sign_in.html', data=result)

@app.route('/sign-up', methods=['GET', 'POST'])
def sign_up():
  if request.method == 'GET':
    error = 'Nesprávne meno alebo heslo!'
    return render_template('signs/sign_in.html', error=error)
  else:
    data = request.get_json()
    username = data['email']
    password = data['password']
    session['username'] = username
    session['password'] = password
    session['role'] = 'user'
    return redirect('/dashboard')

@app.route(f'/dashboard', methods=['GET'])
@require_role('user','manager')
#@check_token() # nefunguje
def dashboard():
  bell = url_for('static', filename='sources/images/bell.svg')
  user = url_for('static', filename='sources/images/user.svg')
  settings = url_for('static', filename='sources/images/settings.svg')
  location = request.args.get('location', None)
  cars = request_all_car_data(location)
  username = session['username']
  role = session['role']

  return render_template('dashboards/dashboard.html', cars = cars, token=session.get('token'), icons = [bell, user, settings], username=username, role=role)

@app.route(f'/reservations', methods=['GET', 'POST'])
@require_role('user','manager')
#@check_token() # nefunguje
def reservations():
  bell = url_for('static', filename='sources/images/bell.svg')
  user = url_for('static', filename='sources/images/user.svg')
  settings = url_for('static', filename='sources/images/settings.svg')
  leases = request_user_leases(session['username'],session['role'])
  print(leases)
  return render_template('dashboards/reservations.html', leases=leases, icons = [bell, user, settings], username=session['username'], role=session['role'])


@app.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('role', None)
    session.pop('token', None)
    session.pop('password', None)
    return redirect(url_for('sign_in'))

@require_role('user','manager')
@app.route('/get_session_data', methods=['POST'])
def get_session_data():
    data = {
      'username': session.get('username'),
      'password': session.get('password'),
      'token': session.get('token'),
      'role': session.get('role')
    }
    return jsonify(data)

if __name__ == '__main__':
    app.run(debug=True)


if __name__ == '__main__':
  app.run(debug=True, use_reloader=True)