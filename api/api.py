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
        return jsonify({'error': 'Token is missing'}), 401
      try:
        payload = jwt.decode(token, app.config['SECRET_KEY'])
      except:
        return jsonify({'error': 'Token is invalid'}), 401
    return wrapper
  return decorator

@app.route('/login', methods=['POST'])
def login():
  username=request.form.get('username')
  password=request.form.get('password')
  if not username or not password:
    return jsonify({'error': 'Username or password is missing'}), 401
  db_con = psycopg2.connect("dbname='postgres' user='postgres' host='localhost' password='<DB_ICLS_PASSWORD>'")
  cur = db_con.cursor()
  