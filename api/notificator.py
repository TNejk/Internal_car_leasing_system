
import datetime
from firebase_admin import messaging
import psycopg2

# Login to firebase    # FIREBASE
cred = credentials.Certificate("aklsdjlaksjal-firebase-adminsdk-x9g9j-8d6f043791.json")
firebase_admin.initialize_app(cred)

db_con = psycopg2.connect(dbname=db_name, user=db_user, host=db_host, port=db_port, password=db_pass)
cur = db_con.cursor()
#  check for live leases
# compare the end times to now

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
    str_mess = "Skončil sa limit na vrátenie auta, prosím odovzdajťe auto cez aplikáciu!"
    message = messaging.Message(
                        notification=messaging.Notification(
                        title="Nezabudni vrátiť auto!",
                        body=str_mess
                    ),
                        topic=email
                    )