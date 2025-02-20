import csv
import os
import hashlib
import jwt
from dateutil import parser 
import psycopg2
from flask_mail import Mail, Message
from flask import Flask, request, jsonify, send_from_directory
import requests
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

# def send_email(msg: str) -> bool:
#   	return requests.post(
#   		"https://api.mailgun.net/v3/sandbox82ff4f07bb7b40a188f61b4766eff128.mailgun.org/messages",
#   		auth=("api", mail_api_key),
#   		data={"from": "ICLS <mailgun@sandbox82ff4f07bb7b40a188f61b4766eff128.mailgun.org>",
#   			"to": ["iclsgamo@gmail.com", "mailgun@sandbox82ff4f07bb7b40a188f61b4766eff128.mailgun.org"],
#   			"subject": "Rezervácia auta",
#   			"text": "Zamestnanec: {user} \n Auto: {auto}, \n Čas od: {timeof}, \n Čas do: {timeto}"})

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

  

  if not email or not password:
    return {"status": False, "msg": f"Chýba meno, heslo!"}
  
  conn, cur = connect_to_db()
  req_salted = login_salt+req_password+login_salt
  req_hashed = hashlib.sha256(req_salted.encode()).hexdigest()

  #! Only allow the admin to create users
  res = cur.execute(
    "SELECT id_driver FROM driver WHERE email = %s AND password = %s AND role LIKE 'admin'", 
    (requester, req_hashed)
  )
  tmp = cur.fetchall()
  if len(tmp) <1:
     return {"status": False, "msg": "Unauthorized"}
  
  salted = login_salt+password+login_salt
  hashed = hashlib.sha256(salted.encode()).hexdigest()


  result = cur.execute(
      "INSERT INTO driver (email, password, role) VALUES (%s, %s, %s)",
      (email, hashed, role)
  )
  
  conn.commit()
  conn.close()
  
  return {"status": True}



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


#Order by reserved first, then by metric and filter by reserved cars by the provided email
# Cars table does not have the email, you will have to get it from the leases table that combines the car and driver table together,
@app.route('/get_car_list', methods=['GET'])
@jwt_required()
def get_car_list():
  if request.method == 'GET':
      conn, cur = connect_to_db()
      if conn is None:
          return jsonify({'error': cur, 'status': 501}), 501

      try:
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
                  SELECT id_car, name, status, url
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


# Warning!!!
# The allowed dates return here is kinda retarted, it would be better to just return a list of start > stop dates that the user would then generate locally
# But i dont feel like doing it, so a MONSTER json has been created, enjoy :)
#
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

    conn, cur = connect_to_db()
    data = request.get_json()

    if conn is None:
        return jsonify({'error': 'Database connection error: ' + cur}), 500

  
    car = data.get("car_id")
    if not car or car == 'none':
        return jsonify({'error': 'The "car_id" parameter is missing or invalid'}), 400

    query = "SELECT * FROM car WHERE id_car = %s;"
    cur.execute(query, (car,))
    res = cur.fetchall()

    if not res:
        return jsonify({'error': 'No car found with the given ID'}), 404

    
    # TODO: this
    #! Here add the check for under_review, as if its true than we need to protect the date range from other users scooping it out 
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
    bratislava_tz = pytz.timezone('Europe/Bratislava')
    def convert_to_bratislava_timezone(dt_obj):
      # Ensure the datetime is in UTC before converting
      utc_time = dt_obj.replace(tzinfo=pytz.utc) if dt_obj.tzinfo is None else dt_obj.astimezone(pytz.utc)
      bratislava_time = utc_time.astimezone(bratislava_tz)  # Convert to Bratislava timezone
      return bratislava_time.strftime("%Y-%m-%d %H:%M:%S") 

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
    
    response = jsonify({"car_details": res, "notallowed_dates": lease_dates})
    return response, 200




# # Get a list of reports, using their name you then download the correct file
#?
    # "reports": [
    #     "/app/reports/2025-01-21 18:06:00exc_ICLS_report.csv"
    # ]
