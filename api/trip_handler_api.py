# Example API endpoints for the trips system
# Add these to your Flask app

@app.route('/create_trip', methods=['POST'])
@jwt_required()
def create_trip():
    claims = get_jwt()
    creator_email = claims.get('sub', None)
    role = claims.get('role', None)
    
    data = request.get_json()
    
    try:
        trip_name = data['trip_name']
        destination_name = data['destination_name']
        start_time = data['start_time']
        end_time = data['end_time']
        selected_cars = data['cars']  # List of car IDs
        car_assignments = data['car_assignments']  # Dict: {car_id: [list of user emails]}
        description = data.get('description', '')
        destination_lat = data.get('destination_lat')
        destination_lon = data.get('destination_lon')
    except KeyError as e:
        return {"status": False, "msg": f"Missing required field: {e}"}, 400
    
    conn, cur = connect_to_db()
    
    try:
        # Get creator ID
        cur.execute("SELECT id_driver FROM driver WHERE email = %s", (creator_email,))
        creator_id = cur.fetchone()[0]
        
        # Create the trip
        cur.execute("""
            INSERT INTO trips (trip_name, creator_id, destination_name, destination_lat, 
                             destination_lon, start_time, end_time, description)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id_trip
        """, (trip_name, creator_id, destination_name, destination_lat, 
              destination_lon, start_time, end_time, description))
        
        trip_id = cur.fetchone()[0]
        
        # Add cars to the trip
        for car_id in selected_cars:
            cur.execute("""
                INSERT INTO trip_cars (id_trip, id_car)
                VALUES (%s, %s)
                RETURNING id_trip_car
            """, (trip_id, car_id))
            
            trip_car_id = cur.fetchone()[0]
            
            # Add participants for this car
            if str(car_id) in car_assignments:
                for user_email in car_assignments[str(car_id)]:
                    # Get user ID
                    cur.execute("SELECT id_driver FROM driver WHERE email = %s", (user_email,))
                    user_result = cur.fetchone()
                    if user_result:
                        user_id = user_result[0]
                        
                        # Determine role (first person is driver)
                        participant_role = 'driver' if user_email == car_assignments[str(car_id)][0] else 'passenger'
                        
                        cur.execute("""
                            INSERT INTO trip_participants (id_trip, id_trip_car, id_driver, role)
                            VALUES (%s, %s, %s, %s)
                        """, (trip_id, trip_car_id, user_id, participant_role))
                        
                        # Send notification to invited user
                        if user_email != creator_email:
                            create_notification(
                                conn, cur, user_email, None, 'user',
                                f"Pozvánka na výlet: {trip_name}",
                                f"Boli ste pozvaní na výlet do {destination_name}. Skontrolujte podrobnosti v aplikácii.",
                                is_system_wide=False
                            )
        
        conn.commit()
        return {"status": True, "trip_id": trip_id, "msg": "Trip created successfully"}, 200
        
    except Exception as e:
        conn.rollback()
        return {"status": False, "msg": f"Error creating trip: {e}"}, 500
    finally:
        conn.close()


@app.route('/get_trip_invitations', methods=['GET'])
@jwt_required()
def get_trip_invitations():
    claims = get_jwt()
    user_email = claims.get('sub', None)
    
    conn, cur = connect_to_db()
    
    try:
        cur.execute("SELECT id_driver FROM driver WHERE email = %s", (user_email,))
        user_id = cur.fetchone()[0]
        
        # Get pending trip invitations
        cur.execute("""
            SELECT t.id_trip, t.trip_name, t.destination_name, t.start_time, t.end_time,
                   c.name as car_name, tp.role, tp.invitation_status, tp.id_participant,
                   d.name as creator_name
            FROM trip_participants tp
            JOIN trips t ON tp.id_trip = t.id_trip
            JOIN trip_cars tc ON tp.id_trip_car = tc.id_trip_car
            JOIN car c ON tc.id_car = c.id_car
            JOIN driver d ON t.creator_id = d.id_driver
            WHERE tp.id_driver = %s AND tp.invitation_status = 'pending'
            ORDER BY tp.invited_at DESC
        """, (user_id,))
        
        invitations = []
        for row in cur.fetchall():
            invitations.append({
                "trip_id": row[0],
                "trip_name": row[1],
                "destination": row[2],
                "start_time": row[3].isoformat(),
                "end_time": row[4].isoformat(),
                "car_name": row[5],
                "role": row[6],
                "status": row[7],
                "participant_id": row[8],
                "creator_name": row[9]
            })
        
        return {"invitations": invitations}, 200
        
    except Exception as e:
        return {"status": False, "msg": f"Error fetching invitations: {e}"}, 500
    finally:
        conn.close()


@app.route('/respond_to_trip_invitation', methods=['POST'])
@jwt_required()
def respond_to_trip_invitation():
    claims = get_jwt()
    user_email = claims.get('sub', None)
    
    data = request.get_json()
    participant_id = data['participant_id']
    response = data['response']  # 'accept' or 'decline'
    
    if response not in ['accept', 'decline']:
        return {"status": False, "msg": "Invalid response"}, 400
    
    conn, cur = connect_to_db()
    
    try:
        # Update invitation status
        status = 'accepted' if response == 'accept' else 'declined'
        cur.execute("""
            UPDATE trip_participants 
            SET invitation_status = %s, responded_at = NOW()
            WHERE id_participant = %s
            RETURNING id_trip, id_trip_car
        """, (status, participant_id))
        
        result = cur.fetchone()
        if not result:
            return {"status": False, "msg": "Invitation not found"}, 404
            
        trip_id, trip_car_id = result
        
        # If accepted and they're the driver, create the actual lease
        if response == 'accept':
            cur.execute("""
                SELECT tp.role, t.start_time, t.end_time, tc.id_car
                FROM trip_participants tp
                JOIN trips t ON tp.id_trip = t.id_trip
                JOIN trip_cars tc ON tp.id_trip_car = tc.id_trip_car
                WHERE tp.id_participant = %s
            """, (participant_id,))
            
            role, start_time, end_time, car_id = cur.fetchone()
            
            if role == 'driver':
                # Get driver ID
                cur.execute("SELECT id_driver FROM driver WHERE email = %s", (user_email,))
                driver_id = cur.fetchone()[0]
                
                # Create lease for this car
                cur.execute("""
                    INSERT INTO lease (id_car, id_driver, start_of_lease, end_of_lease, 
                                     status, id_trip)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id_lease
                """, (car_id, driver_id, start_time, end_time, True, trip_id))
                
                lease_id = cur.fetchone()[0]
                
                # Update trip_cars with the lease ID
                cur.execute("""
                    UPDATE trip_cars SET id_lease = %s WHERE id_trip_car = %s
                """, (lease_id, trip_car_id))
                
                # Update car status
                cur.execute("UPDATE car SET status = 'leased' WHERE id_car = %s", (car_id,))
        
        conn.commit()
        return {"status": True, "msg": f"Invitation {response}ed successfully"}, 200
        
    except Exception as e:
        conn.rollback()
        return {"status": False, "msg": f"Error responding to invitation: {e}"}, 500
    finally:
        conn.close()


