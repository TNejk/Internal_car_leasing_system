# New API 
# Uses SQL Alchermy and FastAPI 
from pathlib import Path
from fastapi import FastAPI, Query
from pydantic import BaseModel
from typing import Annotated
from datetime import datetime, timedelta, timezone
from dateutil.parser import parse
import pytz


##################################################################
#                   Default multi use models                     #
##################################################################
class ErrorResponse(BaseModel):
    status: bool
    msg: str

#? used for every endpoint with a simple true false response
class default_response(BaseModel):
    status: bool
    msg:    Annotated[str | None, Query(default=None)]


##################################################################
#                      User REQUEST models                       #
# ################################################################

class register_obj(BaseModel):
    email: Annotated[str, Query(min_length=9)]
    password: Annotated[str, Query(min_length=15)]
    role: Annotated[str, Query(examples=["manager", "user", "admin", "system"])]
    name: Annotated[str, Query(min_length=4)]

class login_obj(BaseModel):
    email: str
    password: str

class user_edit_req(BaseModel):
    email: Annotated[str | None, Query(min_length=9)] # @gamo.sk = 8 char
    password: Annotated[str | None, Query(default=None)]
    role: Annotated[str | None, Query(default=None)]
    name: Annotated[str | None, Query(default=None)]

class car_creation_req(BaseModel):
    car_name:   Annotated[str, Query(max_length=30, min_length=4)]
    car_type:   Annotated[str, Query(examples=["personal", "cargo"])]
    spz:        Annotated[str, Query(min_length=7)]
    gas_type:   Annotated[str, Query(example=['benzine','naft','diesel','electric'])]
    drive_type: Annotated[str, Query(example=["manual", "automatic"])]
    car_image:  Annotated[bytearray, Query(description=".jpg or .png only")]

class car_editing_req(BaseModel):
    car_name:   Annotated[str | None, Query(default=None)]
    car_type:   Annotated[str | None, Query(default=None, examples=["personal", "cargo"])]
    car_status: Annotated[str | None, Query(default=None, examples=['available','away','unavailable','decommissioned'])]
    spz:        Annotated[str | None, Query(default=None, min_length=7)]
    gas_type:   Annotated[str | None, Query(default=None, example=['benzine','naft','diesel','electric'])]
    drive_type: Annotated[str | None, Query(default=None, example=['manual','automatic'])]
    car_image:  Annotated[bytearray | None, Query(default=None)]

class car_deletion_req(BaseModel):
    car_id: int

class user_deletion_req(BaseModel):
    email: str

class single_car_req(BaseModel):
    car_name: str

class car_decommision_req(BaseModel):
    car_name: str
    time_from: Annotated[datetime, Query(example="", description="CET time when the car was decommisoned.")]
    time_to:   Annotated[datetime, Query(example="", description="CET time when the car will be active again.")]

class car_activation_req(BaseModel):
    car_name: str
    car_id: Annotated[int | None, Query(description="If ID is available use it before selecting with car name")]

class car_information_req(BaseModel):
    car_id: int

# class user_information_req(BaseModel):
# This will only use headers to get the email and role 
# class report_list is the same  

class report_req(BaseModel):
    path: Annotated[Path, Query(description="Path and filename to a locally stored excel report.")]

class car_starting_date_req(BaseModel):
    car_name: str
    car_id: Annotated[int | None, Query(description="If ID is available use it before selecting with car name")]

class leases_list_req(BaseModel):
    filter_email:             Annotated[str | None, Query(default=None)]
    filter_car_id:            Annotated[int | None, Query(default=None)]
    filter_time_from:         Annotated[datetime | None, Query(example="CET time",    default=None)]
    filter_time_to:           Annotated[datetime | None, Query(example="CET time",    default=None)]
    filter_active_leases:     Annotated[bool | None, Query(example="Active leases",   default=None)]
    filter_incactive_leases:  Annotated[bool | None, Query(example="InActive leases", default=None)]

class monthly_leases_req(BaseModel):
    month: Annotated[int, Query(description="Which month to filter leases by.")]

class cancel_lease_req(BaseModel):
    recipient: Annotated[str | None, Query(default=None, description="Whose lease to cancel, if not manager users email is utilized instead.")]
    car_name:  str
    car_id:    Annotated[int | None, Query(description="If ID is available use it before selecting with car name")]

