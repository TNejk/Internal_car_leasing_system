import base64
import csv
import os
import hashlib
import jwt
from dateutil import parser 
import psycopg2
from flask_mail import Mail, Message
from flask import Flask, request, jsonify, send_from_directory
import requests
from excel_writer import writer
from flask_jwt_extended import JWTManager, create_access_token, create_refresh_token, jwt_required, get_jwt_identity, get_jwt
from flask_cors import CORS, cross_origin
from functools import wraps
from datetime import datetime, timedelta, timezone
from dateutil.parser import parse
import pytz
import openpyxl
from openpyxl.styles import Font, PatternFill, Border, Side, Alignment
from openpyxl import Workbook
import glob
import firebase_admin
from firebase_admin import credentials
from firebase_admin import messaging

import smtplib, ssl

def send_firebase_message_safe(message):
    """Send Firebase message with error handling."""
    try:
        messaging.send(message)
        return True
    except Exception as e:
        print(f"ERROR: Failed to send Firebase message: {e}")
        return False

bratislava_tz = pytz.timezone('Europe/Bratislava')

mail_api_key = os.getenv("MAIL_API_KEY")
db_host = os.getenv('DB_HOST')
db_port = os.getenv('DB_PORT')
db_user = os.getenv('POSTGRES_USER')
db_pass = os.getenv('POSTGRES_PASS')
db_name = os.getenv('POSTGRES_DB')
app_secret_key = os.getenv('APP_SECRET_KEY')
login_salt = os.getenv('LOGIN_SALT')

cred = credentials.Certificate("icls-56e37-firebase-adminsdk-2d4e2-be93ca6a35.json")
firebase_admin.initialize_app(cred)

app = Flask(__name__)
app.config['SECRET_KEY'] = app_secret_key

# app.config['MAIL_SERVER']= 'live.smtp.mailtrap.io'
# app.config['MAIL_PORT'] = 587
# app.config['MAIL_USERNAME'] = 'your_email@gmail.com'
# app.config['MAIL_PASSWORD'] = 'your_password'
# app.config['MAIL_USE_TLS'] = True
# app.config['MAIL_USE_SSL'] = False

# mail = Mail(app)



CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

jwt_manager = JWTManager(app)

def connect_to_db():
  try:
    db_con = psycopg2.connect(dbname=db_name, user=db_user, host=db_host, port=db_port, password=db_pass)
    cur = db_con.cursor()
    return db_con, cur
  except psycopg2.Error as e:
    return None, str(e)

def __convert_to_datetime(string) -> datetime:
    """ 
    Date string: "%Y-%m-%d %H:%M:%S" / "%Y-%m-%d %H:%M
    """
    try:
        # Parse string, handling timezone if present
        dt_obj = datetime.strptime(string, "%Y-%m-%d %H:%M:%S")
        return dt_obj
    except: #? Ok now bear with me, it may look stupid, be stupid and make me look stupid, but it works :) Did i mention how much i hate dates
        try:
            dt_obj = datetime.strptime(string, "%Y-%m-%d %H:%M")
            return dt_obj
        except ValueError as e:
            raise ValueError(f"Invalid datetime format: {string}") from e
def get_reports_paths(folder_path):
    try:
        files = []
        with os.scandir(folder_path) as entries:
            for entry in entries:
                if entry.is_file() and entry.name.endswith('.xlsx'):
                    try:
                        # Extract datetime from filename
                        timestamp_str = entry.name.split('_', 1)[0]
                        file_date = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
                        files.append((file_date, entry.path))
                    except (ValueError, IndexError) as e:
                        # Skip files with invalid format
                        print(f"Skipping invalid file: {entry.name} - {str(e)}")
                        continue
        
        # Sort by datetime descending (newest first)
        files.sort(key=lambda x: x[0], reverse=True)
        
        # Remove path prefix and return just sorted filenames
        return [entry[1].removeprefix("/app/reports/") for entry in files]
        
    except OSError as e:
        print(f"Error accessing directory: {str(e)}")
        return None

import os

def get_latest_file(folder_path, use_modification_time=True):
    try:
        if not os.path.exists(folder_path):
            raise FileNotFoundError(f"The folder '{folder_path}' does not exist.")
        
        if not os.path.isdir(folder_path):
            raise NotADirectoryError(f"'{folder_path}' is not a directory.")

        latest_file = None
        latest_time = 0

        # Use os.scandir for better performance
        with os.scandir(folder_path) as entries:
            for entry in entries:
                if entry.is_file():
                    # Use modification time or creation time based on the parameter
                    file_time = entry.stat().st_mtime 
                    
                    if file_time > latest_time:
                        latest_time = file_time
                        latest_file = entry.path

        return latest_file

    except (FileNotFoundError, NotADirectoryError, PermissionError, OSError) as e:
        print(f"An error occurred: {e}")
        return None

def get_sk_date():
    # Ensure the datetime is in UTC before converting
    dt_obj = datetime.now()
    utc_time = dt_obj.replace(tzinfo=pytz.utc) if dt_obj.tzinfo is None else dt_obj.astimezone(pytz.utc)
    bratislava_time = utc_time.astimezone(bratislava_tz)  # Convert to Bratislava timezone
    return bratislava_time.strftime("%Y-%m-%d %H:%M:%S") 

@app.after_request
def apply_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type"
    return response

# headers = {
#     "Authorization": f"Bearer {jwt_token}",
#     "Content-Type": "application/json"  # Ensure the server expects JSON
# }
# Callback function to check if a JWT exists in the database blocklist
@jwt_manager.token_in_blocklist_loader
def check_if_token_revoked(jwt_header, jwt_payload: dict): # None if an error happnes or a borken poipo
    jwt = jwt_header
    jti = jwt_payload["jti"]

    conn, cur = connect_to_db()
    try:
      cur.execute("select * from revoked_jwt where jti = %s", (jti,))
      result = cur.fetchone()

    except Exception as e:
      return jsonify({'error': e})

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



