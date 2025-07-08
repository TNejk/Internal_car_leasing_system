import pytz
import os
import jwt
from pathlib import Path
from fastapi import FastAPI, Query, HTTPException, Header, status, Depends
from pydantic import BaseModel, Field
from typing import Annotated, Optional
from datetime import datetime, timedelta, timezone
from dateutil.parser import parse
from typing import Annotated
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jwt.exceptions import InvalidTokenError
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from db.database import SessionLocal
import db.models as model
from db.enums import *


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
    car_image:  Annotated[str, Field(description=".jpg or .png only")]

class car_editing_req(BaseModel):
    car_name:   Annotated[str | None, Field(default=None)]
    car_type:   Annotated[str | None, Field(default=None, examples=["personal", "cargo"])]
    car_status: Annotated[str | None, Field(default=None, examples=['available','away','unavailable','decommissioned'])]
    spz:        Annotated[str | None, Field(default=None, min_length=7)]
    gas_type:   Annotated[str | None, Field(default=None, examples=['benzine','naft','diesel','electric'])]
    drive_type: Annotated[str | None, Field(default=None, examples=['manual','automatic'])]
    car_image:  Annotated[str | None, Field(default=None)]

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
    private_trip: bool
    trip_participants: Annotated[list[str] | None, Field(examples=["['user@gamo.sk', 'user2@gamo.sk']"], default=None)] 
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

class trip_join_request_req(BaseModel):
    trip_id: int

class trip_invite_response_req(BaseModel):
    invite_id: int
    accepted: bool

class trip_join_response_req(BaseModel):
    request_id: int
    approved: bool

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

class tripEntry(BaseModel):
    trip_id: int
    trip_name: str
    creator_email: str
    car_name: str
    is_public: bool
    status: Annotated[str, Field(examples=['scheduled', 'active', 'completed', 'cancelled'])]
    free_seats: int
    destination_name: str
    destination_lat: float
    destination_lon: float
    created_at: Annotated[datetime, Field(examples=["CET time"])]

class tripListResponse(BaseModel):
    trips: list[tripEntry]

class tripJoinRequestEntry(BaseModel):
    request_id: int
    trip_id: int
    user_email: str
    status: Annotated[str, Field(examples=['pending', 'accepted', 'rejected'])]
    requested_at: Annotated[datetime, Field(examples=["CET time"])]

class tripJoinRequestListResponse(BaseModel):
    join_requests: list[tripJoinRequestEntry]

class tripInviteEntry(BaseModel):
    invite_id: int
    trip_id: int
    user_email: str
    status: Annotated[str, Field(examples=['pending', 'accepted', 'rejected'])]
    invited_at: Annotated[datetime, Field(examples=["CET time"])]

class tripInviteListResponse(BaseModel):
    invites: list[tripInviteEntry]

#######################################################
#                   UTILITY MODELS                    #
#######################################################
USER_ROLES = {
    "user",
    "manager",
    "admin",
    "system"
}

bratislava_tz = pytz.timezone('Europe/Bratislava')


def admin_or_manager(role: str):
    if role == "manager" or role == "admin": 
        return True
    return False

class Token(BaseModel):
    JWT: str
    token_type: str

class TokenData(BaseModel):
    email: str
    role:  Annotated[str, Field(examples=["manager", "user", "admin", "system"])]

class User(BaseModel):
    email: str
    role: Annotated[str, Field(examples=["manager", "user", "admin", "system"])]
    username: str  # This maps to name in the database
    disabled: bool # This maps to is_deleted in the database

    class Config:
        from_attributes = True  # Allows conversion from SQLAlchemy model

class Car(BaseModel):
    car_id: int
    plate_number: str
    name: str
    category: str
    gearbox_type: str
    fuel_type: str
    region: str
    status: str
    seats: int
    usage_metric: int
    img_url: str
    created_at: datetime
    is_deleted: bool

    class Config:
        from_attributes = True