@app.route('/get_my_trips', methods=['GET'])
@jwt_required()
def get_my_trips():
    claims = get_jwt()
    user_email = claims.get('sub', None)
    
    conn, cur = connect_to_db()
    
    try:
        cur.execute("SELECT id_driver FROM driver WHERE email = %s", (user_email,))
        user_id = cur.fetchone()[0]
        
        # Get trips where user is creator or participant
        cur.execute("""
            SELECT DISTINCT t.id_trip, t.trip_name, t.destination_name, t.start_time, 
                   t.end_time, t.status, t.creator_id = %s as is_creator
            FROM trips t
            LEFT JOIN trip_participants tp ON t.id_trip = tp.id_trip
            WHERE t.creator_id = %s OR (tp.id_driver = %s AND tp.invitation_status = 'accepted')
            ORDER BY t.start_time DESC
        """, (user_id, user_id, user_id))
        
        trips = []
        for row in cur.fetchall():
            trip_id = row[0]
            
            # Get trip details including cars and participants
            cur.execute("""
                SELECT c.name, tp.role, d.name, tp.invitation_status
                FROM trip_cars tc
                JOIN car c ON tc.id_car = c.id_car
                LEFT JOIN trip_participants tp ON tc.id_trip_car = tp.id_trip_car
                LEFT JOIN driver d ON tp.id_driver = d.id_driver
                WHERE tc.id_trip = %s
                ORDER BY c.name, tp.role DESC
            """, (trip_id,))
            
            trip_details = cur.fetchall()
            
            trips.append({
                "trip_id": row[0],
                "trip_name": row[1],
                "destination": row[2],
                "start_time": row[3].isoformat(),
                "end_time": row[4].isoformat(),
                "status": row[5],
                "is_creator": row[6],
                "cars_and_participants": trip_details
            })
        
        return {"trips": trips}, 200
        
    except Exception as e:
        return {"status": False, "msg": f"Error fetching trips: {e}"}, 500
    finally:
        conn.close()


@app.route('/cancel_trip', methods=['POST'])
@jwt_required()
def cancel_trip():
    claims = get_jwt()
    user_email = claims.get('sub', None)
    role = claims.get('role', None)
    
    data = request.get_json()
    trip_id = data['trip_id']
    
    conn, cur = connect_to_db()
    
    try:
        # Check if user can cancel (creator or admin/manager)
        cur.execute("SELECT creator_id FROM trips WHERE id_trip = %s", (trip_id,))
        result = cur.fetchone()
        if not result:
            return {"status": False, "msg": "Trip not found"}, 404
            
        creator_id = result[0]
        
        cur.execute("SELECT id_driver FROM driver WHERE email = %s", (user_email,))
        user_id = cur.fetchone()[0]
        
        if creator_id != user_id and role not in ['admin', 'manager']:
            return {"status": False, "msg": "Unauthorized"}, 403
        
        # Cancel all related leases
        cur.execute("""
            UPDATE lease SET status = FALSE 
            WHERE id_trip = %s
        """, (trip_id,))
        
        # Free up cars
        cur.execute("""
            UPDATE car SET status = 'stand_by' 
            WHERE id_car IN (
                SELECT tc.id_car FROM trip_cars tc WHERE tc.id_trip = %s
            )
        """, (trip_id,))
        
        # Update trip status
        cur.execute("""
            UPDATE trips SET status = 'cancelled' WHERE id_trip = %s
        """, (trip_id,))
        
        # Notify all participants
        cur.execute("""
            SELECT d.email, t.trip_name 
            FROM trip_participants tp
            JOIN driver d ON tp.id_driver = d.id_driver  
            JOIN trips t ON tp.id_trip = t.id_trip
            WHERE tp.id_trip = %s AND tp.invitation_status = 'accepted'
        """, (trip_id,))
        
        for participant_email, trip_name in cur.fetchall():
            if participant_email != user_email:
                create_notification(
                    conn, cur, participant_email, None, 'user',
                    f"Výlet zrušený: {trip_name}",
                    f"Výlet '{trip_name}' bol zrušený organizátorom.",
                    is_system_wide=False
                )
        
        conn.commit()
        return {"status": True, "msg": "Trip cancelled successfully"}, 200
        
    except Exception as e:
        conn.rollback()
        return {"status": False, "msg": f"Error cancelling trip: {e}"}, 500
    finally:
        conn.close()


@app.route('/get_trip_details', methods=['POST'])
@jwt_required()
def get_trip_details():
    """Get detailed information about a specific trip."""
    claims = get_jwt()
    user_email = claims.get('sub', None)
    
    data = request.get_json()
    trip_id = data.get('trip_id')
    
    if not trip_id:
        return {"status": False, "msg": "Missing trip_id"}, 400
    
    conn, cur = connect_to_db()
    
    try:
        # Get user ID
        cur.execute("SELECT id_driver FROM driver WHERE email = %s", (user_email,))
        user_result = cur.fetchone()
        if not user_result:
            return {"status": False, "msg": "User not found"}, 404
        user_id = user_result[0]
        
        # Get trip basic info
        cur.execute("""
            SELECT t.trip_name, t.destination_name, t.destination_lat, t.destination_lon,
                   t.start_time, t.end_time, t.status, t.description, t.created_at,
                   d.name as creator_name, d.email as creator_email,
                   t.creator_id = %s as is_creator
            FROM trips t
            JOIN driver d ON t.creator_id = d.id_driver
            WHERE t.id_trip = %s
        """, (user_id, trip_id))
        
        trip_info = cur.fetchone()
        if not trip_info:
            return {"status": False, "msg": "Trip not found"}, 404
        
        # Get cars and their assignments
        cur.execute("""
            SELECT tc.id_trip_car, c.id_car, c.name as car_name, c.stk, c.location,
                   COUNT(tp.id_participant) FILTER (WHERE tp.invitation_status = 'accepted') as accepted_count,
                   COUNT(tp.id_participant) FILTER (WHERE tp.invitation_status = 'pending') as pending_count
            FROM trip_cars tc
            JOIN car c ON tc.id_car = c.id_car
            LEFT JOIN trip_participants tp ON tc.id_trip_car = tp.id_trip_car
            WHERE tc.id_trip = %s
            GROUP BY tc.id_trip_car, c.id_car, c.name, c.stk, c.location
            ORDER BY c.name
        """, (trip_id,))
        
        cars = []
        for car_row in cur.fetchall():
            trip_car_id, car_id, car_name, stk, location, accepted_count, pending_count = car_row
            
            # Get participants for this car
            cur.execute("""
                SELECT tp.id_participant, tp.role, tp.invitation_status, tp.invited_at, tp.responded_at,
                       d.name as participant_name, d.email as participant_email
                FROM trip_participants tp
                JOIN driver d ON tp.id_driver = d.id_driver
                WHERE tp.id_trip_car = %s
                ORDER BY tp.role DESC, tp.invited_at
            """, (trip_car_id,))
            
            participants = []
            for p_row in cur.fetchall():
                participants.append({
                    'id_participant': p_row[0],
                    'role': p_row[1],
                    'invitation_status': p_row[2],
                    'invited_at': p_row[3].isoformat() if p_row[3] else None,
                    'responded_at': p_row[4].isoformat() if p_row[4] else None,
                    'participant_name': p_row[5],
                    'participant_email': p_row[6]
                })
            
            cars.append({
                'id_trip_car': trip_car_id,
                'id_car': car_id,
                'car_name': car_name,
                'stk': stk,
                'location': location,
                'accepted_count': accepted_count,
                'pending_count': pending_count,
                'participants': participants
            })
        
        # Check if current user is a participant
        cur.execute("""
            SELECT tp.role, tp.invitation_status, c.name as assigned_car
            FROM trip_participants tp
            JOIN trip_cars tc ON tp.id_trip_car = tc.id_trip_car
            JOIN car c ON tc.id_car = c.id_car
            WHERE tp.id_trip = %s AND tp.id_driver = %s
        """, (trip_id, user_id))
        
        user_participation = cur.fetchone()
        user_role = None
        user_status = None
        user_car = None
        
        if user_participation:
            user_role, user_status, user_car = user_participation
        
        trip_details = {
            'trip_id': trip_id,
            'trip_name': trip_info[0],
            'destination_name': trip_info[1],
            'destination_lat': float(trip_info[2]) if trip_info[2] else None,
            'destination_lon': float(trip_info[3]) if trip_info[3] else None,
            'start_time': trip_info[4].isoformat() if trip_info[4] else None,
            'end_time': trip_info[5].isoformat() if trip_info[5] else None,
            'status': trip_info[6],
            'description': trip_info[7],
            'created_at': trip_info[8].isoformat() if trip_info[8] else None,
            'creator_name': trip_info[9],
            'creator_email': trip_info[10],
            'is_creator': trip_info[11],
            'cars': cars,
            'user_participation': {
                'role': user_role,
                'invitation_status': user_status,
                'assigned_car': user_car
            }
        }
        
        return {"status": True, "trip": trip_details}, 200
        
    except Exception as e:
        return {"status": False, "msg": f"Error getting trip details: {e}"}, 500
    finally:
        conn.close()