# ONLY ICLS GAMO CAN REGISTETR PEOPLE
@app.route('/register', methods = ['POST'])
@jwt_required()
def register():
  data = request.get_json()
  requester = data["requester"]
  req_password = data["req_password"]

  email = data['email']
  password = data['password']
  role = data['role']
  name = data['name']

  

  if not email or not password:
    return {"status": False, "msg": f"Chýba email alebo heslo!"}
  
  conn, cur = connect_to_db()

  #! Only allow the admin to create users
  res = cur.execute(
    "SELECT id_driver FROM driver WHERE email = %s AND password = %s AND role LIKE 'admin'", 
    (requester, req_password)
  )
  tmp = cur.fetchall()
  if len(tmp) <1:
     return {"status": False, "msg": "Unauthorized"}
  
  salted = login_salt+password+login_salt
  hashed = hashlib.sha256(salted.encode()).hexdigest()


  result = cur.execute(
      "INSERT INTO driver (email, password, role, name) VALUES (%s, %s, %s, %s)",
      (email, hashed, role, name)
  )
  
  conn.commit()
  conn.close()
  
  return {"status": True}



@app.route('/login', methods=['POST'])
def login():
  data = request.get_json()
  email=data['username']
  password=data['password']
  if not email or not password:
    return jsonify({'error': 'Chýba email alebo heslo!', 'type': 0}), 401

  conn, cur = connect_to_db()
  if conn is None:
    return jsonify({'error': cur, 'type': 1}), 501

  salted = login_salt+password+login_salt
  hashed = hashlib.sha256(salted.encode()).hexdigest()
  try:
    query = "SELECT role, name FROM driver WHERE email = %s AND password = %s;"
    cur.execute(query, (email, hashed))
    res = cur.fetchone()

    if res is None:
      return jsonify({'error': 'Nesprávne meno alebo heslo!', 'type': 0}), 401
    else:
      additional_claims = {'role': res[0]}
      access_token = create_access_token(identity=email, fresh=True, expires_delta=timedelta(minutes=30), additional_claims=additional_claims)
      # refresh_token = create_refresh_token(identity=username, expires_delta=timedelta(days=1), additional_claims=additional_claims)
      # return jsonify(access_token=access_token, refresh_token=refresh_token), 200
      return jsonify(access_token=access_token, role=res[0], name=res[1]), 200

  finally:
    cur.close()
    conn.close()


# Only ICLS GAMO can create new cars and such

@app.route('/create_car', methods = ['POST'])
@jwt_required()
def create_car():
  claims = get_jwt()
  email = claims.get('sub', None)
  role = claims.get('role', None)

  if role != "admin" or email is None:
     return {"status": False, "msg": "Unathorized"}, 400

  data = request.get_json()
  try:
    car_name = data['name']  
    _type = data['type']
    status = data['status']
    location = data['location']
    
    spz = data['spz']
    gas = data['gas']
    drive_tp = data['drive_tp']

    # The image is a list of bytes, only allow .png or .jpg files
    car_image = data['image']
  except:
     return {"status": False, "msg": "Chýbajúce parametre pri vytvorení auta!"}
  
  # TODO: Here construct an image from the bytes

  # TODO: After constructing it, save it to the /images folder, where it should then be automatically added to the nginx file server
  

  #* construct a url using the new images name and add it to the database
  
  url = "https://fl.gamo.sosit-wh.net/{0}".format()
  conn, cur = connect_to_db()

  query = "INSERT INTO car (name, type, status, location, stk, gas, drive_type) VALUES (%s,%s,%s,%s,%s,%s,%s)"
  try:
    cur.execute(query, (car_name, _type, status, location, spz, gas, drive_tp,))
    conn.commit()
    conn.close()
    return {"status": True, "msg": "Auto bolo vytvorené."}
  except Exception as e:
    conn.commit()
    conn.close()
    return {"status": False, "msg": e}


# Only the admin should be able to do this ig
# the password check may not be really all that important? As technically you simply cannot get a json token with the admin role,
# Since you know, its under a cryptographic pwassword or smth idk im just typing this so it makes sound and the people here think i am doing something and i cannot be available to them, so yeah
# hard owrky or hardly working
# thats a physiloshpy  
@app.route('/delete_car', methods=['POST'])
@jwt_required()
def del_cars():
    claims = get_jwt()
    role = claims.get('role', None)
    
    data = request.get_json()
    car_name = data["car_name"]

    if role != "admin":
       return {"status": False, "msg": "Unathorized"}, 400
    
    if car_name == "":
       return {"status": False, "msg": "Missing parameters!"}, 500
    
    #TODO:  Make this into an ID check, not a name check dumbfuck
    try:
      conn, cur = connect_to_db()
      cur.execute("DELETE FROM car WHERE name = %s", (car_name, ))
      conn.commit()
      conn.close()
      return {"status": True, "msg": "Car succesfully deleted!"}, 200
    except Exception as e:
       return {"status": False, "msg": f"An error has occured in deleting a car: {e}"}

@app.route('/delete_user', methods=['POST'])
@jwt_required()
def del_users():
    claims = get_jwt()
    role = claims.get('role', None)
    
    data = request.get_json()
    email = data["email"]

    if role != "admin":
       return {"status": False, "msg": "Unauthorized"}, 400

    if email == "":
       return {"status": False, "msg": "Missing parameters!"}, 500
           
    try:
      conn, cur = connect_to_db()
      cur.execute("DELETE FROM driver WHERE email = %s", (email, ))
      conn.commit()
      conn.close()
      return {"status": True, "msg": "User succesfully deleted!"}, 200
    except Exception as e:
       return {"status": False, "msg": f"An error has occured in deleting a user: {e}"}


@app.route('/get_users', methods=['GET'])
@jwt_required()
def get_users():
  # Authentication check
    claims = get_jwt()
    email = claims.get('sub', None)
    role = claims.get('role', None)
    
    if role != "manager" and role != "admin":
       return {"error": "Unauthorized"}, 400

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


@app.route('/get_cars', methods=['GET'])
@jwt_required()
def get_cars():
  # Authentication check
  claims = get_jwt()
  email = claims.get('sub', None)
  role = claims.get('role', None)

  if role != "manager" and role != "admin":
    return {"error": "Unauthorized"}, 400

  conn, cur = connect_to_db()
  try:
    cur.execute('SELECT name FROM car;')
    cars = cur.fetchall()

    return {'cars': cars}
  except Exception as e:

    return {"error": str(e)}, 500
  finally:
    cur.close()
    conn.close()