def convert_to_datetime(string):
    try:
        # Parse string, handling timezone if present
        dt_obj = datetime.strptime(string, "%Y-%m-%d %H:%M:%S")
        return dt_obj
    except: #? Ok now bear with me, it may look stupid, be stupid and make me look stupid, but it works :) Did i mention how much i hate dates
        try:
            dt_obj = datetime.strptime(string, "%Y-%m-%d %H:%M")
            return dt_obj
        except ValueError as e:
            raise ValueError(f"Invalid datetime format: {string}") from e
        

def ten_minute_tolerance(a_timeof, today):
    """ Gives user 10 minutes ofleaniency to lease a car before a lease from the past error. """
    timeof = convert_to_datetime(string=a_timeof)
    diff = today - timeof
    if (diff.total_seconds()/60) >= 10:
        return True

def get_sk_date():
    # Ensure the datetime is in UTC before converting
    dt_obj = datetime.now()
    utc_time = dt_obj.replace(tzinfo=pytz.utc) if dt_obj.tzinfo is None else dt_obj.astimezone(pytz.utc)
    bratislava_time = utc_time.astimezone(bratislava_tz)  # Convert to Bratislava timezone
    return bratislava_time

#######################################################
#                 APP INITIALIZATION                  #
#######################################################

SECRET_KEY = os.environ.get('SECRET_KEY')
ALGORITHM = "HS256"
TOKEN_EXPIRATION_MINUTES = 30


pwd_context = CryptContext(schemes=["bcrypt"], deprecated ="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

#! app = FastAPI(docs_url=None, redoc_url=None)
#! 
# V produkcií, nenechať otvorenú dokumentáciu svetu!!
app = FastAPI()

def connect_to_db():
    # Get the running session from sqlalchemy's engine
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def authenticate_user(email: str, password: str, db: Session) -> User:
    """Checks if the user exists and verifies password"""
    # Query the SQLAlchemy Users model
    db_user = db.query(model.Users).filter(
        model.Users.email == email,
        model.Users.is_deleted == False
    ).first()

    if not db_user:
        return None
    
    if not verify_password(password, db_user.password):
        return None

    # Convert SQLAlchemy model to Pydantic model
    return User(
        email=db_user.email,
        role=db_user.role.value,  # Since role is an Enum
        username=db_user.name,    # Using name as username
        disabled=db_user.is_deleted
    )

#* data is a dictionary of all metadata we want, if the expire date is not specified its set at 15 minutes
def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def get_existing_user(email: str, role: str, db: Session) -> User:
    """Check in the database for a non-deleted user that matches the email role combo"""
    db_user = db.query(model.Users).filter(
        model.Users.email == email,
        model.Users.role == role,
        model.Users.is_deleted == False
    ).first()

    if not db_user:
        return None
    
    return User(
        email=db_user.email,
        role=db_user.role.value,
        username=db_user.name,
        disabled=db_user.is_deleted
    )

def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Session = Depends(connect_to_db)
) -> User:
    cred_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Error validating credentials",
        headers={"WWW-Authenticate": "Bearer"}
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        role = payload.get("role")
        if email is None or role is None:
            raise cred_exception
        token_data = TokenData(email=email, role=role)
    
    except InvalidTokenError:
        raise cred_exception

    user = get_existing_user(email=email, role=role, db=db)
    if not user:
        raise cred_exception
    return user



#######################################################
#                  ENDPOINTS SECTION                  #
#######################################################

@app.get("jjj")
async def hi():
    return {"msg": "gheloo"}


@app.post("/v2/logout", response_model=DefaultResponse)
async def logout(current_user: Annotated[User, Depends(get_current_user)]):
    """Logout endpoint to revoke JWT token"""
    pass

@app.post("/v2/register", response_model=DefaultResponse)
async def register(request: RegisterRequest, current_user: Annotated[User, Depends(get_current_user)]):
    """Register a new user (admin only)"""
    
    http_exception = HTTPException(status_code=401, detail="Unauthorized.")
    
    if admin_or_manager() == False:
        return http_exception



    
    pass


