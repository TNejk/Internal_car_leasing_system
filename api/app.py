import os
import hashlib
import jwt
import psycopg2
from flask import Flask, request, jsonify
from flask_jwt_extended import JWTManager, create_access_token, create_refresh_token, jwt_required, get_jwt_identity, get_jwt
from functools import wraps
from datetime import datetime, timedelta




db_host = os.getenv('DB_HOST')
db_port = os.getenv('DB_PORT')
db_user = os.getenv('POSTGRES_USER')
db_pass = os.getenv('POSTGRES_PASS')
db_name = os.getenv('POSTGRES_DB')
app_secret_key = os.getenv('APP_SECRET_KEY')
login_salt = os.getenv('LOGIN_SALT')

app = Flask(__name__)
app.config['SECRET_KEY'] = app_secret_key

jwt_manager = JWTManager(app)

def connect_to_db():
  try:
    db_con = psycopg2.connect(dbname=db_name, user=db_user, host=db_host, port=db_port, password=db_pass)
    cur = db_con.cursor()
    return db_con, cur
  except psycopg2.Error as e:
    return None, str(e)


# headers = {
#     "Authorization": f"Bearer {jwt_token}",
#     "Content-Type": "application/json"  # Ensure the server expects JSON
# }
# Callback function to check if a JWT exists in the database blocklist
@jwt_manager.token_in_blocklist_loader
def check_if_token_revoked(jwt_header, jwt_payload: dict) -> bool: # None if an error happnes or a borken poipo
    jwt = jwt_header
    jti = jwt_payload["jti"]

    conn, cur = connect_to_db()
    try:
      cur.execute("select * from revoked_jwt where jti = %s", (jti,))
      result = cur.fetchone()

    except Exception as e:
      return jsonify({'error': cur})

    conn.close()
    return result is not None



@app.route("/logout", methods=["POST"])
@jwt_required()
def modify_token():
    jti = get_jwt()["jti"]
    now = datetime.now()
    conn, cur = connect_to_db()
    try:
      cur.execute("insert into revoked_jwt(jti, added_at) values (%s, %s)", (jti, now))
      conn.commit()
    except Exception as e:
      return jsonify(msg= f"Error rewoking JWT!:  {e}")

    conn.close()
    return jsonify(msg="JWT revoked")



@app.route('/login', methods=['POST'])
def login():
  data = request.get_json()
  username=data['username']
  password=data['password']
  if not username or not password:
    return jsonify({'error': 'Chýba meno alebo heslo!'}), 401

  conn, cur = connect_to_db()
  if conn is None:
    return jsonify({'error': cur}), 501

  salted = login_salt+password+login_salt
  hashed = hashlib.sha256(salted.encode()).hexdigest()
  try:
    query = "SELECT role FROM driver WHERE email = %s AND password = %s;"
    cur.execute(query, (username, hashed))
    res = cur.fetchone()

    if res is None:
      return jsonify({'error': 'Meno alebo heslo sú nesprávne!'}), 401
    else:
      additional_claims = {'role': res[0]}
      access_token = create_access_token(identity=username, fresh=True, expires_delta=timedelta(minutes=30), additional_claims=additional_claims)
      # refresh_token = create_refresh_token(identity=username, expires_delta=timedelta(days=1), additional_claims=additional_claims)
      # return jsonify(access_token=access_token, refresh_token=refresh_token), 200
      return jsonify(access_token=access_token), 200

  finally:
    cur.close()
    conn.close()

# @app.route('/refresh', methods=['POST'])
# @jwt_required(refresh=True)
# def refresh():
#     claims = get_jwt()
#     role = claims.get('role', 'Nenašla sa žiadna rola')
#     current_user = get_jwt_identity()
#     additional_claims = {'role': role}
#     access_token = create_access_token(identity=current_user, expires_delta=timedelta(minutes=30), additional_claims=additional_claims)
#     return jsonify(access_token=access_token), 200

