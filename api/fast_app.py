from pathlib import Path
from fastapi import FastAPI, Query, HTTPException, Header
from pydantic import BaseModel, Field
from typing import Annotated, Optional
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
class DefaultResponse(BaseModel):
    status: bool
    msg: Annotated[str | None, Field(default=None)]


##################################################################
#                      User REQUEST models                       #
# ################################################################

class RegisterRequest(BaseModel):
    email: Annotated[str, Field(min_length=9)]
    password: Annotated[str, Field(min_length=15)]
    role: Annotated[str, Field(examples=["manager", "user", "admin", "system"])]
    name: Annotated[str, Field(min_length=4)]

class login_obj(BaseModel):
    email: str
    password: str

class user_edit_req(BaseModel):
    email: Annotated[str | None, Field(min_length=9)] # @gamo.sk = 8 char
    password: Annotated[str | None, Field(default=None)]
    role: Annotated[str | None, Field(default=None)]
    name: Annotated[str | None, Field(default=None)]

class car_creation_req(BaseModel):
    car_name:   Annotated[str, Field(max_length=30, min_length=4)]
    car_type:   Annotated[str, Field(examples=["personal", "cargo"])]
    spz:        Annotated[str, Field(min_length=7)]
    gas_type:   Annotated[str, Field(examples=['benzine','naft','diesel','electric'])]
    drive_type: Annotated[str, Field(examples=["manual", "automatic"])]
    car_image:  Annotated[bytearray, Field(description=".jpg or .png only")]

class car_editing_req(BaseModel):
    car_name:   Annotated[str | None, Field(default=None)]
    car_type:   Annotated[str | None, Field(default=None, examples=["personal", "cargo"])]
    car_status: Annotated[str | None, Field(default=None, examples=['available','away','unavailable','decommissioned'])]
    spz:        Annotated[str | None, Field(default=None, min_length=7)]
    gas_type:   Annotated[str | None, Field(default=None, examples=['benzine','naft','diesel','electric'])]
    drive_type: Annotated[str | None, Field(default=None, examples=['manual','automatic'])]
    car_image:  Annotated[bytearray | None, Field(default=None)]

class car_deletion_req(BaseModel):
    car_id: int

class user_deletion_req(BaseModel):
    email: str

class single_car_req(BaseModel):
    car_name: str

class car_decommision_req(BaseModel):
    car_name: str
    time_from: Annotated[datetime, Field(examples=[""], description="CET time when the car was decommisoned.")]
    time_to:   Annotated[datetime, Field(examples=[""], description="CET time when the car will be active again.")]

class car_activation_req(BaseModel):
    car_name: str
    car_id: Annotated[int | None, Field(description="If ID is available use it before selecting with car name")]

class car_information_req(BaseModel):
    car_id: int

# class user_information_req(BaseModel):
# This will only use headers to get the email and role 
# class report_list is the same  

class report_req(BaseModel):
    path: Annotated[Path, Field(description="Path and filename to a locally stored excel report.")]

class car_starting_date_req(BaseModel):
    car_name: str
    car_id: Annotated[int | None, Field(description="If ID is available use it before selecting with car name")]

class leases_list_req(BaseModel):
    filter_email:             Annotated[str | None, Field(default=None)]
    filter_car_id:            Annotated[int | None, Field(default=None)]
    filter_time_from:         Annotated[datetime | None, Field(examples=["CET time"],    default=None)]
    filter_time_to:           Annotated[datetime | None, Field(examples=["CET time"],    default=None)]
    filter_active_leases:     Annotated[bool | None, Field(examples=["Active leases"],   default=None)]
    filter_incactive_leases:  Annotated[bool | None, Field(examples=["InActive leases"], default=None)]

class monthly_leases_req(BaseModel):
    month: Annotated[int, Field(description="Which month to filter leases by.")]