class lease_car_req(BaseModel):
    recipient:    Annotated[str | None, Query(default=None)]
    car_id:       int
    private_ride: bool
    time_from:    Annotated[datetime | None, Query(example="CET time",    default=None)]
    time_to:      Annotated[datetime | None, Query(example="CET time",    default=None)]

class approve_pvr_req(BaseModel):
    approval:   bool
    request_id: int
    time_from:  Annotated[datetime | None, Query(example="CET time",    default=None)]
    time_to:    Annotated[datetime | None, Query(example="CET time",    default=None)]
    car_id:     int
    requester:  Annotated[str, Query(description="User who requested the private ride",  default=None)]

class return_car_req(BaseModel):
    lease_id:        int
    time_of_return:  Annotated[datetime | None, Query(example="CET time",    default=None)]
    return_location: str
    damaged:         bool
    dirty_car:       bool
    interior_damage: bool
    exterior_damage: bool
    collision:       bool

class read_notification_req(BaseModel):
    notification_id: int


#################################################################
#                    API RESPONSE MODELS                        #
#################################################################

class login_response(BaseModel):
    token: str
    role:  Annotated[str, Query(examples=["manager", "user", "admin"])]
    email: str

class user_list_response(BaseModel):
    """ A list of all users and their roles in a dict. """
    users: Annotated[list[dict] | None, Query(default=None, example="{email: user@gamo.sk, role: manager}")]

class single_car_response(BaseModel, Query(deprecated=True)):
    """ Redundant function, does the same as car_info_response. """
    car_id:       int
    spz:          Annotated[str, Query(min_length=7)]
    car_type:     Annotated[str, Query(examples=['personal', 'cargo'])]
    gearbox_type: Annotated[str, Query(examples=['manual', 'automatic'])]
    fuel_type:    Annotated[str, Query(examples=['benzine','naft','diesel','electric'])]
    region:       Annotated[str, Query(examples=['local', 'global'])]
    car_status:   Annotated[str, Query(examples=['available','away','unavailable','decommissioned'])]
    seats:        Annotated[int, Query(min_length=2)]
    usage_metric: int
    image_url:    str

class list_car_reponse(BaseModel):
    """ A list of car's with their status, name, spz and image. """
    car_id:     int 
    car_name:   str
    car_status: Annotated[str, Query(examples=['available','away','unavailable','decommissioned'])]
    spz:        Annotated[str | None, Query(default=None, min_length=7)]
    image_url:  str

class car_info_response(BaseModel):
    """ Every information about the requested car. """
    car_id:       int
    spz:          Annotated[str, Query(min_length=7)]
    car_type:     Annotated[str, Query(examples=['personal', 'cargo'])]
    gearbox_type: Annotated[str, Query(examples=['manual', 'automatic'])]
    fuel_type:    Annotated[str, Query(examples=['benzine','naft','diesel','electric'])]
    region:       Annotated[str, Query(examples=['local', 'global'])]
    car_status:   Annotated[str, Query(examples=['available','away','unavailable','decommissioned'])]
    seats:        Annotated[int, Query(min_length=2)]
    usage_metric: int
    image_url:    str
    decommision_time: Annotated[datetime | None, Query(example="CET time", default=None, description="Unless the car is decommisioned this will be None")]
    allowed_hours: Annotated[list[list[datetime, datetime]], Query(example="[[2025.12.3 11:30, 2025.14.3 07:00]]", description="A list containing starting and ending times of leases bound to this car.")]

class user_info_response(BaseModel):
    """ Basic information about the requested user. """
    user_id:  int
    username: str
    email:    str
    role:     Annotated[str, Query(examples=["manager", "user", "admin", "system"])]

class report_list_response(BaseModel):
    """ Returns a list of paths to individual excel reports.\n  ['/app/reports/2025-01-21 ICLS_report.xlsx'] """
    reports: Annotated[list[str], Query(example="['/app/reports/2025-01-21 ICLS_report.xlsx']", description="A list containing relative paths to the report directory. ")]

class report_single_response(BaseModel, Query(deprecated=True)):
    """ This object is useless, as it returns the excel file as a file to be downlaoed by the browser."""
    # This should send the requested excel file as a file to donwload. So nothing is actually being sent back by the endpoint except the file
    pass