@app.post("/v2/login", response_model=login_response)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Session = Depends(connect_to_db)):
    """ Login user to app, returns a login_response obj that includes a token and role email combo. """
    user = authenticate_user(
        email=form_data.username, 
        password=form_data.password,
        db=db
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Wrong username or password",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    access_token = create_access_token(
        data={"sub": user.email, "role": user.role},
        expires_delta=timedelta(minutes=TOKEN_EXPIRATION_MINUTES)
    )
    
    return login_response(
        token=access_token,
        email=user.email,
        role=user.role
    )


@app.post("/v2/edit_user", response_model=DefaultResponse)
async def edit_user(request: user_edit_req, current_user: Annotated[User, Depends(get_current_user)]):
    """Edit user information (admin only)"""
    
    pass

@app.post("/v2/create_car", response_model=DefaultResponse)
async def create_car(request: car_creation_req, current_user: Annotated[User, Depends(get_current_user)]):
    """Create a new car (admin only)"""
    pass

@app.post("/v2/edit_car", response_model=DefaultResponse)
async def edit_car(request: car_editing_req, current_user: Annotated[User, Depends(get_current_user)]):
    """Edit car information (admin only)"""
    pass

@app.post("/v2/delete_car", response_model=DefaultResponse)
async def delete_car(request: car_deletion_req, current_user: Annotated[User, Depends(get_current_user)]):
    """Delete a car (admin only)"""
    pass

@app.post("/v2/delete_user", response_model=DefaultResponse)
async def delete_user(request: user_deletion_req, current_user: Annotated[User, Depends(get_current_user)]):
    """Delete a user (admin only)"""
    pass

@app.get("/v2/get_users", response_model=user_list_response)
async def get_users(current_user: Annotated[User, Depends(get_current_user)]):
    """Get list of all users (manager/v2/admin only)"""
    pass

@app.post("/v2/get_single_car", response_model=single_car_response)
async def get_single_car(request: single_car_req, current_user: Annotated[User, Depends(get_current_user)]):
    """Get detailed information about a single car"""
    pass