@app.route('/update_trip', methods=['POST'])
@jwt_required()
def update_trip():
    """Update trip details - only creator can do this."""
    claims = get_jwt()
    user_email = claims.get('sub', None)
    role = claims.get('role', None)
    
    data = request.get_json()
    trip_id = data.get('trip_id')
    
    if not trip_id:
        return {"status": False, "msg": "Missing trip_id"}, 400
    
    conn, cur = connect_to_db()
    
    try:
        # Get user ID and verify permissions
        cur.execute("SELECT id_driver FROM driver WHERE email = %s", (user_email,))
        user_result = cur.fetchone()
        if not user_result:
            return {"status": False, "msg": "User not found"}, 404
        user_id = user_result[0]
        
        # Check if user is trip creator
        cur.execute("SELECT creator_id, status FROM trips WHERE id_trip = %s", (trip_id,))
        trip_result = cur.fetchone()
        if not trip_result:
            return {"status": False, "msg": "Trip not found"}, 404
        
        creator_id, current_status = trip_result
        
        if creator_id != user_id and role not in ['manager', 'admin']:
            return {"status": False, "msg": "Only trip creator can update trip"}, 403
        
        if current_status in ['ongoing', 'completed', 'cancelled']:
            return {"status": False, "msg": f"Cannot update trip with status: {current_status}"}, 400
        
        # Build update query dynamically
        update_fields = []
        update_values = []
        
        updatable_fields = ['trip_name', 'destination_name', 'destination_lat', 
                           'destination_lon', 'start_time', 'end_time', 'description']
        
        for field in updatable_fields:
            if field in data:
                update_fields.append(f"{field} = %s")
                update_values.append(data[field])
        
        if not update_fields:
            return {"status": False, "msg": "No valid fields to update"}, 400
        
        update_values.append(trip_id)
        
        update_query = f"""
            UPDATE trips 
            SET {', '.join(update_fields)}
            WHERE id_trip = %s
        """
        
        cur.execute(update_query, update_values)
        
        # If start_time or end_time changed, update associated leases
        if 'start_time' in data or 'end_time' in data:
            new_start = data.get('start_time')
            new_end = data.get('end_time')
            
            if new_start and new_end:
                cur.execute("""
                    UPDATE lease 
                    SET start_of_lease = %s, end_of_lease = %s
                    WHERE id_trip = %s AND status = true
                """, (new_start, new_end, trip_id))
        
        # Notify all participants about the update
        cur.execute("""
            SELECT d.email, t.trip_name 
            FROM trip_participants tp
            JOIN driver d ON tp.id_driver = d.id_driver  
            JOIN trips t ON tp.id_trip = t.id_trip
            WHERE tp.id_trip = %s AND tp.invitation_status = 'accepted'
        """, (trip_id,))
        
        trip_name = None
        for participant_email, trip_name in cur.fetchall():
            if participant_email != user_email:
                create_notification(
                    conn, cur, participant_email, None, 'user',
                    f"Výlet upravený: {trip_name}",
                    f"Organizátor upravil detaily výletu '{trip_name}'. Skontrolujte aktuálne informácie.",
                    is_system_wide=False
                )
        
        conn.commit()
        return {"status": True, "msg": "Trip updated successfully"}, 200
        
    except Exception as e:
        conn.rollback()
        return {"status": False, "msg": f"Error updating trip: {e}"}, 500
    finally:
        conn.close() 