@app.route('/get_car_list', methods=['GET'])
@jwt_required()
def get_car_list():
  conn, cur = connect_to_db()
  if conn is None:
    return jsonify({'error': cur}), 501
  try:
    location = request.args.get('location', 'none')
    if location != 'none':
      query = """
            SELECT CONCAT(name, ';', status, ';', usage_metric, ';', location) AS car_details
            FROM car
            ORDER BY 
                CASE 
                    WHEN location = %s THEN 1 
                    ELSE 2 
                END,
                usage_metric ASC;
        """
    else:
      query = """
                  SELECT CONCAT(name, ';', status, ';', usage_metric, ';', location) AS car_details
                  FROM car
                  ORDER BY usage_metric ASC;
              """

    cur.execute(query, (location,) if location != 'none' else ())
    res = cur.fetchall()
    return jsonify({"car_details": [row[0] for row in res]}), 200

  finally:
    cur.close()
    conn.close()

@app.route('/get_full_car_info', methods=['GET'])
@jwt_required()
def get_full_car_info():
  conn, cur = connect_to_db()
  if conn is None:
    return jsonify({'error': cur}), 501

  car = request.args.get('car', 'none')
  if car == 'none':
    return jsonify({'error': 'Chýba parameter: car'}), 501
  query = ("SELECT * FROM car WHERE id_car = %s;")
  cur.execute(query, (car,))
  res = cur.fetchall()
  return jsonify({"car_details": res}), 200

@app.route('/reports', methods = ['POST'])
#! ADD @jwt_required() AFTER IT WORKS TO LOOK FOR TOKEN FOR SECURITY
def reports():
  con, cur = connect_to_db()
  if con is None:
    return jsonify({'error': cur}), 501
  
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



@app.route('/allowed_dates', methods = ['GET'])
@jwt_required()
def allowed_dates():
  pass


@app.route('/cancel_lease', methods = ['POST'])
@jwt_required()
def cancel_lease():
  # make a sql statement that updates the table lease and sets it stauts to false where you will filter the result by the driver, car, and order by id_lease descending limit 1
  data = request.get_json()
  conn, cur = connect_to_db()
  
  cur.execute("UPDATE lease SET status = false WHERE id_lease = (SELECT id_lease FROM lease WHERE driver = %s AND car = %s ORDER BY id_lease DESC LIMIT 1)", (data["driver"], data["car"]))

@app.route('/lease_car', methods = ['POST'])
@jwt_required()
def lease_car():
  data =  request.get_json()

  username = str(data["username"])
  role = str(data["role"])
  car_name  = str(data["car_name"])
  private = data["is_private"]
  timeof = datetime.now()
  timeto = datetime.now() + timedelta(hours=1)


  con, cur = connect_to_db()

  # You dont need to check if you can reserve a car in a timeframe as the car would allready be in reserved status mode

  # STATUS CHECKER
  cur.execute("select status from car where name = %s", (car_name,))
  car_status = cur.fetchall()[0][0]
  if car_status != "stand_by":
    return jsonify(msg = f"Car is not available!, {car_status}")


  # USER CHECKER
  cur.execute("select * from driver where email = %s and role = %s", (username, role,))
  # user is a list within a list [[]] to access it use double [0][1,2,3,4]
  user = cur.fetchall()

  cur.execute("select * from car where name = %s", (car_name,))
  car_data = cur.fetchall()

  # compare the user leasing and user thats recieving the lease,
  if user[0][1] ==  username:
    # Priavte ride check
    if private == True:
      if user[0][3] == role:
        pass
      else: return jsonify("Users cannot order private rides!")

    try:
      # id, userid, carid, timeof, timeto, tiemreturn, status, note, status is either 1 or zero to indicate boolean values
      cur.execute("insert into lease(id_car, id_driver, start_of_lease, end_of_lease, status) values (%s, %s, %s, %s, %s)", (car_data[0][0], user[0][0], timeof, timeto, True))
      cur.execute("update car set status = %s where name = %s", ("leased", car_name,))
      con.commit()
    except Exception as e:
      return jsonify(msg= f"Error occured when leasing. {e}")

    return {"status": True, "private": private}

  # If the user leasing is a manager allow him to order lease for other users
  elif user[0][3]  == role:
    try:
      cur.execute("insert into lease(id_car, id_driver, start_of_lease, end_of_lease, status) values (%s, %s, %s, %s, %s)", (car_data[0][0], user[0][0], timeof, timeto, True))
      cur.execute("update car set status = %s where name = %s", ("leased", car_name,))
      con.commit()
    except Exception as e:
      return jsonify(msg= f"Error occured when leasing. {e}")

    return {"status": True, "private": private}
  else:
    return jsonify(msg= "Users do not match, nor is the requester a manager.")