@app.route('/list_reports', methods = ['POST'])
@jwt_required()
def list_reports():
  data = request.get_json()
  email = data["email"]
  role = data["role"]

  conn, curr = connect_to_db()

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
    email = request.args.get('email')
    role = request.args.get('role')
    
    # Validate parameters
    if not email or not role:
        return {"msg": "Missing email or role parameters"}, 400

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
            path=filename
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
  email = data["email"]
  role = data["role"]
  
  bratislava_tz = pytz.timezone('Europe/Bratislava')
  # IF YOU ARE A USER RETURN ONLY FOR YOUR EMAIL
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
          c.drive_type
        FROM 
            lease l
        JOIN 
            driver d ON l.id_driver = d.id_driver
        JOIN 
            car c ON l.id_car = c.id_car
        WHERE 
            l.status = TRUE AND d.email = %s; 
    """
    curr.execute(query, (email,))
  elif role == "manager": 
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
          c.drive_type
        FROM 
            lease l
        JOIN 
            driver d ON l.id_driver = d.id_driver
        JOIN 
            car c ON l.id_car = c.id_car
        WHERE 
            l.status = TRUE; 
    """    
    curr.execute(query)

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
        "shaft": i[12]

      })
    return {"active_leases": leases}, 200
  
  except Exception as e:
    return jsonify(msg=  f"Error recieving leases: {e}"), 500

# needs: email, car name, 
@app.route('/cancel_lease', methods = ['POST'])
@jwt_required()
def cancel_lease():
  # make a sql statement that updates the table lease and sets it stauts to false where you will filter the result by the driver, car, and order by id_lease descending limit 1
  data = request.get_json()
  email = data["email"]

  recipient = ""
  if data["recipient"]:
     recipient = data["recipient"]
  else:
    recipient = email

  car_name = data["car_name"]

  conn, cur = connect_to_db()
  
  try:
    # need to get the car_id  and driver_id 
    cur.execute("select id_driver from driver where email = %s", (recipient,))
    id_name = cur.fetchall()[0][0]

    cur.execute("select id_car from car where name = %s", (car_name,))
    id_car = cur.fetchall()[0][0]
  except Exception as e:
    return jsonify(msg= f"Error cancelling lease!, {e}")
  
  try:
    cur.execute("UPDATE lease SET status = false WHERE id_lease = (SELECT id_lease FROM lease WHERE id_driver = %s AND id_car = %s  AND status = true ORDER BY id_lease DESC LIMIT 1)", (id_name, id_car))
    cur.execute("update car set status = %s where id_car = %s", ("stand_by", id_car))
  except Exception as e:
    return jsonify(msg= f"Error cancelling lease!, {e}")

  conn.commit()
  conn.close()

  return {"cancelled": True}

@app.route('/get_monthly_leases', methods = ['POST'])
@jwt_required()
def get_monthly_leases():
  data = request.get_json()
  role = data["role"]

  if role != "manager":
    return jsonify({'msg': "Only manager can get monthly leases!"})
  else:
    try:
      month = data["month"]
      conn, cur = connect_to_db()
      stmt = "SELECT start_of_lease, time_of_return FROM lease WHERE EXTRACT(MONTH FROM start_of_lease)::int = $s)"

      cur.execute(stmt, (month,))
      res = cur.fetchall()

      conn.close()
      return jsonify(res)
    except Exception as e:
      return jsonify(msg= f"Error getting monthly leases: {e}")

@app.route('/file', methods = ['GET'])
@jwt_required()
def atempetdates():
    #latest_file = get_latest_file(f"{os.getcwd()}/reports")

    path = f"{os.getcwd()}/reports/ICLS_report.csv"
    
    # if latest_file:
    #   with open(latest_file, "a+") as report:
    #     report.write("Posadasdasdasdasdasdznámka")
    # else:

    # Herer chjeck if the if stsetametns are the problem 
    # if so then i may be fucked
    er = "sdssdd"
    if er == "sdsd":
      with open(path, "+a") as new_report:
        new_report.write("NWE RPTORT NEW RPTORT")
    else:
      with open(path, "+a") as new_report:
        new_report.write("TOOT JE DRUHA VEC")

    return {"stauts": True}