@app.route('/cancel_trip_participation', methods=['POST'])
@jwt_required()
def cancel_trip_participation():
    """Allow users to cancel their participation in a trip before it starts."""
    claims = get_jwt()
    user_email = claims.get('sub', None)
    
    data = request.get_json()
    trip_id = data.get('trip_id')
    
    if not trip_id:
        return {"status": False, "msg": "Missing trip_id"}, 400
    
    conn, cur = connect_to_db()
    
    try:
        # Get user ID
        cur.execute("SELECT id_driver FROM driver WHERE email = %s", (user_email,))
        user_result = cur.fetchone()
        if not user_result:
            return {"status": False, "msg": "User not found"}, 404
        user_id = user_result[0]
        
        # Check if user is part of this trip
        cur.execute("""
            SELECT tp.id_participant, tp.role, tp.id_trip_car, t.trip_name, t.start_time, t.creator_id,
                   c.name as car_name, d.name as creator_name, d.email as creator_email
            FROM trip_participants tp
            JOIN trips t ON tp.id_trip = t.id_trip
            JOIN trip_cars tc ON tp.id_trip_car = tc.id_trip_car
            JOIN car c ON tc.id_car = c.id_car
            JOIN driver d ON t.creator_id = d.id_driver
            WHERE tp.id_trip = %s AND tp.id_driver = %s AND tp.invitation_status = 'accepted'
        """, (trip_id, user_id))
        
        participation = cur.fetchone()
        if not participation:
            return {"status": False, "msg": "You are not an accepted participant in this trip"}, 404
        
        participant_id, role, trip_car_id, trip_name, start_time, creator_id, car_name, creator_name, creator_email = participation
        
        # Check if user is the trip creator
        if creator_id == user_id:
            return {"status": False, "msg": "Trip creator cannot cancel participation. Cancel the entire trip instead."}, 400
        
        # Check if trip has already started
        current_time = datetime.now()
        if start_time <= current_time:
            return {"status": False, "msg": "Cannot cancel participation after trip has started"}, 400
        
        # If user is a driver, we need to cancel their lease and free the car
        # Also need to handle passengers in the same car
        if role == 'driver':
            # Find and cancel the lease for this trip and car
            cur.execute("""
                SELECT id_lease FROM lease 
                WHERE id_driver = %s AND id_trip = %s AND status = true
            """, (user_id, trip_id))
            
            lease_result = cur.fetchone()
            if lease_result:
                lease_id = lease_result[0]
                
                # Cancel the lease
                cur.execute("UPDATE lease SET status = false WHERE id_lease = %s", (lease_id,))
                
                # Free up the car (set back to stand_by)
                cur.execute("""
                    UPDATE car SET status = 'stand_by' 
                    WHERE id_car = (
                        SELECT tc.id_car FROM trip_cars tc WHERE tc.id_trip_car = %s
                    )
                """, (trip_car_id,))
                
                # Clear the lease reference from trip_cars
                cur.execute("UPDATE trip_cars SET id_lease = NULL WHERE id_trip_car = %s", (trip_car_id,))
                
                # Notify all passengers in the same car that they need reassignment
                cur.execute("""
                    SELECT d.email, d.name
                    FROM trip_participants tp
                    JOIN driver d ON tp.id_driver = d.id_driver
                    WHERE tp.id_trip_car = %s AND tp.role = 'passenger' AND tp.invitation_status = 'accepted'
                """, (trip_car_id,))
                
                affected_passengers = cur.fetchall()
                
                for passenger_email, passenger_name in affected_passengers:
                    create_notification(
                        conn, cur, passenger_email, car_name, 'user',
                        f"Zmena vodiča na výlete: {trip_name}",
                        f"Váš vodič {user_email} zrušil účasť. Organizátor musí prideliť nového vodiča alebo vás presunúť do iného auta.",
                        is_system_wide=False
                    )
                    
                    passenger_topic = passenger_email.replace("@", "_")
                    message = messaging.Message(
                        notification=messaging.Notification(
                            title=f"Zmena vodiča na výlete: {trip_name}",
                            body=f"Váš vodič zrušil účasť. Čakajte na nové priradenie."
                        ),
                        topic=passenger_topic
                    )
                    send_firebase_message_safe(message)
        
        # Remove participant from trip
        cur.execute("""
            UPDATE trip_participants 
            SET invitation_status = 'declined', responded_at = NOW() 
            WHERE id_participant = %s
        """, (participant_id,))
        
        # Notify trip creator about the cancellation
        create_notification(
            conn, cur, creator_email, car_name, 'user',
            f"Účastník zrušil účasť na výlete: {trip_name}",
            f"{user_email} zrušil účasť na výlete. Auto: {car_name}, Rola: {role}",
            is_system_wide=False
        )
        
        # Send Firebase notification to creator
        creator_topic = creator_email.replace("@", "_")
        message = messaging.Message(
            notification=messaging.Notification(
                title=f"Účastník zrušil účasť na výlete: {trip_name}",
                body=f"{user_email} zrušil účasť na výlete. Auto: {car_name}"
            ),
            topic=creator_topic
        )
        send_firebase_message_safe(message)
        
        # Check if trip is still viable (has drivers for all cars)
        cur.execute("""
            SELECT tc.id_trip_car, 
                   COUNT(tp.id_participant) as driver_count
            FROM trip_cars tc
            LEFT JOIN trip_participants tp ON tc.id_trip_car = tp.id_trip_car 
                AND tp.invitation_status = 'accepted' AND tp.role = 'driver'
            WHERE tc.id_trip = %s
            GROUP BY tc.id_trip_car
            HAVING COUNT(tp.id_participant) = 0
        """, (trip_id,))
        
        cars_without_drivers = cur.fetchall()
        
        if cars_without_drivers:
            # Notify creator that some cars don't have drivers
            create_notification(
                conn, cur, creator_email, None, 'user',
                f"Upozornenie: Výlet {trip_name} nemá vodiča!",
                f"Po zrušení účasti {user_email} nemajú niektoré autá vodičov. Priraďte nových vodičov alebo zrušte výlet.",
                is_system_wide=False
            )
        
        conn.commit()
        return {"status": True, "msg": "Participation cancelled successfully"}, 200
        
    except Exception as e:
        conn.rollback()
        return {"status": False, "msg": f"Error cancelling participation: {e}"}, 500
    finally:
        conn.close()


