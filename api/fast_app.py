import pytz
import os
import jwt
from pathlib import Path
from fastapi import FastAPI, Query, HTTPException, Header, status, Depends
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from typing import Annotated, Optional
from datetime import datetime, timedelta, timezone
from dateutil.parser import parse
from typing import Annotated
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jwt.exceptions import InvalidTokenError
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from dotenv import load_dotenv
load_dotenv()
from db.database import SessionLocal
import db.models as model
from db.enums import *
import models.request as moreq
import models.response as mores

regreq = moreq.RegisterRequest
print(regreq)
##################################################################
#                   Default multi use models                     #
##################################################################
class ErrorResponse(BaseModel):
    status: bool
    msg: str

# used for every endpoint with a simple true false response
class DefaultResponse(BaseModel):
    status: bool
    msg: Annotated[str | None, Field(default=None)]



#######################################################
#                   UTILITY MODELS                    #
#######################################################
USER_ROLES = [
    "user",
    "manager",
    "admin",
    "system"
]

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

def find_reports_directory():
    """Find the reports directory at the volume mount location."""
    reports_path = "/app/reports"
        
    if os.path.exists(reports_path) and os.path.isdir(reports_path):
        print(f"DEBUG: Found reports directory at: {reports_path}")
        # List contents of reports directory
        try:
            print(f"DEBUG: Contents of reports directory:")
            for item in os.listdir(reports_path):
                item_path = os.path.join(reports_path, item)
                print(f"DEBUG:   {item} ({'dir' if os.path.isdir(item_path) else 'file'})")
        except Exception as e:
            print(f"DEBUG: Error listing reports directory: {e}")
        return reports_path
    
    print("ERROR: /app/reports directory not found - check Docker volume mount")
    print("HINT: Volume should be: -v /home/systemak/icls/api/reports:/app/reports")
    return None

def get_reports_paths(folder_path):  
    """Get list of report file paths relative to the reports directory."""
    try:  
        with os.scandir(folder_path) as entries:  
            return [entry.path.removeprefix("/app/reports/") for entry in entries if entry.is_file()]  
    except OSError:  # Specific exception > bare except!  
        return None

#################################################################
#                    API RESPONSE MODELS                        #
#################################################################


class user_list_response(BaseModel):
  """ A list of all users and their roles in a dict. """
  users: Annotated[list[User] | None, Field(default=None, examples=["{email: user@gamo.sk, role: manager}"])]

# class single_car_response(BaseModel):
#     """ Redundant function, does the same as car_info_response. """
#     car_id:       int
#     spz:          Annotated[str, Field(min_length=7)]
#     car_type:     Annotated[str, Field(examples=['personal', 'cargo'])]
#     gearbox_type: Annotated[str, Field(examples=['manual', 'automatic'])]
#     fuel_type:    Annotated[str, Field(examples=['benzine','naft','diesel','electric'])]
#     region:       Annotated[str, Field(examples=['local', 'global'])]
#     car_status:   Annotated[str, Field(examples=['available','away','unavailable','decommissioned'])]
#     seats:        Annotated[int, Field(ge=2)]
#     usage_metric: int
#     image_url:    str

class list_car_reponse(BaseModel):
    """ A list of car's with their status, name, spz and image. """
    car_id:     int 
    car_name:   str
    car_status: Annotated[str, Field(examples=['available','away','unavailable','decommissioned'])]
    spz:        Annotated[str | None, Field(default=None, min_length=7)]
    seats: int
    gearbox_type: GearboxTypes
    fuel_type: FuelTypes
    usage_metric: int
    type: CarTypes
    image_url:  str

class carListResponse(BaseModel):
    car_list: list[list_car_reponse]

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
    type: CarTypes
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
async def register(request: moreq.RegisterRequest, current_user: Annotated[User, Depends(get_current_user)]):
    """Register a new user (admin only)"""
    
    http_exception = HTTPException(status_code=401, detail="Unauthorized.")
    
    if not admin_or_manager(current_user.role):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized access. Admin or manager role required.",
            headers={"WWW-Authenticate": "Bearer"}
        )



    
    pass