# Order by reserved first, then by metric and filter by reserved cars by the provided email
# Cars table does not have the email, you will have to get it from the leases table that combines the car and driver table together,
#! Return cars, sort by usage metric first, other options: location, gas type, shift type
@app.route('/get_car_list', methods=['GET'])
@jwt_required()
def get_car_list():
  #! This is useless here, why have it?
  if request.method == 'GET':
      conn, cur = connect_to_db()
      if conn is None:
          return jsonify({'error': cur, 'status': 501}), 501

      try:
          location = request.args.get('location', 'none')
          if location != 'none':
              query = """
                  SELECT id_car, name, status, url, stk 
                  FROM car 
                  ORDER BY 
                      CASE 
                          WHEN location = %s THEN 1 
                          ELSE 2 
                      END,
                      CASE 
                          WHEN status = 'leased' THEN 1
                          WHEN status = 'stand_by' THEN 2
                          ELSE 3
                      END,
                      usage_metric ASC;
              """
              cur.execute(query, (location,))
          else:
              query = """
                  SELECT id_car, name, status, url, stk
                  FROM car
                  ORDER BY 
                      CASE 
                          WHEN status = 'leased' THEN 1
                          WHEN status = 'stand_by' THEN 2
                          ELSE 3
                      END,
                      usage_metric ASC;
              """
              cur.execute(query)
          res = cur.fetchall()
          return jsonify({'cars': res}), 200

      except Exception or psycopg2 as e:
        return jsonify({"error": str(e)}), 500

      finally:
        cur.close()
        conn.close()  


@app.route('/decommision_car', methods= ['POST'])
@jwt_required()
def decommission():
  data = request.get_json()
  
  # Authentication check
  claims = get_jwt()
  email = claims.get('sub', None)
  role = claims.get('role', None)

  if role != "manager" and role != "admin":
      return {"status": False, "msg": "Unauthorized"}, 401

  # Input validation
  try:
      car_name = data["car_name"]
      # TODO: Replace timeof with todays date, as i no longer require time_of
      time_of = __convert_to_datetime(get_sk_date())
      time_to = __convert_to_datetime(data["timeto"])
  except KeyError as e:
      return {"status": False, "msg": f"Missing required field: {e}"}, 400
  except ValueError as e:
      return {"status": False, "msg": f"{e}"}, 400

  try:
      conn, cur = connect_to_db()

      # UPdate car status so it shows as decommisioned to the user
      car_update_query = "UPDATE car SET status = 'service' WHERE name = %s and not status = 'service'"
      cur.execute(car_update_query, (car_name,))

      # Add a decomission request to the DB
      car_decomission_query = "INSERT INTO decommissioned_cars(status, car_name, email, time_to, requested_at) values (%s, %s, %s, %s, %s)"
      cur.execute(car_decomission_query, (True, car_name, email, time_to, time_of, ))
      
      lease_update_query = """
          UPDATE lease 
          SET status = FALSE 
          WHERE start_of_lease > %s AND end_of_lease < %s
      """

      cur.execute(lease_update_query, (time_of, time_to, ))
      conn.commit()

      return {
          "status": True,
          "msg": f"Decommissioned {car_name}."
      }, 200

  except Exception as e: # This is also cool, you can rollback changes if an error occured
      if conn:
          conn.rollback()
      return {"status": False, "msg": f"Decomission error: {e}"}, 500



@app.route('/activate_car', methods= ['POST'])
@jwt_required()
def activate_car():
  data = request.get_json()
  car_name = data["car_name"]

  claims = get_jwt()
  role = claims.get('role', None)

  if role != "manager" and role != "admin":
    return {"status": False, "msg": "Unathorized"}, 401
  
  # Update car status, so its visible to the user again
  query = "update car set status = 'stand_by' where name = %s"
  conn, cur = connect_to_db()  
  cur.execute(query, (car_name, ))

  # Update decommision status so it wont trigger the notificator again
  dec_query = "UPDATE decommissioned_cars SET status = FALSE where car_name = %s"
  cur.execute(dec_query, (car_name, ))
  
  conn.commit()
  conn.close()

  message = messaging.Message(
          notification=messaging.Notification(
          title=f"Auto {car_name} je k dispozíci!",
          body=f"""Je možné znova auto rezervovať v aplikácií."""
      ),
          topic="system"
      )
  send_firebase_message_safe(message)
  return {"status": True, "msg": f"Car {car_name} was activated!"}



# Warning!!!
# The allowed dates return here is kinda retarted, it would be better to just return a list of start > stop dates that the user would then generate locally
# But i dont feel like doing it, so a MONSTER json has been created, enjoy :)
#
#?  22/02/2025, I did indeed feel like doing it after all :O
# TODO: For the ove of god make this into a json not a fucking index guessing game jesus christ
@app.route('/get_full_car_info', methods=['POST', 'OPTIONS'])
@jwt_required()
def get_full_car_info():
    if request.method == 'OPTIONS':
      # Handle the preflight request by returning appropriate CORS headers
      response = jsonify({"message": "CORS preflight successful"})
      response.headers['Access-Control-Allow-Origin'] = '*'
      response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
      response.headers['Access-Control-Allow-Headers'] = 'Authorization, Content-Type'
      return response, 200


    bratislava_tz = pytz.timezone('Europe/Bratislava')
    def convert_to_bratislava_timezone(dt_obj):
      # Ensure the datetime is in UTC before converting
      utc_time = dt_obj.replace(tzinfo=pytz.utc) if dt_obj.tzinfo is None else dt_obj.astimezone(pytz.utc)
      bratislava_time = utc_time.astimezone(bratislava_tz)  # Convert to Bratislava timezone
      return bratislava_time.strftime("%Y-%m-%d %H:%M:%S") 
    
    conn, cur = connect_to_db()
    data = request.get_json()

    if conn is None:
        return jsonify({'error': 'Database connection error: ' + cur}), 500

  
    car = data.get("car_id")
    if not car or car == 'none':
        return jsonify({'error': 'The "carid" parameter is missing or invalid'}), 500

    query = "SELECT * FROM car WHERE id_car = %s;"
    cur.execute(query, (car,))
    res = cur.fetchall()

    if not res:
        return jsonify({'error': 'No car found with the given ID'}), 404

    # res[3] = status
    # res[1] = car name string
    decom_timeto = ""
    if res[0][3] != "stand_by":
       dec_query = "SELECT time_to FROM decommissioned_cars WHERE car_name = %s"
       cur.execute(dec_query, (res[0][1],)) 
       decom_timeto = convert_to_bratislava_timezone(cur.fetchone()[0])

    
    query = "SELECT start_of_lease, end_of_lease FROM lease WHERE id_car = %s AND status = %s;"
    cur.execute(query, (car, True, ))

    leases = cur.fetchall()


    query = "SELECT start_of_request, end_of_request FROM request WHERE id_car = %s AND status = %s;"
    cur.execute(query, (car, True, ))

    requests = cur.fetchall()



    # [
    #     [
    #         "Thu, 12 Dec 2024 16:01:22 GMT",
    #         "Thu, 12 Dec 2024 17:01:22 GMT"
    #     ]
    # ]


    def parse_lease_dates(resu):
        lease_dates = []
        for i in resu:
            # Parse the RFC 1123 strings into datetime object
            start_datetime = convert_to_bratislava_timezone(i[0])
            end_datetime = convert_to_bratislava_timezone(i[1])
            lease_dates.append([start_datetime, end_datetime])
        return lease_dates

    # Parse the dates, also add the request dates
    lease_dates = parse_lease_dates(leases)
    
    if len(parse_lease_dates(requests)) > 0:
      lease_dates.extend(parse_lease_dates(requests))
    
    response = jsonify(
       {
        "car_details": res, 
        "decommission_time": decom_timeto, 
        "notallowed_dates": lease_dates
       })
    return response, 200


