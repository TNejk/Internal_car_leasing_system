import os
import hashlib
import jwt
import psycopg2
from flask import Flask, request, jsonify
from flask_jwt_extended import JWTManager, create_access_token, create_refresh_token, jwt_required, get_jwt_identity, get_jwt
from flask_cors import CORS
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

CORS(app, supports_credentials=True, resources={
    r"/get_full_car_info": {
        "origins": "http://127.0.0.1:5000",  # Change to your client app's origin
        "allow_headers": ["Authorization", "Content-Type"],
        "methods": ["GET", "POST", "OPTIONS"]
    }
})

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
    return jsonify({'error': 'Chábe meno alebo heslo!', 'type': 0}), 401

  conn, cur = connect_to_db()
  if conn is None:
    return jsonify({'error': cur, 'type': 1}), 501

  salted = login_salt+password+login_salt
  hashed = hashlib.sha256(salted.encode()).hexdigest()
  try:
    query = "SELECT role FROM driver WHERE email = %s AND password = %s;"
    cur.execute(query, (username, hashed))
    res = cur.fetchone()

    if res is None:
      return jsonify({'error': 'Nesprávne meno alebo heslo!', 'type': 0}), 401
    else:
      additional_claims = {'role': res[0]}
      access_token = create_access_token(identity=username, fresh=True, expires_delta=timedelta(minutes=30), additional_claims=additional_claims)
      # refresh_token = create_refresh_token(identity=username, expires_delta=timedelta(days=1), additional_claims=additional_claims)
      # return jsonify(access_token=access_token, refresh_token=refresh_token), 200
      return jsonify(access_token=access_token, role=res[0]), 200

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




# {
#     "users": [
#         {
#             "email": "gamo_icls@gamo.sk",
#             "role": "admin"
#         },]
# }
@app.route('/get_users', methods=['GET'])
@jwt_required()
def get_users():
    conn, cur = connect_to_db()
    try:
        cur.execute('SELECT email, role FROM driver;')  
        users = cur.fetchall()  
        ed_users = []
        for i in users:
            ed_users.append({
                "email": i[0],
                "role": i[1]
            })

        return {'users': ed_users}
    except Exception as e:

        return {"error": str(e)}, 500
    finally:
        cur.close()
        conn.close()


@app.route('/get_car_list', methods=['POST'])
@jwt_required()
def get_car_list():
  conn, cur = connect_to_db()
  if conn is None:
    return jsonify({'error': cur, 'status': 501}), 501
  try:
    data = request.get_json()
    location = request.args.get('location', 'none')
    if location != 'none':
      query = """
            SELECT id_car, name, status, url
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
                  SELECT id_car, name, status, url
                  FROM car
                  ORDER BY usage_metric ASC;
              """

    cur.execute(query, (location,) if location != 'none' else ())
    res = cur.fetchall()
    return jsonify({"car_details": res}), 200

  finally:
    cur.close()
    conn.close()

@app.route('/get_full_car_info', methods=['POST'])
@jwt_required()
def get_full_car_info():
  conn, cur = connect_to_db()
  if conn is None:
    return jsonify({'error': cur}), 501

  car = request.get_json()["car_id"]
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


# ROUTE TO GET ALL THE USERNAMES IF YOU ARE A MANAGER



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
  
  try:
    # need to get the car_id  and driver_id 
    cur.execute("select id_driver from driver where email = %s", (data["driver"],))
    id_name = cur.fetchall()[0][0]

    cur.execute("select id_car from car where name = %s", (data["car"],))
    id_car = cur.fetchall()[0][0]
  except Exception as e:
    return jsonify(msg= f"Error cancelling lease!, {e}")
  
  try:
    cur.execute("UPDATE lease SET status = false WHERE id_lease = (SELECT id_lease FROM lease WHERE id_driver = %s AND id_car = %s ORDER BY id_lease DESC LIMIT 1)", (id_name, id_car))
    cur.execute("update car set status = %s where id_car = %s", ("stand_by", id_car))
  except Exception as e:
    return jsonify(msg= f"Error cancelling lease!, {e}")

  conn.commit()
  conn.close()

  return {"cancelled": True}