class leaseEntry(BaseModel):
    lease_id:             int
    lease_status:         Annotated[str | None, Query(examples=['created', 'scheduled', 'active', 'late', 'unconfirmed', 'returned', 'canceled', 'missing', 'aborted'],    default=None)]
    creation_time:        Annotated[datetime | None, Query(example="CET time",    default=None)]
    starting_time:        Annotated[datetime | None, Query(example="CET time",    default=None)]
    ending_time:          Annotated[datetime | None, Query(example="CET time",    default=None)]
    approved_return_time: Annotated[datetime | None, Query(example="CET time",    default=None)]
    missing_time:         Annotated[datetime | None, Query(example="CET time",    default=None)]
    cancelled_time:       Annotated[datetime | None, Query(example="CET time",    default=None)]
    aborted_time:         Annotated[datetime | None, Query(example="CET time",    default=None)]
    driver_email:         str
    car_name:             str
    status_updated_at:    Annotated[datetime | None, Query(example="CET time",    default=None)]
    last_changed_by:      str
    region_tag:           Annotated[str, Query(examples=['local', 'global'])]


class leaseListResponse(BaseModel):
    active_leases: list[leaseEntry]


class leaseCancelResponse(BaseModel):
    cancelled: bool

class monthlyLeasesResponse(BaseModel):
    start_of_lease:  Annotated[datetime | None, Query(example="CET time",    default=None)]
    end_of_lease:    Annotated[datetime | None, Query(example="CET time",    default=None)]
    time_of_return:  Annotated[datetime | None, Query(example="CET time",    default=None)]
    lease_status:    Annotated[str | None, Query(examples=['created', 'scheduled', 'active', 'late', 'unconfirmed', 'returned', 'canceled', 'missing', 'aborted'],    default=None)]
    car_name:        str
    driver_email:    str
    note:            Annotated[str, Query(max_length=250)]

class leaseCarResponse(BaseModel):
    status:  bool
    private: bool
    msg: Annotated[str | None, Query(default=None)]

class requestEntry(BaseModel):
    request_id:     int
    starting_time:  Annotated[datetime | None, Query(example="CET time",    default=None)]
    ending_time:    Annotated[datetime | None, Query(example="CET time",    default=None)]
    request_status: Annotated[str, Query(examples=['pending',  'approved',  'rejected',  'cancelled'])]
    car_name:       str
    spz:            Annotated[str | None, Query(default=None, min_length=7)]
    driver_email:   str
    image_url:      str

class requestListResponse(BaseModel):
    active_requests: list[requestEntry]


#######################################################
#                  ENDPOINTS SECTION                  #
#######################################################
app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Hellow"}

# This will get the json, convert it to the Item object (if possible) and then return that object for you to work with
# ! THJIS USES A DEFAULT ERROR RESPONSE MODEL FROM PYDANTIC, DO IT LIKE THIS FOR EVERY ROUTE
@app.post("/sss", responses={500: {"model": ErrorResponse}}) 
def return_sdsd():

    ss = car_decommision.time_from




@app.route("/logout", methods=["POST"])


@app.route('/register', methods = ['POST'])

@app.route('/login', methods=['POST'])

@app.route('/edit_user', methods = ['POST'])

@app.route('/create_car', methods = ['POST'])

@app.route('/edit_car', methods = ['POST'])

@app.route('/delete_car', methods=['POST'])

@app.route('/delete_user', methods=['POST'])

@app.route('/get_users', methods=['GET'])

#@app.route('/get_single_user', methods=['POST'])
@app.route('/get_single_car', methods=['POST'])

@app.route('/get_car_list', methods=['GET'])

@app.route('/decommision_car', methods= ['POST'])

@app.route('/activate_car', methods= ['POST'])

@app.route('/get_full_car_info', methods=['POST', 'OPTIONS'])

@app.route('/get_all_car_info', methods=['POST'])

@app.route('/get_all_user_info', methods=['POST'])

@app.route('/list_reports', methods = ['POST'])

@app.route('/get_report/<path:filename>', methods=['GET'])

@app.route('/get_leases', methods = ['POST'])

@app.route('/cancel_lease', methods = ['POST'])

@app.route('/get_monthly_leases', methods = ['POST'])

@app.route('/lease_car', methods = ['POST'])

@app.route('/get_requests', methods = ['POST'])

@app.route('/approve_req', methods = ['POST'])

@app.route('/return_car', methods = ['POST'])

#@app.route('/read_notification', methods = ['POST'])

@app.route('/notifications', methods=['GET'])

@app.route('/notifications/mark-as-read/', methods=['POST'])

@app.route('/check_token', methods = ['POST'])