class cancel_lease_req(BaseModel):
    recipient: Annotated[str | None, Field(default=None, description="Whose lease to cancel, if not manager users email is utilized instead.")]
    car_name:  str
    car_id:    Annotated[int | None, Field(description="If ID is available use it before selecting with car name")]

class lease_car_req(BaseModel):
    recipient:    Annotated[str | None, Field(default=None)]
    car_id:       int
    private_ride: bool
    time_from:    Annotated[datetime | None, Field(examples=["CET time"],    default=None)]
    time_to:      Annotated[datetime | None, Field(examples=["CET time"],    default=None)]

class approve_pvr_req(BaseModel):
    approval:   bool
    request_id: int
    time_from:  Annotated[datetime | None, Field(examples=["CET time"],    default=None)]
    time_to:    Annotated[datetime | None, Field(examples=["CET time"],    default=None)]
    car_id:     int
    requester:  Annotated[str, Field(description="User who requested the private ride",  default=None)]

class return_car_req(BaseModel):
    lease_id:        int
    time_of_return:  Annotated[datetime | None, Field(examples=["CET time"],    default=None)]
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
    role:  Annotated[str, Field(examples=["manager", "user", "admin"])]
    email: str

class user_list_response(BaseModel):
    """ A list of all users and their roles in a dict. """
    users: Annotated[list[dict] | None, Field(default=None, examples=["{email: user@gamo.sk, role: manager}"])]

class single_car_response(BaseModel):
    """ Redundant function, does the same as car_info_response. """
    car_id:       int
    spz:          Annotated[str, Field(min_length=7)]
    car_type:     Annotated[str, Field(examples=['personal', 'cargo'])]
    gearbox_type: Annotated[str, Field(examples=['manual', 'automatic'])]
    fuel_type:    Annotated[str, Field(examples=['benzine','naft','diesel','electric'])]
    region:       Annotated[str, Field(examples=['local', 'global'])]
    car_status:   Annotated[str, Field(examples=['available','away','unavailable','decommissioned'])]
    seats:        Annotated[int, Field(ge=2)]
    usage_metric: int
    image_url:    str

class list_car_reponse(BaseModel):
    """ A list of car's with their status, name, spz and image. """
    car_id:     int 
    car_name:   str
    car_status: Annotated[str, Field(examples=['available','away','unavailable','decommissioned'])]
    spz:        Annotated[str | None, Field(default=None, min_length=7)]
    image_url:  str

class car_info_response(BaseModel):
    """ Every information about the requested car. """
    car_id:       int
    spz:          Annotated[str, Field(min_length=7)]
    car_type:     Annotated[str, Field(examples=['personal', 'cargo'])]
    gearbox_type: Annotated[str, Field(examples=['manual', 'automatic'])]
    fuel_type:    Annotated[str, Field(examples=['benzine','naft','diesel','electric'])]
    region:       Annotated[str, Field(examples=['local', 'global'])]
    car_status:   Annotated[str, Field(examples=['available','away','unavailable','decommissioned'])]
    seats:        Annotated[int, Field(ge=2)]
    usage_metric: int
    image_url:    str
    decommision_time: Annotated[datetime | None, Field(examples=["CET time"], default=None, description="Unless the car is decommisioned this will be None")]
    allowed_hours: Annotated[list[list[datetime, datetime]], Field(examples=["[[2025.12.3 11:30, 2025.14.3 07:00]]"], description="A list containing starting and ending times of leases bound to this car.")]

class user_info_response(BaseModel):
    """ Basic information about the requested user. """
    user_id:  int
    username: str
    email:    str
    role:     Annotated[str, Field(examples=["manager", "user", "admin", "system"])]

class report_list_response(BaseModel):
    """ Returns a list of paths to individual excel reports.\n  ['/app/reports/2025-01-21 ICLS_report.xlsx'] """
    reports: Annotated[list[str], Field(examples=["['/app/reports/2025-01-21 ICLS_report.xlsx']"], description="A list containing relative paths to the report directory. ")]

