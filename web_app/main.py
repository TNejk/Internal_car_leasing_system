import sys, os
sys.path.append('controllers')
sys.path.append('workers')
from flask import Flask, render_template, request, redirect, url_for, jsonify, session
from require_role import require_role
from request_all_car_data import request_all_car_data
from sign_in_api import sign_in_api
from check_token import check_token

SECRET_KEY = os.getenv('SECRET_KEY')
SALT = os.getenv('SALT')
SALT = '7tqeo@#%%^&*(n7irqcnw78oaieNOQIE73124@#%%^&*NCo'

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
    sign_in_api(username, password, SALT)

    return redirect('/dashboard')

@app.route('/sign-up', methods=['GET', 'POST'])
def sign_up():
  if request.method == 'GET':
    error = 'fake error :)'
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
@check_token()
def dashboard():
  bell = url_for('static', filename='sources/images/bell.svg')
  user = url_for('static', filename='sources/images/user.svg')
  settings = url_for('static', filename='sources/images/settings.svg')
  location = request.args.get('location', None)
  cars = request_all_car_data(location)

  return render_template('dashboards/dashboard.html', cars = cars, token=session.get('token'), icons = [bell, user, settings])

@app.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('role', None)
    return redirect(url_for('login'))


if __name__ == '__main__':
  app.run(debug=True, use_reloader=True)