@app.route('/return_trip_car', methods=['POST'])
@jwt_required()
def return_trip_car():
    """Handle car returns for trips - only trip creator can return cars."""
    claims = get_jwt()
    user_email = claims.get('sub', None)
    
    data = request.get_json()
    
    # Required fields for car return
    required_fields = ['trip_id', 'car_id', 'time_of_return', 'health', 'note', 'location', 
                      'damaged', 'dirty', 'int_damage', 'ext_damage', 'collision']
    
    for field in required_fields:
        if field not in data:
            return {"status": False, "msg": f"Missing required field: {field}"}, 400
    
    trip_id = data['trip_id']
    car_id = data['car_id']
    time_of_return = data['time_of_return']
    health = data['health']
    note = data['note']
    location = data['location']
    damaged = data['damaged']
    dirty = data['dirty']
    int_damage = data['int_damage']
    ext_damage = data['ext_damage']
    collision = data['collision']
    
    # Location mapping
    location_mapping = {
        "Bratislava": "BA",
        "Banská Bystrica": "BB", 
        "Kosice": "KE",
        "Private": "FF"
    }
    location_code = location_mapping.get(location, "ER")
    
    conn, cur = connect_to_db()
    
    try:
        # Get user ID
        cur.execute("SELECT id_driver FROM driver WHERE email = %s", (user_email,))
        user_result = cur.fetchone()
        if not user_result:
            return {"status": False, "msg": "User not found"}, 404
        user_id = user_result[0]
        
        # Check if user is the trip creator
        cur.execute("SELECT creator_id, trip_name FROM trips WHERE id_trip = %s", (trip_id,))
        trip_result = cur.fetchone()
        if not trip_result:
            return {"status": False, "msg": "Trip not found"}, 404
        
        creator_id, trip_name = trip_result
        if creator_id != user_id:
            return {"status": False, "msg": "Only trip creator can return cars"}, 403
        
        # Find the lease for this car in this trip
        cur.execute("""
            SELECT l.id_lease, l.id_driver, tc.id_trip_car, c.name as car_name
            FROM lease l
            JOIN trip_cars tc ON l.id_lease = tc.id_lease
            JOIN car c ON tc.id_car = c.id_car
            WHERE l.id_trip = %s AND tc.id_car = %s AND l.status = true
        """, (trip_id, car_id))
        
        lease_result = cur.fetchone()
        if not lease_result:
            return {"status": False, "msg": "No active lease found for this car in this trip"}, 404
        
        lease_id, driver_id, trip_car_id, car_name = lease_result
        
        # Update the lease with return information
        cur.execute("""
            UPDATE lease 
            SET status = false, 
                time_of_return = %s, 
                note = %s, 
                car_health_check = %s,
                dirty = %s,
                exterior_damage = %s,
                interior_damage = %s,
                collision = %s
            WHERE id_lease = %s
        """, (time_of_return, note, damaged, dirty, ext_damage, int_damage, collision, lease_id))
        
        # Update car status and location
        usage_metric = _usage_metric(car_id, conn)
        cur.execute("""
            UPDATE car 
            SET health = %s, status = 'stand_by', usage_metric = %s, location = %s 
            WHERE id_car = %s
        """, (health, usage_metric, location_code, car_id))
        
        # Get driver email for notification
        cur.execute("SELECT email FROM driver WHERE id_driver = %s", (driver_id,))
        driver_email = cur.fetchone()[0]
        
        # Notify the driver that their car was returned
        create_notification(
            conn, cur, driver_email, car_name, 'user',
            f"Auto vrátené: {trip_name}",
            f"Vaše auto {car_name} bolo vrátené organizátorom výletu.",
            is_system_wide=False
        )
        
        # Send damage notifications if needed
        if damaged:
            create_notification(
                conn, cur, None, car_name, 'manager',
                'Poškodenie auta pri výlete!',
                f"Auto {car_name} z výletu '{trip_name}' bolo vrátené s poškodením.",
                is_system_wide=False
            )
            
            message = messaging.Message(
                notification=messaging.Notification(
                    title="Poškodenie auta pri výlete!",
                    body=f"Auto {car_name} z výletu '{trip_name}' bolo vrátené s poškodením."
                ),
                topic="manager"
            )
            send_firebase_message_safe(message)
        
        conn.commit()
        return {"status": True, "msg": f"Car {car_name} returned successfully"}, 200
        
    except Exception as e:
        conn.rollback()
        return {"status": False, "msg": f"Error returning car: {e}"}, 500
    finally:
        conn.close()


@app.route('/return_all_trip_cars', methods=['POST'])
@jwt_required()
def return_all_trip_cars():
    """Return all cars for a trip at once - only trip creator can do this."""
    claims = get_jwt()
    user_email = claims.get('sub', None)
    
    data = request.get_json()
    trip_id = data.get('trip_id')
    time_of_return = data.get('time_of_return')
    global_note = data.get('note', '')
    global_health = data.get('health', 'good')
    global_location = data.get('location', 'Banská Bystrica')
    
    # Car-specific return data (optional)
    car_specific_data = data.get('car_data', {})  # {car_id: {health, note, damaged, etc.}}
    
    if not trip_id or not time_of_return:
        return {"status": False, "msg": "Missing trip_id or time_of_return"}, 400
    
    # Location mapping
    location_mapping = {
        "Bratislava": "BA",
        "Banská Bystrica": "BB",
        "Kosice": "KE", 
        "Private": "FF"
    }
    location_code = location_mapping.get(global_location, "BB")
    
    conn, cur = connect_to_db()
    
    try:
        # Get user ID and verify trip creator
        cur.execute("SELECT id_driver FROM driver WHERE email = %s", (user_email,))
        user_result = cur.fetchone()
        if not user_result:
            return {"status": False, "msg": "User not found"}, 404
        user_id = user_result[0]
        
        cur.execute("SELECT creator_id, trip_name FROM trips WHERE id_trip = %s", (trip_id,))
        trip_result = cur.fetchone()
        if not trip_result:
            return {"status": False, "msg": "Trip not found"}, 404
        
        creator_id, trip_name = trip_result
        if creator_id != user_id:
            return {"status": False, "msg": "Only trip creator can return cars"}, 403
        
        # Get all active leases for this trip
        cur.execute("""
            SELECT l.id_lease, l.id_driver, tc.id_car, c.name as car_name, d.email as driver_email
            FROM lease l
            JOIN trip_cars tc ON l.id_lease = tc.id_lease
            JOIN car c ON tc.id_car = c.id_car
            JOIN driver d ON l.id_driver = d.id_driver
            WHERE l.id_trip = %s AND l.status = true
        """, (trip_id,))
        
        active_leases = cur.fetchall()
        if not active_leases:
            return {"status": False, "msg": "No active leases found for this trip"}, 404
        
        returned_cars = []
        damaged_cars = []
        
        # Process each lease
        for lease_id, driver_id, car_id, car_name, driver_email in active_leases:
            # Get car-specific data or use global defaults
            car_data = car_specific_data.get(str(car_id), {})
            car_health = car_data.get('health', global_health)
            car_note = car_data.get('note', global_note)
            car_damaged = car_data.get('damaged', False)
            car_dirty = car_data.get('dirty', False)
            car_int_damage = car_data.get('int_damage', False)
            car_ext_damage = car_data.get('ext_damage', False)
            car_collision = car_data.get('collision', False)
            
            # Update the lease
            cur.execute("""
                UPDATE lease 
                SET status = false, 
                    time_of_return = %s, 
                    note = %s, 
                    car_health_check = %s,
                    dirty = %s,
                    exterior_damage = %s,
                    interior_damage = %s,
                    collision = %s
                WHERE id_lease = %s
            """, (time_of_return, car_note, car_damaged, car_dirty, car_ext_damage, car_int_damage, car_collision, lease_id))
            
            # Update car status
            usage_metric = _usage_metric(car_id, conn)
            cur.execute("""
                UPDATE car 
                SET health = %s, status = 'stand_by', usage_metric = %s, location = %s 
                WHERE id_car = %s
            """, (car_health, usage_metric, location_code, car_id))
            
            # Notify driver
            create_notification(
                conn, cur, driver_email, car_name, 'user',
                f"Auto vrátené: {trip_name}",
                f"Váš výlet '{trip_name}' skončil. Auto {car_name} bolo vrátené.",
                is_system_wide=False
            )
            
            returned_cars.append(car_name)
            
            if car_damaged:
                damaged_cars.append(car_name)
        
        # Update trip status to completed
        cur.execute("UPDATE trips SET status = 'completed' WHERE id_trip = %s", (trip_id,))
        
        # Send damage notifications if any cars were damaged
        if damaged_cars:
            create_notification(
                conn, cur, None, None, 'manager',
                f'Poškodenia pri výlete: {trip_name}',
                f"Nasledujúce autá boli vrátené s poškodením: {', '.join(damaged_cars)}",
                is_system_wide=False
            )
            
            message = messaging.Message(
                notification=messaging.Notification(
                    title=f"Poškodenia pri výlete: {trip_name}",
                    body=f"Autá s poškodením: {', '.join(damaged_cars)}"
                ),
                topic="manager"
            )
            send_firebase_message_safe(message)
        
        conn.commit()
        return {
            "status": True, 
            "msg": f"All cars returned successfully for trip: {trip_name}",
            "returned_cars": returned_cars,
            "damaged_cars": damaged_cars
        }, 200
        
    except Exception as e:
        conn.rollback()
        return {"status": False, "msg": f"Error returning cars: {e}"}, 500
    finally:
        conn.close()