# Add a notofication call after leasing, to the manager
# fix private rides
@app.route('/lease_car', methods = ['POST'])
@jwt_required()
def lease_car():
  data =  request.get_json()

  # for whom the lease is 
  username = str(data["username"])
  recipient = data["recipient"]

  role = str(data["role"])
  car_name  = str(data["car_name"])
  stk = str(data["stk"])
  private = data["is_private"]



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
  tmp_of = timeof.split(" ")
  dates =  tmp_of[0].split("-")
  # 02-20-2025 21:40:00+01
  form_timeof = f"{dates[2]}-{dates[1]}-{dates[0]} {tmp_of[1]}"

  # Chnage time to date format
  tmp_to = timeto.split(" ")
  dates =  tmp_to[0].split("-")
  # 02-20-2025 21:40:00+01
  form_timeto = f"{dates[2]}-{dates[1]}-{dates[0]} {tmp_to[1]}"

  # for some fucking reason this function converts my good looking date format into a datermot of NOW, give it a 20/02 and it spits out the current date
  # def convert_to_datetime(string):
  # dt_timeto = convert_to_datetime(timeto)
  # dt_timeof = convert_to_datetime(timeof)
  # # For some reason if i compare these two like this, time to becomes the value from get_sk_date()
  # # Even if i put it into a parentheses
  # # Fuck me thats wierd, loclly on the pc it does not happen tho
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
          
  def get_sk_date_str():
      # Ensure the datetime is in UTC before converting
      dt_obj = datetime.now()
      utc_time = dt_obj.replace(tzinfo=pytz.utc) if dt_obj.tzinfo is None else dt_obj.astimezone(pytz.utc)
      bratislava_time = utc_time.astimezone(bratislava_tz)  # Convert to Bratislava timezone
      return bratislava_time.strftime("%Y-%m-%d %H:%M:%S") 
  
  def compare_timeof(a_timeof, today):
    timeof = convert_to_datetime(string=a_timeof)
    diff = today - timeof
    # If the lease from date is a minute behind the current date, dont allow the lease
    # This gives the user 2 minutes to make a reservation, before being time blocked by leasing into the past
    if (diff.total_seconds()/60) >= 2:
        return True

    
  today = datetime.strptime(get_sk_date_str(), "%Y-%m-%d %H:%M:%S")
  try:
      if convert_to_datetime(timeto) < today:
          return {"status": False, "private": False, "msg": f"Nemožno rezervovať do minulosti.\n Dnes: {today}, \nDO:{timeto}"}
      elif compare_timeof(timeof, today):
          return {"status": False, "private": False, "msg": f"Nemožno rezervovať z minulosti.\n Dnes: {today}, \nOD:{timeof}"}
  except Exception as e:
      return {"status": False, "private": False, "msg": f"{e}"}

  con, cur = connect_to_db()

  def write_report(recipient, car_name, stk, drive_type, timeof, timeto):
    """
    Writes to a csv lease file about a new lease being made, if no such file exists it creates it.
    
    If a report is too old it creates a new one each month. 
    ex: '2025-01-21 15:37:00ICLS_report.csv'
    """
    # To fix the wierd seconds missing error, i will just get rid of the seconds manually
    if timeof.count(":") > 1:
      timeof = timeof[:-3]
    
    if timeto.count(":") > 1:
      timeto = timeto[:-3]

    
    latest_file = get_latest_file(f"{os.getcwd()}/reports")

    # Use year and month to check if a new excel spreadsheet needs to be created
    # '2025-01-21 15:37:00ICLS_report.csv'  '2025-01-21 15:37:26_ICLS_report.csv'
    try:
      # /app/reports/'2025-01-21 17:51:44exc_ICLS_report.csv' -> 2025-01-21 18:53:46

    


      split_date = latest_file.split("-")
      spl_year = split_date[0].removeprefix("/app/reports/")
      spl_month = split_date[1]

      # "%Y-%m-%d %H:%M:%S"
      current_date = get_sk_date().split("-")
      cur_year = current_date[0]
      cur_month = current_date[1]
      
      #timeof = timeof.strftime("%Y-%m-%d %H:%M:%S")
      if int(cur_year) == int(spl_year) and int(cur_month) == int(spl_month):


        wb = openpyxl.load_workbook(latest_file)
        
        # If a sheet name has been made before compare it with today, if its not equal create a new worksheet with the new days number
        all_sheets = wb.sheetnames
        if len(all_sheets) >0:
          cur_day = convert_to_datetime(get_sk_date_str())
          if int(all_sheets[-1]) == cur_day.day:
            # Select the last sheet, that should correspond to the current day
            ws = wb[wb.sheetnames[-1]]
          else: 
            ws = wb.create_sheet(f"{cur_day.day}")


        data = [["","",timeof, timeto, car_name, stk, drive_type, recipient, "NULL", "NULL", "NULL"]]
        for row in data:
          ws.append(row)

        wb.save(latest_file)

      else:
          # Define styles
          red_flag_ft = Font(bold=True, color="B22222")
          red_flag_fill = PatternFill("solid", "B22222")
          Header_fill = PatternFill("solid", "00CCFFFF")
          Header_ft = Font(bold=True, color="000000", size=20)
          Data_ft = Font(size=17)  # New font for data cells

          Header_border = Border(
              left=Side(border_style="thick", color='FF000000'),
              right=Side(border_style="thick", color='FF000000'),
              top=Side(border_style="thick", color='FF000000'),
              bottom=Side(border_style="thick", color='FF000000')
          )

          header_alignment = Alignment(
              horizontal='center',
              vertical='center'
          )
          wb = Workbook()
          del wb["Sheet"]
          ws = wb.create_sheet(f"{convert_to_datetime(get_sk_date_str()).day}")
          #email_ft = Font(bold=True, color="B22222")
          filler = ["","","","","","","",""]
          data = [filler,filler,["", "", "Čas od", "Čas do", "Auto", "SPZ", "Typ","Email", "Odovzdanie", "Meškanie", "Poznámka"],["","",timeof, timeto, car_name, stk, drive_type, recipient, "NULL","NULL","NULL"]]

          for row in data:
              ws.append(row)
              # Format red flag cell (B3)
          red_flag_cell = ws["B3"]
          red_flag_cell.font = red_flag_ft
          red_flag_cell.fill = red_flag_fill
          red_flag_cell.border = Header_border
          email_cell = ws["B3"]
          #email_cell.font = email_ft

          # Set row height for header row
          ws.row_dimensions[3].height = 35

          # Set column widths for data columns
          for col in ["C", "D", "E", "F", "G", "H", "I", "J","K"]:
              ws.column_dimensions[col].width = 23

          # Format header row (C3:J3)
          for row_cells in ws["C3:K3"]:
              for cell in row_cells:
                  cell.font = Header_ft
                  cell.alignment = header_alignment
                  cell.fill = Header_fill
                  cell.border = Header_border

          # Format data rows (from row 4 onwards, columns C-J)
          # for row in ws.iter_rows(min_row=4, min_col=3, max_col=10):
          #     for cell in row:
          #         cell.font = Data_ft
          # Set row height for data rows (from row 4 to the last row)
          wb.save(f"{os.getcwd()}/reports/{get_sk_date()}_EXCEL_ICLS_report.xlsx")

    except Exception as e: #? ONLY HAPPENDS IF THE DIRECTORY IS EMPTY, SO LIKE ONCE
          with open(f"{os.getcwd()}/reports/{get_sk_date()}_ERRORt.txt", "a+") as file:
             file.write(f"{e}")

          # Define styles
          red_flag_ft = Font(bold=True, color="B22222")
          red_flag_fill = PatternFill("solid", "B22222")
          Header_fill = PatternFill("solid", "00CCFFFF")
          Header_ft = Font(bold=True, color="000000", size=20)
          Data_ft = Font(size=17)  # New font for data cells
          Header_border = Border(left=Side(border_style="thick", color='FF000000'),right=Side(border_style="thick", color='FF000000'),top=Side(border_style="thick", color='FF000000'),bottom=Side(border_style="thick", color='FF000000'))
          header_alignment = Alignment(horizontal='center',vertical='center')

          wb = Workbook()
          del wb["Sheet"]
          ws = wb.create_sheet(f"{convert_to_datetime(get_sk_date_str()).day}")
          filler = ["","","","","","","",""]
          data = [filler,filler,["", "", "Čas od", "Čas do", "Auto", "SPZ", "TYP","Email", "Odovzdanie", "Meškanie", "Poznámka"],["","",timeof, timeto, car_name, stk, drive_type, recipient,"NULL","NULL","NULL"]]
          for row in data:
              ws.append(row)
              # Format red flag cell (B3)
          red_flag_cell = ws["B3"]
          red_flag_cell.font = red_flag_ft
          red_flag_cell.fill = red_flag_fill
          red_flag_cell.border = Header_border
          email_cell = ws["B3"]
          # Set row height for header row
          ws.row_dimensions[3].height = 35
          # Set column widths for data columns
          for col in ["C", "D", "E", "F", "G", "H", "I", "J", "K"]:
              ws.column_dimensions[col].width = 23
          # Format header row (C3:J3)
          for row_cells in ws["C3:K3"]:
              for cell in row_cells:
                  cell.font = Header_ft
                  cell.alignment = header_alignment
                  cell.fill = Header_fill
                  cell.border = Header_border
          # Format data rows (from row 4 onwards, columns C-J)
          # for row in ws.iter_rows(min_row=4, min_col=3, max_col=10):
          #     for cell in row:
          #         cell.font = Data_ft
                  # Set row height for data rows (from row 4 to the last row)
          wb.save(f"{os.getcwd()}/reports/{get_sk_date()}_NW_ICLS_report.xlsx")

  # user is a list within a list [[]] to access it use double [0][1,2,3,4]
  cur.execute("select * from car where name = %s", (car_name,))
  
  car_data = cur.fetchall()
  
  drive_type = f"{car_data[0][9]}, {car_data[0][10]}"
  # Check if a lease conflicts time wise with another
  # SQL FORMAT:  2025-01-01 16:10:00+01 | 2025-01-10 15:15:00+01 
  #   "timeof": "2025-01-21 20:10:00+01",
  #   "timeto": "2025-02-10 11:14:00+01"
  # USER ROLE CHECKER
  cur.execute("select id_car from car where name = %s", (car_name,))
  car_id = cur.fetchall()[0][0]

  cur.execute("select * from driver where email = %s and role = %s", (username, role,))
  user = cur.fetchall()
  
  # Check for the leased car if it has available date range to lease from
  cur.execute("""
    SELECT id_lease start_of_lease, end_of_lease FROM lease 
    WHERE status = true AND id_car = %s  
      AND (start_of_lease < %s AND end_of_lease > %s 
           OR start_of_lease < %s AND end_of_lease > %s 
           OR start_of_lease >= %s AND start_of_lease < %s
           OR start_of_lease = %s AND end_of_lease = %s
              )
    """, (car_id,timeof, timeto, timeto, timeof, timeof, timeto, timeof, timeto))
  
  #return {"sd": timeof, "sda": timeto}, 200
  conflicting_leases = cur.fetchall()
  if len(conflicting_leases) > 0:
     return {"status": False, "private": False, "msg": f"Zabratý dátum (hodina typujem)"}
  
  # If the user is leasing for himself
  if recipient ==  username:
    if private == True:
      if user[0][3] != "manager" or user[0][3] != "admin":
        # Just need to create a requst row, a new lease is only created and activated after being approved in the approve_request route
        cur.execute("insert into request(start_of_request, end_of_request, status, id_car, id_driver) values (%s, %s, %s, %s, %s)", (timeof, timeto, True, car_data[0][0], user[0][0]))
        con.commit()

        message = messaging.Message(
                  notification=messaging.Notification(
                  title=f"Žiadosť o súkromnu jazdu!",
                  body=f"""email: {username} \n Od: {timeof} \n Do: {timeto}"""
              ),
                  topic="manager"
              )
        messaging.send(message)

        return {"status": True, "private": True, "msg": f"Request for a private ride was sent!"}, 500

      else: # User is a manager, therfore no request need to be made, and a private ride is made 
        try:
          cur.execute("insert into lease(id_car, id_driver, start_of_lease, end_of_lease, status, private) values (%s, %s, %s, %s, %s,%s)", (car_data[0][0], user[0][0], timeof, timeto, True, True))
          con.commit()
        except Exception as e:
          return {"status": False, "private": False, "msg": f"Error has occured! 113"}, 500
        write_report(recipient, car_name,stk,drive_type, form_timeof, form_timeto)
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
              body=f"""email: {recipient} \n Od: {timeof} \n Do: {timeto}"""
          ),
              topic="manager"
          )
    messaging.send(message)

    #!!!!!!!!!!!!
    write_report(recipient, car_name,stk,drive_type, form_timeof, form_timeto)
    #send_email(msg="Auto bolo rezervovane!")

    return {"status": True, "private": private}

  # If the user leasing is a manager allow him to order lease for other users
  elif user[0][3]  == "manager":
    try:
      # If the manager is leasing a car for someone else check if the recipeint exists and lease for his email
      try:
        cur.execute("select id_driver from driver where email = %s", (recipient,)) # NO need to check for role here!!!
        id_recipient = cur.fetchall()
        if private == False:
          cur.execute("insert into lease(id_car, id_driver, start_of_lease, end_of_lease, status, private) values (%s, %s, %s,  %s, %s, %s)", (car_data[0][0], id_recipient[0][0], timeof, timeto, True, False))
        else:
          cur.execute("insert into lease(id_car, id_driver, start_of_lease, end_of_lease, status, private) values (%s, %s, %s,  %s, %s, %s)", (car_data[0][0], id_recipient[0][0], timeof, timeto, True, True))

      except:
        return {"status": False, "private": False, "msg": f"Error has occured! 111"}, 500
            
      con.commit()
      
      # Upozorni manazerou iba ak si leasne auto normalny smrtelnik 
      #!!!!!!!!!!!!!!!!!!!!!!  POZOR OTAZNIK NEZNAMY SYMBOL JE NEW LINE CHARACTER OD TIALTO: http://www.unicode-symbol.com/u/0085.html
      message = messaging.Message(
                notification=messaging.Notification(
                title=f"Upozornenie o leasingu auta: {car_name}!",
                body=f"""email: {recipient} \n Od: {timeof[:-4]} \n Do: {timeto}"""
            ),
                topic="manager"
            )
      messaging.send(message)
    except Exception as e:
      return {"status": False, "private": False, "msg": f"Error has occured! 112"}, 500
    con.close()

    #!!!  
    write_report(recipient, car_name,stk, drive_type, form_timeof, form_timeto)
    #send_email(msg="Auto bolo rezervovane!")
    return {"status": True, "private": private}
      
  else:
    return {"status": False, "private": False, "msg": f"Users do not match, nor is the requester a manager."}, 500



