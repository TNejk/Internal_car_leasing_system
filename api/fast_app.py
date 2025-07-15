import os
import pytz
from typing import Annotated
from fastapi import FastAPI, Depends
from dotenv import load_dotenv
load_dotenv()
import api_models.default as modef
from internal.dependencies import get_current_user
from routers import auth, car, lease, notifications, report, trip, user

bratislava_tz = pytz.timezone('Europe/Bratislava')


#! app = FastAPI(docs_url=None, redoc_url=None)
#! 
# V produkcií, nenechať otvorenú dokumentáciu svetu!!
app = FastAPI()

app.include_router(auth.router)
app.include_router(car.router)
app.include_router(lease.router)
app.include_router(notifications.router)
app.include_router(report.router)
app.include_router(trip.router)
app.include_router(user.router)

@app.get("jjj")
async def hi():
  return {"msg": "gheloo"}

@app.post("/v2/check_token", response_model=modef.DefaultResponse)
async def check_token(current_user: Annotated[modef.User, Depends(get_current_user)]):
  """Validate JWT token"""
  pass
