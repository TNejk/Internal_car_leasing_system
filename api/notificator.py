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

db_con = psycopg2.connect(dbname=db_name, user=db_user, host=db_host, port=db_port, password=db_pass)
cur = db_con.cursor()
print("Notificator started.")

def sleep_replacement(seconds):
    start_time = time.time()  # Record the current time
    while time.time() - start_time < seconds:
        pass  # Keep looping until the time difference reaches the desired seconds

tz = pytz.timezone('Europe/Bratislava')

allready_sent_notification = []
while True:

    now = datetime.now(tz).replace(microsecond=0) 
    # Late returns
    lease_query = """
        SELECT id_driver, id_car, start_of_lease, end_of_lease
        FROM lease
        WHERE end_of_lease < %s AND status = true
        LIMIT 1;
    """

    cur.execute(lease_query, (now,))
    active_leases = cur.fetchall()
    if len(active_leases) >0:
        # if its over the limit
        for i in active_leases:

            email_query = "SELECT email FROM driver WHERE id_driver = %s"
            cur.execute(email_query, (i[0],))
            email = cur.fetchone()

            cur.execute("select name from car where id_car = %s", (i[1],))
            car_name = cur.fetchall()[0]
            # send notif to the email topic and the
            str_mess = "Skončil sa limit na vrátenie auta, prosím odovzdajte auto v aplikácií!"

            #TODO: PRED POSLANIM SA MUSIM ZBAVIT @ V EMAILE KEDZE TO NENI PLATNY TOPIC, NAHRAD HO _
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
                        title=f"Zamestnanec {email[0]} nestihol odovzdať auto včas {car_name}."
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
            if next_lease:
                upcoming_start = next_lease[1]
                # Check if the lease's start time is now or within the next 5 minutes
                if upcoming_start <= now + timedelta(minutes=5):
                    # Cancel the upcoming lease by updating its status
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
                        topic=email.replace("@", "_")
                    )
                    messaging.send(cancel_notification)
                    print(f"{datetime.now(tz).replace(microsecond=0)}  ## Upcoming lease cancelled for {email}.")
            






    reminder_query = """
        SELECT id_driver, id_car
        FROM lease
        WHERE EXTRACT(EPOCH FROM (end_of_lease - %s)) / 60 < 20 
        AND status = true
        LIMIT 1;
    """
    cur.execute(reminder_query, (now,))
    active_leases = cur.fetchall()
    if len(active_leases) > 0:
        for i in active_leases:
            email_query = "SELECT email FROM driver WHERE id_driver = %s"
            cur.execute(email_query, (i[0],))
            email = cur.fetchone()

            cur.execute("select name from car where id_car = %s", (i[1],))
            car_name = cur.fetchone()
            message = messaging.Message(
                                notification=messaging.Notification(
                                title=f"Nezabudni odovzdať požičané auto: {car_name}"
                            ),
                                topic=email[0].replace("@", "_")
                            )
            messaging.send(message)
            print(f"{datetime.now(tz).replace(microsecond=0)}  ## Reminder message sent to {email}. ")

    sleep_replacement(600)