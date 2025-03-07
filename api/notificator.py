from datetime import datetime, timedelta
from firebase_admin import messaging
import psycopg2
import firebase_admin
from firebase_admin import credentials
import os
import time

import pytz
from pytz import timezone as tz



db_host = os.getenv('DB_HOST')
db_port = os.getenv('DB_PORT')
db_user = os.getenv('POSTGRES_USER')
db_pass = os.getenv('POSTGRES_PASS')
db_name = os.getenv('POSTGRES_DB')

# Login to firebase    # FIREBASE
cred = credentials.Certificate("icls-56e37-firebase-adminsdk-2d4e2-be93ca6a35.json")
firebase_admin.initialize_app(cred)


print("Notificator started.")

def get_sk_date() -> str:
    bratislava_tz = pytz.timezone('Europe/Bratislava')
    # Ensure the datetime is in UTC before converting
    dt_obj = datetime.now()
    utc_time = dt_obj.replace(tzinfo=pytz.utc) if dt_obj.tzinfo is None else dt_obj.astimezone(pytz.utc)
    bratislava_time = utc_time.astimezone(bratislava_tz)  # Convert to Bratislava timezone
    return bratislava_time.strftime("%Y-%m-%d %H:%M:%S") 

def sleep_replacement(seconds):
    start_time = time.time()  # Record the current time
    while time.time() - start_time < seconds:
        pass  # Keep looping until the time difference reaches the desired seconds

tz = pytz.timezone('Europe/Bratislava')

while True:
    db_con = psycopg2.connect(dbname=db_name, user=db_user, host=db_host, port=db_port, password=db_pass)
    cur = db_con.cursor()
    now = datetime.now(tz).replace(microsecond=0)

    str_today = get_sk_date()
    obj_today = datetime.strptime(str_today, "%Y-%m-%d %H:%M:%S")
    
    # TODO: add into a TRY CATCH BLOCK!
    decom_cars_query = """
    SELECT car_name, email, time_to from decommissioned_cars WHERE status = TRUE AND time_to < %s 
    """
    cur.execute(decom_cars_query, (obj_today))
    activable_cars = cur.fetchall()

    # Turn off the decomission request status and send a notification for the car
    for i in activable_cars:
        cur.execute("UPDATE car SET status = 'stand_by' WHERE name = %s", (i[0], ))
        
        message = messaging.Message(
        notification=messaging.Notification(
        title=f"Auto {i[0]} je k dispozíci!",
        body=f"""Je možné znova auto rezervovať v aplikácií. :D"""),topic="system")

        messaging.send(message)
    db_con.commit()


    # Late returns
    lease_query = """
        SELECT id_driver, id_car, start_of_lease, end_of_lease, id_lease
        FROM lease
        WHERE end_of_lease < %s AND status = true AND under_review IS NOT true;
    """

    cur.execute(lease_query, (now,))
    active_leases = cur.fetchall()
    if len(active_leases) >0:
        # if its over the limit, id_driver, id_car, start_of_lease, end_of_lease
        for i in active_leases:

            email_query = "SELECT email FROM driver WHERE id_driver = %s"
            cur.execute(email_query, (i[0],))
            email = cur.fetchone()

            cur.execute("select name from car where id_car = %s", (i[1],))
            car_name = cur.fetchall()[0]
            # send notif to the email topic and the
            str_mess = "Skončil sa limit na vrátenie auta, prosím odovzdajte auto v aplikácií!"
            
            #! email.replace("@", "_")
            message = messaging.Message(
                                notification=messaging.Notification(
                                title="Prekrocenie limitu na odovzdanie auta",
                                body=str_mess
                            ),
                                topic=email[0].replace("@", "_")
                            )
            messaging.send(message)

    
            manager_message = messaging.Message(
                    notification=messaging.Notification(
                        title= "Neskoré odovzdanie auta!",
                        body=f"Zamestnanec {email[0]} nestihol odovzdať auto: {car_name}."
                    ),
                    topic = "late_returns"
                )
            messaging.send(manager_message)
                # Appedn the car_email combo to the allready send notifications, i[2] is timeof, i[3] is timeto 
            #allready_sent_notification.append((email, car_name, i[2], i[3]))

            print(f"{datetime.now(tz).replace(microsecond=0)}  ## Later return message sent to {email}. ")

            # *** New functionality: Check for an upcoming lease to cancel ***
            # Look for the next lease for the same car that hasn't started yet
            next_lease_query = """
                SELECT id_driver, start_of_lease, id_lease
                FROM lease
                WHERE id_car = %s AND start_of_lease >= %s AND status = true
                ORDER BY start_of_lease ASC
                LIMIT 1;
            """
            cur.execute(next_lease_query, (i[1], now))
            next_lease = cur.fetchone()

            # Then check if it needs to be cancelled by checking if the difference between the now and the next leases start time.
            # Since we have established that this car has yet to be returned, we can safely cancell the next lease if its near 30 minutes of its start 
            if next_lease:
                upcoming_start = next_lease[1]
                time_difference = upcoming_start - now
                # If the upcoming lease starts within 30 minutes, cancel it
                if time_difference <= timedelta(minutes=30):
                    cancel_query = """
                        UPDATE lease
                        SET status = false
                        WHERE id_lease = %s AND status = true;
                    """
                    cur.execute(cancel_query, (next_lease[2],))
                    db_con.commit()

                    cancel_notification = messaging.Message(
                        notification=messaging.Notification(
                            title="Rezervácia zrušená",
                            body="Vaša rezervácia na auto bola zrušená, pretože predchádzajúci prenájom neskončil načas."
                        ),
                        topic=email[0].replace("@", "_")
                    )
                    messaging.send(cancel_notification)
                    print(f"{datetime.now(tz).replace(microsecond=0)} - Upcoming lease cancelled for {email[0]}.")
                else:
                    print(f"Next lease debug: time_difference={time_difference}, upcoming_start={upcoming_start}, now={now}, next_lease={next_lease}")
            else:
                print(f"No upcoming lease found for car {car_name} at {now}.")

            # Set under_review to true so the notification does not go again
            review_query = """
                        UPDATE lease
                        SET under_review = true
                        WHERE id_lease = %s AND status = true;
                    """
            cur.execute(review_query, (i[4], ))
        
    db_con.close()
    sleep_replacement(120)