# Modified existing return_car endpoint to handle trips
@app.route('/return_car_enhanced', methods=['POST'])
@jwt_required()
def return_car_enhanced():
    """Enhanced car return that handles both regular leases and trips."""
    claims = get_jwt()
    user_email = claims.get('sub', None)
    
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data'}), 501
    
    lease_id = data.get("id_lease")
    if not lease_id:
        return {"status": False, "msg": "Missing lease_id"}, 400
    
    conn, cur = connect_to_db()
    
    try:
        # Check if this lease is part of a trip
        cur.execute("""
            SELECT l.id_trip, t.trip_name, t.creator_id, d.email as creator_email
            FROM lease l
            LEFT JOIN trips t ON l.id_trip = t.id_trip
            LEFT JOIN driver d ON t.creator_id = d.id_driver
            WHERE l.id_lease = %s
        """, (lease_id,))
        
        lease_info = cur.fetchone()
        if not lease_info:
            return {"status": False, "msg": "Lease not found"}, 404
        
        trip_id, trip_name, creator_id, creator_email = lease_info
        
        if trip_id:
            # This is a trip lease
            cur.execute("SELECT id_driver FROM driver WHERE email = %s", (user_email,))
            user_id = cur.fetchone()[0]
            
            if creator_id != user_id:
                return {
                    "status": False, 
                    "msg": "This car is part of a trip. Only the trip creator can return cars.",
                    "trip_id": trip_id,
                    "trip_name": trip_name,
                    "creator_email": creator_email
                }, 403
            
            # If user is trip creator, redirect to trip car return
            return return_trip_car()
        else:
            # Regular lease - use existing logic
            # Call the existing return_car function logic here
            # (Copy the existing return_car code)
            pass
    
    except Exception as e:
        return {"status": False, "msg": f"Error processing car return: {e}"}, 500
    finally:
        conn.close()


@app.route('/reassign_trip_driver', methods=['POST'])
@jwt_required()
def reassign_trip_driver():
    """Allow trip creator to reassign driver role to another participant."""
    claims = get_jwt()
    user_email = claims.get('sub', None)
    role = claims.get('role', None)
    
    data = request.get_json()
    trip_id = data.get('trip_id')
    car_id = data.get('car_id')  # Which car needs a new driver
    new_driver_email = data.get('new_driver_email')  # Email of new driver
    
    if not all([trip_id, car_id, new_driver_email]):
        return {"status": False, "msg": "Missing required parameters"}, 400
    
    conn, cur = connect_to_db()
    
    try:
        # Verify user is trip creator
        cur.execute("SELECT creator_id FROM trips WHERE id_trip = %s", (trip_id,))
        trip_result = cur.fetchone()
        if not trip_result:
            return {"status": False, "msg": "Trip not found"}, 404
        
        creator_id = trip_result[0]
        
        cur.execute("SELECT id_driver FROM driver WHERE email = %s", (user_email,))
        user_id = cur.fetchone()[0]
        
        if creator_id != user_id and role not in ['admin', 'manager']:
            return {"status": False, "msg": "Only trip creator can reassign drivers"}, 403
        
        # Get trip_car_id for this car in this trip
        cur.execute("SELECT id_trip_car FROM trip_cars WHERE id_trip = %s AND id_car = %s", (trip_id, car_id))
        trip_car_result = cur.fetchone()
        if not trip_car_result:
            return {"status": False, "msg": "Car not found in this trip"}, 404
        
        trip_car_id = trip_car_result[0]
        
        # Check if new driver is already a participant in this car
        cur.execute("""
            SELECT tp.id_participant, tp.role, tp.invitation_status, d.id_driver
            FROM trip_participants tp
            JOIN driver d ON tp.id_driver = d.id_driver
            WHERE tp.id_trip = %s AND tp.id_trip_car = %s AND d.email = %s
        """, (trip_id, trip_car_id, new_driver_email))
        
        new_driver_result = cur.fetchone()
        if not new_driver_result:
            return {"status": False, "msg": "Selected user is not a participant in this car"}, 404
        
        participant_id, current_role, invitation_status, new_driver_id = new_driver_result
        
        if invitation_status != 'accepted':
            return {"status": False, "msg": "Selected user has not accepted the trip invitation"}, 400
        
        if current_role == 'driver':
            return {"status": False, "msg": "Selected user is already the driver"}, 400
        
        # Check if there's currently a driver for this car
        cur.execute("""
            SELECT tp.id_participant, d.id_driver
            FROM trip_participants tp
            JOIN driver d ON tp.id_driver = d.id_driver
            WHERE tp.id_trip = %s AND tp.id_trip_car = %s AND tp.role = 'driver' AND tp.invitation_status = 'accepted'
        """, (trip_id, trip_car_id))
        
        current_driver_result = cur.fetchone()
        
        # Get trip timing for lease creation
        cur.execute("SELECT start_time, end_time, trip_name FROM trips WHERE id_trip = %s", (trip_id,))
        start_time, end_time, trip_name = cur.fetchone()
        
        if current_driver_result:
            # Demote current driver to passenger
            current_driver_participant_id, current_driver_id = current_driver_result
            
            cur.execute("""
                UPDATE trip_participants 
                SET role = 'passenger' 
                WHERE id_participant = %s
            """, (current_driver_participant_id,))
            
            # Cancel current driver's lease
            cur.execute("""
                UPDATE lease 
                SET status = false 
                WHERE id_driver = %s AND id_trip = %s AND status = true
            """, (current_driver_id, trip_id))
            
            # Clear lease reference from trip_cars
            cur.execute("UPDATE trip_cars SET id_lease = NULL WHERE id_trip_car = %s", (trip_car_id,))
        
        # Promote new user to driver
        cur.execute("""
            UPDATE trip_participants 
            SET role = 'driver' 
            WHERE id_participant = %s
        """, (participant_id,))
        
        # Create new lease for new driver
        cur.execute("""
            INSERT INTO lease (id_car, id_driver, start_of_lease, end_of_lease, status, id_trip)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id_lease
        """, (car_id, new_driver_id, start_time, end_time, True, trip_id))
        
        new_lease_id = cur.fetchone()[0]
        
        # Update trip_cars with new lease
        cur.execute("UPDATE trip_cars SET id_lease = %s WHERE id_trip_car = %s", (new_lease_id, trip_car_id))
        
        # Update car status
        cur.execute("UPDATE car SET status = 'leased' WHERE id_car = %s", (car_id,))
        
        # Notify new driver
        create_notification(
            conn, cur, new_driver_email, None, 'user',
            f"Nová rola na výlete: {trip_name}",
            f"Boli ste vymenovaní za vodiča na výlete '{trip_name}'.",
            is_system_wide=False
        )
        
        # Send Firebase notification
        driver_topic = new_driver_email.replace("@", "_")
        message = messaging.Message(
            notification=messaging.Notification(
                title=f"Nová rola na výlete: {trip_name}",
                body=f"Boli ste vymenovaní za vodiča na výlete '{trip_name}'."
            ),
            topic=driver_topic
        )
        send_firebase_message_safe(message)
        
        conn.commit()
        return {"status": True, "msg": "Driver reassigned successfully"}, 200
        
    except Exception as e:
        conn.rollback()
        return {"status": False, "msg": f"Error reassigning driver: {e}"}, 500
    finally:
        conn.close()