@app.route('/get_requests', methods = ['POST'])
@jwt_required()
def get_requests():
  data = request.get_json()
  email = data["email"]
  role = data["role"]

  if not data:
     return {"msg": "No Data."}, 501
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
  email = data["email"]
  role = data["role"]

  request_id = data["request_id"]
  timeof = data["timeof"]
  timeto = data["timeto"]
  car_name = data["id_car"]
  
  conn, curr = connect_to_db()

  curr.execute("select id_car from car where name = %s", (car_name,))
  car = curr.fetchall()
  if not car:
    return {"status": False, "msg": "Car does not exist."}
  car_id = car[0][0]

  curr.execute("select id_driver from driver where email = %s and role = %s", (email, role,))
  user = curr.fetchall()
  if len(user) == 0:
    return {"status": False, "msg": "No such user exists!"}, 400

  if approval == True:
    # Create a lease and change the requests statust o false
    try:
      curr.execute("update request set status = FALSE where id_request = %s ", (request_id, ))
      curr.execute("insert into lease(id_car, id_driver, start_of_lease, end_of_lease, status, private) values (%s, %s, %s, %s, %s,%s)", (car_id, user[0][0], timeof, timeto, True, True))
    except Exception as e:
      return {"status": False, "msg": f"Error approving, {e}"}, 400
  
  elif approval == False:
    # Just deactivaet the request, dont create a lease
    curr.execute("update request set status = FALSE where id_request = %s ", (request_id, ))


  conn.commit()
  conn.close()

  return {"status": True, "msg": "Success"}, 200