@app.route('/lease_car', methods = ['POST'])
@jwt_required()
def lease_car():
  data =  request.get_json()

  # for whom the lease is 
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
  # This may be useless as the user result itself makes a check if a given person exists
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
    con.close()
    return {"status": True, "private": private}

  # If the user leasing is a manager allow him to order lease for other users
  elif user[0][3]  == role:
    try:
      cur.execute("insert into lease(id_car, id_driver, start_of_lease, end_of_lease, status) values (%s, %s, %s, %s, %s)", (car_data[0][0], user[0][0], timeof, timeto, True))
      cur.execute("update car set status = %s where name = %s", ("leased", car_name,))
      con.commit()
    except Exception as e:
      return jsonify(msg= f"Error occured when leasing. {e}")
    con.close()
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

  conn, error = connect_to_db()
  if conn is None:
    return jsonify({'error': error}), 501

  try:
    with conn.cursor() as cur:
      # Check if a lease exists in the DB
      query = "SELECT * FROM lease WHERE id_lease = %s;"
      cur.execute(query, (id_lease,))
      res = cur.fetchall()
      if not res:
        return jsonify({'error1': 'Jazda už neexistuje!'}), 501

      # Update the lease table
      query = "UPDATE lease SET status = %s, time_of_return = %s, note = %s WHERE id_lease = %s;"
      cur.execute(query, (False, tor, note, id_lease))

      # Get the car ID
      query = "SELECT id_car FROM lease WHERE id_lease = %s;"
      cur.execute(query, (id_lease,))
      id_car, = cur.fetchone()

      # Update the car table
      um = _usage_metric(id_car, conn)
      query = "UPDATE car SET health = %s, status = %s, usage_metric = %s WHERE id_car = %s;"
      cur.execute(query, (health, 'stand_by', um, id_car))

    conn.commit()
    return f'stand_by, {health}, {um}, {tor}, {id_car}'

  except psycopg2.Error as e:
    conn.rollback()
    return jsonify({'error': str(e)}), 501
  finally:
    conn.close()


def _usage_metric(id_car, conn):
  try:
    with conn.cursor() as cur:
      # Get the latest lease start time
      query = "SELECT start_of_lease FROM lease WHERE id_car = %s ORDER BY id_lease DESC LIMIT 1;"
      cur.execute(query, (id_car,))
      result = cur.fetchone()
      if not result:
        return 1  # Default metric if no leases exist
      start_of_lease = result[0]

      # Fetch leases from the past 14 days
      query = """
                  SELECT start_of_lease, time_of_return 
                  FROM lease 
                  WHERE id_car = %s AND start_of_lease >= %s - INTERVAL '14 days';
                  """
      cur.execute(query, (id_car, start_of_lease))
      leases = cur.fetchall()

    hours = 0.0
    num_of_leases = len(leases)
    for lease in leases:
      # Skip processing if time_of_return is None
      if lease[1] is None:
        continue
      try:
        time1 = datetime.fromisoformat(str(lease[1]))  # Proper parsing with timezone
        time2 = datetime.fromisoformat(str(lease[0]))
      except ValueError as e:
        print(f"Error parsing lease times: {e}")
        continue
      difference = time1 - time2
      hours += difference.total_seconds() / 3600

    # Return metric based on lease count and hours
    if num_of_leases <= 2 or hours <= 48.0:
      return 1
    elif 3 <= num_of_leases <= 4 or hours <= 72.0:
      return 2
    elif 5 <= num_of_leases <= 7 or hours <= 144.0:
      return 3
    elif 8 <= num_of_leases <= 11 or hours <= 288.0:
      return 4
    else:
      return 5

  except psycopg2.Error or Exception as e:
    return jsonify({'error': str(e)}), 501


# @app.route('/token_test', methods = ['POST'])
# @jwt_required()
# def token_test():
#   claims = get_jwt()
#   role = claims.get('role', 'Nenašla sa žiadna rola')
#   return jsonify({'identity': get_jwt_identity(),
#                   'additional_claims': role}), 200

if __name__ == "__main__":
  app.run()