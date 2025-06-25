# Modifications to existing lease endpoints to handle trip vs regular lease distinction

# Modified version of your existing get_leases endpoint
@app.route('/get_leases', methods = ['POST'])
@jwt_required()
def get_leases():
  conn, curr = connect_to_db()
  
  data = request.get_json()

  # Add new parameter to control if trip leases should be included
  include_trip_leases = data.get('include_trip_leases', False)
  
  # Existing filter parameters
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
          l.status,
          l.id_trip,
          t.trip_name,
          CASE WHEN l.id_trip IS NOT NULL THEN 'trip' ELSE 'regular' END as lease_type
        FROM 
            lease l
        JOIN 
            driver d ON l.id_driver = d.id_driver
        JOIN 
            car c ON l.id_car = c.id_car
        LEFT JOIN
            trips t ON l.id_trip = t.id_trip
        WHERE 
            d.email = %(user_email)s
            AND (
                ( %(ft_istrue)s = true AND l.status = true )
                OR 
                ( %(ft_isfalse)s = true AND l.status = false )
            )
            AND (
                %(include_trip_leases)s = true 
                OR l.id_trip IS NULL
            ); 
    """
    params = {
      'ft_istrue': ft_istrue,
      'ft_isfalse': ft_isfalse,
      'user_email': email,
      'include_trip_leases': include_trip_leases
    }
    curr.execute(query, params)

  elif role == "manager" or role == "admin": 
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
            l.status,
            l.id_trip,
            t.trip_name,
            CASE WHEN l.id_trip IS NOT NULL THEN 'trip' ELSE 'regular' END as lease_type
        FROM 
            lease l
        JOIN 
            driver d ON l.id_driver = d.id_driver
        JOIN 
            car c ON l.id_car = c.id_car
        LEFT JOIN
            trips t ON l.id_trip = t.id_trip
        WHERE 
            (
                ( %(ft_istrue)s = true AND l.status = true )
                OR 
                ( %(ft_isfalse)s = true AND l.status = false )
            )
            AND ( %(ft_email)s IS NULL OR d.email = %(ft_email)s )
            AND ( %(ft_car)s IS NULL OR c.name = %(ft_car)s )
            AND ( %(ft_timeof)s IS NULL OR l.start_of_lease >= %(ft_timeof)s )
            AND ( %(ft_timeto)s IS NULL OR l.end_of_lease <= %(ft_timeto)s )
            AND (
                %(include_trip_leases)s = true 
                OR l.id_trip IS NULL
            );
      """
    params = {
      'ft_istrue': ft_istrue,
      'ft_isfalse': ft_isfalse,
      'ft_email': ft_email,
      'ft_car': ft_car,
      'ft_timeof': ft_timeof,
      'ft_timeto': ft_timeto,
      'include_trip_leases': include_trip_leases
    }
    curr.execute(query, params)

  def convert_to_bratislava_timezone(dt_obj):
      bratislava_tz = pytz.timezone('Europe/Bratislava')

      if dt_obj.tzinfo is None:
          utc_time = pytz.utc.localize(dt_obj)
      else:
          utc_time = dt_obj.astimezone(pytz.utc)

      bratislava_time = utc_time.astimezone(bratislava_tz)
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
        "status": i[13],
        "trip_id": i[14],  # NEW: Trip ID if this is a trip lease
        "trip_name": i[15],  # NEW: Trip name if this is a trip lease
        "lease_type": i[16]  # NEW: 'trip' or 'regular'
      })

    conn.close()
    return {"active_leases": leases}, 200
  
  except Exception as e:
    return jsonify(msg=  f"Error recieving leases: {e}"), 500


# New endpoint to get ONLY regular (non-trip) leases
@app.route('/get_regular_leases', methods = ['POST'])
@jwt_required()
def get_regular_leases():
    """Get only regular leases (exclude trip-related leases)"""
    # Call the existing get_leases with include_trip_leases=False
    original_data = request.get_json()
    original_data['include_trip_leases'] = False
    
    # Temporarily replace request data
    request._cached_json = original_data
    
    return get_leases()


