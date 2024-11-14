import hashlib
import jwt
import psycopg2
from flask import Flask, request, jsonify
from functools import wraps
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = '598474ea66434fa7992d54ff8881e7c2'

def require_token():
  def decorator(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
      token = request.args.get('token')
      if not token:
        return jsonify({'error': 'Chýba token!'}), 401
      try:
        payload = jwt.decode(token, app.config['SECRET_KEY'])
      except:
        return jsonify({'error': 'Token je neplatný!'}), 401
    return wrapper
  return decorator

def connect_to_db():
  try:
    db_con = psycopg2.connect("dbname='postgres' user='postgres' host='localhost' password='<DB_ICLS_PASSWORD>'")
    cur = db_con.cursor()
    return db_con, cur
  except psycopg2.Error as e:
    return None, e

@app.route('/login', methods=['POST'])
def login():
  username=request.form.get('username')
  password=request.form.get('password')
  if not username or not password:
    return jsonify({'error': 'Chýba meno alebo heslo!'}), 401

  db_conn, cur = connect_to_db()
  if db_conn is None:
    return jsonify({'error': cur}), 501

  salt = '$2b$12$4/ZiN3Ga8VQjxm9.K2V3/.'
  salted = salt+password+salt
  hashed = hashlib.sha256(salted.encode()).hexdigest()
  try:
    query = "SELECT role FROM users WHERE username = %s AND password = %s;"
    cur.execute(query, (username, hashed))
    res = cur.fetchone()

    if res is None:
      return jsonify({'error': 'Meno alebo heslo sú nesprávne!'}), 401
    else:
      token = jwt.encode({
        'user': username,
        'role': res[0],
        'exp': str(datetime.now() + timedelta(seconds=300)),
        },
        app.config['SECRET_KEY'])
      return jsonify({'token': token.decode('utf-8')}), 200

  finally:
    cur.close()
    db_conn.close()

@app.route('/reports', methods = ['POST'])
@require_token()
def reports():
  connect_to_db()
  sql_string = "select * from reports;"
  # the app will just use the url to get the file instead
  # you need to just  retun
  return {
    'name':
    'url':
  }
