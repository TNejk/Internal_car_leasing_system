import os
import jwt
from passlib.context import CryptContext
import db.models as model
from fastapi import HTTPException, Header, status, Depends
from sqlalchemy.orm import Session
import api_models.default as modef
from datetime import datetime, timedelta, timezone
from .database import connect_to_db
from typing import Annotated
from fastapi.security import OAuth2PasswordBearer
from internal.token_models import TokenData

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
SECRET_KEY = os.environ.get('APP_SECRET_KEY')
LOGIN_SALT = os.environ.get('LOGIN_SALT')
ALGORITHM = "HS256"

def verify_password(plain_password, hashed_password):
  salted_pass = LOGIN_SALT + plain_password + LOGIN_SALT
  return pwd_context.verify(salted_pass, hashed_password)


def get_password_hash(password):
  salted_pass = LOGIN_SALT + password + LOGIN_SALT
  return pwd_context.hash(salted_pass)


def authenticate_user(email: str, password: str, db: Session) -> modef.User:
  user = model.Users
  db_user = db.query(user).filter(
    user.email == email,
    user.is_deleted == False
  ).first()

  if not db_user:
    return None

  if not verify_password(password, db_user.password):
    return None

  # Convert SQLAlchemy model to Pydantic model
  return modef.User(
    email=db_user.email,
    role=db_user.role.value,  # Since role is an Enum
    name=db_user.name,  # Using name as username
    disabled=db_user.is_deleted
  )


# data is a dictionary of all metadata we want, if the expiry date is not specified its set at 15 minutes
def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
  to_encode = data.copy()
  if expires_delta:
    expire = datetime.now(timezone.utc) + expires_delta
  else:
    expire = datetime.now(timezone.utc) + timedelta(minutes=15)
  to_encode.update({"exp": expire})
  encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
  return encoded_jwt


def get_existing_user(email: str, role: str, db: Session) -> modef.User:
  """Check in the database for a non-deleted user that matches the email role combo"""
  db_user = db.query(model.Users).filter(
    model.Users.email == email,
    model.Users.role == role,
    model.Users.is_deleted == False
  ).first()

  if not db_user:
    return None

  return modef.User(
    email=db_user.email,
    role=db_user.role.value,
    name=db_user.name,
    disabled=db_user.is_deleted
  )


def get_current_user(token: Annotated[str, Depends(oauth2_scheme)], db: Session = Depends(connect_to_db)) -> modef.User:
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

  except jwt.InvalidTokenError:
    raise cred_exception

  user = get_existing_user(email=email, role=role, db=db)
  if not user:
    raise cred_exception
  return user