class report_single_response(BaseModel):
    """ This object is useless, as it returns the excel file as a file to be downlaoed by the browser."""
    # This should send the requested excel file as a file to donwload. So nothing is actually being sent back by the endpoint except the file
    pass

class leaseEntry(BaseModel):
    lease_id:             int
    lease_status:         Annotated[str | None, Field(examples=['created', 'scheduled', 'active', 'late', 'unconfirmed', 'returned', 'canceled', 'missing', 'aborted'],    default=None)]
    creation_time:        Annotated[datetime | None, Field(examples=["CET time"],    default=None)]
    starting_time:        Annotated[datetime | None, Field(examples=["CET time"],    default=None)]
    ending_time:          Annotated[datetime | None, Field(examples=["CET time"],    default=None)]
    approved_return_time: Annotated[datetime | None, Field(examples=["CET time"],    default=None)]
    missing_time:         Annotated[datetime | None, Field(examples=["CET time"],    default=None)]
    cancelled_time:       Annotated[datetime | None, Field(examples=["CET time"],    default=None)]
    aborted_time:         Annotated[datetime | None, Field(examples=["CET time"],    default=None)]
    driver_email:         str
    car_name:             str
    status_updated_at:    Annotated[datetime | None, Field(examples=["CET time"],    default=None)]
    last_changed_by:      str
    region_tag:           Annotated[str, Field(examples=['local', 'global'])]


class leaseListResponse(BaseModel):
    active_leases: list[leaseEntry]


class leaseCancelResponse(BaseModel):
    cancelled: bool

class monthlyLeasesResponse(BaseModel):
    start_of_lease:  Annotated[datetime | None, Field(examples=["CET time"],    default=None)]
    end_of_lease:    Annotated[datetime | None, Field(examples=["CET time"],    default=None)]
    time_of_return:  Annotated[datetime | None, Field(examples=["CET time"],    default=None)]
    lease_status:    Annotated[str | None, Field(examples=['created', 'scheduled', 'active', 'late', 'unconfirmed', 'returned', 'canceled', 'missing', 'aborted'],    default=None)]
    car_name:        str
    driver_email:    str
    note:            Annotated[str, Field(max_length=250)]

class leaseCarResponse(BaseModel):
    status:  bool
    private: bool
    msg: Annotated[str | None, Field(default=None)]

class requestEntry(BaseModel):
    request_id:     int
    starting_time:  Annotated[datetime | None, Field(examples=["CET time"],    default=None)]
    ending_time:    Annotated[datetime | None, Field(examples=["CET time"],    default=None)]
    request_status: Annotated[str, Field(examples=['pending',  'approved',  'rejected',  'cancelled'])]
    car_name:       str
    spz:            Annotated[str | None, Field(default=None, min_length=7)]
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
    return {"message": "Hello"}

@app.post("/logout", response_model=DefaultResponse)
async def logout(authorization: str = Header(None)):
    """Logout endpoint to revoke JWT token"""
    pass

@app.post("/register", response_model=DefaultResponse)
async def register(request: RegisterRequest, authorization: str = Header(None)):
    """Register a new user (admin only)"""
    pass

@app.post("/login", response_model=login_response)
async def login(request: login_obj):
    """Login endpoint for user authentication"""
    pass

@app.post("/edit_user", response_model=DefaultResponse)
async def edit_user(request: user_edit_req, authorization: str = Header(None)):
    """Edit user information (admin only)"""
    pass

@app.post("/create_car", response_model=DefaultResponse)
async def create_car(request: car_creation_req, authorization: str = Header(None)):
    """Create a new car (admin only)"""
    pass

@app.post("/edit_car", response_model=DefaultResponse)
async def edit_car(request: car_editing_req, authorization: str = Header(None)):
    """Edit car information (admin only)"""
    pass