@app.route('/get_all_car_info', methods=['POST'])
@jwt_required()
def get_all_car_info():
  conn, cur = connect_to_db()
  data = request.get_json()
  if conn is None:
    return jsonify({'error': 'Database connection error: ' + cur}), 500

  role = 'admin' if data.get("role") == 'admin' else None

  if role is None:
    return jsonify({'error': 'The "role" parameter is missing or invalid'}), 500

  stmt = "SELECT * FROM car"
  cur.execute(stmt)
  res = cur.fetchall()
  if not res:
    return jsonify({'error': 'No cars!'}), 404

  return jsonify({'cars': res}), 200

@app.route('/get_all_user_info', methods=['POST'])
@jwt_required()
def get_all_user_info():
  conn, cur = connect_to_db()
  data = request.get_json()
  if conn is None:
    return jsonify({'error': 'Database connection error: ' + cur}), 500

  role = 'admin' if data.get("role") == 'admin' else None

  if role is None:
    return jsonify({'error': 'The "role" parameter is missing or invalid'}), 500

  stmt = "SELECT id_driver, name, email, role FROM driver WHERE name != 'admin'"
  cur.execute(stmt)
  res = cur.fetchall()
  if not res:
    return jsonify({'error': 'No users!'}), 404

  return jsonify({'users': res}), 200


# # Get a list of reports, using their name you then download the correct file
#?
    # "reports": [
    #     "/app/reports/2025-01-21 18:06:00exc_ICLS_report.csv"
    # ]
@app.route('/list_reports', methods = ['POST'])
@jwt_required()
def list_reports():
  claims = get_jwt()
  email = claims.get('sub', None)
  role = claims.get('role', None)

  conn, curr = connect_to_db()

  if role != "manager" and role != "admin":
     return {"msg": "Unathorized"}

  curr.execute("select id_driver from driver where email = %s and role = %s", (email, role))
  res =  curr.fetchall()
  if len(res) <1:
    return {"msg": "Unauthorized access detected, ball explosion spell had been cast at your spiritual chackra."}
  # Should return all file names
  return {"reports": get_reports_paths(folder_path=f"{os.getcwd()}/reports/")}


# NEED TO REPLACE WHITESPACE WITH %20
# https://icls.sosit-wh.net/get_report/2025-01-21%2018:06:00exc_ICLS_report.csv?email=test@manager.sk&role=manager
@app.route('/get_report/<path:filename>', methods=['GET'])  # Changed to <path:filename> and explicit methods
@jwt_required()
def get_reports(filename):
    claims = get_jwt()
    email = claims.get('sub', None)
    role = claims.get('role', None)

    
    # Validate parameters
    if not email or not role:
        return {"msg": "Missing email or role parameters"}, 400
    
    if role != "manager" and role != "admin":
        return {"msg": "Unauthorized"}, 400

    try:
        conn, curr = connect_to_db()
        query = "SELECT email FROM driver WHERE email = %s AND role = %s"  # Removed semicolon
        curr.execute(query, (email, role))
        res = curr.fetchone()
    except Exception as e:
        return {"msg": f"Database error: {str(e)}"}, 500
    finally:
        if conn:
            conn.close()

    if not res:
        return {"msg": "Invalid authorization"}, 403

    try:
        # Safe path construction
        reports_dir = os.path.join(os.getcwd(), 'reports')
        safe_path = os.path.join(reports_dir, filename)
        
        # Security check to prevent path traversal
        if not os.path.realpath(safe_path).startswith(os.path.realpath(reports_dir)):
            return {"msg": "Invalid file path"}, 400

        if not os.path.isfile(safe_path):
            return {"msg": "File not found"}, 404

        return send_from_directory(
            directory=reports_dir,
            path=filename, as_attachment=True
        )
    except Exception as e:
        return {"msg": f"Error accessing file: {str(e)}"}, 500




# returns a wierd string but i can work with it 
@app.route('/starting_date', methods = ['POST'])
@jwt_required()
def allowed_dates():
    bratislava_tz = pytz.timezone('Europe/Bratislava')
    def convert_to_bratislava_timezone(dt_obj):
      # Ensure the datetime is in UTC before converting
      if dt_obj == None: return "null"
      utc_time = dt_obj.replace(tzinfo=pytz.utc) if dt_obj.tzinfo is None else dt_obj.astimezone(pytz.utc)
      bratislava_time = utc_time.astimezone(bratislava_tz)  # Convert to Bratislava timezone
      return bratislava_time.strftime("%Y-%m-%d %H:%M:%S") 
    
    try: 
       name = request.get_json()["name"]
    except: 
       return 500

    # Get the last allowed time for a car to be leased, so it can be put into the apps limiter
    con, curr = connect_to_db()
    query = """SELECT id_car FROM car WHERE name = %s"""
    
    curr.execute(query, (name, ))
    id_car = curr.fetchone()

    query ="""SELECT end_of_lease 
            FROM lease
            WHERE status = true 
            AND id_car = %s
            ORDER BY end_of_lease DESC
            LIMIT 1
            """
    curr.execute(query, (id_car,))
    res = curr.fetchone()
    if res:
      return {"starting_date": convert_to_bratislava_timezone(res[0])}, 200
    else:
      return {"starting_date": "null"}