@app.post("/v2/login", response_model=mores.LoginResponse)
async def login(form_data: Annotated[OAuth2PasswordRequestForm, Depends()], db: Session = Depends(connect_to_db)):

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
async def edit_user(request: moreq.UserEditReq, current_user: Annotated[User, Depends(get_current_user)]):
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
    
    session = connect_to_db()

    if not session:
        return HTTPException(
            status_code=500,
            detail="Error getting users!",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # Get all users, that are not disabled
    users = session.query(model.Users).filter(
        model.Users.is_deleted == False,
        model.Users.role != UserRoles.admin
    ).all()

    user_list = []
    for user in users:
        user_list.append(
            User(
                email= user.email,
                username= user.name,
                role= user.role,
                disabled= user.is_deleted
            )
        )

    return user_list_response(
        users= user_list
    )


    

@app.get("/v2/get_car_list", response_model=carListResponse)
async def get_car_list(
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Get list of all cars with basic information"""
    session = connect_to_db()

    cars = session.query(model.Cars).filter(
            model.Cars.is_deleted == False,
            model.Cars.status != CarStatus.unavailable,
    ).order_by(model.Cars.usage_metric.asc()).all()


    list_car = []        
    for car in cars:
        list_car.append(
            list_car_reponse(
                car_id= car.id,
                car_name= car.name,
                car_status=  car.status,
                gearbox_type = car.gearbox_type,
                fuel_type = car.fuel_type,
                type= car.category,
                spz= car.plate_number,
                seats= car.seats,
                usage_metric = car.usage_metric,
                image_url= car.img_url
            )
        )
    
    return carListResponse(
        car_list= list_car
    )


    

@app.post("/v2/decommission_car", response_model=DefaultResponse)
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
async def get_all_car_info(current_user: Annotated[User, Depends(get_current_user)], db: Session = Depends(connect_to_db)):
    """Get information about all cars (admin only)"""
    
    # Check if user is admin
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized access. Admin role required.",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    try:
        cars = db.query(model.Cars).filter(
            model.Cars.is_deleted == False
        ).all()
        
        if not cars:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No cars found"
            )
        
        car_info_list = []
        
        for car in cars:
            # Get decommission time - set to None for now since DecommissionedCars model doesn't exist
            # TODO: IMPLEMENT DECOMMISSION TIME IN THE TABLE!! iTS NEEDED FOR AUTOMATIC CAR ACTIVATION
            decommission_time = None
            
            # Get allowed hours (active leases and requests)
            allowed_hours = []
            
            active_leases = db.query(model.Leases).filter(
                model.Leases.id_car == car.id,
                model.Leases.status.in_([LeaseStatus.scheduled, LeaseStatus.active])
            ).all()
            
            for lease in active_leases:
                allowed_hours.append([lease.start_time, lease.end_time])
            
            # Get active private ride requests for this car
            active_requests = db.query(model.LeaseRequests).filter(
                model.LeaseRequests.id_car == car.id,
                model.LeaseRequests.status == RequestStatus.pending
            ).all()
            
            for request in active_requests:
                allowed_hours.append([request.start_time, request.end_time])
            
            car_info_list.append(car_info_response(
                car_id=car.id,
                spz=car.plate_number,
                car_type=car.category.value,
                gearbox_type=car.gearbox_type.value,
                fuel_type=car.fuel_type.value,
                region=car.region.value,
                car_status=car.status.value,
                seats=car.seats,
                type=car.category,
                usage_metric=car.usage_metric,
                image_url=car.img_url,
                decommision_time=decommission_time,
                allowed_hours=allowed_hours
            ))
        
        return car_info_list
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving car information: {str(e)}"
        )

@app.post("/v2/get_all_user_info", response_model=list[user_info_response])
async def get_all_user_info(current_user: Annotated[User, Depends(get_current_user)], db: Session = Depends(connect_to_db)):
    """Get information about all users (admin only)"""
    
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized access. Admin role required.",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    try:
        # Get all non-deleted users except admin users
        users = db.query(model.Users).filter(
            model.Users.is_deleted == False,
            model.Users.name != 'admin' 
        ).all()
        
        if not users:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No users found"
            )
        
        user_info_list = []
        
        for user in users:
            user_info_list.append(user_info_response(
                user_id=user.id,
                username=user.name,
                email=user.email,
                role=user.role.value
            ))
        
        return user_info_list
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving user information: {str(e)}"
        )

@app.post("/v2/list_reports", response_model=report_list_response)
async def list_reports(current_user: Annotated[User, Depends(get_current_user)], db: Session = Depends(connect_to_db)):
    """List available reports (manager/admin only)"""
    
    if not admin_or_manager(current_user.role):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized access",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    db_user = db.query(model.Users).filter(
        model.Users.email == current_user.email,
        model.Users.role.in_([UserRoles.manager, UserRoles.admin]),
        model.Users.is_deleted == False
    ).first()
    
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User verification failed"
        )
    
    try:
        reports_dir = find_reports_directory()
        if not reports_dir:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Reports directory not found"
            )
        
        report_paths = get_reports_paths(reports_dir)
        if report_paths is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error accessing reports directory"
            )
        
        return report_list_response(reports=report_paths)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing reports: {str(e)}"
        )

@app.get("/v2/get_report/v2/{filename}")
async def get_report(filename: str, current_user: Annotated[User, Depends(get_current_user)], db: Session = Depends(connect_to_db)):
    """Download a specific report file (manager/admin only)"""

    if not admin_or_manager(current_user.role):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized access",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    db_user = db.query(model.Users).filter(
        model.Users.email == current_user.email,
        model.Users.role.in_([UserRoles.manager, UserRoles.admin]),
        model.Users.is_deleted == False
    ).first()
    
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid authorization"
        )
    
    try:
        reports_dir = find_reports_directory()
        if not reports_dir:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Reports directory not found"
            )
        
        safe_path = os.path.join(reports_dir, filename)
        
        # Security check to prevent path traversal attacks
        if not os.path.realpath(safe_path).startswith(os.path.realpath(reports_dir)):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid file path"
            )
        
        if not os.path.isfile(safe_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found"
            )
        
        return FileResponse(
            path=safe_path,
            filename=filename,
            media_type='application/octet-stream'
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error accessing file: {str(e)}"
        )

@app.post("/v2/get_leases", response_model=leaseListResponse)
async def get_leases(request: leases_list_req, current_user: Annotated[User, Depends(get_current_user)], db: Session = Depends(connect_to_db)):
    """Get list of leases with optional filtering"""
    try:
        # Build base query with joins
        query = db.query(model.Leases).join(
            model.Users, model.Leases.id_user == model.Users.id
        ).join(
            model.Cars, model.Leases.id_car == model.Cars.id
        ).filter(
            model.Users.is_deleted == False,
            model.Cars.is_deleted == False
        )
        
        # Role-based filtering
        if current_user.role == model.UserRoles.user:
            # Users can only see their own leases
            query = query.filter(model.Users.email == current_user.email)
        elif current_user.role in [model.UserRoles.manager, model.UserRoles.admin]:
            # Managers and admins can filter by email if provided
            if request.filter_email:
                query = query.filter(model.Users.email == request.filter_email)
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        
        # Apply optional filters
        if request.filter_car_id:
            query = query.filter(model.Leases.id_car == request.filter_car_id)
            
        if request.filter_time_from:
            query = query.filter(model.Leases.start_time >= request.filter_time_from)
            
        if request.filter_time_to:
            query = query.filter(model.Leases.end_time <= request.filter_time_to)
            
        # Status filtering - map boolean filters to enum values
        status_filters = []
        if request.filter_active_leases:
            # Active leases include: scheduled, active, late
            status_filters.extend([LeaseStatus.scheduled, LeaseStatus.active, LeaseStatus.late])
        if request.filter_incactive_leases:
            # Inactive leases include: returned, canceled, missing, aborted
            status_filters.extend([LeaseStatus.returned, LeaseStatus.canceled, LeaseStatus.missing, LeaseStatus.aborted])
        
        # If neither filter is specified, show all lease statuses
        if not request.filter_active_leases and not request.filter_incactive_leases:
            # Show all statuses
            pass
        elif status_filters:
            query = query.filter(model.Leases.status.in_(status_filters))
        
        # Execute query with ordering
        leases = query.order_by(model.Leases.start_time.desc()).all()
        
        # Build response
        lease_entries = []
        for lease in leases:
            # Get last changed by user info
            last_changed_by_name = ""
            if lease.last_changed_by:
                changed_by_user = db.query(model.Users).filter(
                    model.Users.id == lease.last_changed_by
                ).first()
                if changed_by_user:
                    last_changed_by_name = changed_by_user.email
            
            lease_entries.append(leaseEntry(
                lease_id=lease.id,
                lease_status=lease.status.value,
                creation_time=lease.create_time,
                starting_time=lease.start_time,
                ending_time=lease.end_time,
                approved_return_time=lease.return_time,
                missing_time=lease.missing_time,
                cancelled_time=lease.canceled_time,
                aborted_time=lease.aborted_time,
                driver_email=lease.user.email,
                car_name=lease.car.name,
                status_updated_at=lease.status_updated_at,
                last_changed_by=last_changed_by_name,
                region_tag=lease.region_tag.value
            ))
        
        return leaseListResponse(active_leases=lease_entries)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving leases: {str(e)}"
        )

@app.post("/v2/cancel_lease", response_model=leaseCancelResponse)
async def cancel_lease(request: cancel_lease_req, current_user: Annotated[User, Depends(get_current_user)], db: Session = Depends(connect_to_db)):
    """Cancel an active lease"""
    try:
        # Determine whose lease to cancel
        recipient_email = request.recipient or current_user.email
        
        # Permission check: only managers and admins can cancel other people's leases
        if recipient_email != current_user.email:
            if admin_or_manager(current_user.role) == False:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient permissions to cancel another user's lease"
                )
        
        # Find the recipient user
        recipient_user = db.query(model.Users).filter(
            model.Users.email == recipient_email,
            model.Users.is_deleted == False
        ).first()
        
        if not recipient_user:
            return leaseCancelResponse(cancelled=False)
        
        # Find the car - use either car_id or car_name
        car = None
        if request.car_id:
            car = db.query(model.Cars).filter(
                model.Cars.id == request.car_id,
                model.Cars.is_deleted == False
            ).first()
        elif request.car_name:
            car = db.query(model.Cars).filter(
                model.Cars.name == request.car_name,
                model.Cars.is_deleted == False
            ).first()
        
        if not car:
            return leaseCancelResponse(cancelled=False)

        active_lease = db.query(model.Leases).filter(
            model.Leases.id_user == recipient_user.id,
            model.Leases.id_car == car.id,
            model.Leases.id == request.lease_id,
            model.Leases.status.in_([LeaseStatus.scheduled, LeaseStatus.active])
        ).order_by(model.Leases.id.desc()).first()
        
        if not active_lease:
            return leaseCancelResponse(cancelled=False)
        
        # Get current user for tracking changes
        current_user_db = db.query(model.Users).filter(
            model.Users.email == current_user.email
        ).first()
        
        # Cancel the lease
        old_status = active_lease.status
        active_lease.status = LeaseStatus.canceled
        active_lease.canceled_time = get_sk_date()
        active_lease.status_updated_at = get_sk_date()
        active_lease.last_changed_by = current_user_db.id if current_user_db else None
        
        # TODO: CHECK IF WE EVEN WANT TO DO THIS
        # AS THE CAR CAN BE LEASED INTO THE FUTURE AND THEN CANCELLED
        # WE SHOULD NOT CHANGE THE CAR STATUS TO AVAILABLE, as its kinda redundant
        #car.status = CarStatus.available
        
        # Create change log entry
        change_log = model.LeaseChangeLog(
            id_lease=active_lease.id,
            changed_by=current_user_db.id if current_user_db else None,
            previous_status=old_status,
            new_status=LeaseStatus.canceled,
            note=f"Lease cancelled by {current_user.email}"
        )
        db.add(change_log)
        
        # Send notification if manager/admin is cancelling for someone else
        if (current_user.role in [model.UserRoles.manager, model.UserRoles.admin] and 
            current_user.email != recipient_email):
            
            # TODO: Implement notification system for FastAPI
            # This would replace the Firebase messaging from the old Flask app
            # For now, we'll just log that a notification should be sent
            print(f"NOTIFICATION: Lease cancelled by {current_user.email} for {recipient_email}, car: {car.name}")
        
        db.commit()
        
        return leaseCancelResponse(cancelled=True)
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error cancelling lease: {str(e)}"
        )

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
        db.flush()  # Get the lease ID, without commiting the transaction, the changes are stashed on the db untill we commit(), which means we can still rollback 
        
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



# !
# TODO: Here you need to get email and car name from id's, ALSO remake the sql table for Lease requests to add a foreign key to the lease table to get the IMG URL AND SUCH
@app.post("/v2/get_requests", response_model=requestListResponse)
async def get_requests(current_user: Annotated[User, Depends(get_current_user)]):
    """Get pending private ride requests (manager/v2/admin only)"""
    # work with LeaseRequests object 

    if not admin_or_manager(current_user.role):
        return HTTPException(
            status_code=401,
            detail="Unauthorized.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    session = connect_to_db()

    requests = session.query(model.LeaseRequests).filter(
        model.LeaseRequests.status != RequestStatus.canceled,
        model.LeaseRequests.status != RequestStatus.rejected
    ).all()

    list_request = []

    # for req in requests:
    #     list_request.append(
    #         requestEntry(
    #             request_id= req.id,
    #             request_status= req.status,
    #             car_id= 
    #             driver_id=
    #             image_url= req.img_url

    #             spz=
    #             starting_time=
    #             ending_time=

    #         )
    #     )



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

