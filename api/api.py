import hashlib
import jwt
import psycopg2
from flask import Flask, request, jsonify
from functools import wraps
from datetime import datetime, timedelta

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
    db_con = psycopg2.connect("dbname='postgres' user='postgres' host='' password='<DB_ICLS_PASSWORD>'")
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
def reports():
  con, cur = connect_to_db()
  
  reports = []
  sql_string = "select * from reports;"
  # the app will just use the url to get the file instead
  # you need to just  return
  result = cur.execute(sql_string)
  
  for i in result:
    reports.append( {"name": i[1], "url": i[2]} )
  con.close()

  return {
    'reports': reports
  }


@app.route('/lease_car', methods = ['POST'])
def lease_car():
  # check token, 
  # can the car be leased, 
  # is the user a manager 
  # (compare the user leasing and user thats recieving the lease, 
  # if the user leasing is a manager and has the manager token, allow it.)
  # we need: 
  # the reserver
  # the user recieving the reservation
  # time from
  # time to
  # private ride?
  data = request.get_json()
  user = data["user"]
  time_now = data["time_now"]
  time_till = data["time_till"]
  private = data["private"]

  con, cur = connect_to_db()
  con.close()
  # Then we return a confirmation of order
  # so we can show a return car option
  return {
    "status": "ordered",
    "private": True
  }

@app.route('/return_car', methods = ['POST'])
def return_car():
  # check if a lease exist in the DB
  # check if the user is either a manager or the reservist
  # if yes, delete/mark it as complete
  # if not a private ride save the return location
  # save the note
  # change the leased car status to free, and change its location driver and use metric

  pass




if __name__ == "__main__":
  app.run()