# Only get active leases!!! 
# And leases that need aproval
# Get the lease time_from, time_to
# driver name 
# car name
# car location
# 
@app.route('/get_leases', methods = ['POST'])
@jwt_required()
def get_leases():
  conn, curr = connect_to_db()
  
  data = request.get_json()

  # No fucking way this works
  # what the fuck python ????
  ft_email = None if (data["email"] == "") else data["email"] 
  ft_car = None if (data["car_name"] == "") else data["car_name"]
  
  ft_timeof = None if (data["timeof"] == "") else data["timeof"]
  ft_timeto = None if (data["timeto"] == "") else data["timeto"]

  ft_istrue = True if 'istrue' not in data or data['istrue'] is True else data["istrue"]
  ft_isfalse = False if 'isfalse' not in data or data['isfalse'] is False else data["isfalse"]

  if ft_timeof is not None and ft_timeto is None:
     return jsonify(msg=  f"Chýba konečný dátum rozsahu."), 500
  
  if ft_timeof is None and ft_timeto is not None:
     return jsonify(msg=  f"Chýba začiatočný dátum rozsahu."), 500
  
     

  claims = get_jwt()
  email = claims.get('sub', None)
  role = claims.get('role', None)
  
  bratislava_tz = pytz.timezone('Europe/Bratislava')

  if role == "user":
    query  = """
        SELECT 
          d.email AS driver_email,
          d.role AS driver_role,
          c.name AS car_name,
          c.location AS car_location,
          c.url AS car_url,
          l.id_lease,
          l.start_of_lease,
          l.end_of_lease,
          l.time_of_return,
          l.private,
          c.stk,
          c.gas,
          c.drive_type,
          l.status
        FROM 
            lease l
        JOIN 
            driver d ON l.id_driver = d.id_driver
        JOIN 
            car c ON l.id_car = c.id_car
        WHERE 
            d.email = %(user_email)s
            AND (
                ( %(ft_istrue)s = true AND l.status = true )
                OR 
                ( %(ft_isfalse)s = true AND l.status = false )
            ); 
    """
    params = {
      'ft_istrue': ft_istrue,
      'ft_isfalse': ft_isfalse,
      'user_email': email
    }
    curr.execute(query, params)

  elif role == "manager" or role == "admin": 
    # These are all voluntary!!!
    # These have to be NULL, they cannot be ""

    #? This checks each filter variable, if empty ignore it, if not apply its rule
    query = """
        SELECT 
            d.email AS driver_email,
            d.role AS driver_role,
            c.name AS car_name,
            c.location AS car_location,
            c.url AS car_url,
            l.id_lease,
            l.start_of_lease,
            l.end_of_lease,
            l.time_of_return,
            l.private,
            c.stk,
            c.gas,
            c.drive_type,
            l.status
        FROM 
            lease l
        JOIN 
            driver d ON l.id_driver = d.id_driver
        JOIN 
            car c ON l.id_car = c.id_car
        WHERE 
            (
                ( %(ft_istrue)s = true AND l.status = true )
                OR 
                ( %(ft_isfalse)s = true AND l.status = false )
            )
            AND ( %(ft_email)s IS NULL OR d.email = %(ft_email)s )
            AND ( %(ft_car)s IS NULL OR c.name = %(ft_car)s )
            AND ( %(ft_timeof)s IS NULL OR l.start_of_lease >= %(ft_timeof)s )
            AND ( %(ft_timeto)s IS NULL OR l.end_of_lease <= %(ft_timeto)s );
      """  
    params = {
      'ft_istrue': ft_istrue,
      'ft_isfalse': ft_isfalse,
      'ft_email': ft_email,
      'ft_car': ft_car,
      'ft_timeof': ft_timeof,
      'ft_timeto': ft_timeto,
    }
    curr.execute(query, params)

  def convert_to_bratislava_timezone(dt_obj):
      bratislava_tz = pytz.timezone('Europe/Bratislava')

      if dt_obj.tzinfo is None:  # Most likely case when coming from DB
          # Assume UTC and make it an *aware* datetime
          utc_time = pytz.utc.localize(dt_obj)  # Key change
      else:
          utc_time = dt_obj.astimezone(pytz.utc) # Convert to UTC first

      bratislava_time = utc_time.astimezone(bratislava_tz) # Now convert to Bratislava
      return bratislava_time.strftime("%Y-%m-%d %H:%M:%S")
  try:

    res = curr.fetchall()
    leases = []
    for i in res:
      leases.append({
        "email": i[0],
        "role": i[1],
        "car_name": i[2],
        "location": i[3],
        "url": i[4],
        "lease_id": i[5],
        "time_from": convert_to_bratislava_timezone(i[6]),
        "time_to": convert_to_bratislava_timezone(i[7]),
        "time_of_return": i[8],
        "private": i[9], 
        "spz": i[10],
        "gas": i[11],
        "shaft": i[12],
        "status": i[13]
      })

    conn.close()
    return {"active_leases": leases}, 200
  
  except Exception as e:
    return jsonify(msg=  f"Error recieving leases: {e}"), 500

