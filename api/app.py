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

app = Flask(__name__)
app.config['SECRET_KEY'] = '598474ea66434fa7992d54ff8881e7c2'
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
  username=request.args.get('username')
  password=request.args.get('password')
  if not username or not password:
    return jsonify({'error': 'Chýba meno alebo heslo!'}), 401

  conn, cur = connect_to_db()
  if conn is None:
    return jsonify({'error': cur}), 501

  salt = '$2b$12$4/ZiN3Ga8VQjxm9.K2V3/.'
  salted = salt+password+salt
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


@app.route('/lease_car', methods = ['POST'])
@jwt_required() #AFTER IT WORKS TO LOOK FOR TOKEN FOR SECURITY
def lease_car():
  data =  request.get_json()

  username = data["username"]
  role = data["role"]
  car_name  = data["car_name"]
  private = data["is_private"]
  timeof = datetime.now()
  timeto = datetime.now() + timedelta(hours=1)
  note = data["note"]

  con, cur = connect_to_db()
  
  # You dont need to check if you can reserve a car in a timeframe as the car would allready be in reserved status mode 

  # STATUS CHECKER
  cur.execute("select (status) from lease where name = %s", (car_name))
  car_status = cur.fetchone()
  if car_status != "stand_by":
    return jsonify(msg = "Car is not available!")

  
  # USER CHECKER 
  cur.execute("select * from users where name = %s and role = %s", (username, role))
  user = cur.fetchone()
  user_id = user[0]

  cur.execute("select id from cars where name = %s", (car_name,))
  car_data = cur.fetchone()

  # compare the user leasing and user thats recieving the lease,
  if user[1] ==  username:
    # Priavte ride check
    if private == True:
      if user[3] == role:
        pass
      else: return jsonify("Users cannot order private rides!")
    
    try:
      # id, userid, carid, timeof, timeto, tiemreturn, status, note
      cur.execute("insert into lease_car(id_car, id_driver, time_of_lease, time_to_lease, status, note) values (%s, %s, %s, %s, %s, %s,)", (user_id, car_id, timeof, timeto, status, note))
      cur.execute("update car set status = %s where name = %s", ("leased", car_name))
    except Exception as e:
      return jsonify(msg= f"Error occured when leasing. {cur}")

    return {"status": True, "private": private}
  
  # If the user leasing is a manager allow him to order lease for other users
  elif user[3]  == role:
    try:
      cur.execute("insert into lease_car values (%s, %s, %s, %s, %s, %s,)", (user_id, car_data[0], timeof, timeto, car_data[3], note))
      cur.execute("update car set status = %s where name = %s", ("leased", car_name))
    except Exception as e:
      return jsonify(msg= f"Error occured when leasing. {cur}")

    return {"status": True, "private": private}
  else: 
    return jsonify(msg= "Users do not match, nor is the requester a manager.")


@app.route('/return_car', methods = ['POST'])
#! ADD @jwt_required() AFTER IT WORKS TO LOOK FOR TOKEN FOR SECURITY
def return_car():
  # check if a lease exist in the DB
  # check if the user is either a manager or the reservist
  # if yes, delete/mark it as complete
  # if not a private ride save the return location
  # save the note
  # change the leased car status to free, and change its location driver and use metric

  pass


# @app.route('/token_test', methods = ['POST'])
# @jwt_required()
# def token_test():
#   claims = get_jwt()
#   role = claims.get('role', 'Nenašla sa žiadna rola')
#   return jsonify({'identity': get_jwt_identity(),
#                   'additional_claims': role}), 200

if __name__ == "__main__":
  app.run()