@app.get("/v2/get_car_list", response_model=list[list_car_reponse])
async def get_car_list(
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Get list of all cars with basic information"""
    pass

@app.post("/v2/decommision_car", response_model=DefaultResponse)
async def decommision_car(request: car_decommision_req, current_user: Annotated[User, Depends(get_current_user)]):
    """Decommission a car for maintenance (manager/v2/admin only)"""
    pass

@app.post("/v2/activate_car", response_model=DefaultResponse)
async def activate_car(request: car_activation_req, current_user: Annotated[User, Depends(get_current_user)]):
    """Activate a decommissioned car (manager/v2/admin only)"""
    pass

@app.post("/v2/get_full_car_info", response_model=car_info_response)
async def get_full_car_info(request: car_information_req, current_user: Annotated[User, Depends(get_current_user)]):
    """Get complete car information including availability"""
    pass

@app.post("/v2/get_all_car_info", response_model=list[car_info_response])
async def get_all_car_info(current_user: Annotated[User, Depends(get_current_user)]):
    """Get information about all cars (admin only)"""
    pass

@app.post("/v2/get_all_user_info", response_model=list[user_info_response])
async def get_all_user_info(current_user: Annotated[User, Depends(get_current_user)]):
    """Get information about all users (admin only)"""
    pass

@app.post("/v2/list_reports", response_model=report_list_response)
async def list_reports(current_user: Annotated[User, Depends(get_current_user)]):
    """List available reports (manager/v2/admin only)"""
    pass

@app.get("/v2/get_report/v2/{filename}")
async def get_report(filename: str, current_user: Annotated[User, Depends(get_current_user)]):
    """Download a specific report file (manager/v2/admin only)"""
    pass

@app.post("/v2/get_leases", response_model=leaseListResponse)
async def get_leases(request: leases_list_req, current_user: Annotated[User, Depends(get_current_user)]):
    """Get list of leases with optional filtering"""
    pass

@app.post("/v2/cancel_lease", response_model=leaseCancelResponse)
async def cancel_lease(request: cancel_lease_req, current_user: Annotated[User, Depends(get_current_user)]):
    """Cancel an active lease"""
    pass

@app.post("/v2/get_monthly_leases", response_model=list[monthlyLeasesResponse])
async def get_monthly_leases(request: monthly_leases_req, current_user: Annotated[User, Depends(get_current_user)]):
    """Get leases for a specific month (manager/v2/admin only)"""
    pass

@app.post("/v2/lease_car", response_model=leaseCarResponse)
async def lease_car(request: lease_car_req, current_user: Annotated[User, Depends(get_current_user)], db: Session = Depends(connect_to_db)):
    """Create a lease for a car and optionally create a trip with participants"""
    try:
        car_id = request.car_id
        time_from = request.time_from
        time_to = request.time_to
        recipient = request.recipient or current_user.email
        private_ride = request.private_ride
        private_trip = request.private_trip
        trip_participants = request.trip_participants or []
        
        # Check privilege
        has_privilege = admin_or_manager(current_user.role)

        # Check if leasing for someone else
        if current_user.email != recipient:
            if not has_privilege:
                raise HTTPException(
                    status_code=401,
                    detail="Unauthorized lease.",
                    headers={"WWW-Authenticate": "Bearer"}
                )
        
        # Date validation
        if not time_from or not time_to:
            return ErrorResponse(msg="Time from and time to are required.", status=False)
            
        today = get_sk_date()
        
        # Convert datetime to timezone-aware if needed
        if time_to.replace(tzinfo=None) < today.replace(tzinfo=None):
            return ErrorResponse(msg=f"Nemožno rezervovať do minulosti. \nDnes: {today}\nDO: {time_to}", status=False)
        
        if ten_minute_tolerance(str(time_from), today.replace(tzinfo=None)):
            return ErrorResponse(msg=f"Nemožno rezervovať z minulosti. \nDnes: {today}\nOD: {time_from}", status=False)

        # Get car and validate availability
        car = db.query(model.Cars).filter(
            model.Cars.id == car_id,
            model.Cars.status != CarStatus.decommissioned,
            model.Cars.is_deleted == False
        ).first()
        
        if not car:
            return ErrorResponse(msg="Auto nie je dostupné alebo neexistuje.", status=False)

        # Check for conflicting leases
        conflicting_lease = db.query(model.Leases).filter(
            model.Leases.id_car == car_id,
            model.Leases.status.in_([LeaseStatus.scheduled, LeaseStatus.active]),
            ~((model.Leases.end_time <= time_from) | (model.Leases.start_time >= time_to))
        ).first()
        
        if conflicting_lease:
            return ErrorResponse(msg="Zabratý dátum (hodina typujem)", status=False)

        # Get recipient user
        recipient_user = db.query(model.Users).filter(
            model.Users.email == recipient,
            model.Users.is_deleted == False
        ).first()
        
        if not recipient_user:
            return ErrorResponse(msg="Príjemca neexistuje.", status=False)

        # If private ride and user is not manager/admin, create a request instead
        if private_ride and not has_privilege:
            # Create lease request for approval
            lease_request = model.LeaseRequests(
                id_car=car_id,
                id_user=recipient_user.id,
                start_time=time_from,
                end_time=time_to,
                status=RequestStatus.pending
            )
            db.add(lease_request)
            db.commit()
            
            # TODO: Send notification to managers
            
            return leaseCarResponse(status=True, private=True, msg="Request for a private ride was sent!")

        # Create the lease
        new_lease = model.Leases(
            id_car=car_id,
            id_user=recipient_user.id,
            start_time=time_from,
            end_time=time_to,
            status=LeaseStatus.scheduled,
            private=private_ride,
            region_tag=Regions.local  # Default to local
        )
        
        db.add(new_lease)
        db.flush()  # Get the lease ID
        
        # Update car status
        car.status = CarStatus.away
        
        # Create trip for the lease
        trip_name = f"Trip for {car.name} - {recipient}"
        new_trip = model.Trips(
            trip_name=trip_name,
            id_lease=new_lease.id,
            id_car=car_id,
            creator=recipient_user.id,
            is_public=not private_trip,
            status=TripsStatuses.scheduled,
            free_seats=car.seats - 1,  # -1 for the driver
            destination_name="Not specified",
            destination_lat=0.0,
            destination_lon=0.0
        )
        
        db.add(new_trip)
        db.flush()  # Get the trip ID
        
        # Add creator as participant
        trip_participant = model.TripsParticipants(
            id_trip=new_trip.id,
            id_user=recipient_user.id,
            seat_number=1,  # Driver seat
            trip_finished=False
        )
        db.add(trip_participant)
        
        # Send invites to trip participants if provided
        if trip_participants:
            for participant_email in trip_participants:
                participant_user = db.query(model.Users).filter(
                    model.Users.email == participant_email,
                    model.Users.is_deleted == False
                ).first()
                
                if participant_user and participant_user.id != recipient_user.id:
                    trip_invite = model.TripsInvites(
                        id_trip=new_trip.id,
                        id_user=participant_user.id,
                        status=TripsInviteStatus.pending
                    )
                    db.add(trip_invite)
                    new_trip.free_seats -= 1  # Reserve seat for invited participant
        
        db.commit()
        
        # TODO: Send notifications
        
        return leaseCarResponse(status=True, private=private_ride, msg="Lease created successfully!")
        
    except Exception as e:
        db.rollback()
        return ErrorResponse(msg=f"Error creating lease: {str(e)}", status=False)


@app.post("/v2/trips/join_request", response_model=DefaultResponse)
async def request_trip_join(request: trip_join_request_req, current_user: Annotated[User, Depends(get_current_user)], db: Session = Depends(connect_to_db)):
    """Request to join a public trip"""
    try:
        trip = db.query(model.Trips).filter(
            model.Trips.id == request.trip_id,
            model.Trips.is_public == True,
            model.Trips.status == TripsStatuses.scheduled
        ).first()
        
        if not trip:
            return DefaultResponse(status=False, msg="Trip not found or not available for joining")
        
        if trip.free_seats <= 0:
            return DefaultResponse(status=False, msg="No free seats available")
        
        user = db.query(model.Users).filter(model.Users.email == current_user.email).first()
        
        # Check if user already has a request or is already a participant
        existing_request = db.query(model.TripsJoinRequests).filter(
            model.TripsJoinRequests.id_trip == request.trip_id,
            model.TripsJoinRequests.id_user == user.id,
            model.TripsJoinRequests.status == TripsInviteStatus.pending
        ).first()
        
        if existing_request:
            return DefaultResponse(status=False, msg="You already have a pending request for this trip")
        
        existing_participant = db.query(model.TripsParticipants).filter(
            model.TripsParticipants.id_trip == request.trip_id,
            model.TripsParticipants.id_user == user.id
        ).first()
        
        if existing_participant:
            return DefaultResponse(status=False, msg="You are already a participant in this trip")
        
        # Create join request
        join_request = model.TripsJoinRequests(
            id_trip=request.trip_id,
            id_user=user.id,
            status=TripsInviteStatus.pending
        )
        
        db.add(join_request)
        db.commit()
        
        return DefaultResponse(status=True, msg="Join request sent successfully")
        
    except Exception as e:
        db.rollback()
        return DefaultResponse(status=False, msg=f"Error sending join request: {str(e)}")


@app.post("/v2/trips/respond_invite", response_model=DefaultResponse)
async def respond_trip_invite(request: trip_invite_response_req, current_user: Annotated[User, Depends(get_current_user)], db: Session = Depends(connect_to_db)):
    """Accept or reject a trip invite"""
    try:
        user = db.query(model.Users).filter(model.Users.email == current_user.email).first()
        
        invite = db.query(model.TripsInvites).filter(
            model.TripsInvites.id == request.invite_id,
            model.TripsInvites.id_user == user.id,
            model.TripsInvites.status == TripsInviteStatus.pending
        ).first()
        
        if not invite:
            return DefaultResponse(status=False, msg="Invite not found or already responded")
        
        trip = db.query(model.Trips).filter(model.Trips.id == invite.id_trip).first()
        
        if request.accepted:
            if trip.free_seats <= 0:
                return DefaultResponse(status=False, msg="No free seats available")
            
            # Accept invite - add as participant
            invite.status = TripsInviteStatus.accepted
            
            # Find next available seat number
            existing_participants = db.query(model.TripsParticipants).filter(
                model.TripsParticipants.id_trip == invite.id_trip
            ).all()
            
            used_seats = [p.seat_number for p in existing_participants]
            seat_number = 2  # Start from 2 (driver is seat 1)
            while seat_number in used_seats:
                seat_number += 1
            
            participant = model.TripsParticipants(
                id_trip=invite.id_trip,
                id_user=user.id,
                seat_number=seat_number,
                trip_finished=False
            )
            
            db.add(participant)
            trip.free_seats -= 1
            
        else:
            # Reject invite
            invite.status = TripsInviteStatus.rejected
        
        db.commit()
        
        status_msg = "Invite accepted" if request.accepted else "Invite rejected"
        return DefaultResponse(status=True, msg=status_msg)
        
    except Exception as e:
        db.rollback()
        return DefaultResponse(status=False, msg=f"Error responding to invite: {str(e)}")


@app.get("/v2/trips", response_model=tripListResponse)
async def get_trips(current_user: Annotated[User, Depends(get_current_user)], db: Session = Depends(connect_to_db)):
    """Get list of available trips"""
    try:
        user = db.query(model.Users).filter(model.Users.email == current_user.email).first()
        
        # Get public trips and trips created by the user
        trips = db.query(model.Trips).filter(
            (model.Trips.is_public == True) | (model.Trips.creator == user.id),
            model.Trips.status == TripsStatuses.scheduled
        ).all()
        
        trip_list = []
        for trip in trips:
            creator = db.query(model.Users).filter(model.Users.id == trip.creator).first()
            car = db.query(model.Cars).filter(model.Cars.id == trip.id_car).first()
            
            trip_list.append(tripEntry(
                trip_id=trip.id,
                trip_name=trip.trip_name,
                creator_email=creator.email,
                car_name=car.name,
                is_public=trip.is_public,
                status=trip.status.value,
                free_seats=trip.free_seats,
                destination_name=trip.destination_name,
                destination_lat=float(trip.destination_lat),
                destination_lon=float(trip.destination_lon),
                created_at=trip.created_at
            ))
        
        return tripListResponse(trips=trip_list)
        
    except Exception as e:
        return tripListResponse(trips=[])


@app.post("/v2/get_requests", response_model=requestListResponse)
async def get_requests(current_user: Annotated[User, Depends(get_current_user)]):
    """Get pending private ride requests (manager/v2/admin only)"""
    pass

@app.post("/v2/approve_req", response_model=DefaultResponse)
async def approve_request(request: approve_pvr_req, current_user: Annotated[User, Depends(get_current_user)]):
    """Approve or reject a private ride request (manager/v2/admin only)"""
    pass

@app.post("/v2/return_car", response_model=DefaultResponse)
async def return_car(request: return_car_req, current_user: Annotated[User, Depends(get_current_user)]):
    """Return a leased car"""
    pass

@app.get("/v2/notifications", response_model=list[dict])
async def get_notifications(current_user: Annotated[User, Depends(get_current_user)]):
    """Get user notifications"""
    pass

@app.post("/v2/notifications/v2/mark-as-read", response_model=DefaultResponse)
async def mark_notification_as_read(request: read_notification_req, current_user: Annotated[User, Depends(get_current_user)]):
    """Mark a notification as read"""
    pass

@app.post("/v2/check_token", response_model=DefaultResponse)
async def check_token(current_user: Annotated[User, Depends(get_current_user)]):
    """Validate JWT token"""
    pass

