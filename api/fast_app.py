import os
import pytz
from typing import Annotated
from fastapi import FastAPI, Depends
from dotenv import load_dotenv
load_dotenv()
from routers import auth, car, lease, notifications, report, trip, user, admin
import firebase_admin
from firebase_admin import credentials



bratislava_tz = pytz.timezone('Europe/Bratislava')


#! app = FastAPI(docs_url=None, redoc_url=None)
#! 
# V produkcií, nenechať otvorenú dokumentáciu svetu!!

cred = credentials.Certificate("icls-56e37-firebase-adminsdk-2d4e2-be93ca6a35.json")
firebase_admin.initialize_app(cred)


app = FastAPI()

app.include_router(auth.router)
app.include_router(car.router)
app.include_router(lease.router)
app.include_router(notifications.router)
app.include_router(report.router)
app.include_router(trip.router)
app.include_router(user.router)
app.include_router(admin.router)

