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

def sleep_replacement(seconds):
    start_time = time.time()  # Record the current time
    while time.time() - start_time < seconds:
        pass  # Keep looping until the time difference reaches the desired seconds

tz = pytz.timezone('Europe/Bratislava')
while True:

    excel_query = """
        SELECT 
            d.email AS email, 
            c.name AS car_name, 
            l.start_of_lease, 
            l.end_of_lease
        FROM lease l
        INNER JOIN driver d ON l.id_driver = d.id_driver
        INNER JOIN car c ON l.id_car = c.id_car
        WHERE l.status = true
        LIMIT 1;
    """


    cur.execute(excel_query)
    active_leases = cur.fetchall()
    
    path = f"{os.getcwd()}/reports/ ICLS report.csv"
    for i in active_leases:
        file = open(path, "a+")
        file.write("Meno,Auto,Čas prevziatia,Čas odovzdania,Čas vrátenia,Meškanie,Poznámka")
        file.write(f"{i[0]},{i[1]},{i[2]},{i[3]},{"REPLACE"},{"REPLACE"}")
        file.close()


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
        # if its over the limit get user email
        for i in active_leases:
            email_query = "SELECT email FROM driver WHERE id_driver = %s"
            cur.execute(email_query, (i[0],))
            email = cur.fetchone()

            cur.execute("select name from car where id_car = %s", (i[1],))
            car_name = cur.fetchone()
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
                    title=f"Zamestnanec {email[0]} nestihol odovzdať auto včas {car_name}.",
                    body="Okamžitá poprava strelnou zbraňou je odporúčaná."
                ),
                topic = "late_returns"
            )
            messaging.send(manager_message)
            print(f"{datetime.now(tz).replace(microsecond=0)}  ## Later return message sent to {email}. ")

    reminder_query = """
        SELECT id_driver, id_car
        FROM lease
        WHERE EXTRACT(EPOCH FROM (end_of_lease - %s)) / 60 < 20 
        AND status = true
        LIMIT 1;
    """
    cur.execute(reminder_query, (now,))
    active_leases = cur.fetchall()
    print("ran again")
    print(active_leases)

    if len(active_leases) > 0:
        for i in active_leases:
            email_query = "SELECT email FROM driver WHERE id_driver = %s"
            cur.execute(email_query, (i[0],))
            email = cur.fetchone()

            cur.execute("select name from car where id_car = %s", (i[1],))
            car_name = cur.fetchone()
            message = messaging.Message(
                                notification=messaging.Notification(
                                title=f"Nezabudni odovzdať požičané auto: {car_name}",
                                body="inak bue zle :()"
                            ),
                                topic=email[0].replace("@", "_")
                            )
            messaging.send(message)
            print(f"{datetime.now(tz).replace(microsecond=0)}  ## Reminder message sent to {email}. ")

    sleep_replacement(60)