# New endpoint to get ONLY trip-related leases  
@app.route('/get_trip_leases', methods = ['POST'])
@jwt_required()
def get_trip_leases():
    """Get only trip-related leases"""
    conn, curr = connect_to_db()
    
    claims = get_jwt()
    email = claims.get('sub', None)
    role = claims.get('role', None)
    
    try:
        if role == "user":
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
                  l.status,
                  l.id_trip,
                  t.trip_name,
                  'trip' as lease_type
                FROM 
                    lease l
                JOIN 
                    driver d ON l.id_driver = d.id_driver
                JOIN 
                    car c ON l.id_car = c.id_car
                JOIN
                    trips t ON l.id_trip = t.id_trip
                WHERE 
                    d.email = %s
                    AND l.id_trip IS NOT NULL
                ORDER BY l.start_of_lease DESC; 
            """
            curr.execute(query, (email,))
        else:
            return {"error": "Unauthorized"}, 403
            
        def convert_to_bratislava_timezone(dt_obj):
            bratislava_tz = pytz.timezone('Europe/Bratislava')
            if dt_obj.tzinfo is None:
                utc_time = pytz.utc.localize(dt_obj)
            else:
                utc_time = dt_obj.astimezone(pytz.utc)
            bratislava_time = utc_time.astimezone(bratislava_tz)
            return bratislava_time.strftime("%Y-%m-%d %H:%M:%S")
        
        res = curr.fetchall()
        trip_leases = []
        for i in res:
            trip_leases.append({
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
                "status": i[13],
                "trip_id": i[14],
                "trip_name": i[15],
                "lease_type": i[16]
            })

        conn.close()
        return {"trip_leases": trip_leases}, 200
        
    except Exception as e:
        return jsonify(msg=f"Error receiving trip leases: {e}"), 500


# Modified cancel_lease to handle trips
@app.route('/cancel_lease_or_trip', methods = ['POST'])
@jwt_required()
def cancel_lease_or_trip():
    data = request.get_json()
    claims = get_jwt()
    email = claims.get('sub', None)
    role = claims.get('role', None)

    lease_id = data.get("lease_id")
    recipient = data.get("recipient", email)
    car_name = data.get("car_name")

    # Only managers and admins can cancel other peoples rides
    if recipient != email:
        if role not in ["manager", "admin"]:
            return {"cancelled": False}, 400
 
    conn, cur = connect_to_db()
    
    try:
        # Check if this lease is part of a trip
        cur.execute("SELECT id_trip FROM lease WHERE id_lease = %s", (lease_id,))
        lease_result = cur.fetchone()
        
        if not lease_result:
            return {"cancelled": False, "msg": "Lease not found"}, 404
            
        trip_id = lease_result[0]
        
        if trip_id:
            # This is a trip lease - need special handling
            return {"cancelled": False, 
                   "msg": "This reservation is part of a trip. Please cancel the entire trip instead.",
                   "trip_id": trip_id}, 400
        
        # Regular lease cancellation logic (your existing code)
        cur.execute("select id_driver from driver where email = %s", (recipient,))
        id_name = cur.fetchall()[0][0]

        cur.execute("select id_car from car where name = %s", (car_name,))
        id_car = cur.fetchall()[0][0]
        
        cur.execute("UPDATE lease SET status = false WHERE id_lease = %s", (lease_id,))
        sql_status_message = cur.statusmessage
        cur.execute("update car set status = %s where id_car = %s", ("stand_by", id_car))
        
        # Send notification if manager cancelling for someone else
        if (role in ["manager", "admin"]) and (email != recipient):
            msg_rec = recipient.replace("@" ,"_")
            message = messaging.Message(
                notification=messaging.Notification(
                title=f"Vaša rezervácia bola zrušená!",
                body=f"""Rezervácia pre auto: {car_name} bola zrušená."""
            ),
                topic=msg_rec
            )
            send_firebase_message_safe(message)

            create_notification(conn, cur, recipient, car_name,'user', 
                              f"Vaša rezervácia bola zrušená!",
                              f"""Rezervácia pre auto: {car_name} bola zrušená.""", 
                              is_system_wide=False)
 
        conn.commit()
        conn.close()

        return {"cancelled": True, "msg": sql_status_message}, 200
        
    except Exception as e:
        return jsonify(msg= f"Error cancelling lease!, {e}"), 500 