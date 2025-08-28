###########################

# This file handles late returns and decommissioned cars, also sends notifications

###########################

from datetime import datetime, timedelta
from firebase_admin import messaging
import firebase_admin
from firebase_admin import credentials
import os
import time
import pytz
from typing import Optional, List, Tuple
from sqlalchemy.orm import sessionmaker
from sqlalchemy import and_, or_


from db.database import SessionLocal
import db.models as model
from db.enums import LeaseStatus, CarStatus, UserRoles, NotificationTypes, TargetFunctions, TripsStatuses


db_host = os.getenv('DB_HOST')
db_port = os.getenv('DB_PORT')
db_user = os.getenv('POSTGRES_USER')
db_pass = os.getenv('POSTGRES_PASS')
db_name = os.getenv('POSTGRES_DB')

def create_notification(db_session, actor_user_id: int, recipient_role: UserRoles, 
                       notification_type: NotificationTypes, target_func: TargetFunctions,
                       title: str, message: str, expires_at: Optional[datetime] = None,
                       specific_recipients: Optional[List[int]] = None) -> bool:

    try:
        notification = model.Notifications(
            title=title,
            message=message,
            actor=actor_user_id,
            recipient_role=recipient_role,
            type=notification_type,
            target_func=target_func,
            expires_at=expires_at
        )
        
        db_session.add(notification)
        db_session.flush()  # Get the notification ID
        
        # If specific recipients are provided, create individual recipient records
        if specific_recipients:
            for recipient_id in specific_recipients:
                recipient_record = model.NotificationsRecipients(
                    notification=notification.id,
                    recipient=recipient_id,
                    is_read=False
                )
                db_session.add(recipient_record)
        
        db_session.commit()
        
        notif_type = f"role-based ({recipient_role.value})" if not specific_recipients else "specific users"
        print(f"[NOTIF] Notification created - Type: {notif_type}, Target: {target_func.value}, Title: {title}")
        return True
        
    except Exception as e:
        db_session.rollback()
        print(f"[NOTIF EXCEPTION] {e}")
        return False


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
        
    def get_database_session(self) -> Optional[sessionmaker]:
        """Get SQLAlchemy database session with error handling."""
        try:
            return SessionLocal()
        except Exception as e:
            print(f"ERROR: Database session creation failed: {e}")
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
    
    def handle_decommissioned_cars(self, db_session, current_time: datetime) -> None:
        """Handle reactivation of decommissioned cars."""
        try:
            # Find cars that should be reactivated 
            # NOTE: The original code used a 'decommissioned_cars' table that doesn't exist in the new schema
            # For now, we'll look for cars with status 'decommissioned' that have been decommissioned for a certain period
            # This logic may need adjustment based on how decommission time is actually tracked
            
            decommissioned_cars = db_session.query(model.Cars).filter(
                model.Cars.status == CarStatus.decommissioned,
                model.Cars.is_deleted == False
            ).all()
            
            # Get system user for notifications 
            system_user = db_session.query(model.Users).filter(
                model.Users.role == UserRoles.system
            ).first()
            
            if not system_user:
                print("WARNING: No system user found for notifications")
                return
            
            for car in decommissioned_cars:
                try:
                    # Reactivate the car
                    car.status = CarStatus.available
                    
                    # Create system-wide notification for all users
                    create_notification(
                        db_session=db_session,
                        actor_user_id=system_user.id,
                        recipient_role=UserRoles.user,  # Notify all users
                        notification_type=NotificationTypes.success,
                        target_func=TargetFunctions.lease,
                        title=f"Auto {car.name} je k dispozíci!",
                        message="Je možné znova auto rezervovať v aplikácií. :D"
                    )
                    
                    message = messaging.Message(
                        notification=messaging.Notification(
                            title=f"Auto {car.name} je k dispozíci!",
                            body="Je možné znova auto rezervovať v aplikácií. :D"
                        ),
                        topic="system"
                    )
                    
                    if self.send_firebase_message(message):
                        print(f"INFO: Reactivated car: {car.name}")
                    else:
                        print(f"WARNING: Failed to send reactivation notification for car: {car.name}")
                        
                except Exception as e:
                    print(f"ERROR: Error while reactivating car {car.name}: {e}")
                    db_session.rollback()
                    raise
                    
        except Exception as e:
            print(f"ERROR: Error handling decommissioned cars: {e}")
            raise
    
    def handle_late_returns(self, db_session, current_time: datetime) -> None:
        """Handle late car returns and potential lease cancellations."""
        try:
            # Find late returns - leases that should have ended but are still active
            late_leases = db_session.query(model.Leases).filter(
                model.Leases.end_time < current_time,
                model.Leases.status.in_([LeaseStatus.scheduled, LeaseStatus.active]),
                # Assuming we add a flag to track if already notified
                # model.Leases.late_notification_sent == False TODO: ADD THIS
            ).all()
            
            if not late_leases:
                return
                
            print(f"INFO: Processing {len(late_leases)} late returns")
            
            system_user = db_session.query(model.Users).filter(
                model.Users.role == UserRoles.system
            ).first()
            
            if not system_user:
                print("WARNING: No system user found for notifications")
                return
            
            for lease in late_leases:
                try:
                    driver = db_session.query(model.Users).filter(
                        model.Users.id == lease.id_user
                    ).first()
                    
                    car = db_session.query(model.Cars).filter(
                        model.Cars.id == lease.id_car
                    ).first()
                    
                    if not driver or not car:
                        print(f"WARNING: Missing driver or car for lease {lease.id}")
                        continue
                    
                    # Send notification to driver (specific user notification)
                    create_notification(
                        db_session=db_session,
                        actor_user_id=system_user.id,
                        recipient_role=UserRoles.user,
                        notification_type=NotificationTypes.danger,
                        target_func=TargetFunctions.lease,
                        title="Prekročenie limitu na odovzdanie auta",
                        message="Skončil sa limit na vrátenie auta, prosím odovzdajte auto v aplikácií!",
                        specific_recipients=[driver.id]
                    )
                    
                    # Send notification to managers (role-based)
                    create_notification(
                        db_session=db_session,
                        actor_user_id=system_user.id,
                        recipient_role=UserRoles.manager,
                        notification_type=NotificationTypes.warning,
                        target_func=TargetFunctions.lease,
                        title="Neskoré odovzdanie auta!",
                        message=f"Zamestnanec {driver.email} nestihol odovzdať auto: {car.name}."
                    )
                    
                    driver_topic = driver.email.replace("@", "_")
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
                            body=f"Zamestnanec {driver.email} nestihol odovzdať auto: {car.name}."
                        ),
                        topic="late_returns"
                    )
                    
                    self.send_firebase_message(driver_message)
                    self.send_firebase_message(manager_message)
                    
                    print(f"INFO: Late return notification sent to {driver.email} for car {car.name}")
                    
            
                    self.handle_upcoming_lease_warning(db_session, current_time, car, system_user)
                    
                    lease.status = LeaseStatus.late
                    
                except Exception as e:
                    print(f"ERROR: Error processing late return for lease {lease.id}: {e}")
                    continue
                    
        except Exception as e:
            print(f"ERROR: Error handling late returns: {e}")
            raise
    
    def handle_status_changes(self, db_session, current_time: datetime) -> None:
        """ Handle status changes for leases, cars and trips based on current time. """
        try:
            # Handle scheduled leases that should start (scheduled -> active)
            starting_leases = db_session.query(model.Leases).filter(
                model.Leases.start_time <= current_time,
                model.Leases.status == LeaseStatus.scheduled
            ).all()
            
            for lease in starting_leases:
                try:
                    car = db_session.query(model.Cars).filter(
                        model.Cars.id == lease.id_car
                    ).first()
                    
                    user = db_session.query(model.Users).filter(
                        model.Users.id == lease.id_user
                    ).first()
                    
                    if not car or not user:
                        print(f"WARNING: Missing car or user for lease {lease.id}")
                        continue
                    
                
                    lease.status = LeaseStatus.active
                    lease.status_updated_at = current_time
                    
               
                    if car.status != CarStatus.away:
                        car.status = CarStatus.away
                        print(f"INFO: Car {car.name} status changed to 'away' for active lease {lease.id}")
                    
             
                    trip = db_session.query(model.Trips).filter(
                        model.Trips.id_lease == lease.id
                    ).first()
                    
                    if trip and trip.status == TripsStatuses.scheduled:
                        trip.status = TripsStatuses.ongoing
                        print(f"INFO: Trip {trip.trip_name} status changed to 'ongoing'")
                    
                    print(f"INFO: Lease {lease.id} activated for user {user.email} with car {car.name}")
                    
                except Exception as e:
                    print(f"ERROR: Error activating lease {lease.id}: {e}")
                    continue
            
            # Handle leases that should end (active -> returned) and haven't been manually returned
            ending_leases = db_session.query(model.Leases).filter(
                model.Leases.end_time <= current_time,
                model.Leases.status == LeaseStatus.active,
                model.Leases.return_time.is_(None)  # Not manually returned yet
            ).all()
            
            for lease in ending_leases:
                try:
                    car = db_session.query(model.Cars).filter(
                        model.Cars.id == lease.id_car
                    ).first()
                    
                    if not car:
                        print(f"WARNING: Missing car for ending lease {lease.id}")
                        continue
                    
                    # Check if there's another lease starting immediately after
                    next_lease = db_session.query(model.Leases).filter(
                        model.Leases.id_car == car.id,
                        model.Leases.start_time <= current_time + timedelta(minutes=30),  # Within 30 minutes
                        model.Leases.status == LeaseStatus.scheduled,
                        model.Leases.id != lease.id
                    ).order_by(model.Leases.start_time.asc()).first()
                    
                    # If no immediate next lease, mark car as available
                    if not next_lease:
                        car.status = CarStatus.available
                        print(f"INFO: Car {car.name} status changed to 'available' after lease {lease.id} ended")
                    
                    # Update associated trip status if exists
                    trip = db_session.query(model.Trips).filter(
                        model.Trips.id_lease == lease.id
                    ).first()
                    
                    if trip and trip.status == TripsStatuses.ongoing:
                        trip.status = TripsStatuses.ended
                        print(f"INFO: Trip {trip.trip_name} status changed to 'ended'")
                        
                except Exception as e:
                    print(f"ERROR: Error processing ending lease {lease.id}: {e}")
                    continue
            
            # Handle cars that should be available but aren't (cleanup)
            self._cleanup_car_statuses(db_session, current_time)
            
            if starting_leases or ending_leases:
                print(f"INFO: Status changes - Started: {len(starting_leases)}, Ended: {len(ending_leases)}")
                
        except Exception as e:
            print(f"ERROR: Error handling status changes: {e}")
            raise
    
    def _cleanup_car_statuses(self, db_session, current_time: datetime) -> None:
        """Clean up car statuses that may be inconsistent."""
        try:
            # Find cars that are 'away' but have no active leases
            cars_away = db_session.query(model.Cars).filter(
                model.Cars.status == CarStatus.away,
                model.Cars.is_deleted == False
            ).all()
            
            for car in cars_away:
                # Check if there's currently an active lease for this car
                active_lease = db_session.query(model.Leases).filter(
                    model.Leases.id_car == car.id,
                    model.Leases.status.in_([LeaseStatus.active, LeaseStatus.late]),
                    model.Leases.start_time <= current_time,
                    or_(
                        model.Leases.end_time > current_time,
                        model.Leases.return_time.is_(None)
                    )
                ).first()
                
                if not active_lease:
                    # No active lease found, but car is marked as away
                    # Check if there's a scheduled lease starting soon (within 1 hour)
                    upcoming_lease = db_session.query(model.Leases).filter(
                        model.Leases.id_car == car.id,
                        model.Leases.status == LeaseStatus.scheduled,
                        model.Leases.start_time <= current_time + timedelta(hours=1),
                        model.Leases.start_time > current_time
                    ).first()
                    
                    if not upcoming_lease:
                        car.status = CarStatus.available
                        print(f"INFO: Cleaned up car {car.name} status - changed from 'away' to 'available'")
                        
        except Exception as e:
            print(f"ERROR: Error during car status cleanup: {e}")
            raise

    def handle_upcoming_lease_warning(self, db_session, current_time: datetime, 
                                         car: model.Cars, system_user: model.Users) -> None:
        """Handle warning for upcoming leases if current lease is late."""

        #! Nemazať nasledujúcu rezerváciu, tá sa začne normálne, len bude upozornení pouzivatel 
        
        try:
            # Find next lease for the same car
            next_lease = db_session.query(model.Leases).filter(
                model.Leases.id_car == car.id,
                model.Leases.start_time >= current_time,
                model.Leases.status == LeaseStatus.scheduled
            ).order_by(model.Leases.start_time.asc()).first()
            
            if not next_lease:
                print(f"DEBUG: No upcoming lease found for car {car.name}")
                return
                
            next_driver = db_session.query(model.Users).filter(
                model.Users.id == next_lease.id_user
            ).first()
            
            if not next_driver:
                print(f"WARNING: No driver found for upcoming lease {next_lease.id}")
                return
                
            time_difference = next_lease.start_time - current_time
            
            # Give the next lease user an early warning if reservation is within 24 hours
            if time_difference <= timedelta(hours=24):
                # Create notification for upcoming lease holder
                create_notification(
                    db_session=db_session,
                    actor_user_id=system_user.id,
                    recipient_role=UserRoles.user,
                    notification_type=NotificationTypes.warning,
                    target_func=TargetFunctions.lease,
                    title="Dôležitá informácia o rezervácií!",
                    message="Vami rezervované auto nebolo včas odovzdané, je možné že nastane problém s vašou rezerváciou.",
                    specific_recipients=[next_driver.id]
                )
                
                # Send Firebase notification
                cancel_topic = next_driver.email.replace("@", "_")
                cancel_notification = messaging.Message(
                    notification=messaging.Notification(
                        title="Dôležitá informácia o rezervácií!",
                        body="Vami rezervované auto nebolo včas odovzdané, je možné že nastane problém s vašou rezerváciou."
                    ),
                    topic=cancel_topic
                )
                
                if self.send_firebase_message(cancel_notification):
                    print(f"INFO: Upcoming lease warning sent to {next_driver.email}, car: {car.name}")
                else:
                    print(f"WARNING: Failed to send warning notification to {next_driver.email}")
            else:
                print(f"DEBUG: Next lease for car {car.name} starts in {time_difference}, no warning needed")
                
        except Exception as e:
            print(f"ERROR: Error handling upcoming lease warning: {e}")
            raise
    
    def run_monitoring_cycle(self) -> None:
        """Run one complete monitoring cycle."""
        db_session = None
        
        try:
            db_session = self.get_database_session()
            if not db_session:
                print("ERROR: Could not establish database session")
                return
                
            current_time = self.get_sk_date().replace(microsecond=0)
            
            print(f"DEBUG: Starting monitoring cycle at {current_time}")

            self.handle_status_changes(db_session, current_time)
            self.handle_decommissioned_cars(db_session, current_time)
            self.handle_late_returns(db_session, current_time)
            db_session.commit()

            print("DEBUG: Monitoring cycle completed successfully")
            
        except Exception as e:
            print(f"ERROR: Error during monitoring cycle: {e}")
            if db_session:
                try:
                    db_session.rollback()
                    print("INFO: Database changes rolled back")
                except Exception as rollback_error:
                    print(f"ERROR: Error during rollback: {rollback_error}")
        
        finally:
            if db_session:
                try:
                    db_session.close()
                except Exception:
                    pass
    
    def run(self) -> None:
        """Main execution loop."""
        print("Car Lease Notificator started")
        
        while True:
            try:
                self.run_monitoring_cycle()
                time.sleep(120)  
                
            except Exception as e:
                print(f"ERROR: Unexpected error in main loop: {e}")
                time.sleep(120)  # Continue after error

if __name__ == "__main__":
    notificator = CarLeaseNotificator()
    notificator.run() 