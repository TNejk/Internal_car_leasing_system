from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from typing import Annotated
from internal.dependencies import get_current_user, connect_to_db
import api_models.default as modef
import api_models.request as moreq
import api_models.response as mores
from sqlalchemy.orm import Session

router = APIRouter(prefix='/v2/auth', tags=['auth'])
TOKEN_EXPIRATION_MINUTES = 30

@router.post("/logout/", response_model=modef.DefaultResponse)
async def logout(current_user: Annotated[modef.User, Depends(get_current_user)]):
  """Logout endpoint to revoke JWT token"""
  pass


@router.post("/register/", response_model=modef.DefaultResponse)
async def register(request: moreq.UserRegister, current_user: Annotated[modef.User, Depends(get_current_user)]):
  """Register a new user (admin only)"""

  http_exception = HTTPException(status_code=401, detail="Unauthorized.")

  if not admin_or_manager(current_user.role):
    raise HTTPException(
      status_code=status.HTTP_401_UNAUTHORIZED,
      detail="Unauthorized access. Admin or manager role required.",
      headers={"WWW-Authenticate": "Bearer"}
    )
  pass


@router.post("/login/", response_model=mores.LoginResponse)
async def login(form_data: Annotated[OAuth2PasswordRequestForm, Depends()], db: Session = Depends(connect_to_db)):
  """ Login user to app, returns a login_response obj that includes a token and role email combo. """
  user = depend.auth.authenticate_user(
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

  access_token = dependencies.auth.create_access_token(
    data={"sub": user.email, "role": user.role},
    expires_delta=timedelta(minutes=TOKEN_EXPIRATION_MINUTES)
  )

  return mores.LoginResponse(
    token=access_token,
    email=user.email,
    role=user.role
  )