# needs: email, car name, 
@app.route('/cancel_lease', methods = ['POST'])
@jwt_required()
def cancel_lease():
  # make a sql statement that updates the table lease and sets it stauts to false where you will filter the result by the driver, car, and order by id_lease descending limit 1
  data = request.get_json()
  claims = get_jwt()
  email = claims.get('sub', None)
  role = claims.get('role', None)

  recipient = ""
  if data["recipient"]:
     recipient = data["recipient"]
  else:
    recipient = email

  car_name = data["car_name"]

  # Only managers and admins can cancel other peoples rides
  # A normal user should not be able to cancel another ones ride using postman for example
  if recipient != email:
     if role != "manager" and role != "admin":
        return {"cancelled": False}, 400
 
  conn, cur = connect_to_db()
  
  try:
    # need to get the car_id  and driver_id 
    cur.execute("select id_driver from driver where email = %s", (recipient,))
    id_name = cur.fetchall()[0][0]

    cur.execute("select id_car from car where name = %s", (car_name,))
    id_car = cur.fetchall()[0][0]
  except Exception as e:
    return jsonify(msg= f"Error cancelling lease!, {e}"), 500
  
  try:
    cur.execute("UPDATE lease SET status = false WHERE id_lease = (SELECT id_lease FROM lease WHERE id_driver = %s AND id_car = %s  AND status = true ORDER BY id_lease DESC LIMIT 1)", (id_name, id_car))
    sql_status_message = cur.statusmessage
    cur.execute("update car set status = %s where id_car = %s", ("stand_by", id_car))
  except Exception as e:
    return jsonify(msg= f"Error cancelling lease!, {e}"), 500
  
  # If manager cancelling for someone send him a notification 
  if (role == "manager" or role == "admin") and (email != recipient):
      msg_rec = recipient.replace("@" ,"_")
      message = messaging.Message(
        notification=messaging.Notification(
        title=f"Vaša rezervácia bola zrušená!",
        body=f"""Rezervácia pre auto: {car_name} bola zrušená."""
      ),
          topic=msg_rec
      )
      send_firebase_message_safe(message)
 
  conn.commit()
  conn.close()

  return {"cancelled": True, "msg": sql_status_message}, 200




@app.route('/get_monthly_leases', methods = ['POST'])
@jwt_required()
def get_monthly_leases():
  data = request.get_json()
  
  claims = get_jwt()
  role = claims.get('role', None)

  if role != "manager" and role != "admin":
    return jsonify({'msg': "Not enough clearance!"}), 400
  else:
    try:
      month = data["month"]
      conn, cur = connect_to_db()
      stmt = ("SELECT l.start_of_lease, COALESCE(l.time_of_return,l.end_of_lease), l.status, c.name, d.email, COALESCE(l.note,'') "
              "FROM lease l LEFT JOIN car c ON l.id_car=c.id_car LEFT JOIN driver d ON l.id_driver = d.id_driver "
              "WHERE EXTRACT(MONTH FROM start_of_lease)::int = %s")

      cur.execute(stmt, (month,))
      res = cur.fetchall()

      conn.close()
      return jsonify(res)
    except Exception as e:
      return jsonify(msg= f"Error getting monthly leases: {e}")



