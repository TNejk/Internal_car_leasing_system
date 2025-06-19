###########################

# This file handles late returns and decommissioned cars, also sends notifications

###########################

from datetime import datetime, timedelta
from firebase_admin import messaging
import psycopg2
import firebase_admin
from firebase_admin import credentials
import os
import time
import pytz
from typing import Optional, List, Tuple

# Database configuration
db_host = os.getenv('DB_HOST')
db_port = os.getenv('DB_PORT')
db_user = os.getenv('POSTGRES_USER')
db_pass = os.getenv('POSTGRES_PASS')
db_name = os.getenv('POSTGRES_DB')



def create_notification(conn, cur, email=None, car_name=None, target_role=None, title=None, message=None, is_system_wide=False):
    """
    Create a notification in the database.
    
    Args:
        conn: Database connection
        cur: Database cursor
        email: User email (optional for system notifications)
        car_name: Car name (optional for system notifications)
        target_role: Target role ('user', 'manager', 'admin', 'system')
        title: Notification title
        message: Notification message
        is_system_wide: Boolean indicating if this is a system-wide notification
    """
    try:
        id_driver = None
        id_car = None
        
        # For system-wide notifications, we don't need specific user/car associations
        if not is_system_wide:
            if not email or not isinstance(email, str):
                print(f"[NOTIF ERROR] Email required for non-system notifications")
                return False
                
            cur.execute("SELECT id_driver FROM driver WHERE email = %s", (email,))
            res = cur.fetchone()
            if not res:
                print(f"[NOTIF ERROR] Driver not found for email: {email}")
                return False
            id_driver = res[0]

            if car_name and isinstance(car_name, str):
                cur.execute("SELECT id_car FROM car WHERE name = %s", (car_name,))
                res = cur.fetchone()
                if res:
                    id_car = res[0]

        # Insert notification
        cur.execute("""
            INSERT INTO notifications (id_driver, id_car, target_role, title, message, is_system_wide)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id_notification
        """, (id_driver, id_car, target_role, title, message, is_system_wide))

        notification_id = cur.fetchone()[0]

        # If it's a system-wide notification, create read status entries for all users
        if is_system_wide:
            cur.execute("SELECT id_driver FROM driver WHERE is_deleted = FALSE")
            all_drivers = cur.fetchall()
            
            for (driver_id,) in all_drivers:
                cur.execute("""
                    INSERT INTO system_notification_read_status (id_notification, id_driver, is_read)
                    VALUES (%s, %s, %s)
                """, (notification_id, driver_id, False))

        conn.commit()
        print(f"[NOTIF] Notification created - Role: {target_role}, Driver: {email or 'System'}, Car: {car_name or 'N/A'}")
        return True

    except Exception as e:
        conn.rollback()
        print(f"[NOTIF EXCEPTION] {e}")
        return False



# Firebase initialization
try:
    cred = credentials.Certificate("icls-56e37-firebase-adminsdk-2d4e2-be93ca6a35.json")
    firebase_admin.initialize_app(cred)
    print("Firebase initialized successfully")
except Exception as e:
    print(f"ERROR: Failed to initialize Firebase: {e}")
    raise