@app.route('/return_car', methods = ['POST'])
@jwt_required() 
def return_car():
  data = request.get_json()
  if not data:
    return jsonify({'error': 'No data'}), 501
  
  def edit_csv_row(timeof,timeto, return_date, meskanie, new_note):
      # Get rid of the seconds, cuz python sometimes cuts them off on one date and that fucks up the editing proces
      # So just get rid of them yourself
      if timeof.count(":") > 1:
        timeof = timeof[:-3]
    
      if timeto.count(":") > 1:
        timeto = timeto[:-3]
      
      csv_file_path = get_latest_file(f"{os.getcwd()}/reports")

      # rows = []
      # with open(csv_file_path, mode='r', newline='\n', encoding='utf-8') as file:
      #     reader = csv.DictReader(file)
      #     fieldnames = reader.fieldnames
      #     for row in reader:
      #         rows.append(row)
      # # email,auto,stk,cas_od,cas_do,odovzdanie,meskanie,note
      # # cas_od: 2025-02-02 20:50 
      # # Find the row with the matching recipient email and update the specified columns
      # # cas_do: 2025-02-01 16:00
      # for row in rows:
      #     if row['cas_od'] == timeof and row["cas_do"] == timeto:
      #         row['odovzdanie'] = return_date
      #         row['meskanie'] = meskanie
      #         row['note'] = new_note
      #         break

      # # Write the updated rows back to the CSV file
      # with open(csv_file_path, mode='w', newline='\n', encoding='utf-8') as file:
      #     writer = csv.DictWriter(file, fieldnames=fieldnames)
      #     writer.writeheader()
      #     writer.writerows(rows)

      wb = openpyxl.load_workbook(csv_file_path)
      sheet1 = wb.active

      # Loop over all rows in the worksheet
      # ["","Čas od", "Čas do", "Auto", "SPZ","Email", "Odovzdanie", "Meškanie", "Poznámka"]
      for row in range(3, sheet1.max_row + 1):
          # Get the values from the cells in the current row
          exc_timeof = sheet1.cell(row=row, column=1).value
          exc_timeto = sheet1.cell(row=row, column=2).value
          time_of_return_cell = sheet1.cell(row=row, column=7)
          late_return_cell = sheet1.cell(row=row, column=8)
          note_cell = sheet1.cell(row=row, column=9)
          
            # To avoid duplicates when returing, as dates could collide probalby idk fuck my stupid chungus life 
          if time_of_return_cell.value == "NULL":

              if exc_timeof == timeof and exc_timeto == timeto:
                  time_of_return_cell.value = tor
                  late_return_cell.value = meskanie
                  note_cell.value = new_note

      # Save changes to the workbook
      wb.save(csv_file_path)
    
  
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
      query = "UPDATE lease SET status = %s, time_of_return = %s, note = %s WHERE id_lease = %s;"
      cur.execute(query, (False, tor, note, id_lease))

      # Get the car ID
      query = "SELECT id_car FROM lease WHERE id_lease = %s;"
      cur.execute(query, (id_lease,))
      id_car, = cur.fetchone()

      # Update the car table
      um = _usage_metric(id_car, conn)
      
      # no longer needed to reset status!!!
      query = "UPDATE car SET health = %s, status = %s, usage_metric = %s, location = %s WHERE id_car = %s;"
      cur.execute(query, (health, 'stand_by', um, location, id_car ))

      # If the return date is after the timeof, indicate late return of car
      late_return = "False"
      # Str + datetime.datetime
      
      tor_as_datetime = datetime.strptime(tor, "%Y-%m-%d %H:%M:%S.%f%z")
      # Now you can compare the two datetime objects
      if tor_as_datetime < res[0][2]:
          late_return = "True"
      else:
          late_return = "False"

      str_timeof = res[0][1].strftime("%Y-%m-%d %H:%M:%S")
      str_timeto = res[0][2].strftime("%Y-%m-%d %H:%M:%S")

      # Get rid of the miliseconds
      tor = tor_as_datetime.strftime("%Y-%m-%d %H:%M:%S")
      # Update report, open as csv object, look for row where time_from ,time_to, id_car, id_driver is the same and update the return&-time, meskanie and note values
      edit_csv_row(timeof=str_timeof, timeto=str_timeto, return_date=tor, meskanie=late_return, new_note= note)

    conn.commit()
    

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