@app.route('/lease_car', methods = ['POST'])
@jwt_required()
def lease_car():
  data =  request.get_json()

  # for whom the lease is 
  recipient = data["recipient"]
  car_name  = str(data["car_name"])
  stk = str(data["stk"])
  private = data["is_private"]

  claims = get_jwt()  # JWT data
  # Replaced user given username,role for a JWT gotten one to prevent fraud
  username = claims.get('sub', None)
  jwt_role = claims.get('role', None)
  
  if username is None or jwt_role is None:
    return {"status": False, "private": False, "msg": f"JWT token incomplete? whaaa"}

  # Try to dezinfect timeof from the .2342212 number horseshit
  timeof = data["timeof"]
  try:
    timeof = timeof.split(".", 1)[0]
  except:
    pass
  
  timeto = data["timeto"]
  
  # shit implementation for a shit fucking data format, god if cuking haéte working with dates, such a retarted THING
  # kys
  # And yes i know i could use a strptime and make it better, but guess waht? I am wokring on this shit for FREE on a saturday so i dont give a fuck
  # 2025-02-02 21:04:48+01        | 2025-02-20 21:04:00+01
  #! The commented dates may be in the wrong format, i dont care enough to recheck, but the +01 timezone awareness may be wrong idk
  tmp_of = timeof.split(" ")
  dates =  tmp_of[0].split("-")

  # 2025-02-25 21:04:00+01 --->> 25-02-2025 21:04
  try: 
    form_timeof = f"{dates[2]}-{dates[1]}-{dates[0]} {tmp_of[1]}"

    # Chnage time to date format
    tmp_to = timeto.split(" ")
    dates =  tmp_to[0].split("-")
    # 25-02-2025 10:44
    form_timeto = f"{dates[2]}-{dates[1]}-{dates[0]} {tmp_to[1]}"
  except Exception as e :
     return {"status": False, "private": False, "msg": f"Incorrect date format: {e}"} 
  

  def convert_to_datetime(string):
      try:
          # Parse string, handling timezone if present
          dt_obj = datetime.strptime(string, "%Y-%m-%d %H:%M:%S")
          return dt_obj
      except: #? Ok now bear with me, it may look stupid, be stupid and make me look stupid, but it works :) Did i mention how much i hate dates
        try:
          dt_obj = datetime.strptime(string, "%Y-%m-%d %H:%M")
          return dt_obj
        except ValueError as e:
          raise ValueError(f"Invalid datetime format: {string}") from e
          
  
  def compare_timeof(a_timeof, today):
    # This gives the user 2 minutes to make a reservation, before being time blocked by leasing into the past
    timeof = convert_to_datetime(string=a_timeof)
    diff = today - timeof
    if (diff.total_seconds()/60) >= 2:
        return True

    
  today = datetime.strptime(get_sk_date(), "%Y-%m-%d %H:%M:%S")
  try:
      if convert_to_datetime(timeto) < today:
          return {"status": False, "private": False, "msg": f"Nemožno rezervovať do minulosti.\n Dnes: {today}, \nDO:{timeto}"}
      elif compare_timeof(timeof, today):
          return {"status": False, "private": False, "msg": f"Nemožno rezervovať z minulosti.\n Dnes: {today}, \nOD:{timeof}"}
  except Exception as e:
      return {"status": False, "private": False, "msg": f"{e}"}

  con, cur = connect_to_db()

  # user is a list within a list [[]] to access it use double [0][1,2,3,4]
  try:
    cur.execute("select * from car where name = %s and not status = 'service'", (car_name,))
    car_data = cur.fetchall()
  except:
    return {"status": False, "private": False, "msg": "Auto je momentálne nedostupné."}

  drive_type = f"{car_data[0][9]}, {car_data[0][10]}"
  car_id = car_data[0][0]

  cur.execute("select * from driver where email = %s and role = %s", (username, jwt_role,))
  user = cur.fetchall()
  
  # Check for the leased car if it has available date range to lease from
  conflict_query = """
    SELECT COUNT(*) FROM lease 
    WHERE status = true AND id_car = %s  
    AND (
        (start_of_lease < %s AND end_of_lease > %s) OR
        (start_of_lease < %s AND end_of_lease > %s) OR
        (start_of_lease >= %s AND start_of_lease < %s)
    )
  """
  cur.execute(conflict_query, (car_id, timeof, timeof, timeto, timeto, timeof, timeto))
  
  conflicting_leases = cur.fetchone()
  if conflicting_leases[0] > 0:
     return {"status": False, "private": False, "msg": f"Zabratý dátum (hodina typujem)"}
  
  # Init excel writer to use later 
  #exc_writer = writer()
  
  # If the user is leasing for himself
  if recipient ==  username:
    if private == True:
      if jwt_role != "manager" and jwt_role != "admin":
        # Just need to create a requst row, a new lease is only created and activated after being approved in the approve_request route
        cur.execute("insert into request(start_of_request, end_of_request, status, id_car, id_driver) values (%s, %s, %s, %s, %s)", (timeof, timeto, True, car_data[0][0], user[0][0]))
        con.commit()

        message = messaging.Message(
                  notification=messaging.Notification(
                  title=f"Žiadosť o súkromnu jazdu!",
                  body=f"""email: {username} \n Od: {form_timeof} \n Do: {form_timeto}"""
              ),
                  topic="manager"
              )
        send_firebase_message_safe(message)

        return {"status": True, "private": True, "msg": f"Request for a private ride was sent!"}, 200

      else: # User is a manager, therfore no request need to be made, and a private ride is made 
        try:
          cur.execute("insert into lease(id_car, id_driver, start_of_lease, end_of_lease, status, private) values (%s, %s, %s, %s, %s,%s)", (car_data[0][0], user[0][0], timeof, timeto, True, True))
          con.commit()
        except Exception as e:
          return {"status": False, "private": False, "msg": f"Error has occured! 113"}, 500
        #exc_writer.write_report(recipient, car_name,stk,drive_type, form_timeof, form_timeto)
        return {"status": True, "private": True}


    try:
      cur.execute("insert into lease(id_car, id_driver, start_of_lease, end_of_lease, status, private) values (%s, %s, %s, %s, %s, %s)", (car_data[0][0], user[0][0], timeof, timeto, True, False))
      con.commit()
    except Exception as e:
      return {"status": False, "private": False, "msg": f"Error has occured! 113"}, 500
    
    con.close()


    message = messaging.Message(
              notification=messaging.Notification(
              title=f"Upozornenie o leasingu auta: {car_name}!",
              body=f"""email: {recipient} \n Od: {form_timeof} \n Do: {form_timeto}"""
          ),
              topic="manager"
          )
    send_firebase_message_safe(message)

    #!!!!!!!!!!!!
    #exc_writer.write_report(recipient, car_name,stk,drive_type, form_timeof, form_timeto)
    #send_email(msg="Auto bolo rezervovane!")
    return {"status": True, "private": private}

  # If the user leasing is a manager allow him to order lease for other users
  elif jwt_role  == "manager" or jwt_role == "admin":
    try:
      # If the manager is leasing a car for someone else check if the recipeint exists and lease for his email
      try:
        cur.execute("select id_driver from driver where email = %s", (recipient,)) # NO need to check for role here!!!
        id_recipient = cur.fetchall()
        cur.execute("insert into lease(id_car, id_driver, start_of_lease, end_of_lease, status, private) values (%s, %s, %s,  %s, %s, %s)", (car_data[0][0], id_recipient[0][0], timeof, timeto, True, private))

      except Exception as e:
        return {"status": False, "private": False, "msg": f"Error has occured! 111, {e}"}, 500
            
      con.commit()
      
      # Upozorni manazerou iba ak si leasne auto normalny smrtelnik 
      #!!!!!!!!!!!!!!!!!!!!!!  POZOR OTAZNIK NEZNAMY SYMBOL JE NEW LINE CHARACTER OD TIALTO: http://www.unicode-symbol.com/u/0085.html
      message = messaging.Message(
                notification=messaging.Notification(
                title=f"Nová rezervácia auta: {car_name}!",
                body=f"""email: {recipient} \n Od: {form_timeof} \n Do: {form_timeto}"""
            ),
                topic="manager"
            )
      send_firebase_message_safe(message)
    except Exception as e:
      return {"status": False, "private": False, "msg": f"Error has occured! 112"}, 500
    con.close()

    #!!!  
    #exc_writer.write_report(recipient, car_name,stk, drive_type, form_timeof, form_timeto)
    #send_email(msg="Auto bolo rezervovane!")
    return {"status": True, "private": private}
      
  else:
    return {"status": False, "private": False, "msg": f"Users do not match, nor is the requester a manager."}, 500



@app.route('/get_requests', methods = ['POST'])
@jwt_required()
def get_requests():

  claims = get_jwt()
  email = claims.get('sub', None)
  role = claims.get('role', None)

  # triewd to do a role != admin/manager but did not work lmao
  # idk how to make it not be nested sry
  if role == "manager" or role =="admin":
    conn, curr = connect_to_db()
    curr.execute("select id_driver from driver where email = %s and role = %s", (email, role,))

    if len(curr.fetchall()) <0:
      return {"active_requests": []}, 500

    curr.execute("""
          SELECT 
            d.email AS driver_email,
            d.role AS driver_role,
            c.name AS car_name,
            c.location AS car_location,
            c.url AS car_url,
            l.id_request,
            l.start_of_request,
            l.end_of_request,
            c.stk
          FROM 
              request l
          JOIN 
              driver d ON l.id_driver = d.id_driver
          JOIN 
              car c ON l.id_car = c.id_car
          WHERE 
              l.status = TRUE; 
      """)
    

    def convert_to_bratislava_timezone(dt_obj):
      # Ensure the datetime is in UTC before converting
      utc_time = dt_obj.replace(tzinfo=pytz.utc) if dt_obj.tzinfo is None else dt_obj.astimezone(pytz.utc)
      bratislava_time = utc_time.astimezone(bratislava_tz)  # Convert to Bratislava timezone
      return bratislava_time.strftime("%Y-%m-%d %H:%M:%S") 

    res = curr.fetchall()
    requests = []
    for i in res:
      requests.append({
        "email": i[0],
        "role": i[1],
        "car_name": i[2],
        "location": i[3],
        "url": i[4],
        "request_id": i[5],
        "time_from": convert_to_bratislava_timezone(i[6]),
        "time_to": convert_to_bratislava_timezone(i[7]),
        "spz": i[8]
      })

    conn.close()
    return {"active_requests": requests}, 200
  
  else: 
    return {"active_requests": []}, 200
    