class CarLeaseNotificator:
    def __init__(self):
        self.bratislava_tz = pytz.timezone('Europe/Bratislava')
        
    def get_database_connection(self) -> Optional[psycopg2.extensions.connection]:
        """Establish database connection with error handling."""
        try:
            connection = psycopg2.connect(
                dbname=db_name, 
                user=db_user, 
                host=db_host, 
                port=db_port, 
                password=db_pass
            )
            return connection
        except psycopg2.Error as e:
            print(f"ERROR: Database connection failed: {e}")
            return None
    
    def get_sk_date(self) -> datetime:
        """Get current time in Bratislava timezone."""
        dt_obj = datetime.now()
        utc_time = dt_obj.replace(tzinfo=pytz.utc) if dt_obj.tzinfo is None else dt_obj.astimezone(pytz.utc)
        bratislava_time = utc_time.astimezone(self.bratislava_tz)
        return bratislava_time
    
    def send_firebase_message(self, message: messaging.Message) -> bool:
        """Send Firebase message with error handling."""
        try:
            messaging.send(message)
            return True
        except Exception as e:
            print(f"ERROR: Failed to send Firebase message: {e}")
            return False
    
    def handle_decommissioned_cars(self, cursor: psycopg2.extensions.cursor, current_time: datetime) -> None:
        """Handle reactivation of decommissioned cars."""
        try:
            decom_cars_query = """
            SELECT car_name, email, time_to 
            FROM decommissioned_cars 
            WHERE status = TRUE AND time_to < %s 
            """
            cursor.execute(decom_cars_query, (current_time,))
            activable_cars = cursor.fetchall()
            
            for car_name, email, time_to in activable_cars:
                try:
                    # Update car status to stand_by
                    cursor.execute("UPDATE car SET status = 'stand_by' WHERE name = %s", (car_name,))
                    
                    # Update decommissioned_cars status to false
                    cursor.execute("UPDATE decommissioned_cars SET status = FALSE WHERE car_name = %s", (car_name,))
                    
                    # Send notification
                    message = messaging.Message(
                        notification=messaging.Notification(
                            title=f"Auto {car_name} je k dispozíci!",
                            body="Je možné znova auto rezervovať v aplikácií. :D"
                        ),
                        topic="system"
                    )
                    
                    # Create system-wide notification
                    create_notification(
                        cursor.connection, cursor,
                        email=None,
                        car_name=car_name,
                        target_role='system',
                        title=f"Auto {car_name} je k dispozíci!",
                        message="Je možné znova auto rezervovať v aplikácií.",
                        is_system_wide=True
                    )
                    
                    if self.send_firebase_message(message):
                        print(f"INFO: Reactivated car: {car_name}")
                    else:
                        print(f"WARNING: Failed to send reactivation notification for car: {car_name}")
                        
                except psycopg2.Error as e:
                    print(f"ERROR: Database error while reactivating car {car_name}: {e}")
                    raise
                    
        except psycopg2.Error as e:
            print(f"ERROR: Error handling decommissioned cars: {e}")
            raise
    
    def handle_late_returns(self, cursor: psycopg2.extensions.cursor, current_time: datetime) -> None:
        """Handle late car returns and potential lease cancellations."""
        try:
            # Find late returns
            lease_query = """
                SELECT id_driver, id_car, start_of_lease, end_of_lease, id_lease
                FROM lease
                WHERE end_of_lease < %s AND status = true AND under_review IS NOT true;
            """
            
            cursor.execute(lease_query, (current_time,))
            active_leases = cursor.fetchall()
            
            if not active_leases:
                return
                
            print(f"INFO: Processing {len(active_leases)} late returns")
            
            for id_driver, id_car, start_of_lease, end_of_lease, id_lease in active_leases:
                try:
                    # Get driver email
                    cursor.execute("SELECT email FROM driver WHERE id_driver = %s", (id_driver,))
                    email_result = cursor.fetchone()
                    if not email_result:
                        print(f"WARNING: No email found for driver ID: {id_driver}")
                        continue
                    
                    driver_email = email_result[0]
                    
                    # Get car name
                    cursor.execute("SELECT name FROM car WHERE id_car = %s", (id_car,))
                    car_result = cursor.fetchone()
                    if not car_result:
                        print(f"WARNING: No car found for car ID: {id_car}")
                        continue
                        
                    car_name = car_result[0]
                    
                    # Send notification to driver (personal notification)
                    create_notification(
                        cursor.connection, cursor,
                        email=driver_email,
                        car_name=car_name,
                        target_role='user',
                        title="Prekročenie limitu na odovzdanie auta",
                        message="Skončil sa limit na vrátenie auta, prosím odovzdajte auto v aplikácií!",
                        is_system_wide=False
                    )
                    
                    # Send notification to managers (system-wide for managers)
                    create_notification(
                        cursor.connection, cursor,
                        email=None,
                        car_name=car_name,
                        target_role='manager',
                        title="Neskoré odovzdanie auta!",
                        message=f"Zamestnanec {driver_email} nestihol odovzdať auto: {car_name}.",
                        is_system_wide=True
                    )
                    
                    # Send Firebase notifications
                    driver_topic = driver_email.replace("@", "_")
                    driver_message = messaging.Message(
                        notification=messaging.Notification(
                            title="Prekročenie limitu na odovzdanie auta",
                            body="Skončil sa limit na vrátenie auta, prosím odovzdajte auto v aplikácií!"
                        ),
                        topic=driver_topic
                    )
                    
                    manager_message = messaging.Message(
                        notification=messaging.Notification(
                            title="Neskoré odovzdanie auta!",
                            body=f"Zamestnanec {driver_email} nestihol odovzdať auto: {car_name}."
                        ),
                        topic="late_returns"
                    )
                    
                    self.send_firebase_message(driver_message)
                    self.send_firebase_message(manager_message)
                    
                    print(f"INFO: Late return notification sent to {driver_email} for car {car_name}")
                    
                    # Check for upcoming lease to cancel
                    self.handle_upcoming_lease_cancellation(cursor, current_time, id_car, car_name)
                    
                    # Mark lease as under review
                    cursor.execute(
                        "UPDATE lease SET under_review = true WHERE id_lease = %s AND status = true",
                        (id_lease,)
                    )
                    
                except Exception as e:
                    print(f"ERROR: Error processing late return for lease {id_lease}: {e}")
                    continue
                    
        except psycopg2.Error as e:
            print(f"ERROR: Error handling late returns: {e}")
            raise
    
    def handle_upcoming_lease_cancellation(self, cursor: psycopg2.extensions.cursor, 
                                         current_time: datetime, car_id: int, car_name: str) -> None:
        """Handle cancellation of upcoming leases if current lease is late."""
        try:
            # Find next lease for the same car
            next_lease_query = """
                SELECT l.id_driver, l.start_of_lease, l.id_lease, d.email
                FROM lease l
                JOIN driver d ON l.id_driver = d.id_driver
                WHERE l.id_car = %s AND l.start_of_lease >= %s AND l.status = true
                ORDER BY l.start_of_lease ASC
                LIMIT 1;
            """
            cursor.execute(next_lease_query, (car_id, current_time))
            next_lease = cursor.fetchone()
            
            if not next_lease:
                print(f"DEBUG: No upcoming lease found for car {car_name}")
                return
                
            next_driver_id, upcoming_start, next_lease_id, next_driver_email = next_lease
            time_difference = upcoming_start - current_time
            
            # Cancel if lease starts within 30 minutes
            if time_difference <= timedelta(minutes=30):
                # Cancel the lease
                cursor.execute(
                    "UPDATE lease SET status = false WHERE id_lease = %s AND status = true",
                    (next_lease_id,)
                )
                
                # Send cancellation notification
                cancel_topic = next_driver_email.replace("@", "_")
                cancel_notification = messaging.Message(
                    notification=messaging.Notification(
                        title="Rezervácia zrušená",
                        body="Vaša rezervácia na auto bola zrušená, pretože predchádzajúci prenájom neskončil načas."
                    ),
                    topic=cancel_topic
                )
                
                if self.send_firebase_message(cancel_notification):
                    print(f"INFO: Upcoming lease cancelled for {next_driver_email}, car: {car_name}")
                else:
                    print(f"WARNING: Failed to send cancellation notification to {next_driver_email}")
            else:
                print(f"DEBUG: Next lease for car {car_name} starts in {time_difference}, no cancellation needed")
                
        except psycopg2.Error as e:
            print(f"ERROR: Error handling upcoming lease cancellation: {e}")
            raise
    
    def run_monitoring_cycle(self) -> None:
        """Run one complete monitoring cycle."""
        db_connection = None
        cursor = None
        
        try:
            # Get database connection
            db_connection = self.get_database_connection()
            if not db_connection:
                print("ERROR: Could not establish database connection")
                return
                
            cursor = db_connection.cursor()
            current_time = self.get_sk_date().replace(microsecond=0)
            
            print(f"DEBUG: Starting monitoring cycle at {current_time}")
            
            # Handle decommissioned cars
            self.handle_decommissioned_cars(cursor, current_time)
            
            # Handle late returns
            self.handle_late_returns(cursor, current_time)
            
            # Commit all changes
            db_connection.commit()
            print("DEBUG: Monitoring cycle completed successfully")
            
        except Exception as e:
            print(f"ERROR: Error during monitoring cycle: {e}")
            if db_connection:
                try:
                    db_connection.rollback()
                    print("INFO: Database changes rolled back")
                except Exception as rollback_error:
                    print(f"ERROR: Error during rollback: {rollback_error}")
        
        finally:
            # Clean up resources
            if cursor:
                try:
                    cursor.close()
                except Exception:
                    pass
            if db_connection:
                try:
                    db_connection.close()
                except Exception:
                    pass
    
    def run(self) -> None:
        """Main execution loop."""
        print("Car Lease Notificator started")
        
        while True:
            try:
                self.run_monitoring_cycle()
                time.sleep(120)  # Sleep for 2 minutes
                
            except KeyboardInterrupt:
                print("Notificator stopped by user")
                break
            except Exception as e:
                print(f"ERROR: Unexpected error in main loop: {e}")
                time.sleep(120)  # Continue after error

if __name__ == "__main__":
    notificator = CarLeaseNotificator()
    notificator.run() 