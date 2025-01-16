from datetime import datetime
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

# add a chcecker for when there is 20 minutes till car return 
# so they wont forget to return i
# only after that send notifications to both

def send_late_return_notif(active_leases, cur):
    # if its over the limit get user email
    for i in active_leases:
        email_query = "SELECT email FROM driver WHERE id_driver = %s"
        cur.execute(email_query, (i[0],))
        email = cur.fetchone()

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
                title="Zamestnanec {} neskoro odovzdal auto {}.",
                body="Okamžitá poprava strelnou zbraňou je odporúčaná."
            ),
            topic = "late_returns"
        )
        messaging.send(manager_message)

        print(f"{datetime.now(tz).replace(microsecond=0)}  ## Message sent. ")

def send_reminder(active_leases, cur):
    for i in active_leases:
        email_query = "SELECT email FROM driver WHERE id_driver = %s"
        cur.execute(email_query, (i[0],))
        email = cur.fetchone()

        cur.execute("select car_name from car where id_car = %s", (i[1]))
        car_name = cur.fetchone()
        message = messaging.Message(
                            notification=messaging.Notification(
                            title=f"Nezabudni odovzdať požičané auto: {car_name}",
                            body="inak bue zle :()"
                        ),
                            topic=email[0].replace("@", "_")
                        )
        messaging.send(message)

while True:
    tz = pytz.timezone('Europe/Bratislava')
    now = datetime.now(tz).replace(microsecond=0) 
    # Late returns
    lease_query = """
        SELECT id_driver, id_car
        FROM lease
        WHERE end_of_lease < %s AND status = true
        LIMIT 1;
    """

    cur.execute(lease_query, (now,))
    active_leases = cur.fetchall()
    if len(active_leases) >0:
        send_late_return_notif(active_leases=active_leases, cur=cur)

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
        send_reminder(active_leases= active_leases, cur=cur)

    time.sleep(30)