@app.post("/delete_car", response_model=DefaultResponse)
async def delete_car(request: car_deletion_req, authorization: str = Header(None)):
    """Delete a car (admin only)"""
    pass

@app.post("/delete_user", response_model=DefaultResponse)
async def delete_user(request: user_deletion_req, authorization: str = Header(None)):
    """Delete a user (admin only)"""
    pass

@app.get("/get_users", response_model=user_list_response)
async def get_users(authorization: str = Header(None)):
    """Get list of all users (manager/admin only)"""
    pass

@app.post("/get_single_car", response_model=single_car_response)
async def get_single_car(request: single_car_req, authorization: str = Header(None)):
    """Get detailed information about a single car"""
    pass

@app.get("/get_car_list", response_model=list[list_car_reponse])
async def get_car_list(authorization: str = Header(None)):
    """Get list of all cars with basic information"""
    pass

@app.post("/decommision_car", response_model=DefaultResponse)
async def decommision_car(request: car_decommision_req, authorization: str = Header(None)):
    """Decommission a car for maintenance (manager/admin only)"""
    pass

@app.post("/activate_car", response_model=DefaultResponse)
async def activate_car(request: car_activation_req, authorization: str = Header(None)):
    """Activate a decommissioned car (manager/admin only)"""
    pass

@app.post("/get_full_car_info", response_model=car_info_response)
async def get_full_car_info(request: car_information_req, authorization: str = Header(None)):
    """Get complete car information including availability"""
    pass

@app.post("/get_all_car_info", response_model=list[car_info_response])
async def get_all_car_info(authorization: str = Header(None)):
    """Get information about all cars (admin only)"""
    pass

@app.post("/get_all_user_info", response_model=list[user_info_response])
async def get_all_user_info(authorization: str = Header(None)):
    """Get information about all users (admin only)"""
    pass

@app.post("/list_reports", response_model=report_list_response)
async def list_reports(authorization: str = Header(None)):
    """List available reports (manager/admin only)"""
    pass

@app.get("/get_report/{filename}")
async def get_report(filename: str, authorization: str = Header(None)):
    """Download a specific report file (manager/admin only)"""
    pass

@app.post("/get_leases", response_model=leaseListResponse)
async def get_leases(request: leases_list_req, authorization: str = Header(None)):
    """Get list of leases with optional filtering"""
    pass

@app.post("/cancel_lease", response_model=leaseCancelResponse)
async def cancel_lease(request: cancel_lease_req, authorization: str = Header(None)):
    """Cancel an active lease"""
    pass

@app.post("/get_monthly_leases", response_model=list[monthlyLeasesResponse])
async def get_monthly_leases(request: monthly_leases_req, authorization: str = Header(None)):
    """Get leases for a specific month (manager/admin only)"""
    pass

@app.post("/lease_car", response_model=leaseCarResponse)
async def lease_car(request: lease_car_req, authorization: str = Header(None)):
    """Create a new lease for a car"""
    pass

@app.post("/get_requests", response_model=requestListResponse)
async def get_requests(authorization: str = Header(None)):
    """Get pending private ride requests (manager/admin only)"""
    pass

@app.post("/approve_req", response_model=DefaultResponse)
async def approve_request(request: approve_pvr_req, authorization: str = Header(None)):
    """Approve or reject a private ride request (manager/admin only)"""
    pass

@app.post("/return_car", response_model=DefaultResponse)
async def return_car(request: return_car_req, authorization: str = Header(None)):
    """Return a leased car"""
    pass

@app.get("/notifications", response_model=list[dict])
async def get_notifications(authorization: str = Header(None)):
    """Get user notifications"""
    pass

@app.post("/notifications/mark-as-read", response_model=DefaultResponse)
async def mark_notification_as_read(request: read_notification_req, authorization: str = Header(None)):
    """Mark a notification as read"""
    pass

@app.post("/check_token", response_model=DefaultResponse)
async def check_token(authorization: str = Header(None)):
    """Validate JWT token"""
    pass

