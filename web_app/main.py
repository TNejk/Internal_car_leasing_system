import sys
sys.path.append('controllers')
from flask import Flask, render_template, request, redirect, url_for, jsonify, session
from require_role import require_role

app = Flask(__name__)
app.config['SECRET_KEY'] = '3ccef32a4991129e86b6f80611a3e1e5287475c27d7ab3a8e26d122862119c49'

@app.route('/sign-in', methods=['GET', 'POST'])
def sign_in():
  if request.method == 'GET':
    error = 'fakovy error :)'
    return render_template('signs/sign_in.html', error=error)
  else:
    username = request.form['email']
    password = request.form['password']
    session['username'] = username
    session['password'] = password
    session['role'] = 'user'
    return redirect('/dashboard')

@app.route('/sign-up', methods=['GET', 'POST'])
def sign_up():
  if request.method == 'GET':
    error = 'fakovy error :)'
    return render_template('signs/sign_in.html', error=error)
  else:
    username = request.form['email']
    password = request.form['password']
    session['username'] = username
    session['password'] = password
    session['role'] = 'user'
    return redirect('/dashboard')

@app.route(f'/dashboard', methods=['GET', 'POST'])
@require_role('user','manager')
def dashboard():
  return render_template('dashboards/dashboard.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('role', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
  app.run(debug=True, use_reloader=True)