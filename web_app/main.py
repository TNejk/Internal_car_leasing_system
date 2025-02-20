import sys, os
from flask import Flask, render_template, request, redirect, url_for, jsonify, session
sys.path.append('controllers')
from check_token import check_token
from require_role import require_role
from revoke_token import revoke_token
sys.path.append('workers')
from request_all_car_data import request_all_car_data
from sign_in_api import sign_in_api
from request_user_leases import request_user_leases
from list_reports import list_reports
from get_report import get_report
from request_monthly_leases import request_monthly_leases
sys.path.append('misc')
from load_icons import load_icons

SECRET_KEY = os.getenv('SECRET_KEY')
SALT = os.getenv('SALT', '%2b%12%4/ZiN3Ga8VQjxm9.K2V3/.')


app = Flask(__name__)
app.config['SECRET_KEY'] = '3ccef32a4991129e86b6f80611a3e1e5287475c27d7ab3a8e26d122862119c49'

@app.route('/')
def index():
  return redirect('/sign-in')

@app.route('/sign-in', methods=['GET','POST'])
@revoke_token()
def sign_in():
  if request.method == 'GET':
    return render_template('signs/sign_in.html')
  else:
    username = request.form['email']
    password = request.form['password']
    result = sign_in_api(username, password, SALT)
    if result == 'success':
      if session.get('role') == 'user':
        return redirect('/dashboard')
      elif session.get('role') == 'manager':
        return redirect('/manager/dashboard')
      elif session.get('role') == 'admin':
        return redirect('/admin/dashboard')
    else:
      return render_template('signs/sign_in.html', data=result, show_header=False)

@app.route('/sign-up', methods=['GET', 'POST'])
@revoke_token()
def sign_up():
  if request.method == 'GET':
    error = 'Nesprávne meno alebo heslo!'
    return render_template('signs/sign_in.html', error=error, show_header=False)
  else:
    data = request.get_json()
    username = data['email']
    password = data['password']
    # sprav funkciu
    return redirect('/dashboard')

@app.route('/manager/dashboard', methods=['GET', 'POST'])
@require_role('manager')
def manager_dashboard():
  return render_template('dashboards/dashboard.html', icons = load_icons(), show_header=True, role = session.get('role'))

@app.route('/lease', methods=['GET'])
@require_role('user','manager')
def lease():
  location = request.args.get('location', None)
  cars = request_all_car_data(location)
  username = session['username']
  role = session['role']

  return render_template('dashboards/lease.html', cars = cars, token=session.get('token'), icons = load_icons(), username=username, role=role, show_header=True)

@app.route(f'/reservations', methods=['GET', 'POST'])
@require_role('user','manager')
@check_token()
def reservations():
  leases = request_user_leases(session['username'],session['role'])
  return render_template('dashboards/reservations.html', leases=leases, icons = load_icons(), username=session['username'], role=session['role'], show_header=True)

@app.route('/get_user_leases', methods=['GET', 'POST'])
@require_role('user', 'manager')
@check_token()
def get_user_leases():
  data = request_user_leases(session['username'], session['role'])
  return jsonify(data)

@app.route('/manager/get_monthly_leases', methods=['GET', 'POST'])
@require_role('manager')
@check_token()
def get_monthly_leases():
  data = request_monthly_leases(session['role'])
  return jsonify(data)

@app.route(f'/manager/reports', methods=['GET', 'POST'])
@require_role('manager')
@check_token()
def reports():
  data = list_reports(session['username'], session['role'])
  return render_template('dashboards/reports.html', icons = load_icons(), data=data, show_header=True)

@app.route(f'/manager/get_report', methods=['GET', 'POST'])
@require_role('manager')
@check_token()
def get_report_r():
  report = request.args.get('report', None)
  email = session['username']
  role = session['role']
  returned_report = get_report(email,role,report)
  return returned_report

@app.route('/get_session_data', methods=['POST'])
@require_role('user','manager')
@check_token()
def get_session_data():
    data = {
      'username': session.get('username'),
      'password': session.get('password'),
      'token': session.get('token'),
      'role': session.get('role')
    }
    return jsonify(data)

@app.route('/save_notification', methods=['POST'])
@require_role('user','manager')
def save_notification():
  data = request.get_json()
  session['notifications'] = [data['notifications']]
  return jsonify("success")

@app.route('/get_notifications', methods=['POST'])
@require_role('user','manager')
def get_notifications():
  data = session['notifications']
  return jsonify(data)

@app.route('/logout')
@revoke_token()
def logout():
    return redirect(url_for('sign_in'))

if __name__ == '__main__':
  app.run(debug=True, use_reloader=True)