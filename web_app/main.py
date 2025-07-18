import os
import logging
from flask import Flask, render_template, request, redirect, url_for, jsonify, session, Response
from dotenv import load_dotenv

load_dotenv()
from misc import load_icons
from controllers import check_token, require_role, revoke_token
from workers import api_call, sign_in_api_call

SECRET_KEY = os.getenv('SECRET_KEY')

app = Flask(__name__)
app.config['SECRET_KEY'] = SECRET_KEY


@app.route('/')
def index():
  return redirect('/sign-in')


#################################
#       User and Manager        #
#################################

@app.route('/sign-in', methods=['GET', 'POST'])
@revoke_token()
def sign_in():
  if request.method == 'GET':
    return render_template('sign_in.html')
  else:
    email = request.form['email']
    password = request.form['password']
    result = sign_in_api_call(email, password)
    if result['status_code'] == 200:
      role = session.get('role')
      if role == 'user':
        return redirect('/user/dashboard')
      elif role == 'manager':
        return redirect('/manager/dashboard')
      elif role == 'admin':
        return redirect('/admin/dashboard')
      else:
        chyba = {'error': 'danger', 'msg': 'danger', 'status_code': 550}
        return render_template('sign_in.html', data=chyba)
    else:
      return render_template('sign_in.html', data=result, show_header=False)


@app.route('/logout')
@revoke_token()
def logout():
  return redirect(url_for('sign_in'))


@app.route('/user/dashboard', methods=['GET'])
@require_role('user')
def user_dashboard():
  return render_template('dashboards/dashboard.html', icons=load_icons(), email=session.get('email'),
                         role=session.get('role'), show_header=True)


@app.route('/lease', methods=['GET'])
@require_role('user', 'manager')
def lease():
  location = request.args.get('location', None)
  cars = api_call(method='GET', postfix='cars/get_cars', payload={'location': location})
  email = session['email']
  role = session['role']
  if session.get('role') == 'manager':
    users = api_call(method='GET', postfix='user/get_users')
    return render_template('dashboards/lease.html', users=users, cars=cars, token=session.get('token'),
                           icons=load_icons(), email=email, role=role, show_header=True)
  else:
    return render_template('dashboards/lease.html', cars=cars, token=session.get('token'),
                           icons=load_icons(), email=email, role=role, show_header=True)


@app.route(f'/reservations', methods=['GET', 'POST'])
@require_role('user', 'manager')
@check_token()
def reservations():
  filters = {'email': '', 'car_name': '', 'timeof': '', 'timeto': '', 'status': ''}
  leases = request_user_leases(session['role'], filters)
  return render_template('dashboards/reservations.html', leases=leases, icons=load_icons(),
                         email=session['email'], role=session['role'], show_header=True, theme=session.get('theme'))


@app.route('/get_user_leases', methods=['GET', 'POST'])
@require_role('user', 'manager')
@check_token()
def get_user_leases():
  filters = request.get_json()
  data = request_user_leases(session['role'], filters)
  return jsonify(data)


@app.route('/get_session_data', methods=['POST'])
@require_role('user', 'manager', 'admin')
@check_token()
def get_session_data():
  data = {
    'email': session.get('email'),
    'password': session.get('password'),
    # 'token': session.get('token'),
    'role': session.get('role')
  }
  return jsonify(data)


@app.route('/return_car', methods=['POST'])
@require_role('user', 'manager')
def return_car_p():
  data = request.get_json()
  response = return_car(data)
  return response


@app.route('/cancel_lease', methods=['POST'])
@require_role('user', 'manager')
def cancelLease():
  data = request.get_json()
  response = cancel_lease(data)
  return response


@app.route('/notifications', methods=['POST'])
@require_role('user', 'manager')
def get_notification():
  response = notifications()
  return response


#################################
#            Manager            #
#################################

@app.route('/manager/dashboard', methods=['GET', 'POST'])
@require_role('manager')
def manager_dashboard():
  return render_template('dashboards/manager/dashboard.html', icons=load_icons(), show_header=True,
                         role=session.get('role'), theme=session.get('theme'))


@app.route('/manager/get_monthly_leases', methods=['POST'])
@require_role('manager')
@check_token()
def get_monthly_leases():
  data = request.get_json()
  month = data['month']
  data = request_monthly_leases(month)
  return jsonify(data)