@app.route('/approve_req', methods = ['POST'])
@jwt_required()
def approve_requests():
  data = request.get_json()
  if not data:
     return {"msg": "No Data."}, 400

  approval = data["approval"]


  request_id = data["request_id"]
  timeof = data["timeof"]
  timeto = data["timeto"]
  car_name = data["id_car"]

  reciever = data["reciever"]
  # This is for the amanger 
  claims = get_jwt()
  email = claims.get('sub', None)
  role = claims.get('role', None)

  conn, curr = connect_to_db()

  try:
    curr.execute("select id_car, name from car where name = %s", (car_name,))
    car = curr.fetchall()
    if not car:
      return {"status": False, "msg": "Car does not exist."}
    car_id = car[0][0]



    if role != "manager" and role != "admin":
      return {"status": False, "msg": "Unauthorized request!"}, 400
      
    curr.execute("select id_driver from driver where email = %s and role = %s", (email, role, ))
    managers = curr.fetchall()
    if len(managers) == 0:
      return {"status": False, "msg": "User does not exist!"}, 400

    # Check if the perosn you are leasing for exists, if so get his ID as we need it to make a lease 
    curr.execute("select id_driver from driver where email = %s", (reciever,))
    user = curr.fetchall()
    if len(user) == 0:
      return {"status": False, "msg": "Recipient does not exist!"}, 400


    rep_email = reciever.replace("@", "_")
    if approval == True:
      # Create a lease and change the requests statust o false
      try:
        curr.execute("update request set status = FALSE where id_request = %s ", (request_id, ))
        curr.execute("insert into lease(id_car, id_driver, start_of_lease, end_of_lease, status, private) values (%s, %s, %s, %s, %s,%s)", (car_id, user[0][0], timeof, timeto, True, True))
        

        message = messaging.Message(
            notification=messaging.Notification(
            title=f"Vaša rezervácia bola prijatá!",
            body=f"""Súkromná rezervácia auta: {car[0][1]}"""
        ),
            topic= rep_email
        )
        send_firebase_message_safe(message)
      except Exception as e:
        return {"status": False, "msg": f"Error approving, {e}"}, 400
    
    elif approval == False:

      # Just deactivaet the request, dont create a lease
      curr.execute("update request set status = FALSE where id_request = %s ", (request_id, ))

      message = messaging.Message(
          notification=messaging.Notification(
          title=f"Súkromná rezervácia nebola prijatá!",
          body=f"""Súkromná rezervácia auta: {car[0][1]}.\nBola odmietnutá."""
      ),
          topic= rep_email
      )
      send_firebase_message_safe(message)

    conn.commit()
    conn.close()

    return {"status": True, "msg": "Success"}, 200
  
  except Exception as e:
      return {"status": False, "msg": f"Nastala chyba! {e}"}



# CAR RETURN NO LONGER NEEDS TO WRITE TO AN EXCEL FILE
@app.route('/return_car', methods = ['POST'])
@jwt_required() 
def return_car():
  data = request.get_json()
  if not data:
    return jsonify({'error': 'No data'}), 501
  
  claims = get_jwt()
  email = claims.get('sub', None)
  role = claims.get('role', None)  
  
  damaged = ""
  dirty   = ""
  int_damage = ""
  ext_damage = ""
  collision  = ""

  try:
    damaged = data["damaged"]
    dirty   = data["dirty"]
    int_damage = data["int_damage"]
    ext_damage = data["ext_damage"]
    collision  = data["collision"]
  except:
     return {"status": False, "msg": "missing damage data"}, 400
  
  id_lease = data["id_lease"]
  # TODO: ADD A VARIABLE FOR TIME_TO SO YOU CAN CALCULATE BEING LATE and write it to a csv
  tor = data["time_of_return"]
  try:
    health = data["health"]
  except:
    health = "good"
  note = data["note"]

  # ADDED LOCATION!!!
  location = data["location"]

  match location:
    case "Bratislava":
      location = "BA"
    case "Banská Bystrica":
      location = "BB"
    case "Kosice":
      location = "KE"
    case "Private":
      location = "FF"
    case _:
      location = "ER"

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
      query = """UPDATE lease 
                SET status = %s, 
                time_of_return = %s, 
                note = %s, 
                car_health_check = %s,
                dirty = %s,
                exterior_damage = %s,
                interior_damage = %s,
                collision = %s
                WHERE id_lease = %s;"""
      cur.execute(query, (False, tor, note, damaged, dirty, ext_damage, int_damage, collision, id_lease, ))

      # Get the car ID
      query = "SELECT id_car FROM lease WHERE id_lease = %s;"
      cur.execute(query, (id_lease,))
      id_car, = cur.fetchone()

      # Update the car table
      um = _usage_metric(id_car, conn)
      
      query = "UPDATE car SET health = %s, status = %s, usage_metric = %s, location = %s WHERE id_car = %s;"
      cur.execute(query, (health, 'stand_by', um, location, id_car ))

    conn.commit()
    
    if (damaged == True):
      message = messaging.Message(
        notification=messaging.Notification(
        title=f"Poškodenie auta!",
        body=f"""Email: {email}\nVrátil auto s poškodením!"""
      ),
        topic= "manager"
      )
      send_firebase_message_safe(message)  
    
    return jsonify({'status': "returned"}), 200

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

#PGRV 
@app.route('/check_token', methods = ['POST'])
@jwt_required()
def token_test():
  return jsonify({'msg': 'success'}), 200

if __name__ == "__main__":
  app.run()