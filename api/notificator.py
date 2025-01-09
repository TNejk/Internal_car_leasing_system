
import datetime
from firebase_admin import messaging
import psycopg2
import firebase_admin
from firebase_admin import credentials
import os
import time

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


while False:
    lease_query = """SELECT *
        FROM leases
        WHERE (
            (time_of < @new_time_to AND time_to > @new_time_of)
        ) AND WHERE status = true
        LIMIT 1; """

    cur.execute(lease_query, (datetime.now()))
    active_leases = cur.fetchall()

    # if its over the limit get user email
    for i in active_leases:
        email_query = "SELECT email FROM USER WHERE id_user = %s"
        cur.execute(email_query, (i))
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

        message = messaging.Message(
            notification=messaging.Notification(
                title="Zamestnanec {} neskoro odovzdal auto {}.",
                body="Zamestnanec {} neskoro odovzdal auto {} o {} minút."
            ),
            topic = "manager"
        )

    time.sleep(1700)