@app.route(f'/manager/reports', methods=['GET'])
@require_role('manager')
@check_token()
def reports():
  return render_template('dashboards/manager/reports.html', icons=load_icons(), show_header=True, role=session['role'],
                         theme=session.get('theme'))


@app.route('/manager/get_all_reports', methods=['GET'])
@require_role('manager')
@check_token()
def get_all_reports():
  data = list_reports(session['email'], session['role'])
  return jsonify(data)


@app.route('/manager/get_report', methods=['GET'])
@require_role('manager')
@check_token()
def get_report_r():
  try:
    data = request.args.get('report')
    response = get_report(data)
    return response

  except Exception as e:
    logging.error(f"Error in get_report_r: {str(e)}")
    return {"msg": f"Server error: {str(e)}"}, 500


@app.route('/get_cars', methods=['POST'])
@require_role('manager', 'user')
@check_token()
def get_car_list():
  data = get_all_cars(session['email'], session['role'])
  return data


@app.route('/get_users', methods=['POST'])
@require_role('manager')
@check_token()
def get_users():
  data = get_all_users(session['email'], session['role'])
  return data


@app.route('/get_cars', methods=['POST'])
@require_role('manager', 'user')
@check_token()
def get_cars():
  data = get_all_cars(session['email'], session['role'])
  return data


@app.route('/manager/private_requests', methods=['GET'])
@require_role('manager')
@check_token()
def private_requests():
  return render_template('dashboards/manager/private_requests.html', icons=load_icons(), show_header=True,
                         role=session.get('role'), theme=session.get('theme'))


@app.route('/manager/get_requests', methods=['GET'])
@require_role('manager')
@check_token()
def get_requests_d():
  return get_requests()


@app.route('/manager/approve_requests', methods=['POST'])
@require_role('manager')
@check_token()
def approve_requests_d():
  data = request.get_json()
  response = approve_requests(data)
  return response


#################################
#             Admin             #
#################################

@app.route('/admin/dashboard', methods=['GET', 'POST'])
@require_role('admin')
@check_token()
def admin_dashboard():
  return render_template('dashboards/admin/dashboard.html', icons=load_icons(), show_header=True,
                         role=session.get('role'), theme=session.get('theme'))


@app.route('/admin/get_car_list', methods=['POST'])
@require_role('admin')
@check_token()
def admin_get_car_list():
  data = get_all_car_info(session['email'], session['role'])
  return data


@app.route('/admin/get_user_list', methods=['POST'])
@require_role('admin')
@check_token()
def admin_get_user_list():
  data = get_all_user_info(session['email'], session['role'])
  return data


@app.route('/admin/create_car', methods=['POST'])
@require_role('admin')
@check_token()
def admin_create_car():
  data = request.get_json()
  print(data['image'])
  response = create_car(data)
  return response


@app.route('/admin/update_car', methods=['POST'])
@require_role('admin')
@check_token()
def admin_edit_car():
  data = request.json
  response = edit_car(data)
  return response


@app.route('/admin/delete_car', methods=['POST'])
@require_role('admin')
@check_token()
def admin_delete_car():
  data = request.get_json()
  response = delete_car(data)
  return response


@app.route('/admin/decommission', methods=['POST'])
@require_role('admin')
@check_token()
def admin_decommission():
  data = request.json
  response = decommission(data)
  return response


@app.route('/admin/activation', methods=['POST'])
@require_role('admin')
@check_token()
def admin_activation():
  data = request.json
  response = activation(data)
  return response


@app.route('/admin/create_user', methods=['POST'])
@require_role('admin')
@check_token()
def admin_add_user():
  data = request.get_json()
  response = create_user(data)
  return response


@app.route('/admin/update_user', methods=['POST'])
@require_role('admin')
@check_token()
def admin_update_user():
  data = request.json
  response = edit_user(data)
  return response


@app.route('/admin/delete_user', methods=['POST'])
@require_role('admin')
@check_token()
def admin_delete_user():
  data = request.get_json()
  response = delete_user(data)
  return response


if __name__ == '__main__':
  app.run(debug=True, use_reloader=True)