@app.route('/return_car', methods = ['POST'])
#! ADD @jwt_required() AFTER IT WORKS TO LOOK FOR TOKEN FOR SECURITY
def return_car():
  data = request.get_json()
  if not data:
    return jsonify({'error': 'No data'}), 501

  id_lease = data["id_lease"]
  tor = data["time_of_return"]
  health = data["health"]
  note = data["note"]

  conn, cur = connect_to_db()
  if conn is None:
    return jsonify({'error': cur}), 501

  # check if a lease exist in the DB
  try:
    query = ("SELECT * FROM lease WHERE id_lease = %s;")
    cur.execute(query, (id_lease,))
    res = cur.fetchall()
    if not res:
      cur.close()
      conn.close()
      return jsonify({'error': 'Jazda už neexistuje!'}), 501
  except psycopg2.Error as e:
    cur.close()
    conn.close()
    return jsonify({'error': str(e)}), 501

  # update the lease table with change of status, time_of_return and note
  try:
    query = "UPDATE lease SET status = %s, time_of_return = %s, note = %s WHERE id_lease = %s;"
    cur.execute(query, (False, tor, note, id_lease))
    conn.commit()
  except psycopg2.Error as e:
    cur.close()
    conn.close()
    return jsonify({'error': str(e)}), 501

  # get the car id
  try:
    query = ("SELECT id_car FROM lease WHERE id_lease = %s;")
    cur.execute(query, (id_lease,))
    id_car = cur.fetchall()
  except psycopg2.Error as e:
    cur.close()
    conn.close()
    return jsonify({'error': str(e)}), 501

  # update the car table with chnage of car status, health and calculate the metric
  try:
    um = _usage_metric(id_car, conn, cur)
    query = ("UPDATE car SET health = %s, status = %s, usage_metric = %s WHERE id_car = %s;")
    cur.execute(query, (health, 'stand_by', um, tor, id_car))
    con.commit()
  except psycopg2.Error as e:
    return jsonify({'error': str(e)}), 501
  finally:
    cur.close()
    conn.close()
    return jsonify({'status': 'stand_by', 'health': health, 'um': um, 'timenow': tor, 'id_car': id_car}), 201

def _usage_metric(id_car, conn, cur):
  try:
    query = ("SELECT start_of_lease FROM lease ORDER BY id_lease DESC LIMIT 1 WHERE id_car = %s;")
    cur.execute(query)
    start_of_lease = cur.fetchone()[0][0]
    query = ("SELECT start_of_lease, time_of_return FROM lease WHERE id_car = %s AND %s - start_of_lease >= $s;")
    cur.execute(query, (id_car, start_of_lease, '14 days'))
    res = cur.fetchall()
    res = [row[0] for row in res]
  except psycopg2.Error as e:
    cur.close()
    conn.close()
    return jsonify({'error': str(e)}), 501

  num_of_leases = len(res) # max should be 14
  hours = 0.0 # max should be 336.0
  for lease in res:
    lease[1] -= lease[0]
    hours += lease[1]

  if num_of_leases <= 2 and hours <= 48.0:
    return 1
  elif 3 <= num_of_leases <= 4 and hours <= 72.0:
    return 2
  elif 5 <= num_of_leases <= 7 and hours <= 144.0:
    return 3
  elif 8 <= num_of_leases <= 11 and hours <= 288.0:
    return 4
  else:
    return 5


# @app.route('/token_test', methods = ['POST'])
# @jwt_required()
# def token_test():
#   claims = get_jwt()
#   role = claims.get('role', 'Nenašla sa žiadna rola')
#   return jsonify({'identity': get_jwt_identity(),
#                   'additional_claims': role}), 200

if __name__ == "__main__":
  app.run()