@app.route('/manage_trip_participants', methods=['POST'])
@jwt_required()
def manage_trip_participants():
    """Add, remove, or modify participants in a trip."""
    claims = get_jwt()
    user_email = claims.get('sub', None)
    role = claims.get('role', None)
    
    data = request.get_json()
    trip_id = data.get('trip_id')
    action = data.get('action')  # 'add', 'remove', 'change_car'
    participant_email = data.get('participant_email')
    car_id = data.get('car_id')
    participant_role = data.get('role', 'passenger')  # 'driver' or 'passenger'
    
    if not all([trip_id, action, participant_email]):
        return {"status": False, "msg": "Missing required parameters"}, 400
    
    if action not in ['add', 'remove', 'change_car']:
        return {"status": False, "msg": "Invalid action"}, 400
    
    conn, cur = connect_to_db()
    
    try:
        # Verify user is trip creator
        cur.execute("SELECT creator_id, trip_name, status FROM trips WHERE id_trip = %s", (trip_id,))
        trip_result = cur.fetchone()
        if not trip_result:
            return {"status": False, "msg": "Trip not found"}, 404
        
        creator_id, trip_name, trip_status = trip_result
        
        cur.execute("SELECT id_driver FROM driver WHERE email = %s", (user_email,))
        user_id = cur.fetchone()[0]
        
        if creator_id != user_id and role not in ['admin', 'manager']:
            return {"status": False, "msg": "Only trip creator can manage participants"}, 403
        
        if trip_status != 'scheduled':
            return {"status": False, "msg": "Cannot modify participants after trip has started"}, 400
        
        # Get participant ID if they exist
        cur.execute("SELECT id_driver FROM driver WHERE email = %s", (participant_email,))
        participant_result = cur.fetchone()
        if not participant_result:
            return {"status": False, "msg": "Participant not found"}, 404
        
        participant_id = participant_result[0]
        
        if action == 'add':
            if not car_id:
                return {"status": False, "msg": "car_id required for adding participants"}, 400
            
            # Check if participant already in trip
            cur.execute("""
                SELECT id_participant FROM trip_participants 
                WHERE id_trip = %s AND id_driver = %s
            """, (trip_id, participant_id))
            
            if cur.fetchone():
                return {"status": False, "msg": "Participant already in trip"}, 400
            
            # Get trip_car_id
            cur.execute("SELECT id_trip_car FROM trip_cars WHERE id_trip = %s AND id_car = %s", (trip_id, car_id))
            trip_car_result = cur.fetchone()
            if not trip_car_result:
                return {"status": False, "msg": "Car not found in trip"}, 404
            
            trip_car_id = trip_car_result[0]
            
            # If adding as driver, check if car already has a driver
            if participant_role == 'driver':
                cur.execute("""
                    SELECT COUNT(*) FROM trip_participants 
                    WHERE id_trip_car = %s AND role = 'driver' AND invitation_status = 'accepted'
                """, (trip_car_id,))
                
                driver_count = cur.fetchone()[0]
                if driver_count > 0:
                    return {"status": False, "msg": "Car already has a driver"}, 400
            
            # Add participant
            cur.execute("""
                INSERT INTO trip_participants (id_trip, id_trip_car, id_driver, role, invitation_status)
                VALUES (%s, %s, %s, %s, 'pending')
                RETURNING id_participant
            """, (trip_id, trip_car_id, participant_id, participant_role))
            
            new_participant_id = cur.fetchone()[0]
            
            # Send invitation notification
            create_notification(
                conn, cur, participant_email, None, 'user',
                f"Pozvánka na výlet: {trip_name}",
                f"Boli ste pozvaní na výlet '{trip_name}' ako {participant_role}.",
                is_system_wide=False
            )
            
            message_body = f"Boli ste pozvaní na výlet '{trip_name}' ako {participant_role}."
            participant_topic = participant_email.replace("@", "_")
            message = messaging.Message(
                notification=messaging.Notification(
                    title=f"Pozvánka na výlet: {trip_name}",
                    body=message_body
                ),
                topic=participant_topic
            )
            send_firebase_message_safe(message)
            
            conn.commit()
            return {"status": True, "msg": "Participant added successfully", "participant_id": new_participant_id}, 200
        
        elif action == 'remove':
            # Get participant info
            cur.execute("""
                SELECT tp.id_participant, tp.role, tp.id_trip_car, tp.invitation_status
                FROM trip_participants tp
                WHERE tp.id_trip = %s AND tp.id_driver = %s
            """, (trip_id, participant_id))
            
            participant_info = cur.fetchone()
            if not participant_info:
                return {"status": False, "msg": "Participant not found in trip"}, 404
            
            participant_db_id, current_role, trip_car_id, invitation_status = participant_info
            
            # If removing a driver, cancel their lease and free the car
            if current_role == 'driver' and invitation_status == 'accepted':
                cur.execute("""
                    UPDATE lease 
                    SET status = false 
                    WHERE id_driver = %s AND id_trip = %s AND status = true
                """, (participant_id, trip_id))
                
                cur.execute("UPDATE trip_cars SET id_lease = NULL WHERE id_trip_car = %s", (trip_car_id,))
                
                # Get car info for notification
                cur.execute("SELECT id_car FROM trip_cars WHERE id_trip_car = %s", (trip_car_id,))
                car_id_result = cur.fetchone()[0]
                cur.execute("UPDATE car SET status = 'stand_by' WHERE id_car = %s", (car_id_result,))
            
            # Remove participant
            cur.execute("DELETE FROM trip_participants WHERE id_participant = %s", (participant_db_id,))
            
            # Notify removed participant
            create_notification(
                conn, cur, participant_email, None, 'user',
                f"Odstránenie z výletu: {trip_name}",
                f"Boli ste odstránení z výletu '{trip_name}'.",
                is_system_wide=False
            )
            
            conn.commit()
            return {"status": True, "msg": "Participant removed successfully"}, 200
        
        elif action == 'change_car':
            if not car_id:
                return {"status": False, "msg": "car_id required for changing cars"}, 400
            
            # Get new trip_car_id
            cur.execute("SELECT id_trip_car FROM trip_cars WHERE id_trip = %s AND id_car = %s", (trip_id, car_id))
            new_trip_car_result = cur.fetchone()
            if not new_trip_car_result:
                return {"status": False, "msg": "Target car not found in trip"}, 404
            
            new_trip_car_id = new_trip_car_result[0]
            
            # Get current participant info
            cur.execute("""
                SELECT tp.id_participant, tp.role, tp.id_trip_car
                FROM trip_participants tp
                WHERE tp.id_trip = %s AND tp.id_driver = %s
            """, (trip_id, participant_id))
            
            participant_info = cur.fetchone()
            if not participant_info:
                return {"status": False, "msg": "Participant not found in trip"}, 404
            
            participant_db_id, current_role, old_trip_car_id = participant_info
            
            # If changing car for a driver, need to handle lease transfer
            if current_role == 'driver':
                # Check if target car already has a driver
                cur.execute("""
                    SELECT COUNT(*) FROM trip_participants 
                    WHERE id_trip_car = %s AND role = 'driver' AND invitation_status = 'accepted'
                """, (new_trip_car_id,))
                
                target_car_driver_count = cur.fetchone()[0]
                if target_car_driver_count > 0:
                    return {"status": False, "msg": "Target car already has a driver"}, 400
                
                # Cancel old lease and create new one
                cur.execute("""
                    UPDATE lease 
                    SET status = false 
                    WHERE id_driver = %s AND id_trip = %s AND status = true
                """, (participant_id, trip_id))
                
                # Get trip timing and new car info
                cur.execute("SELECT start_time, end_time FROM trips WHERE id_trip = %s", (trip_id,))
                start_time, end_time = cur.fetchone()
                
                # Create new lease for new car
                cur.execute("""
                    INSERT INTO lease (id_car, id_driver, start_of_lease, end_of_lease, status, id_trip)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id_lease
                """, (car_id, participant_id, start_time, end_time, True, trip_id))
                
                new_lease_id = cur.fetchone()[0]
                
                # Update trip_cars
                cur.execute("UPDATE trip_cars SET id_lease = NULL WHERE id_trip_car = %s", (old_trip_car_id,))
                cur.execute("UPDATE trip_cars SET id_lease = %s WHERE id_trip_car = %s", (new_lease_id, new_trip_car_id))
                
                # Update car statuses
                cur.execute("SELECT id_car FROM trip_cars WHERE id_trip_car = %s", (old_trip_car_id,))
                old_car_id = cur.fetchone()[0]
                cur.execute("UPDATE car SET status = 'stand_by' WHERE id_car = %s", (old_car_id,))
                cur.execute("UPDATE car SET status = 'leased' WHERE id_car = %s", (car_id,))
            
            # Update participant's car assignment
            cur.execute("""
                UPDATE trip_participants 
                SET id_trip_car = %s 
                WHERE id_participant = %s
            """, (new_trip_car_id, participant_db_id))
            
            conn.commit()
            return {"status": True, "msg": "Participant moved to new car successfully"}, 200
        
    except Exception as e:
        conn.rollback()
        return {"status": False, "msg": f"Error managing participants: {e}"}, 500
    finally:
        conn.close()


