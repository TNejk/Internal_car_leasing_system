import os
import hashlib
import jwt
import psycopg2
from flask_mail import Mail, Message
from flask import Flask, request, jsonify
from flask_jwt_extended import JWTManager, create_access_token, create_refresh_token, jwt_required, get_jwt_identity, get_jwt
from flask_cors import CORS, cross_origin
from functools import wraps
from datetime import datetime, timedelta, timezone
from dateutil.parser import parse
import pytz
import openpyxl
import glob
import firebase_admin
from firebase_admin import credentials
from firebase_admin import messaging

bratislava_tz = pytz.timezone('Europe/Bratislava')

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

def send_email(msg: str) -> bool:
  msg = Message(
    'ICLS Rezervácia auta, ' + datetime.now(pytz.timezone('Europe/Bratislava')),
    recipients=['recipient@example.com'],
    body=msg
  )
  mail.send(msg)
  return True

def get_latest_file(folder_path):
    """
    Returns the path to the latest created file in a specified folder.

    Parameters:
        folder_path (str): The path to the folder.

    Returns:
        str: The full path of the latest created file, or None if the folder is empty.
    """
    try:
        # Get a list of all files in the folder with their full paths
        files = [os.path.join(folder_path, f) for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f))]
        
        if not files:
            return None  # Return None if the folder is empty
        
        # Get the latest created file by creation time
        latest_file = max(files, key=os.path.getctime)
        
        return latest_file
    except Exception as e:
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
    
    # get a list of dates split by 30 miniyute intervals for each car
    # where first check if an active lease exists for that car and edit the list of dates removing times between the active leases

    def get_dates_to_end_of_month(interval_minutes=60, tz=pytz.timezone('Europe/Bratislava')) -> list:
        """
        Generate a list of datetime strings from now until the end of the current month in specified intervals.
        
        :param interval_minutes: The interval in minutes. Default is 60.
        :param tz: The timezone to use. Default is 'Europe/Bratislava'.
        :return: A list of formatted datetime strings (yyyy-MM-dd HH:mm:ss).
        """
        # Get the current time with timezone information
        now = datetime.now(tz).replace(microsecond=0)

        # Calculate the start of the next month
        next_month = (now.month % 12) + 1
        year = now.year + (1 if next_month == 1 else 0)
        start_of_next_month = tz.localize(datetime(year, next_month, 1))

        # Generate the list of formatted date strings
        dates = []

        while now < start_of_next_month:
            # Format the datetime in the new format (yyyy-MM-dd HH:mm:ss)
            formatted_date = now.strftime("%Y-%m-%d %H:%M:%S")
            dates.append(formatted_date)
            now += timedelta(minutes=interval_minutes)

        return dates

    def filter_dates(rm_dates):
        """
        Remove dates from the list generated by get_dates_to_end_of_month that fall within specified ranges.

        :param rm_dates: A list of tuples with start and end datetime objects, e.g., [(datetime_from, datetime_to)].
        :return: A filtered list of datetime objects.
        """
        tz = pytz.timezone('Europe/Bratislava')
        # Convert the string dates back to datetime objects
        data_list = [datetime.strptime(date, "%a, %d %b %Y %H:%M:%S GMT").replace(tzinfo=tz) 
                    for date in get_dates_to_end_of_month()]
        
        if not rm_dates:
            return data_list

        # Filter out dates that fall within the specified ranges
        for start, end in rm_dates:
            data_list = [date for date in data_list if not (start <= date <= end)]
        
        return data_list

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

    
    #! Remove dates from allowed dates if an active lease exists so you wont lease a car on the same date 
    #date_list = get_dates_to_end_of_month()
    query = "SELECT start_of_lease, end_of_lease FROM lease WHERE id_car = %s AND status = %s;"

    cur.execute(query, (car, True, ))
    resu = cur.fetchall()

    # [
    #     [
    #         "Thu, 12 Dec 2024 16:01:22 GMT",
    #         "Thu, 12 Dec 2024 17:01:22 GMT"
    #     ]
    # ]
    dates = []

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

    # Parse the dates
    lease_dates = parse_lease_dates(resu)
    #dates = filter_dates(lease_dates)
    

    response = jsonify({"car_details": res, "notallowed_dates": lease_dates})
    return response, 200


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
          l.private
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
          l.private
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
      # Ensure the datetime is in UTC before converting
      utc_time = dt_obj.replace(tzinfo=pytz.utc) if dt_obj.tzinfo is None else dt_obj.astimezone(pytz.utc)
      bratislava_time = utc_time.astimezone(bratislava_tz)  # Convert to Bratislava timezone
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
  private = data["is_private"]

  # Needed date format
  # 2011-08-09 00:00:00+09
  timeof = data["timeof"]
  timeto = data["timeto"]

  con, cur = connect_to_db()

  def write_report(recipient, car_name, timeof, timeto):
    """
    Writes to a csv lease file about a new lease being made, if no such file exists it creates it.
    
    If a report is too old it creates a new one each month. 
    ex: '2025-01-21 15:37:00ICLS_report.csv'
    """
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
      
      if cur_year == spl_year and spl_month == cur_month:
        with open(latest_file, "a+") as report_file:
            report_file.write(f"{recipient},{car_name},{timeof},{timeto},{"REPLACE"},{"LATEST_FILE"}")

      else:
          path = f"{os.getcwd()}/reports/{get_sk_date()}_ICLS_report.csv"
          with open(path, "a+") as new_file: 
            new_file.write(f"email,auto,cas_od,cas_do,meskanie,note\n")
            new_file.write(f"{recipient},{car_name},{timeof},{timeto},{split_date},{current_date}\n")

    except Exception as e:
      #? Triggered only if ./reports is empty or a naming issue
      path = f"{os.getcwd()}/reports/{get_sk_date()}exc_ICLS_report.csv"
      with open(path, "a+") as new_file: 
        new_file.write(f"email,auto,cas_od,cas_do,meskanie,note\n")
        new_file.write(f"{recipient},{car_name},{timeof},{timeto},{"REPLACE"},{"REPLACE"}\n")
    

  # Check if a lease conflicts time wise with another
  # This doesnt work for some reason
  # probalby beacue the sql is fucked up
  # SQL FORMAT:  2025-01-01 16:10:00+01        | 2025-01-10 15:15:00+01 
  #   "timeof": "2025-01-21 20:10:00+01",
  #   "timeto": "2025-02-10 11:14:00+01"

  cur.execute("""
    SELECT id_lease start_of_lease, end_of_lease FROM lease 
    WHERE status = true 
      AND (start_of_lease < %s AND end_of_lease > %s 
           OR start_of_lease < %s AND end_of_lease > %s 
           OR start_of_lease >= %s AND start_of_lease < %s
           OR start_of_lease = %s AND end_of_lease = %s
              )
    """, (timeof, timeto, timeto, timeof, timeof, timeto, timeof, timeto))
  
  #return {"sd": timeof, "sda": timeto}, 200
  conflicting_leases = cur.fetchall()
  if len(conflicting_leases) > 1:
     return {"status": False, "private": False, "msg": f"{conflicting_leases}"}
  
  # USER ROLE CHECKER
  cur.execute("select id_car from car where name = %s", (car_name,))
  car_id = cur.fetchall()[0][0]

  # user is a list within a list [[]] to access it use double [0][1,2,3,4]
  cur.execute("select * from driver where email = %s and role = %s", (username, role,))
  user = cur.fetchall()

  cur.execute("select * from car where name = %s", (car_name,))
  car_data = cur.fetchall()

  # compare the user leasing and user thats recieving the lease,
  if recipient ==  username:
    
    # Priavte ride check
    if private == True:
      if user[0][3] == role:
        pass
      else: return {"status": False, "private": False, "msg": f"User cannot order private rides"}, 500

    try:
      # id, userid, carid, timeof, timeto, tiemreturn, status, note, status is either 1 or zero to indicate boolean values
      cur.execute("insert into lease(id_car, id_driver, start_of_lease, end_of_lease, status) values (%s, %s, %s, %s, %s)", (car_data[0][0], user[0][0], timeof, timeto, True))
      #cur.execute("update car set status = %s where name = %s", ("leased", car_name,))
      con.commit()
    except Exception as e:
      return {"status": False, "private": False, "msg": f"Error has occured! #113"}, 500
    
    con.close()
    message = messaging.Message(
              notification=messaging.Notification(
              title="Upozornenie o leasingu auta!",
              body=f"""Zamestnanec: {recipient} si rezervoval auto: {car_name}! \n Rezervácia trvá: \n od {timeof} \n do {timeto} !"""
          ),
              topic="manager"
          )
    messaging.send(message)

    #!!!!!!!!!!!!
    write_report(recipient, car_name, timeof, timeto)
    return {"status": True, "private": private}

  # If the user leasing is a manager allow him to order lease for other users
  elif user[0][3]  == "manager":
    try:
      # If the manager is leasing a car for someone else check if the recipeint exists and lease for his email
      try:
        cur.execute("select id_driver from driver where email = %s", (recipient,)) # NO need to check for role here!!!
        recipient = cur.fetchall()
        if private == False:
          cur.execute("insert into lease(id_car, id_driver, start_of_lease, end_of_lease, status, private) values (%s, %s, %s,  %s, %s, %s)", (car_data[0][0], recipient[0][0], timeof, timeto, True, False))
        else:
          cur.execute("insert into lease(id_car, id_driver, start_of_lease, end_of_lease, status, private) values (%s, %s, %s,  %s, %s, %s)", (car_data[0][0], recipient[0][0], timeof, timeto, True, True))

      except:
        return {"status": False, "private": False, "msg": f"Error has occured! #111"}, 500
            
      con.commit()
      # Upozorni manazerou iba ak si leasne auto normalny smrtelnik 
      message = messaging.Message(
                notification=messaging.Notification(
                title="Upozornenie o leasingu auta!",
                body=f"""Zamestnanec: {recipient} si rezervoval auto: {car_name}! \n Rezervácia trvá: \n od {timeof} \n do {timeto} !"""
            ),
                topic="manager"
            )
      messaging.send(message)
    except Exception as e:
      return {"status": False, "private": False, "msg": f"Error has occured! #112"}, 500
    con.close()

    #!!!  
    write_report(recipient, car_name, timeof, timeto)
    return {"status": True, "private": private}
      
  else:
    return {"status": False, "private": False, "msg": f"Users do not match, nor is the requester a manager."}, 500


@app.route('/return_car', methods = ['POST'])
@jwt_required() 
def return_car():
  data = request.get_json()
  if not data:
    return jsonify({'error': 'No data'}), 501

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