@app.route('/create_trip_enhanced', methods=['POST'])
@jwt_required()
def create_trip_enhanced():
    """Enhanced trip creation with explicit driver selection."""
    claims = get_jwt()
    creator_email = claims.get('sub', None)
    role = claims.get('role', None)
    
    data = request.get_json()
    
    try:
        trip_name = data['trip_name']
        destination_name = data['destination_name']
        start_time = data['start_time']
        end_time = data['end_time']
        selected_cars = data['cars']  # List of car IDs
        car_assignments = data['car_assignments']  # Dict: {car_id: {driver: email, passengers: [emails]}}
        description = data.get('description', '')
        destination_lat = data.get('destination_lat')
        destination_lon = data.get('destination_lon')
    except KeyError as e:
        return {"status": False, "msg": f"Missing required field: {e}"}, 400
    
    conn, cur = connect_to_db()
    
    try:
        # Get creator ID
        cur.execute("SELECT id_driver FROM driver WHERE email = %s", (creator_email,))
        creator_id = cur.fetchone()[0]
        
        # Create the trip
        cur.execute("""
            INSERT INTO trips (trip_name, creator_id, destination_name, destination_lat, 
                             destination_lon, start_time, end_time, description)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id_trip
        """, (trip_name, creator_id, destination_name, destination_lat, 
              destination_lon, start_time, end_time, description))
        
        trip_id = cur.fetchone()[0]
        
        # Add cars and participants with explicit driver assignment
        for car_id in selected_cars:
            cur.execute("""
                INSERT INTO trip_cars (id_trip, id_car)
                VALUES (%s, %s)
                RETURNING id_trip_car
            """, (trip_id, car_id))
            
            trip_car_id = cur.fetchone()[0]
            
            if str(car_id) in car_assignments:
                car_assignment = car_assignments[str(car_id)]
                driver_email = car_assignment.get('driver')
                passengers = car_assignment.get('passengers', [])
                
                # Add driver first
                if driver_email:
                    cur.execute("SELECT id_driver FROM driver WHERE email = %s", (driver_email,))
                    driver_result = cur.fetchone()
                    if driver_result:
                        driver_id = driver_result[0]
                        
                        cur.execute("""
                            INSERT INTO trip_participants (id_trip, id_trip_car, id_driver, role)
                            VALUES (%s, %s, %s, %s)
                        """, (trip_id, trip_car_id, driver_id, 'driver'))
                        
                        # Send notification to driver
                        if driver_email != creator_email:
                            create_notification(
                                conn, cur, driver_email, None, 'user',
                                f"Pozvánka na výlet: {trip_name} (Vodič)",
                                f"Boli ste pozvaní ako vodič na výlet do {destination_name}.",
                                is_system_wide=False
                            )
                
                # Add passengers
                for passenger_email in passengers:
                    if passenger_email != driver_email:  # Don't add driver as passenger too
                        cur.execute("SELECT id_driver FROM driver WHERE email = %s", (passenger_email,))
                        passenger_result = cur.fetchone()
                        if passenger_result:
                            passenger_id = passenger_result[0]
                            
                            cur.execute("""
                                INSERT INTO trip_participants (id_trip, id_trip_car, id_driver, role)
                                VALUES (%s, %s, %s, %s)
                            """, (trip_id, trip_car_id, passenger_id, 'passenger'))
                            
                            # Send notification to passenger
                            if passenger_email != creator_email:
                                create_notification(
                                    conn, cur, passenger_email, None, 'user',
                                    f"Pozvánka na výlet: {trip_name} (Spolujazdec)",
                                    f"Boli ste pozvaní ako spolujazdec na výlet do {destination_name}.",
                                    is_system_wide=False
                                )
        
        conn.commit()
        return {"status": True, "trip_id": trip_id, "msg": "Trip created successfully"}, 200
        
    except Exception as e:
        conn.rollback()
        return {"status": False, "msg": f"Error creating trip: {e}"}, 500
    finally:
        conn.close() 